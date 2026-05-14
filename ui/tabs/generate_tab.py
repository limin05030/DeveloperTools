# -*- coding: utf-8 -*-
import wx
import uuid
import qrcode
from io import BytesIO
from ui.tabs.base_tab import BaseTab
from ui.styles import ThemeManager

class QRCodeDialog(wx.Dialog):
    def __init__(self, parent, qr_img, data):
        super(QRCodeDialog, self).__init__(parent, title="生成二维码", size=wx.Size(350, 420))
        self.qr_img = qr_img
        self.data = data
        self.SetBackgroundColour(wx.WHITE)
        self._init_ui()
        self.CentreOnParent()
        ThemeManager.apply_theme(self)

    def _init_ui(self):
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        # 将 PIL 图片转换为 wx.Bitmap
        temp = BytesIO()
        self.qr_img.save(temp, format="PNG")
        temp.seek(0)
        image = wx.Image(temp, wx.BITMAP_TYPE_PNG)
        image = image.Scale(300, 300, wx.IMAGE_QUALITY_HIGH)
        bitmap = wx.Bitmap(image)
        
        static_bitmap = wx.StaticBitmap(self, wx.ID_ANY, bitmap)
        vbox.Add(static_bitmap, 0, wx.ALIGN_CENTER | wx.ALL, 20)
        
        save_btn = wx.Button(self, label="保存为图片")
        save_btn.Bind(wx.EVT_BUTTON, self._on_save)
        vbox.Add(save_btn, 0, wx.ALIGN_CENTER | wx.BOTTOM, 20)
        
        self.SetSizer(vbox)

    def _on_save(self, event):
        # 使用最简化的通配符以尝试规避 macOS 上的断言错误
        with wx.FileDialog(self, "保存二维码", defaultFile="qrcode.png",
                         wildcard="PNG files (*.png)|*.png|All files (*.*)|*.*",
                         style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fd:
            if fd.ShowModal() == wx.ID_OK:
                self.qr_img.save(fd.GetPath(), "PNG")
                wx.MessageBox("保存成功", "提示")

class GenerateTab(BaseTab):
    def __init__(self, parent):
        super(GenerateTab, self).__init__(parent)
        self.qr_input = None
        self.uuid_count = None
        self.uuid_hyphen = None
        self.uuid_upper = None
        self.uuid_braces = None
        self.uuid_output = None
        self._raw_uuids = [] # 存储原始生成的 UUID 字符串
        
        self._init_ui()
        ThemeManager.apply_theme(self)

    def _init_ui(self):
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # 二维码生成
        qr_card, qr_cont = self._create_card_sizer(self, "二维码生成")
        h1 = wx.BoxSizer(wx.HORIZONTAL)
        # 单行输入
        self.qr_input = wx.TextCtrl(self, size=wx.Size(-1, 30))
        self.qr_input.SetHint("输入文字或链接生成二维码...")
        h1.Add(self.qr_input, 1, wx.CENTER | wx.RIGHT, 10)
        
        qr_btn = wx.Button(self, label="生成", size=wx.Size(100, 32))
        qr_btn.Bind(wx.EVT_BUTTON, self._on_gen_qr)
        h1.Add(qr_btn, 0, wx.CENTER)
        qr_cont.Add(h1, 0, wx.EXPAND | wx.RIGHT | wx.BOTTOM, 10)
        main_sizer.Add(qr_card, 0, wx.EXPAND | wx.ALL, 15)

        # UUID 生成
        uuid_card, uuid_cont = self._create_card_sizer(self, "批量生成 UUID")
        
        opts_sizer = wx.BoxSizer(wx.HORIZONTAL)
        opts_sizer.Add(self._create_label(self, "生成数量:"), 0, wx.CENTER | wx.RIGHT, 5)
        self.uuid_count = wx.SpinCtrl(self, value="5", min=1, max=1000, size=wx.Size(70, -1))
        opts_sizer.Add(self.uuid_count, 0, wx.CENTER | wx.RIGHT, 20)
        
        self.uuid_hyphen = wx.CheckBox(self, label="带分割线")
        self.uuid_hyphen.SetValue(True)
        self.uuid_hyphen.Bind(wx.EVT_CHECKBOX, self._on_uuid_opt_changed)
        opts_sizer.Add(self.uuid_hyphen, 0, wx.CENTER | wx.RIGHT, 15)
        
        self.uuid_upper = wx.CheckBox(self, label="字母大写")
        self.uuid_upper.SetValue(True)
        self.uuid_upper.Bind(wx.EVT_CHECKBOX, self._on_uuid_opt_changed)
        opts_sizer.Add(self.uuid_upper, 0, wx.CENTER | wx.RIGHT, 15)
        
        self.uuid_braces = wx.CheckBox(self, label="带花括号 {}")
        self.uuid_braces.SetValue(False)
        self.uuid_braces.Bind(wx.EVT_CHECKBOX, self._on_uuid_opt_changed)
        opts_sizer.Add(self.uuid_braces, 0, wx.CENTER | wx.RIGHT, 15)
        
        uuid_cont.Add(opts_sizer, 0, wx.EXPAND | wx.BOTTOM, 10)
        
        self.uuid_output = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY, size=wx.Size(-1, 200))
        self.uuid_output.SetFont(ThemeManager.get_mono_font(12))
        uuid_cont.Add(self.uuid_output, 1, wx.EXPAND | wx.RIGHT, 20)
        
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        gen_uuid_btn = wx.Button(self, label="生成", size=wx.Size(120, 36))
        gen_uuid_btn.Bind(wx.EVT_BUTTON, self._on_gen_uuid)
        btn_sizer.Add(gen_uuid_btn, 0, wx.RIGHT, 10)
        
        copy_btn = wx.Button(self, label="复制结果", size=wx.Size(120, 36))
        copy_btn.Bind(wx.EVT_BUTTON, self._on_copy_uuid)
        btn_sizer.Add(copy_btn, 0)
        uuid_cont.Add(btn_sizer, 0, wx.TOP | wx.BOTTOM, 10)
        
        main_sizer.Add(uuid_card, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 15)

        self.SetSizer(main_sizer)

    def _on_gen_qr(self, event):
        data = self.qr_input.GetValue().strip()
        if not data:
            wx.MessageBox("请输入内容", "提示")
            return
        
        try:
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            dlg = QRCodeDialog(self, img, data)
            dlg.ShowModal()
            dlg.Destroy()
        except Exception as e:
            wx.MessageBox(f"生成失败: {str(e)}", "错误")

    def _on_uuid_opt_changed(self, event):
        if self._raw_uuids:
            self._update_uuid_display()

    def _on_gen_uuid(self, event):
        count = self.uuid_count.GetValue()
        self._raw_uuids = [str(uuid.uuid4()) for _ in range(count)]
        self._update_uuid_display()

    def _update_uuid_display(self):
        hyphen = self.uuid_hyphen.IsChecked()
        upper = self.uuid_upper.IsChecked()
        braces = self.uuid_braces.IsChecked()
        
        results = []
        for u in self._raw_uuids:
            processed = u
            if not hyphen:
                processed = processed.replace("-", "")
            if upper:
                processed = processed.upper()
            if braces:
                processed = "{" + processed + "}"
            results.append(processed)
        
        self.uuid_output.SetValue("\n".join(results))

    def _on_copy_uuid(self, event):
        val = self.uuid_output.GetValue().strip()
        if val:
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(wx.TextDataObject(val))
                wx.TheClipboard.Close()
                wx.MessageBox("已复制到剪贴板", "提示")
