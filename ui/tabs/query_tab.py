# -*- coding: utf-8 -*-
import wx
import wx.lib.mixins.listctrl as listmix
from ui.tabs.base_tab import BaseTab
from ui.styles import ThemeManager

class AsciiListCtrl(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin):
    def __init__(self, parent, ID, pos=wx.DefaultPosition, size=wx.DefaultSize, style=0):
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        listmix.ListCtrlAutoWidthMixin.__init__(self)

class QueryTab(BaseTab):
    def __init__(self, parent):
        super(QueryTab, self).__init__(parent)
        self.ascii_list = None
        self._init_ui()
        ThemeManager.apply_theme(self)

    def _init_ui(self):
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        card, cont = self._create_card_sizer(self, "ASCII 码对照表")
        
        # 加一个面板来包裹 ListCtrl 以实现边框效果，并调小边距
        border_panel = wx.Panel(self, style=wx.BORDER_SUNKEN)
        border_sizer = wx.BoxSizer(wx.VERTICAL)
        
        self.ascii_list = AsciiListCtrl(border_panel, wx.ID_ANY, style=wx.LC_REPORT | wx.BORDER_NONE | wx.LC_SINGLE_SEL)
        self.ascii_list.SetFont(ThemeManager.get_mono_font(14))
        
        self.ascii_list.InsertColumn(0, "Bin(二进制)", width=100)
        self.ascii_list.InsertColumn(1, "Oct(八进制)", width=80)
        self.ascii_list.InsertColumn(2, "Dec(十进制)", width=80)
        self.ascii_list.InsertColumn(3, "Hex(十六进制)", width=90)
        self.ascii_list.InsertColumn(4, "缩写/字符", width=100)
        self.ascii_list.InsertColumn(5, "描述", width=300)
        
        self._load_ascii_data()
        
        border_sizer.Add(self.ascii_list, 1, wx.EXPAND)
        border_panel.SetSizer(border_sizer)
        
        # 调小左右边距 (由原来的 20 调小为 5)
        cont.Add(border_panel, 1, wx.EXPAND | wx.RIGHT, 5)
        main_sizer.Add(card, 1, wx.EXPAND | wx.ALL, 15)
        
        self.SetSizer(main_sizer)

    def _load_ascii_data(self):
        # ASCII 控制字符 (0-31, 127)
        control_chars = [
            ("0000 0000", "000", "0", "0x00", "NUL", "Null (空字符)"),
            ("0000 0001", "001", "1", "0x01", "SOH", "Start of Heading (标题开始)"),
            ("0000 0010", "002", "2", "0x02", "STX", "Start of Text (正文开始)"),
            ("0000 0011", "003", "3", "0x03", "ETX", "End of Text (正文结束)"),
            ("0000 0100", "004", "4", "0x04", "EOT", "End of Transmission (传输结束)"),
            ("0000 0101", "005", "5", "0x05", "ENQ", "Enquiry (询问)"),
            ("0000 0110", "006", "6", "0x06", "ACK", "Acknowledgment (确认)"),
            ("0000 0111", "007", "7", "0x07", "BEL", "Bell (响铃)"),
            ("0000 1000", "010", "8", "0x08", "BS", "Backspace (退格)"),
            ("0000 1001", "011", "9", "0x09", "HT", "Horizontal Tab (水平制表符)"),
            ("0000 1010", "012", "10", "0x0A", "LF", "Line Feed (换行)"),
            ("0000 1011", "013", "11", "0x0B", "VT", "Vertical Tab (垂直制表符)"),
            ("0000 1100", "014", "12", "0x0C", "FF", "Form Feed (换页)"),
            ("0000 1101", "015", "13", "0x0D", "CR", "Carriage Return (回车)"),
            ("0000 1110", "016", "14", "0x0E", "SO", "Shift Out (不用切换)"),
            ("0000 1111", "017", "15", "0x0F", "SI", "Shift In (启用切换)"),
            ("0001 0000", "020", "16", "0x10", "DLE", "Data Link Escape (数据链路转义)"),
            ("0001 0001", "021", "17", "0x11", "DC1", "Device Control 1 (设备控制1)"),
            ("0001 0010", "022", "18", "0x12", "DC2", "Device Control 2 (设备控制2)"),
            ("0001 0011", "023", "19", "0x13", "DC3", "Device Control 3 (设备控制3)"),
            ("0001 0100", "024", "20", "0x14", "DC4", "Device Control 4 (设备控制4)"),
            ("0001 0101", "025", "21", "0x15", "NAK", "Negative Acknowledgment (否定确认)"),
            ("0001 0110", "026", "22", "0x16", "SYN", "Synchronous Idle (同步空闲)"),
            ("0001 0111", "027", "23", "0x17", "ETB", "End of Transmission Block (传输块结束)"),
            ("0001 1000", "030", "24", "0x18", "CAN", "Cancel (取消)"),
            ("0001 1001", "031", "25", "0x19", "EM", "End of Medium (介质结束)"),
            ("0001 1010", "032", "26", "0x1A", "SUB", "Substitute (替换)"),
            ("0001 1011", "033", "27", "0x1B", "ESC", "Escape (转义)"),
            ("0001 1100", "034", "28", "0x1C", "FS", "File Separator (文件分隔符)"),
            ("0001 1101", "035", "29", "0x1D", "GS", "Group Separator (组分隔符)"),
            ("0001 1110", "036", "30", "0x1E", "RS", "Record Separator (记录分隔符)"),
            ("0001 1111", "037", "31", "0x1F", "US", "Unit Separator (单元分隔符)"),
            ("0010 0000", "040", "32", "0x20", "Space", "Space (空格)"),
        ]
        
        for item in control_chars:
            self.ascii_list.Append(item)
            
        # 可打印字符 (33-126)
        for i in range(33, 127):
            bin_str = format(i, '08b')
            bin_str = bin_str[:4] + " " + bin_str[4:]
            oct_str = format(i, '03o')
            dec_str = str(i)
            hex_str = "0x" + format(i, '02X')
            char_str = chr(i)
            desc = ""
            if i == 127:
                char_str = "DEL"
                desc = "Delete (删除)"
            self.ascii_list.Append((bin_str, oct_str, dec_str, hex_str, char_str, desc))
