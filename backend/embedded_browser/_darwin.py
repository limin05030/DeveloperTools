# -*- coding: utf-8 -*-
"""
嵌入式原生浏览器（macOS WKWebView）

每个标签页一个 WKWebView，切换时显示/隐藏。
绕过 X-Frame-Options / CSP：原生 WKWebView 不是 iframe。

Cookie 持久化机制：
    1. 所有标签页共享 WKProcessPool，确保会话互通
    2. 显式使用 defaultDataStore() 配置持久化存储
    3. 离开 AI 聊天标签页时，通过 WKHTTPCookieStore API 获取所有 cookies
       （包括 HTTPOnly），序列化保存到 ~/.developer_tools/
    4. 下次启动时，通过 NSHTTPCookieStorage 同步恢复 cookies
       （setCookie_ 是同步方法，无需等待回调）
    5. macOS 上关闭窗口仅隐藏而非退出（main.py 中处理），
       保留会话 Cookie 在进程内存中
"""

import os
import sys
import json
import logging
import time

log = logging.getLogger(__name__)

SIDEBAR_W = 220
TAB_BAR_H = 68

COOKIE_DIR = os.path.expanduser("~/.developer_tools")
COOKIE_FILE = os.path.join(COOKIE_DIR, "webkit_cookies.json")


def _ensure_cookie_dir():
    os.makedirs(COOKIE_DIR, exist_ok=True)


