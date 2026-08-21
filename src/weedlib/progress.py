# -*- coding: utf-8 -*-
"""Optional progress / cancel / pause hooks for long-running weed solvers.

Hosts install hooks around ``generate_weeds`` (Inkscape dialog, tests).
Phase names come from ``debug.phase`` and a few explicit calls.
Geometry callbacks fire on each accepted weed segment (``_add_seg``).

Pause is cooperative: the worker blocks in ``check_pause`` / ``check_cancel``
until the host clears the pause condition (or cancels).
"""
from __future__ import division

import time

_progress_cb = None
_cancel_cb = None
_pause_cb = None
_geometry_cb = None


class WeedCancelled(Exception):
    """Raised when a host cancel callback requests abort."""


def install(progress=None, cancel=None, geometry=None, pause=None):
    """Install hooks for the current run (``None`` clears that hook).

    Parameters
    ----------
    progress : callable(str), optional
        Phase label callback.
    cancel : callable() -> bool, optional
        Return True to abort with ``WeedCancelled``.
    geometry : callable(seg), optional
        Called with ``(x0, y0, x1, y1)`` on each accepted segment.
    pause : callable() -> bool, optional
        Return True while the run should block (inspect / resume later).
        Cancel is still honored while paused. Keyword preferred so older
        ``install(progress, cancel, geometry)`` call sites stay valid.
    """
    global _progress_cb, _cancel_cb, _pause_cb, _geometry_cb
    _progress_cb = progress
    _cancel_cb = cancel
    _geometry_cb = geometry
    _pause_cb = pause


def clear():
    install(None, None, None, None)


def report(phase):
    """Publish a short phase label to the host, then check pause/cancel."""
    cb = _progress_cb
    if cb is not None:
        try:
            cb(str(phase))
        except Exception:
            pass
    check_cancel()


def report_segment(seg):
    """Notify host of an accepted weed segment ``(x0, y0, x1, y1)``."""
    check_cancel()
    cb = _geometry_cb
    if cb is None:
        return
    try:
        cb(seg)
    except WeedCancelled:
        raise
    except Exception:
        pass


def check_pause():
    """Block while the host reports paused; cancel still aborts."""
    while True:
        cancel = _cancel_cb
        if cancel is not None and cancel():
            raise WeedCancelled('weed generation cancelled')
        pause = _pause_cb
        if pause is None or not pause():
            return
        time.sleep(0.05)


def check_cancel():
    """Honor pause (block) then cancel (raise)."""
    check_pause()
    cb = _cancel_cb
    if cb is not None and cb():
        raise WeedCancelled('weed generation cancelled')
