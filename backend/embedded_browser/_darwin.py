# -*- coding: utf-8 -*-
"""
嵌入式原生浏览器（macOS WKWebView）

每个标签页一个 WKWebView，切换时显示/隐藏。
绕过 X-Frame-Options / CSP：原生 WKWebView 不是 iframe。
"""

import sys
import logging

log = logging.getLogger(__name__)

SIDEBAR_W = 220
TAB_BAR_H = 68  # content padding(20) + tab-sub-nav(32) + border(1) + margin(15)


class EmbeddedBrowser:

    def __init__(self):
        self._views = {}      # tab_id -> WKWebView
        self._urls = {}       # tab_id -> url
        self._current = None  # 当前显示的 tab_id
        self._initialized = False
        self._main_content = None  # contentView 引用

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
        import time
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
        from Foundation import NSMakeRect

        for w in AppKit.NSApp.windows():
            if w.title() == "开发者工具":
                main_win = w
                break
        else:
            return False

        self._main_content = main_win.contentView()
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
            log.exception("init failed")
            return False

    def _create_view(self, tab_id, url):
        """为主线程创建 WKWebView（必须主线程调用）"""
        if tab_id in self._views:
            return self._views[tab_id]

        import AppKit
        from WebKit import WKWebView, WKWebViewConfiguration
        from Foundation import NSMakeRect, NSURL, NSURLRequest

        cw = self._main_content.frame().size.width
        ch = self._main_content.frame().size.height

        frame = NSMakeRect(SIDEBAR_W, TAB_BAR_H, max(cw - SIDEBAR_W, 100), ch - TAB_BAR_H)
        config = WKWebViewConfiguration.alloc().init()
        wv = WKWebView.alloc().initWithFrame_configuration_(frame, config)
        wv.setTranslatesAutoresizingMaskIntoConstraints_(True)
        wv.setAutoresizingMask_(
            AppKit.NSViewWidthSizable | AppKit.NSViewHeightSizable)
        wv.setHidden_(True)

        self._main_content.addSubview_(wv)

        # 加载 URL
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
            # 使用已有的 url（如果之前加载过）
            if url is None:
                url = self._urls.get(tab_id)
            if not url:
                return False

            def _switch():
                # 隐藏当前
                if self._current and self._current in self._views:
                    self._views[self._current].setHidden_(True)

                # 创建或显示目标
                wv = self._create_view(tab_id, url)
                wv.setHidden_(False)
                self._current = tab_id

            self._run_on_main(_switch)
            return True
        except Exception:
            log.exception("show_tab failed")
            return False

    def hide(self):
        """隐藏所有嵌入式视图"""
        if not self._main_content:
            return
        def _hide():
            for wv in self._views.values():
                wv.setHidden_(True)
            self._current = None
        self._run_on_main(_hide)


_embedded_browser = None


def get_embedded_browser():
    global _embedded_browser
    if _embedded_browser is None:
        _embedded_browser = EmbeddedBrowser()
    return _embedded_browser
