# -*- coding: utf-8 -*-
"""
嵌入式原生浏览器（Windows Edge WebView2）

创建无边框 pywebview 窗口，通过 Win32 API 附加为子窗口并定位在内容区。
绕过 X-Frame-Options / CSP：原生 WebView2 不是 iframe。
"""

import sys
import logging
import ctypes
from ctypes import wintypes
import webview

log = logging.getLogger(__name__)

SIDEBAR_W = 220
TAB_BAR_H = 68

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

GWL_STYLE = -16
GWL_EXSTYLE = -20
WS_CHILD = 0x40000000
WS_POPUP = 0x80000000
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
WS_SYSMENU = 0x00080000
WS_MINIMIZEBOX = 0x00020000
WS_MAXIMIZEBOX = 0x00010000
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040


class EmbeddedBrowser:

    def __init__(self):
        self._windows = {}     # tab_id -> pywebview Window
        self._urls = {}
        self._hwnds = {}       # tab_id -> HWND
        self._current = None
        self._initialized = False
        self._hwnd_main = None

    def _find_main_window(self):
        if self._hwnd_main:
            return True
        hwnd = user32.FindWindowW(None, "开发者工具")
        if hwnd:
            self._hwnd_main = hwnd
            return True
        return False

    def _ensure_setup(self):
        if self._initialized:
            return True
        self._initialized = True
        if not sys.platform == "win32":
            return False
        return self._find_main_window()

    def _make_child_window(self, win, tab_id):
        """将 pywebview 窗口改为无边框并附加到主窗口"""
        # pywebview 的 Window 对象有一个隐藏的 _window 属性（平台相关）
        # 通过遍历所有顶层窗口找到匹配标题的 HWND
        title = f"__eb_{tab_id}__"
        hwnd = user32.FindWindowW(None, title)
        if not hwnd:
            return

        # 去掉边框、标题栏
        style = user32.GetWindowLongW(hwnd, GWL_STYLE)
        style &= ~(WS_CAPTION | WS_THICKFRAME | WS_SYSMENU |
                    WS_MINIMIZEBOX | WS_MAXIMIZEBOX)
        user32.SetWindowLongW(hwnd, GWL_STYLE, style)

        # 定位到主窗口内容区
        self._reposition(hwnd)

        # 设为子窗口
        ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)

        self._hwnds[tab_id] = hwnd

    def _reposition(self, hwnd):
        """重新定位窗口到主窗口内容区"""
        if not self._hwnd_main:
            return
        rect = wintypes.RECT()
        user32.GetWindowRect(self._hwnd_main, ctypes.byref(rect))
        user32.SetWindowPos(
            hwnd, 0,
            rect.left + SIDEBAR_W,
            rect.top + TAB_BAR_H,
            max(rect.right - rect.left - SIDEBAR_W, 100),
            max(rect.bottom - rect.top - TAB_BAR_H, 100),
            SWP_NOZORDER | SWP_NOACTIVATE | SWP_SHOWWINDOW)

    def show_tab(self, tab_id, url=None):
        if not self._ensure_setup():
            return False
        try:
            if url is None:
                url = self._urls.get(tab_id)
            if not url:
                return False

            # 隐藏当前
            if self._current and self._current in self._hwnds:
                user32.ShowWindow(self._hwnds[self._current], 0)

            # 创建或显示
            if tab_id not in self._windows:
                title = f"__eb_{tab_id}__"
                win = webview.create_window(title, url,
                                            width=980, height=800)
                self._windows[tab_id] = win
                self._urls[tab_id] = url
                # 等窗口创建完成后再修改样式
                import time
                time.sleep(0.3)
                self._make_child_window(win, tab_id)
            else:
                self._reposition(self._hwnds[tab_id])
                user32.ShowWindow(self._hwnds[tab_id], 1)

            self._current = tab_id
            return True
        except Exception:
            log.exception("Win32 show_tab failed")
            return False

    def hide(self):
        for hwnd in self._hwnds.values():
            try:
                user32.ShowWindow(hwnd, 0)
            except Exception:
                pass
        self._current = None


_embedded_browser = None


def get_embedded_browser():
    global _embedded_browser
    if _embedded_browser is None:
        _embedded_browser = EmbeddedBrowser()
    return _embedded_browser
