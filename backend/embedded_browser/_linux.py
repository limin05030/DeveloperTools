# -*- coding: utf-8 -*-
"""
嵌入式原生浏览器（Linux GTK WebKit2）

通过 Gtk.POPUP 窗口附加到 pywebview 主窗口，内置 WebKit2.WebView。
绕过 X-Frame-Options / CSP：原生 WebView 不是 iframe。
"""

import logging
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.0')
from gi.repository import Gtk, WebKit2, GLib

log = logging.getLogger(__name__)

SIDEBAR_W = 220
TAB_BAR_H = 68


class EmbeddedBrowser:

    def __init__(self):
        self._views = {}       # tab_id -> (popup, webview)
        self._urls = {}
        self._current = None
        self._initialized = False
        self._main_window = None

    # ---------- GTK 主线程调度 ----------

    def _run_on_gtk(self, func):
        """在 GTK 主线程执行函数"""
        result = []
        done = []

        def _wrapper():
            try:
                result.append(func())
            except Exception as e:
                result.append(e)
            done.append(True)

        GLib.idle_add(_wrapper)
        import time
        deadline = time.time() + 5.0
        while not done and time.time() < deadline:
            Gtk.main_iteration_do(False)
        if result:
            r = result[0]
            if isinstance(r, Exception):
                raise r
            return r
        return None

    # ---------- 初始化 ----------

    def _init_impl(self):
        for w in Gtk.Window.list_toplevels():
            if w.get_title() == "开发者工具":
                self._main_window = w
                return True
        return False

    def _ensure_setup(self):
        if self._initialized:
            return self._main_window is not None
        self._initialized = True
        try:
            return bool(self._run_on_gtk(self._init_impl))
        except Exception:
            log.exception("Linux init failed")
            return False

    def _create_view(self, tab_id, url):
        if tab_id in self._views:
            return self._views[tab_id]

        popup = Gtk.Window(type=Gtk.WindowType.POPUP)
        popup.set_transient_for(self._main_window)

        webview = WebKit2.WebView()
        webview.load_uri(url)
        popup.add(webview)

        # 计算位置
        main_alloc = self._main_window.get_allocation()
        popup.set_default_size(
            max(main_alloc.width - SIDEBAR_W, 100),
            main_alloc.height - TAB_BAR_H)

        popup.show_all()
        # 先隐藏，等切换时再显示
        popup.hide()

        self._views[tab_id] = (popup, webview)
        self._urls[tab_id] = url
        return (popup, webview)

    # ---------- 公共 API ----------

    def show_tab(self, tab_id, url=None):
        if not self._ensure_setup():
            return False
        try:
            if url is None:
                url = self._urls.get(tab_id)
            if not url:
                return False

            def _switch():
                # 隐藏当前
                if self._current and self._current in self._views:
                    self._views[self._current][0].hide()

                # 创建或显示目标
                popup, wv = self._create_view(tab_id, url)

                # 重新定位
                main_win_pos = self._main_window.get_position()
                main_alloc = self._main_window.get_allocation()
                popup.move(
                    main_win_pos[0] + SIDEBAR_W,
                    main_win_pos[1] + TAB_BAR_H)
                popup.resize(
                    max(main_alloc.width - SIDEBAR_W, 100),
                    main_alloc.height - TAB_BAR_H)
                popup.show_all()
                self._current = tab_id

            self._run_on_gtk(_switch)
            return True
        except Exception:
            log.exception("Linux show_tab failed")
            return False

    def hide(self):
        if not self._main_window:
            return

        def _hide():
            for popup, _ in self._views.values():
                popup.hide()
            self._current = None

        self._run_on_gtk(_hide)


_embedded_browser = None


def get_embedded_browser():
    global _embedded_browser
    if _embedded_browser is None:
        _embedded_browser = EmbeddedBrowser()
    return _embedded_browser
