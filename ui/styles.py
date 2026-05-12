# -*- coding: utf-8 -*-
# Author: sens
# Date: 2026/05/11 13:10

from tkinter import ttk

class StyleManager:
    """管理全局 UI 样式和主题"""
    
    @staticmethod
    def setup_styles(root):
        style = ttk.Style()
        
        # 针对 macOS 强制使用 aqua 主题以保证一致性
        if root.tk.call('tk', 'windowingsystem') == 'aqua':
            style.theme_use('aqua')
            
        # 配置自定义样式
        style.configure("TLabelframe.Label", font=("Arial", 11, "bold"), foreground="white")
        style.configure("TLabel", font=("Arial", 10), foreground="white")
        style.configure("TButton", font=("Arial", 10))
        style.configure("TCheckbutton", font=("Arial", 10), foreground="white")
        
        # 统一 Entry 和 Combobox 在深色模式下的基础色调
        style.configure("TEntry", fieldbackground="#333", bordercolor="#555")
        style.configure("TCombobox", fieldbackground="#333", bordercolor="#555")
        
        # 配置焦点颜色映射
        style.map("TEntry", 
                  bordercolor=[("focus", "#007AFF")], 
                  lightcolor=[("focus", "#007AFF")], 
                  darkcolor=[("focus", "#007AFF")])
        style.map("TCombobox", 
                  bordercolor=[("focus", "#007AFF")], 
                  lightcolor=[("focus", "#007AFF")], 
                  darkcolor=[("focus", "#007AFF")])
        
        return style

    @staticmethod
    def get_text_area_style():
        """返回 Text 组件的基础样式字典"""
        return {
            "highlightthickness": 1,
            "highlightbackground": "#555",
            "highlightcolor": "#007AFF",
            "relief": "flat",
            "bg": "#333",
            "fg": "white",
            "insertbackground": "white",
            "font": ("Arial", 11)
        }
