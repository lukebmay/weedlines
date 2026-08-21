# -*- coding: utf-8 -*-
"""Opt-in auto-weed decision / firm-rule debug log.

``WEEDLINES_LOG=1`` — clusters, peel-frame, rank picks, rejects, audit.
``WEEDLINES_LOG=2`` / ``trace`` — also every ``emit.accept``.
Legacy ``INKCUT_WEED_DEBUG`` is accepted as an alias.
Stderr via logger ``weedlib``. Does not change emit logic.

Greppable: ``rg 'phase\\.|island_hop\\.|emit\\.|reject'``.
"""
from __future__ import division

import logging
import os
from contextlib import contextmanager

_log = logging.getLogger('weedlib')
_configured = False
_phase_stack = []

_EP_NAMES = {0: 'corner', 1: 'frame', 2: 'edge'}


def level():
    """0=off, 1=decisions/audits, 2=also every emit.accept (WEEDLINES_LOG)."""
    v = (os.environ.get('WEEDLINES_LOG') or os.environ.get('INKCUT_WEED_DEBUG') or '').strip().lower()
    if v in ('', '0', 'false', 'no', 'off'):
        return 0
    if v in ('2', 'verbose', 'all', 'trace', 'debug'):
        return 2
    return 1


def enabled():
    """True when ``WEEDLINES_LOG`` (or legacy ``INKCUT_WEED_DEBUG``) is set."""
    return level() > 0


def _ensure_handler():
    global _configured
    if _configured or not enabled():
        return
    _configured = True
    _log.setLevel(logging.DEBUG)
    if not any(isinstance(h, logging.StreamHandler) for h in _log.handlers):
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter(
            '%(levelname)s weedlib: %(message)s'))
        _log.addHandler(handler)
        _log.propagate = False


def phase_name():
    return _phase_stack[-1] if _phase_stack else '-'


@contextmanager
def phase(name, **fields):
    """Push a named planner phase for nested emit / rank logs.

    Always reports *name* to ``weedlib.progress`` (Apply UI / cancel),
    even when ``WEEDLINES_LOG`` is off.
    """
    from . import progress as _progress
    _progress.report(name)
    if not enabled():
        try:
            yield
        finally:
            _progress.check_cancel()
        return
    _ensure_handler()
    _phase_stack.append(str(name))
    log('phase.enter', **fields)
    try:
        yield
    finally:
        log('phase.exit')
        if _phase_stack and _phase_stack[-1] == str(name):
            _phase_stack.pop()
        elif _phase_stack:
            _phase_stack.pop()
        _progress.check_cancel()


def log(event, **fields):
    """Emit one structured debug line: ``event key=val ...``.

    ``emit.accept`` is level-2 only (very noisy). Everything else is level 1+.
    """
    need = 2 if str(event) == 'emit.accept' else 1
    if level() < need:
        return
    _ensure_handler()
    parts = [str(event), 'phase=%s' % phase_name()]
    for key in sorted(fields):
        parts.append('%s=%s' % (key, _fmt(fields[key])))
    _log.debug(' '.join(parts))


def seg_fmt(seg):
    if seg is None:
        return 'None'
    return '(%.3f,%.3f)->(%.3f,%.3f)' % (
        float(seg[0]), float(seg[1]), float(seg[2]), float(seg[3]))


def ep_name(klass):
    return _EP_NAMES.get(int(klass), str(klass))


def _fmt(value):
    if value is None:
        return 'None'
    if isinstance(value, float):
        return '%.3f' % value
    if isinstance(value, bool):
        return '1' if value else '0'
    if isinstance(value, (tuple, list)):
        if (len(value) == 4
                and all(isinstance(x, (int, float)) for x in value)):
            return seg_fmt(value)
        if (len(value) == 2
                and all(isinstance(x, (int, float)) for x in value)):
            return '(%s,%s)' % (_fmt(value[0]), _fmt(value[1]))
        return '[' + ','.join(_fmt(v) for v in value) + ']'
    return str(value)


def bbox_fmt(rect):
    if rect is None or rect.isNull():
        return 'empty'
    return 'x=%.1f y=%.1f w=%.1f h=%.1f' % (
        rect.x(), rect.y(), rect.width(), rect.height())
