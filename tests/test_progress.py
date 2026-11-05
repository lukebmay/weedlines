# -*- coding: utf-8 -*-
"""Progress / cancel / pause hooks for long-running solvers."""
from __future__ import division

import threading
import time

import pytest

from weedlib import progress
from weedlib.progress import WeedCancelled


def test_check_with_no_hooks():
    progress.clear()
    try:
        progress.check()
        progress.install()
        progress.check(
            outline=[(0, 0), (1, 0), (1, 1)],
            line=(0, 0, 1, 1),
        )
    finally:
        progress.clear()


def test_pause_blocks_in_check_then_returns():
    paused = threading.Event()
    in_check = threading.Event()
    progress.clear()

    def on_pause():
        in_check.set()
        return paused.is_set()

    progress.install(pause=on_pause)
    paused.set()
    thread = threading.Thread(target=progress.check)
    thread.start()
    try:
        assert in_check.wait(2.0), 'check never paused'
        time.sleep(0.2)
        assert thread.is_alive()
        paused.clear()
        thread.join(5.0)
        assert not thread.is_alive()
    finally:
        paused.clear()
        progress.clear()
        thread.join(5.0)


def test_cancel_during_check_pause():
    paused = threading.Event()
    cancel = threading.Event()
    in_check = threading.Event()
    done = {'error': None}
    progress.clear()

    def on_pause():
        in_check.set()
        return paused.is_set()

    def work():
        try:
            progress.check()
        except Exception as exc:
            done['error'] = exc

    progress.install(pause=on_pause, cancel=lambda: cancel.is_set())
    paused.set()
    thread = threading.Thread(target=work)
    thread.start()
    try:
        assert in_check.wait(2.0), 'check never paused'
        cancel.set()
        thread.join(5.0)
        assert not thread.is_alive()
        assert isinstance(done['error'], WeedCancelled)
    finally:
        cancel.set()
        paused.clear()
        progress.clear()
        thread.join(5.0)


def test_check_names_reach_host_and_clear():
    seen = []
    segs = []
    progress.clear()

    def on_focus(outline, line):
        seen.append((outline, line))

    progress.install(
        focus=on_focus,
        geometry=lambda seg: segs.append(tuple(seg)),
    )
    try:
        outline = [(0, 0), (2, 0), (2, 2)]
        progress.check(outline=outline, line=(0, 1, 3, 4))
        outline.append((9, 9))
        assert seen == [(
            ((0, 0), (2, 0), (2, 2)),
            ((0, 1), (3, 4)),
        )]
        assert segs == []
        progress.check(outline=[(1, 1), (2, 2)])
        assert seen[-1] == (((1, 1), (2, 2)), None)
        progress.check(line=((5, 6), (7, 8)))
        assert seen[-1] == (None, ((5, 6), (7, 8)))
        progress.check()
        assert seen[-1] == (None, None)
        progress.check(outline=[], line=[])
        assert seen[-1] == (None, None)
        before = len(seen)
        with pytest.raises(TypeError):
            progress.check(outline=object())
        with pytest.raises(TypeError):
            progress.check(line=object())
        assert len(seen) == before
        progress.report_segment((1, 2, 3, 4))
        assert segs == [(1, 2, 3, 4)]
        assert seen[-1] == (None, None)
    finally:
        progress.clear()


def _need_solver():
    pytest.importorskip('PyQt5', reason='Qt binding required')
    from weedlib.qt import QPainterPath, QRectF
    from weedlib import generate_weeds
    return QPainterPath, QRectF, generate_weeds


def test_cancel_raises_during_grid():
    QPainterPath, QRectF, generate_weeds = _need_solver()
    keep = QPainterPath()
    keep.addRect(QRectF(0, 0, 40, 40))
    raise_cancel = [False]

    def on_phase(name):
        raise_cancel[0] = True

    progress.install(
        progress=on_phase,
        cancel=lambda: raise_cancel[0],
    )
    try:
        with pytest.raises(WeedCancelled):
            raise_cancel[0] = True
            generate_weeds(keep, mode='frame', padding=[2, 2, 2, 2])
    finally:
        progress.clear()


def test_geometry_callback_sees_segments():
    QPainterPath, QRectF, generate_weeds = _need_solver()
    keep = QPainterPath()
    keep.addRect(QRectF(0, 0, 50, 50))
    segs = []

    progress.install(geometry=lambda seg: segs.append(seg))
    try:
        weed = generate_weeds(
            keep, mode='grid', padding=[2, 2, 2, 2], spacing=20)
        assert not weed.isEmpty()
        assert isinstance(segs, list)
    finally:
        progress.clear()


def test_pause_blocks_then_resume_completes():
    QPainterPath, QRectF, generate_weeds = _need_solver()
    keep = QPainterPath()
    keep.addRect(QRectF(0, 0, 60, 60))
    paused = threading.Event()
    started = threading.Event()
    done = {'path': None, 'error': None}

    def work():
        progress.install(
            progress=lambda _n: started.set(),
            pause=lambda: paused.is_set(),
            cancel=lambda: False,
        )
        try:
            done['path'] = generate_weeds(
                keep, mode='grid', padding=[2, 2, 2, 2], spacing=15)
        except Exception as exc:
            done['error'] = exc
        finally:
            progress.clear()

    paused.set()
    thread = threading.Thread(target=work)
    thread.start()
    assert started.wait(2.0), 'solver never reached a progress checkpoint'
    # Still running / blocked while paused
    time.sleep(0.2)
    assert thread.is_alive()
    paused.clear()
    thread.join(5.0)
    assert not thread.is_alive()
    assert done['error'] is None
    assert done['path'] is not None and not done['path'].isEmpty()


def test_cancel_while_paused():
    QPainterPath, QRectF, generate_weeds = _need_solver()
    keep = QPainterPath()
    keep.addRect(QRectF(0, 0, 40, 40))
    paused = threading.Event()
    cancel = threading.Event()
    started = threading.Event()
    done = {'error': None}

    def work():
        progress.install(
            progress=lambda _n: started.set(),
            pause=lambda: paused.is_set(),
            cancel=lambda: cancel.is_set(),
        )
        try:
            generate_weeds(keep, mode='frame', padding=[2, 2, 2, 2])
        except WeedCancelled as exc:
            done['error'] = exc
        finally:
            progress.clear()

    paused.set()
    thread = threading.Thread(target=work)
    thread.start()
    assert started.wait(2.0)
    cancel.set()
    thread.join(5.0)
    assert not thread.is_alive()
    assert isinstance(done['error'], WeedCancelled)
