# -*- coding: utf-8 -*-
# Author: sens
# Date: 2026/05/11 13:10

import time
from datetime import timezone, timedelta

def get_system_tz_str():
    """获取系统当前时区的字符串表示，如 UTC+8"""
    offset_sec = -time.timezone if (time.localtime().tm_isdst == 0) else -time.altzone
    return f"UTC{int(offset_sec / 3600):+d}"

def get_timezone_from_var(tz_var):
    """根据变量内容返回 timezone 对象"""
    try:
        offset = int(tz_var.get().replace("UTC", ""))
        return timezone(timedelta(hours=offset))
    except ValueError:
        return timezone.utc

def copy_to_clipboard(root, text):
    """将文本复制到系统剪贴板"""
    root.clipboard_clear()
    root.clipboard_append(text)
