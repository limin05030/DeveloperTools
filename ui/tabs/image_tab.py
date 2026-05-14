# -*- coding: utf-8 -*-
import wx
import base64
import os
from PIL import Image, ImageDraw
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
        
        # 圆角功能变量
        self.radius_src_ctrl = None
        self.radius_all_ctrl = None
        self.radius_tl_ctrl = None
        self.radius_tr_ctrl = None
        self.radius_bl_ctrl = None
        self.radius_br_ctrl = None
        
        self._init_ui()
        ThemeManager.apply_theme(self)

    def _init_ui(self):
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.nb = wx.Notebook(self)
        self.nb.AddPage(self._build_conv_panel(), "格式转换")
        self.nb.AddPage(self._build_comp_panel(), "图片压缩")
        self.nb.AddPage(self._build_size_panel(), "尺寸调整")
        self.nb.AddPage(self._build_radius_panel(), "圆角处理")
        self.nb.AddPage(self._build_b64_panel(), "图片转Base64")
        main_sizer.Add(self.nb, 1, wx.EXPAND | wx.ALL, 5)
        self.SetSizer(main_sizer)

    def _on_browse(self, ctrl):
        with wx.FileDialog(self.GetTopLevelParent(), "打开文件") as fd:
            fd.CenterOnParent()
            if fd.ShowModal() == wx.ID_OK:
                ctrl.SetValue(fd.GetPath())

    def _build_conv_panel(self):
        panel = wx.Panel(self.nb)
        panel.SetBackgroundColour(ThemeManager.BG_WINDOW)
        sizer = wx.BoxSizer(wx.VERTICAL)
        card1, cont1 = self._create_card_sizer(panel, "源图片")
        h1 = wx.BoxSizer(wx.HORIZONTAL)
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
        panel.SetBackgroundColour(ThemeManager.BG_WINDOW)
        sizer = wx.BoxSizer(wx.VERTICAL)
        card1, cont1 = self._create_card_sizer(panel, "源图片 (支持 JPEG/WEBP/PNG)")
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
        h2.Add(self._create_label(panel, "质量/压缩率 (1-100):"), 0, wx.CENTER | wx.RIGHT, 15)
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
        panel.SetBackgroundColour(ThemeManager.BG_WINDOW)
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

    def _build_radius_panel(self):
        panel = wx.Panel(self.nb)
        panel.SetBackgroundColour(ThemeManager.BG_WINDOW)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        card1, cont1 = self._create_card_sizer(panel, "源图片")
        h1 = wx.BoxSizer(wx.HORIZONTAL)
        self.radius_src_ctrl = wx.TextCtrl(panel)
        h1.Add(self.radius_src_ctrl, 1, wx.CENTER | wx.RIGHT, 10)
        btn1 = wx.Button(panel, label="浏览", size=wx.Size(80, 36))
        btn1.Bind(wx.EVT_BUTTON, lambda e: self._on_browse(self.radius_src_ctrl))
        h1.Add(btn1, 0, wx.CENTER)
        cont1.Add(h1, 0, wx.EXPAND | wx.RIGHT | wx.BOTTOM, 10)
        sizer.Add(card1, 0, wx.EXPAND | wx.ALL, 15)

        card2, cont2 = self._create_card_sizer(panel, "圆角设置 (像素)")
        gs = wx.FlexGridSizer(0, 4, 10, 15)
        
        gs.Add(self._create_label(panel, "全部四个角:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.radius_all_ctrl = wx.TextCtrl(panel, value="0", size=wx.Size(60, -1))
        self.radius_all_ctrl.Bind(wx.EVT_TEXT, self._on_radius_all_changed)
        gs.Add(self.radius_all_ctrl, 0, wx.ALIGN_CENTER_VERTICAL)
        gs.AddSpacer(1)
        gs.AddSpacer(1)

        gs.Add(self._create_label(panel, "左上角:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.radius_tl_ctrl = wx.TextCtrl(panel, value="0", size=wx.Size(60, -1))
        gs.Add(self.radius_tl_ctrl, 0, wx.ALIGN_CENTER_VERTICAL)
        
        gs.Add(self._create_label(panel, "右上角:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.radius_tr_ctrl = wx.TextCtrl(panel, value="0", size=wx.Size(60, -1))
        gs.Add(self.radius_tr_ctrl, 0, wx.ALIGN_CENTER_VERTICAL)
        
        gs.Add(self._create_label(panel, "左下角:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.radius_bl_ctrl = wx.TextCtrl(panel, value="0", size=wx.Size(60, -1))
        gs.Add(self.radius_bl_ctrl, 0, wx.ALIGN_CENTER_VERTICAL)
        
        gs.Add(self._create_label(panel, "右下角:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.radius_br_ctrl = wx.TextCtrl(panel, value="0", size=wx.Size(60, -1))
        gs.Add(self.radius_br_ctrl, 0, wx.ALIGN_CENTER_VERTICAL)
        
        cont2.Add(gs, 0, wx.EXPAND | wx.RIGHT, 20)
        sizer.Add(card2, 0, wx.EXPAND | wx.ALL, 15)
        
        go_btn = wx.Button(panel, label="生成并保存为PNG", size=wx.Size(180, 45))
        go_btn.Bind(wx.EVT_BUTTON, self._on_apply_radius)
        sizer.Add(go_btn, 0, wx.ALIGN_CENTER | wx.TOP, 10)
        
        panel.SetSizer(sizer)
        return panel

    def _on_radius_all_changed(self, e):
        val = self.radius_all_ctrl.GetValue()
        if val.isdigit():
            self.radius_tl_ctrl.SetValue(val)
            self.radius_tr_ctrl.SetValue(val)
            self.radius_bl_ctrl.SetValue(val)
            self.radius_br_ctrl.SetValue(val)

    def _on_apply_radius(self, e):
        src = self.radius_src_ctrl.GetValue()
        if not src or not os.path.exists(src):
            wx.MessageBox("请选择源图片", "提示")
            return

        try:
            tl = int(self.radius_tl_ctrl.GetValue() or 0)
            tr = int(self.radius_tr_ctrl.GetValue() or 0)
            bl = int(self.radius_bl_ctrl.GetValue() or 0)
            br = int(self.radius_br_ctrl.GetValue() or 0)
        except ValueError:
            wx.MessageBox("圆角值必须是数字", "错误")
            return

        with wx.FileDialog(self, "保存图片", defaultFile="rounded.png",
                           wildcard="PNG files (*.png)|*.png|All files (*.*)|*.*",
                           style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fd:
            if fd.ShowModal() == wx.ID_OK:
                save_path = fd.GetPath()
                with Image.open(src) as img:
                    img = img.convert("RGBA")
                    w, h = img.size

                    # 创建一个透明背景图层
                    rounded = Image.new("RGBA", (w, h), (0, 0, 0, 0))
                    # 绘制白色圆角矩形作为临时遮罩（抗锯齿用）
                    mask = Image.new("L", (w, h), 0)
                    draw = ImageDraw.Draw(mask)

                    # 使用多边形+圆弧方式绘制支持不同半径的圆角矩形（避免第二个矩形覆盖）
                    # 这里提供标准实现：绘制4个角的圆弧和中间矩形
                    # 坐标边界
                    x1, y1 = 0, 0
                    x2, y2 = w, h

                    # 绘制顶部水平线（从左上角圆弧结束到右上角圆弧开始）
                    if tl > 0:
                        draw.pieslice([x1, y1, x1 + 2 * tl, y1 + 2 * tl], 180, 270, fill=255)
                    if tr > 0:
                        draw.pieslice([x2 - 2 * tr, y1, x2, y1 + 2 * tr], 270, 360, fill=255)
                    if bl > 0:
                        draw.pieslice([x1, y2 - 2 * bl, x1 + 2 * bl, y2], 90, 180, fill=255)
                    if br > 0:
                        draw.pieslice([x2 - 2 * br, y2 - 2 * br, x2, y2], 0, 90, fill=255)

                    # 绘制中心矩形（避开四个圆角区域）
                    # 矩形左边界：如果左上角或左下角有圆角，左边界从 max(tl, bl) 开始，否则为0
                    left = max(tl, bl)
                    right = w - max(tr, br)
                    top = max(tl, tr)
                    bottom = h - max(bl, br)
                    if left < right and top < bottom:
                        draw.rectangle([left, top, right, bottom], fill=255)

                    # 绘制四个边上的窄条（补齐圆弧之间的间隙）
                    if tl > 0 or tr > 0:
                        draw.rectangle([tl, 0, w - tr, top], fill=255)  # 上边
                    if bl > 0 or br > 0:
                        draw.rectangle([bl, bottom, w - br, h], fill=255)  # 下边
                    if tl > 0 or bl > 0:
                        draw.rectangle([0, tl, left, h - bl], fill=255)  # 左边
                    if tr > 0 or br > 0:
                        draw.rectangle([right, tr, w, h - br], fill=255)  # 右边

                    # 应用mask到原图
                    img.putalpha(mask)
                    img.save(save_path, "PNG")
                wx.MessageBox("处理成功", "完成")

    def _build_b64_panel(self):
        panel = wx.Panel(self.nb)
        panel.SetBackgroundColour(ThemeManager.BG_WINDOW)
        sizer = wx.BoxSizer(wx.VERTICAL)
        for label, btn_lbl, handler, ctrl_attr in [
            ("图片 转 Base64", "转换并保存", self._on_img_to_b64, "b64_img_ctrl"),
            ("Base64 转 图片", "还原并保存", self._on_b64_to_img, "b64_txt_ctrl")
        ]:
            card, cont = self._create_card_sizer(panel, label)
            h = wx.BoxSizer(wx.HORIZONTAL)
            ctrl = wx.TextCtrl(panel)
            setattr(self, ctrl_attr, ctrl)
            h.Add(ctrl, 1, wx.CENTER | wx.RIGHT, 10)
            btn_br = wx.Button(panel, label="浏览", size=wx.Size(80, 36))
            btn_br.Bind(wx.EVT_BUTTON, lambda e, c=ctrl: self._on_browse(c))
            h.Add(btn_br, 0, wx.CENTER | wx.RIGHT, 10)
            btn_go = wx.Button(panel, label=btn_lbl, size=wx.Size(100, 36))
            btn_go.Bind(wx.EVT_BUTTON, handler)
            h.Add(btn_go, 0, wx.CENTER)
            cont.Add(h, 0, wx.EXPAND | wx.RIGHT | wx.BOTTOM, 10)
            sizer.Add(card, 0, wx.EXPAND | wx.ALL, 15)
        panel.SetSizer(sizer)
        return panel

    def _on_browse_size(self, e):
        with wx.FileDialog(self.GetTopLevelParent(), "打开图片") as fd:
            fd.CenterOnParent()
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
        if not src or not os.path.exists(src):
            return

        fmt = self.conv_fmt_cb.GetValue()
        ext = fmt.lower()
        wildcard = f"{fmt} files (*.{ext})|*.{ext}|All files (*.*)|*.*"
        with wx.FileDialog(self.GetTopLevelParent(), "保存图片", defaultFile="converted."+ext, wildcard=wildcard, style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fd:
            fd.CenterOnParent()
            if fd.ShowModal() == wx.ID_OK:
                save_path = fd.GetPath()
                with Image.open(src) as img:
                    if fmt == "JPEG" and img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                    img.save(save_path, fmt)
                wx.MessageBox("转换成功", "完成")

    def _on_compress(self, e):
        src = self.comp_src_ctrl.GetValue()
        if not src:
            return

        ext = os.path.splitext(src)[1].lower()
        # 根据扩展名构建友好的文件类型描述
        if ext in ('.png',):
            desc = "PNG files (*.png)|*.png"
        elif ext in ('.jpg', '.jpeg'):
            desc = "JPEG files (*.jpg;*.jpeg)|*.jpg;*.jpeg"
        elif ext in ('.webp',):
            desc = "WEBP files (*.webp)|*.webp"
        else:
            desc = f"Image files (*{ext})|*{ext}"
        # 关键：添加 "All files" 作为备份，防止空数组
        wildcard = f"{desc}|All files (*.*)|*.*"

        ext = str(os.path.splitext(src)[1].lower())
        with wx.FileDialog(self.GetTopLevelParent(), "保存压缩后的图片", defaultFile="compressed"+ext, wildcard=wildcard, style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fd:
            fd.CenterOnParent()
            if fd.ShowModal() == wx.ID_OK:
                save_path = fd.GetPath()
                with Image.open(src) as img:
                    if "png" in ext:
                        fmt = "PNG"
                        # PNG 压缩
                        quality = self.comp_quality_sld.GetValue()
                        # compress_level 0-9
                        clevel = int((100 - quality) / 10)
                        img.save(save_path, format=fmt, optimize=True, compress_level=clevel)
                    else:
                        fmt = "JPEG" if "jpg" in ext or "jpeg" in ext else "WEBP"
                        if fmt == "JPEG" and img.mode in ("RGBA", "P"):
                            img = img.convert("RGB")
                        img.save(save_path, format=fmt, quality=self.comp_quality_sld.GetValue(), optimize=True)
                wx.MessageBox("压缩成功", "完成")

    def _on_resize_crop(self, e):
        src = self.size_src_ctrl.GetValue()
        if not src:
            return

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

        ext = os.path.splitext(src)[1].lower()
        # 根据扩展名构建友好的文件类型描述
        if ext in ('.png',):
            desc = "PNG files (*.png)|*.png"
        elif ext in ('.jpg', '.jpeg'):
            desc = "JPEG files (*.jpg;*.jpeg)|*.jpg;*.jpeg"
        elif ext in ('.webp',):
            desc = "WEBP files (*.webp)|*.webp"
        else:
            desc = f"Image files (*{ext})|*{ext}"
        # 关键：添加 "All files" 作为备份，防止空数组
        wildcard = f"{desc}|All files (*.*)|*.*"

        ext = str(os.path.splitext(src)[1])
        with wx.FileDialog(self.GetTopLevelParent(), "保存处理后的图片", defaultFile="processed"+ext, wildcard=wildcard, style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fd:
            fd.CenterOnParent()
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
        if not src or not os.path.exists(src):
            return

        with open(src, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
            data = f"data:image/{os.path.splitext(src)[1][1:]};base64,{b64}"

        wildcard = "TEXT files (*.txt)|*.txt|All files (*.*)|*.*"

        with wx.FileDialog(self.GetTopLevelParent(), "保存 Base64 文本", defaultFile="image_base64.txt",
                         wildcard=wildcard, style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fd:
            fd.CenterOnParent()
            if fd.ShowModal() == wx.ID_OK:
                with open(fd.GetPath(), "w") as f:
                    f.write(data)
                wx.MessageBox("转换成功并已保存到文件", "成功")

    def _on_b64_to_img(self, e):
        path = self.b64_txt_ctrl.GetValue()
        if not path or not os.path.exists(path):
            return

        try:
            with open(path, "r") as f:
                content = f.read().strip()

            # 解析图片格式和纯 base64 数据
            img_format = None
            if content.startswith("data:image/"):
                # 格式: data:image/png;base64,xxxx
                header, data = content.split(",", 1)
                # 提取 MIME 类型，例如 "data:image/png;base64" -> "png"
                mime = header.split(";")[0].split("/")[1]  # "png", "jpeg", "gif", "webp" 等
                img_format = mime.lower().replace("jpeg", "jpg")  # 统一 .jpg 扩展名
            else:
                # 纯 base64，无 MIME 信息，尝试根据解码后的文件头猜测格式
                data = content

            # 解码 base64
            img_data = base64.b64decode(data)

            # 如果没有从 header 获取到格式，则尝试从二进制数据猜测
            if img_format is None:
                # 检查常见文件头
                if img_data.startswith(b'\x89PNG\r\n\x1a\n'):
                    img_format = "png"
                elif img_data.startswith(b'\xff\xd8'):
                    img_format = "jpg"
                elif img_data.startswith(b'GIF87a') or img_data.startswith(b'GIF89a'):
                    img_format = "gif"
                elif img_data.startswith(b'RIFF') and img_data[8:12] == b'WEBP':
                    img_format = "webp"
                else:
                    # 默认 png
                    img_format = "png"

            # 构造默认文件名
            default_name = f"restored.{img_format}"

            # 设置文件类型过滤器（可选，让用户只能保存为该格式）
            wildcard = f"{img_format.upper()} files (*.{img_format})|*.{img_format}|All files (*.*)|*.*"

            with wx.FileDialog(self, "保存还原后的图片",
                               defaultFile=default_name,
                               wildcard=wildcard,
                               style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fd:
                fd.CenterOnParent()
                if fd.ShowModal() == wx.ID_OK:
                    save_path = fd.GetPath()
                    # 确保扩展名正确（如果用户删除了扩展名，自动补上）
                    if not save_path.lower().endswith(f'.{img_format}'):
                        save_path += f'.{img_format}'
                    with open(save_path, "wb") as f:
                        f.write(img_data)
                    wx.MessageBox("还原成功", "完成")
        except Exception as ex:
            wx.MessageBox(f"失败: {str(ex)}", "错误")
