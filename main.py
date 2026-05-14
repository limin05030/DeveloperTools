# -*- coding: utf-8 -*-
# Author: sens
# Date: 2026/05/13

import wx
from ui.app import DeveloperToolsApp

# pip freeze > requirements.txt
# pip install -r requirements.txt
# pip install pyinstaller
# git tag v1.0.0
# git push origin v1.0.0
if __name__ == "__main__":
    app = wx.App(False)
    frame = DeveloperToolsApp(None)
    frame.Show()
    app.MainLoop()
