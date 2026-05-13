# -*- coding: utf-8 -*-
# Author: sens
# Date: 2026/05/12 15:30

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import re
import os
from bs4 import BeautifulSoup
from ui.styles import StyleManager
from utils.common import copy_to_clipboard

class FormatTab:
    """数据格式化标签页：JSON, HTML/XML, JS/TS"""
    def __init__(self, parent, root):
        self.parent = parent
        self.root = root
        self.format_mode_tabs = None
        self.format_input = None
        self.format_file_path = None
        self.format_output = None
        self._setup_ui()

    def _setup_ui(self):
        text_style = StyleManager.get_text_area_style()
        
        self.format_mode_tabs = ttk.Notebook(self.parent)
        fmt_sub_text = ttk.Frame(self.format_mode_tabs)
        fmt_sub_file = ttk.Frame(self.format_mode_tabs)
        self.format_mode_tabs.add(fmt_sub_text, text="文本模式")
        self.format_mode_tabs.add(fmt_sub_file, text="文件模式")
        self.format_mode_tabs.pack(fill="x", padx=0, pady=5)

        # 文本模式输入
        self.format_input = tk.Text(fmt_sub_text, height=10, **text_style)
        self.format_input.pack(fill="x", padx=5, pady=5)
        ttk.Button(fmt_sub_text, text="清空输入", command=lambda: self.format_input.delete("1.0", tk.END)).pack(side="right", padx=5)

        # 文件模式输入
        fmt_file_frame = ttk.Frame(fmt_sub_file)
        fmt_file_frame.pack(fill="x", padx=5, pady=25)
        ttk.Label(fmt_file_frame, text="文件路径:").pack(side="left")
        self.format_file_path = ttk.Entry(fmt_file_frame, font=("Arial", 11))
        self.format_file_path.pack(side="left", padx=5, expand=True, fill="x")
        ttk.Button(fmt_file_frame, text="选择文件", command=self.select_file).pack(side="left")

        # 按钮区
        btn_frame = ttk.Frame(self.parent)
        btn_frame.pack(fill="x", padx=10, pady=0)
        btns = [
            ("JSON 格式化", self.json_format), ("JSON 压缩", self.json_compress),
            ("HTML/XML 格式化", self.html_xml_format), ("JS/TS 格式化", self.js_ts_format),
            ("JS/TS 压缩", self.js_ts_compress)
        ]
        for i, (t, c) in enumerate(btns):
            btn = ttk.Button(btn_frame, text=t, command=c)
            btn.grid(row=i//6, column=i%6, padx=5, pady=2, sticky="ew")

        # 结果区（带滚动条）
        res_frame = ttk.LabelFrame(self.parent, text="格式化结果")
        res_frame.pack(fill="both", expand=True, padx=10, pady=15)
        
        container = ttk.Frame(res_frame)
        container.pack(fill="both", expand=True, padx=5, pady=5)
        
        res_style = text_style.copy()
        res_style.update({
            "font": ("Courier", 11),
            "wrap": "none",
            "padx": 5,  # 水平内边距
            "pady": 5   # 垂直内边距
        })
        self.format_output = tk.Text(container, **res_style)
        v_scroll = ttk.Scrollbar(container, orient="vertical", command=self.format_output.yview)
        h_scroll = ttk.Scrollbar(container, orient="horizontal", command=self.format_output.xview)
        self.format_output.configure(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)
        
        v_scroll.pack(side="right", fill="y")
        h_scroll.pack(side="bottom", fill="x")
        self.format_output.pack(side="left", fill="both", expand=True)
        
        ttk.Button(res_frame, text="复制结果", 
                   command=lambda: copy_to_clipboard(self.root, self.format_output.get("1.0", tk.END).strip())).pack(pady=5)

    def select_file(self):
        path = filedialog.askopenfilename(parent=self.root)
        if path:
            self.format_file_path.delete(0, tk.END)
            self.format_file_path.insert(0, path)

    def _get_input(self):
        mode = self.format_mode_tabs.index(self.format_mode_tabs.select())
        if mode == 0:
            return self.format_input.get("1.0", tk.END).strip()
        else:
            path = self.format_file_path.get().strip().strip("\"'\"")
            if not path or not os.path.isfile(path):
                messagebox.showerror("错误", "文件路径无效", parent=self.root)
                return None
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return f.read().strip()
            except Exception as e:
                messagebox.showerror("读取失败", str(e), parent=self.root)
                return None

    def _set_output(self, text):
        self.format_output.delete("1.0", tk.END)
        self.format_output.insert("1.0", text)

    def json_format(self):
        data = self._get_input()
        if data:
            try: self._set_output(json.dumps(json.loads(data), indent=4, ensure_ascii=False))
            except Exception as e: messagebox.showerror("JSON 错误", str(e))

    def json_compress(self):
        data = self._get_input()
        if data:
            try: self._set_output(json.dumps(json.loads(data), separators=(',', ':'), ensure_ascii=False))
            except Exception as e: messagebox.showerror("JSON 错误", str(e))

    def html_xml_format(self):
        data = self._get_input()
        if data:
            try:
                is_xml = data.startswith("<?xml") or ("<" in data and not data.lower().startswith("<!doctype html"))
                soup = BeautifulSoup(data, "xml" if is_xml else "html.parser")
                self._set_output(soup.prettify())
            except Exception as e: messagebox.showerror("格式化错误", str(e))

    def js_ts_format(self):
        code = self._get_input()
        if not code: return
        # 简单正则格式化实现
        code = code.replace('{', ' {\n').replace('}', '\n}\n').replace(';', ';\n')
        code = re.sub(r'\n\s*\n', '\n', code)
        lines = code.split('\n')
        indent, formatted = 0, []
        for line in lines:
            line = line.strip()
            if not line: continue
            if line.startswith('}'): indent -= 1
            formatted.append("    " * max(0, indent) + line)
            if line.endswith('{'): indent += 1
        self._set_output('\n'.join(formatted))

    def js_ts_compress(self):
        code = self._get_input()
        if not code: return
        code = re.sub(r'//.*?\n|/\*.*?\*/', '', code, flags=re.S)
        code = re.sub(r'\s+', ' ', code)
        code = re.sub(r'\s*([\{\}\(\)\[\];,])\s*', r'\1', code)
        self._set_output(code.strip())
