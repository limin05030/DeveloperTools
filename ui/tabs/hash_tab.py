# -*- coding: utf-8 -*-
# Author: sens
# Date: 2026/05/12 16:12

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import hashlib
import hmac
import os
from ui.styles import StyleManager
from utils.common import copy_to_clipboard

class HashTab:
    """哈希计算标签页：支持标准哈希和 HMAC 计算"""
    def __init__(self, parent, root):
        self.parent = parent
        self.root = root
        
        # UI 变量
        self.hash_mode_tabs = None
        self.hash_text_input = None
        self.hash_file_path = None
        self.hash_key = None
        self.hash_output = None
        
        self._setup_ui()

    def _setup_ui(self):
        # 模式切换：文本 vs 文件
        self.hash_mode_tabs = ttk.Notebook(self.parent)
        sub_tab_text = ttk.Frame(self.hash_mode_tabs)
        sub_tab_file = ttk.Frame(self.hash_mode_tabs)
        self.hash_mode_tabs.add(sub_tab_text, text="文本模式")
        self.hash_mode_tabs.add(sub_tab_file, text="文件模式")
        self.hash_mode_tabs.pack(fill="x", padx=0, pady=5)

        text_style = StyleManager.get_text_area_style()

        # 文本输入区
        self.hash_text_input = tk.Text(sub_tab_text, height=5, **text_style)
        self.hash_text_input.pack(fill="x", padx=5, pady=5)

        # 文件选择区
        file_frame = ttk.Frame(sub_tab_file)
        file_frame.pack(fill="x", padx=5, pady=10)
        ttk.Label(file_frame, text="文件路径:").pack(side="left")
        self.hash_file_path = ttk.Entry(file_frame, font=("Arial", 11))
        self.hash_file_path.pack(side="left", padx=5, expand=True, fill="x")
        ttk.Button(file_frame, text="选择文件", command=self.select_file).pack(side="left")

        # 算法按钮区
        algo_frame = ttk.Frame(self.parent)
        algo_frame.pack(fill="x", padx=10, pady=5)
        
        # 标准哈希
        sh_frame = ttk.LabelFrame(algo_frame, text="标准哈希 (Standard Hash)")
        sh_frame.pack(fill="x", pady=5)
        sh_btns = [
            ("MD5-16", "md5-16"), ("MD5-32", "md5-32"), ("SHA-1", "sha1"), ("SHA-224", "sha224"),
            ("SHA-256", "sha256"), ("SHA-384", "sha384"), ("SHA-512", "sha512"), ("SHA3-224", "sha3_224"),
            ("SHA3-256", "sha3_256"), ("SHA3-384", "sha3_384"), ("SHA3-512", "sha3_512")
        ]
        for i, (t, a) in enumerate(sh_btns):
            btn = ttk.Button(sh_frame, text=t, width=9, command=lambda algo=a: self.do_calc(algo, False))
            btn.grid(row=i//6, column=i%6, padx=5, pady=5)

        # HMAC
        hmac_frame = ttk.LabelFrame(algo_frame, text="HMAC 计算 (Keyed Hash)")
        hmac_frame.pack(fill="x", pady=5)
        
        key_row = ttk.Frame(hmac_frame)
        key_row.pack(fill="x", padx=10, pady=5)
        ttk.Label(key_row, text="HMAC 密钥 (Key):").pack(side="left")
        self.hash_key = ttk.Entry(key_row, font=("Arial", 11))
        self.hash_key.pack(side="left", padx=10, expand=True, fill="x")
        
        hmac_btns_frame = ttk.Frame(hmac_frame)
        hmac_btns_frame.pack(fill="x", padx=5, pady=5)
        hmac_btns = [
            ("HmacMD5", "md5"), ("HmacSHA1", "sha1"), ("HmacSHA256", "sha256"),
            ("HmacSHA512", "sha512"), ("HmacSHA3-256", "sha3_256"), ("HmacRIPEMD160", "ripemd160")
        ]
        for i, (t, a) in enumerate(hmac_btns):
            btn = ttk.Button(hmac_btns_frame, text=t, width=14, command=lambda algo=a: self.do_calc(algo, True))
            btn.grid(row=i//4, column=i%4, padx=5, pady=5)

        # 结果展示区
        res_frame = ttk.LabelFrame(self.parent, text="计算结果")
        res_frame.pack(fill="both", expand=True, padx=10, pady=5)
        res_style = text_style.copy()
        res_style.update({"font": ("Courier", 11, "bold"), "height": 4})
        self.hash_output = tk.Text(res_frame, wrap="char", **res_style)
        self.hash_output.pack(fill="both", expand=True, padx=5, pady=5)
        
        op_frame = ttk.Frame(res_frame)
        op_frame.pack(fill="x", padx=5, pady=5)
        ttk.Button(op_frame, text="复制结果", command=lambda: copy_to_clipboard(self.root, self.hash_output.get("1.0", tk.END).strip())).pack(side="left", padx=5)
        ttk.Button(op_frame, text="大小写切换", command=self.toggle_case).pack(side="left", padx=5)
        ttk.Button(op_frame, text="清空全部", command=self.clear_all).pack(side="left", padx=5)

    def select_file(self):
        path = filedialog.askopenfilename(parent=self.root)
        if path:
            self.hash_file_path.delete(0, tk.END)
            self.hash_file_path.insert(0, path)

    def clear_all(self):
        self.hash_text_input.delete("1.0", tk.END)
        self.hash_file_path.delete(0, tk.END)
        self.hash_key.delete(0, tk.END)
        self.hash_output.delete("1.0", tk.END)

    def toggle_case(self):
        content = self.hash_output.get("1.0", tk.END).strip()
        if content:
            res = content.lower() if content.isupper() else content.upper()
            self.hash_output.delete("1.0", tk.END)
            self.hash_output.insert("1.0", res)

    def do_calc(self, algo_name, is_hmac):
        mode = self.hash_mode_tabs.index(self.hash_mode_tabs.select())
        key = self.hash_key.get().encode()
        
        if mode == 0:
            data = self.hash_text_input.get("1.0", tk.END).strip().encode("utf-8")
            if not data: return
            res = self._calc_hash(data, algo_name, is_hmac, key)
        else:
            path = self.hash_file_path.get().strip().strip("\"'\"")
            if not os.path.isfile(path):
                messagebox.showerror("错误", "文件路径无效", parent=self.root)
                return
            res = self._calc_file_hash(path, algo_name, is_hmac, key)
        
        if res:
            self.hash_output.delete("1.0", tk.END)
            self.hash_output.insert("1.0", res)

    def _calc_hash(self, data, algo, is_hmac, key):
        actual_algo = "md5" if algo.startswith("md5") else algo
        h = hmac.new(key, digestmod=actual_algo) if is_hmac else hashlib.new(actual_algo)
        h.update(data)
        res = h.hexdigest()
        return res[8:24] if algo == "md5-16" else res

    def _calc_file_hash(self, path, algo, is_hmac, key):
        try:
            actual_algo = "md5" if algo.startswith("md5") else algo
            h = hmac.new(key, digestmod=actual_algo) if is_hmac else hashlib.new(actual_algo)
            with open(path, "rb") as f:
                while chunk := f.read(8192):
                    h.update(chunk)
            res = h.hexdigest()
            return res[8:24] if algo == "md5-16" else res
        except Exception as e:
            messagebox.showerror("错误", f"计算失败: {str(e)}", parent=self.root)
            return ""
