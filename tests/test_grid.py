# -*- coding: utf-8 -*-
"""Grid, snap, and the region alias."""
from __future__ import division

import math

import pytest

from weedlib.qt import QPainterPath, QRectF
from weedlib.solvers import (
    grid_weeds,
    region_weeds,
    sample_points_on_path,
    weed_path_stats,
    even_odd_keep_fill,
    padded_work_rect,
)
import weedlib.solvers.emit as mod_emit
import weedlib.solvers.grid as mod_grid

pytest.importorskip('PyQt5', reason='Qt binding required for weedlib geometry')

from tests.weed_shapes import (
    _IN_KEEP_BUDGET,
    _rect_path,
    _circle_path,
    _inkscape_fill_stroke_twin,
    _letter_o,
    _fraction_inside,
    _line_segments,
    _mid_ring_samples,
    _framed_hi,
)

def test_grid_does_not_slice_keep_island():
    keep = _rect_path(20, 20, 40, 40)
    keep_fill = even_odd_keep_fill(keep)
    weed = grid_weeds(keep, padding=[10, 10, 10, 10], spacing=8)
    assert not weed.isEmpty()
    frac = _fraction_inside(weed, keep_fill, step=1.0)
    assert frac < _IN_KEEP_BUDGET, "grid weed sliced keep (frac=%s)" % frac


def test_grid_letter_o_grids_hole_not_ring():
    keep = _letter_o()
    pad = [8, 8, 8, 8]
    weed = grid_weeds(keep, padding=pad, spacing=10)
    keep_fill = even_odd_keep_fill(keep)
    frac = _fraction_inside(weed, keep_fill, step=1.0)
    assert frac < _IN_KEEP_BUDGET, "grid sliced O ring (frac=%s)" % frac
    assert not _mid_ring_samples(weed, 50, 50, 22.0, 38.0), (
        "grid put weeds in the O ring")
    hole = _circle_path(50, 50, 18)
    pts = sample_points_on_path(weed, step=1.5)
    in_hole = sum(1 for p in pts if hole.contains(p))
    assert in_hole > 0, "grid never entered O hole waste"


def test_grid_ends_meet_keep_weed_or_work():
    """Every remaining grid end is within tol of keep, weed, or work."""
    keep = _rect_path(20, 20, 40, 40)
    pad = [10, 10, 10, 10]
    spacing = 8.0
    tol = 1.5
    weed = grid_weeds(keep, padding=pad, spacing=spacing)
    work = padded_work_rect(keep, pad)
    segs = _line_segments(weed)
    assert segs, "expected grid segments"
    keep_edges = mod_emit._keep_outline_edges(keep)
    for seg in segs:
        dx, dy = seg[2] - seg[0], seg[3] - seg[1]
        ln = math.hypot(dx, dy)
        assert ln > 1e-9
        ux, uy = dx / ln, dy / ln
        assert mod_emit._end_anchored(
            seg[0], seg[1], segs, keep_edges, skip=seg, tol=tol, work=work,
            keep_path=keep, weed_dir=(ux, uy)), seg
        assert mod_emit._end_anchored(
            seg[2], seg[3], segs, keep_edges, skip=seg, tol=tol, work=work,
            keep_path=keep, weed_dir=(-ux, -uy)), seg


def test_grid_sample_gap_snaps_not_float():
    """Short-of-keep stubs snap to outline; true floaters are dropped."""
    keep = _rect_path(20, 20, 40, 40)
    work = QRectF(10, 10, 60, 60)
    keep_edges = mod_emit._keep_outline_edges(keep)
    # Simulate pre-snap sample gap: 1.8 mm short of keep (tol 1.5 misses).
    raw = [
        (40.0, 10.0, 40.0, 18.2),
        (40.0, 61.8, 40.0, 70.0),
    ]
    snapped = []
    for seg in raw:
        s = mod_grid._snap_grid_seg(seg, False, keep_edges, [], work)
        if s is not None:
            snapped.append(s)
    assert len(snapped) == 2, snapped
    for seg in snapped:
        for px, py in ((seg[0], seg[1]), (seg[2], seg[3])):
            on_work = mod_grid._on_work_edge(px, py, work, tol=1.5)
            near_keep = mod_emit._point_near_edges(px, py, keep_edges, 1.5)
            assert on_work or near_keep, (seg, px, py)
        # Keep-facing end should have extended from the 2.5 mm miss.
        ys = (seg[1], seg[3])
        assert min(abs(y - 20.0) for y in ys) <= 1e-3 or min(
            abs(y - 60.0) for y in ys) <= 1e-3, seg
    float_path = QPainterPath()
    float_path.moveTo(45, 45)
    float_path.lineTo(50, 50)
    for seg in snapped:
        float_path.moveTo(seg[0], seg[1])
        float_path.lineTo(seg[2], seg[3])
    cleaned = mod_emit._require_connected_ends(
        float_path, keep, tol=1.5, work=work)
    cleaned_segs = _line_segments(cleaned)
    assert len(cleaned_segs) == 2, cleaned_segs
    for seg in cleaned_segs:
        assert not (
            abs(seg[0] - 45) < 1e-6 and abs(seg[1] - 45) < 1e-6
        ), "floater stub must be removed"


