# -*- coding: utf-8 -*-
# Author: sens
# Date: 2026/05/12 17:10

import tkinter as tk
from tkinter import ttk, messagebox
import base64
import urllib.parse
import html
import zhconv
from ui.styles import StyleManager
from utils.common import copy_to_clipboard

class EncodeTab:
    """编码转换标签页：Base64, URL, Unicode, HTML, 大小写, 繁简转换"""
    def __init__(self, parent, root):
        self.parent = parent
        self.root = root
        self.encode_input = None
        self.encode_output = None
        self._setup_ui()

    def _setup_ui(self):
        text_style = StyleManager.get_text_area_style()
        
        # 输入区 - 高度从 6 减少到 4
        in_frame = ttk.LabelFrame(self.parent, text="输入内容")
        in_frame.pack(fill="x", padx=10, pady=5)
        self.encode_input = tk.Text(in_frame, height=4, **text_style)
        self.encode_input.pack(fill="x", padx=5, pady=5)
        
        # 按钮容器
        btn_container = ttk.Frame(self.parent)
        btn_container.pack(fill="x", padx=10, pady=5)

        # 1. 编码转换组
        enc_frame = ttk.LabelFrame(btn_container, text="编码转换")
        enc_frame.pack(fill="x", pady=5)
        enc_btns = [
            ("Base64 编码", self.b64_encode), ("Base64 解码", self.b64_decode),
            ("URL 编码", self.url_encode), ("URL 解码", self.url_decode),
            ("Unicode 编码", self.unicode_encode), ("Unicode 解码", self.unicode_decode),
            ("HTML 转义", self.html_escape), ("HTML 反转义", self.html_unescape)
        ]
        for i, (t, c) in enumerate(enc_btns):
            btn = ttk.Button(enc_frame, text=t, command=c)
            btn.grid(row=i//6, column=i%6, padx=5, pady=2, sticky="ew")
        
        # 2. 文本转换组 (大小写、繁简转换等)
        txt_frame = ttk.LabelFrame(btn_container, text="文本转换")
        txt_frame.pack(fill="x", pady=5)
        txt_btns = [
            ("转大写", self.to_upper), ("转小写", self.to_lower), ("大小写互转", self.swap_case),
            ("转繁体", self.to_traditional), ("转简体", self.to_simplified)
        ]
        for i, (t, c) in enumerate(txt_btns):
            btn = ttk.Button(txt_frame, text=t, command=c)
            btn.grid(row=0, column=i, padx=5, pady=2, sticky="ew")

        # 结果区
        res_frame = ttk.LabelFrame(self.parent, text="转换结果")
        res_frame.pack(fill="both", expand=True, padx=10, pady=5)
        res_style = text_style.copy()
        res_style.update({"font": ("Courier", 11), "height": 8})
        self.encode_output = tk.Text(res_frame, wrap="char", **res_style)
        self.encode_output.pack(fill="both", expand=True, padx=5, pady=5)
        
        ttk.Button(res_frame, text="复制结果", 
                   command=lambda: copy_to_clipboard(self.root, self.encode_output.get("1.0", tk.END).strip())).pack(pady=5)

    def _safe_exec(self, func):
        try:
            res = func()
            self.encode_output.delete("1.0", tk.END)
            self.encode_output.insert("1.0", res)
        except Exception as e:
            messagebox.showerror("错误", f"操作失败: {str(e)}", parent=self.root)

    def to_upper(self):
        self._safe_exec(lambda: self.encode_input.get("1.0", tk.END).strip().upper())

    def to_lower(self):
        self._safe_exec(lambda: self.encode_input.get("1.0", tk.END).strip().lower())

    def swap_case(self):
        self._safe_exec(lambda: self.encode_input.get("1.0", tk.END).strip().swapcase())

    def to_traditional(self):
        self._safe_exec(lambda: zhconv.convert(self.encode_input.get("1.0", tk.END).strip(), 'zh-hant'))

    def to_simplified(self):
        self._safe_exec(lambda: zhconv.convert(self.encode_input.get("1.0", tk.END).strip(), 'zh-hans'))

    def b64_encode(self):
        self._safe_exec(lambda: base64.b64encode(self.encode_input.get("1.0", tk.END).strip().encode()).decode())

    def b64_decode(self):
        self._safe_exec(lambda: base64.b64decode(self.encode_input.get("1.0", tk.END).strip().encode()).decode())

    def url_encode(self):
        self._safe_exec(lambda: urllib.parse.quote(self.encode_input.get("1.0", tk.END).strip()))

    def url_decode(self):
        self._safe_exec(lambda: urllib.parse.unquote(self.encode_input.get("1.0", tk.END).strip()))

    def unicode_encode(self):
        self._safe_exec(lambda: self.encode_input.get("1.0", tk.END).strip().encode('unicode_escape').decode('ascii'))

    def unicode_decode(self):
        self._safe_exec(lambda: self.encode_input.get("1.0", tk.END).strip().encode().decode('unicode_escape'))

    def html_escape(self):
        self._safe_exec(lambda: html.escape(self.encode_input.get("1.0", tk.END).strip()))

    def html_unescape(self):
        self._safe_exec(lambda: html.unescape(self.encode_input.get("1.0", tk.END).strip()))
