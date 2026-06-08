# -*- coding: utf-8 -*-
"""嵌入式终端 — 伪终端 (pty) + 子进程（Windows ConPTY / Unix pty）"""

import os
import sys
import subprocess
import threading
import signal


class TerminalSession:
    """单个终端会话"""

    def __init__(self, shell=None):
        self._fd = None
        self._proc = None
        self._reader = None
        self._running = False
        self._shell = shell or os.environ.get('SHELL', '/bin/bash')
        self._on_output = None

        # Windows ConPTY
        self._conpty_hpc = None
        self._conpty_in_handle = None
        self._conpty_out_handle = None
        self._conpty_pi = None
        self._conpty_mode = False

    # ==================== 启动 ====================

    def start(self, on_output, cols=80, rows=24):
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
        import pty as _pty
        master_fd, slave_fd = _pty.openpty()
        self._fd = master_fd
        try:
            import fcntl, struct, termios
            winsize = struct.pack('HHHH', rows, cols, 0, 0)
            fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, winsize)
        except Exception:
            pass
        env = os.environ.copy()
        env['TERM'] = 'xterm-256color'
        self._proc = subprocess.Popen(
            [self._shell], stdin=slave_fd, stdout=slave_fd, stderr=slave_fd,
            close_fds=True, preexec_fn=os.setsid, env=env,
            cwd=os.path.expanduser('~'),
        )
        os.close(slave_fd)

    # ==================== Windows: ConPTY ====================

    def _start_windows(self, cols, rows):
        if self._try_conpty(cols, rows):
            return
        self._start_windows_pipe()

    def _try_conpty(self, cols, rows):
        """ConPTY 伪终端（Windows 10 1809+）"""
        try:
            import ctypes
            from ctypes import wintypes, byref, POINTER

            kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

            try:
                create_pc = kernel32.CreatePseudoConsole
            except AttributeError:
                return False

            class COORD(ctypes.Structure):
                _fields_ = [('X', ctypes.c_short), ('Y', ctypes.c_short)]

            create_pc.argtypes = [
                COORD, wintypes.HANDLE, wintypes.HANDLE,
                wintypes.DWORD, POINTER(wintypes.HANDLE),
            ]
            create_pc.restype = wintypes.HRESULT

            # 创建管道
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

            # 创建伪控制台 (hInput=in_read, hOutput=out_write)
            size = COORD(ctypes.c_short(cols), ctypes.c_short(rows))
            hpc = wintypes.HANDLE()
            if create_pc(size, in_read, out_write, 0, byref(hpc)) != 0:
                for h in (in_read, in_write, out_read, out_write):
                    kernel32.CloseHandle(h)
                return False

            # 通过 STARTUPINFOEX 将 ConPTY 句柄传给子进程
            success, pi = self._conpty_create_process(
                kernel32, hpc,
                in_read.value, in_write.value,
                out_read.value, out_write.value,
            )
            if not success:
                kernel32.ClosePseudoConsole(hpc)
                return False

            # 保存句柄，用于 ReadFile / WriteFile
            self._conpty_out_handle = out_read.value
            self._conpty_in_handle = in_write.value
            self._fd = out_read.value  # 兼容 Unix 路径
            self._conpty_hpc = hpc
            self._conpty_pi = pi
            self._conpty_mode = True
            self._proc = True
            return True
        except Exception:
            return False

    def _conpty_create_process(self, kernel32, hpc, in_read, in_write,
                                out_read, out_write):
        """CreateProcessW + ConPTY 属性"""
        import ctypes
        from ctypes import wintypes, byref, sizeof, POINTER, cast

        PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE = 0x00020016
        EXTENDED_STARTUPINFO_PRESENT = 0x00080000

        class STARTUPINFOW(ctypes.Structure):
            _fields_ = [
                ('cb', wintypes.DWORD), ('lpReserved', wintypes.LPWSTR),
                ('lpDesktop', wintypes.LPWSTR), ('lpTitle', wintypes.LPWSTR),
                ('dwX', wintypes.DWORD), ('dwY', wintypes.DWORD),
                ('dwXSize', wintypes.DWORD), ('dwYSize', wintypes.DWORD),
                ('dwXCountChars', wintypes.DWORD), ('dwYCountChars', wintypes.DWORD),
                ('dwFillAttribute', wintypes.DWORD), ('dwFlags', wintypes.DWORD),
                ('wShowWindow', wintypes.WORD), ('cbReserved2', wintypes.WORD),
                ('lpReserved2', POINTER(wintypes.BYTE)),
                ('hStdInput', wintypes.HANDLE), ('hStdOutput', wintypes.HANDLE),
                ('hStdError', wintypes.HANDLE),
            ]

        class STARTUPINFOEXW(ctypes.Structure):
            _fields_ = [
                ('StartupInfo', STARTUPINFOW),
                ('lpAttributeList', ctypes.c_void_p),
            ]

        class PROCESS_INFORMATION(ctypes.Structure):
            _fields_ = [
                ('hProcess', wintypes.HANDLE), ('hThread', wintypes.HANDLE),
                ('dwProcessId', wintypes.DWORD), ('dwThreadId', wintypes.DWORD),
            ]

        # 初始化属性列表
        attr_size = ctypes.c_size_t()
        kernel32.InitializeProcThreadAttributeList(None, 1, 0, byref(attr_size))
        if attr_size.value == 0:
            self._close_handles(kernel32, in_read, in_write, out_read, out_write)
            return False, None
        attr_list = ctypes.create_string_buffer(attr_size.value)
        if not kernel32.InitializeProcThreadAttributeList(attr_list, 1, 0, byref(attr_size)):
            self._close_handles(kernel32, in_read, in_write, out_read, out_write)
            return False, None

        # 设置 ConPTY 属性
        if not kernel32.UpdateProcThreadAttribute(
            attr_list, 0, PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE,
            byref(hpc), ctypes.sizeof(ctypes.c_void_p), None, None,
        ):
            kernel32.DeleteProcThreadAttributeList(attr_list)
            self._close_handles(kernel32, in_read, in_write, out_read, out_write)
            return False, None

        # 创建进程
        si = STARTUPINFOEXW()
        si.StartupInfo.cb = sizeof(STARTUPINFOEXW)
        si.lpAttributeList = cast(attr_list, ctypes.c_void_p)

        pi = PROCESS_INFORMATION()
        cmdline = ctypes.create_unicode_buffer(
            os.environ.get('COMSPEC', 'cmd.exe'))
        home = os.path.expanduser('~')

        success = kernel32.CreateProcessW(
            None, cmdline, None, None, False,
            EXTENDED_STARTUPINFO_PRESENT,
            None, home,
            ctypes.byref(si), ctypes.byref(pi),
        )

        kernel32.DeleteProcThreadAttributeList(attr_list)
        # ConPTY 已接管 in_read 和 out_write，关闭本侧引用
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

    # ---- PIPE 回退 ----

    def _start_windows_pipe(self):
        self._proc = subprocess.Popen(
            os.environ.get('COMSPEC', 'cmd.exe'),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, cwd=os.path.expanduser('~'),
        )
        self._fd = self._proc.stdout.fileno()

    # ==================== 读取 ====================

    def _read_loop(self):
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
        for line in iter(self._proc.stdout.readline, b''):
            if not self._running:
                break
            if self._on_output:
                self._on_output(line.decode('utf-8', errors='replace'))

    def _read_conpty(self):
        """ConPTY 输出读取 — ReadFile 直读句柄"""
        import ctypes
        from ctypes import wintypes, byref
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        buf = ctypes.create_string_buffer(4096)
        while self._running:
            bytes_read = wintypes.DWORD(0)
            if not kernel32.ReadFile(
                self._conpty_out_handle, buf, 4096, byref(bytes_read), None
            ) or bytes_read.value == 0:
                break
            data = buf.raw[:bytes_read.value]
            if self._on_output:
                # 优先 GBK（中文 Windows cmd.exe 输出），失败则 UTF-8
                try:
                    text = data.decode('gbk')
                except Exception:
                    try:
                        text = data.decode('utf-8')
                    except Exception:
                        text = data.decode('utf-8', errors='replace')
                self._on_output(text)

    # ==================== 写入 ====================

    def write(self, data):
        if not self._running:
            return
        try:
            if self._conpty_mode and self._conpty_in_handle is not None:
                import ctypes
                from ctypes import wintypes, byref
                kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
                payload = data.encode('utf-8')
                written = wintypes.DWORD(0)
                kernel32.WriteFile(
                    self._conpty_in_handle, payload, len(payload),
                    byref(written), None,
                )
            elif sys.platform == 'win32' and isinstance(self._proc, subprocess.Popen):
                self._proc.stdin.write(data.encode('utf-8'))
                self._proc.stdin.flush()
            elif self._fd is not None:
                os.write(self._fd, data.encode('utf-8'))
        except Exception:
            pass

    # ==================== 大小调整 ====================

    def resize(self, cols, rows):
        try:
            if self._conpty_hpc is not None:
                self._resize_conpty(cols, rows)
            elif sys.platform != 'win32' and self._fd is not None:
                import fcntl, struct, termios
                winsize = struct.pack('HHHH', rows, cols, 0, 0)
                fcntl.ioctl(self._fd, termios.TIOCSWINSZ, winsize)
        except Exception:
            pass

    def _resize_conpty(self, cols, rows):
        try:
            import ctypes
            kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
            class COORD(ctypes.Structure):
                _fields_ = [('X', ctypes.c_short), ('Y', ctypes.c_short)]
            kernel32.ResizePseudoConsole(
                self._conpty_hpc, COORD(ctypes.c_short(cols), ctypes.c_short(rows)))
        except Exception:
            pass

    # ==================== 停止 ====================

    def stop(self):
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
                self._proc.wait(timeout=2)
            except Exception:
                try:
                    self._proc.kill()
                    self._proc.wait(timeout=1)
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
        except Exception:
            pass
        finally:
            self._conpty_hpc = None
            self._conpty_in_handle = None
            self._conpty_out_handle = None
            self._fd = None
            self._conpty_pi = None
            self._proc = None
