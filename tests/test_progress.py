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


def _marks_are_one_each(outline, line):
    """A check names at most one outline and one trial line."""
    if outline is not None:
        assert isinstance(outline, tuple) and outline
        for pt in outline:
            assert len(pt) == 2
    if line is not None:
        assert len(line) == 2
        assert len(line[0]) == 2 and len(line[1]) == 2


def test_frame_and_grid_check_before_first_segment():
    """Host records a check from frame and from grid before any segment."""
    QPainterPath, QRectF, _generate = _need_solver()
    from weedlib.solvers import frame_weeds, grid_weeds

    keep = QPainterPath()
    keep.addRect(QRectF(0, 0, 80, 60))
    events = []

    def on_focus(outline, line):
        _marks_are_one_each(outline, line)
        events.append(('check', outline, line))

    def on_seg(seg):
        events.append(('seg', tuple(seg)))

    progress.clear()
    try:
        progress.install(focus=on_focus, geometry=on_seg)
        frame_weeds(keep, padding=[2, 2, 2, 2])
        kinds = [event[0] for event in events]
        assert 'check' in kinds and 'seg' in kinds
        assert kinds.index('check') < kinds.index('seg')

        events[:] = []
        grid_weeds(keep, padding=[2, 2, 2, 2], spacing=20)
        pre = []
        for event in events:
            if event[0] == 'seg':
                break
            pre.append(event)
        assert len(pre) > 1
        assert all(event[2] is not None for event in pre)
    finally:
        progress.clear()


def test_large_grid_cancel_at_start_raises():
    """Cancel set at the start aborts a hatch that would emit many lines."""
    QPainterPath, QRectF, _generate = _need_solver()
    from weedlib.solvers import grid_weeds

    keep = QPainterPath()
    keep.addRect(QRectF(0, 0, 400, 400))
    returned = None
    progress.clear()
    try:
        progress.install(cancel=lambda: True)
        with pytest.raises(WeedCancelled):
            returned = grid_weeds(
                keep, padding=[10, 10, 10, 10], spacing=5)
        assert returned is None
    finally:
        progress.clear()


def _two_by_two():
    from weedlib.qt import QPainterPath, QRectF
    path = QPainterPath()
    for i in range(2):
        for j in range(2):
            path.addRect(QRectF(i * 30, j * 40, 12, 24))
    return path


def test_seal_search_checks_while_it_runs():
    """Island-hop mouth search checks before that search returns."""
    pytest.importorskip('pyclipper')
    _QPainterPath, _QRectF, _generate = _need_solver()
    from weedlib import solvers
    from weedlib.solvers import island_hop_weeds

    seen = {'inside': False, 'checks': 0, 'emits': 0, 'during': []}
    real_mouth = solvers._mouth_seal
    real_emit = solvers._seg_emit_ok

    def wrap_mouth(*args, **kwargs):
        seen['inside'] = True
        seen['emits'] = 0
        try:
            return real_mouth(*args, **kwargs)
        finally:
            seen['inside'] = False

    def wrap_emit(*args, **kwargs):
        if seen['inside']:
            seen['emits'] += 1
        return real_emit(*args, **kwargs)

    def on_focus(outline, line):
        _marks_are_one_each(outline, line)
        if not seen['inside']:
            return
        seen['checks'] += 1
        # A check before the first emit, or after the last, does not count.
        if seen['emits'] > 0:
            seen['during'].append((seen['emits'], outline, line))

    solvers._mouth_seal = wrap_mouth
    solvers._seg_emit_ok = wrap_emit
    progress.clear()
    try:
        progress.install(focus=on_focus)
        weed = island_hop_weeds(
            _two_by_two(), padding=[10, 10, 10, 10], collar=4)
        assert not weed.isEmpty()
        assert seen['checks'] > 1
        assert seen['during']
        assert all(outline is None for _n, outline, _line in seen['during'])
        assert all(line is not None for _n, _outline, line in seen['during'])
    finally:
        solvers._mouth_seal = real_mouth
        solvers._seg_emit_ok = real_emit
        progress.clear()


def test_cancel_during_seal_search_returns_no_path():
    """Cancel inside the mouth search raises before a path is returned."""
    pytest.importorskip('pyclipper')
    _QPainterPath, _QRectF, _generate = _need_solver()
    from weedlib import solvers
    from weedlib.solvers import island_hop_weeds

    seen = {'inside': False, 'checks': 0}
    real_mouth = solvers._mouth_seal

    def wrap_mouth(*args, **kwargs):
        seen['inside'] = True
        try:
            return real_mouth(*args, **kwargs)
        finally:
            seen['inside'] = False

    def on_focus(outline, line):
        if seen['inside']:
            seen['checks'] += 1

    def cancel():
        return seen['inside'] and seen['checks'] > 0

    solvers._mouth_seal = wrap_mouth
    returned = None
    progress.clear()
    try:
        progress.install(focus=on_focus, cancel=cancel)
        with pytest.raises(WeedCancelled):
            returned = island_hop_weeds(
                _two_by_two(), padding=[10, 10, 10, 10], collar=4)
        assert returned is None
        assert seen['checks'] > 0
    finally:
        solvers._mouth_seal = real_mouth
        progress.clear()


def _u_keep():
    from weedlib.qt import QPainterPath
    path = QPainterPath()
    path.moveTo(0, 0)
    path.lineTo(100, 0)
    path.lineTo(100, 80)
    path.lineTo(80, 80)
    path.lineTo(80, 20)
    path.lineTo(20, 20)
    path.lineTo(20, 80)
    path.lineTo(0, 80)
    path.closeSubpath()
    return path


def test_pocket_search_checks_while_it_runs():
    """A bay search checks before that search accepts its segment."""
    pytest.importorskip('pyclipper')
    _QPainterPath, _QRectF, _generate = _need_solver()
    from weedlib import solvers
    from weedlib.solvers import island_hop_weeds

    seen = {'inside': False, 'checks': 0, 'named': 0}
    real = solvers._body_pocket_seals

    def wrap_pocket(*args, **kwargs):
        seen['inside'] = True
        try:
            return real(*args, **kwargs)
        finally:
            seen['inside'] = False

    def on_focus(outline, line):
        _marks_are_one_each(outline, line)
        if not seen['inside']:
            return
        seen['checks'] += 1
        if outline is not None and line is not None:
            seen['named'] += 1

    solvers._body_pocket_seals = wrap_pocket
    progress.clear()
    try:
        progress.install(focus=on_focus)
        weed = island_hop_weeds(
            _u_keep(), padding=[12, 12, 12, 12], collar=4)
        assert not weed.isEmpty()
        assert seen['checks'] > 1
        assert seen['named'] >= 1
    finally:
        solvers._body_pocket_seals = real
        progress.clear()
