# -*- coding: utf-8 -*-
import wx

class ThemeManager:
    """现代深色主题引擎 - Obsidian Style"""

    # 颜色字符串定义
    BG_WINDOW = "#121212"
    BG_CARD = "#1E1E1E"
    BG_INPUT = "#2D2D2D"
    BG_FOCUS = "#353535"

    TEXT_PRIMARY = "#FFFFFF"
    TEXT_SECONDARY = "#8E8E93"

    ACCENT_COLOR = "#0A84FF"
    SUCCESS_COLOR = "#32D74B"
    BORDER_COLOR = "#333333"

    @staticmethod
    def apply_theme(window):
        """递归应用现代主题"""
        if isinstance(window, (wx.TextCtrl, wx.ComboBox, wx.Choice)):
            window.SetBackgroundColour(wx.Colour(ThemeManager.BG_INPUT))
            window.SetForegroundColour(wx.Colour(ThemeManager.TEXT_PRIMARY))
        elif isinstance(window, wx.StaticText):
            window.SetForegroundColour(wx.Colour(ThemeManager.TEXT_SECONDARY))
        elif isinstance(window, (wx.Button, wx.ToggleButton)):
            window.SetForegroundColour(wx.Colour(ThemeManager.TEXT_PRIMARY))
        elif isinstance(window, wx.Notebook):
            window.SetBackgroundColour(wx.Colour(ThemeManager.BG_WINDOW))
        else:
            window.SetBackgroundColour(wx.Colour(ThemeManager.BG_WINDOW))
            window.SetForegroundColour(wx.Colour(ThemeManager.TEXT_PRIMARY))

        for child in window.GetChildren():
            ThemeManager.apply_theme(child)

    @staticmethod
    def get_font(size=11, bold=False):
        face = "PingFang SC" if wx.Platform == "__WXMAC__" else "Segoe UI"
        return wx.Font(size, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                      wx.FONTWEIGHT_BOLD if bold else wx.FONTWEIGHT_NORMAL, faceName=face)

    @staticmethod
    def get_mono_font(size=12):
        return wx.Font(size, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
