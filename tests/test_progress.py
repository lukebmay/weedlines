# -*- coding: utf-8 -*-
"""Progress / cancel / pause hooks for long-running solvers."""
from __future__ import division

import threading
import time

import pytest

pytest.importorskip('PyQt5', reason='Qt binding required')

from weedlib.qt import QPainterPath, QRectF
from weedlib import progress, generate_weeds
from weedlib.progress import WeedCancelled


def test_cancel_raises_during_grid():
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
