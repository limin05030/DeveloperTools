# -*- coding: utf-8 -*-
import os
import sys
import certifi
os.environ['SSL_CERT_FILE'] = certifi.where()
import webview
from backend.api import Api

# pip freeze > requirements.txt （不要使用这个命令更新requirements.txt，有些库是 macOS 平台专有的）
# pip install -r requirements.txt
# pip install pyinstaller
# git tag v1.0.0
# git push origin v1.0.0

DEBUG_MODE = False

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
        width=1000,
        height=880,
        resizable=False
    )
    api.set_window(window)

    if DEBUG_MODE and sys.platform != "win32":
        # macOS / Linux: WKWebView/GTK 不会自动弹出 DevTools，注入 eruda 作为页内调试面板
        window.events.loaded += lambda: window.evaluate_js(ERUDA_INJECT_JS)

    webview.start(debug=DEBUG_MODE)
