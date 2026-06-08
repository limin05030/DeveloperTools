# -*- coding: utf-8 -*-
"""嵌入式终端 — 伪终端 (pty) + 子进程"""

import os
import sys
import pty
import subprocess
import threading
import signal

_instances = {}


class TerminalSession:
    """单个终端会话"""

    def __init__(self, shell=None):
        self._fd = None          # pty master fd (Unix) / ConPTY output read handle (Windows)
        self._proc = None        # shell 子进程
        self._reader = None      # 输出读取线程
        self._running = False
        self._shell = shell or os.environ.get('SHELL', '/bin/bash')
        self._on_output = None   # 输出回调 (data: str) -> None

        # Windows ConPTY 专用
        self._conpty_hpc = None       # 伪控制台句柄
        self._conpty_in_write = None  # 写入端（用户输入 → 进程）
        self._conpty_pi = None        # PROCESS_INFORMATION

    def start(self, on_output, cols=80, rows=24):
        """启动 shell 并开始读取输出"""
        self._on_output = on_output
        self._running = True

        if sys.platform == 'win32':
            self._start_windows(cols, rows)
        else:
            self._start_unix(cols, rows)

        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()

    # ==================== Unix ====================

    def _start_unix(self, cols, rows):
        """Unix: 通过 pty 伪终端启动"""
        master_fd, slave_fd = pty.openpty()
        self._fd = master_fd

        try:
            import fcntl
            import struct
            import termios
            winsize = struct.pack('HHHH', rows, cols, 0, 0)
            fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, winsize)
        except Exception:
            pass

        env = os.environ.copy()
        env['TERM'] = 'xterm-256color'
        self._proc = subprocess.Popen(
            [self._shell],
            stdin=slave_fd, stdout=slave_fd, stderr=slave_fd,
            close_fds=True, preexec_fn=os.setsid, env=env,
            cwd=os.path.expanduser('~'),
        )
        os.close(slave_fd)

    # ==================== Windows ====================

    def _start_windows(self, cols, rows):
        """Windows: 优先使用 ConPTY，不支持时回退到 PIPE"""
        if not self._try_start_conpty(cols, rows):
            self._start_windows_pipe()

    def _try_start_conpty(self, cols, rows):
        """尝试使用 ConPTY 伪终端启动（Windows 10 1809+）"""
        try:
            import ctypes
            from ctypes import wintypes, byref, sizeof, POINTER, cast

            kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

            # ---- 常量 ----
            PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE = 0x00020016
            EXTENDED_STARTUPINFO_PRESENT = 0x00080000
            CREATE_UNICODE_ENVIRONMENT = 0x00000400
            STILL_ACTIVE = 259

            # ---- 结构体定义 ----

            class COORD(ctypes.Structure):
                _fields_ = [('X', ctypes.c_short), ('Y', ctypes.c_short)]

            class STARTUPINFOW(ctypes.Structure):
                _fields_ = [
                    ('cb', wintypes.DWORD),
                    ('lpReserved', wintypes.LPWSTR),
                    ('lpDesktop', wintypes.LPWSTR),
                    ('lpTitle', wintypes.LPWSTR),
                    ('dwX', wintypes.DWORD),
                    ('dwY', wintypes.DWORD),
                    ('dwXSize', wintypes.DWORD),
                    ('dwYSize', wintypes.DWORD),
                    ('dwXCountChars', wintypes.DWORD),
                    ('dwYCountChars', wintypes.DWORD),
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

            # ---- 创建通信管道 ----
            # 管道 1：读取进程输出（ConPTY 写入 → 我们读取）
            out_read = wintypes.HANDLE()
            out_write = wintypes.HANDLE()
            if not kernel32.CreatePipe(byref(out_read), byref(out_write), None, 0):
                raise OSError("CreatePipe for output failed")

            # 管道 2：写入用户输入（我们写入 → ConPTY 读取）
            in_read = wintypes.HANDLE()
            in_write = wintypes.HANDLE()
            if not kernel32.CreatePipe(byref(in_read), byref(in_write), None, 0):
                kernel32.CloseHandle(out_read)
                kernel32.CloseHandle(out_write)
                raise OSError("CreatePipe for input failed")

            # ---- 创建伪控制台 ----
            size = COORD(ctypes.c_short(cols), ctypes.c_short(rows))
            hpc = wintypes.HANDLE()

            # CreatePseudoConsole 返回 HRESULT（0 = S_OK）
            ret = kernel32.CreatePseudoConsole(size, in_read, out_write, 0, byref(hpc))
            if ret != 0:
                kernel32.CloseHandle(in_read)
                kernel32.CloseHandle(in_write)
                kernel32.CloseHandle(out_read)
                kernel32.CloseHandle(out_write)
                raise OSError(f"CreatePseudoConsole failed, HRESULT=0x{ret & 0xFFFFFFFF:08X}")

            # ---- 初始化属性列表 ----
            # 需要 InitializeProcThreadAttributeList 两次调用：
            # 第一次获取大小，第二次实际初始化
            attr_size = ctypes.c_size_t()
            # 第一次调用：获取所需大小
            kernel32.InitializeProcThreadAttributeList(None, 1, 0, byref(attr_size))
            # 分配内存
            attr_list = ctypes.create_string_buffer(attr_size.value)
            if not kernel32.InitializeProcThreadAttributeList(attr_list, 1, 0, byref(attr_size)):
                kernel32.ClosePseudoConsole(hpc)
                kernel32.CloseHandle(in_read)
                kernel32.CloseHandle(in_write)
                kernel32.CloseHandle(out_read)
                kernel32.CloseHandle(out_write)
                raise OSError("InitializeProcThreadAttributeList failed")

            # 设置伪控制台属性
            hpc_value = ctypes.c_void_p(hpc.value)
            if not kernel32.UpdateProcThreadAttribute(
                attr_list, 0, PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE,
                hpc_value, ctypes.sizeof(hpc_value), None, None
            ):
                kernel32.DeleteProcThreadAttributeList(attr_list)
                kernel32.ClosePseudoConsole(hpc)
                kernel32.CloseHandle(in_read)
                kernel32.CloseHandle(in_write)
                kernel32.CloseHandle(out_read)
                kernel32.CloseHandle(out_write)
                raise OSError("UpdateProcThreadAttribute failed")

            # ---- 创建进程 ----
            si = STARTUPINFOEXW()
            si.StartupInfo.cb = sizeof(STARTUPINFOEXW)
            si.lpAttributeList = cast(attr_list, ctypes.c_void_p)

            pi = PROCESS_INFORMATION()

            # 选择 shell
            comspec = os.environ.get('COMSPEC', 'cmd.exe')

            # CreateProcessW 需要可写的命令行缓冲区
            cmdline = ctypes.create_unicode_buffer(comspec)

            home = os.path.expanduser('~')

            success = kernel32.CreateProcessW(
                None,                    # lpApplicationName
                cmdline,                 # lpCommandLine（可写缓冲区）
                None,                    # lpProcessAttributes
                None,                    # lpThreadAttributes
                False,                   # bInheritHandles
                EXTENDED_STARTUPINFO_PRESENT | CREATE_UNICODE_ENVIRONMENT,
                None,                    # lpEnvironment
                home,                    # lpCurrentDirectory
                ctypes.byref(si),        # lpStartupInfo
                ctypes.byref(pi),        # lpProcessInformation
            )

            # 清理属性列表（CreateProcess 之后即可删除）
            kernel32.DeleteProcThreadAttributeList(attr_list)

            # 关闭不再需要的管道端（已由 ConPTY 接管）
            kernel32.CloseHandle(in_read)
            kernel32.CloseHandle(out_write)

            if not success:
                err = ctypes.get_last_error()
                kernel32.ClosePseudoConsole(hpc)
                kernel32.CloseHandle(out_read)
                kernel32.CloseHandle(in_write)
                raise OSError(f"CreateProcessW failed, error={err}")

            # 将 Windows HANDLE 转换为 CRT 文件描述符（os.read/os.write 需要 fd）
            import msvcrt
            self._fd = msvcrt.open_osfhandle(out_read, os.O_RDONLY)
            self._conpty_in_write = msvcrt.open_osfhandle(in_write, os.O_WRONLY)

            # 保存状态
            self._conpty_hpc = hpc
            self._conpty_pi = pi
            self._proc = True    # 标记进程已启动（非 None 即可）

            return True

        except Exception:
            # ConPTY 不可用，清理残留句柄后回退
            try:
                if hasattr(self, '_conpty_hpc') and self._conpty_hpc:
                    kernel32.ClosePseudoConsole(self._conpty_hpc)
                    self._conpty_hpc = None
            except Exception:
                pass
            self._conpty_hpc = None
            self._fd = None
            self._proc = None
            return False

    def _start_windows_pipe(self):
        """Windows: 通过 subprocess.PIPE 启动（旧版 Windows 回退方案）"""
        self._proc = subprocess.Popen(
            os.environ.get('COMSPEC', 'cmd.exe'),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=False,  # 使用默认缓冲（非 bufsize=0，避免 Windows 兼容问题）
            cwd=os.path.expanduser('~'),
        )
        self._fd = self._proc.stdout.fileno()

    # ==================== 读写循环 ====================

    def _read_loop(self):
        """持续读取 shell 输出"""
        try:
            if sys.platform == 'win32' and self._conpty_hpc:
                self._read_conpty()
            elif sys.platform == 'win32' and self._proc:
                self._read_pipe()
            else:
                self._read_unix()
        except Exception:
            pass

    def _read_unix(self):
        """Unix pty 读取"""
        import os as _os
        while self._running:
            try:
                data = _os.read(self._fd, 4096)
                if not data:
                    break
                if self._on_output:
                    self._on_output(data.decode('utf-8', errors='replace'))
            except (OSError, ValueError):
                break

    def _read_pipe(self):
        """Windows PIPE 读取（回退方案）"""
        for line in iter(self._proc.stdout.readline, b''):
            if not self._running:
                break
            if self._on_output:
                self._on_output(line.decode('utf-8', errors='replace'))

    def _read_conpty(self):
        """Windows ConPTY 读取"""
        import os as _os
        while self._running:
            try:
                data = _os.read(self._fd, 4096)
                if not data:
                    break
                if self._on_output:
                    self._on_output(data.decode('utf-8', errors='replace'))
            except (OSError, ValueError):
                break

    # ==================== 写入 ====================

    def write(self, data):
        """写入数据到 shell stdin"""
        if not self._running:
            return
        try:
            if self._conpty_in_write is not None:
                # Windows ConPTY 模式
                import os as _os
                _os.write(self._conpty_in_write, data.encode('utf-8'))
            elif sys.platform == 'win32' and self._proc:
                # Windows PIPE 回退模式
                self._proc.stdin.write(data.encode('utf-8'))
                self._proc.stdin.flush()
            elif self._fd is not None:
                # Unix pty 模式
                import os as _os
                _os.write(self._fd, data.encode('utf-8'))
        except Exception:
            pass

    # ==================== 调整大小 ====================

    def resize(self, cols, rows):
        """调整终端大小"""
        try:
            if self._conpty_hpc is not None:
                # Windows ConPTY 模式
                import ctypes
                kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

                class COORD(ctypes.Structure):
                    _fields_ = [('X', ctypes.c_short), ('Y', ctypes.c_short)]

                size = COORD(ctypes.c_short(cols), ctypes.c_short(rows))
                kernel32.ResizePseudoConsole(self._conpty_hpc, size)
            elif sys.platform != 'win32' and self._fd is not None:
                # Unix pty 模式
                import fcntl
                import struct
                import termios
                winsize = struct.pack('HHHH', rows, cols, 0, 0)
                fcntl.ioctl(self._fd, termios.TIOCSWINSZ, winsize)
        except Exception:
            pass

    # ==================== 停止 ====================

    def stop(self):
        """终止 shell 进程"""
        self._running = False

        if self._conpty_hpc is not None:
            # Windows ConPTY 模式
            try:
                import ctypes
                kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

                # 终止进程
                pi = self._conpty_pi
                if pi and pi.hProcess:
                    kernel32.TerminateProcess(pi.hProcess, 0)
                    kernel32.CloseHandle(pi.hProcess)
                    if pi.hThread:
                        kernel32.CloseHandle(pi.hThread)

                # 关闭伪控制台
                kernel32.ClosePseudoConsole(self._conpty_hpc)

                # 关闭管道句柄
                if self._fd:
                    try:
                        import os as _os
                        _os.close(self._fd)
                    except Exception:
                        pass
                if self._conpty_in_write:
                    try:
                        import os as _os
                        _os.close(self._conpty_in_write)
                    except Exception:
                        pass
            except Exception:
                pass
            finally:
                self._conpty_hpc = None
                self._conpty_in_write = None
                self._fd = None
                self._conpty_pi = None
                self._proc = None
            return

        if self._proc:
            try:
                if sys.platform == 'win32':
                    self._proc.kill()
                else:
                    # SIGTERM 优雅终止进程组
                    os.killpg(os.getpgid(self._proc.pid), signal.SIGTERM)
                # 等待子进程退出，避免僵尸进程阻塞应用关闭
                try:
                    self._proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    try:
                        self._proc.kill()
                        self._proc.wait(timeout=1)
                    except Exception:
                        pass
            except Exception:
                pass
            self._proc = None
        if self._fd:
            try:
                import os as _os
                _os.close(self._fd)
            except Exception:
                pass
            self._fd = None
