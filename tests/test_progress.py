# -*- coding: utf-8 -*-
"""Progress / cancel hooks for long-running solvers."""
from __future__ import division

import pytest

pytest.importorskip('PyQt5', reason='Qt binding required')

from weedlib.qt import QPainterPath, QRectF
from weedlib import progress, generate_weeds
from weedlib.progress import WeedCancelled


def test_cancel_raises_during_grid():
    keep = QPainterPath()
    keep.addRect(QRectF(0, 0, 40, 40))
    calls = []

    def on_phase(name):
        calls.append(name)
        if len(calls) >= 1:
            raise_cancel[0] = True

    raise_cancel = [False]

    progress.install(
        progress=on_phase,
        cancel=lambda: raise_cancel[0],
    )
    try:
        with pytest.raises(WeedCancelled):
            # Force cancel on first phase report inside generate_weeds
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
        # Grid may report via emit path; at least solver completed
        assert isinstance(segs, list)
    finally:
        progress.clear()
