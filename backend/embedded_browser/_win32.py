# -*- coding: utf-8 -*-
"""
嵌入式原生浏览器（Windows Edge WebView2）

Windows 上通过查找主窗口 HWND，创建子窗口并附加。
由于 WebView2 初始化流程复杂，当前使用 pywebview.create_window 作为临时方案。
"""

import logging
import webview

log = logging.getLogger(__name__)

SIDEBAR_W = 220
TAB_BAR_H = 68


class EmbeddedBrowser:

    def __init__(self):
        self._windows = {}     # tab_id -> pywebview Window
        self._urls = {}
        self._current = None
        self._initialized = False

    def _ensure_setup(self):
        if self._initialized:
            return True
        self._initialized = True
        return True

    def show_tab(self, tab_id, url=None):
        if not self._ensure_setup():
            return False
        try:
            if url is None:
                url = self._urls.get(tab_id)
            if not url:
                return False

            # 隐藏上一个
            if self._current and self._current in self._windows:
                try:
                    self._windows[self._current].hide()
                except Exception:
                    pass

            # 创建或显示
            if tab_id not in self._windows:
                win = webview.create_window(tab_id, url, width=980, height=848)
                self._windows[tab_id] = win
                self._urls[tab_id] = url
            else:
                self._windows[tab_id].show()

            self._current = tab_id
            return True
        except Exception:
            log.exception("Win32 show_tab failed")
            return False

    def hide(self):
        for w in self._windows.values():
            try:
                w.hide()
            except Exception:
                pass
        self._current = None


_embedded_browser = None


def get_embedded_browser():
    global _embedded_browser
    if _embedded_browser is None:
        _embedded_browser = EmbeddedBrowser()
    return _embedded_browser
