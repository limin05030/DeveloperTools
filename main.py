# -*- coding: utf-8 -*-
import os
import sys
import webview
from backend.api import Api

def get_entrypoint():
    # PyInstaller 打包后的临时目录路径存储在 _MEIPASS 中
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(base_path, "web", "index.html")

if __name__ == "__main__":
    api = Api()
    window = webview.create_window(
        "开发者工具",
        get_entrypoint(),
        js_api=api,
        width=1000,
        height=880,
        resizable=False  # 固定尺寸，不可缩放/最大化
    )
    api.set_window(window)
    webview.start(debug=False)
