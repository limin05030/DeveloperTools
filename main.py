# -*- coding: utf-8 -*-
import os
import sys
import webview
from backend.api import Api

DEBUG_MODE = True

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
    webview.start(debug=DEBUG_MODE)
