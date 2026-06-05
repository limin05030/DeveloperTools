# -*- coding: utf-8 -*-
"""
嵌入式原生浏览器（Windows Edge WebView2）

创建无边框 pywebview 窗口 + 实时跟随主窗口位置。
保持顶层窗口 → WebView2 不会触发反嵌套检测。
通过 Win32 定时器/消息钩子持续同步位置，视觉上嵌入在内容区域。
"""

import sys
import logging
import ctypes
from ctypes import wintypes
import threading
import webview

log = logging.getLogger(__name__)

SIDEBAR_W = 220
TAB_BAR_H = 68

user32 = ctypes.windll.user32

GWL_STYLE = -16
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
WS_SYSMENU = 0x00080000
WS_MINIMIZEBOX = 0x00020000
WS_MAXIMIZEBOX = 0x00010000
HWND_TOPMOST = -1
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040


class EmbeddedBrowser:

    def __init__(self):
        self._windows = {}
        self._urls = {}
        self._hwnds = {}
        self._current = None
        self._initialized = False
        self._hwnd_main = None
        self._tracker = None
        self._tracking = False

    def _find_main_window(self):
        self._hwnd_main = user32.FindWindowW(None, "开发者工具")
        return self._hwnd_main is not None

    def _ensure_setup(self):
        if self._initialized:
            return True
        self._initialized = True
        if not sys.platform == "win32":
            return False
        return self._find_main_window()

    def _reposition_all(self):
        """将所有可见的浮动窗口定位到主窗口内容区"""
        if not self._hwnd_main:
            return
        try:
            rect = wintypes.RECT()
            if not user32.IsWindow(self._hwnd_main):
                return
            user32.GetWindowRect(self._hwnd_main, ctypes.byref(rect))
            x = rect.left + SIDEBAR_W
            y = rect.top + TAB_BAR_H
            w = max(rect.right - rect.left - SIDEBAR_W, 100)
            h = max(rect.bottom - rect.top - TAB_BAR_H, 100)

            for tab_id, hwnd in self._hwnds.items():
                if user32.IsWindow(hwnd) and user32.IsWindowVisible(hwnd):
                    user32.SetWindowPos(hwnd, HWND_TOPMOST,
                                        x, y, w, h,
                                        SWP_NOACTIVATE)
        except Exception:
            pass

    def _start_tracking(self):
        """启动后台线程持续同步位置"""
        if self._tracking:
            return
        self._tracking = True
        def _track():
            import time
            while self._tracking:
                self._reposition_all()
                time.sleep(0.1)
        self._tracker = threading.Thread(target=_track, daemon=True)
        self._tracker.start()

    def _stop_tracking(self):
        self._tracking = False

    def _make_floating(self, hwnd):
        """去掉边框并设为置顶"""
        style = user32.GetWindowLongW(hwnd, GWL_STYLE)
        style &= ~(WS_CAPTION | WS_THICKFRAME | WS_SYSMENU |
                    WS_MINIMIZEBOX | WS_MAXIMIZEBOX)
        user32.SetWindowLongW(hwnd, GWL_STYLE, style)

    def _find_child_hwnd(self, title):
        import time
        for _ in range(50):
            hwnd = user32.FindWindowW(None, title)
            if hwnd:
                return hwnd
            time.sleep(0.1)
        return None

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

            if tab_id not in self._windows:
                title = f"__eb_{tab_id}__"
                win = webview.create_window(title, url,
                                            width=980, height=800)
                self._windows[tab_id] = win
                self._urls[tab_id] = url

                hwnd = self._find_child_hwnd(title)
                if hwnd:
                    self._make_floating(hwnd)
                    self._hwnds[tab_id] = hwnd

                # 开始跟踪主窗口位置
                self._start_tracking()
            else:
                hwnd = self._hwnds[tab_id]
                user32.ShowWindow(hwnd, 1)

            # 立即定位
            self._reposition_all()
            self._current = tab_id
            return True
        except Exception:
            log.exception("Win32 show_tab failed")
            return False

    def hide(self):
        self._stop_tracking()
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
