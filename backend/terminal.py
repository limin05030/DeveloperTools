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
        self._fd = None          # pty master fd
        self._proc = None        # shell 子进程
        self._reader = None      # 输出读取线程
        self._running = False
        self._shell = shell or os.environ.get('SHELL', '/bin/bash')
        self._on_output = None   # 输出回调 (data: str) -> None

    def start(self, on_output, cols=80, rows=24):
        """启动 shell 并开始读取输出"""
        self._on_output = on_output
        self._running = True

        if sys.platform == 'win32':
            self._start_windows()
        else:
            self._start_unix(cols, rows)

        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()

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
        )
        os.close(slave_fd)

    def _start_windows(self):
        """Windows: 通过 subprocess.PIPE 启动 cmd"""
        self._proc = subprocess.Popen(
            os.environ.get('COMSPEC', 'cmd.exe'),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=False, bufsize=0,
        )
        self._fd = self._proc.stdout.fileno()

    def _read_loop(self):
        """持续读取 shell 输出"""
        try:
            if sys.platform == 'win32' and self._proc:
                for line in iter(self._proc.stdout.readline, b''):
                    if not self._running:
                        break
                    if self._on_output:
                        self._on_output(line.decode('utf-8', errors='replace'))
            else:
                while self._running:
                    try:
                        data = os.read(self._fd, 4096)
                        if not data:
                            break
                        if self._on_output:
                            self._on_output(data.decode('utf-8', errors='replace'))
                    except (OSError, ValueError):
                        break
        except Exception:
            pass

    def write(self, data):
        """写入数据到 shell stdin"""
        if not self._running:
            return
        try:
            if sys.platform == 'win32' and self._proc:
                self._proc.stdin.write(data.encode('utf-8'))
                self._proc.stdin.flush()
            elif self._fd is not None:
                os.write(self._fd, data.encode('utf-8'))
        except Exception:
            pass

    def resize(self, cols, rows):
        """调整终端大小（仅 Unix pty 有效）"""
        if sys.platform == 'win32':
            return
        if self._fd is not None:
            try:
                import fcntl
                import struct
                import termios
                winsize = struct.pack('HHHH', rows, cols, 0, 0)
                fcntl.ioctl(self._fd, termios.TIOCSWINSZ, winsize)
            except Exception:
                pass

    def stop(self):
        """终止 shell 进程"""
        self._running = False
        if self._proc:
            try:
                if sys.platform == 'win32':
                    self._proc.kill()
                else:
                    os.killpg(os.getpgid(self._proc.pid), signal.SIGTERM)
            except Exception:
                pass
            self._proc = None
        if self._fd:
            try:
                os.close(self._fd)
            except Exception:
                pass
            self._fd = None
