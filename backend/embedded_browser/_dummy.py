# -*- coding: utf-8 -*-
"""嵌入式浏览器占位实现（不支持的平台）"""


class EmbeddedBrowser:
    def show_tab(self, tab_id, url=None):
        return False

    def hide(self):
        pass

    def go_back(self):
        return False

    def go_forward(self):
        return False

    def reload(self):
        return False


_embedded_browser = None


def get_embedded_browser():
    global _embedded_browser
    if _embedded_browser is None:
        _embedded_browser = EmbeddedBrowser()
    return _embedded_browser
