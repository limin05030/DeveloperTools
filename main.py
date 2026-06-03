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
    # if DEBUG_MODE:
    #     webview.settings['OPEN_DEVTOOLS_IN_DEBUG'] = True
    #     webview.settings['REMOTE_DEBUGGING_PORT'] = 9222
        # webview.create_window('调试窗口', 'https://pywebview.flowrl.com/hello')
    webview.start(debug=DEBUG_MODE)
