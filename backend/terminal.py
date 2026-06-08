# -*- coding: utf-8 -*-
"""嵌入式终端 — 伪终端 (pty) + 子进程"""

import os
import sys
import pty
import subprocess
import threading
import signal
import logging

log = logging.getLogger(__name__)

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
        """Windows: 依次尝试 ConPTY → 回退方案"""
        if self._try_conpty_via_winapi(cols, rows):
            log.info("终端: 已通过 _winapi.ConPTY 启动")
            return
        if self._try_conpty_via_ctypes(cols, rows):
            log.info("终端: 已通过 ctypes.ConPTY 启动")
            return
        log.warning("终端: ConPTY 不可用，回退到 PIPE 模式（输入可能受限）")
        self._start_windows_pipe()

    # ---- ConPTY 方案 A：_winapi（Python 3.8+，最可靠） ----

    def _try_conpty_via_winapi(self, cols, rows):
        """使用 _winapi.CreatePseudoConsole（CPython 内置，更可靠）"""
        try:
            import _winapi
            import ctypes
            from ctypes import wintypes, byref, sizeof, POINTER, cast

            # 检查 _winapi 是否有 CreatePseudoConsole
            if not hasattr(_winapi, 'CreatePseudoConsole'):
                log.debug("_winapi.CreatePseudoConsole 不可用")
                return False

            kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

            # 常量
            PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE = 0x00020016
            EXTENDED_STARTUPINFO_PRESENT = 0x00080000

            # ---- 创建管道 ----
            out_read, out_write = _winapi.CreatePipe(None, 0)
            in_read, in_write = _winapi.CreatePipe(None, 0)

            # ---- 创建伪控制台 ----
            # _winapi.CreatePseudoConsole(size_tuple, hInput, hOutput, flags)
            hpc = _winapi.CreatePseudoConsole((cols, rows), in_read, out_write, 0)
            if not hpc or hpc == _winapi.NULL:
                _winapi.CloseHandle(in_read)
                _winapi.CloseHandle(in_write)
                _winapi.CloseHandle(out_read)
                _winapi.CloseHandle(out_write)
                log.debug("CreatePseudoConsole 返回无效句柄")
                return False

            # ---- CreateProcess with ConPTY ----
            success, pi = self._create_process_conpty(
                kernel32, hpc, in_read, in_write, out_read, out_write, cols, rows
            )
            if not success:
                _winapi.ClosePseudoConsole(hpc)
                return False

            # 将 Win32 HANDLE 转为 CRT fd（os.read/os.write 需要）
            import msvcrt
            self._fd = msvcrt.open_osfhandle(out_read, os.O_RDONLY)
            self._conpty_in_write = msvcrt.open_osfhandle(in_write, os.O_WRONLY)
            self._conpty_hpc = hpc
            self._conpty_pi = pi
            self._conpty_mode = True
            self._proc = True
            return True

        except Exception:
            log.exception("_winapi ConPTY 启动失败")
            return False

    # ---- ConPTY 方案 B：纯 ctypes ----

    def _try_conpty_via_ctypes(self, cols, rows):
        """使用 ctypes 直接调用 kernel32（备用方案）"""
        try:
            import ctypes
            from ctypes import wintypes, byref, sizeof, POINTER, cast

            kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

            # 检查函数是否存在
            try:
                create_pseudo_console = kernel32.CreatePseudoConsole
            except AttributeError:
                log.debug("kernel32.CreatePseudoConsole 未找到")
                return False

            # 常量
            PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE = 0x00020016
            EXTENDED_STARTUPINFO_PRESENT = 0x00080000

            # ---- 创建管道 ----
            out_read = wintypes.HANDLE()
            out_write = wintypes.HANDLE()
            if not kernel32.CreatePipe(byref(out_read), byref(out_write), None, 0):
                log.debug("CreatePipe (output) 失败")
                return False

            in_read = wintypes.HANDLE()
            in_write = wintypes.HANDLE()
            if not kernel32.CreatePipe(byref(in_read), byref(in_write), None, 0):
                kernel32.CloseHandle(out_read)
                kernel32.CloseHandle(out_write)
                log.debug("CreatePipe (input) 失败")
                return False

            # ---- 创建伪控制台 ----
            class COORD(ctypes.Structure):
                _fields_ = [('X', ctypes.c_short), ('Y', ctypes.c_short)]

            size = COORD(ctypes.c_short(cols), ctypes.c_short(rows))
            hpc = wintypes.HANDLE()

            ret = create_pseudo_console(size, in_read, out_write, 0, byref(hpc))
            if ret != 0:  # S_OK = 0
                kernel32.CloseHandle(in_read)
                kernel32.CloseHandle(in_write)
                kernel32.CloseHandle(out_read)
                kernel32.CloseHandle(out_write)
                log.debug("CreatePseudoConsole 失败, HRESULT=0x%08X", ret & 0xFFFFFFFF)
                return False

            # ---- CreateProcess ----
            # 需要把 py-HANDLE 转为原始 int 给后续流程
            in_read_val = in_read.value
            in_write_val = in_write.value
            out_read_val = out_read.value
            out_write_val = out_write.value

            success, pi = self._create_process_conpty(
                kernel32, hpc, in_read_val, in_write_val,
                out_read_val, out_write_val, cols, rows
            )
            if not success:
                kernel32.ClosePseudoConsole(hpc)
                return False

            # 将 Win32 HANDLE 转为 CRT fd
            import msvcrt
            self._fd = msvcrt.open_osfhandle(out_read_val, os.O_RDONLY)
            self._conpty_in_write = msvcrt.open_osfhandle(in_write_val, os.O_WRONLY)
            self._conpty_hpc = hpc
            self._conpty_pi = pi
            self._conpty_mode = True
            self._proc = True
            return True

        except Exception:
            log.exception("ctypes ConPTY 启动失败")
            return False

    # ---- CreateProcess（共用的 Windows 进程创建逻辑） ----

    def _create_process_conpty(self, kernel32, hpc, in_read, in_write,
                                out_read, out_write, cols, rows):
        """使用 ConPTY 句柄创建 Windows 进程，返回 (success, PROCESS_INFORMATION)"""
        import ctypes
        from ctypes import wintypes, byref, sizeof, POINTER, cast

        PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE = 0x00020016
        EXTENDED_STARTUPINFO_PRESENT = 0x00080000

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

        # ---- 初始化属性列表 ----
        attr_size = ctypes.c_size_t()
        kernel32.InitializeProcThreadAttributeList(None, 1, 0, byref(attr_size))
        attr_list = ctypes.create_string_buffer(attr_size.value)
        if not kernel32.InitializeProcThreadAttributeList(attr_list, 1, 0, byref(attr_size)):
            kernel32.CloseHandle(in_read)
            kernel32.CloseHandle(in_write)
            kernel32.CloseHandle(out_read)
            kernel32.CloseHandle(out_write)
            log.debug("InitializeProcThreadAttributeList 失败")
            return False, None

        hpc_void = ctypes.c_void_p(hpc.value if hasattr(hpc, 'value') else hpc)
        if not kernel32.UpdateProcThreadAttribute(
            attr_list, 0, PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE,
            hpc_void, ctypes.sizeof(hpc_void), None, None
        ):
            kernel32.DeleteProcThreadAttributeList(attr_list)
            kernel32.CloseHandle(in_read)
            kernel32.CloseHandle(in_write)
            kernel32.CloseHandle(out_read)
            kernel32.CloseHandle(out_write)
            log.debug("UpdateProcThreadAttribute 失败")
            return False, None

        # ---- 启动进程 ----
        si = STARTUPINFOEXW()
        si.StartupInfo.cb = sizeof(STARTUPINFOEXW)
        si.lpAttributeList = cast(attr_list, ctypes.c_void_p)

        pi = PROCESS_INFORMATION()

        comspec = os.environ.get('COMSPEC', 'cmd.exe')
        cmdline = ctypes.create_unicode_buffer(comspec)
        home = os.path.expanduser('~')

        success = kernel32.CreateProcessW(
            None,
            cmdline,
            None, None,
            False,  # bInheritHandles
            EXTENDED_STARTUPINFO_PRESENT,
            None,
            home,
            ctypes.byref(si),
            ctypes.byref(pi),
        )

        kernel32.DeleteProcThreadAttributeList(attr_list)

        # 关闭 ConPTY 已接管的管道端
        # in_read / out_write 已由 CreatePseudoConsole 接管
        kernel32.CloseHandle(in_read)
        kernel32.CloseHandle(out_write)

        if not success:
            err = ctypes.get_last_error()
            kernel32.CloseHandle(out_read)
            kernel32.CloseHandle(in_write)
            log.debug("CreateProcessW 失败, error=%d", err)
            return False, None

        return True, pi

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
            log.exception("读取循环异常退出")

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
                    self._on_output(data.decode('utf-8', errors='replace'))
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
            log.exception("写入终端失败")

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
            log.exception("调整终端大小失败")

    def _resize_conpty(self, cols, rows):
        """ConPTY 大小调整"""
        try:
            # 优先尝试 _winapi
            import _winapi
            _winapi.ResizePseudoConsole(self._conpty_hpc, (cols, rows))
        except Exception:
            try:
                # 回退到 ctypes
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

            # 终止进程
            pi = self._conpty_pi
            if pi and pi.hProcess:
                kernel32.TerminateProcess(pi.hProcess, 0)
                kernel32.CloseHandle(pi.hProcess)
                if pi.hThread:
                    kernel32.CloseHandle(pi.hThread)

            # 关闭伪控制台（_winapi 或 kernel32）
            try:
                import _winapi
                _winapi.ClosePseudoConsole(self._conpty_hpc)
            except Exception:
                try:
                    kernel32.ClosePseudoConsole(self._conpty_hpc)
                except Exception:
                    pass

            # 关闭管道 fd
            for attr in ('_fd', '_conpty_in_write'):
                fd = getattr(self, attr, None)
                if fd is not None:
                    try:
                        os.close(fd)
                    except Exception:
                        pass
        except Exception:
            log.exception("停止 ConPTY 终端异常")
        finally:
            self._conpty_hpc = None
            self._conpty_in_write = None
            self._fd = None
            self._conpty_pi = None
            self._proc = None
