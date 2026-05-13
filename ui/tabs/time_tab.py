# -*- coding: utf-8 -*-
import wx
import time
from datetime import datetime, timezone, timedelta
from ui.tabs.base_tab import BaseTab
from ui.styles import ThemeManager
from utils.common import get_system_tz_str

class TimeTab(BaseTab):

    def __init__(self, parent):
        super(TimeTab, self).__init__(parent)
        self.APPLE_OFFSET = 978307200
        self.cur_tz_cb = None
        self.cur_time_ctrl = None
        self.cur_ts_ctrl = None
        self.ts_input = None
        self.date_output = None
        self.t2d_tz_cb = None
        self.t2d_ios_chk = None
        self.date_input = None
        self.ts_output = None
        self.d2t_tz_cb = None
        self.d2t_ios_chk = None
        
        self._init_ui()
        self._on_update_clock(None)
        ThemeManager.apply_theme(self)

    def _init_ui(self):
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        tz_values = [f"UTC{i:+d}" for i in range(-12, 15)]

        # 当前时间
        cur_card, cur_content = self._create_card_sizer(self, "当前时间戳")
        r1 = wx.BoxSizer(wx.HORIZONTAL)
        r1.Add(self._create_label(self, "时区:"), 0, wx.CENTER | wx.RIGHT, 10)
        self.cur_tz_cb = wx.ComboBox(self, value=get_system_tz_str(), choices=tz_values, style=wx.CB_READONLY)
        r1.Add(self.cur_tz_cb, 0, wx.CENTER)
        refresh_btn = wx.Button(self, label="刷新", size=wx.Size(80, 32))
        refresh_btn.Bind(wx.EVT_BUTTON, self._on_update_clock)
        r1.Add(refresh_btn, 0, wx.LEFT, 15)
        cur_content.Add(r1, 0, wx.EXPAND | wx.BOTTOM, 15)
        
        r2 = wx.BoxSizer(wx.HORIZONTAL)
        r2.Add(self._create_label(self, "本地时间:"), 0, wx.CENTER | wx.RIGHT, 10)
        # 移除固定高度，由 Sizer 的 wx.CENTER 处理垂直居中
        self.cur_time_ctrl = wx.TextCtrl(self, style=wx.TE_READONLY, size=wx.Size(220, -1))
        self.cur_time_ctrl.SetFont(ThemeManager.get_mono_font(12))
        r2.Add(self.cur_time_ctrl, 0, wx.CENTER)
        copy_t_btn = wx.Button(self, label="复制", size=wx.Size(60, 32))
        copy_t_btn.Bind(wx.EVT_BUTTON, lambda e: self._on_copy(self.cur_time_ctrl))
        r2.Add(copy_t_btn, 0, wx.LEFT | wx.CENTER, 10)
        
        r2.AddSpacer(30)
        r2.Add(self._create_label(self, "时间戳:"), 0, wx.CENTER | wx.RIGHT, 10)
        self.cur_ts_ctrl = wx.TextCtrl(self, style=wx.TE_READONLY, size=wx.Size(140, -1))
        self.cur_ts_ctrl.SetFont(ThemeManager.get_mono_font(12))
        r2.Add(self.cur_ts_ctrl, 0, wx.CENTER)
        copy_ts_btn = wx.Button(self, label="复制", size=wx.Size(60, 32))
        copy_ts_btn.Bind(wx.EVT_BUTTON, lambda e: self._on_copy(self.cur_ts_ctrl))
        r2.Add(copy_ts_btn, 0, wx.LEFT | wx.CENTER, 10)
        cur_content.Add(r2, 0, wx.EXPAND | wx.BOTTOM, 15)
        main_sizer.Add(cur_card, 0, wx.EXPAND | wx.ALL, 15)

        # 转换器
        panels_cfg = [
            ("时间戳 转 日期", "转换", self._on_ts_to_date, "ts_input", "date_output", "t2d_tz_cb", "t2d_ios_chk"),
            ("日期 转 时间戳", "转换", self._on_date_to_ts, "date_input", "ts_output", "d2t_tz_cb", "d2t_ios_chk")
        ]

        for label, btn_lbl, handler, input_attr, output_attr, tz_attr, ios_attr in panels_cfg:
            card, content = self._create_card_sizer(self, label)

            r_top = wx.BoxSizer(wx.HORIZONTAL)
            r_top.Add(self._create_label(self, "时区:"), 0, wx.CENTER | wx.RIGHT, 10)

            cb = wx.ComboBox(self, value=get_system_tz_str(), choices=tz_values, style=wx.CB_READONLY)
            setattr(self, tz_attr, cb)
            r_top.Add(cb, 0, wx.CENTER)

            chk = wx.CheckBox(self, label="iOS 格式 (自 2001 年起)")
            setattr(self, ios_attr, chk)
            r_top.Add(chk, 0, wx.CENTER | wx.LEFT, 25)
            content.Add(r_top, 0, wx.EXPAND | wx.BOTTOM, 10)

            r_mid = wx.BoxSizer(wx.HORIZONTAL)

            in_ctrl = wx.TextCtrl(self)
            setattr(self, input_attr, in_ctrl)
            r_mid.Add(in_ctrl, 1, wx.CENTER | wx.RIGHT, 10)

            btn = wx.Button(self, label=btn_lbl, size=wx.Size(80, 36))
            btn.Bind(wx.EVT_BUTTON, handler)
            r_mid.Add(btn, 0, wx.CENTER | wx.RIGHT, 10)

            out_ctrl = wx.TextCtrl(self, style=wx.TE_READONLY)
            out_ctrl.SetFont(ThemeManager.get_mono_font(12))
            setattr(self, output_attr, out_ctrl)
            r_mid.Add(out_ctrl, 1, wx.CENTER | wx.RIGHT, 20)

            content.Add(r_mid, 0, wx.EXPAND | wx.BOTTOM, 10)
            main_sizer.Add(card, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 15)

        self.date_input.SetValue(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.SetSizer(main_sizer)

    def _on_update_clock(self, e):
        now = time.time()
        self.cur_ts_ctrl.SetValue(str(int(now * 1000)))
        tz_str = self.cur_tz_cb.GetValue()
        offset = int(tz_str.replace("UTC", ""))
        tz = timezone(timedelta(hours=offset))
        dt_str = datetime.fromtimestamp(now, tz=tz).strftime("%Y-%m-%d %H:%M:%S.%f")
        self.cur_time_ctrl.SetValue(dt_str[:-3])

    def _on_copy(self, ctrl):
        val = ctrl.GetValue().strip()
        if val and wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(val))
            wx.TheClipboard.Close()

    def _on_ts_to_date(self, e):
        def _conv():
            val = self.ts_input.GetValue().strip()
            ts = float(val)
            if self.t2d_ios_chk.IsChecked(): ts += self.APPLE_OFFSET
            show_ms = ts > 10**11 or "." in val
            if ts > 10**11: ts /= 1000.0
            tz_str = self.t2d_tz_cb.GetValue()
            offset = int(tz_str.replace("UTC", ""))
            tz = timezone(timedelta(hours=offset))
            dt = datetime.fromtimestamp(ts, tz=tz)
            fmt = "%Y-%m-%d %H:%M:%S.%f" if show_ms else "%Y-%m-%d %H:%M:%S"
            res = dt.strftime(fmt)
            return res[:-3] if show_ms else res
        self._safe_exec(_conv, self.date_output)

    def _on_date_to_ts(self, e):
        def _conv():
            dt_str = self.date_input.GetValue().strip()
            fmt = "%Y-%m-%d %H:%M:%S.%f" if "." in dt_str else "%Y-%m-%d %H:%M:%S"
            dt = datetime.strptime(dt_str, fmt)
            tz_str = self.d2t_tz_cb.GetValue()
            offset = int(tz_str.replace("UTC", ""))
            tz = timezone(timedelta(hours=offset))
            unix_ts = dt.replace(tzinfo=tz).timestamp()
            if self.d2t_ios_chk.IsChecked():
                unix_ts -= self.APPLE_OFFSET
                return f"{unix_ts:.3f}".rstrip('0').rstrip('.')
            else:
                return str(int(unix_ts * 1000)) if "." in dt_str else str(int(unix_ts))
        self._safe_exec(_conv, self.ts_output)
