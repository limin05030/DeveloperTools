# -*- coding: utf-8 -*-
# Author: sens
# Date: 2026/05/11 13:10

import tkinter as tk
from ui.app import DeveloperToolsApp


# pip freeze > requirements.txt
# pip install -r requirements.txt
# pip install pyinstaller
# git tag v1.0.0
# git push origin v1.0.0
if __name__ == "__main__":
    _root = tk.Tk()
    app = DeveloperToolsApp(_root)
    _root.mainloop()
