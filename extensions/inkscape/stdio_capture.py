# -*- coding: utf-8 -*-
"""Capture OS-level stdout/stderr so Qt C++ chatter never reaches Inkscape.

Python ``sys.stderr = …`` does not catch ``qWarning`` writes to fd 2.
We dup those fds to a pipe, drain lines on a background thread, and keep
them for the dialog log. Logging to stderr during capture is avoided
(that would re-enter the pipe).
"""
from __future__ import division

import os
import sys
import threading
from collections import deque


class NativeStdioCapture(object):
    """Context manager: redirect fd 1/2 to a pipe and collect text lines."""

    def __init__(self):
        self.lines = deque(maxlen=500)
        self._stop = threading.Event()
        self._thread = None
        self._saved_out = None
        self._saved_err = None
        self._read_fd = None
        self._write_fd = None

    def __enter__(self):
        self._read_fd, self._write_fd = os.pipe()
        self._saved_out = os.dup(1)
        self._saved_err = os.dup(2)
        os.dup2(self._write_fd, 1)
        os.dup2(self._write_fd, 2)
        self._thread = threading.Thread(
            target=self._drain, name='weedlines-stdio')
        self._thread.daemon = True
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            sys.stdout.flush()
        except Exception:
            pass
        try:
            sys.stderr.flush()
        except Exception:
            pass
        if self._saved_out is not None:
            os.dup2(self._saved_out, 1)
            os.close(self._saved_out)
            self._saved_out = None
        if self._saved_err is not None:
            os.dup2(self._saved_err, 2)
            os.close(self._saved_err)
            self._saved_err = None
        if self._write_fd is not None:
            try:
                os.close(self._write_fd)
            except OSError:
                pass
            self._write_fd = None
        self._stop.set()
        if self._thread is not None:
            self._thread.join(1.0)
            self._thread = None
        if self._read_fd is not None:
            try:
                os.close(self._read_fd)
            except OSError:
                pass
            self._read_fd = None
        # Do not log to stderr here — that is Inkscape's stream again.
        # The dialog drains ``lines`` into its own log view instead.
        return False

    def _drain(self):
        buf = b''
        while True:
            try:
                chunk = os.read(self._read_fd, 4096)
            except OSError:
                break
            if not chunk:
                break
            buf += chunk
            while b'\n' in buf:
                raw, buf = buf.split(b'\n', 1)
                self._take_line(raw.decode('utf-8', 'replace'))
        if buf.strip():
            self._take_line(buf.decode('utf-8', 'replace'))

    def _take_line(self, line):
        line = line.rstrip('\r\n')
        if not line.strip():
            return
        # Deque only while fds are redirected — never log here.
        self.lines.append(line)

    def snapshot(self):
        """Return collected lines (copy)."""
        return list(self.lines)
