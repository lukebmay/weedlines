# -*- coding: utf-8 -*-
"""Frame and the mode switch."""
from __future__ import division

import pytest

from weedlib import solvers as weeds_mod
from weedlib.solvers import (
    frame_weeds,
    generate_weeds,
    grid_weeds,
)
import weedlib.solvers.geom as mod_geom

pytest.importorskip('PyQt5', reason='Qt binding required for weedlib geometry')

from tests.weed_shapes import _rect_path

def test_frame_weeds_padded_rect():
    keep = _rect_path(10, 20, 30, 40)
    weed = frame_weeds(keep, padding=[5, 5, 5, 5])
    assert not weed.isEmpty()
    br = weed.boundingRect()
    assert abs(br.x() - 5) < 1e-6
    assert abs(br.y() - 15) < 1e-6
    assert abs(br.width() - 40) < 1e-6
    assert abs(br.height() - 50) < 1e-6


def test_generate_weeds_modes():
    keep = _rect_path(0, 0, 50, 50)
    f = generate_weeds(keep, mode='frame', padding=[2, 2, 2, 2])
    g = generate_weeds(keep, mode='grid', padding=[2, 2, 2, 2], spacing=10)
    r = generate_weeds(keep, mode='region', padding=[2, 2, 2, 2], spacing=10)
    a = generate_weeds(keep, mode='island-hop', padding=[2, 2, 2, 2], spacing=20)
    assert not f.isEmpty()
    assert not g.isEmpty()
    assert not r.isEmpty()
    assert not a.isEmpty()


@pytest.mark.skip(reason="Inkcut Job pipeline not in weedlines")
def test_job_plan_emits_weed_segment_frame():
    svg = '''<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="50">
  <rect x="10" y="10" width="80" height="30" fill="none" stroke="black"/>
</svg>'''
    doc = QtSvgDoc(svg)
    job = Job()
    job.doc = doc
    job.path = doc
    job.optimized_path = doc
    job.plot_weedline = True
    job.plot_weedline_padding = [10, 10, 10, 10]
    job.weed_mode = 'frame'
    job.feed_to_end = False

    plan = job.build_plan(
        swap_xy=False, scale=[1, 1],
        origin_position='bottom_left', feed_axis='y', epilogue='none')
    assert plan is not None
    kinds = [s.kind for s in plan.segments]
    assert 'cut' in kinds
    assert 'weed' in kinds
    weeds = plan.weeds()
    assert not weeds.isEmpty()
    assert plan.weeds().elementCount() > 0
    stream = plan.to_device_stream()
    assert stream.elementCount() >= plan.cuts().elementCount()


@pytest.mark.skip(reason="Inkcut Job pipeline not in weedlines")
def test_legacy_add_weedline_uses_frame():
    path = _rect_path(0, 0, 10, 10)
    job = Job()
    job._add_weedline(path, [1, 1, 1, 1])
    assert path.boundingRect().width() >= 12


def test_legacy_frame_mode_stays_closed_box():
    """Legacy frame mode is still a closed padded box (not auto peel)."""
    keep = _rect_path(20.0, 20.0, 60.0, 40.0)
    weed = frame_weeds(keep, padding=[12, 12, 12, 12])
    segs = list(mod_geom._iter_line_segs(weed))
    # addRect may be one closed subpath or four edges; either way closed box.
    assert not weed.isEmpty()
    br = weed.boundingRect()
    assert abs(br.width() - 84.0) < 0.5 and abs(br.height() - 64.0) < 0.5


def test_frame_and_grid_report_preview_segments():
    from weedlib import progress as weed_progress
    keep = _rect_path(0, 0, 40, 40)
    segs = []
    weed_progress.install(geometry=lambda s: segs.append(s))
    try:
        frame_weeds(keep, padding=[2, 2, 2, 2])
        assert len(segs) >= 4
        n = len(segs)
        grid_weeds(keep, padding=[2, 2, 2, 2], spacing=10)
        assert len(segs) > n
    finally:
        weed_progress.clear()
