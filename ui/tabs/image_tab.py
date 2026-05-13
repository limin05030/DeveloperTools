# -*- coding: utf-8 -*-
import wx
import base64
import os
from PIL import Image
from ui.tabs.base_tab import BaseTab
from ui.styles import ThemeManager

class ImageTab(BaseTab):

    def __init__(self, parent):
        super(ImageTab, self).__init__(parent)
        self.orig_ratio = 1.0
        self._is_updating = False
        self.nb = None
        self.conv_src_ctrl = None
        self.conv_fmt_cb = None
        self.comp_src_ctrl = None
        self.comp_quality_sld = None
        self.size_src_ctrl = None
        self.size_mode_rb = []
        self.width_ctrl = None
        self.height_ctrl = None
        self.keep_ratio_chk = None
        self.b64_img_ctrl = None
        self.b64_txt_ctrl = None
        
        self._init_ui()
        ThemeManager.apply_theme(self)

    def _init_ui(self):
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.nb = wx.Notebook(self)
        self.nb.AddPage(self._build_conv_panel(), "格式转换")
        self.nb.AddPage(self._build_comp_panel(), "图片压缩")
        self.nb.AddPage(self._build_size_panel(), "尺寸调整")
        self.nb.AddPage(self._build_b64_panel(), "Base64 工具")
        main_sizer.Add(self.nb, 1, wx.EXPAND | wx.ALL, 5)
        self.SetSizer(main_sizer)

    def _on_browse(self, ctrl):
        with wx.FileDialog(self, "打开文件") as fd:
            if fd.ShowModal() == wx.ID_OK: ctrl.SetValue(fd.GetPath())

    def _build_conv_panel(self):
        panel = wx.Panel(self.nb)
        panel.SetBackgroundColour(wx.Colour(ThemeManager.BG_WINDOW))
        sizer = wx.BoxSizer(wx.VERTICAL)
        card1, cont1 = self._create_card_sizer(panel, "源图片")
        h1 = wx.BoxSizer(wx.HORIZONTAL)
        # 移除固定高度
        self.conv_src_ctrl = wx.TextCtrl(panel)
        h1.Add(self.conv_src_ctrl, 1, wx.CENTER | wx.RIGHT, 10)
        btn1 = wx.Button(panel, label="浏览", size=wx.Size(80, 36))
        btn1.Bind(wx.EVT_BUTTON, lambda e: self._on_browse(self.conv_src_ctrl))
        h1.Add(btn1, 0, wx.CENTER)
        cont1.Add(h1, 0, wx.EXPAND | wx.RIGHT | wx.BOTTOM, 10)
        sizer.Add(card1, 0, wx.EXPAND | wx.ALL, 15)
        
        card2, cont2 = self._create_card_sizer(panel, "目标格式")
        h2 = wx.BoxSizer(wx.HORIZONTAL)
        h2.Add(self._create_label(panel, "格式:"), 0, wx.CENTER | wx.RIGHT, 10)
        self.conv_fmt_cb = wx.ComboBox(panel, value="PNG", choices=["PNG", "JPEG", "WEBP", "BMP", "ICO", "TIFF", "GIF"], style=wx.CB_READONLY)
        h2.Add(self.conv_fmt_cb, 0, wx.CENTER)
        cont2.Add(h2, 0, wx.EXPAND)
        sizer.Add(card2, 0, wx.EXPAND | wx.ALL, 15)
        
        go_btn = wx.Button(panel, label="开始转换", size=wx.Size(150, 45))
        go_btn.Bind(wx.EVT_BUTTON, self._on_convert)
        sizer.Add(go_btn, 0, wx.ALIGN_CENTER | wx.TOP, 10)
        panel.SetSizer(sizer)
        return panel

    def _build_comp_panel(self):
        panel = wx.Panel(self.nb)
        panel.SetBackgroundColour(wx.Colour(ThemeManager.BG_WINDOW))
        sizer = wx.BoxSizer(wx.VERTICAL)
        card1, cont1 = self._create_card_sizer(panel, "源图片 (仅限 JPEG/WEBP)")
        h1 = wx.BoxSizer(wx.HORIZONTAL)
        self.comp_src_ctrl = wx.TextCtrl(panel)
        h1.Add(self.comp_src_ctrl, 1, wx.CENTER | wx.RIGHT, 10)
        btn1 = wx.Button(panel, label="浏览", size=wx.Size(80, 36))
        btn1.Bind(wx.EVT_BUTTON, lambda e: self._on_browse(self.comp_src_ctrl))
        h1.Add(btn1, 0, wx.CENTER)
        cont1.Add(h1, 0, wx.EXPAND | wx.RIGHT | wx.BOTTOM, 10)
        sizer.Add(card1, 0, wx.EXPAND | wx.ALL, 15)
        
        card2, cont2 = self._create_card_sizer(panel, "压缩设置")
        h2 = wx.BoxSizer(wx.HORIZONTAL)
        h2.Add(self._create_label(panel, "质量 (1-100):"), 0, wx.CENTER | wx.RIGHT, 15)
        self.comp_quality_sld = wx.Slider(panel, value=75, minValue=1, maxValue=100, style=wx.SL_HORIZONTAL | wx.SL_LABELS)
        h2.Add(self.comp_quality_sld, 1, wx.CENTER)
        cont2.Add(h2, 0, wx.EXPAND)
        sizer.Add(card2, 0, wx.EXPAND | wx.ALL, 15)
        
        go_btn = wx.Button(panel, label="压缩并保存", size=wx.Size(150, 45))
        go_btn.Bind(wx.EVT_BUTTON, self._on_compress)
        sizer.Add(go_btn, 0, wx.ALIGN_CENTER | wx.TOP, 10)
        panel.SetSizer(sizer)
        return panel

    def _build_size_panel(self):
        panel = wx.Panel(self.nb)
        panel.SetBackgroundColour(wx.Colour(ThemeManager.BG_WINDOW))
        sizer = wx.BoxSizer(wx.VERTICAL)
        card1, cont1 = self._create_card_sizer(panel, "源图片")
        h1 = wx.BoxSizer(wx.HORIZONTAL)
        self.size_src_ctrl = wx.TextCtrl(panel)
        h1.Add(self.size_src_ctrl, 1, wx.CENTER | wx.RIGHT, 10)
        btn1 = wx.Button(panel, label="浏览", size=wx.Size(80, 36))
        btn1.Bind(wx.EVT_BUTTON, self._on_browse_size)
        h1.Add(btn1, 0, wx.CENTER)
        cont1.Add(h1, 0, wx.EXPAND | wx.RIGHT | wx.BOTTOM, 10)
        sizer.Add(card1, 0, wx.EXPAND | wx.ALL, 15)
        
        card2, cont2 = self._create_card_sizer(panel, "尺寸与方式")
        h_modes = wx.BoxSizer(wx.HORIZONTAL)
        modes = [("缩放", "resize"), ("中心裁剪", "center"), ("左上", "tl"), ("右上", "tr"), ("左下", "bl"), ("右下", "br")]
        self.size_mode_rb = []
        for i, (label, val) in enumerate(modes):
            rb = wx.RadioButton(panel, label=label, style=wx.RB_GROUP if val=="resize" else 0)
            rb.name = val
            if i == 0:
                rb.SetValue(True)
            h_modes.Add(rb, 0, wx.RIGHT | wx.CENTER, 15)
            self.size_mode_rb.append(rb)
        cont2.Add(h_modes, 0, wx.BOTTOM, 15)
        
        h_size = wx.BoxSizer(wx.HORIZONTAL)
        h_size.Add(self._create_label(panel, "宽度(px):"), 0, wx.CENTER | wx.RIGHT, 10)
        self.width_ctrl = wx.TextCtrl(panel, size=wx.Size(80, -1))
        self.width_ctrl.Bind(wx.EVT_TEXT, lambda e: self._sync_ratio("w"))
        h_size.Add(self.width_ctrl, 0, wx.CENTER)
        h_size.Add(self._create_label(panel, "高度(px):"), 0, wx.CENTER | wx.LEFT | wx.RIGHT, 10)
        self.height_ctrl = wx.TextCtrl(panel, size=wx.Size(80, -1))
        self.height_ctrl.Bind(wx.EVT_TEXT, lambda e: self._sync_ratio("h"))
        h_size.Add(self.height_ctrl, 0, wx.CENTER)
        self.keep_ratio_chk = wx.CheckBox(panel, label="保持宽高比")
        self.keep_ratio_chk.SetValue(True)
        h_size.Add(self.keep_ratio_chk, 0, wx.CENTER | wx.LEFT, 25)
        cont2.Add(h_size, 0, wx.EXPAND)
        sizer.Add(card2, 0, wx.EXPAND | wx.ALL, 15)
        
        go_btn = wx.Button(panel, label="处理并保存", size=wx.Size(150, 45))
        go_btn.Bind(wx.EVT_BUTTON, self._on_resize_crop)
        sizer.Add(go_btn, 0, wx.ALIGN_CENTER | wx.TOP, 10)
        panel.SetSizer(sizer)
        return panel

    def _build_b64_panel(self):
        panel = wx.Panel(self.nb)
        panel.SetBackgroundColour(wx.Colour(ThemeManager.BG_WINDOW))
        sizer = wx.BoxSizer(wx.VERTICAL)
        for label, btn_lbl, handler, ctrl_attr in [
            ("图片 转 Base64", "转换", self._on_img_to_b64, "b64_img_ctrl"),
            ("Base64 转 图片", "还原", self._on_b64_to_img, "b64_txt_ctrl")
        ]:
            card, cont = self._create_card_sizer(panel, label)
            h = wx.BoxSizer(wx.HORIZONTAL)
            ctrl = wx.TextCtrl(panel)
            setattr(self, ctrl_attr, ctrl)
            h.Add(ctrl, 1, wx.CENTER | wx.RIGHT, 10)
            btn_br = wx.Button(panel, label="浏览", size=wx.Size(80, 36))
            btn_br.Bind(wx.EVT_BUTTON, lambda e, c=ctrl: self._on_browse(c))
            h.Add(btn_br, 0, wx.CENTER | wx.RIGHT, 10)
            btn_go = wx.Button(panel, label=btn_lbl, size=wx.Size(80, 36))
            btn_go.Bind(wx.EVT_BUTTON, handler)
            h.Add(btn_go, 0, wx.CENTER)
            cont.Add(h, 0, wx.EXPAND | wx.RIGHT | wx.BOTTOM, 10)
            sizer.Add(card, 0, wx.EXPAND | wx.ALL, 15)
        panel.SetSizer(sizer)
        return panel

    def _on_browse_size(self, e):
        with wx.FileDialog(self, "打开图片") as fd:
            if fd.ShowModal() == wx.ID_OK:
                path = fd.GetPath()
                self.size_src_ctrl.SetValue(path)
                with Image.open(path) as img:
                    self.orig_ratio = img.width / img.height if img.height != 0 else 1.0
                    self._is_updating = True
                    self.width_ctrl.SetValue(str(img.width))
                    self.height_ctrl.SetValue(str(img.height))
                    self._is_updating = False

    def _sync_ratio(self, origin):
        if not self.keep_ratio_chk.IsChecked() or self._is_updating or not self.size_src_ctrl.GetValue():
            return
        self._is_updating = True
        try:
            if origin == "w":
                val = self.width_ctrl.GetValue()
                if val.isdigit():
                    self.height_ctrl.SetValue(str(int(int(val) / self.orig_ratio)))
            else:
                val = self.height_ctrl.GetValue()
                if val.isdigit():
                    self.width_ctrl.SetValue(str(int(int(val) * self.orig_ratio)))
        except:
            pass
        self._is_updating = False

    def _on_convert(self, e):
        src = self.conv_src_ctrl.GetValue()
        if not src or not os.path.exists(src): return
        fmt = self.conv_fmt_cb.GetValue()
        ext = fmt.lower()
        with wx.FileDialog(self, "保存图片", defaultFile="converted."+ext, style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fd:
            if fd.ShowModal() == wx.ID_OK:
                save_path = fd.GetPath()
                with Image.open(src) as img:
                    if fmt == "JPEG" and img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                    img.save(save_path, fmt)
                wx.MessageBox("转换成功", "完成")

    def _on_compress(self, e):
        src = self.comp_src_ctrl.GetValue()
        if not src: return
        ext = str(os.path.splitext(src)[1].lower())
        with wx.FileDialog(self, "保存压缩后的图片", defaultFile="compressed"+ext, style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fd:
            if fd.ShowModal() == wx.ID_OK:
                save_path = fd.GetPath()
                with Image.open(src) as img:
                    fmt = "JPEG" if "jpg" in ext or "jpeg" in ext else "WEBP"
                    if fmt == "JPEG" and img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                    img.save(save_path, format=fmt, quality=self.comp_quality_sld.GetValue(), optimize=True)
                wx.MessageBox("压缩成功", "完成")

    def _on_resize_crop(self, e):
        src = self.size_src_ctrl.GetValue()
        if not src: return
        try:
            tw, th = int(self.width_ctrl.GetValue()), int(self.height_ctrl.GetValue())
        except:
            wx.MessageBox("尺寸必须是整数", "错误")
            return
        mode = "resize"
        for rb in self.size_mode_rb:
            if rb.GetValue():
                mode = rb.name
                break
        ext = str(os.path.splitext(src)[1])
        with wx.FileDialog(self, "保存处理后的图片", defaultFile="processed"+ext, style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fd:
            if fd.ShowModal() == wx.ID_OK:
                save_path = fd.GetPath()
                with Image.open(src) as img:
                    w, h = img.size
                    if mode == "resize":
                        res = img.resize((tw, th), Image.Resampling.LANCZOS)
                    else:
                        if tw > w or th > h:
                            wx.MessageBox(f"裁剪尺寸 ({tw}x{th}) 不能大于原图尺寸 ({w}x{h})", "错误")
                            return
                        if mode == "center":
                            left, top = (w-tw)//2, (h-th)//2
                        elif mode == "tl":
                            left, top = 0, 0
                        elif mode == "tr":
                            left, top = w-tw, 0
                        elif mode == "bl":
                            left, top = 0, h-th
                        elif mode == "br":
                            left, top = w-tw, h-th
                        res = img.crop((left, top, left+tw, top+th))
                    res.save(save_path)
                wx.MessageBox("处理成功", "完成")

    def _on_img_to_b64(self, e):
        src = self.b64_img_ctrl.GetValue()
        if not src: return
        with open(src, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
            data = f"data:image/{os.path.splitext(src)[1][1:]};base64,{b64}"
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(wx.TextDataObject(data))
                wx.TheClipboard.Close()
                wx.MessageBox("已复制到剪贴板", "成功")

    def _on_b64_to_img(self, e):
        path = self.b64_txt_ctrl.GetValue()
        if not path: return
        try:
            with open(path, "r") as f:
                content = f.read().strip()
            if "," in content:
                content = content.split(",")[1]
            img_data = base64.b64decode(content)
            with wx.FileDialog(self, "Save Restored Image", style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fd:
                if fd.ShowModal() == wx.ID_OK:
                    with open(fd.GetPath(), "wb") as f:
                        f.write(img_data)
                    wx.MessageBox("还原成功", "完成")
        except Exception as ex:
            wx.MessageBox(f"失败: {str(ex)}", "错误")
