# -*- coding: utf-8 -*-
# Author: sens
# Date: 2026/05/11 13:10

import tkinter as tk
from tkinter import ttk
import os
import sys
from ui.styles import StyleManager
from ui.tabs.hash_tab import HashTab
from ui.tabs.encode_tab import EncodeTab
from ui.tabs.format_tab import FormatTab
from ui.tabs.time_tab import TimeTab
from ui.tabs.image_tab import ImageTab

class DeveloperToolsApp:
    """主程序类：负责窗口初始化 and 功能分发"""
    def __init__(self, root):
        self.root = root
        self.root.title("开发者工具")

        # 设置窗口图标
        self._set_app_icon()

        self._center_window(880, 700)
        self.style = StyleManager.setup_styles(self.root)
        
        # 创建 Notebook 并设置顶部边距
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill="both", pady=(10, 0))

        self._init_tabs()

    def _set_app_icon(self):
        """设置应用程序图标"""
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "images", "app.png")
            if os.path.exists(icon_path):
                full_icon = tk.PhotoImage(file=icon_path)
                self.icon = full_icon.subsample(32, 32)
                self.root.iconphoto(True, self.icon)
                
                if sys.platform == 'darwin':
                    try:
                        from AppKit import NSApp, NSImage
                        image = NSImage.alloc().initByReferencingFile_(icon_path)
                        NSApp.setApplicationIconImage_(image)
                    except ImportError:
                        pass
        except Exception:
            pass

    def _center_window(self, width, height):
        """计算并设置窗口在屏幕中央"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _init_tabs(self):
        """初始化并添加所有功能标签页"""
        tab_list = [
            (HashTab,   "哈希计算"),
            (EncodeTab, "编码转换"),
            (FormatTab, "格式化"),
            (TimeTab,   "日期时间"),
            (ImageTab,  "图片处理")
        ]
        
        for tab_class, tab_label in tab_list:
            frame = ttk.Frame(self.notebook)
            self.notebook.add(frame, text=tab_label)
            tab_class(frame, self.root)

# pip freeze > requirements.txt
# pip install -r requirements.txt
# pip install pyinstaller
# git tag v1.0.0
# git push origin v1.0.0
if __name__ == "__main__":
    _root = tk.Tk()
    app = DeveloperToolsApp(_root)
    _root.mainloop()
