# -*- coding: utf-8 -*-
import wx
import hashlib
import hmac
import os
from ui.tabs.base_tab import BaseTab
from ui.styles import ThemeManager

class HashTab(BaseTab):

    def __init__(self, parent):
        super(HashTab, self).__init__(parent)
        self.nb = None
        self.txt_panel = None
        self.input_ctrl = None
        self.file_panel = None
        self.file_path_ctrl = None
        self.key_ctrl = None
        self.output_ctrl = None
        
        self._init_ui()
        ThemeManager.apply_theme(self)

    def _init_ui(self):
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.nb = wx.Notebook(self)
        
        # 文本模式
        self.txt_panel = wx.Panel(self.nb)
        txt_sizer = wx.BoxSizer(wx.VERTICAL)
        self.input_ctrl = wx.TextCtrl(self.txt_panel, style=wx.TE_MULTILINE, size=wx.Size(-1, 100))
        self.input_ctrl.SetFont(ThemeManager.get_font(13))
        self._apply_focus_effect(self.input_ctrl)
        txt_sizer.Add(self.input_ctrl, 1, wx.EXPAND | wx.ALL, 15)
        self.txt_panel.SetSizer(txt_sizer)
        
        # 文件模式
        self.file_panel = wx.Panel(self.nb)
        file_sizer = wx.BoxSizer(wx.HORIZONTAL)
        lbl = self._create_label(self.file_panel, "路径:")
        file_sizer.Add(lbl, 0, wx.CENTER | wx.LEFT, 15)
        # 移除固定高度，改用自然高度
        self.file_path_ctrl = wx.TextCtrl(self.file_panel)
        file_sizer.Add(self.file_path_ctrl, 1, wx.CENTER | wx.ALL, 15)
        browse_btn = wx.Button(self.file_panel, label="选择文件")
        browse_btn.Bind(wx.EVT_BUTTON, self._on_browse)
        file_sizer.Add(browse_btn, 0, wx.CENTER | wx.RIGHT, 15)
        self.file_panel.SetSizer(file_sizer)

        self.nb.AddPage(self.txt_panel, "文本模式")
        self.nb.AddPage(self.file_panel, "文件模式")
        main_sizer.Add(self.nb, 0, wx.EXPAND | wx.ALL, 15)

        # 算法区
        sh_card, sh_content = self._create_card_sizer(self, "标准哈希")
        sh_gs = wx.GridSizer(2, 6, 10, 10)
        sh_btns = [
            ("MD5-16", "md5-16"), ("MD5-32", "md5-32"), ("SHA-1", "sha1"), ("SHA-224", "sha224"),
            ("SHA-256", "sha256"), ("SHA-384", "sha384"), ("SHA-512", "sha512"), ("SHA3-224", "sha3_224"),
            ("SHA3-256", "sha3_256"), ("SHA3-384", "sha3_384"), ("SHA3-512", "sha3_512")
        ]
        for label, algo in sh_btns:
            btn = wx.Button(self, label=label)
            btn.Bind(wx.EVT_BUTTON, lambda e, a=algo: self._on_calc(a, False))
            sh_gs.Add(btn, 0, wx.EXPAND)
        sh_content.Add(sh_gs, 1, wx.EXPAND | wx.RIGHT, 20)
        main_sizer.Add(sh_card, 0, wx.EXPAND | wx.TOP, 5)

        hmac_card, hmac_content = self._create_card_sizer(self, "HMAC 加密哈希")
        key_sizer = wx.BoxSizer(wx.HORIZONTAL)
        klbl = self._create_label(self, title="密钥 (KEY):")
        key_sizer.Add(klbl, 0, wx.CENTER | wx.RIGHT, 10)
        # 移除固定高度
        self.key_ctrl = wx.TextCtrl(self)
        key_sizer.Add(self.key_ctrl, 1, wx.CENTER | wx.RIGHT, 20)
        hmac_content.Add(key_sizer, 0, wx.EXPAND | wx.BOTTOM, 15)
        
        hmac_gs = wx.GridSizer(1, 6, 10, 10)
        hmac_btns = [
            ("HmacMD5", "md5"), ("HmacSHA1", "sha1"), ("HmacSHA256", "sha256"),
            ("HmacSHA512", "sha512"), ("HmacSHA3-256", "sha3_256"), ("HmacRIPEMD160", "ripemd160")
        ]
        for label, algo in hmac_btns:
            btn = wx.Button(self, label=label)
            btn.Bind(wx.EVT_BUTTON, lambda e, a=algo: self._on_calc(a, True))
            hmac_gs.Add(btn, 0, wx.EXPAND)
        hmac_content.Add(hmac_gs, 1, wx.EXPAND | wx.RIGHT, 20)
        main_sizer.Add(hmac_card, 0, wx.EXPAND | wx.TOP, 25)

        # 结果区
        res_card, res_content = self._create_card_sizer(self, "计算结果")
        self.output_ctrl = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.output_ctrl.SetFont(ThemeManager.get_mono_font(14))
        self._apply_focus_effect(self.output_ctrl)
        res_content.Add(self.output_ctrl, 1, wx.EXPAND | wx.RIGHT, 20)
        
        ops_sizer = wx.BoxSizer(wx.HORIZONTAL)
        for label, handler in [("复制结果", self._on_copy), ("转换大小写", self._on_toggle), ("清空全部", self._on_clear)]:
            btn = wx.Button(self, label=label, size=wx.Size(110, 36))
            btn.Bind(wx.EVT_BUTTON, handler)
            ops_sizer.Add(btn, 0, wx.RIGHT, 15)
        res_content.Add(ops_sizer, 0, wx.TOP | wx.BOTTOM, 15)
        main_sizer.Add(res_card, 1, wx.EXPAND | wx.TOP, 25)

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

    def _on_toggle(self, e):
        val = self.output_ctrl.GetValue()
        self.output_ctrl.SetValue(val.lower() if val.isupper() else val.upper())

    def _on_clear(self, e):
        self.input_ctrl.Clear()
        self.file_path_ctrl.Clear()
        self.key_ctrl.Clear()
        self.output_ctrl.Clear()

    def _on_calc(self, algo, is_hmac):
        mode = self.nb.GetSelection()
        key = self.key_ctrl.GetValue().encode()
        if mode == 0:
            data = self.input_ctrl.GetValue().strip().encode("utf-8")
            if not data: return
            self._safe_exec(lambda: self._calc_hash(data, algo, is_hmac, key), self.output_ctrl)
        else:
            path = self.file_path_ctrl.GetValue().strip()
            if not os.path.isfile(path):
                wx.MessageBox("文件路径无效", "错误")
                return
            self._safe_exec(lambda: self._calc_file_hash(path, algo, is_hmac, key), self.output_ctrl)

    def _calc_hash(self, data, algo, is_hmac, key):
        actual_algo = "md5" if algo.startswith("md5") else algo
        h = hmac.new(key, digestmod=actual_algo) if is_hmac else hashlib.new(actual_algo)
        h.update(data)
        res = h.hexdigest()
        return res[8:24] if algo == "md5-16" else res

    def _calc_file_hash(self, path, algo, is_hmac, key):
        actual_algo = "md5" if algo.startswith("md5") else algo
        h = hmac.new(key, digestmod=actual_algo) if is_hmac else hashlib.new(actual_algo)
        with open(path, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        res = h.hexdigest()
        return res[8:24] if algo == "md5-16" else res
