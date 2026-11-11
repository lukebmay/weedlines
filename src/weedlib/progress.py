# -*- coding: utf-8 -*-
"""Optional progress / cancel / pause hooks for long-running weed solvers.

Hosts install hooks around ``generate_weeds`` (Inkscape dialog, tests).
Phase names come from ``debug.phase`` and a few explicit calls.
Geometry callbacks fire on each accepted weed segment (``_add_seg``).

Pause is cooperative: the worker blocks in ``check_pause`` / ``check_cancel``
until the host clears the pause condition (or cancels).

``check`` is that same pause and cancel. It may also name one object
outline and one candidate line. The name is not a cut.
"""
from __future__ import division

import time

_progress_cb = None
_cancel_cb = None
_pause_cb = None
_geometry_cb = None
_focus_cb = None
_stage_open = False


class WeedCancelled(Exception):
    """Raised when a host cancel callback requests abort."""


def install(progress=None, cancel=None, geometry=None, pause=None,
            focus=None):
    """Install hooks for the current run (``None`` clears that hook).

    Parameters
    ----------
    progress : callable(str, str), optional
        Label callback. The second argument is ``stage``,
        ``substage``, or empty when the name is neither.
    cancel : callable() -> bool, optional
        Return True to abort with ``WeedCancelled``.
    geometry : callable(seg), optional
        Called with ``(x0, y0, x1, y1)`` on each accepted segment.
    pause : callable() -> bool, optional
        Return True while the run should block (inspect / resume later).
        Cancel is still honored while paused. Keyword preferred so older
        ``install(progress, cancel, geometry)`` call sites stay valid.
    focus : callable(outline, line), optional
        Called from ``check`` with the current names. Each argument is
        a tuple of ``(x, y)`` points, or ``None`` when that mark is
        absent. A line is exactly two points. This is not a cut.
    """
    global _progress_cb, _cancel_cb, _pause_cb, _geometry_cb, _focus_cb
    global _stage_open
    _progress_cb = progress
    _cancel_cb = cancel
    _geometry_cb = geometry
    _pause_cb = pause
    _focus_cb = focus
    _stage_open = False


def clear():
    install(None, None, None, None, None)


def report(name, stage=False, substage=False):
    """Publish a stage or substage label, then check pause/cancel.

    The mode ``generate_weeds`` reports is a stage. A phase
    entered while that stage is open is a substage. The kind
    is set with the log quiet.
    """
    global _stage_open
    if stage:
        kind = 'stage'
        _stage_open = True
    elif substage and _stage_open:
        kind = 'substage'
    else:
        kind = ''
    cb = _progress_cb
    if cb is not None:
        try:
            cb(str(name), kind)
        except Exception:
            pass
    check_cancel()


def close_stage():
    """The stage stays open until the run that reported it returns."""
    global _stage_open
    _stage_open = False


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


def check(outline=None, line=None):
    """Name one outline and one candidate line, then pause or cancel.

    *outline* is a sequence of ``(x, y)`` points, or omitted when
    there is no outline mark. *line* is ``(x0, y0, x1, y1)`` or two
    ``(x, y)`` points, or omitted when there is no line mark. The
    host receives a copy: a tuple of ``(x, y)`` points, and a line
    is exactly two points. ``None`` means there is no mark of that
    kind. An empty sequence is the same as omitting the name. A
    call that names neither clears the previous name. The name is
    not a cut and not a ``QPainterPath``.

    With no hooks installed, the call still returns. Pause blocks
    here until the host clears it. Cancel raises ``WeedCancelled``,
    including while paused.
    """
    outline = _outline_coords(outline)
    line = _line_coords(line)
    cb = _focus_cb
    if cb is not None:
        try:
            cb(outline, line)
        except WeedCancelled:
            raise
        except Exception:
            pass
    check_cancel()


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_point(value):
    if isinstance(value, (str, bytes)):
        return False
    try:
        count = len(value)
    except TypeError:
        return False
    if count != 2:
        return False
    return _is_number(value[0]) and _is_number(value[1])


def _outline_coords(value):
    """Copy an outline to ``(x, y)`` points, or ``None`` when unnamed."""
    if value is None:
        return None
    if isinstance(value, (str, bytes)):
        return _bad_outline()
    try:
        seq = tuple(value)
    except TypeError:
        return _bad_outline()
    if not seq:
        return None
    points = []
    for item in seq:
        if not _is_point(item):
            return _bad_outline()
        points.append((item[0], item[1]))
    return tuple(points)


def _bad_outline():
    raise TypeError('an outline is plain (x, y) coordinates')


def _line_coords(value):
    """Copy a candidate line to two points, or ``None`` when unnamed."""
    if value is None:
        return None
    if isinstance(value, (str, bytes)):
        return _bad_line()
    try:
        seq = tuple(value)
    except TypeError:
        return _bad_line()
    if not seq:
        return None
    if len(seq) == 4 and all(_is_number(item) for item in seq):
        return ((seq[0], seq[1]), (seq[2], seq[3]))
    if len(seq) == 2 and _is_point(seq[0]) and _is_point(seq[1]):
        return ((seq[0][0], seq[0][1]), (seq[1][0], seq[1][1]))
    return _bad_line()


def _bad_line():
    raise TypeError('a candidate line is plain coordinates')