def test_region_aliases_grid():
    keep = _letter_o()
    pad = [5, 5, 5, 5]
    a = region_weeds(keep, padding=pad, spacing=12)
    b = grid_weeds(keep, padding=pad, spacing=12)
    assert weed_path_stats(a)['segments'] == weed_path_stats(b)['segments']


@pytest.mark.skip(reason="Inkcut Job pipeline not in weedlines")
def test_job_plan_grid_mode_typed_weed():
    svg = '''<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="80" height="80">
  <rect x="20" y="20" width="40" height="40" fill="none" stroke="black"/>
</svg>'''
    doc = QtSvgDoc(svg)
    job = Job()
    job.doc = doc
    job.path = doc
    job.optimized_path = doc
    job.plot_weedline = True
    job.weed_mode = 'grid'
    job.weed_grid_spacing = 15
    job.plot_weedline_padding = [10, 10, 10, 10]

    plan = job.build_plan(
        swap_xy=False, scale=[1, 1],
        origin_position='bottom_left', feed_axis='y', epilogue='return')
    weed_segs = [s for s in plan.segments if s.kind == 'weed']
    assert len(weed_segs) >= 1
    assert all(s.meta.get('mode') == 'grid' for s in weed_segs)
    assert plan.segments[-1].kind == 'epilogue'
    assert any(s.kind == 'travel' for s in plan.segments)


def test_grid_framed_hi_covers_counter_and_surround():
    """Frame vinyl stays uncut; counter waste is hatched; work gets a surround."""
    keep = _inkscape_fill_stroke_twin(_framed_hi())
    pad = [12, 12, 12, 12]
    weed = grid_weeds(keep, padding=pad, spacing=15)
    keep_fill = even_odd_keep_fill(keep)
    assert _fraction_inside(weed, keep_fill, step=1.0) < _IN_KEEP_BUDGET
    # Counter waste (inside hole, outside letters) must receive hatch.
    hole = QPainterPath()
    hole.addRect(QRectF(6, 6, 108, 88))
    pts = sample_points_on_path(weed, step=2.0)
    in_counter = sum(
        1 for p in pts
        if hole.contains(p) and not keep_fill.contains(p))
    assert in_counter > 0, "grid never entered frame-counter waste"
    work = padded_work_rect(keep, pad)
    # Closed surround on the work edge (peel rail for any outer scrap).
    segs = _line_segments(weed)
    sides = 0
    for x0, y0, x1, y1 in segs:
        on_edge = (
            (abs(x0 - work.left()) <= 1.5 and abs(x1 - work.left()) <= 1.5)
            or (abs(x0 - work.right()) <= 1.5 and abs(x1 - work.right()) <= 1.5)
            or (abs(y0 - work.top()) <= 1.5 and abs(y1 - work.top()) <= 1.5)
            or (abs(y0 - work.bottom()) <= 1.5
                and abs(y1 - work.bottom()) <= 1.5))
        if on_edge:
            sides += 1
    assert sides >= 4, "expected padded surround rectangle, got %s edge segs" % sides


def test_grid_soft_clearance_keeps_tight_alleys():
    """Default grid must not use island-hop's 5 mm body floor."""
    keep = _framed_hi()
    pad = [12, 12, 12, 12]
    soft = grid_weeds(keep, padding=pad, spacing=15)
    # Force the old island-hop floors — should drop more hatch.
    strict = grid_weeds(
        keep, padding=pad, spacing=15,
        body_clearance=5.0, alpha_min=30.0)
    soft_n = weed_path_stats(soft)['segments']
    strict_n = weed_path_stats(strict)['segments']
    assert soft_n >= strict_n, (soft_n, strict_n)
    assert soft_n > 4, soft_n
