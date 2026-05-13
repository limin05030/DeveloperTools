# -*- coding: utf-8 -*-
import wx

class classproperty(object):
    def __init__(self, f):
        self.f = f
    def __get__(self, obj, owner):
        return self.f(owner)

class ThemeManager:
    """现代主题引擎 - 支持明亮和黑暗模式自动切换"""

    DARK_COLORS = {
        'BG_WINDOW': "#121212",
        'BG_CARD': "#1E1E1E",
        'BG_INPUT': "#2D2D2D",
        'BG_FOCUS': "#353535",
        'TEXT_PRIMARY': "#FFFFFF",
        'TEXT_SECONDARY': "#8E8E93",
        'ACCENT_COLOR': "#0A84FF",
        'SUCCESS_COLOR': "#32D74B",
        'BORDER_COLOR': "#333333"
    }

    LIGHT_COLORS = {
        'BG_WINDOW': "#F2F2F7",
        'BG_CARD': "#FFFFFF",
        'BG_INPUT': "#E0E0E0",
        'BG_FOCUS': "#FFFFFF",
        'TEXT_PRIMARY': "#000000",
        'TEXT_SECONDARY': "#3C3C43",
        'ACCENT_COLOR': "#007AFF",
        'SUCCESS_COLOR': "#34C759",
        'BORDER_COLOR': "#C6C6C8"
    }

    @staticmethod
    def is_dark():
        try:
            return wx.SystemSettings.GetAppearance().IsDark()
        except:
            bg = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)
            return (bg.Red() + bg.Green() + bg.Blue()) / 3 < 128

    @classmethod
    def get_color(cls, name):
        is_dark = cls.is_dark()
        colors = cls.DARK_COLORS if is_dark else cls.LIGHT_COLORS
        return wx.Colour(colors.get(name, "#000000"))

    @classproperty
    def BG_WINDOW(cls): return cls.get_color('BG_WINDOW')
    @classproperty
    def BG_CARD(cls): return cls.get_color('BG_CARD')
    @classproperty
    def BG_INPUT(cls): return cls.get_color('BG_INPUT')
    @classproperty
    def BG_FOCUS(cls): return cls.get_color('BG_FOCUS')
    @classproperty
    def TEXT_PRIMARY(cls): return cls.get_color('TEXT_PRIMARY')
    @classproperty
    def TEXT_SECONDARY(cls): return cls.get_color('TEXT_SECONDARY')
    @classproperty
    def ACCENT_COLOR(cls): return cls.get_color('ACCENT_COLOR')
    @classproperty
    def SUCCESS_COLOR(cls): return cls.get_color('SUCCESS_COLOR')
    @classproperty
    def BORDER_COLOR(cls): return cls.get_color('BORDER_COLOR')

    @staticmethod
    def _on_focus_event(event):
        """极其稳健的焦点处理，使用 CallAfter 避免同步 UI 异常"""
        ctrl = event.GetEventObject()
        if not ctrl:
            event.Skip()
            return
            
        is_dark = ThemeManager.is_dark()
        theme = ThemeManager.DARK_COLORS if is_dark else ThemeManager.LIGHT_COLORS
        
        # 确定目标颜色
        color_hex = theme['BG_FOCUS'] if event.GetEventType() == wx.EVT_SET_FOCUS.typeId else theme['BG_INPUT']
        target_color = wx.Colour(color_hex)
        
        # 异步执行，确保不打断当前的焦点转换逻辑
        wx.CallAfter(ThemeManager._safe_set_bg, ctrl, target_color)
        event.Skip()

    @staticmethod
    def _safe_set_bg(ctrl, color):
        """安全设置背景色，防止控件已销毁或处于不稳定状态"""
        if ctrl and not isinstance(ctrl, (wx.TopLevelWindow, wx.Dialog)):
            try:
                ctrl.SetBackgroundColour(color)
                ctrl.Refresh()
            except:
                pass

    @staticmethod
    def apply_theme(window):
        is_dark = ThemeManager.is_dark()
        colors = ThemeManager.DARK_COLORS if is_dark else ThemeManager.LIGHT_COLORS
        
        c_bg_win = wx.Colour(colors['BG_WINDOW'])
        c_bg_input = wx.Colour(colors['BG_INPUT'])
        c_text_pri = wx.Colour(colors['TEXT_PRIMARY'])
        
        def _force_apply(win):
            if not win: return
            
            # 针对文本输入框
            if isinstance(win, wx.TextCtrl):
                if not (win.GetWindowStyleFlag() & wx.TE_MULTILINE):
                    style = win.GetWindowStyleFlag()
                    style &= ~wx.BORDER_SUNKEN
                    style &= ~wx.BORDER_THEME
                    style |= wx.BORDER_SIMPLE
                    win.SetWindowStyleFlag(style)
                
                win.SetBackgroundColour(c_bg_input)
                win.SetForegroundColour(c_text_pri)
                
                if not hasattr(win, "_theme_bound"):
                    win.Bind(wx.EVT_SET_FOCUS, ThemeManager._on_focus_event)
                    win.Bind(wx.EVT_KILL_FOCUS, ThemeManager._on_focus_event)
                    win._theme_bound = True
            
            # 针对下拉框等，跳过 BORDER_SIMPLE 以防破坏原生逻辑
            elif isinstance(win, (wx.ComboBox, wx.Choice, wx.SearchCtrl, wx.ListBox)):
                win.SetBackgroundColour(c_bg_input)
                win.SetForegroundColour(c_text_pri)
            
            elif hasattr(win, "SetOwnBackgroundColour"):
                # 跳过 Notebook 的 Own 系列设置，防止 macOS 上的 Tab 渲染 assertion 错误
                if not isinstance(win, wx.Notebook):
                    win.SetOwnBackgroundColour(c_bg_win)
                    win.SetOwnForegroundColour(c_text_pri)
                else:
                    win.SetBackgroundColour(c_bg_win)
                    win.SetForegroundColour(c_text_pri)
            else:
                try:
                    win.SetBackgroundColour(c_bg_win)
                    win.SetForegroundColour(c_text_pri)
                except:
                    pass

            if isinstance(win, (wx.StaticText, wx.CheckBox, wx.RadioButton)):
                win.SetForegroundColour(c_text_pri)
            elif isinstance(win, (wx.Button, wx.ToggleButton)):
                win.SetForegroundColour(c_text_pri)

            for child in win.GetChildren():
                _force_apply(child)
            
            if hasattr(win, "Refresh"):
                win.Refresh()

        _force_apply(window)

    @staticmethod
    def get_font(size=11, bold=False):
        face = "PingFang SC" if wx.Platform == "__WXMAC__" else "Segoe UI"
        return wx.Font(size, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, 
                      wx.FONTWEIGHT_BOLD if bold else wx.FONTWEIGHT_NORMAL, faceName=face)

    @staticmethod
    def get_mono_font(size=12):
        return wx.Font(size, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
