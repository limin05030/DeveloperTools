# -*- coding: utf-8 -*-
import logging
import os
import sys

import certifi

os.environ['SSL_CERT_FILE'] = certifi.where()

import webview
from backend.api import Api

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(name)s: %(message)s')

# pip freeze > requirements.txt （不要使用这个命令更新requirements.txt，有些库是 macOS 平台专有的）
# pip install -r requirements.txt
# pip install pyinstaller
# git tag v1.0.0
# git push origin v1.0.0

DEBUG_MODE = True

# eruda — 轻量级移动端 DevTools，嵌入页面后无需系统配置即可使用 Console / Elements / Network 等面板
ERUDA_INJECT_JS = """
(function() {
    if (document.getElementById('eruda-script')) return;
    var script = document.createElement('script');
    script.id = 'eruda-script';
    script.src = 'https://cdn.jsdelivr.net/npm/eruda@3';
    script.onload = function() {
        eruda.init({
            tool: ['console', 'elements', 'network', 'resources', 'sources', 'info']
        });
        eruda.position({x: window.innerWidth - 50, y: window.innerHeight / 2 - 100});
        console.log('[eruda] DevTools ready. Drag the gear icon to move it.');
    };
    script.onerror = function() {
        console.warn('[eruda] Failed to load from CDN (offline?). DevTools unavailable.');
    };
    document.head.appendChild(script);
})();
"""


def get_entrypoint():
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, "web", "index.html")


if __name__ == "__main__":
    api = Api(DEBUG_MODE)
    window = webview.create_window(
        "开发者工具",
        get_entrypoint(),
        js_api=api,
        width=1200,
        height=880,
        resizable=False,
        hidden=True,  # 先隐藏，等背景色设好后再显示，避免白屏闪烁
    )
    api.set_window(window)

    def _on_loaded():
        """页面加载完成后：设置原生背景色 → 显示窗口 → 注入调试工具"""
        if sys.platform == "darwin":
            try:
                import AppKit
                from Foundation import NSColor

                for w in AppKit.NSApp.windows():
                    if w.title() == "开发者工具":
                        bg = NSColor.colorWithRed_green_blue_alpha_(
                            0.949, 0.949, 0.969, 1.0  # #F2F2F7
                        )
                        w.setBackgroundColor_(bg)
                        # 找到 pywebview 的 WKWebView 并设置底色
                        for sv in w.contentView().subviews():
                            name = (
                                sv.className()
                                if hasattr(sv, "className")
                                else str(type(sv))
                            )
                            if "WKWebView" in name:
                                sv.setValue_forKey_(bg, "underPageBackgroundColor")
            except Exception:
                pass

        window.show()

        if DEBUG_MODE and sys.platform != "win32":
            window.evaluate_js(ERUDA_INJECT_JS)

    # macOS：关闭窗口时隐藏而非退出，保留会话 Cookie（模仿 Safari 行为）
    if sys.platform == "darwin":
        def _on_closing():
            window.hide()
        window.events.closing += _on_closing

    window.events.loaded += _on_loaded

    webview.start(debug=DEBUG_MODE)
