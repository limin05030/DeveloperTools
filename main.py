# -*- coding: utf-8 -*-
# Author: sens
# Date: 2026/5/11 13:10

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import hashlib
import hmac
import base64
import urllib.parse
import time
import os
import json
import html
import re
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup

class ToolApp:
    def __init__(self, _root):
        self.root = _root
        self.root.title("开发者工具")
        # 窗口居中
        width = 880
        height = 900
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
        self.style = ttk.Style()
        if self.root.tk.call('tk', 'windowingsystem') == 'aqua':
            self.style.theme_use('aqua')
        
        # 提前定义所有成员变量 (Member Variables)
        self.APPLE_OFFSET = 978307200
        self.system_tz_str = ""
        
        # 标签页框架
        self.tab_hash = None
        self.tab_encode = None
        self.tab_format = None
        self.tab_time = None
        
        # 哈希计算相关
        self.hash_mode_tabs = None
        self.sub_tab_text = None
        self.sub_tab_file = None
        self.hash_text_input = None
        self.hash_file_path = None
        self.hash_key = None
        self.hash_output = None
        
        # 编码转换相关
        self.encode_input = None
        self.encode_output = None
        
        # 格式化相关
        self.format_mode_tabs = None
        self.fmt_sub_tab_text = None
        self.fmt_sub_tab_file = None
        self.format_input = None
        self.format_file_path = None
        self.format_output = None
        
        # 日期时间相关
        self.cur_tz_var = None
        self.cur_time_var = None
        self.cur_ts_var = None
        self.ts_input = None
        self.date_output = None
        self.t2d_tz_var = None
        self.t2d_ios_var = None
        self.date_input = None
        self.ts_output = None
        self.d2t_tz_var = None
        self.d2t_ios_var = None
        
        # 初始化配置
        self._setup_styles()
        self.system_tz_str = self._get_system_tz_str()
        self._init_tabs()

    def _setup_styles(self):
        self.style.configure("TLabelframe.Label", font=("Arial", 11, "bold"), foreground="white")
        self.style.configure("TLabel", font=("Arial", 10), foreground="white")
        self.style.configure("TButton", font=("Arial", 10))
        self.style.configure("TCheckbutton", font=("Arial", 10), foreground="white")
        self.style.configure("TEntry", fieldbackground="#333", bordercolor="#555", lightcolor="#555", darkcolor="#555")
        self.style.configure("TCombobox", fieldbackground="#333", bordercolor="#555", lightcolor="#555", darkcolor="#555")
        
        # 统一 Entry 焦点色映射
        self.style.map("TEntry", 
            bordercolor=[("focus", "#007AFF")], 
            lightcolor=[("focus", "#007AFF")], 
            darkcolor=[("focus", "#007AFF")])
        self.style.map("TCombobox", 
            bordercolor=[("focus", "#007AFF")], 
            lightcolor=[("focus", "#007AFF")], 
            darkcolor=[("focus", "#007AFF")])

    def _init_tabs(self):
        _tab_control = ttk.Notebook(self.root)
        self.tab_hash = ttk.Frame(_tab_control)
        self.tab_encode = ttk.Frame(_tab_control)
        self.tab_format = ttk.Frame(_tab_control)
        self.tab_time = ttk.Frame(_tab_control)
        
        _tab_control.add(self.tab_hash, text='哈希计算')
        _tab_control.add(self.tab_encode, text='编码转换')
        _tab_control.add(self.tab_format, text='格式化')
        _tab_control.add(self.tab_time, text='日期时间')
        _tab_control.pack(expand=1, fill="both")
        
        self.setup_hash_tab()
        self.setup_encode_tab()
        self.setup_format_tab()
        self.setup_time_tab()

    def _get_system_tz_str(self):
        _offset_sec = -time.timezone if (time.localtime().tm_isdst == 0) else -time.altzone
        return f"UTC{int(_offset_sec / 3600):+d}"

    def setup_hash_tab(self):
        self.style.configure("TNotebook", padding=0)
        self.hash_mode_tabs = ttk.Notebook(self.tab_hash)
        self.sub_tab_text = ttk.Frame(self.hash_mode_tabs)
        self.sub_tab_file = ttk.Frame(self.hash_mode_tabs)
        self.hash_mode_tabs.add(self.sub_tab_text, text="文本模式")
        self.hash_mode_tabs.add(self.sub_tab_file, text="文件模式")
        self.hash_mode_tabs.pack(fill="x", padx=10, pady=5)

        _base_style = {
            "highlightthickness": 1,
            "highlightbackground": "#555",
            "highlightcolor": "#007AFF",
            "relief": "flat",
            "bg": "#333",
            "fg": "white",
            "insertbackground": "white"
        }

        self.hash_text_input = tk.Text(self.sub_tab_text, height=5, font=("Arial", 11), **_base_style)
        self.hash_text_input.pack(fill="x", padx=5, pady=5)

        _file_frame = ttk.Frame(self.sub_tab_file)
        _file_frame.pack(fill="x", padx=5, pady=10)
        ttk.Label(_file_frame, text="文件路径:").pack(side="left")
        self.hash_file_path = ttk.Entry(_file_frame, font=("Arial", 11))
        self.hash_file_path.pack(side="left", padx=5, expand=True, fill="x")
        ttk.Button(_file_frame, text="选择文件", command=self.select_file).pack(side="left")

        _algo_frame = ttk.Frame(self.tab_hash)
        _algo_frame.pack(fill="x", padx=10, pady=5)
        
        _sh_frame = ttk.LabelFrame(_algo_frame, text="标准哈希 (Standard Hash)")
        _sh_frame.pack(fill="x", pady=5)
        _sh_btns = [
            ("MD5-16", "md5-16"), ("MD5-32", "md5-32"), ("SHA1", "sha1"), ("SHA224", "sha224"),
            ("SHA256", "sha256"), ("SHA384", "sha384"), ("SHA512", "sha512"), ("SHA3-224", "sha3_224"),
            ("SHA3-256", "sha3_256"), ("SHA3-384", "sha3_384"), ("SHA3-512", "sha3_512")
        ]
        for _i, (_t, _a) in enumerate(_sh_btns):
            _btn = ttk.Button(_sh_frame, text=_t, width=10, command=lambda _algo=_a: self.do_calc(_algo, False))
            _btn.grid(row=_i//6, column=_i%6, padx=8, pady=5)

        _hmac_frame = ttk.LabelFrame(_algo_frame, text="HMAC 计算 (Keyed Hash)")
        _hmac_frame.pack(fill="x", pady=5)
        
        _hmac_btns_frame = ttk.Frame(_hmac_frame)
        _hmac_btns_frame.pack(fill="x", padx=5, pady=5)
        
        _key_row = ttk.Frame(_hmac_frame)
        _key_row.pack(fill="x", padx=10, pady=10)
        ttk.Label(_key_row, text="HMAC 密钥 (Key):").pack(side="left")
        self.hash_key = ttk.Entry(_key_row, font=("Arial", 11))
        self.hash_key.pack(side="left", padx=10, expand=True, fill="x")
        
        _hmac_btns = [
            ("HmacMD5", "md5"), ("HmacSHA1", "sha1"), ("HmacSHA224", "sha224"), ("HmacSHA256", "sha256"),
            ("HmacSHA384", "sha384"), ("HmacSHA512", "sha512"), ("HmacSHA3-224", "sha3_224"), ("HmacSHA3-256", "sha3_256"),
            ("HmacSHA3-384", "sha3_384"), ("HmacSHA3-512", "sha3_512"), ("HmacRIPEMD160", "ripemd160")
        ]
        for _i, (_t, _a) in enumerate(_hmac_btns):
            _btn = ttk.Button(_hmac_btns_frame, text=_t, width=13, command=lambda _algo=_a: self.do_calc(_algo, True))
            _btn.grid(row=_i//5, column=_i%5, padx=8, pady=5)

        _res_frame = ttk.LabelFrame(self.tab_hash, text="计算结果")
        _res_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.hash_output = tk.Text(_res_frame, height=4, font=("Courier", 11, "bold"), wrap="char", **_base_style)
        self.hash_output.pack(fill="both", expand=True, padx=5, pady=5)
        
        _op_frame = ttk.Frame(_res_frame)
        _op_frame.pack(fill="x", padx=5, pady=5)
        ttk.Button(_op_frame, text="复制结果", command=lambda: self.copy_to_clipboard(self.hash_output.get("1.0", tk.END).strip())).pack(side="left", padx=5)
        ttk.Button(_op_frame, text="大小写切换", command=self.toggle_case).pack(side="left", padx=5)
        ttk.Button(_op_frame, text="清空全部", command=self.clear_all_hash).pack(side="left", padx=5)

    def select_file(self):
        _path = filedialog.askopenfilename(parent=self.root)
        if _path:
            self.hash_file_path.delete(0, tk.END)
            self.hash_file_path.insert(0, _path)
            self.hash_mode_tabs.select(1)

    def clear_all_hash(self):
        self.hash_text_input.delete("1.0", tk.END)
        self.hash_file_path.delete(0, tk.END)
        self.hash_key.delete(0, tk.END)
        self.hash_output.delete("1.0", tk.END)

    def toggle_case(self):
        _c = self.hash_output.get("1.0", tk.END).strip()
        if _c:
            _res = _c.lower() if _c.isupper() else _c.upper()
            self.hash_output.delete("1.0", tk.END)
            self.hash_output.insert("1.0", _res)

    def do_calc(self, _algo_name, _is_hmac):
        _mode = self.hash_mode_tabs.index(self.hash_mode_tabs.select())
        if _mode == 0:
            _content = self.hash_text_input.get("1.0", tk.END).strip()
            if not _content:
                return
            _res = self._hash_text(_content.encode('utf-8'), _algo_name, _is_hmac, self.hash_key.get().encode())
        else:
            _path = self.hash_file_path.get().strip().strip('\"\'')
            if _path.startswith("file://"):
                _path = _path[7:]
            if not os.path.isfile(_path):
                messagebox.showerror("错误", "文件路径无效", parent=self.root)
                return
            _res = self._hash_file(_path, _algo_name, _is_hmac, self.hash_key.get().encode())
        
        if _res:
            self.hash_output.delete("1.0", tk.END)
            self.hash_output.insert("1.0", _res)

    def _get_hasher(self, _algo, _is_hmac, _key):
        _actual_algo = "md5" if _algo.startswith("md5") else _algo
        if _is_hmac:
            return hmac.new(_key, digestmod=_actual_algo)
        return hashlib.new(_actual_algo)

    def _hash_text(self, _data, _algo, _is_hmac, _key):
        _h = self._get_hasher(_algo, _is_hmac, _key)
        _h.update(_data)
        _res = _h.hexdigest()
        if _algo == "md5-16":
            return _res[8:24]
        return _res

    def _hash_file(self, _path, _algo, _is_hmac, _key):
        try:
            _h = self._get_hasher(_algo, _is_hmac, _key)
            with open(_path, "rb") as _f:
                while _chunk := _f.read(8192):
                    _h.update(_chunk)
            _res = _h.hexdigest()
            if _algo == "md5-16":
                return _res[8:24]
            return _res
        except Exception as _e:
            messagebox.showerror("错误", f"计算失败: {str(_e)}", parent=self.root)
            return ""

    def setup_encode_tab(self):
        _frame = ttk.LabelFrame(self.tab_encode, text="输入内容")
        _frame.pack(fill="x", padx=10, pady=5)
        
        _base_style = {
            "highlightthickness": 1,
            "highlightbackground": "#555",
            "highlightcolor": "#007AFF",
            "relief": "flat",
            "bg": "#333",
            "fg": "white",
            "insertbackground": "white"
        }

        self.encode_input = tk.Text(_frame, height=6, font=("Arial", 11), takefocus=False, **_base_style)
        self.encode_input.pack(fill="x", padx=5, pady=5)
        
        _btn_frame = ttk.Frame(self.tab_encode)
        _btn_frame.pack(fill="x", padx=10, pady=5)
        
        _btns = [
            ("Base64 编码", self.b64_encode), ("Base64 解码", self.b64_decode),
            ("URL 编码", self.url_encode), ("URL 解码", self.url_decode),
            ("Unicode 编码", self.unicode_encode), ("Unicode 解码", self.unicode_decode),
            ("HTML 转义", self.html_escape), ("HTML 反转义", self.html_unescape)
        ]
        for _i, (_t, _c) in enumerate(_btns):
            _btn = ttk.Button(_btn_frame, text=_t, command=_c)
            _btn.grid(row=_i//6, column=_i%6, padx=2, pady=2, sticky="ew")
        
        _res_frame = ttk.LabelFrame(self.tab_encode, text="结果")
        _res_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.encode_output = tk.Text(_res_frame, height=8, wrap="char", font=("Courier", 11), **_base_style)
        self.encode_output.pack(fill="both", expand=True, padx=5, pady=5)
        ttk.Button(_res_frame, text="复制结果", command=lambda: self.copy_to_clipboard(self.encode_output.get("1.0", tk.END).strip())).pack(pady=5)
        self.tab_encode.focus_set()

    def b64_encode(self):
        try:
            _res = base64.b64encode(self.encode_input.get("1.0", tk.END).strip().encode()).decode()
            self.set_encode_output(_res)
        except Exception as _e:
            messagebox.showerror("错误", f"编码失败: {str(_e)}", parent=self.root)

    def b64_decode(self):
        try:
            _res = base64.b64decode(self.encode_input.get("1.0", tk.END).strip().encode()).decode()
            self.set_encode_output(_res)
        except Exception:
            messagebox.showerror("错误", "无效的 Base64 内容", parent=self.root)

    def url_encode(self):
        _res = urllib.parse.quote(self.encode_input.get("1.0", tk.END).strip())
        self.set_encode_output(_res)

    def url_decode(self):
        _res = urllib.parse.unquote(self.encode_input.get("1.0", tk.END).strip())
        self.set_encode_output(_res)

    def unicode_encode(self):
        try:
            _res = self.encode_input.get("1.0", tk.END).strip().encode('unicode_escape').decode('ascii')
            self.set_encode_output(_res)
        except Exception as _e:
            messagebox.showerror("错误", f"Unicode 编码失败: {str(_e)}", parent=self.root)

    def unicode_decode(self):
        try:
            _res = self.encode_input.get("1.0", tk.END).strip().encode().decode('unicode_escape')
            self.set_encode_output(_res)
        except Exception as _e:
            messagebox.showerror("错误", f"Unicode 解码失败: {str(_e)}", parent=self.root)

    def html_escape(self):
        _res = html.escape(self.encode_input.get("1.0", tk.END).strip())
        self.set_encode_output(_res)

    def html_unescape(self):
        _res = html.unescape(self.encode_input.get("1.0", tk.END).strip())
        self.set_encode_output(_res)

    def set_encode_output(self, _t):
        self.encode_output.delete("1.0", tk.END)
        self.encode_output.insert("1.0", _t)

    def setup_format_tab(self):
        self.format_mode_tabs = ttk.Notebook(self.tab_format)
        self.fmt_sub_tab_text = ttk.Frame(self.format_mode_tabs)
        self.fmt_sub_tab_file = ttk.Frame(self.format_mode_tabs)
        self.format_mode_tabs.add(self.fmt_sub_tab_text, text="文本模式")
        self.format_mode_tabs.add(self.fmt_sub_tab_file, text="文件模式")
        self.format_mode_tabs.pack(fill="x", padx=10, pady=5)

        _base_style = {
            "highlightthickness": 1,
            "highlightbackground": "#555",
            "highlightcolor": "#007AFF",
            "relief": "flat",
            "bg": "#333",
            "fg": "white",
            "insertbackground": "white"
        }

        self.format_input = tk.Text(self.fmt_sub_tab_text, height=10, font=("Arial", 11), **_base_style)
        self.format_input.pack(fill="x", padx=5, pady=5)
        
        _fmt_op_frame = ttk.Frame(self.fmt_sub_tab_text)
        _fmt_op_frame.pack(fill="x", padx=5)
        ttk.Button(_fmt_op_frame, text="清空输入", command=self.clear_all_format).pack(side="right")

        _fmt_file_frame = ttk.Frame(self.fmt_sub_tab_file)
        _fmt_file_frame.pack(fill="x", padx=5, pady=25)
        ttk.Label(_fmt_file_frame, text="文件路径:").pack(side="left")
        self.format_file_path = ttk.Entry(_fmt_file_frame, font=("Arial", 11))
        self.format_file_path.pack(side="left", padx=5, expand=True, fill="x")
        ttk.Button(_fmt_file_frame, text="选择文件", command=self.select_format_file).pack(side="left")

        _btn_frame = ttk.Frame(self.tab_format)
        _btn_frame.pack(fill="x", padx=10, pady=5)
        
        _btns = [
            ("JSON 格式化", self.json_format), ("JSON 压缩", self.json_compress),
            ("HTML/XML 格式化", self.html_xml_format), ("JS/TS 格式化", self.js_ts_format),
            ("JS/TS 压缩", self.js_ts_compress)
        ]
        for _i, (_t, _c) in enumerate(_btns):
            _btn = ttk.Button(_btn_frame, text=_t, command=_c)
            _btn.grid(row=_i//6, column=_i%6, padx=2, pady=2, sticky="ew")

        _res_frame = ttk.LabelFrame(self.tab_format, text="结果")
        _res_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        _text_container = ttk.Frame(_res_frame)
        _text_container.pack(fill="both", expand=True, padx=5, pady=5)

        self.format_output = tk.Text(_text_container, height=12, wrap="none", font=("Courier", 11), **_base_style)
        _v_scroll = ttk.Scrollbar(_text_container, orient="vertical", command=self.format_output.yview)
        _h_scroll = ttk.Scrollbar(_text_container, orient="horizontal", command=self.format_output.xview)
        self.format_output.configure(xscrollcommand=_h_scroll.set, yscrollcommand=_v_scroll.set)
        
        _v_scroll.pack(side="right", fill="y")
        _h_scroll.pack(side="bottom", fill="x")
        self.format_output.pack(side="left", fill="both", expand=True)
        
        ttk.Button(_res_frame, text="复制结果", command=lambda: self.copy_to_clipboard(self.format_output.get("1.0", tk.END).strip())).pack(pady=5)

    def select_format_file(self):
        _path = filedialog.askopenfilename(parent=self.root)
        if _path:
            self.format_file_path.delete(0, tk.END)
            self.format_file_path.insert(0, _path)
            self.format_mode_tabs.select(1)

    def clear_all_format(self):
        self.format_input.delete("1.0", tk.END)
        self.format_file_path.delete(0, tk.END)
        self.format_output.delete("1.0", tk.END)

    def _get_format_input(self):
        _mode = self.format_mode_tabs.index(self.format_mode_tabs.select())
        if _mode == 0:
            return self.format_input.get("1.0", tk.END).strip()
        else:
            _path = self.format_file_path.get().strip().strip('\"\'')
            if not _path:
                return ""
            if not os.path.isfile(_path):
                messagebox.showerror("错误", "文件路径无效", parent=self.root)
                return None
            try:
                with open(_path, "r", encoding="utf-8") as _f:
                    return _f.read().strip()
            except Exception as _e:
                messagebox.showerror("读取错误", f"无法读取文件: {str(_e)}", parent=self.root)
                return None

    def set_format_output(self, _t):
        self.format_output.delete("1.0", tk.END)
        self.format_output.insert("1.0", _t)

    def json_format(self):
        _data = self._get_format_input()
        if not _data:
            return
        try:
            _obj = json.loads(_data)
            self.set_format_output(json.dumps(_obj, indent=4, ensure_ascii=False))
        except Exception as _e:
            messagebox.showerror("JSON 错误", f"解析失败: {str(_e)}", parent=self.root)

    def json_compress(self):
        _data = self._get_format_input()
        if not _data:
            return
        try:
            _obj = json.loads(_data)
            self.set_format_output(json.dumps(_obj, separators=(',', ':'), ensure_ascii=False))
        except Exception as _e:
            messagebox.showerror("JSON 错误", f"解析失败: {str(_e)}", parent=self.root)

    def html_xml_format(self):
        _data = self._get_format_input()
        if not _data:
            return
        try:
            _is_xml = _data.strip().startswith("<?xml") or "<" in _data and not _data.strip().lower().startswith("<!doctype html")
            _soup = BeautifulSoup(_data, "xml" if _is_xml else "html.parser")
            self.set_format_output(_soup.prettify())
        except Exception as _e:
            messagebox.showerror("格式化错误", f"处理失败: {str(_e)}", parent=self.root)

    def js_ts_format(self):
        _code = self._get_format_input()
        if not _code:
            return
        try:
            _code = _code.replace('{', ' {\n').replace('}', '\n}\n').replace(';', ';\n')
            _code = re.sub(r'\n\s*\n', '\n', _code)
            _lines = _code.split('\n')
            _indent = 0
            _formatted = []
            for _line in _lines:
                _line = _line.strip()
                if not _line:
                    continue
                if _line.startswith('}'):
                    _indent -= 1
                _formatted.append("    " * max(0, _indent) + _line)
                if _line.endswith('{'):
                    _indent += 1
            self.set_format_output('\n'.join(_formatted))
        except Exception as _e:
            messagebox.showerror("格式化错误", f"处理失败: {str(_e)}", parent=self.root)

    def js_ts_compress(self):
        _code = self._get_format_input()
        if not _code:
            return
        try:
            _code = re.sub(r'//.*?\n|/\*.*?\*/', '', _code, flags=re.S)
            _code = re.sub(r'\s+', ' ', _code)
            _code = re.sub(r'\s*([\{\}\(\)\[\];,])\s*', r'\1', _code)
            self.set_format_output(_code.strip())
        except Exception as _e:
            messagebox.showerror("压缩错误", f"处理失败: {str(_e)}", parent=self.root)

    def setup_time_tab(self):
        _tz_values = [f"UTC{_i:+d}" for _i in range(-12, 15)]
        _cur_frame = ttk.LabelFrame(self.tab_time, text="当前时间")
        _cur_frame.pack(fill="x", padx=10, pady=10)
        
        _row1 = ttk.Frame(_cur_frame)
        _row1.pack(fill="x", padx=10, pady=5)
        ttk.Label(_row1, text="显示时区:").pack(side="left")
        self.cur_tz_var = tk.StringVar(value=self.system_tz_str)
        _cb = ttk.Combobox(
            _row1, textvariable=self.cur_tz_var, values=_tz_values, 
            width=8, state="readonly", takefocus=False
        )
        _cb.pack(side="left", padx=5)
        _cb.bind("<<ComboboxSelected>>", lambda _e: self.update_current_ts())
        ttk.Button(_row1, text="刷新", command=self.update_current_ts).pack(side="left", padx=10)
        
        _row2 = ttk.Frame(_cur_frame)
        _row2.pack(fill="x", padx=10, pady=5)
        ttk.Label(_row2, text="当前时间:").pack(side="left")
        self.cur_time_var = tk.StringVar()
        ttk.Entry(_row2, textvariable=self.cur_time_var, state="readonly", font=("Courier", 11, "bold"), width=20).pack(side="left", padx=5)
        ttk.Button(_row2, text="复制", width=6, command=lambda: self.copy_to_clipboard(self.cur_time_var.get())).pack(side="left")
        
        ttk.Label(_row2, text="  时间戳:").pack(side="left", padx=(15, 0))
        self.cur_ts_var = tk.StringVar()
        ttk.Entry(_row2, textvariable=self.cur_ts_var, state="readonly", font=("Courier", 11, "bold"), width=15).pack(side="left", padx=5)
        ttk.Button(_row2, text="复制", width=6, command=lambda: self.copy_to_clipboard(self.cur_ts_var.get())).pack(side="left")

        _t2d_frame = ttk.LabelFrame(self.tab_time, text="时间戳 -> 时间转换 (支持10位的秒、13位的毫秒、10位数字带3位小数的秒)")
        _t2d_frame.pack(fill="x", padx=10, pady=10)
        
        _r_t2d_1 = ttk.Frame(_t2d_frame)
        _r_t2d_1.pack(fill="x", padx=10, pady=2)
        ttk.Label(_r_t2d_1, text="目标时区:").pack(side="left")
        self.t2d_tz_var = tk.StringVar(value=self.system_tz_str)
        ttk.Combobox(_r_t2d_1, textvariable=self.t2d_tz_var, values=_tz_values, width=8, state="readonly").pack(side="left", padx=5)
        self.t2d_ios_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(_r_t2d_1, text="iOS格式 (2001起始)", variable=self.t2d_ios_var).pack(side="left", padx=10)
        
        _r_t2d_2 = ttk.Frame(_t2d_frame)
        _r_t2d_2.pack(fill="x", padx=5, pady=5)
        self.ts_input = ttk.Entry(_r_t2d_2, font=("Arial", 11))
        self.ts_input.pack(side="left", padx=5, expand=True, fill="x")
        ttk.Button(_r_t2d_2, text="转换", command=self.ts_to_date).pack(side="left")
        self.date_output = tk.StringVar()
        ttk.Entry(_r_t2d_2, textvariable=self.date_output, state="readonly", font=("Courier", 11, "bold")).pack(side="left", padx=5, expand=True, fill="x")

        _d2t_frame = ttk.LabelFrame(self.tab_time, text="时间 -> 时间戳转换 (支持带毫秒 .SSS)")
        _d2t_frame.pack(fill="x", padx=10, pady=10)
        
        _r_d2t_1 = ttk.Frame(_d2t_frame)
        _r_d2t_1.pack(fill="x", padx=10, pady=2)
        ttk.Label(_r_d2t_1, text="输入时区:").pack(side="left")
        self.d2t_tz_var = tk.StringVar(value=self.system_tz_str)
        ttk.Combobox(_r_d2t_1, textvariable=self.d2t_tz_var, values=_tz_values, width=8, state="readonly").pack(side="left", padx=5)
        self.d2t_ios_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(_r_d2t_1, text="iOS格式 (2001起始)", variable=self.d2t_ios_var).pack(side="left", padx=10)
        
        _r_d2t_2 = ttk.Frame(_d2t_frame)
        _r_d2t_2.pack(fill="x", padx=5, pady=5)
        self.date_input = ttk.Entry(_r_d2t_2, font=("Arial", 11))
        self.date_input.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.date_input.pack(side="left", padx=5, expand=True, fill="x")
        ttk.Button(_r_d2t_2, text="转换", command=self.date_to_ts).pack(side="left")
        self.ts_output = tk.StringVar()
        ttk.Entry(_r_d2t_2, textvariable=self.ts_output, state="readonly", font=("Courier", 11, "bold")).pack(side="left", padx=5, expand=True, fill="x")
        
        self.update_current_ts()
        self.tab_time.focus_set()

    def _get_tz(self, _var):
        _offset = int(_var.get().replace("UTC", ""))
        return timezone(timedelta(hours=_offset))

    def update_current_ts(self):
        _now = time.time()
        _now_ms = int(_now * 1000)
        self.cur_ts_var.set(str(_now_ms))
        self.cur_time_var.set(
            datetime.fromtimestamp(_now, tz=self._get_tz(self.cur_tz_var)).strftime("%Y-%m-%d %H:%M:%S")
        )

    def ts_to_date(self):
        try:
            _input_str = self.ts_input.get().strip()
            _ts = float(_input_str)
            if self.t2d_ios_var.get():
                _ts += self.APPLE_OFFSET
            _show_ms = False
            if _ts > 10**11:
                _ts /= 1000.0
                _show_ms = True
            elif "." in _input_str:
                _show_ms = True
            _dt = datetime.fromtimestamp(_ts, tz=self._get_tz(self.t2d_tz_var))
            if _show_ms:
                _res = _dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            else:
                _res = _dt.strftime("%Y-%m-%d %H:%M:%S")
            self.date_output.set(_res)
        except Exception:
            messagebox.showerror("错误", "无效的时间戳格式", parent=self.root)

    def date_to_ts(self):
        try:
            _dt_str = self.date_input.get().strip()
            _fmt = "%Y-%m-%d %H:%M:%S.%f" if "." in _dt_str else "%Y-%m-%d %H:%M:%S"
            _dt = datetime.strptime(_dt_str, _fmt)
            _unix_ts = _dt.replace(tzinfo=self._get_tz(self.d2t_tz_var)).timestamp()
            if self.d2t_ios_var.get():
                _unix_ts -= self.APPLE_OFFSET
                _res = f"{_unix_ts:.3f}".rstrip('0').rstrip('.')
            else:
                if "." in _dt_str:
                    _res = str(int(_unix_ts * 1000))
                else:
                    _res = str(int(_unix_ts))
            self.ts_output.set(_res)
        except Exception:
            messagebox.showerror("错误", "日期时间格式不正确", parent=self.root)

    def copy_to_clipboard(self, _t):
        self.root.clipboard_clear()
        self.root.clipboard_append(_t)

if __name__ == "__main__":
    root = tk.Tk()
    app = ToolApp(root)
    root.mainloop()
