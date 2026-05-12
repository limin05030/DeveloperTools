# -*- coding: utf-8 -*-
# Author: sens
# Date: 2026/05/11 13:10

import tkinter as tk
from tkinter import ttk
from ui.styles import StyleManager
from ui.tabs.hash_tab import HashTab
from ui.tabs.encode_tab import EncodeTab
from ui.tabs.format_tab import FormatTab
from ui.tabs.time_tab import TimeTab

class DeveloperToolsApp:
    """主程序类：负责窗口初始化和功能分发"""
    def __init__(self, root):
        self.root = root
        self.root.title("开发者工具")
        
        # 1. 窗口布局与居中
        self._center_window(880, 700)
        
        # 2. 初始化样式
        self.style = StyleManager.setup_styles(self.root)
        
        # 3. 初始化主标签页容器
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill="both")
        
        # 4. 加载各个功能模块
        self._init_tabs()

    def _center_window(self, width, height):
        """计算并设置窗口在屏幕中央"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _init_tabs(self):
        """初始化并添加所有功能标签页"""
        # 定义标签页信息：(类名, 显示文本)
        tab_list = [
            (HashTab, "哈希计算"),
            (EncodeTab, "编码转换"),
            (FormatTab, "格式化"),
            (TimeTab, "日期时间")
        ]
        
        for tab_class, tab_label in tab_list:
            frame = ttk.Frame(self.notebook)
            self.notebook.add(frame, text=tab_label)
            # 实例化具体的功能类
            tab_class(frame, self.root)

# pip freeze > requirements.txt
# pip install -r requirements.txt
# pip install pyinstaller
# git tag v1.0.0
# git push origin v1.0.0
if __name__ == "__main__":
    # 创建主窗口
    _root = tk.Tk()
    # 启动应用
    app = DeveloperToolsApp(_root)
    # 进入事件循环
    _root.mainloop()
