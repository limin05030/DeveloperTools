# -*- coding: utf-8 -*-
"""嵌入式原生浏览器 — 按平台分派"""

import sys

if sys.platform == 'darwin':
    from backend.embedded_browser._darwin import EmbeddedBrowser, get_embedded_browser  # noqa
elif sys.platform.startswith('linux'):
    from backend.embedded_browser._linux import EmbeddedBrowser, get_embedded_browser  # noqa
elif sys.platform == 'win32':
    from backend.embedded_browser._win32 import EmbeddedBrowser, get_embedded_browser  # noqa
else:
    from backend.embedded_browser._dummy import EmbeddedBrowser, get_embedded_browser  # noqa
