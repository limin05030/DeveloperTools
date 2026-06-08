# -*- coding: utf-8 -*-
"""独立 ConPTY 测试 — 在 Windows 上运行验证伪控制台是否正常工作"""
import os
import sys
import ctypes
from ctypes import wintypes, byref, sizeof, POINTER, cast

def test_conpty():
    print("=== ConPTY 测试 ===")
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

    # 1. 检查函数是否存在
    try:
        kernel32.CreatePseudoConsole
        print("✓ kernel32.CreatePseudoConsole 存在")
    except AttributeError:
        print("✗ kernel32.CreatePseudoConsole 不存在 — 需要 Windows 10 1809+")
        return False

    # 2. 创建管道
    out_read = wintypes.HANDLE()
    out_write = wintypes.HANDLE()
    if not kernel32.CreatePipe(byref(out_read), byref(out_write), None, 0):
        print(f"✗ CreatePipe 失败: {ctypes.get_last_error()}")
        return False

    in_read = wintypes.HANDLE()
    in_write = wintypes.HANDLE()
    if not kernel32.CreatePipe(byref(in_read), byref(in_write), None, 0):
        print(f"✗ CreatePipe 失败: {ctypes.get_last_error()}")
        kernel32.CloseHandle(out_read)
        kernel32.CloseHandle(out_write)
        return False

    print(f"✓ 管道已创建: out_read={out_read.value}, out_write={out_write.value}, in_read={in_read.value}, in_write={in_write.value}")

    # 3. 创建伪控制台
    class COORD(ctypes.Structure):
        _fields_ = [('X', ctypes.c_short), ('Y', ctypes.c_short)]

    # 设置参数类型
    kernel32.CreatePseudoConsole.argtypes = [
        COORD, wintypes.HANDLE, wintypes.HANDLE,
        wintypes.DWORD, POINTER(wintypes.HANDLE),
    ]
    kernel32.CreatePseudoConsole.restype = wintypes.HRESULT

    size = COORD(80, 24)
    hpc = wintypes.HANDLE()
    ret = kernel32.CreatePseudoConsole(size, in_read, out_write, 0, byref(hpc))

    if ret != 0:
        print(f"✗ CreatePseudoConsole 失败: HRESULT=0x{ret & 0xFFFFFFFF:08X}")
        kernel32.CloseHandle(in_read)
        kernel32.CloseHandle(in_write)
        kernel32.CloseHandle(out_read)
        kernel32.CloseHandle(out_write)
        return False

    print(f"✓ CreatePseudoConsole 成功: hpc={hpc.value}")

    # 4. 创建进程
    PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE = 0x00020016
    EXTENDED_STARTUPINFO_PRESENT = 0x00080000

    class STARTUPINFOW(ctypes.Structure):
        _fields_ = [
            ('cb', wintypes.DWORD),
            ('lpReserved', wintypes.LPWSTR),
            ('lpDesktop', wintypes.LPWSTR),
            ('lpTitle', wintypes.LPWSTR),
            ('dwX', wintypes.DWORD), ('dwY', wintypes.DWORD),
            ('dwXSize', wintypes.DWORD), ('dwYSize', wintypes.DWORD),
            ('dwXCountChars', wintypes.DWORD), ('dwYCountChars', wintypes.DWORD),
            ('dwFillAttribute', wintypes.DWORD),
            ('dwFlags', wintypes.DWORD),
            ('wShowWindow', wintypes.WORD),
            ('cbReserved2', wintypes.WORD),
            ('lpReserved2', POINTER(wintypes.BYTE)),
            ('hStdInput', wintypes.HANDLE),
            ('hStdOutput', wintypes.HANDLE),
            ('hStdError', wintypes.HANDLE),
        ]

    class STARTUPINFOEXW(ctypes.Structure):
        _fields_ = [
            ('StartupInfo', STARTUPINFOW),
            ('lpAttributeList', ctypes.c_void_p),
        ]

    class PROCESS_INFORMATION(ctypes.Structure):
        _fields_ = [
            ('hProcess', wintypes.HANDLE),
            ('hThread', wintypes.HANDLE),
            ('dwProcessId', wintypes.DWORD),
            ('dwThreadId', wintypes.DWORD),
        ]

    attr_size = ctypes.c_size_t()
    kernel32.InitializeProcThreadAttributeList(None, 1, 0, byref(attr_size))
    print(f"  属性列表大小: {attr_size.value}")

    if attr_size.value == 0:
        print("✗ 属性列表大小为 0")
        return False

    attr_list = ctypes.create_string_buffer(attr_size.value)
    if not kernel32.InitializeProcThreadAttributeList(attr_list, 1, 0, byref(attr_size)):
        err = ctypes.get_last_error()
        print(f"✗ InitializeProcThreadAttributeList 失败: {err}")
        return False

    print("✓ 属性列表已初始化")

    # 关键：传递 ConPTY 句柄
    if not kernel32.UpdateProcThreadAttribute(
        attr_list, 0,
        PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE,
        byref(hpc),                          # 指针指向 hpc 的值
        ctypes.sizeof(ctypes.c_void_p),      # sizeof(HPCON) = sizeof(void*)
        None, None
    ):
        err = ctypes.get_last_error()
        print(f"✗ UpdateProcThreadAttribute 失败: {err}")
        kernel32.DeleteProcThreadAttributeList(attr_list)
        return False

    print("✓ ConPTY 属性已设置")

    si = STARTUPINFOEXW()
    si.StartupInfo.cb = sizeof(STARTUPINFOEXW)
    si.lpAttributeList = cast(attr_list, ctypes.c_void_p)

    pi = PROCESS_INFORMATION()
    comspec = os.environ.get('COMSPEC', 'cmd.exe')
    cmdline = ctypes.create_unicode_buffer(comspec)
    home = os.path.expanduser('~')

    success = kernel32.CreateProcessW(
        None, cmdline, None, None, False,
        EXTENDED_STARTUPINFO_PRESENT,
        None, home,
        ctypes.byref(si), ctypes.byref(pi),
    )

    kernel32.DeleteProcThreadAttributeList(attr_list)
    kernel32.CloseHandle(in_read)
    kernel32.CloseHandle(out_write)

    if not success:
        err = ctypes.get_last_error()
        print(f"✗ CreateProcessW 失败: {err}")
        kernel32.CloseHandle(out_read)
        kernel32.CloseHandle(in_write)
        kernel32.ClosePseudoConsole(hpc)
        return False

    print(f"✓ CreateProcess 成功: pid={pi.dwProcessId}")

    # 5. 尝试读取输出（给 cmd.exe 一些时间输出 banner）
    import time
    print("  等待 cmd.exe 输出...")
    time.sleep(2)

    buf = ctypes.create_string_buffer(4096)
    bytes_read = wintypes.DWORD(0)
    read_success = kernel32.ReadFile(out_read, buf, 4096, byref(bytes_read), None)

    if read_success and bytes_read.value > 0:
        data = buf.raw[:bytes_read.value]
        print(f"✓ 读取到 {bytes_read.value} 字节:")
        print(f"  raw: {repr(data[:200])}")
        try:
            text = data.decode('gbk')
            print(f"  gbk: {text[:200]}")
        except Exception:
            text = data.decode('utf-8', errors='replace')
            print(f"  utf8: {text[:200]}")

        # 写入 dir 命令测试
        cmd = b"dir\r\n"
        written = wintypes.DWORD(0)
        kernel32.WriteFile(in_write, cmd, len(cmd), byref(written), None)
        print(f"✓ 写入 'dir' 命令: {written.value} 字节")

        time.sleep(1)
        buf2 = ctypes.create_string_buffer(4096)
        bytes_read2 = wintypes.DWORD(0)
        read_success2 = kernel32.ReadFile(out_read, buf2, 4096, byref(bytes_read2), None)
        if read_success2 and bytes_read2.value > 0:
            data2 = buf2.raw[:bytes_read2.value]
            print(f"✓ 收到命令回显: {bytes_read2.value} 字节")
            try:
                print(data2.decode('gbk', errors='replace')[:500])
            except Exception:
                print(data2.decode('utf-8', errors='replace')[:500])
        else:
            print(f"✗ 未收到命令回显: success={read_success2}, bytes={bytes_read2.value}")

        # 测试成功！
        print("\n✓✓✓ ConPTY 工作正常！")
    else:
        err = ctypes.get_last_error()
        print(f"✗ 未读到输出: success={read_success}, bytes={bytes_read.value}, err={err}")
        print("  ConPTY 管道未收到数据 — 进程可能未连接到伪控制台")

    # 6. 清理
    kernel32.TerminateProcess(pi.hProcess, 0)
    kernel32.CloseHandle(pi.hProcess)
    kernel32.CloseHandle(pi.hThread)
    kernel32.ClosePseudoConsole(hpc)
    kernel32.CloseHandle(out_read)
    kernel32.CloseHandle(in_write)
    print("  已清理")

    return True

if __name__ == '__main__':
    test_conpty()
