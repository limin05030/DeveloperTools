# -*- coding: utf-8 -*-
"""嵌入式终端 — 伪终端 (pty) + 子进程"""

import os
import sys
import subprocess
import threading
import signal
import tempfile

_instances = {}

# 调试日志文件（Windows 上无控制台，写文件才能看到）
_DBG_FILE = os.path.join(tempfile.gettempdir(), 'devtools_terminal.log')


def _dbg(msg, *args):
    """调试输出：写入临时文件"""
    if args:
        msg = msg % args
    try:
        with open(_DBG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"[Terminal] {msg}\n")
    except Exception:
        pass


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

        _dbg("start() 被调用, platform=%s, cols=%s, rows=%s", sys.platform, cols, rows)

        if sys.platform == 'win32':
            self._start_windows(cols, rows)
        else:
            self._start_unix(cols, rows)

        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()
        _dbg("读取线程已启动")

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
        """Windows: 依次尝试 ConPTY → 回退方案"""
        _dbg("_start_windows: 尝试 ConPTY...")

        if self._try_conpty(cols, rows):
            _dbg(">>> ConPTY 启动成功")
            return

        _dbg(">>> ConPTY 不可用，回退到 PIPE 模式（输入可能受限）")
        self._start_windows_pipe()

    # ---- ConPTY 实现 ----

    def _try_conpty(self, cols, rows):
        """尝试使用 ConPTY 伪终端启动（Windows 10 1809+, 通过 ctypes 调用 kernel32）"""
        try:
            import ctypes
            from ctypes import wintypes, byref

            kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

            # 检查 CreatePseudoConsole 是否可用
            try:
                create_pc = kernel32.CreatePseudoConsole
            except AttributeError:
                _dbg("kernel32.CreatePseudoConsole 不存在（需要 Windows 10 1809+）")
                return False

            # ---- 创建管道 ----
            out_read = wintypes.HANDLE()
            out_write = wintypes.HANDLE()
            if not kernel32.CreatePipe(byref(out_read), byref(out_write), None, 0):
                _dbg("CreatePipe (output) 失败, err=%s", ctypes.get_last_error())
                return False

            in_read = wintypes.HANDLE()
            in_write = wintypes.HANDLE()
            if not kernel32.CreatePipe(byref(in_read), byref(in_write), None, 0):
                _dbg("CreatePipe (input) 失败, err=%s", ctypes.get_last_error())
                kernel32.CloseHandle(out_read)
                kernel32.CloseHandle(out_write)
                return False

            _dbg("管道已创建 out_read=%s in_write=%s", out_read.value, in_write.value)

            # ---- 创建伪控制台 ----
            class COORD(ctypes.Structure):
                _fields_ = [('X', ctypes.c_short), ('Y', ctypes.c_short)]

            size = COORD(ctypes.c_short(cols), ctypes.c_short(rows))
            hpc = wintypes.HANDLE()

            ret = create_pc(size, in_read, out_write, 0, byref(hpc))
            if ret != 0:  # S_OK == 0
                _dbg("CreatePseudoConsole 失败, HRESULT=0x%08X", ret & 0xFFFFFFFF)
                kernel32.CloseHandle(in_read)
                kernel32.CloseHandle(in_write)
                kernel32.CloseHandle(out_read)
                kernel32.CloseHandle(out_write)
                return False

            _dbg("CreatePseudoConsole 成功, hpc=%s", hpc.value)

            # ---- 创建进程 ----
            success, pi = self._conpty_create_process(
                kernel32, hpc,
                in_read.value, in_write.value,
                out_read.value, out_write.value
            )

            if not success:
                kernel32.ClosePseudoConsole(hpc)
                _dbg("CreateProcess 失败")
                return False

            _dbg("CreateProcess 成功, pid=%s", pi.dwProcessId)

            # 将 Win32 HANDLE 转为 CRT fd（os.read/os.write 需要）
            import msvcrt
            self._fd = msvcrt.open_osfhandle(out_read.value, os.O_RDONLY)
            self._conpty_in_write = msvcrt.open_osfhandle(in_write.value, os.O_WRONLY)
            _dbg("fd 转换完成: _fd=%s, _conpty_in_write=%s",
                 self._fd, self._conpty_in_write)

            self._conpty_hpc = hpc
            self._conpty_pi = pi
            self._conpty_mode = True
            self._proc = True
            return True

        except Exception as e:
            _dbg("ConPTY 异常: %s: %s", type(e).__name__, e)
            import traceback
            _dbg("Traceback: %s", traceback.format_exc())
            return False

    def _conpty_create_process(self, kernel32, hpc, in_read, in_write,
                                out_read, out_write):
        """使用 ConPTY 句柄创建 Windows 进程"""
        import ctypes
        from ctypes import wintypes, byref, sizeof, POINTER, cast

        PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE = 0x00020016
        EXTENDED_STARTUPINFO_PRESENT = 0x00080000

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

        # 初始化属性列表
        attr_size = ctypes.c_size_t()
        kernel32.InitializeProcThreadAttributeList(None, 1, 0, byref(attr_size))
        attr_list = ctypes.create_string_buffer(attr_size.value)
        if not kernel32.InitializeProcThreadAttributeList(attr_list, 1, 0, byref(attr_size)):
            _dbg("InitializeProcThreadAttributeList 失败")
            self._close_handles(kernel32, in_read, in_write, out_read, out_write)
            return False, None

        # 获取 hpc 的原始值（兼容 int 和 ctypes 类型）
        hpc_val = hpc.value if hasattr(hpc, 'value') else hpc
        hpc_void = ctypes.c_void_p(hpc_val)
        if not kernel32.UpdateProcThreadAttribute(
            attr_list, 0, PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE,
            hpc_void, ctypes.sizeof(hpc_void), None, None
        ):
            kernel32.DeleteProcThreadAttributeList(attr_list)
            _dbg("UpdateProcThreadAttribute 失败, err=%s", ctypes.get_last_error())
            self._close_handles(kernel32, in_read, in_write, out_read, out_write)
            return False, None

        si = STARTUPINFOEXW()
        si.StartupInfo.cb = sizeof(STARTUPINFOEXW)
        si.lpAttributeList = cast(attr_list, ctypes.c_void_p)

        pi = PROCESS_INFORMATION()

        comspec = os.environ.get('COMSPEC', 'cmd.exe')
        cmdline = ctypes.create_unicode_buffer(comspec)
        home = os.path.expanduser('~')

        _dbg("CreateProcessW: cmd=%s, cwd=%s", comspec, home)

        success = kernel32.CreateProcessW(
            None,
            cmdline,
            None, None,
            False,
            EXTENDED_STARTUPINFO_PRESENT,
            None,
            home,
            ctypes.byref(si),
            ctypes.byref(pi),
        )

        kernel32.DeleteProcThreadAttributeList(attr_list)

        # 关闭已被 ConPTY 接管的管道端
        kernel32.CloseHandle(in_read)
        kernel32.CloseHandle(out_write)

        if not success:
            err = ctypes.get_last_error()
            _dbg("CreateProcessW 失败, error=%d", err)
            kernel32.CloseHandle(out_read)
            kernel32.CloseHandle(in_write)
            return False, None

        return True, pi

    @staticmethod
    def _close_handles(kernel32, *handles):
        """批量关闭句柄"""
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
        _dbg("PIPE 回退启动完成, fd=%s", self._fd)

    # ==================== 读写循环 ====================

    def _read_loop(self):
        """持续读取 shell 输出"""
        try:
            if self._conpty_mode:
                _dbg("进入 ConPTY 读取循环")
                self._read_conpty()
            elif sys.platform == 'win32' and self._proc:
                _dbg("进入 PIPE 读取循环")
                self._read_pipe()
            else:
                _dbg("进入 Unix 读取循环")
                self._read_unix()
        except Exception:
            import traceback
            _dbg("读取循环异常: %s", traceback.format_exc())

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
            _dbg("write: 终端未运行, 忽略")
            return
        try:
            if self._conpty_mode and self._conpty_in_write is not None:
                encoded = data.encode('utf-8')
                _dbg("write(ConPTY): len=%d, repr=%s", len(encoded), repr(encoded[:50]))
                os.write(self._conpty_in_write, encoded)
            elif sys.platform == 'win32' and isinstance(self._proc, subprocess.Popen):
                encoded = data.encode('utf-8')
                _dbg("write(PIPE): len=%d, repr=%s", len(encoded), repr(encoded[:50]))
                self._proc.stdin.write(encoded)
                self._proc.stdin.flush()
            elif self._fd is not None:
                encoded = data.encode('utf-8')
                _dbg("write(Unix): len=%d, repr=%s", len(encoded), repr(encoded[:50]))
                os.write(self._fd, encoded)
        except Exception:
            import traceback
            _dbg("write 异常: %s", traceback.format_exc())

    # ==================== 调整大小 ====================

    def resize(self, cols, rows):
        """调整终端大小"""
        try:
            if self._conpty_hpc is not None:
                try:
                    import ctypes
                    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
                    class COORD(ctypes.Structure):
                        _fields_ = [('X', ctypes.c_short), ('Y', ctypes.c_short)]
                    size = COORD(ctypes.c_short(cols), ctypes.c_short(rows))
                    kernel32.ResizePseudoConsole(self._conpty_hpc, size)
                    _dbg("ConPTY resize 成功: %sx%s", cols, rows)
                except Exception as e:
                    _dbg("ConPTY resize 失败: %s", e)
            elif sys.platform != 'win32' and self._fd is not None:
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
        _dbg("stop() 被调用")
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

            # 关闭伪控制台（先尝试 kernel32，失败则忽略）
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
