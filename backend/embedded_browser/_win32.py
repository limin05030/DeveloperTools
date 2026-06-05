# -*- coding: utf-8 -*-
"""
嵌入式原生浏览器（Windows Edge WebView2 — 原生控件）

直接通过 WebView2 COM 接口在主窗口中创建子窗口控件。
与 macOS WKWebView 方案一致：创建原生浏览器控件（不是 iframe）
→ X-Frame-Options / CSP 不适用。

依赖：Windows 10+ 自带 WebView2 Runtime，或需安装 Edge WebView2。
"""

import sys
import logging
import ctypes
from ctypes import wintypes, byref, POINTER, cast, HRESULT
import os
import threading

log = logging.getLogger(__name__)

SIDEBAR_W = 220
TAB_BAR_H = 68

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# ---- WebView2 vtbl 索引（基于 WebView2.h v1.0）----
# ICoreWebView2Environment : IUnknown
#   3: CreateCoreWebView2Controller(HWND, handler)
# ICoreWebView2Controller : IUnknown
#   4: put_IsVisible(BOOL)
#   6: put_Bounds(RECT)
#   14: get_CoreWebView2(ICoreWebView2**)
# ICoreWebView2 : IUnknown
#   5: Navigate(LPCWSTR)


class EmbeddedBrowser:

    def __init__(self):
        self._views = {}        # tab_id -> (ctrl_ptr, wv_ptr)
        self._urls = {}
        self._current = None
        self._initialized = False
        self._hwnd_main = None
        self._env_ptr = None    # ICoreWebView2Environment*
        self._dll = None

    def _find_main_window(self):
        self._hwnd_main = user32.FindWindowW(None, "开发者工具")
        return self._hwnd_main is not None

    def _load_dll(self):
        """加载 WebView2Loader.dll"""
        # 搜索路径
        search = [".\\WebView2Loader.dll", "WebView2Loader.dll"]

        # Edge 安装目录
        for edge_base in [
            os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)") +
            r"\Microsoft\Edge\Application",
            os.environ.get("ProgramFiles", r"C:\Program Files") +
            r"\Microsoft\Edge\Application",
        ]:
            if os.path.isdir(edge_base):
                for ver in sorted(os.listdir(edge_base), reverse=True):
                    p = os.path.join(edge_base, ver, "EBWebView", "x86",
                                     "EmbeddedBrowserWebView.dll")
                    if os.path.isfile(p):
                        search.append(p)
                        break

        # 系统目录
        import glob as _glob
        for p in _glob.glob(r"C:\Windows\System32\WebView2Loader*.dll"):
            search.append(p)

        for p in search:
            try:
                self._dll = ctypes.windll.LoadLibrary(p)
                return True
            except Exception:
                continue
        return False

    # ---- Environment 初始化 ----

    def _init_environment(self):
        if self._env_ptr:
            return True
        if not self._load_dll():
            log.warning("WebView2Loader.dll 未找到")
            return False

        try:
            fn = self._dll.CreateCoreWebView2EnvironmentWithOptions
            fn.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR,
                           ctypes.c_void_p, ctypes.c_void_p]
            fn.restype = HRESULT
        except AttributeError:
            log.warning("CreateCoreWebView2EnvironmentWithOptions 不存在")
            return False

        # 数据目录（确保持久化）
        data_dir = os.path.join(
            os.path.dirname(self._hwnd_path() or os.getcwd()),
            "WebView2Data")

        env_ready = threading.Event()
        env_result = []

        @ctypes.WINFUNCTYPE(HRESULT, c_void_p, c_void_p, c_void_p)
        def _cb(hr, env_ptr, _):
            if hr >= 0 and env_ptr:
                env_result.append(env_ptr)
            env_ready.set()
            return 0

        hr = fn(None, ctypes.create_unicode_buffer(data_dir), None, _cb)
        if hr >= 0:
            env_ready.wait(10)

        if env_result:
            self._env_ptr = env_result[0]
            return True
        return False

    def _hwnd_path(self):
        """获取主程序路径"""
        try:
            import __main__
            return __main__.__file__
        except Exception:
            pass
        return None

    # ---- 创建 WebView2 控件 ----

    def _create_controller(self, parent_hwnd):
        """在指定父窗口中创建 WebView2 controller"""

        # ICoreWebView2Environment::CreateCoreWebView2Controller
        ctrl_ready = threading.Event()
        ctrl_result = []

        @ctypes.WINFUNCTYPE(HRESULT, c_void_p, c_void_p, c_void_p)
        def _cb(hr, ctrl_ptr, _):
            if hr >= 0 and ctrl_ptr:
                ctrl_result.append(ctrl_ptr)
            ctrl_ready.set()
            return 0

        # 调用 env.vtbl[3] = CreateCoreWebView2Controller
        env = cast(self._env_ptr, POINTER(POINTER(ctypes.c_void_p)))
        vtbl = env[0]
        fn = cast(vtbl[3], ctypes.CFUNCTYPE(
            HRESULT, ctypes.c_void_p, wintypes.HWND, ctypes.c_void_p))
        hr = fn(self._env_ptr, parent_hwnd, _cb)
        if hr >= 0:
            ctrl_ready.wait(15)

        if ctrl_result:
            return ctrl_result[0]
        return None

    def _get_webview(self, ctrl_ptr):
        """从 controller 获取 ICoreWebView2 接口"""
        ctrl = cast(ctrl_ptr, POINTER(POINTER(ctypes.c_void_p)))
        vtbl = ctrl[0]
        fn = cast(vtbl[14], ctypes.CFUNCTYPE(
            HRESULT, ctypes.c_void_p, POINTER(ctypes.c_void_p)))
        wv_ptr = ctypes.c_void_p()
        hr = fn(ctrl_ptr, byref(wv_ptr))
        if hr >= 0:
            return wv_ptr
        return None

    def _navigate(self, wv_ptr, url):
        """导航 WebView2 到指定 URL"""
        wv = cast(wv_ptr, POINTER(POINTER(ctypes.c_void_p)))
        vtbl = wv[0]
        fn = cast(vtbl[5], ctypes.CFUNCTYPE(
            HRESULT, ctypes.c_void_p, wintypes.LPCWSTR))
        fn(wv_ptr, url)

    def _position_and_show(self, ctrl_ptr, show=True):
        """定位 WebView2 控件并设置可见性"""
        ctrl = cast(ctrl_ptr, POINTER(POINTER(ctypes.c_void_p)))
        vtbl = ctrl[0]

        # put_Bounds
        rect = wintypes.RECT()
        user32.GetClientRect(self._hwnd_main, byref(rect))
        bounds = wintypes.RECT(
            SIDEBAR_W, TAB_BAR_H,
            max(rect.right, 100),
            max(rect.bottom, 100))
        fn_bounds = cast(vtbl[6], ctypes.CFUNCTYPE(
            HRESULT, ctypes.c_void_p, wintypes.RECT))
        fn_bounds(ctrl_ptr, bounds)

        # put_IsVisible
        fn_vis = cast(vtbl[4], ctypes.CFUNCTYPE(
            HRESULT, ctypes.c_void_p, wintypes.BOOL))
        fn_vis(ctrl_ptr, show)

    # ---- 公共接口 ----

    def _ensure_setup(self):
        if self._initialized and self._env_ptr:
            return True
        self._initialized = True
        if not sys.platform == "win32":
            return False
        if not self._find_main_window():
            return False
        return self._init_environment()

    def show_tab(self, tab_id, url=None):
        if not self._ensure_setup():
            return False
        try:
            if url is None:
                url = self._urls.get(tab_id)
            if not url:
                return False

            # 隐藏当前
            if self._current and self._current in self._views:
                self._position_and_show(self._views[self._current][0], False)

            # 创建或显示
            if tab_id not in self._views:
                ctrl_ptr = self._create_controller(self._hwnd_main)
                if not ctrl_ptr:
                    raise RuntimeError("WebView2 controller 创建失败")
                wv_ptr = self._get_webview(ctrl_ptr)
                self._navigate(wv_ptr, url)
                self._views[tab_id] = (ctrl_ptr, wv_ptr)
                self._urls[tab_id] = url

            self._position_and_show(self._views[tab_id][0], True)
            self._current = tab_id
            return True
        except Exception:
            log.exception("Win32 show_tab failed")
            return False

    def hide(self):
        for ctrl_ptr, _ in self._views.values():
            try:
                self._position_and_show(ctrl_ptr, False)
            except Exception:
                pass
        self._current = None


_embedded_browser = None


def get_embedded_browser():
    global _embedded_browser
    if _embedded_browser is None:
        _embedded_browser = EmbeddedBrowser()
    return _embedded_browser
