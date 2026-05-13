# -*- coding: utf-8 -*-
# Author: sens
# Date: 2026/05/12 18:30

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import base64
import os
import io
from PIL import Image
from ui.styles import StyleManager
from utils.common import copy_to_clipboard

class ImageTab:
    """图片处理标签页：格式转换、压缩、尺寸调整与 Base64 互转"""
    def __init__(self, parent, root):
        self.parent = parent
        self.root = root
        
        # 1. 格式转换变量
        self.conv_src_path = tk.StringVar()
        self.target_ext = tk.StringVar(value="PNG")
        
        # 2. 图片压缩变量
        self.comp_src_path = tk.StringVar()
        self.comp_quality = tk.IntVar(value=75)

        # 3. 尺寸调整变量
        self.size_src_path = tk.StringVar()
        self.target_width = tk.StringVar()
        self.target_height = tk.StringVar()
        self.keep_ratio = tk.BooleanVar(value=True)
        self.size_mode = tk.StringVar(value="resize") # resize, center, tl, tr, bl, br
        self.orig_ratio = 1.0
        self._is_updating = False # 防止监听循环
        
        # 4. Base64 变量
        self.b64_img_path = tk.StringVar()
        self.b64_txt_path = tk.StringVar()
        
        self._setup_ui()
        self._setup_traces()

    def _setup_ui(self):
        sub_notebook = ttk.Notebook(self.parent)
        sub_notebook.pack(expand=True, fill="both", padx=5, pady=5)
        
        tabs = [
            (self._build_conv_ui, "格式转换"),
            (self._build_comp_ui, "图片压缩"),
            (self._build_size_ui, "尺寸处理"),
            (self._build_b64_ui, "Base64 互转")
        ]
        for builder, name in tabs:
            frame = ttk.Frame(sub_notebook)
            sub_notebook.add(frame, text=name)
            builder(frame)

    def _setup_traces(self):
        self.target_width.trace_add("write", lambda *args: self._sync_ratio("w"))
        self.target_height.trace_add("write", lambda *args: self._sync_ratio("h"))

    def _sync_ratio(self, origin):
        if not self.keep_ratio.get() or self._is_updating or not self.size_src_path.get():
            return
        self._is_updating = True
        try:
            if origin == "w":
                val = self.target_width.get()
                if val and val.isdigit():
                    self.target_height.set(str(int(int(val) / self.orig_ratio)))
            else:
                val = self.target_height.get()
                if val and val.isdigit():
                    self.target_width.set(str(int(int(val) * self.orig_ratio)))
        except: pass
        self._is_updating = False

    def _build_conv_ui(self, frame):
        src_row = ttk.LabelFrame(frame, text="选择源图片")
        src_row.pack(fill="x", padx=10, pady=10)
        ttk.Entry(src_row, textvariable=self.conv_src_path, font=("Arial", 11)).pack(side="left", padx=5, pady=10, expand=True, fill="x")
        ttk.Button(src_row, text="浏览", command=self._select_conv_src).pack(side="left", padx=5)
        
        target_row = ttk.LabelFrame(frame, text="转换设置")
        target_row.pack(fill="x", padx=10, pady=10)
        ttk.Label(target_row, text="目标格式:").pack(side="left", padx=5, pady=10)
        formats = ["PNG", "JPEG", "WEBP", "BMP", "ICO", "TIFF", "GIF"]
        cb = ttk.Combobox(target_row, textvariable=self.target_ext, values=formats, width=10, state="readonly")
        cb.pack(side="left", padx=5)
        ttk.Button(frame, text="开始转换并保存", command=self._convert_image).pack(pady=20)

    def _build_comp_ui(self, frame):
        src_row = ttk.LabelFrame(frame, text="选择图片 (仅限 JPEG/WEBP)")
        src_row.pack(fill="x", padx=10, pady=10)
        ttk.Entry(src_row, textvariable=self.comp_src_path, font=("Arial", 11)).pack(side="left", padx=5, pady=10, expand=True, fill="x")
        ttk.Button(src_row, text="浏览", command=self._select_comp_src).pack(side="left", padx=5)

        set_row = ttk.LabelFrame(frame, text="压缩设置")
        set_row.pack(fill="x", padx=10, pady=10)
        ttk.Label(set_row, text="质量 (1-100):").pack(side="left", padx=5)
        
        # 优化滑块，解决感知区域过窄问题
        scale = tk.Scale(set_row, from_=1, to=100, orient="horizontal", 
                         variable=self.comp_quality, 
                         showvalue=False,
                         borderwidth=0,
                         highlightthickness=0,
                         bg="#454545", 
                         troughcolor="#1a1a1a", 
                         activebackground="#007AFF", 
                         width=25, 
                         sliderlength=30, 
                         sliderrelief='flat',
                         cursor="hand2")
        scale.pack(side="left", padx=5, expand=True, fill="x")
        
        ttk.Label(set_row, textvariable=self.comp_quality, width=3, font=("Arial", 10, "bold")).pack(side="left", padx=5)
        ttk.Button(frame, text="执行有损压缩并保存", command=self._compress_image).pack(pady=20)

    def _build_size_ui(self, frame):
        src_row = ttk.LabelFrame(frame, text="选择源图片")
        src_row.pack(fill="x", padx=10, pady=10)
        ttk.Entry(src_row, textvariable=self.size_src_path, font=("Arial", 11)).pack(side="left", padx=5, pady=10, expand=True, fill="x")
        ttk.Button(src_row, text="浏览", command=self._select_size_src).pack(side="left", padx=5)

        config_row = ttk.LabelFrame(frame, text="尺寸配置")
        config_row.pack(fill="x", padx=10, pady=10)
        
        # 模式选择行：缩放与裁剪合并
        mode_frame = ttk.Frame(config_row)
        mode_frame.pack(fill="x", padx=5, pady=10)
        
        all_modes = [
            ("缩放", "resize"),
            ("中心裁剪", "center"),
            ("左上裁剪", "tl"),
            ("右上裁剪", "tr"),
            ("左下裁剪", "bl"),
            ("右下裁剪", "br")
        ]
        for text, mode in all_modes:
            ttk.Radiobutton(mode_frame, text=text, variable=self.size_mode, value=mode).pack(side="left", padx=10)

        # 尺寸输入行
        s_frame = ttk.Frame(config_row); s_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(s_frame, text="宽度 (px):").pack(side="left", padx=5)
        ttk.Entry(s_frame, textvariable=self.target_width, width=8).pack(side="left", padx=5)
        ttk.Label(s_frame, text="高度 (px):").pack(side="left", padx=(15, 5))
        ttk.Entry(s_frame, textvariable=self.target_height, width=8).pack(side="left", padx=5)
        ttk.Checkbutton(s_frame, text="保持比例", variable=self.keep_ratio).pack(side="left", padx=20)
        ttk.Button(frame, text="开始处理并保存", command=self._resize_crop_image).pack(pady=20)

    def _build_b64_ui(self, frame):
        i2b_row = ttk.LabelFrame(frame, text="图片 转 Base64")
        i2b_row.pack(fill="x", padx=10, pady=10)
        ttk.Entry(i2b_row, textvariable=self.b64_img_path, font=("Arial", 11)).pack(side="left", padx=5, pady=10, expand=True, fill="x")
        ttk.Button(i2b_row, text="选择图片", command=self._select_b64_img).pack(side="left", padx=5)
        ttk.Button(i2b_row, text="转换并复制代码", command=self._img_to_base64).pack(side="left", padx=5)
        b2i_row = ttk.LabelFrame(frame, text="Base64 转 图片")
        b2i_row.pack(fill="x", padx=10, pady=10)
        ttk.Entry(b2i_row, textvariable=self.b64_txt_path, font=("Arial", 11)).pack(side="left", padx=5, pady=10, expand=True, fill="x")
        ttk.Button(b2i_row, text="选择文本文件", command=self._select_b64_txt).pack(side="left", padx=5)
        ttk.Button(b2i_row, text="还原为图片", command=self._base64_to_img).pack(side="left", padx=5)

    def _select_conv_src(self):
        path = filedialog.askopenfilename(parent=self.root)
        if path: self.conv_src_path.set(path)

    def _convert_image(self):
        src = self.conv_src_path.get()
        if not src or not os.path.exists(src): return
        target_fmt = self.target_ext.get()
        base, _ = os.path.splitext(src)
        save_path = filedialog.asksaveasfilename(parent=self.root, defaultextension=f".{target_fmt.lower()}", initialfile=os.path.basename(base) + f"_converted", initialdir=os.path.dirname(src))
        if save_path:
            with Image.open(src) as img:
                if target_fmt == "JPEG" and img.mode in ("RGBA", "P"): img = img.convert("RGB")
                img.save(save_path, target_fmt)
            messagebox.showinfo("成功", "转换完成", parent=self.root)

    def _select_comp_src(self):
        path = filedialog.askopenfilename(parent=self.root, filetypes=[("JPEG/WEBP", "*.jpg *.jpeg *.webp")])
        if path: self.comp_src_path.set(path)

    def _compress_image(self):
        src = self.comp_src_path.get()
        if not src: return
        ext = os.path.splitext(src)[1].lower()
        base, _ = os.path.splitext(src)
        save_path = filedialog.asksaveasfilename(parent=self.root, defaultextension=ext, initialfile=os.path.basename(base) + f"_compressed", initialdir=os.path.dirname(src))
        if save_path:
            with Image.open(src) as img:
                fmt = "JPEG" if "jpg" in ext or "jpeg" in ext else "WEBP"
                if fmt == "JPEG" and img.mode in ("RGBA", "P"): img = img.convert("RGB")
                img.save(save_path, format=fmt, quality=self.comp_quality.get(), optimize=True)
            messagebox.showinfo("成功", "压缩完成", parent=self.root)

    def _select_size_src(self):
        path = filedialog.askopenfilename(parent=self.root)
        if path:
            self.size_src_path.set(path)
            with Image.open(path) as img:
                self.orig_ratio = img.width / img.height if img.height != 0 else 1.0
                self._is_updating = True
                self.target_width.set(str(img.width))
                self.target_height.set(str(img.height))
                self._is_updating = False

    def _resize_crop_image(self):
        src = self.size_src_path.get()
        if not src: return
        try: tw, th = int(self.target_width.get()), int(self.target_height.get())
        except: return messagebox.showerror("错误", "尺寸必须为整数", parent=self.root)
        base, ext = os.path.splitext(src)
        
        mode = self.size_mode.get()
        suffix = f"_{mode}"
        save_path = filedialog.asksaveasfilename(parent=self.root, defaultextension=ext, initialfile=os.path.basename(base) + suffix, initialdir=os.path.dirname(src))
        if not save_path: return
        try:
            with Image.open(src) as img:
                w, h = img.size
                if mode == "resize":
                    res_img = img.resize((tw, th), Image.Resampling.LANCZOS)
                else:
                    # 裁剪逻辑
                    if tw > w or th > h:
                        return messagebox.showerror("错误", f"裁剪尺寸 ({tw}x{th}) 不能大于原图尺寸 ({w}x{h})", parent=self.root)
                    
                    if mode == "center":
                        left, top = (w - tw) / 2, (h - th) / 2
                    elif mode == "tl": # Top-Left
                        left, top = 0, 0
                    elif mode == "tr": # Top-Right
                        left, top = w - tw, 0
                    elif mode == "bl": # Bottom-Left
                        left, top = 0, h - th
                    elif mode == "br": # Bottom-Right
                        left, top = w - tw, h - th
                    else:
                        left, top = (w - tw) / 2, (h - th) / 2
                        
                    res_img = img.crop((left, top, left + tw, top + th))
                res_img.save(save_path)
            messagebox.showinfo("成功", "处理完成", parent=self.root)
        except Exception as e: messagebox.showerror("错误", str(e), parent=self.root)

    def _select_b64_img(self):
        path = filedialog.askopenfilename(parent=self.root)
        if path: self.b64_img_path.set(path)

    def _select_b64_txt(self):
        path = filedialog.askopenfilename(parent=self.root, filetypes=[("Text", "*.txt"), ("All", "*")])
        if path: self.b64_txt_path.set(path)

    def _img_to_base64(self):
        src = self.b64_img_path.get()
        if not src: return
        with open(src, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
            copy_to_clipboard(self.root, f"data:image/{os.path.splitext(src)[1][1:]};base64,{b64}")
            messagebox.showinfo("成功", "已复制", parent=self.root)

    def _base64_to_img(self):
        path = self.b64_txt_path.get()
        if not path: return
        try:
            with open(path, "r") as f:
                content = f.read().strip()
            
            # 默认后缀
            ext = ".png"
            
            # 1. 尝试从 Data URI 头部识别
            if content.startswith("data:image/"):
                header = content.split(";")[0]
                detected_type = header.split("/")[1]
                if detected_type:
                    ext = f".{detected_type}"
            
            # 去掉 Base64 头部（如果有）
            if "," in content: content = content.split(",")[1]
            img_data = base64.b64decode(content)
            
            # 2. 尝试使用 PIL 识别真实格式
            try:
                with Image.open(io.BytesIO(img_data)) as img:
                    if img.format:
                        ext = f".{img.format.lower()}"
            except:
                pass

            save_path = filedialog.asksaveasfilename(
                parent=self.root, 
                defaultextension=ext,
                initialfile=f"restored_image{ext}", 
                initialdir=os.path.dirname(path)
            )
            if save_path:
                with open(save_path, "wb") as f:
                    f.write(img_data)
                messagebox.showinfo("成功", "图片已还原并保存", parent=self.root)
        except Exception as e:
            messagebox.showerror("错误", f"还原失败: {str(e)}", parent=self.root)
