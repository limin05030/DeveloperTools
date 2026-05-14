# -*- coding: utf-8 -*-
import os
import wx
from ui.styles import ThemeManager
from ui.tabs.hash_tab import HashTab
from ui.tabs.encode_tab import EncodeTab
from ui.tabs.format_tab import FormatTab
from ui.tabs.time_tab import TimeTab
from ui.tabs.image_tab import ImageTab
from ui.tabs.generate_tab import GenerateTab
from ui.tabs.query_tab import QueryTab

class DeveloperToolsApp(wx.Frame):
    def __init__(self, parent):
        super(DeveloperToolsApp, self).__init__(parent, title="开发者工具", size=wx.Size(900, 750))
        self.notebook = None
        self._set_app_icon()
        self._init_ui()
        self.Centre()
        
        # 绑定系统颜色变化事件，实现实时主题切换
        self.Bind(wx.EVT_SYS_COLOUR_CHANGED, self._on_sys_colour_changed)

    def _set_app_icon(self):
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "images", "app.png")
        if os.path.exists(icon_path):
            icon = wx.Icon(icon_path, wx.BITMAP_TYPE_PNG)
            self.SetIcon(icon)

    def _init_ui(self):
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)
        self.notebook = wx.Notebook(panel)
        
        tabs = [
            (HashTab, "哈希计算"),
            (EncodeTab, "编码转换"),
            (FormatTab, "格式化工具"),
            (TimeTab, "日期时间"),
            (ImageTab, "图片处理"),
            (GenerateTab, "生成工具"),
            (QueryTab, "查询工具")
        ]

        for tab_class, label in tabs:
            page = tab_class(self.notebook)
            self.notebook.AddPage(page, label)

        vbox.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 5)
        panel.SetSizer(vbox)
        ThemeManager.apply_theme(self)

    def _on_sys_colour_changed(self, event):
        """系统主题变化时的回调"""
        ThemeManager.apply_theme(self)
        self.Refresh()
        event.Skip()
