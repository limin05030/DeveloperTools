# -*- coding: utf-8 -*-
import wx
import json
import re
import os
from bs4 import BeautifulSoup
from ui.tabs.base_tab import BaseTab
from ui.styles import ThemeManager

class FormatTab(BaseTab):
    def __init__(self, parent):
        super(FormatTab, self).__init__(parent)
        self.nb = None
        self.txt_panel = None
        self.input_ctrl = None
        self.file_panel = None
        self.file_path_ctrl = None
        self.output_ctrl = None
        
        self._init_ui()
        ThemeManager.apply_theme(self)

    def _init_ui(self):
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.nb = wx.Notebook(self)
        
        # 文本模式
        self.txt_panel = wx.Panel(self.nb)
        txt_sizer = wx.BoxSizer(wx.VERTICAL)
        self.input_ctrl = wx.TextCtrl(self.txt_panel, style=wx.TE_MULTILINE, size=wx.Size(-1, 150))
        self.input_ctrl.SetFont(ThemeManager.get_font(12))
        txt_sizer.Add(self.input_ctrl, 1, wx.EXPAND | wx.ALL, 15)
        clear_in_btn = wx.Button(self.txt_panel, label="清空输入")
        clear_in_btn.Bind(wx.EVT_BUTTON, lambda e: self.input_ctrl.Clear())
        txt_sizer.Add(clear_in_btn, 0, wx.ALIGN_RIGHT | wx.RIGHT | wx.BOTTOM, 15)
        self.txt_panel.SetSizer(txt_sizer)
        
        # 文件模式
        self.file_panel = wx.Panel(self.nb)
        file_sizer = wx.BoxSizer(wx.HORIZONTAL)
        lbl = self._create_label(self.file_panel, "路径:")
        file_sizer.Add(lbl, 0, wx.CENTER | wx.LEFT, 15)
        # 移除固定高度
        self.file_path_ctrl = wx.TextCtrl(self.file_panel)
        file_sizer.Add(self.file_path_ctrl, 1, wx.CENTER | wx.ALL, 15)
        browse_btn = wx.Button(self.file_panel, label="选择文件")
        browse_btn.Bind(wx.EVT_BUTTON, self._on_browse)
        file_sizer.Add(browse_btn, 0, wx.CENTER | wx.RIGHT, 15)
        self.file_panel.SetSizer(file_sizer)

        self.nb.AddPage(self.txt_panel, "文本模式")
        self.nb.AddPage(self.file_panel, "文件模式")
        main_sizer.Add(self.nb, 0, wx.EXPAND | wx.ALL, 15)

        # 按钮区
        btn_sizer = wx.GridSizer(1, 6, 10, 10)
        btns = [
            ("JSON 格式化", self._json_format), ("JSON 压缩", self._json_compress),
            ("HTML/XML 美化", self._html_xml_format), ("JS/TS 格式化", self._js_ts_format)
        ]
        for label, handler in btns:
            btn = wx.Button(self, label=label)
            btn.Bind(wx.EVT_BUTTON, handler)
            btn_sizer.Add(btn, 0, wx.EXPAND)
        main_sizer.Add(btn_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 25)

        # 结果区
        res_card, res_content = self._create_card_sizer(self, "美化结果")
        self.output_ctrl = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_DONTWRAP | wx.TE_READONLY)
        self.output_ctrl.SetFont(ThemeManager.get_mono_font(12))
        res_content.Add(self.output_ctrl, 1, wx.EXPAND | wx.RIGHT, 20)
        
        copy_btn = wx.Button(self, label="复制到剪贴板", size=wx.Size(120, 40))
        copy_btn.Bind(wx.EVT_BUTTON, self._on_copy)
        res_content.Add(copy_btn, 0, wx.ALIGN_LEFT | wx.TOP | wx.BOTTOM, 15)
        main_sizer.Add(res_card, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)

        self.SetSizer(main_sizer)

    def _on_browse(self, e):
        with wx.FileDialog(self, "选择文件", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fd:
            if fd.ShowModal() == wx.ID_OK:
                self.file_path_ctrl.SetValue(fd.GetPath())

    def _on_copy(self, e):
        val = self.output_ctrl.GetValue().strip()
        if val:
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(wx.TextDataObject(val))
                wx.TheClipboard.Close()

    def _get_input(self) -> str | None:
        mode = self.nb.GetSelection()
        if mode == 0:
            return self.input_ctrl.GetValue().strip()
        else:
            path = self.file_path_ctrl.GetValue().strip()
            if not path or not os.path.isfile(path):
                return None
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return f.read().strip()
            except:
                return None

    def _json_format(self, e):
        _data = self._get_input()
        if _data:
            self._safe_exec(lambda: json.dumps(json.loads(_data), indent=4, ensure_ascii=False), self.output_ctrl)

    def _json_compress(self, e):
        _data = self._get_input()
        if _data:
            self._safe_exec(lambda: json.dumps(json.loads(_data), separators=(',', ':'), ensure_ascii=False), self.output_ctrl)

    def _html_xml_format(self, e):
        _data = self._get_input()
        if _data:
            def _fmt():
                is_xml = _data.startswith("<?xml") or ("<" in _data and not _data.lower().startswith("<!doctype html"))
                soup = BeautifulSoup(_data, "xml" if is_xml else "html.parser")
                return soup.prettify()
            self._safe_exec(_fmt, self.output_ctrl)

    def _js_ts_format(self, e):
        code = self._get_input()
        if not code:
            return

        def _fmt():
            c = code.replace('{', ' {\n').replace('}', '\n}\n').replace(';', ';\n')
            c = re.sub(r'\n\s*\n', '\n', c)
            lines = c.split('\n')
            indent, formatted = 0, []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if line.startswith('}'):
                    indent -= 1
                formatted.append("    " * max(0, indent) + line)
                if line.endswith('{'):
                    indent += 1
            return '\n'.join(formatted)
        self._safe_exec(_fmt, self.output_ctrl)
