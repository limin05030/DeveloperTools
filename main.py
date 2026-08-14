# -*- coding: utf-8 -*-
import os
import sys
import webview
from backend.api import Api

# pip freeze > requirements.txt （不要使用这个命令更新requirements.txt，有些库是 macOS 平台专有的）
# pip install -r requirements.txt
# pip install pyinstaller
# git tag v1.0.0
# git push origin v1.0.0

DEBUG_MODE = True


def get_entrypoint():
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base_path, "web", "index.html")
    # 调试模式下通过 hash 激活 eruda（仅 macOS）
    if DEBUG_MODE and sys.platform == "darwin":
        path += "#eruda=1"
    return path


if __name__ == "__main__":
    # SSL 证书路径（仅需在启动时设置一次）
    import certifi
    os.environ['SSL_CERT_FILE'] = certifi.where()

    api = Api(DEBUG_MODE)
    window = webview.create_window(
        "开发者工具",
        get_entrypoint(),
        js_api=api,
        width=1200,
        height=880,
        min_size=(1200, 880),
        resizable=True,
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

    window.events.loaded += _on_loaded

    webview.start(debug=DEBUG_MODE)
