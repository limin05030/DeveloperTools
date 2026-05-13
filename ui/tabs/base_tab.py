# -*- coding: utf-8 -*-
import wx
from ui.styles import ThemeManager

class BaseTab(wx.Panel):
    def __init__(self, parent):
        super(BaseTab, self).__init__(parent)
        self.root = wx.GetApp().GetTopWindow()
        self.SetBackgroundColour(ThemeManager.BG_WINDOW)

    def _safe_exec(self, func, output_ctrl):
        try:
            res = func()
            output_ctrl.SetValue(str(res))
            output_ctrl.SetForegroundColour(ThemeManager.SUCCESS_COLOR)
        except Exception as e:
            wx.MessageBox(f"操作失败: {str(e)}", "错误", wx.OK | wx.ICON_ERROR)

    def _create_label(self, parent, title):
        label = wx.StaticText(parent, label=title)
        label.SetFont(ThemeManager.get_font(14, bold=True))
        label.SetForegroundColour(ThemeManager.TEXT_PRIMARY)
        return label

    def _create_section_header(self, parent, title):
        container = wx.BoxSizer(wx.HORIZONTAL)
        line = wx.StaticText(parent, label="", size=wx.Size(4, 20))
        line.SetBackgroundColour(ThemeManager.ACCENT_COLOR)
        container.Add(line, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 10)
        txt = wx.StaticText(parent, label=title)
        txt.SetFont(ThemeManager.get_font(14, bold=True))
        txt.SetForegroundColour(ThemeManager.ACCENT_COLOR)
        container.Add(txt, 0, wx.ALIGN_CENTER_VERTICAL)
        return container

    def _create_card_sizer(self, parent, title):
        sizer = wx.BoxSizer(wx.VERTICAL)
        header = self._create_section_header(parent, title)
        sizer.Add(header, 0, wx.LEFT | wx.BOTTOM, 10)
        content_sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(content_sizer, 1, wx.EXPAND | wx.LEFT, 14)
        return sizer, content_sizer

    def _apply_focus_effect(self, ctrl):
        """已废弃：焦点效果现在由 ThemeManager.apply_theme 自动处理"""
        pass
