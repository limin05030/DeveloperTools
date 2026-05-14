# -*- coding: utf-8 -*-
import wx
import base64
import urllib.parse
import html
import zhconv
from ui.tabs.base_tab import BaseTab
from ui.styles import ThemeManager

class EncodeTab(BaseTab):
    def __init__(self, parent):
        super(EncodeTab, self).__init__(parent)
        # 成员变量提前定义
        self.input_ctrl = None
        self.output_ctrl = None
        
        self._init_ui()
        ThemeManager.apply_theme(self)

    def _init_ui(self):
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # 输入区
        in_card, in_content = self._create_card_sizer(self, "输入内容")
        self.input_ctrl = wx.TextCtrl(self, style=wx.TE_MULTILINE, size=wx.Size(-1, 80))
        self.input_ctrl.SetFont(ThemeManager.get_font(12))
        in_content.Add(self.input_ctrl, 1, wx.EXPAND | wx.RIGHT, 20)
        main_sizer.Add(in_card, 0, wx.EXPAND | wx.ALL, 15)

        # 编码组
        enc_card, enc_content = self._create_card_sizer(self, "编码与解码")
        enc_gs = wx.GridSizer(2, 6, 10, 10)
        enc_btns = [
            ("Base64 编码", self._b64_encode), ("Base64 解码", self._b64_decode),
            ("URL 编码", self._url_encode), ("URL 解码", self._url_decode),
            ("Unicode 编码", self._unicode_encode), ("Unicode 解码", self._unicode_decode),
            ("HTML 转义", self._html_escape), ("HTML 反转义", self._html_unescape)
        ]
        for label, handler in enc_btns:
            btn = wx.Button(self, label=label)
            btn.Bind(wx.EVT_BUTTON, handler)
            enc_gs.Add(btn, 0, wx.EXPAND)
        enc_content.Add(enc_gs, 1, wx.EXPAND | wx.RIGHT, 20)
        main_sizer.Add(enc_card, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 15)

        # 文本组
        txt_card, txt_content = self._create_card_sizer(self, "文本转换")
        txt_gs = wx.GridSizer(1, 6, 10, 10)
        txt_btns = [
            ("转大写", self._to_upper), ("转小写", self._to_lower), ("大小写互转", self._swap_case),
            ("转繁体", self._to_traditional), ("转简体", self._to_simplified)
        ]
        for label, handler in txt_btns:
            btn = wx.Button(self, label=label, size=wx.Size(-1, 36))
            btn.Bind(wx.EVT_BUTTON, handler)
            txt_gs.Add(btn, 0, wx.EXPAND)
        txt_content.Add(txt_gs, 1, wx.EXPAND | wx.RIGHT, 20)
        main_sizer.Add(txt_card, 0, wx.EXPAND | wx.ALL, 15)

        # 结果区
        res_card, res_content = self._create_card_sizer(self, "转换结果")
        self.output_ctrl = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.output_ctrl.SetFont(ThemeManager.get_mono_font(12))
        res_content.Add(self.output_ctrl, 1, wx.EXPAND | wx.RIGHT, 20)
        
        copy_btn = wx.Button(self, label="复制结果", size=wx.Size(120, 40))
        copy_btn.Bind(wx.EVT_BUTTON, self._on_copy)
        res_content.Add(copy_btn, 0, wx.ALIGN_LEFT | wx.TOP | wx.BOTTOM, 15)
        main_sizer.Add(res_card, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 15)

        self.SetSizer(main_sizer)

    def _get_val(self): return self.input_ctrl.GetValue().strip()

    def _on_copy(self, event):
        val = self.output_ctrl.GetValue().strip()
        if val:
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(wx.TextDataObject(val))
                wx.TheClipboard.Close()

    def _to_upper(self, e): self._safe_exec(lambda: self._get_val().upper(), self.output_ctrl)
    def _to_lower(self, e): self._safe_exec(lambda: self._get_val().lower(), self.output_ctrl)
    def _swap_case(self, e): self._safe_exec(lambda: self._get_val().swapcase(), self.output_ctrl)
    def _to_traditional(self, e): self._safe_exec(lambda: zhconv.convert(self._get_val(), 'zh-hant'), self.output_ctrl)
    def _to_simplified(self, e): self._safe_exec(lambda: zhconv.convert(self._get_val(), 'zh-hans'), self.output_ctrl)
    
    def _b64_encode(self, e): self._safe_exec(lambda: base64.b64encode(self._get_val().encode()).decode(), self.output_ctrl)
    def _b64_decode(self, e): self._safe_exec(lambda: base64.b64decode(self._get_val().encode()).decode(), self.output_ctrl)
    def _url_encode(self, e): self._safe_exec(lambda: urllib.parse.quote(self._get_val()), self.output_ctrl)
    def _url_decode(self, e): self._safe_exec(lambda: urllib.parse.unquote(self._get_val()), self.output_ctrl)
    def _unicode_encode(self, e): self._safe_exec(lambda: self._get_val().encode('unicode_escape').decode('ascii'), self.output_ctrl)
    def _unicode_decode(self, e): self._safe_exec(lambda: self._get_val().encode().decode('unicode_escape'), self.output_ctrl)
    def _html_escape(self, e): self._safe_exec(lambda: html.escape(self._get_val()), self.output_ctrl)
    def _html_unescape(self, e): self._safe_exec(lambda: html.unescape(self._get_val()), self.output_ctrl)
