# -*- coding: utf-8 -*-
"""嵌入式终端 — 伪终端 (pty) + 子进程"""

import os
import sys
import subprocess
import threading
import signal

_instances = {}


class TerminalSession:
    """单个终端会话"""

    def __init__(self, shell=None):
        self._fd = None          # pty master fd (Unix) / ConPTY 输出读取 fd (Windows)
        self._proc = None        # shell 子进程
        self._reader = None      # 输出读取线程
        self._running = False
        self._shell = shell or os.environ.get('SHELL', '/bin/bash')
        self._on_output = None   # 输出回调 (data: str) -> None

        # Windows ConPTY 专用
        self._conpty_hpc = None       # 伪控制台句柄
        self._conpty_in_write = None  # 写入端 fd（用户输入 → 进程）
        self._conpty_pi = None        # PROCESS_INFORMATION
        self._conpty_mode = False     # 是否成功启用 ConPTY

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
        import pty as _pty
        master_fd, slave_fd = _pty.openpty()
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
        if self._try_conpty(cols, rows):
            return
        self._start_windows_pipe()

    # ---- ConPTY 实现 ----

    def _try_conpty(self, cols, rows):
        """尝试使用 ConPTY 伪终端启动（Windows 10 1809+）"""
        try:
            import ctypes
            from ctypes import wintypes, byref

            kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

            # 检查 CreatePseudoConsole 是否可用
            try:
                create_pc = kernel32.CreatePseudoConsole
            except AttributeError:
                return False

            # 创建通信管道
            out_read = wintypes.HANDLE()
            out_write = wintypes.HANDLE()
            if not kernel32.CreatePipe(byref(out_read), byref(out_write), None, 0):
                return False

            in_read = wintypes.HANDLE()
            in_write = wintypes.HANDLE()
            if not kernel32.CreatePipe(byref(in_read), byref(in_write), None, 0):
                kernel32.CloseHandle(out_read)
                kernel32.CloseHandle(out_write)
                return False

            # 创建伪控制台
            class COORD(ctypes.Structure):
                _fields_ = [('X', ctypes.c_short), ('Y', ctypes.c_short)]

            size = COORD(ctypes.c_short(cols), ctypes.c_short(rows))
            hpc = wintypes.HANDLE()

            ret = create_pc(size, in_read, out_write, 0, byref(hpc))
            if ret != 0:  # S_OK == 0
                kernel32.CloseHandle(in_read)
                kernel32.CloseHandle(in_write)
                kernel32.CloseHandle(out_read)
                kernel32.CloseHandle(out_write)
                return False

            # 创建进程
            success, pi = self._conpty_create_process(
                kernel32, hpc,
                in_read.value, in_write.value,
                out_read.value, out_write.value
            )

            if not success:
                kernel32.ClosePseudoConsole(hpc)
                return False

            # Win32 HANDLE → CRT fd
            import msvcrt
            self._fd = msvcrt.open_osfhandle(out_read.value, os.O_RDONLY)
            self._conpty_in_write = msvcrt.open_osfhandle(in_write.value, os.O_WRONLY)
            self._conpty_hpc = hpc
            self._conpty_pi = pi
            self._conpty_mode = True
            self._proc = True
            return True

        except Exception:
            return False

    def _conpty_create_process(self, kernel32, hpc, in_read, in_write,
                                out_read, out_write):
        """使用 ConPTY 句柄创建 Windows 进程"""
        import ctypes
        from ctypes import wintypes, byref, sizeof, POINTER, cast

        PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE = 0x00020016
        EXTENDED_STARTUPINFO_PRESENT = 0x00080000

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

        # 初始化属性列表
        attr_size = ctypes.c_size_t()
        kernel32.InitializeProcThreadAttributeList(None, 1, 0, byref(attr_size))
        attr_list = ctypes.create_string_buffer(attr_size.value)
        if not kernel32.InitializeProcThreadAttributeList(attr_list, 1, 0, byref(attr_size)):
            self._close_handles(kernel32, in_read, in_write, out_read, out_write)
            return False, None

        # 设置 ConPTY 属性
        hpc_val = hpc.value if hasattr(hpc, 'value') else hpc
        hpc_void = ctypes.c_void_p(hpc_val)
        if not kernel32.UpdateProcThreadAttribute(
            attr_list, 0, PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE,
            hpc_void, ctypes.sizeof(hpc_void), None, None
        ):
            kernel32.DeleteProcThreadAttributeList(attr_list)
            self._close_handles(kernel32, in_read, in_write, out_read, out_write)
            return False, None

        # 创建进程
        si = STARTUPINFOEXW()
        si.StartupInfo.cb = sizeof(STARTUPINFOEXW)
        si.lpAttributeList = cast(attr_list, ctypes.c_void_p)

        pi = PROCESS_INFORMATION()

        comspec = os.environ.get('COMSPEC', 'cmd.exe')
        cmdline = ctypes.create_unicode_buffer(comspec)
        home = os.path.expanduser('~')

        success = kernel32.CreateProcessW(
            None, cmdline,
            None, None,
            False,
            EXTENDED_STARTUPINFO_PRESENT,
            None, home,
            ctypes.byref(si), ctypes.byref(pi),
        )

        kernel32.DeleteProcThreadAttributeList(attr_list)

        # 关闭已被 ConPTY 接管的管道端
        kernel32.CloseHandle(in_read)
        kernel32.CloseHandle(out_write)

        if not success:
            kernel32.CloseHandle(out_read)
            kernel32.CloseHandle(in_write)
            return False, None

        return True, pi

    @staticmethod
    def _close_handles(kernel32, *handles):
        for h in handles:
            try:
                kernel32.CloseHandle(h)
            except Exception:
                pass

    # ---- PIPE 回退方案 ----

    def _start_windows_pipe(self):
        """Windows: subprocess.PIPE 方式（旧版 Windows 回退）"""
        self._proc = subprocess.Popen(
            os.environ.get('COMSPEC', 'cmd.exe'),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=os.path.expanduser('~'),
        )
        self._fd = self._proc.stdout.fileno()

    # ==================== 读写循环 ====================

    def _read_loop(self):
        """持续读取 shell 输出"""
        try:
            if self._conpty_mode:
                self._read_conpty()
            elif sys.platform == 'win32' and self._proc:
                self._read_pipe()
            else:
                self._read_unix()
        except Exception:
            pass

    def _read_unix(self):
        """Unix pty 读取"""
        while self._running:
            try:
                data = os.read(self._fd, 4096)
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
        while self._running:
            try:
                data = os.read(self._fd, 4096)
                if not data:
                    break
                if self._on_output:
                    # Windows 控制台使用系统 OEM 编码（中文 Windows 为 GBK）
                    try:
                        text = data.decode('gbk')
                    except Exception:
                        text = data.decode('utf-8', errors='replace')
                    self._on_output(text)
            except (OSError, ValueError):
                break

    # ==================== 写入 ====================

    def write(self, data):
        """写入数据到 shell stdin"""
        if not self._running:
            return
        try:
            if self._conpty_mode and self._conpty_in_write is not None:
                os.write(self._conpty_in_write, data.encode('utf-8'))
            elif sys.platform == 'win32' and isinstance(self._proc, subprocess.Popen):
                self._proc.stdin.write(data.encode('utf-8'))
                self._proc.stdin.flush()
            elif self._fd is not None:
                os.write(self._fd, data.encode('utf-8'))
        except Exception:
            pass

    # ==================== 调整大小 ====================

    def resize(self, cols, rows):
        """调整终端大小"""
        try:
            if self._conpty_hpc is not None:
                self._resize_conpty(cols, rows)
            elif sys.platform != 'win32' and self._fd is not None:
                import fcntl
                import struct
                import termios
                winsize = struct.pack('HHHH', rows, cols, 0, 0)
                fcntl.ioctl(self._fd, termios.TIOCSWINSZ, winsize)
        except Exception:
            pass

    def _resize_conpty(self, cols, rows):
        """ConPTY 大小调整"""
        try:
            import ctypes
            kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

            class COORD(ctypes.Structure):
                _fields_ = [('X', ctypes.c_short), ('Y', ctypes.c_short)]
            size = COORD(ctypes.c_short(cols), ctypes.c_short(rows))
            kernel32.ResizePseudoConsole(self._conpty_hpc, size)
        except Exception:
            pass

    # ==================== 停止 ====================

    def stop(self):
        """终止 shell 进程"""
        self._running = False

        if self._conpty_hpc is not None:
            self._stop_conpty()
            return

        if isinstance(self._proc, subprocess.Popen):
            try:
                if sys.platform == 'win32':
                    self._proc.kill()
                else:
                    os.killpg(os.getpgid(self._proc.pid), signal.SIGTERM)
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
                os.close(self._fd)
            except Exception:
                pass
            self._fd = None

    def _stop_conpty(self):
        """停止 ConPTY 终端"""
        try:
            import ctypes
            kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

            pi = self._conpty_pi
            if pi and pi.hProcess:
                kernel32.TerminateProcess(pi.hProcess, 0)
                kernel32.CloseHandle(pi.hProcess)
                if pi.hThread:
                    kernel32.CloseHandle(pi.hThread)

            try:
                kernel32.ClosePseudoConsole(self._conpty_hpc)
            except Exception:
                pass

            for attr in ('_fd', '_conpty_in_write'):
                fd = getattr(self, attr, None)
                if fd is not None:
                    try:
                        os.close(fd)
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