class EmbeddedBrowser:

    def __init__(self):
        self._views = {}           # tab_id → WKWebView
        self._urls = {}            # tab_id → url
        self._current = None       # 当前显示的 tab_id
        self._initialized = False
        self._main_content = None  # NSWindow.contentView 引用
        self._process_pool = None  # 共享 WKProcessPool
        self._cookies_restored = False

    # ---------- 主线程调度 ----------

    def _run_on_main(self, func):
        from Foundation import NSThread, NSOperationQueue
        if NSThread.isMainThread():
            return func()
        result = []
        done = []
        def wrapper():
            try:
                result.append(func())
            except Exception as e:
                result.append(e)
            done.append(True)
        NSOperationQueue.mainQueue().addOperationWithBlock_(wrapper)
        while not done:
            time.sleep(0.01)
        if result:
            r = result[0]
            if isinstance(r, Exception):
                raise r
            return r
        return None

    # ---------- 初始化 ----------

    def _init_impl(self):
        import AppKit

        for w in AppKit.NSApp.windows():
            if w.title() == "开发者工具":
                main_win = w
                break
        else:
            return False

        self._main_content = main_win.contentView()

        # 设置稳定的进程名，帮助 WebKit 在多次运行时使用相同的数据目录
        try:
            from Foundation import NSProcessInfo
            proc_info = NSProcessInfo.processInfo()
            if proc_info.processName() in ("Python", "python", "python3"):
                proc_info.setProcessName_("DeveloperTools")
        except Exception:
            pass

        # 创建共享 WKProcessPool，所有标签页共享 cookies 和登录会话
        from WebKit import WKProcessPool
        self._process_pool = WKProcessPool.alloc().init()

        # 从磁盘恢复之前保存的 cookies
        self._restore_cookies()

        return True

    def _ensure_setup(self):
        if self._initialized:
            return bool(self._main_content)
        self._initialized = True
        if sys.platform != "darwin":
            return False
        try:
            return bool(self._run_on_main(self._init_impl))
        except Exception:
            log.exception("初始化嵌入式浏览器失败")
            return False

    # ---------- Cookies 保存 ----------

    def _save_cookies(self):
        """异步保存 cookies 到磁盘（fire-and-forget，不阻塞主线程）"""
        return  # TODO: 排查卡死，暂时禁用
        if not self._views:
            return

        from WebKit import WKWebsiteDataStore
        store = WKWebsiteDataStore.defaultDataStore().httpCookieStore()

        # 检测可用的 get 方法（兼容不同 macOS 版本的 PyObjC 命名）
        get_method = None
        for name in ['getAllCookies_', 'getAllCookiesWithCompletionHandler_']:
            if hasattr(store, name):
                get_method = name
                break

        if not get_method:
            log.warning("WKHTTPCookieStore 无可用的 getAllCookies 方法")
            return

        def _on_complete(all_cookies):
            try:
                by_domain = {}
                for cookie in (all_cookies or []):
                    try:
                        domain = str(cookie.domain())
                        cd = {
                            "name": str(cookie.name()),
                            "value": str(cookie.value()),
                            "domain": domain,
                            "path": str(cookie.path()) if cookie.path() else "/",
                            "isSecure": bool(cookie.isSecure()),
                            "isHTTPOnly": bool(cookie.isHTTPOnly()),
                            "expiresDate": (
                                cookie.expiresDate().timeIntervalSince1970()
                                if cookie.expiresDate() else None
                            ),
                            "sameSite": (
                                str(cookie.sameSitePolicy())
                                if hasattr(cookie, 'sameSitePolicy') and cookie.sameSitePolicy() else None
                            ),
                        }
                        by_domain.setdefault(domain, []).append(cd)
                    except Exception:
                        continue

                _ensure_cookie_dir()
                with open(COOKIE_FILE, 'w', encoding='utf-8') as f:
                    json.dump(by_domain, f, ensure_ascii=False, indent=2)

                total = sum(len(v) for v in by_domain.values())
                log.info("已保存 %d 个域名共 %d 个 cookies", len(by_domain), total)
            except Exception:
                log.exception("保存 cookies 失败")

        getattr(store, get_method)(_on_complete)

    # ---------- Cookies 恢复 ----------

    def _restore_cookies(self):
        """同步恢复 cookies 到 NSHTTPCookieStorage（必须在主线程调用）"""
        self._cookies_restored = True
        return  # TODO: 排查卡死，暂时禁用
        if not os.path.exists(COOKIE_FILE):
            self._cookies_restored = True
            return

        try:
            with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            log.exception("读取 cookies 缓存文件失败")
            self._cookies_restored = True
            return

        if not isinstance(data, dict) or not data:
            self._cookies_restored = True
            return

        from Foundation import (
            NSHTTPCookieStorage, NSMutableDictionary, NSURL,
            NSHTTPCookieName, NSHTTPCookieValue, NSHTTPCookieDomain,
            NSHTTPCookiePath, NSHTTPCookieSecure, NSHTTPCookieExpires,
        )
        from WebKit import NSHTTPCookie

        storage = NSHTTPCookieStorage.sharedHTTPCookieStorage()
        total = sum(len(v) for v in data.values())

        restored = 0
        for domain, cookies in data.items():
            for cd in cookies:
                cookie = None

                # 方法 1：用 Set-Cookie header 格式解析（支持 HttpOnly、SameSite 等完整属性）
                try:
                    parts = [f"{cd['name']}={cd.get('value', '')}"]
                    parts.append(f"Domain={cd.get('domain', domain)}")
                    parts.append(f"Path={cd.get('path', '/')}")
                    if cd.get("isSecure"):
                        parts.append("Secure")
                    if cd.get("isHTTPOnly"):
                        parts.append("HttpOnly")
                    same_site = cd.get("sameSite")
                    if same_site and same_site != "None":
                        parts.append(f"SameSite={same_site}")
                    expires = cd.get("expiresDate")
                    if expires:
                        from Foundation import NSDateFormatter, NSLocale, NSTimeZone, NSDate
                        fmt = NSDateFormatter.alloc().init()
                        fmt.setDateFormat_("EEE, dd MMM yyyy HH:mm:ss z")
                        fmt.setLocale_(NSLocale.localeWithLocaleIdentifier_("en_US_POSIX"))
                        fmt.setTimeZone_(NSTimeZone.timeZoneWithName_("GMT"))
                        d = NSDate.dateWithTimeIntervalSince1970_(float(expires))
                        parts.append(f"Expires={fmt.stringFromDate_(d)}")

                    set_cookie_str = "; ".join(parts)
                    scheme = "https" if cd.get("isSecure") else "http"
                    url = NSURL.URLWithString_(f"{scheme}://{domain.lstrip('.')}/")
                    headers = NSMutableDictionary.dictionary()
                    headers.setObject_forKey_(set_cookie_str, "Set-Cookie")
                    found = NSHTTPCookie.cookiesWithResponseHeaderFields_forURL_(headers, url)
                    if found and len(found) > 0:
                        cookie = found[0]
                except Exception:
                    pass

                # 方法 2：属性字典方式（回退方案，不支持 HttpOnly 但确保基本功能）
                if not cookie:
                    try:
                        from Foundation import NSDate
                        props = NSMutableDictionary.dictionary()
                        props.setObject_forKey_(cd["name"], NSHTTPCookieName)
                        props.setObject_forKey_(cd.get("value", ""), NSHTTPCookieValue)
                        props.setObject_forKey_(cd.get("domain", domain), NSHTTPCookieDomain)
                        props.setObject_forKey_(cd.get("path", "/"), NSHTTPCookiePath)
                        if cd.get("isSecure"):
                            props.setObject_forKey_("TRUE", NSHTTPCookieSecure)
                        expires = cd.get("expiresDate")
                        if expires:
                            d = NSDate.dateWithTimeIntervalSince1970_(float(expires))
                            props.setObject_forKey_(d, NSHTTPCookieExpires)
                        cookie = NSHTTPCookie.cookieWithProperties_(props)
                    except Exception:
                        pass

                if cookie:
                    try:
                        storage.setCookie_(cookie)
                        restored += 1
                    except Exception:
                        pass

        log.info("已恢复 %d/%d 个 cookies", restored, total)

        # 同时异步同步到 WKHTTPCookieStore，双保险
        store = self._get_store()
        all_cookies = list(storage.cookies())
        if all_cookies and hasattr(store, 'setCookies_completionHandler_'):
            store.setCookies_completionHandler_(all_cookies, lambda: None)

        self._cookies_restored = True

    def _get_store(self):
        from WebKit import WKWebsiteDataStore
        return WKWebsiteDataStore.defaultDataStore().httpCookieStore()

    # ---------- 创建 WKWebView ----------

    def _create_view(self, tab_id, url):
        if tab_id in self._views:
            return self._views[tab_id]

        import AppKit
        from WebKit import (
            WKWebView, WKWebViewConfiguration, WKWebsiteDataStore,
            WKUserContentController, WKUserScript,
        )
        from Foundation import NSMakeRect, NSURL, NSURLRequest

        cw = self._main_content.frame().size.width
        ch = self._main_content.frame().size.height

        frame = NSMakeRect(SIDEBAR_W, TAB_BAR_H, max(cw - SIDEBAR_W, 100), ch - TAB_BAR_H)

        # 检测当前外观模式，确定背景色
        is_dark = False
        try:
            from AppKit import NSApp
            best_match = NSApp.effectiveAppearance().bestMatchFromAppearancesWithNames_(
                ["NSAppearanceNameDarkAqua", "NSAppearanceNameAqua"]
            )
            is_dark = best_match == "NSAppearanceNameDarkAqua"
        except Exception:
            pass

        bg_hex = "#121212" if is_dark else "#F2F2F7"

        config = WKWebViewConfiguration.alloc().init()
        config.setWebsiteDataStore_(WKWebsiteDataStore.defaultDataStore())
        if self._process_pool:
            config.setProcessPool_(self._process_pool)

        # 注入 CSS 在网页加载最早时机设置背景色，消除白色闪烁
        try:
            user_ctrl = WKUserContentController.alloc().init()
            js_code = (
                'var s=document.createElement("style");'
                's.textContent="html,body{background-color:' + bg_hex + '}";'
                'document.documentElement.appendChild(s);'
            )
            # WKUserScriptInjectionTimeAtDocumentStart = 0
            script = WKUserScript.alloc().initWithSource_injectionTime_forMainFrameOnly_(
                js_code, 0, True
            )
            user_ctrl.addUserScript_(script)
            config.setUserContentController_(user_ctrl)
        except Exception:
            pass  # 非关键功能，静默忽略

        wv = WKWebView.alloc().initWithFrame_configuration_(frame, config)
        wv.setTranslatesAutoresizingMaskIntoConstraints_(True)
        wv.setAutoresizingMask_(
            AppKit.NSViewWidthSizable | AppKit.NSViewHeightSizable)
        wv.setHidden_(True)

        # 设置原生层背景色（WKWebView 底层）
        try:
            from AppKit import NSColor
            if is_dark:
                bg_color = NSColor.colorWithRed_green_blue_alpha_(0.071, 0.071, 0.071, 1.0)
            else:
                bg_color = NSColor.colorWithRed_green_blue_alpha_(0.949, 0.949, 0.969, 1.0)
            wv.setValue_forKey_(bg_color, "underPageBackgroundColor")
        except Exception:
            pass  # 非关键功能，静默忽略

        self._main_content.addSubview_(wv)

        req = NSURLRequest.requestWithURL_(NSURL.URLWithString_(url))
        wv.loadRequest_(req)

        self._views[tab_id] = wv
        self._urls[tab_id] = url
        return wv

    # ---------- 公共 API ----------

    def show_tab(self, tab_id, url=None):
        """切换/显示标签页，首次使用时传入 url"""
        if not self._ensure_setup():
            return False
        try:
            if url is None:
                url = self._urls.get(tab_id)
            if not url:
                return False

            def _switch():
                if self._current and self._current in self._views:
                    self._views[self._current].setHidden_(True)
                wv = self._create_view(tab_id, url)
                wv.setHidden_(False)
                self._current = tab_id

            self._run_on_main(_switch)
            return True
        except Exception:
            log.exception("show_tab 失败")
            return False

    def hide(self):
        """隐藏所有嵌入式视图，并在隐藏前异步保存 cookies"""
        if not self._main_content:
            return

        def _hide_and_save():
            try:
                self._save_cookies()
            except Exception:
                log.exception("保存 cookies 时出错")

            for wv in self._views.values():
                wv.setHidden_(True)
            self._current = None

        self._run_on_main(_hide_and_save)

    def go_back(self):
        """当前标签页后退"""
        if not self._current or self._current not in self._views:
            return False
        try:
            def _back():
                self._views[self._current].goBack()
            self._run_on_main(_back)
            return True
        except Exception:
            log.exception("go_back 失败")
            return False

    def go_forward(self):
        """当前标签页前进"""
        if not self._current or self._current not in self._views:
            return False
        try:
            def _forward():
                self._views[self._current].goForward()
            self._run_on_main(_forward)
            return True
        except Exception:
            log.exception("go_forward 失败")
            return False

    def reload(self):
        """当前标签页刷新"""
        if not self._current or self._current not in self._views:
            return False
        try:
            def _reload():
                self._views[self._current].reload()
            self._run_on_main(_reload)
            return True
        except Exception:
            log.exception("reload 失败")
            return False


_embedded_browser = None


def get_embedded_browser():
    global _embedded_browser
    if _embedded_browser is None:
        _embedded_browser = EmbeddedBrowser()
    return _embedded_browser
