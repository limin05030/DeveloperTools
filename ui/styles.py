# -*- coding: utf-8 -*-
# Author: sens
# Date: 2026/05/11 13:10

from tkinter import ttk

class StyleManager:
    """管理全局 UI 样式和主题"""
    
    @staticmethod
    def setup_styles(root):
        style = ttk.Style()
        
        # 定义全局深色调
        bg_color = "#2b2b2b"      # 主背景（深灰色）
        fg_color = "#e0e0e0"      # 主文字
        input_bg = "#333333"      # 输入框背景
        border_color = "#2b2b2b"  # 边框色
        accent_color = "#007AFF"  # 强调色（蓝）
        tab_bg = "#3c3c3c"        # 未选中标签页背景

        # 1. 强制设置根窗口背景色
        root.configure(bg=bg_color)
        
        # 2. 尝试使用基础主题
        if root.tk.call('tk', 'windowingsystem') == 'aqua':
            style.theme_use('aqua')
            
        # 3. 配置通用组件样式
        style.configure(".", 
                        background=bg_color, 
                        foreground=fg_color, 
                        troughcolor=bg_color, 
                        focuscolor=accent_color,
                        font=("Arial", 10))
        
        # Frame
        style.configure("TFrame", background=bg_color)
        
        # Notebook (标签页控件)
        style.configure("TNotebook", 
                        background=bg_color, 
                        borderwidth=0, 
                        lightcolor=bg_color, 
                        darkcolor=bg_color)
        
        style.configure("TNotebook.Tab", 
                        background=tab_bg, 
                        foreground=fg_color, 
                        padding=[12, 4], 
                        font=("Arial", 10))
        
        # 选中的标签页背景设为与主背景一致
        style.map("TNotebook.Tab", 
                  background=[("selected", bg_color), ("active", "#444")],
                  foreground=[("selected", "#ffffff")])
        
        # Label & LabelFrame
        style.configure("TLabel", background=bg_color, foreground=fg_color)
        style.configure("TLabelframe", background=bg_color, foreground=fg_color, bordercolor="#404040")
        style.configure("TLabelframe.Label", background=bg_color, foreground=fg_color, font=("Arial", 11, "bold"))
        
        # Scale (滑块) - 针对 ttk.Scale 的全局配置
        style.configure("TScale", 
                        background=bg_color, 
                        troughcolor="#404040", 
                        sliderlength=20, 
                        borderwidth=0)
        
        # Button
        style.configure("TButton", padding=[5, 2])
        
        # Checkbutton
        style.configure("TCheckbutton", background=bg_color, foreground=fg_color)
        
        # Entry & Combobox
        style.configure("TEntry", fieldbackground=input_bg, foreground=fg_color, insertcolor="white")
        style.configure("TCombobox", fieldbackground=input_bg, foreground=fg_color, arrowcolor=fg_color)
        style.map("TCombobox", fieldbackground=[("readonly", input_bg)])
        
        return style

    @staticmethod
    def get_text_area_style():
        """返回 Text 组件的基础样式字典"""
        return {
            "highlightthickness": 1,
            "highlightbackground": "#404040",
            "highlightcolor": "#007AFF",
            "relief": "flat",
            "bg": "#333333",
            "fg": "#e0e0e0",
            "insertbackground": "white",
            "font": ("Arial", 11),
            "padx": 5,
            "pady": 5
        }
