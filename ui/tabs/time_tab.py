# -*- coding: utf-8 -*-
# Author: sens
# Date: 2026/05/12 14:20

import tkinter as tk
from tkinter import ttk, messagebox
import time
from datetime import datetime
from utils.common import get_system_tz_str, get_timezone_from_var, copy_to_clipboard

class TimeTab:
    """时间戳转换标签页"""
    def __init__(self, parent, root):
        self.parent = parent
        self.root = root
        self.APPLE_OFFSET = 978307200
        
        # UI 变量
        self.cur_tz_var = tk.StringVar(value=get_system_tz_str())
        self.cur_time_var = tk.StringVar()
        self.cur_ts_var = tk.StringVar()
        
        self.ts_input = None
        self.date_output = tk.StringVar()
        self.t2d_tz_var = tk.StringVar(value=get_system_tz_str())
        self.t2d_ios_var = tk.BooleanVar(value=False)
        
        self.date_input = None
        self.ts_output = tk.StringVar()
        self.d2t_tz_var = tk.StringVar(value=get_system_tz_str())
        self.d2t_ios_var = tk.BooleanVar(value=False)
        
        self._setup_ui()
        self.update_clock()

    def _setup_ui(self):
        tz_values = [f"UTC{i:+d}" for i in range(-12, 15)]
        
        # 1. 当前时间面板
        cur_frame = ttk.LabelFrame(self.parent, text="当前时间")
        cur_frame.pack(fill="x", padx=10, pady=10)
        
        row1 = ttk.Frame(cur_frame)
        row1.pack(fill="x", padx=10, pady=5)
        ttk.Label(row1, text="显示时区:").pack(side="left")
        cb = ttk.Combobox(row1, textvariable=self.cur_tz_var, values=tz_values, width=8, state="readonly")
        cb.pack(side="left", padx=5)
        ttk.Button(row1, text="刷新", command=self.update_clock).pack(side="left", padx=10)
        
        row2 = ttk.Frame(cur_frame)
        row2.pack(fill="x", padx=10, pady=5)
        ttk.Label(row2, text="当前时间:").pack(side="left")
        ttk.Entry(row2, textvariable=self.cur_time_var, state="readonly", font=("Courier", 11, "bold"), width=20).pack(side="left", padx=5)
        ttk.Button(row2, text="复制", width=6, command=lambda: copy_to_clipboard(self.root, self.cur_time_var.get())).pack(side="left")
        
        ttk.Label(row2, text="  时间戳:").pack(side="left", padx=(15, 0))
        ttk.Entry(row2, textvariable=self.cur_ts_var, state="readonly", font=("Courier", 11, "bold"), width=15).pack(side="left", padx=5)
        ttk.Button(row2, text="复制", width=6, command=lambda: copy_to_clipboard(self.root, self.cur_ts_var.get())).pack(side="left")

        # 2. 时间戳 -> 时间
        t2d_frame = ttk.LabelFrame(self.parent, text="时间戳 -> 时间转换")
        t2d_frame.pack(fill="x", padx=10, pady=10)
        
        r1 = ttk.Frame(t2d_frame)
        r1.pack(fill="x", padx=10, pady=2)
        ttk.Label(r1, text="目标时区:").pack(side="left")
        ttk.Combobox(r1, textvariable=self.t2d_tz_var, values=tz_values, width=8, state="readonly").pack(side="left", padx=5)
        ttk.Checkbutton(r1, text="iOS格式 (2001起始)", variable=self.t2d_ios_var).pack(side="left", padx=10)
        
        r2 = ttk.Frame(t2d_frame)
        r2.pack(fill="x", padx=5, pady=5)
        self.ts_input = ttk.Entry(r2, font=("Arial", 11))
        self.ts_input.pack(side="left", padx=5, expand=True, fill="x")
        ttk.Button(r2, text="转换", command=self.ts_to_date).pack(side="left")
        ttk.Entry(r2, textvariable=self.date_output, state="readonly", font=("Courier", 11, "bold")).pack(side="left", padx=5, expand=True, fill="x")

        # 3. 时间 -> 时间戳
        d2t_frame = ttk.LabelFrame(self.parent, text="时间 -> 时间戳转换")
        d2t_frame.pack(fill="x", padx=10, pady=10)
        
        r3 = ttk.Frame(d2t_frame)
        r3.pack(fill="x", padx=10, pady=2)
        ttk.Label(r3, text="输入时区:").pack(side="left")
        ttk.Combobox(r3, textvariable=self.d2t_tz_var, values=tz_values, width=8, state="readonly").pack(side="left", padx=5)
        ttk.Checkbutton(r3, text="iOS格式 (2001起始)", variable=self.d2t_ios_var).pack(side="left", padx=10)
        
        r4 = ttk.Frame(d2t_frame)
        r4.pack(fill="x", padx=5, pady=5)
        self.date_input = ttk.Entry(r4, font=("Arial", 11))
        self.date_input.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.date_input.pack(side="left", padx=5, expand=True, fill="x")
        ttk.Button(r4, text="转换", command=self.date_to_ts).pack(side="left")
        ttk.Entry(r4, textvariable=self.ts_output, state="readonly", font=("Courier", 11, "bold")).pack(side="left", padx=5, expand=True, fill="x")

    def update_clock(self):
        now = time.time()
        self.cur_ts_var.set(str(int(now * 1000)))
        tz = get_timezone_from_var(self.cur_tz_var)
        self.cur_time_var.set(datetime.fromtimestamp(now, tz=tz).strftime("%Y-%m-%d %H:%M:%S"))

    def ts_to_date(self):
        try:
            val = self.ts_input.get().strip()
            ts = float(val)
            if self.t2d_ios_var.get(): ts += self.APPLE_OFFSET
            show_ms = False
            if ts > 10**11: # 毫秒
                ts /= 1000.0
                show_ms = True
            elif "." in val: show_ms = True
            
            tz = get_timezone_from_var(self.t2d_tz_var)
            dt = datetime.fromtimestamp(ts, tz=tz)
            fmt = "%Y-%m-%d %H:%M:%S.%f" if show_ms else "%Y-%m-%d %H:%M:%S"
            res = dt.strftime(fmt)
            self.date_output.set(res[:-3] if show_ms else res)
        except Exception:
            messagebox.showerror("错误", "无效的时间戳格式")

    def date_to_ts(self):
        try:
            dt_str = self.date_input.get().strip()
            fmt = "%Y-%m-%d %H:%M:%S.%f" if "." in dt_str else "%Y-%m-%d %H:%M:%S"
            dt = datetime.strptime(dt_str, fmt)
            tz = get_timezone_from_var(self.d2t_tz_var)
            unix_ts = dt.replace(tzinfo=tz).timestamp()
            
            if self.d2t_ios_var.get():
                unix_ts -= self.APPLE_OFFSET
                self.ts_output.set(f"{unix_ts:.3f}".rstrip('0').rstrip('.'))
            else:
                self.ts_output.set(str(int(unix_ts * 1000)) if "." in dt_str else str(int(unix_ts)))
        except Exception:
            messagebox.showerror("错误", "日期格式不正确")
