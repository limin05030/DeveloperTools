# -*- coding: utf-8 -*-
# Author: sens
# Date: 2026/05/13

import wx
from ui.app import DeveloperToolsApp

if __name__ == "__main__":
    app = wx.App(False)
    frame = DeveloperToolsApp(None)
    frame.Show()
    app.MainLoop()
