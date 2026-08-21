# -*- coding: utf-8 -*-
"""Optional progress / cancel hooks for long-running weed solvers.

Hosts install hooks around ``generate_weeds`` (Apply button / Inkscape
dialog). Phase names come from ``debug.phase`` and a few explicit calls.
Geometry callbacks fire on each accepted weed segment (``_add_seg``).
"""
from __future__ import division

_progress_cb = None
_cancel_cb = None
_geometry_cb = None


class WeedCancelled(Exception):
    """Raised when a host cancel callback requests abort."""


def install(progress=None, cancel=None, geometry=None):
    """Install hooks for the current run (``None`` clears that hook)."""
    global _progress_cb, _cancel_cb, _geometry_cb
    _progress_cb = progress
    _cancel_cb = cancel
    _geometry_cb = geometry


def clear():
    install(None, None, None)


def report(phase):
    """Publish a short phase label to the host, then check cancel."""
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


def check_cancel():
    cb = _cancel_cb
    if cb is not None and cb():
        raise WeedCancelled('weed generation cancelled')
