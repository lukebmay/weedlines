# -*- coding: utf-8 -*-
"""Weed strategies: even-odd keep/waste, clip to work, no false reliefs."""
from __future__ import division

import math
import os

import pytest

from weedlib.qt import QPointF, QRectF, QPainterPath
from weedlib import solvers as weeds_mod
from weedlib.solvers import (
    DEFAULT_CHANNEL_STANDOFF, DEFAULT_COLLAR, DEFAULT_DELICATE_ANGLE_DEG,
    _ALPHA_HARD, _ALPHA_MIN_PEEL, _agglomerate_islands, _approx_bay_kappa,
    _bay_coast_length, _bay_has_undercut, _bay_kappa, _bay_mouth_already_sealed,
    _bay_mouth_width, _bay_should_seal, _body_pocket_seals,
    _closest_bay_mouth_corner, _cluster_keep_bodies, _convex_corners,
    _created_peel_angles, _deep_keep_peninsula_tips,
    _frontier_complexity, _frontier_run_metrics, _frontier_tip_count,
    _gap_mouths, _has_independent_waste_bays, _hull_bay_mouths,
    _included_angle_deg, _is_corridor_pair, _is_stacked_satellite,
    _isolation_collar_rings, _keep_frame_at, _channel_core,
    _mouth_between_keep_tips, _nest_closed_paths, _peel_axis, _peel_dir_at,
    _seal_corridor_pair,
    _peninsula_is_deep, _peninsula_should_detach,
    _point_seg_dist, _polyline_points, _run_arc_length, _run_chord_length,
    _seg_proper_cross, _vertex_weed_degree, _word_cluster_gap,
    island_hop_weeds, closed_fill_union, even_odd_keep_fill, frame_weeds,
    generate_weeds, grid_weeds, list_closed_subpaths, padded_work_rect,
    region_weeds, residual_waste_traps, sample_points_on_path,
    weed_path_stats, weed_sample_stats,
)

pytest.importorskip('PyQt5', reason='Qt binding required for weedlib geometry')
try:
    import pyclipper as _pyclipper  # noqa: F401
    _HAS_CLIPPER = True
except ImportError:
    _HAS_CLIPPER = False

requires_clipper = pytest.mark.skipif(
    not _HAS_CLIPPER, reason='pyclipper required for island-hop')


# Numerical graze on keep edges — far tighter than the old 8% lock-in.
_IN_KEEP_BUDGET = 0.02


def _rect_path(x, y, w, h):
    p = QPainterPath()
    p.addRect(QRectF(x, y, w, h))
    return p


def _circle_path(cx, cy, r):
    p = QPainterPath()
    p.addEllipse(QPointF(cx, cy), r, r)
    return p


def _letter_o(cx=50, cy=50, r_outer=40, r_inner=20):
    """Even-odd letter O: keep ring, hole waste."""
    p = QPainterPath()
    p.addPath(_circle_path(cx, cy, r_outer))
    p.addPath(_circle_path(cx, cy, r_inner))
    return p


def _letters_hi(ox=0, oy=0):
    """Separated H and I as united strokes."""
    def _united(rects):
        acc = QPainterPath()
        for x, y, w, h in rects:
            r = _rect_path(x, y, w, h)
            acc = acc.united(r) if not acc.isEmpty() else r
        return acc

    h = _united((
        (8 + ox, 18 + oy, 8, 54),
        (30 + ox, 18 + oy, 8, 54),
        (8 + ox, 39 + oy, 30, 10),
    ))
    i = _rect_path(62 + ox, 18 + oy, 8, 54)
    p = QPainterPath()
    p.addPath(h)
    p.addPath(i)
    return p


def _framed_hi():
    """Hollow rectangular border with HI in the counter."""
    p = QPainterPath()
    p.addRect(QRectF(0, 0, 120, 100))
    p.addRect(QRectF(6, 6, 108, 88))
    p.addPath(_letters_hi(ox=20, oy=8))
    return p


def _wreath_hi():
    """Ornaments around HI (siblings, not a nested hole)."""
    p = QPainterPath()
    for x, y in ((4, 4), (54, 2), (104, 4), (4, 40), (104, 40),
                 (4, 76), (54, 80), (104, 76)):
        p.addPath(_rect_path(x, y, 12, 12))
    p.addPath(_letters_hi(ox=26, oy=10))
    return p


def _quoted_blocks():
    """H i , t with quotes — punctuation as separate islands, no font."""
    def _united(rects):
        acc = QPainterPath()
        for x, y, w, h in rects:
            r = _rect_path(x, y, w, h)
            acc = acc.united(r) if not acc.isEmpty() else r
        return acc

    p = QPainterPath()
    p.addPath(_united((  # H
        (8, 18, 8, 54), (30, 18, 8, 54), (8, 39, 30, 10),
    )))
    p.addPath(_rect_path(50, 36, 6, 36))  # i stem
    p.addPath(_rect_path(50, 18, 6, 8))   # i dot
    p.addPath(_rect_path(64, 62, 6, 12))  # comma
    p.addPath(_rect_path(80, 18, 6, 54))  # t-ish stem
    p.addPath(_rect_path(80, 18, 16, 8))  # t bar
    p.addPath(_rect_path(112, 16, 4, 16))  # "
    p.addPath(_rect_path(120, 16, 4, 16))
    p.addPath(_rect_path(132, 18, 24, 54))  # O-ish
    p.addPath(_circle_path(144, 45, 10))    # O hole
    p.addPath(_rect_path(166, 16, 4, 16))  # closing "
    p.addPath(_rect_path(174, 16, 4, 16))
    return p


def _letter_a():
    outer = QPainterPath()
    outer.moveTo(40, 12)
    outer.lineTo(68, 72)
    outer.lineTo(54, 72)
    outer.lineTo(49, 56)
    outer.lineTo(31, 56)
    outer.lineTo(26, 72)
    outer.lineTo(12, 72)
    outer.closeSubpath()
    hole = QPainterPath()
    hole.moveTo(40, 30)
    hole.lineTo(47, 50)
    hole.lineTo(33, 50)
    hole.closeSubpath()
    p = QPainterPath()
    p.addPath(outer)
    p.addPath(hole)
    return p


def _star12(cx=50, cy=50, r_outer=40, r_inner=16):
    """12-point star (alternating radii)."""
    p = QPainterPath()
    n = 12
    for i in range(n * 2):
        ang = -math.pi / 2.0 + i * math.pi / float(n)
        r = r_outer if (i % 2 == 0) else r_inner
        x = cx + r * math.cos(ang)
        y = cy + r * math.sin(ang)
        if i == 0:
            p.moveTo(x, y)
        else:
            p.lineTo(x, y)
    p.closeSubpath()
    return p


def _sharp_diamond():
    """Diamond with acute corners (delicate tips)."""
    p = QPainterPath()
    p.moveTo(50, 10)
    p.lineTo(70, 50)
    p.lineTo(50, 90)
    p.lineTo(30, 50)
    p.closeSubpath()
    return p


def _fraction_inside(weed, keep_fill, step=1.5):
    pts = sample_points_on_path(weed, step=step)
    if not pts:
        return 0.0
    inside = sum(1 for p in pts if keep_fill.contains(p))
    return inside / float(len(pts))


def _line_segments(path):
    segs = []
    x0 = y0 = None
    for i in range(path.elementCount()):
        e = path.elementAt(i)
        if e.isMoveTo():
            x0, y0 = e.x, e.y
            continue
        if x0 is not None:
            segs.append((x0, y0, e.x, e.y))
        x0, y0 = e.x, e.y
    return segs


def _mid_ring_samples(weed, cx, cy, r_lo, r_hi):
    pts = sample_points_on_path(weed, step=1.0)
    hit = []
    for p in pts:
        r = math.hypot(p.x() - cx, p.y() - cy)
        if r_lo < r < r_hi:
            hit.append(p)
    return hit


def _radial_keep_to_collar(weed, cx, cy, r_keep, r_collar, tol=2.5):
    """Segments with one end near keep radius and the other near the collar."""
    found = []
    for x0, y0, x1, y1 in _line_segments(weed):
        r0 = math.hypot(x0 - cx, y0 - cy)
        r1 = math.hypot(x1 - cx, y1 - cy)
        a, b = (r0, r1) if r0 <= r1 else (r1, r0)
        if abs(a - r_keep) <= tol and abs(b - r_collar) <= tol:
            found.append((x0, y0, x1, y1))
    return found


def _star12_tips(cx=50, cy=50, r_outer=40):
    tips = []
    n = 12
    for i in range(n):
        ang = -math.pi / 2.0 + i * 2.0 * math.pi / float(n)
        tips.append(QPointF(cx + r_outer * math.cos(ang),
                            cy + r_outer * math.sin(ang)))
    return tips


def _star12_valleys(cx=50, cy=50, r_inner=16):
    valleys = []
    n = 12
    for i in range(n):
        ang = -math.pi / 2.0 + (i + 0.5) * 2.0 * math.pi / float(n)
        valleys.append(QPointF(cx + r_inner * math.cos(ang),
                               cy + r_inner * math.sin(ang)))
    return valleys


def _dist_to_rect_boundary(x, y, rect):
    return min(
        abs(x - rect.left()), abs(x - rect.right()),
        abs(y - rect.top()), abs(y - rect.bottom()),
    )


def _nearest_seg_end(weed, point, max_dist=4.0):
    """Closest segment endpoint to *point*, or None if farther than *max_dist*."""
    best = None
    best_d = max_dist
    for x0, y0, x1, y1 in _line_segments(weed):
        for x, y in ((x0, y0), (x1, y1)):
            d = math.hypot(x - point.x(), y - point.y())
            if d <= best_d:
                best_d = d
                other = (x1, y1) if (x, y) == (x0, y0) else (x0, y0)
                best = (x, y, other[0], other[1], d)
    return best


def test_solid_keep_leaves_only_is_gone():
    assert not hasattr(weeds_mod, '_solid_keep_from_nodes')


def test_text_star_dispatch_helpers_are_gone():
    assert not hasattr(weeds_mod, '_height_classes')
    assert not hasattr(weeds_mod, '_is_spiky_island')
    assert not hasattr(weeds_mod, '_major_keep_bodies')


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


def test_even_odd_letter_o_keep_is_ring():
    keep = _letter_o()
    fill = even_odd_keep_fill(keep)
    assert fill.contains(QPointF(50, 25))  # ring
    assert not fill.contains(QPointF(50, 50))  # hole is waste
    assert not fill.contains(QPointF(4, 4))  # exterior
    # Alias still names the same design keep fill (not a solid disk).
    assert closed_fill_union is even_odd_keep_fill
    assert not even_odd_keep_fill(keep).contains(QPointF(50, 50))


def test_overlapping_design_stays_keep():
    """Two design islands that overlap: intersection is keep, not waste."""
    keep = QPainterPath()
    keep.addPath(_rect_path(0, 0, 20, 20))
    keep.addPath(_rect_path(10, 10, 20, 20))
    fill = even_odd_keep_fill(keep)
    assert fill.contains(QPointF(5, 5))
    assert fill.contains(QPointF(25, 25))
    # Pure even-odd would XOR the overlap into waste.
    assert fill.contains(QPointF(15, 15)), (
        "design+design overlap must stay keep (not weedable)")


def test_hi_corridor_mouth_reaches_i_dot():
    """H–i long alley mouth is at the i-dot, not only the stem top."""
    keep = QPainterPath()
    # H block + i-dot above i-stem (stem tall enough not to be a "hanging").
    keep.addPath(_rect_path(0, 0, 20, 54))
    keep.addPath(_rect_path(32, 10, 6, 8))   # i-dot
    keep.addPath(_rect_path(32, 20, 6, 34))  # i-stem (height/H > hanging gate)
    bodies = list_closed_subpaths(keep)
    assert len(bodies) == 3
    h, stem = bodies[0], bodies[2]
    assert weeds_mod._is_corridor_pair(h, stem)
    mouths = weeds_mod._gap_mouths(h, stem, cluster=bodies)
    assert mouths and len(mouths) >= 2
    ys = sorted(0.5 * (pa.y() + pb.y()) for pa, pb, _d in mouths)
    assert ys[0] < 16.0, "top mouth should reach the i-dot band (ys=%s)" % ys
    weed = island_hop_weeds(keep, padding=[10, 10, 10, 10], collar=4.0)
    keep_fill = even_odd_keep_fill(keep)
    top = []
    for x0, y0, x1, y1 in _line_segments(weed):
        mx, my = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
        if keep_fill.contains(QPointF(mx, my)):
            continue
        if 18.0 <= mx <= 34.0 and 0.0 <= my <= 18.0:
            top.append((x0, y0, x1, y1))
    assert top, "expected H→i-dot seal near the dot, got none"


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
    keep_edges = weeds_mod._keep_outline_edges(keep)
    for seg in segs:
        dx, dy = seg[2] - seg[0], seg[3] - seg[1]
        ln = math.hypot(dx, dy)
        assert ln > 1e-9
        ux, uy = dx / ln, dy / ln
        assert weeds_mod._end_anchored(
            seg[0], seg[1], segs, keep_edges, skip=seg, tol=tol, work=work,
            keep_path=keep, weed_dir=(ux, uy)), seg
        assert weeds_mod._end_anchored(
            seg[2], seg[3], segs, keep_edges, skip=seg, tol=tol, work=work,
            keep_path=keep, weed_dir=(-ux, -uy)), seg


def test_grid_sample_gap_snaps_not_float():
    """Short-of-keep stubs snap to outline; true floaters are dropped."""
    keep = _rect_path(20, 20, 40, 40)
    work = QRectF(10, 10, 60, 60)
    keep_edges = weeds_mod._keep_outline_edges(keep)
    # Simulate pre-snap sample gap: 1.8 mm short of keep (tol 1.5 misses).
    raw = [
        (40.0, 10.0, 40.0, 18.2),
        (40.0, 61.8, 40.0, 70.0),
    ]
    snapped = []
    for seg in raw:
        s = weeds_mod._snap_grid_seg(seg, False, keep_edges, [], work)
        if s is not None:
            snapped.append(s)
    assert len(snapped) == 2, snapped
    for seg in snapped:
        for px, py in ((seg[0], seg[1]), (seg[2], seg[3])):
            on_work = weeds_mod._on_work_edge(px, py, work, tol=1.5)
            near_keep = weeds_mod._point_near_edges(px, py, keep_edges, 1.5)
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
    cleaned = weeds_mod._require_connected_ends(
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


@pytest.mark.skip(reason="Inkcut Job pipeline not in weedlines")
def test_legacy_add_weedline_uses_frame():
    path = _rect_path(0, 0, 10, 10)
    job = Job()
    job._add_weedline(path, [1, 1, 1, 1])
    assert path.boundingRect().width() >= 12


@requires_clipper
def test_auto_fewer_segments_than_dense_grid():
    cases = (
        (_rect_path(20, 20, 60, 40), [15, 15, 15, 15]),
        (_letter_o(), [8, 8, 8, 8]),
    )
    for keep, pad in cases:
        grid = grid_weeds(keep, padding=pad, spacing=8)
        auto = island_hop_weeds(keep, padding=pad, spacing=25, max_chunk=50)
        g = weed_path_stats(grid)
        a = weed_path_stats(auto)
        assert a['segments'] < g['segments'], (
            "auto should use fewer cuts than dense grid (%s vs %s)" % (
                a['segments'], g['segments']))


@requires_clipper
def test_auto_does_not_slice_keep():
    keep = _letter_o()
    keep_fill = even_odd_keep_fill(keep)
    weed = island_hop_weeds(keep, padding=[8, 8, 8, 8], spacing=20, max_chunk=40)
    assert not weed.isEmpty()
    frac = _fraction_inside(weed, keep_fill, step=1.0)
    assert frac < _IN_KEEP_BUDGET, "auto sliced O keep ring (frac=%s)" % frac

    solid = _rect_path(20, 20, 40, 30)
    solid_fill = even_odd_keep_fill(solid)
    weed2 = island_hop_weeds(solid, padding=[10, 10, 10, 10], spacing=20, max_chunk=40)
    frac2 = _fraction_inside(weed2, solid_fill, step=1.0)
    assert frac2 < _IN_KEEP_BUDGET, "auto sliced solid keep (frac=%s)" % frac2

    star = _star12()
    star_fill = even_odd_keep_fill(star)
    weed3 = island_hop_weeds(star, padding=[12, 12, 12, 12], spacing=20, max_chunk=40)
    frac3 = _fraction_inside(weed3, star_fill, step=1.0)
    assert frac3 < _IN_KEEP_BUDGET, "auto sliced star keep (frac=%s)" % frac3


@requires_clipper
def test_auto_letter_o_zero_weed_in_ring():
    keep = _letter_o()
    pad = [8, 8, 8, 8]
    weed = island_hop_weeds(keep, padding=pad, spacing=20, max_chunk=40)
    # Mid-annulus must see no weed (no pocket channel through the letter).
    assert not _mid_ring_samples(weed, 50, 50, 22.0, 38.0), (
        "auto cut through the O ring")
    keep_fill = even_odd_keep_fill(keep)
    assert keep_fill.contains(QPointF(50, 25))
    assert not keep_fill.contains(QPointF(50, 50))


@requires_clipper
def test_auto_letter_o_collar_and_one_channel():
    keep = _letter_o()
    pad = [8, 8, 8, 8]
    weed = island_hop_weeds(
        keep, padding=pad, spacing=20, max_chunk=40, collar=DEFAULT_COLLAR)
    assert not _mid_ring_samples(weed, 50, 50, 22.0, 38.0), (
        "auto cut through the O ring")
    hole = _circle_path(50, 50, 18)
    hole_pts = [p for p in sample_points_on_path(weed, step=1.0)
                if hole.contains(p)]
    assert not hole_pts, "O hole should be uncut at this max_chunk"
    channels = _radial_keep_to_collar(weed, 50, 50, 40.0, 47.0, tol=4.0)
    assert len(channels) >= 1, (
        "O should have a keep→peel-frame channel, got %s" % len(channels))
    rail = _mid_ring_samples(weed, 50, 50, 41.0, 49.0)
    assert rail, "O missing peel frame outside the keep"


@requires_clipper
def test_auto_rect_no_diagonal_rays():
    keep = _rect_path(20, 20, 60, 40)
    weed = island_hop_weeds(keep, padding=[12, 12, 12, 12], spacing=25, max_chunk=50)
    corners = ((20, 20), (80, 20), (80, 60), (20, 60))
    for x0, y0, x1, y1 in _line_segments(weed):
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        if dx <= 1e-4 or dy <= 1e-4:
            continue
        ln = math.hypot(x1 - x0, y1 - y0)
        if ln < 8.0:
            continue
        for cx, cy in corners:
            near = min(math.hypot(x0 - cx, y0 - cy),
                       math.hypot(x1 - cx, y1 - cy))
            assert near > 2.0, "rect auto emitted a corner ray"


def test_weeds_clip_to_work_rect():
    cases = (
        _rect_path(20, 20, 60, 40),
        _letter_o(),
        _star12(),
        _sharp_diamond(),
        _letters_hi(),
        _letter_a(),
        _framed_hi(),
        _wreath_hi(),
    )
    pad = [10, 10, 10, 10]
    for keep in cases:
        work = padded_work_rect(keep, pad)
        keep_fill = even_odd_keep_fill(keep)
        for mode in ('frame', 'grid', 'auto'):
            weed = generate_weeds(
                keep, mode=mode, padding=pad, spacing=15, max_chunk=40)
            st = weed_sample_stats(
                weed, keep_fill=keep_fill, work_rect=work, step=1.0)
            assert st['outside_work'] == 0, (
                "%s weeds left work rect (%s samples)" % (
                    mode, st['outside_work']))


@requires_clipper
def test_auto_reliefs_use_caller_clearance():
    keep = _sharp_diamond()
    pad = [25, 25, 25, 25]
    tip = QPointF(50, 10)
    near = island_hop_weeds(
        keep, padding=pad, spacing=40, max_chunk=50,
        frame_clearance=4.0, delicate_angle_deg=40.0)
    far = island_hop_weeds(
        keep, padding=pad, spacing=40, max_chunk=50,
        frame_clearance=14.0, delicate_angle_deg=40.0)
    def _min_tip(weed):
        pts = sample_points_on_path(weed, step=0.5)
        ds = [
            math.hypot(p.x() - tip.x(), p.y() - tip.y())
            for p in pts
            if abs(p.x() - tip.x()) < 6 and -8.0 < p.y() < tip.y()
        ]
        return min(ds) if ds else 1e9
    assert _min_tip(far) > _min_tip(near) + 4.0, (
        "frame_clearance ignored (far=%s near=%s)" % (
            _min_tip(far), _min_tip(near)))


def test_polyline_samples_curves_not_control_points():
    keep = _circle_path(50, 50, 40)
    pts = _polyline_points(keep)
    assert len(pts) >= 8
    for p in pts:
        r = math.hypot(p.x() - 50.0, p.y() - 50.0)
        assert abs(r - 40.0) < 1.5, "Bezier control treated as vertex (r=%s)" % r


@requires_clipper
def test_auto_circle_no_control_point_rays():
    keep = _circle_path(50, 50, 30)
    weed = island_hop_weeds(
        keep, padding=[10, 10, 10, 10], spacing=30, max_chunk=80, collar=4.0)
    channels = _radial_keep_to_collar(weed, 50, 50, 30.0, 40.0, tol=4.0)
    assert len(channels) >= 1, (
        "smooth circle should have a keep→frame channel, got %s" % len(channels))
    # Bezier controls must not become extra "tips" with many radial rays.
    assert len(channels) < 4


@requires_clipper
def test_auto_delicate_emits_outward_from_sharp_corners():
    keep = _sharp_diamond()
    pad = [20, 20, 20, 20]
    weed = island_hop_weeds(
        keep, padding=pad, spacing=30, max_chunk=50,
        delicate_angle_deg=40.0)
    assert not weed.isEmpty()
    tip = QPointF(50, 10)
    pts = sample_points_on_path(weed, step=1.0)
    near_outward = [
        p for p in pts
        if abs(p.x() - 50) < 8 and p.y() < 10 - 1.0
    ]
    keep_fill = even_odd_keep_fill(keep)
    near_tip_outside = [
        p for p in pts
        if math.hypot(p.x() - tip.x(), p.y() - tip.y()) < 25
        and not keep_fill.contains(p)
    ]
    assert near_outward or near_tip_outside, (
        "auto produced no outward relief near diamond tip")


@pytest.mark.skip(reason="Inkcut Job pipeline not in weedlines")
def test_job_plan_auto_mode_typed_weed():
    svg = '''<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="80">
  <rect x="25" y="20" width="50" height="40" fill="none" stroke="black"/>
</svg>'''
    doc = QtSvgDoc(svg)
    job = Job()
    job.doc = doc
    job.path = doc
    job.optimized_path = doc
    job.plot_weedline = True
    job.weed_mode = 'island-hop'
    job.weed_grid_spacing = 20
    job.plot_weedline_padding = [12, 12, 12, 12]

    plan = job.build_plan(
        swap_xy=False, scale=[1, 1],
        origin_position='bottom_left', feed_axis='y', epilogue='none')
    weed_segs = [s for s in plan.segments if s.kind == 'weed']
    assert len(weed_segs) >= 1
    assert all(s.meta.get('mode') == 'auto' for s in weed_segs)
    assert not plan.weeds().isEmpty()
    # Weed cuts get travel segments like design cuts (not one blob).
    assert any(s.kind == 'travel' for s in plan.segments)


@requires_clipper
def test_auto_knobs_change_geometry():
    """User-facing knobs must affect generated weed paths."""
    keep = _star12()
    pad = [15, 15, 15, 15]
    few = island_hop_weeds(
        keep, padding=pad, collar=5.0, max_spokes=3,
        delicate_angle_deg=40.0)
    many = island_hop_weeds(
        keep, padding=pad, collar=5.0, max_spokes=12,
        delicate_angle_deg=40.0)
    assert weed_path_stats(many)['segments'] > weed_path_stats(few)['segments']
    a = generate_weeds(
        keep, mode='island-hop', padding=pad, spacing=20,
        max_chunk=30, collar=6.0, max_spokes=8,
        min_cut=2.0, delicate_angle_deg=50.0)
    assert not a.isEmpty()
    # Clearance raises the collar (effective = max(collar, clearance)).
    tight = island_hop_weeds(keep, padding=pad, collar=3.0, clearance=0.5)
    wide = island_hop_weeds(keep, padding=pad, collar=3.0, clearance=10.0)
    assert wide.boundingRect().width() >= tight.boundingRect().width() - 1e-6


@requires_clipper
def test_star12_closed_and_in_work():
    keep = _star12()
    closed = list_closed_subpaths(keep)
    assert len(closed) == 1
    pad = [12, 12, 12, 12]
    work = padded_work_rect(keep, pad)
    weed = island_hop_weeds(keep, padding=pad, spacing=20, max_chunk=40)
    st = weed_sample_stats(
        weed, keep_fill=even_odd_keep_fill(keep), work_rect=work, step=1.0)
    assert st['outside_work'] == 0
    assert st['in_keep_frac'] < _IN_KEEP_BUDGET


@requires_clipper
def test_auto_star12_spokes_end_on_collar():
    keep = _star12()
    pad = [12, 12, 12, 12]
    collar = 4.0
    work = padded_work_rect(keep, pad)
    weed = island_hop_weeds(
        keep, padding=pad, spacing=20, max_chunk=40,
        collar=collar, max_spokes=24, delicate_angle_deg=95.0)
    tips = _star12_tips()
    hit = 0
    for tip in tips:
        found = _nearest_seg_end(weed, tip, max_dist=3.5)
        assert found is not None, "star missing spoke near tip %s" % (
            (tip.x(), tip.y()),)
        _sx, _sy, ex, ey, _d = found
        end_to_work = _dist_to_rect_boundary(ex, ey, work)
        assert end_to_work > 1.5, (
            "star spoke escaped to the work rect (end=%s,%s dist=%s)" % (
                ex, ey, end_to_work))
        spoke_len = math.hypot(ex - tip.x(), ey - tip.y())
        assert spoke_len < min(pad) + 2.0, (
            "star spoke longer than peel frame (len=%s)" % spoke_len)
        hit += 1
    assert hit == 12

    # Valleys must not grow rays out to the work rect (frame itself is ok).
    for valley in _star12_valleys():
        found = _nearest_seg_end(weed, valley, max_dist=2.5)
        if found is None:
            continue
        _sx, _sy, ex, ey, d0 = found
        if d0 > 2.0:
            continue
        if _dist_to_rect_boundary(ex, ey, work) <= 1.5:
            raise AssertionError(
                "valley-to-work-rect ray from (%s, %s)" % (
                    valley.x(), valley.y()))
        other_len = math.hypot(ex - valley.x(), ey - valley.y())
        assert other_len < min(pad) + 4.0, (
            "valley-to-infinity ray (len=%s)" % other_len)


def _keep_bodies(path):
    nodes = _nest_closed_paths(list_closed_subpaths(path))
    return [n['path'] for n in nodes if n['depth'] % 2 == 0]


@requires_clipper
def test_star_has_deep_keep_peninsulas_letters_do_not():
    """Star tips are deep keep peninsulas; boxy/smooth bodies are not."""
    star = _keep_bodies(_star12())
    assert len(star) == 1
    star_tips = _deep_keep_peninsula_tips(star[0], DEFAULT_DELICATE_ANGLE_DEG)
    assert len(star_tips) >= 5, "star12 should have many deep keep tips, got %s" % (
        len(star_tips),)
    for label, path in (
            ('A', _letter_a()), ('O', _letter_o()), ('HI', _letters_hi())):
        for body in _keep_bodies(path):
            n = len(_deep_keep_peninsula_tips(body, DEFAULT_DELICATE_ANGLE_DEG))
            assert n < 3, "%s sprouted %s deep keep peninsulas" % (label, n)


@requires_clipper
def test_nearby_letters_share_one_enclosure():
    keep = _letters_hi()
    bodies = _keep_bodies(keep)
    assert len(bodies) == 2
    gap = _word_cluster_gap(bodies, 4.0)
    clusters = _cluster_keep_bodies(bodies, gap)
    assert len(clusters) == 1
    rings = _isolation_collar_rings(bodies, 4.0, prefer_hull=True)
    assert len(rings) == 1, "word should have one enclosure, got %s" % len(rings)
    weed = island_hop_weeds(keep, padding=[10, 10, 10, 10], collar=4.0)
    keep_fill = even_odd_keep_fill(keep)
    assert _fraction_inside(weed, keep_fill, step=1.0) < _IN_KEEP_BUDGET
    work = padded_work_rect(keep, [10, 10, 10, 10])
    st = weed_sample_stats(weed, keep_fill=keep_fill, work_rect=work, step=1.0)
    assert st['outside_work'] == 0
    near = 0
    for p in sample_points_on_path(weed, step=0.5):
        if keep_fill.contains(p):
            continue
        # Ignore the outer frame.
        if abs(p.x() - work.left()) < 1.0 or abs(p.x() - work.right()) < 1.0:
            continue
        if abs(p.y() - work.top()) < 1.0 or abs(p.y() - work.bottom()) < 1.0:
            continue
        if keep_fill.contains(QPointF(p.x(), p.y())):
            continue
        # Probe a slightly larger keep (clearance disk) via contains of nearby.
        hit = False
        for s in (0.35,):
            if (keep_fill.contains(QPointF(p.x() + s, p.y()))
                    or keep_fill.contains(QPointF(p.x() - s, p.y()))
                    or keep_fill.contains(QPointF(p.x(), p.y() + s))
                    or keep_fill.contains(QPointF(p.x(), p.y() - s))):
                hit = True
                break
        if hit:
            near += 1
    assert near < 16, "too many weed samples grazing the letters (%s)" % near


def _waste_flood(keep_fill, weed, work, seed, step=1.5):
    """4-connected waste cells from *seed*, blocked by keep and weed segs."""
    segs = _line_segments(weed)
    sx = work.left()
    sy = work.top()
    nx = int(math.floor(work.width() / step)) + 1
    ny = int(math.floor(work.height() / step)) + 1

    def cell(p):
        return (int(round((p.x() - sx) / step)),
                int(round((p.y() - sy) / step)))

    def world(ix, iy):
        return QPointF(sx + (ix + 0.5) * step, sy + (iy + 0.5) * step)

    def blocked(p):
        if not work.contains(p):
            return True
        if keep_fill.contains(p):
            return True
        for x0, y0, x1, y1 in segs:
            dx, dy = x1 - x0, y1 - y0
            ln2 = dx * dx + dy * dy
            if ln2 < 1e-12:
                d = math.hypot(p.x() - x0, p.y() - y0)
            else:
                t = max(0.0, min(1.0, (
                    (p.x() - x0) * dx + (p.y() - y0) * dy) / ln2))
                d = math.hypot(p.x() - (x0 + t * dx), p.y() - (y0 + t * dy))
            if d < step * 0.65:
                return True
        return False

    ix0, iy0 = cell(seed)
    seen = set()
    stack = [(ix0, iy0)]
    while stack:
        ix, iy = stack.pop()
        if (ix, iy) in seen:
            continue
        if ix < 0 or iy < 0 or ix >= nx or iy >= ny:
            continue
        p = world(ix, iy)
        if blocked(p):
            continue
        seen.add((ix, iy))
        stack.extend(((ix + 1, iy), (ix - 1, iy), (ix, iy + 1), (ix, iy - 1)))
    return seen, cell, world


@requires_clipper
def test_word_has_object_to_object_cut():
    """Shared outline + per-letter spokes still wrap; need a gap cut."""
    keep = _letters_hi()
    weed = island_hop_weeds(keep, padding=[10, 10, 10, 10], collar=4.0)
    keep_fill = even_odd_keep_fill(keep)
    gap = QRectF(39, 15, 22, 60)
    hits = []
    for x0, y0, x1, y1 in _line_segments(weed):
        mx, my = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
        if not gap.contains(QPointF(mx, my)):
            continue
        if keep_fill.contains(QPointF(mx, my)):
            continue
        hits.append((x0, y0, x1, y1))
    assert hits, "no object-to-object cut in the letter gap"


def test_hi_gap_mouths_are_both_ends():
    """HI channel core is the full alley (L/W≈2.25), so both core ends."""
    keep = _letters_hi()
    closed = list_closed_subpaths(keep)
    assert len(closed) == 2
    mouths = _gap_mouths(closed[0], closed[1])
    assert len(mouths) == 2, "HI alley should have two mouths, got %s" % len(mouths)
    ys = sorted(0.5 * (pa.y() + pb.y()) for pa, pb, _d in mouths)
    assert ys[0] < 24, "missing top mouth (ys=%s)" % ys
    assert ys[1] > 66, "missing bottom mouth (ys=%s)" % ys


@requires_clipper
def test_word_gap_seals_both_mouths():
    """H–I channel core is long (L/W≈2.25 > k): seal both core ends."""
    keep = _letters_hi()
    weed = island_hop_weeds(keep, padding=[10, 10, 10, 10], collar=4.0)
    keep_fill = even_odd_keep_fill(keep)
    top = bot = None
    for x0, y0, x1, y1 in _line_segments(weed):
        mx, my = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
        if keep_fill.contains(QPointF(mx, my)):
            continue
        if not (39.0 <= mx <= 61.0):
            continue
        if 16.0 <= my <= 24.0:
            top = (x0, y0, x1, y1)
        if 66.0 <= my <= 74.0:
            bot = (x0, y0, x1, y1)
    assert top is not None, "no seal at the top of the H–I alley"
    assert bot is not None, "no seal at the bottom of the H–I alley"


@requires_clipper
def test_word_no_slit_from_h_to_outer_frame():
    """Rejected trim: H bottom-left out to the work frame is not a corridor."""
    keep = _letters_hi()
    pad = [10, 10, 10, 10]
    weed = island_hop_weeds(keep, padding=pad, collar=4.0)
    work = padded_work_rect(keep, pad)
    for x0, y0, x1, y1 in _line_segments(weed):
        ends = ((x0, y0), (x1, y1))
        near_h = any(math.hypot(x - 8.0, y - 72.0) < 4.0 for x, y in ends)
        near_frame = any(
            abs(x - work.left()) < 2.5 or abs(y - work.bottom()) < 2.5
            for x, y in ends)
        if near_h and near_frame:
            raise AssertionError(
                "H bottom-left still slits to the frame: %s" % ((x0, y0, x1, y1),))


@requires_clipper
def test_word_waste_does_not_fork_under_letters():
    """Peel down the I must not also reach under the H in the same piece."""
    keep = _letters_hi()
    pad = [10, 10, 10, 10]
    weed = island_hop_weeds(keep, padding=pad, collar=4.0)
    keep_fill = even_odd_keep_fill(keep)
    work = padded_work_rect(keep, pad)
    seed = QPointF(74, 50)  # waste on the right of I
    seen, cell, _world = _waste_flood(keep_fill, weed, work, seed, step=1.5)
    under_h = cell(QPointF(20, 76))
    gap = cell(QPointF(50, 45))
    assert under_h not in seen or gap not in seen, (
        "waste from the I still forks into the gap and under the H")


def test_h_bay_mouths_are_both_counters():
    """H has two U-bays; detector must emit both mouths."""
    keep = _letters_hi()
    closed = list_closed_subpaths(keep)
    h = max(closed, key=lambda p: p.boundingRect().width())
    mouths = _hull_bay_mouths(h, min_depth=4.0, min_width=4.0)
    assert len(mouths) >= 2, "H should have two bay mouths, got %s" % len(mouths)
    ys = sorted(0.5 * (a.y() + b.y()) for a, b, _d, _run in mouths)
    assert ys[0] < 24, "missing H top bay (ys=%s)" % ys
    assert ys[-1] > 66, "missing H bottom bay (ys=%s)" % ys


@requires_clipper
def test_h_lower_bay_is_sealed():
    """Cut across the H lower counter so it is not a live branch."""
    keep = _letters_hi()
    weed = island_hop_weeds(keep, padding=[10, 10, 10, 10], collar=4.0)
    keep_fill = even_odd_keep_fill(keep)
    hit = None
    for x0, y0, x1, y1 in _line_segments(weed):
        mx, my = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
        if keep_fill.contains(QPointF(mx, my)):
            continue
        if 16.5 <= mx <= 29.5 and 68.0 <= my <= 73.0:
            hit = (x0, y0, x1, y1)
            break
    assert hit is not None, "no seal on the H lower bay mouth"


@requires_clipper
def test_under_h_does_not_fork_into_bay_and_left():
    """Under the H: pocket and left wrap must not stay one piece."""
    keep = _letters_hi()
    pad = [10, 10, 10, 10]
    weed = island_hop_weeds(keep, padding=pad, collar=4.0)
    keep_fill = even_odd_keep_fill(keep)
    work = padded_work_rect(keep, pad)
    seed = QPointF(23, 74)
    seen, cell, _world = _waste_flood(keep_fill, weed, work, seed, step=1.5)
    pocket = cell(QPointF(23, 60))
    left = cell(QPointF(6, 45))
    assert pocket not in seen or left not in seen, (
        "under-H waste still forks into the H bay and the left corridor")


@requires_clipper
def test_letter_a_no_cut_through_stroke_or_hole():
    keep = _letter_a()
    pad = [10, 10, 10, 10]
    weed = island_hop_weeds(keep, padding=pad, collar=4.0, max_chunk=80)
    keep_fill = even_odd_keep_fill(keep)
    assert keep_fill.contains(QPointF(40, 20))
    assert not keep_fill.contains(QPointF(40, 42))
    assert _fraction_inside(weed, keep_fill, step=0.8) < _IN_KEEP_BUDGET
    hole = QPainterPath()
    hole.moveTo(40, 32)
    hole.lineTo(45, 48)
    hole.lineTo(35, 48)
    hole.closeSubpath()
    hole_pts = [p for p in sample_points_on_path(weed, step=1.0)
                if hole.contains(p)]
    assert not hole_pts, "A counter should stay uncut"


@requires_clipper
def test_framed_text_gets_inner_weeds_not_through_border():
    keep = _framed_hi()
    pad = [10, 10, 10, 10]
    weed = island_hop_weeds(keep, padding=pad, collar=4.0, max_chunk=80)
    keep_fill = even_odd_keep_fill(keep)
    # Endpoint landings must meet keep; without a long outer peel rail to
    # dilute samples, raw fraction can sit a bit above the unframed budget.
    assert _fraction_inside(weed, keep_fill, step=0.8) < 0.04
    # Border ring is keep.
    assert keep_fill.contains(QPointF(3, 50))
    # Waste just outside the letters, still inside the frame hole.
    halo = QRectF(22, 20, 76, 66)
    hole = QRectF(6, 6, 108, 88)
    pts = sample_points_on_path(weed, step=1.0)
    in_halo = sum(
        1 for p in pts
        if halo.contains(p) and hole.contains(p) and not keep_fill.contains(p))
    assert in_halo > 0, "no weed help between border and inner text"
    # Must not cut through the frame ring.
    ring_hits = [p for p in pts if 0.5 < p.x() < 5.5 and 10 < p.y() < 90]
    ring_hits = [p for p in ring_hits if keep_fill.contains(p)]
    assert not ring_hits, "weed cut through the decorative border"


@requires_clipper
def test_quoted_word_stays_one_word_box():
    """Dots and quotes must not split off the word hull as a 'wreath'."""
    keep = _quoted_blocks()
    nodes = _nest_closed_paths(list_closed_subpaths(keep))
    groups = weeds_mod._enclosure_groups(nodes, 4.0)
    assert len(groups) == 1, "punctuation split the word into %s groups" % len(groups)
    weed = island_hop_weeds(keep, padding=[10, 10, 10, 10], collar=4.0)
    keep_fill = even_odd_keep_fill(keep)
    assert _fraction_inside(weed, keep_fill, step=0.8) < _IN_KEEP_BUDGET
    work = padded_work_rect(keep, [10, 10, 10, 10])
    st = weed_sample_stats(weed, keep_fill=keep_fill, work_rect=work, step=1.0)
    assert st['outside_work'] == 0


def _quote_pair(ox=10.0, oy=20.0, w=3.4, h=9.3, gap=3.16):
    """Two thin quote stems; gap is narrower than 2*standoff+min_cut."""
    p = QPainterPath()
    p.addPath(_rect_path(ox, oy, w, h))
    p.addPath(_rect_path(ox + w + gap, oy, w, h))
    return p


@requires_clipper
def test_narrow_quote_alley_seals_both_mouths():
    """Quote pair core is the full alley (L/W≈2.9): both core ends, not AABB flare."""
    keep = _quote_pair()
    keep.addPath(_rect_path(40, 18, 24, 30))
    weed = island_hop_weeds(keep, padding=[8, 8, 8, 8], collar=4.0)
    keep_fill = even_odd_keep_fill(keep)
    top = bot = None
    for x0, y0, x1, y1 in _line_segments(weed):
        mx, my = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
        if keep_fill.contains(QPointF(mx, my)):
            continue
        if not (13.0 <= mx <= 17.0):
            continue
        if 19.5 <= my <= 23.5:
            top = (x0, y0, x1, y1)
        if 25.8 <= my <= 29.8:
            bot = (x0, y0, x1, y1)
    assert top is not None, "no seal at the top of the quote alley"
    assert bot is not None, "no seal at the bottom of the quote alley"


@requires_clipper
def test_auto_has_one_enclosure_not_frame_plus_collar():
    """Auto must not draw the padded frame on top of the isolation collar."""
    keep = _letters_hi()
    pad = [10, 10, 10, 10]
    weed = island_hop_weeds(keep, padding=pad, collar=4.0)
    work = padded_work_rect(keep, pad)
    on_frame = []
    for x0, y0, x1, y1 in _line_segments(weed):
        ys = (y0, y1)
        xs = (x0, x1)
        if (abs(y0 - work.top()) < 0.6 and abs(y1 - work.top()) < 0.6
                and abs(x1 - x0) > work.width() * 0.5):
            on_frame.append((x0, y0, x1, y1))
        if (abs(x0 - work.left()) < 0.6 and abs(x1 - work.left()) < 0.6
                and abs(y1 - y0) > work.height() * 0.5):
            on_frame.append((x0, y0, x1, y1))
    assert not on_frame, "auto still draws the padded frame: %s" % on_frame


@requires_clipper
def test_apostrophe_does_not_sprout_letter_stubs():
    """A hanging mark next to tall letters is not a corridor node."""
    keep = QPainterPath()
    keep.addPath(_rect_path(10, 18, 8, 30))
    keep.addPath(_rect_path(24, 20, 3.4, 9.3))  # apostrophe
    keep.addPath(_rect_path(34, 18, 12, 30))
    weed = island_hop_weeds(keep, padding=[8, 8, 8, 8], collar=4.0)
    keep_fill = even_odd_keep_fill(keep)
    stubs = []
    for x0, y0, x1, y1 in _line_segments(weed):
        mx, my = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
        if keep_fill.contains(QPointF(mx, my)):
            continue
        if 18.0 <= mx <= 34.0 and 21.5 <= my <= 27.5:
            ln = math.hypot(x1 - x0, y1 - y0)
            if ln < 6.0 and abs(y1 - y0) < 1.0:
                stubs.append((x0, y0, x1, y1))
    assert not stubs, "apostrophe still has letter-spacing stubs: %s" % stubs


@requires_clipper
def test_quote_top_channel_is_near_vertical():
    """Quote tops must not graze the collar at ~45°."""
    keep = QPainterPath()
    keep.addPath(_rect_path(0, 18, 20, 30))
    keep.addPath(_quote_pair(ox=28, oy=20))
    keep.addPath(_rect_path(50, 18, 20, 30))
    weed = island_hop_weeds(keep, padding=[8, 8, 8, 8], collar=4.0)
    keep_fill = even_odd_keep_fill(keep)
    hits = []
    for x0, y0, x1, y1 in _line_segments(weed):
        ends = ((x0, y0), (x1, y1))
        near_top = any(28.0 <= x <= 38.2 and 16.5 <= y <= 21.2 for x, y in ends)
        if not near_top:
            continue
        # Mouth seals stay in the alley; only a collar stub would graze.
        if not any(y < 16.5 for _x, y in ends):
            continue
        if keep_fill.contains(QPointF(0.5 * (x0 + x1), 0.5 * (y0 + y1))):
            continue
        dx, dy = x1 - x0, y1 - y0
        ln = math.hypot(dx, dy)
        if ln < 2.0:
            continue
        from_vert = abs(math.degrees(math.atan2(dx, dy)))
        from_vert = min(from_vert, 180.0 - from_vert)
        hits.append((from_vert, (x0, y0, x1, y1)))
    assert all(a < 20.0 for a, _seg in hits), (
        "quote-top channel still grazes: %s" % hits)


@requires_clipper
def test_agglomerate_joins_until_one_island():
    """Smallest-first cuts must leave one island, not leftover specks."""
    keep = _quoted_blocks()
    bodies = _keep_bodies(keep)
    assert len(bodies) >= 4
    work = padded_work_rect(keep, [8, 8, 8, 8])
    keep_fill = even_odd_keep_fill(keep)
    _path, groups, _sat = _agglomerate_islands(
        bodies, keep_fill, work, DEFAULT_CHANNEL_STANDOFF, 1.0, None)
    assert len(groups) == 1, "still %s islands after merge" % len(groups)


@requires_clipper
def test_wreath_still_weeds_inner_text():
    keep = _wreath_hi()
    nodes = _nest_closed_paths(list_closed_subpaths(keep))
    groups = weeds_mod._enclosure_groups(nodes, 4.0)
    assert len(groups) >= 2, "inner text should split from surrounding ornaments"
    weed = island_hop_weeds(keep, padding=[12, 12, 12, 12], collar=4.0)
    keep_fill = even_odd_keep_fill(keep)
    assert _fraction_inside(weed, keep_fill, step=0.8) < _IN_KEEP_BUDGET
    # Near the letters (translated HI ~ 34-96, 28-82) there should be a collar.
    letter_halo = QRectF(30, 24, 80, 64)
    pts = sample_points_on_path(weed, step=1.0)
    near_text = sum(
        1 for p in pts
        if letter_halo.contains(p) and not keep_fill.contains(p))
    assert near_text > 0, "inner text in a wreath got no enclosure"


def _letter_t():
    """United stem + crossbar; open sides are shallow waste peninsulas."""
    stem = _rect_path(40, 18, 8, 54)
    bar = _rect_path(28, 18, 32, 8)
    return stem.united(bar)


@requires_clipper
def test_deep_waste_peninsula_seals_h_not_t():
    """H counters are deep (sealed); a t open side is shallow (not sealed)."""
    h = max(list_closed_subpaths(_letters_hi()),
            key=lambda p: p.boundingRect().width())
    h_mouths = _hull_bay_mouths(h, min_depth=4.0, min_width=4.0)
    h_deep = []
    for left, right, deep, _run in h_mouths:
        mouth_w = math.hypot(right.x() - left.x(), right.y() - left.y())
        depth = _point_seg_dist(
            deep.x(), deep.y(), left.x(), left.y(), right.x(), right.y())
        if _peninsula_is_deep(depth, mouth_w):
            h_deep.append((left, right, deep))
    assert len(h_deep) >= 2, "H bays should be deep, got %s" % len(h_deep)

    t = _letter_t()
    t_mouths = _hull_bay_mouths(t, min_depth=4.0, min_width=4.0)
    t_deep = []
    for left, right, deep, _run in t_mouths:
        mouth_w = math.hypot(right.x() - left.x(), right.y() - left.y())
        depth = _point_seg_dist(
            deep.x(), deep.y(), left.x(), left.y(), right.x(), right.y())
        if _peninsula_is_deep(depth, mouth_w):
            t_deep.append((left, right, deep))
    assert not t_deep, "t open side should be shallow, got %s deep" % len(t_deep)

    weed = island_hop_weeds(t, padding=[10, 10, 10, 10], collar=4.0)
    keep_fill = even_odd_keep_fill(t)
    # Inside the left dent (between stem and hull), not the outer collar.
    left_notch = QRectF(35.5, 32.0, 4.0, 28.0)
    seals = []
    for x0, y0, x1, y1 in _line_segments(weed):
        mx, my = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
        if keep_fill.contains(QPointF(mx, my)):
            continue
        if left_notch.contains(QPointF(mx, my)) and math.hypot(x1 - x0, y1 - y0) > 3.0:
            seals.append((x0, y0, x1, y1))
    assert not seals, "t left opening was sealed: %s" % seals


def test_font_like_h_counter_is_deep():
    """A U wider than it is deep (font H) is still a trap."""
    u = _rect_path(0, 0, 8, 15).united(_rect_path(21, 0, 8, 15))
    u = u.united(_rect_path(0, 11, 29, 4))
    mouths = _hull_bay_mouths(u, min_depth=4.0, min_width=4.0)
    deep = []
    for left, right, tip, _run in mouths:
        mouth_w = math.hypot(right.x() - left.x(), right.y() - left.y())
        depth = _point_seg_dist(
            tip.x(), tip.y(), left.x(), left.y(), right.x(), right.y())
        if _peninsula_is_deep(depth, mouth_w):
            deep.append((left, right, tip))
    assert deep, "font-like U (11 deep / 13 wide) should be deep"
    weed = island_hop_weeds(u, padding=[8, 8, 8, 8], collar=4.0)
    keep_fill = even_odd_keep_fill(u)
    hit = None
    for x0, y0, x1, y1 in _line_segments(weed):
        mx, my = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
        if keep_fill.contains(QPointF(mx, my)):
            continue
        if 8.0 <= mx <= 21.0 and -0.2 <= my <= 5.0:
            hit = (x0, y0, x1, y1)
            break
    assert hit is not None, "font-like U mouth was not sealed"


def test_star_valley_mouth_is_not_sealed():
    """Waste between two keep tips is a valley, not a peninsula seal."""
    keep = _star12()
    body = _keep_bodies(keep)[0]
    tips = _deep_keep_peninsula_tips(body, DEFAULT_DELICATE_ANGLE_DEG)
    assert len(tips) >= 5
    mouths = _hull_bay_mouths(body, min_depth=4.0, min_width=4.0)
    valley = 0
    for left, right, _deep, _run in mouths:
        if _mouth_between_keep_tips(left, right, tips, tol=3.0):
            valley += 1
    assert valley >= 5, "star valleys should sit between keep tips, got %s" % valley
    weed = island_hop_weeds(keep, padding=[12, 12, 12, 12], collar=4.0)
    valleys = _star12_valleys()
    for x0, y0, x1, y1 in _line_segments(weed):
        mx, my = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
        for v in valleys:
            if math.hypot(mx - v.x(), my - v.y()) < 8.0:
                raise AssertionError(
                    "star valley sealed at (%s, %s)" % (mx, my))


def _letter_k():
    """Stem + two pointed legs: keep tips and independent waste bays."""
    p = QPainterPath()
    p.moveTo(0, 0)
    p.lineTo(8, 0)
    p.lineTo(8, 16)
    p.lineTo(24, 0)
    p.lineTo(32, 0)
    p.lineTo(16, 20)
    p.lineTo(32, 40)
    p.lineTo(24, 40)
    p.lineTo(8, 24)
    p.lineTo(8, 40)
    p.lineTo(0, 40)
    p.closeSubpath()
    return p


def test_k_has_independent_bays_so_no_tip_spokes():
    """A K is not a star: seal the openings, channel to the collar."""
    k = _letter_k()
    tips = _deep_keep_peninsula_tips(k, DEFAULT_DELICATE_ANGLE_DEG)
    assert len(tips) >= 2
    assert _has_independent_waste_bays(
        k, tips, DEFAULT_CHANNEL_STANDOFF, 1.0)
    neighbor = _rect_path(42, 0, 6, 40)
    keep = QPainterPath()
    keep.addPath(k)
    keep.addPath(neighbor)
    weed = island_hop_weeds(keep, padding=[10, 10, 10, 10], collar=4.0)
    keep_fill = even_odd_keep_fill(keep)
    diagonals = []
    for x0, y0, x1, y1 in _line_segments(weed):
        mx, my = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
        if keep_fill.contains(QPointF(mx, my)):
            continue
        ln = math.hypot(x1 - x0, y1 - y0)
        if ln < 4.0:
            continue
        near_tip = any(
            math.hypot(x0 - t['pt'].x(), y0 - t['pt'].y()) < 4.0
            or math.hypot(x1 - t['pt'].x(), y1 - t['pt'].y()) < 4.0
            for t in tips)
        if not near_tip:
            continue
        ang = abs(math.degrees(math.atan2(y1 - y0, x1 - x0)))
        ang = min(ang % 180.0, 180.0 - (ang % 180.0))
        from_axis = min(ang, abs(90.0 - ang))
        if from_axis > 20.0:
            diagonals.append((from_axis, (x0, y0, x1, y1)))
    assert not diagonals, "K still has tip spokes: %s" % diagonals


@requires_clipper
def test_auto_weed_segments_do_not_cross():
    """Weed cuts may T, but interiors must not cross."""
    for keep in (_letters_hi(), _star12(), _quoted_blocks(), _letter_k()):
        weed = island_hop_weeds(keep, padding=[10, 10, 10, 10], collar=4.0)
        segs = _line_segments(weed)
        for i, a in enumerate(segs):
            for b in segs[i + 1:]:
                assert not _seg_proper_cross(*(a + b)), (
                    "crossing weeds %s x %s" % (a, b))


def test_weed_debug_logging_is_side_effect_free():
    """WEEDLINES_LOG must not change emitted geometry."""
    import os
    keep = _letters_hi()
    pad = [10, 10, 10, 10]
    before = os.environ.pop('WEEDLINES_LOG', None)
    try:
        a = weed_path_stats(island_hop_weeds(keep, padding=pad, collar=4.0))
        os.environ['WEEDLINES_LOG'] = '1'
        b = weed_path_stats(island_hop_weeds(keep, padding=pad, collar=4.0))
        assert a == b, (a, b)
    finally:
        if before is None:
            os.environ.pop('WEEDLINES_LOG', None)
        else:
            os.environ['WEEDLINES_LOG'] = before


def test_stacked_satellite_dot_attaches_to_stem():
    """A small stacked speck must get one cut to its host, not a wrap."""
    stem = _rect_path(20, 28, 6, 30)
    dot = _rect_path(20, 18, 6, 6)
    assert _is_stacked_satellite(dot, stem)
    assert not _is_stacked_satellite(stem, dot)
    # Thin neighbor beside a wide body is not a stacked speck.
    wide = _rect_path(0, 18, 20, 30)
    thin = _rect_path(24, 18, 4, 20)
    assert not _is_stacked_satellite(thin, wide)
    keep = QPainterPath()
    keep.addPath(stem)
    keep.addPath(dot)
    weed = island_hop_weeds(keep, padding=[8, 8, 8, 8], collar=4.0)
    keep_fill = even_odd_keep_fill(keep)
    hit = None
    for x0, y0, x1, y1 in _line_segments(weed):
        mx, my = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
        if keep_fill.contains(QPointF(mx, my)):
            continue
        if 20.0 <= mx <= 26.0 and 24.0 <= my <= 28.0:
            hit = (x0, y0, x1, y1)
            break
    assert hit is not None, "dot did not attach to the stem"


def test_stacked_speck_prefers_corner_join_to_neighbor():
    """United host+speck vs next block: short speck-corner join, not shoulder."""
    keep = QPainterPath()
    keep.addPath(_rect_path(20.0, 46.0, 6.0, 36.0))
    keep.addPath(_rect_path(20.0, 28.0, 6.0, 8.0))
    keep.addPath(_rect_path(50.0, 28.0, 6.0, 54.0))
    bodies = list_closed_subpaths(keep)
    assert len(bodies) == 3
    stem, speck, neighbor = bodies
    assert _is_stacked_satellite(speck, stem)
    keep_fill = even_odd_keep_fill(keep)
    pad = [12.0, 12.0, 12.0, 12.0]
    work = padded_work_rect(keep, pad)
    rules = weeds_mod._cut_rules()
    fused, _groups, _sat = _agglomerate_islands(
        bodies, keep_fill, work, DEFAULT_CHANNEL_STANDOFF, 1.0, None,
        rules=rules)
    # collar so the three islands share one enclosure (gap 24 > 4×default).
    weed = island_hop_weeds(keep, padding=pad, collar=8.0)

    def _near(px, py, tx, ty, r=3.0):
        return math.hypot(px - tx, py - ty) <= r

    def _classify(path):
        good, bad = [], []
        for x0, y0, x1, y1 in _line_segments(path):
            mx, my = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
            if keep_fill.contains(QPointF(mx, my)):
                continue
            speck_nb = (
                (_near(x0, y0, 26.0, 28.0) and _near(x1, y1, 50.0, 28.0))
                or (_near(x0, y0, 50.0, 28.0) and _near(x1, y1, 26.0, 28.0)))
            shoulder = (
                (_near(x0, y0, 26.0, 46.0) and _near(x1, y1, 50.0, 28.0))
                or (_near(x0, y0, 50.0, 28.0) and _near(x1, y1, 26.0, 46.0)))
            if speck_nb:
                good.append((x0, y0, x1, y1))
            if shoulder:
                bad.append((x0, y0, x1, y1))
        return good, bad

    for label, path in (('agglomerate', fused), ('auto', weed)):
        good, bad = _classify(path)
        assert good, "%s: expected short speck-to-neighbor corner join" % label
        assert not bad, "%s: stem-shoulder diagonal should not win: %s" % (
            label, bad)
        for seg in good:
            ln = math.hypot(seg[2] - seg[0], seg[3] - seg[1])
            assert ln < 28.0, "%s join too long: %s" % (label, seg)
            assert abs(seg[3] - seg[1]) < 6.0, (
                "%s join should be near-horizontal" % label)


def test_wide_corridor_gets_gutter_steps():
    """Hanging marks in a wide major gap are bridged at the gutter."""
    keep = QPainterPath()
    keep.addPath(_rect_path(0, 18, 16, 30))
    keep.addPath(_rect_path(40, 16, 4, 14))
    keep.addPath(_rect_path(48, 16, 4, 14))
    keep.addPath(_rect_path(72, 18, 20, 30))
    weed = island_hop_weeds(keep, padding=[8, 8, 8, 8], collar=4.0)
    keep_fill = even_odd_keep_fill(keep)
    left = right = None
    for x0, y0, x1, y1 in _line_segments(weed):
        mx, my = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
        if keep_fill.contains(QPointF(mx, my)):
            continue
        if my > 32.0:
            continue
        if 16.0 <= mx <= 40.0:
            left = (x0, y0, x1, y1)
        if 52.0 <= mx <= 72.0:
            right = (x0, y0, x1, y1)
    assert left is not None, "no gutter cut from left major to first mark"
    assert right is not None, "no gutter cut from second mark to right major"


def test_blocked_corridor_does_not_graze_t_arm():
    """A t–s alley with a mark in it must not seal under the t bar."""
    t = _letter_t()
    keep = QPainterPath()
    keep.addPath(t)
    keep.addPath(_rect_path(64, 18, 4, 12))
    keep.addPath(_rect_path(80, 18, 16, 54))
    weed = island_hop_weeds(keep, padding=[8, 8, 8, 8], collar=4.0)
    keep_fill = even_odd_keep_fill(keep)
    grazes = []
    for x0, y0, x1, y1 in _line_segments(weed):
        mx, my = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
        if keep_fill.contains(QPointF(mx, my)):
            continue
        ln = math.hypot(x1 - x0, y1 - y0)
        if ln < 8.0:
            continue
        if 48.0 <= mx <= 62.0 and 24.5 <= my <= 28.0:
            grazes.append((x0, y0, x1, y1))
    assert not grazes, "t–s seal still grazes the t arm: %s" % grazes


def test_corridor_by_overlap_quotes_not_apostrophe():
    """Facing overlap of both islands is a corridor; a hanging mark is not."""
    quotes = list_closed_subpaths(_quote_pair())
    assert len(quotes) == 2
    assert _is_corridor_pair(quotes[0], quotes[1])
    letter = _rect_path(10, 18, 8, 30)
    mark = _rect_path(24, 20, 3.4, 9.3)
    assert not _is_corridor_pair(letter, mark)


def _end_near_keep(x, y, keep_fill, tol=0.25):
    """True if the weed end meets keep (outline or fill); boundary OK."""
    if weeds_mod._point_near_path(x, y, keep_fill, tol=tol):
        return True
    if keep_fill.contains(QPointF(x, y)):
        return True
    for dx, dy in ((tol, 0), (-tol, 0), (0, tol), (0, -tol)):
        if keep_fill.contains(QPointF(x + dx, y + dy)):
            return True
    return False


def test_fuse_cuts_reach_keep_outlines():
    """Keep-to-keep seals must meet the design, not stop a millimetre short."""
    keep = _letters_hi()
    weed = island_hop_weeds(keep, padding=[10, 10, 10, 10], collar=4.0)
    keep_fill = even_odd_keep_fill(keep)
    gap = QRectF(39, 15, 22, 60)
    hits = []
    for x0, y0, x1, y1 in _line_segments(weed):
        mx, my = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
        if keep_fill.contains(QPointF(mx, my)):
            continue
        if not gap.contains(QPointF(mx, my)):
            continue
        if math.hypot(x1 - x0, y1 - y0) < 4.0:
            continue
        hits.append((x0, y0, x1, y1))
    assert hits, "no H–I gap cut to check"
    bodies = list_closed_subpaths(keep)
    keep_keeps = []
    for seg in hits:
        if len(bodies) >= 2 and weeds_mod._seg_spans_pair(
                seg, bodies[0], bodies[1], tol=2.5):
            keep_keeps.append(seg)
    assert keep_keeps, "no keep-to-keep H–I fuse in the gap"
    for x0, y0, x1, y1 in keep_keeps:
        assert _end_near_keep(x0, y0, keep_fill), "cut misses keep at %s" % (
            (x0, y0),)
        assert _end_near_keep(x1, y1, keep_fill), "cut misses keep at %s" % (
            (x1, y1),)


def _kappa_borderline_bay_body():
    """U with κ ≈ 2.0 and depth 0.5×mouth: default depth gate off, ratio 0.15 on."""
    # Mouth 20, depth 10 → L_coast=40, κ=2; deep iff ratio < 0.5.
    return _poly_path((
        (0, 0), (10, 0), (10, 10), (30, 10), (30, 0), (40, 0),
        (40, 24), (0, 24),
    ))


def test_peninsula_ratio_seals_borderline_bay():
    """Lowering peninsula_ratio seals a κ≥2 bay the default depth gate skips."""
    keep = _kappa_borderline_bay_body()
    mouths = _hull_bay_mouths(keep, min_depth=1.0, min_width=4.0)
    assert mouths
    left, right, deep, run = mouths[0]
    mw = _bay_mouth_width(left, right)
    depth = _point_seg_dist(
        deep.x(), deep.y(), left.x(), left.y(), right.x(), right.y())
    assert abs(_bay_kappa(left, right, run, mouth_w=mw) - 2.0) < 0.15
    assert not _peninsula_is_deep(depth, mw, ratio=0.75)
    assert _peninsula_is_deep(depth, mw, ratio=0.15)

    def mouth_seals(weed):
        keep_fill = even_odd_keep_fill(keep)
        return _keep_to_keep_in_box(weed, keep_fill, 9.0, -0.5, 31.0, 3.0)

    default = island_hop_weeds(keep, padding=[10, 10, 10, 10], collar=4.0)
    shallow = island_hop_weeds(
        keep, padding=[10, 10, 10, 10], collar=4.0, peninsula_ratio=0.15)
    assert not mouth_seals(default), "default ratio sealed borderline bay"
    assert mouth_seals(shallow), "ratio 0.15 did not seal borderline bay"


def test_long_corridor_splits_at_max_chunk():
    """A tall H–I alley must gain extra seals when max_chunk is short."""
    keep = _letters_hi()
    keep_fill = even_odd_keep_fill(keep)

    def gap_seals(weed):
        n = 0
        for x0, y0, x1, y1 in _line_segments(weed):
            mx, my = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
            if keep_fill.contains(QPointF(mx, my)):
                continue
            if 39.0 <= mx <= 61.0 and 18.0 <= my <= 72.0:
                if math.hypot(x1 - x0, y1 - y0) >= 4.0:
                    n += 1
        return n

    loose = island_hop_weeds(keep, padding=[10, 10, 10, 10], collar=4.0, max_chunk=80)
    tight = island_hop_weeds(keep, padding=[10, 10, 10, 10], collar=4.0, max_chunk=18)
    assert gap_seals(tight) > gap_seals(loose), (
        "max_chunk did not split the H–I corridor (%s vs %s)" % (
            gap_seals(tight), gap_seals(loose)))


def _side_by_side_rects(w, h, gap=4.0, ox=0.0, oy=0.0):
    """Two axis-aligned rects side by side (vertical alley of width *gap*)."""
    p = QPainterPath()
    p.addPath(_rect_path(ox, oy, w, h))
    p.addPath(_rect_path(ox + w + gap, oy, w, h))
    return p


def _alley_gap_seals(weed, keep_fill, x0, x1, y0, y1, min_len=2.0):
    """Keep-to-keep seal midpoints whose centre sits in the alley bbox."""
    mids = []
    for a, b, c, d in _line_segments(weed):
        mx, my = 0.5 * (a + c), 0.5 * (b + d)
        if keep_fill.contains(QPointF(mx, my)):
            continue
        if not (x0 <= mx <= x1 and y0 <= my <= y1):
            continue
        if math.hypot(c - a, d - b) < min_len:
            continue
        mids.append((mx, my, a, b, c, d))
    return mids


def test_short_corridor_one_mid_seal():
    """Two 40×8 rects, gap 4: span 8 ≤ 2.5×4 → one mid seal, not dual ends."""
    keep = _side_by_side_rects(40.0, 8.0, gap=4.0)
    assert _is_corridor_pair(
        list_closed_subpaths(keep)[0], list_closed_subpaths(keep)[1])
    weed = island_hop_weeds(keep, padding=[10, 10, 10, 10], collar=4.0)
    keep_fill = even_odd_keep_fill(keep)
    # Alley between x=40..44, y=0..8 (padding expands work but gap is local).
    seals = _alley_gap_seals(weed, keep_fill, 39.0, 45.0, -1.0, 9.0)
    assert len(seals) == 1, "short alley expected one mid seal, got %s" % seals
    mx, my, _a, _b, _c, _d = seals[0]
    assert 2.0 <= my <= 6.0, "seal not mid-alley (my=%s)" % my
    # Connected ends: keep-to-keep across the gap.
    cleaned = weeds_mod._require_connected_ends(weed, keep, tol=1.5)
    assert _alley_gap_seals(cleaned, keep_fill, 39.0, 45.0, -1.0, 9.0)


def test_long_corridor_two_end_seals():
    """Two 40×40 rects, gap 4: span 40 > 2.5×4 → both end seals."""
    keep = _side_by_side_rects(40.0, 40.0, gap=4.0)
    weed = island_hop_weeds(keep, padding=[10, 10, 10, 10], collar=4.0)
    keep_fill = even_odd_keep_fill(keep)
    seals = _alley_gap_seals(weed, keep_fill, 39.0, 45.0, -1.0, 41.0)
    assert len(seals) >= 2, "long alley expected two end seals, got %s" % seals
    ys = sorted(s[1] for s in seals)
    assert ys[0] < 8.0, "missing top end seal (ys=%s)" % ys
    assert ys[-1] > 32.0, "missing bottom end seal (ys=%s)" % ys
    # Spaced: no two seals within ~width (gap) of each other.
    width = 4.0
    for i, (mx0, my0, *_r0) in enumerate(seals):
        for mx1, my1, *_r1 in seals[i + 1:]:
            d = math.hypot(mx1 - mx0, my1 - my0)
            assert d >= width * 0.9, (
                "seals too close on long alley: %.2f < width" % d)
    cleaned = weeds_mod._require_connected_ends(weed, keep, tol=1.5)
    assert len(_alley_gap_seals(
        cleaned, keep_fill, 39.0, 45.0, -1.0, 41.0)) >= 2


def test_short_corridor_no_second_seal_near_mid():
    """Short alley must not place a second seal within ~width of the first."""
    keep = _side_by_side_rects(40.0, 8.0, gap=4.0)
    weed = island_hop_weeds(keep, padding=[10, 10, 10, 10], collar=4.0, max_chunk=2.0)
    keep_fill = even_odd_keep_fill(keep)
    seals = _alley_gap_seals(weed, keep_fill, 39.0, 45.0, -1.0, 9.0)
    assert len(seals) == 1, "short alley + tiny max_chunk still one seal: %s" % (
        seals,)
    width = 4.0
    for i, (mx0, my0, *_r0) in enumerate(seals):
        for mx1, my1, *_r1 in seals[i + 1:]:
            assert math.hypot(mx1 - mx0, my1 - my0) >= width * 0.9


def test_outline_samples_stay_on_path():
    """BBox corners of a circle are not outline samples (cuts to nowhere)."""
    keep = _circle_path(50, 50, 30)
    br = keep.boundingRect()
    samples = weeds_mod._outline_samples(keep, max_pts=128)
    assert samples, "expected outline samples"
    corner = QPointF(br.left(), br.top())
    # True outline is 30*sqrt(2)-30 ≈ 12.4 mm inside that corner.
    for p in samples:
        d = math.hypot(p.x() - corner.x(), p.y() - corner.y())
        assert d > 2.0, "bbox corner leaked into outline samples: %s" % (
            (p.x(), p.y()),)


def _square_wave_run(teeth=3, width=2.0, height=4.0):
    """Open serrated polyline: square teeth point +y (into waste)."""
    pts = []
    x = 0.0
    for _ in range(teeth):
        pts.append((x, 0.0))
        pts.append((x, height))
        x += width
        pts.append((x, height))
        pts.append((x, 0.0))
        x += width
    return pts


def _pointed_comb_run(teeth=3, width=2.0, height=4.0):
    """Open zig-zag comb: sharp tips point +y (turn ≫ delicate angle)."""
    pts = [(0.0, 0.0)]
    x = 0.0
    half = 0.5 * width
    for _ in range(teeth):
        pts.append((x + half, height))
        x += width
        pts.append((x, 0.0))
    return pts


def test_frontier_smooth_run_low_rho():
    """Straight and gentle-arc frontier runs stay near ρ ≈ 1."""
    straight = [(0.0, 0.0), (10.0, 0.0), (20.0, 0.0), (30.0, 0.0)]
    assert _frontier_complexity(straight) < 1.15
    assert abs(_run_arc_length(straight) - 30.0) < 1e-9
    assert abs(_run_chord_length(straight) - 30.0) < 1e-9

    # Shallow circular arc (~30°): ρ stays near 1.
    r = 40.0
    arc = []
    for i in range(9):
        t = math.radians(i * 30.0 / 8.0)
        arc.append((r * math.sin(t), r * (1.0 - math.cos(t))))
    assert _frontier_complexity(arc) < 1.15


def test_frontier_serrated_run_high_rho():
    """Square-wave frontier is clearly more complex than a smooth run."""
    serrated = _square_wave_run(teeth=3, width=2.0, height=4.0)
    rho = _frontier_complexity(serrated)
    assert rho > 2.0, "expected serrated ρ > 2, got %s" % rho
    smooth = [(0.0, 0.0), (_run_chord_length(serrated), 0.0)]
    assert rho > _frontier_complexity(smooth) * 1.5


def test_frontier_three_tooth_comb_tip_count():
    """Three keep teeth into waste (+y) yield tip_count ≥ 3."""
    comb = _pointed_comb_run(teeth=3, width=2.0, height=4.0)
    # Waste above the run; tips are the +y tooth peaks.
    n = _frontier_tip_count(comb, waste_dir=(0.0, 1.0))
    assert n >= 3, "expected ≥3 tips on 3-tooth comb, got %s" % n
    m = _frontier_run_metrics(comb, waste_dir=(0.0, 1.0))
    assert m.tip_count == n
    assert m.rho > 1.5


def test_frontier_empty_or_tiny_safe_defaults():
    """Empty/tiny runs: ρ=1, tip_count=0, no exceptions."""
    assert _frontier_complexity([]) == 1.0
    assert _frontier_complexity([(0.0, 0.0)]) == 1.0
    assert _frontier_complexity([(1.0, 1.0), (1.0, 1.0)]) == 1.0
    assert _run_arc_length([]) == 0.0
    assert _run_chord_length([(0.0, 0.0)]) == 0.0
    assert _frontier_tip_count([]) == 0
    assert _frontier_tip_count([(0.0, 0.0), (1.0, 0.0)]) == 0
    m = _frontier_run_metrics([])
    assert m.rho == 1.0 and m.tip_count == 0
    assert m.length == 0.0 and m.chord == 0.0


def _poly_path(pts):
    """Closed QPainterPath from (x, y) vertices."""
    p = QPainterPath()
    p.moveTo(pts[0][0], pts[0][1])
    for x, y in pts[1:]:
        p.lineTo(x, y)
    p.closeSubpath()
    return p


def _deep_smooth_bay_body():
    """Rect 40×28 with a top U-notch: mouth 16, depth 16 (ratio 1.0)."""
    return _poly_path((
        (0, 0), (12, 0), (12, 16), (28, 16), (28, 0), (40, 0),
        (40, 28), (0, 28),
    ))


def _deep_smooth_c_bay_body():
    """Rect 40×40 with a right C-notch: mouth 16, depth 16."""
    return _poly_path((
        (0, 0), (40, 0), (40, 12), (24, 12), (24, 28), (40, 28),
        (40, 40), (0, 40),
    ))


def _shallow_smooth_notch_body():
    """Rect 40×24 with a top U-notch: mouth 24, depth 6 (ratio 0.25)."""
    return _poly_path((
        (0, 0), (8, 0), (8, 6), (32, 6), (32, 0), (40, 0),
        (40, 24), (0, 24),
    ))


def _shallow_jagged_bay_body():
    """Shallow bay (depth < 0.75×mouth) with long coast so κ ≥ 3 (D007)."""
    # Mouth 20 at y=0; 10 teeth of depth 6 → L_coast ≫ mouth, still not deep.
    pts = [(0, 0), (10, 0), (10, 1.0)]
    x = 10.0
    for _ in range(10):
        pts.append((x + 1.0, 6.0))
        x += 2.0
        pts.append((x, 1.0))
    pts.extend(((30, 0), (50, 0), (50, 28), (0, 28)))
    return _poly_path(pts)


def _undercut_bay_body():
    """Mouth 10, wider interior 20 (undercut), moderate depth (κ in [2, 3))."""
    # Bottle bay: neck 10 wide, chamber 20 wide, depth ~12.
    return _poly_path((
        (0, 0), (15, 0), (15, 4), (10, 4), (10, 16), (30, 16), (30, 4),
        (25, 4), (25, 0), (40, 0), (40, 28), (0, 28),
    ))


def _keep_to_keep_in_box(weed, keep_fill, x0, y0, x1, y1, min_len=6.0):
    """Waste segments in *box* whose both ends meet keep."""
    hits = []
    for sx, sy, ex, ey in _line_segments(weed):
        mx, my = 0.5 * (sx + ex), 0.5 * (sy + ey)
        if keep_fill.contains(QPointF(mx, my)):
            continue
        if not (x0 <= mx <= x1 and y0 <= my <= y1):
            continue
        if math.hypot(ex - sx, ey - sy) < min_len:
            continue
        if _end_near_keep(sx, sy, keep_fill) and _end_near_keep(ex, ey, keep_fill):
            hits.append((sx, sy, ex, ey))
    return hits


def test_bay_kappa_and_undercut_helpers():
    """Pure D007 helpers: κ, coast length, undercut probe."""
    deep = _deep_smooth_bay_body()
    mouths = _hull_bay_mouths(deep, min_depth=1.0, min_width=4.0)
    assert len(mouths) >= 1
    left, right, deep_pt, run = mouths[0]
    mw = _bay_mouth_width(left, right)
    assert abs(mw - 16.0) < 0.5
    assert abs(_bay_coast_length(left, right, run) - 48.0) < 1.0
    assert abs(_bay_kappa(left, right, run) - 3.0) < 0.1
    assert _bay_should_seal(left, right, deep_pt, run)

    shallow = _shallow_smooth_notch_body()
    mouths = _hull_bay_mouths(shallow, min_depth=1.0, min_width=4.0)
    left, right, deep_pt, run = mouths[0]
    assert _bay_kappa(left, right, run) < 2.0
    assert not _bay_should_seal(left, right, deep_pt, run)

    # Approx: deep U → κ = 2·d/w + 1 ≥ 3; shallow notch stays below min.
    assert _approx_bay_kappa(10.0, 10.0) >= 3.0
    assert _approx_bay_kappa(2.0, 10.0) < 2.0
    assert _peninsula_should_detach(10.0, 10.0, [(0, 0), (10, 0)])
    assert not _peninsula_should_detach(2.0, 10.0, [(0, 0), (10, 0)])

    under = _undercut_bay_body()
    mouths = _hull_bay_mouths(under, min_depth=1.0, min_width=4.0)
    assert mouths, "undercut bay missing"
    sealed = False
    undercut = False
    for left, right, deep_pt, run in mouths:
        mw = _bay_mouth_width(left, right)
        depth = _point_seg_dist(
            deep_pt.x(), deep_pt.y(), left.x(), left.y(), right.x(), right.y())
        k = _bay_kappa(left, right, run, mouth_w=mw)
        if _bay_has_undercut(left, right, deep_pt, run):
            undercut = True
        if _bay_should_seal(left, right, deep_pt, run, depth=depth, mouth_w=mw):
            sealed = True
        # Prefer the neck mouth (~10), not a wider hull edge.
        if mw < 14.0 and 2.0 <= k < 3.0:
            assert _bay_has_undercut(left, right, deep_pt, run), (
                "bottle interior should undercut mouth=%s κ=%s" % (mw, k))
    assert undercut or sealed, "undercut bay should undercut or seal"


def test_peninsula_should_detach_or_gates():
    """D007: detach via κ/depth approx (ρ/tips alone no longer seal)."""
    smooth = [(0.0, 0.0), (10.0, 0.0), (20.0, 0.0)]
    assert _peninsula_should_detach(10.0, 10.0, smooth)
    assert not _peninsula_should_detach(2.0, 10.0, smooth)
    comb = _pointed_comb_run(teeth=3, width=2.0, height=4.0)
    # Short shallow comb: κ_approx = 2*2/10+1 = 1.4 < 2 → not a bay.
    assert not _peninsula_should_detach(2.0, 10.0, comb, waste_dir=(0.0, 1.0))


def test_deep_smooth_bay_is_sealed():
    """A U with κ ≥ 3 (or deep) gets a keep-to-keep mouth seal."""
    keep = _deep_smooth_bay_body()
    weed = island_hop_weeds(keep, padding=[10, 10, 10, 10], collar=4.0)
    keep_fill = even_odd_keep_fill(keep)
    seals = _keep_to_keep_in_box(weed, keep_fill, 11.0, -0.5, 29.0, 4.0)
    assert seals, "deep smooth bay mouth was not sealed"


def test_shallow_smooth_notch_is_not_sealed():
    """A shallow rectangular notch (κ < 2) must stay open."""
    keep = _shallow_smooth_notch_body()
    weed = island_hop_weeds(keep, padding=[10, 10, 10, 10], collar=4.0)
    keep_fill = even_odd_keep_fill(keep)
    seals = _keep_to_keep_in_box(weed, keep_fill, 7.0, -0.5, 33.0, 5.0)
    assert not seals, "shallow smooth notch was sealed: %s" % seals


def test_shallow_jagged_bay_is_sealed():
    """A shallow bay with κ ≥ 3 (long coast) still seals at the neck."""
    keep = _shallow_jagged_bay_body()
    mouths = _hull_bay_mouths(keep, min_depth=1.0, min_width=4.0)
    assert mouths, "jagged bay was not a hull-bay candidate"
    jagged = False
    for left, right, deep, run in mouths:
        mouth_w = math.hypot(right.x() - left.x(), right.y() - left.y())
        depth = _point_seg_dist(
            deep.x(), deep.y(), left.x(), left.y(), right.x(), right.y())
        assert depth < 0.75 * mouth_w, "fixture is deep, not a κ case"
        assert _bay_kappa(left, right, run, mouth_w=mouth_w) >= 3.0, (
            "fixture needs κ ≥ 3")
        if _bay_should_seal(
                left, right, deep, run, depth=depth, mouth_w=mouth_w):
            jagged = True
    assert jagged, "expected κ ≥ 3 seal on the jagged bay"
    weed = island_hop_weeds(keep, padding=[10, 10, 10, 10], collar=4.0)
    keep_fill = even_odd_keep_fill(keep)
    seals = _keep_to_keep_in_box(weed, keep_fill, 9.0, -0.5, 31.0, 2.5)
    assert seals, "shallow jagged bay was not sealed"


def test_peninsula_detach_uses_neck():
    """Detach is the mouth; both ends meet keep (no floating spur)."""
    keep = _shallow_jagged_bay_body()
    weed = island_hop_weeds(keep, padding=[10, 10, 10, 10], collar=4.0)
    keep_fill = even_odd_keep_fill(keep)
    seals = _keep_to_keep_in_box(weed, keep_fill, 9.0, -0.5, 31.0, 2.5)
    assert seals, "expected a neck seal"
    for x0, y0, x1, y1 in seals:
        assert abs(y1 - y0) < 3.0, "neck seal is not across the mouth: %s" % (
            (x0, y0, x1, y1),)
        assert max(x0, x1) - min(x0, x1) > 12.0, (
            "neck seal does not span the mouth: %s" % ((x0, y0, x1, y1),))
        assert _end_near_keep(x0, y0, keep_fill)
        assert _end_near_keep(x1, y1, keep_fill)
    # Nothing floating among the teeth (y deeper than the neck).
    for x0, y0, x1, y1 in _line_segments(weed):
        mx, my = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
        if keep_fill.contains(QPointF(mx, my)):
            continue
        if not (10.0 <= mx <= 30.0 and 2.4 <= my <= 7.0):
            continue
        raise AssertionError(
            "floating or in-bay spur at %s" % ((x0, y0, x1, y1),))


def test_require_connected_ends_drops_floating_spur():
    """A free-ended weed spur is removed; a keep-to-keep seal stays."""
    keep = QPainterPath()
    keep.addPath(_rect_path(0, 0, 20, 20))
    keep.addPath(_rect_path(40, 0, 20, 20))
    weed = QPainterPath()
    # Good: both ends on keep outlines.
    weed.moveTo(20, 10)
    weed.lineTo(40, 10)
    # Bad: only one end on keep; the other floats in waste.
    weed.moveTo(10, 20)
    weed.lineTo(10, 35)
    # Bad: both ends free.
    weed.moveTo(25, 5)
    weed.lineTo(35, 15)
    cleaned = weeds_mod._require_connected_ends(weed, keep, tol=1.0)
    segs = _line_segments(cleaned)
    assert len(segs) == 1, "expected only the keep-to-keep seal, got %s" % segs
    x0, y0, x1, y1 = segs[0]
    assert min(x0, x1) <= 20.5 and max(x0, x1) >= 39.5


def _wide_stem_pair():
    """Two stems, wide gap (not a corridor) that still share one enclosure.

    Height 24 / gap 16: gap > 0.6×overlap (not a corridor) and
    gap ≤ word-cluster threshold at default collar (one enclosure).
    """
    return _side_by_side_rects(8.0, 24.0, gap=16.0)


def _hanging_mark_cluster():
    """Stem + short hanging mark + neighbor (wide inter-stem gap)."""
    p = QPainterPath()
    p.addPath(_rect_path(0, 20, 10, 50))
    p.addPath(_rect_path(14, 20, 4, 12))
    p.addPath(_rect_path(42, 20, 10, 50))
    return p


def test_wide_stem_gap_gets_one_bottom_seal():
    """Two stems + open bottom (wide gap): one bottom-ish mouth after islands."""
    keep = _wide_stem_pair()
    bodies = list_closed_subpaths(keep)
    assert len(bodies) == 2
    assert not _is_corridor_pair(bodies[0], bodies[1])
    nodes = _nest_closed_paths(bodies)
    groups = weeds_mod._enclosure_groups(nodes, 4.0)
    assert len(groups) == 1 and len(groups[0][0]) == 2, (
        "fixture must be one enclosure cluster, got %s" % (
            [len(g[0]) for g in groups],))
    weed = island_hop_weeds(keep, padding=[10, 10, 10, 10], collar=4.0)
    keep_fill = even_odd_keep_fill(keep)
    # Alley x=8..24, stems y=0..24. Island fuse sits at the top (y=0).
    bot = _alley_gap_seals(weed, keep_fill, 7.0, 25.0, 19.0, 26.0, min_len=10.0)
    assert len(bot) == 1, "expected one bottom-ish mouth seal, got %s" % bot
    _mx, _my, x0, y0, x1, y1 = bot[0]
    assert max(x0, x1) - min(x0, x1) > 10.0, (
        "bottom seal does not span the gap: %s" % ((x0, y0, x1, y1),))
    cleaned = weeds_mod._require_connected_ends(weed, keep, tol=1.5)
    assert _alley_gap_seals(cleaned, keep_fill, 7.0, 25.0, 19.0, 26.0, min_len=10.0)


def test_hanging_mark_pocket_sealed_not_through_cut():
    """Hanging mark pocket/neck is sealed; no through-cut under the arm."""
    keep = _hanging_mark_cluster()
    weed = island_hop_weeds(keep, padding=[10, 10, 10, 10], collar=4.0)
    keep_fill = even_odd_keep_fill(keep)
    # Neck: host (x=10) to mark (x=14) near the mark's inner end (y≈32).
    pocket = _alley_gap_seals(weed, keep_fill, 9.0, 19.0, 30.0, 36.0, min_len=2.0)
    assert pocket, "hanging-mark pocket/neck was not sealed"
    under_arm = []
    for x0, y0, x1, y1 in _line_segments(weed):
        my = 0.5 * (y0 + y1)
        if keep_fill.contains(QPointF(0.5 * (x0 + x1), my)):
            continue
        if not (28.0 <= my <= 36.0):
            continue
        if math.hypot(x1 - x0, y1 - y0) < 16.0:
            continue
        xs = (x0, x1)
        if min(xs) <= 12.0 and max(xs) >= 40.0:
            under_arm.append((x0, y0, x1, y1))
    assert not under_arm, "through-cut under the hanging arm: %s" % under_arm
    cleaned = weeds_mod._require_connected_ends(weed, keep, tol=1.5)
    assert _alley_gap_seals(cleaned, keep_fill, 9.0, 19.0, 30.0, 36.0, min_len=2.0)


def test_weeds_have_no_letter_class_dispatch():
    """Cluster seals stay geometric; no letter/apostrophe/quote type branches."""
    import inspect
    import re
    src = inspect.getsource(weeds_mod)
    assert not re.search(
        r"def _\w*(apostrophe|letter_class|is_letter|quote_type)\w*", src)
    for needle in (
            "kind == 'apostrophe'", 'kind == "apostrophe"',
            "kind == 'letter'", 'kind == "letter"',
            "kind == 'quote'", 'kind == "quote"'):
        assert needle not in src


@requires_clipper
def test_auto_weed_ends_are_connected():
    """Open auto cuts meet keep or another weed at both ends."""
    # Circle + corner speck: old outline samples used the circle bbox
    # corner and grew a fuse into empty waste.
    corner_speck = QPainterPath()
    corner_speck.addPath(_circle_path(50, 50, 22))
    corner_speck.addPath(_rect_path(8, 8, 6, 6))

    fixtures = (
        _letters_hi(),
        _letter_o(),
        _star12(),
        _quoted_blocks(),
        corner_speck,
        _alley_with_serif_pocket(),
        _close_satellite_pair(),
        _three_stem_gutter(),
    )
    tol = max(1.5, DEFAULT_CHANNEL_STANDOFF + 0.25)
    for keep in fixtures:
        weed = island_hop_weeds(keep, padding=[10, 10, 10, 10], collar=4.0)
        segs = _line_segments(weed)
        assert segs, "expected some weed geometry"
        keep_edges = weeds_mod._keep_outline_edges(keep)
        bodies = list_closed_subpaths(keep)
        delta = min(weeds_mod.DEFAULT_FRAME_CLEARANCE, 10.0 - 2.0)
        rings = weeds_mod._cluster_offset_rings(bodies, delta) if bodies else []
        for seg in segs:
            for px, py in ((seg[0], seg[1]), (seg[2], seg[3])):
                on_keep = weeds_mod._point_near_edges(px, py, keep_edges, tol)
                on_weed = weeds_mod._point_near_weed_segs(
                    px, py, segs, skip=seg, tol=tol)
                if on_keep or on_weed:
                    continue
                # Keep→frame radial tip lands on the continuous peel rail.
                corridor_ok = False
                if rings:
                    hit = weeds_mod._nearest_on_rings(px, py, rings)
                    corridor_ok = hit is not None and hit[2] <= tol
                assert corridor_ok, (
                    "dangling weed end at %.2f,%.2f seg=%s" % (
                        px, py, seg))


def _alley_with_serif_pocket():
    """Two 8×40 stems, gap 4; right stem has a mid-alley facing notch."""
    p = QPainterPath()
    p.addPath(_rect_path(0, 0, 8, 40))
    p.addPath(_poly_path((
        (12, 0), (20, 0), (20, 40), (12, 40),
        (12, 28), (18, 28), (18, 16), (12, 16),
    )))
    return p


def _close_satellite_pair():
    """6×6 speck stacked on a 6×30 stem, gap 2 (AABB would look like a corridor)."""
    p = QPainterPath()
    p.addPath(_rect_path(20, 28, 6, 30))
    p.addPath(_rect_path(20, 20, 6, 6))
    return p


def test_alley_serif_pocket_core_and_detach():
    """Channel core is sealed and the side pocket is detached — not huge mouths only."""
    keep = _alley_with_serif_pocket()
    bodies = list_closed_subpaths(keep)
    assert len(bodies) == 2
    assert _is_corridor_pair(bodies[0], bodies[1])
    weed = island_hop_weeds(keep, padding=[10, 10, 10, 10], collar=4.0)
    keep_fill = even_odd_keep_fill(keep)
    # Thin alley x=8..12. Long core (L/W=10) → both end seals.
    core = _alley_gap_seals(weed, keep_fill, 7.5, 12.5, -1.0, 41.0, min_len=2.0)
    assert len(core) >= 2, "expected channel-core end seals, got %s" % core
    ys = sorted(s[1] for s in core)
    assert ys[0] < 6.0, "missing top core seal (ys=%s)" % ys
    assert ys[-1] > 34.0, "missing bottom core seal (ys=%s)" % ys
    # Pocket neck: vertical-ish cut just inside the notch (x=12..18, y=16..28).
    pocket = []
    for x0, y0, x1, y1 in _line_segments(weed):
        mx, my = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
        if keep_fill.contains(QPointF(mx, my)):
            continue
        if not (11.5 <= mx <= 18.5 and 15.0 <= my <= 29.0):
            continue
        if abs(x1 - x0) > 3.0:
            continue
        if abs(y1 - y0) < 8.0:
            continue
        pocket.append((x0, y0, x1, y1))
    assert pocket, "serif pocket was not detached at the neck"
    # Not a single huge mouth across alley+pocket.
    huge = []
    for x0, y0, x1, y1 in _line_segments(weed):
        mx, my = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
        if keep_fill.contains(QPointF(mx, my)):
            continue
        if not (7.0 <= mx <= 19.0 and 14.0 <= my <= 30.0):
            continue
        xs = (x0, x1)
        if min(xs) <= 8.5 and max(xs) >= 17.0:
            huge.append((x0, y0, x1, y1))
    assert not huge, "alley+pocket still sealed as one huge mouth: %s" % huge
    cleaned = weeds_mod._require_connected_ends(weed, keep, tol=1.5)
    assert _alley_gap_seals(cleaned, keep_fill, 7.5, 12.5, -1.0, 41.0, min_len=2.0)
    assert any(
        11.5 <= 0.5 * (s[0] + s[2]) <= 18.5
        and 15.0 <= 0.5 * (s[1] + s[3]) <= 29.0
        and abs(s[2] - s[0]) <= 3.0 and abs(s[3] - s[1]) >= 8.0
        for s in _line_segments(cleaned)), (
            "pocket neck dropped by connected-ends")


def test_satellite_speck_one_bridge_not_dual_mouth():
    """A close stacked speck gets one bridge, never a dual-mouth corridor."""
    keep = _close_satellite_pair()
    stem, speck = list_closed_subpaths(keep)
    if stem.boundingRect().height() < speck.boundingRect().height():
        stem, speck = speck, stem
    assert _is_stacked_satellite(speck, stem)
    assert not _is_corridor_pair(speck, stem)
    weed = island_hop_weeds(keep, padding=[8, 8, 8, 8], collar=4.0)
    keep_fill = even_odd_keep_fill(keep)
    # Gap band between speck bottom (y=26) and stem top (y=28).
    bridges = _alley_gap_seals(weed, keep_fill, 19.0, 27.0, 25.5, 28.5, min_len=1.2)
    assert len(bridges) == 1, "expected one satellite bridge, got %s" % bridges
    cleaned = weeds_mod._require_connected_ends(weed, keep, tol=1.5)
    assert len(_alley_gap_seals(
        cleaned, keep_fill, 19.0, 27.0, 25.5, 28.5, min_len=1.2)) == 1


def _three_stem_gutter(w=8.0, h=24.0, gap=12.0, n=3):
    """Three vertical stems; adjacent alleys are short corridors (L/W=2)."""
    p = QPainterPath()
    x = 0.0
    for _i in range(n):
        p.addPath(_rect_path(x, 0.0, w, h))
        x += w + gap
    return p


def test_three_stem_gutter_fork_stops_wrap():
    """Three stems + bottom gutter: branch necks stop wrap into both alleys."""
    keep = _three_stem_gutter()
    bodies = list_closed_subpaths(keep)
    assert len(bodies) == 3
    assert _is_corridor_pair(bodies[0], bodies[1])
    assert _is_corridor_pair(bodies[1], bodies[2])
    assert weeds_mod._fork_branch_mouths(bodies)
    weed = island_hop_weeds(keep, padding=[10, 10, 10, 10], collar=4.0)
    keep_fill = even_odd_keep_fill(keep)
    work = padded_work_rect(keep, [10, 10, 10, 10])
    seed = QPointF(24.0, 26.5)
    seen, cell, _world = _waste_flood(keep_fill, weed, work, seed, step=1.2)
    a0 = cell(QPointF(14.0, 20.0))
    a1 = cell(QPointF(34.0, 20.0))
    assert a0 not in seen or a1 not in seen, (
        "bottom gutter still wraps into both alleys")
    left = _alley_gap_seals(weed, keep_fill, 7.5, 20.5, 21.0, 25.5, min_len=6.0)
    right = _alley_gap_seals(weed, keep_fill, 27.5, 40.5, 21.0, 25.5, min_len=6.0)
    assert left, "missing left branch neck"
    assert right, "missing right branch neck"
    cleaned = weeds_mod._require_connected_ends(weed, keep, tol=1.5)
    assert _alley_gap_seals(cleaned, keep_fill, 7.5, 20.5, 21.0, 25.5, min_len=6.0)
    assert _alley_gap_seals(cleaned, keep_fill, 27.5, 40.5, 21.0, 25.5, min_len=6.0)


def test_three_stem_gutter_no_triple_seals_within_width():
    """Fork necks must not stack three seals inside one alley width."""
    keep = _three_stem_gutter()
    weed = island_hop_weeds(keep, padding=[10, 10, 10, 10], collar=4.0)
    keep_fill = even_odd_keep_fill(keep)
    width = 12.0
    for x0, x1 in ((7.5, 20.5), (27.5, 40.5)):
        seals = _alley_gap_seals(weed, keep_fill, x0, x1, -1.0, 25.5, min_len=6.0)
        for mx0, my0, _a, _b, _c, _d in seals:
            near = sum(
                1 for mx1, my1, _e, _f, _g, _h in seals
                if math.hypot(mx1 - mx0, my1 - my0) <= width + 0.5)
            assert near <= 2, (
                "triple-redundant seals in alley %s: %s" % ((x0, x1), seals))


def _residual_traps_for(keep, weed=None, padding=None, **auto_kw):
    pad = list(padding) if padding is not None else [10.0, 10.0, 10.0, 10.0]
    if weed is None:
        weed = island_hop_weeds(keep, padding=pad, collar=4.0, **auto_kw)
    work = padded_work_rect(keep, pad)
    return residual_waste_traps(
        keep, weed, work=work, padding=pad, collar=4.0, step=1.5)


def test_residual_traps_unsealed_deep_bay():
    """Empty weeds leave a detachable pocket on the collar peel."""
    keep = _deep_smooth_bay_body()
    traps = _residual_traps_for(keep, weed=QPainterPath())
    assert traps, "unsealed deep bay must be a residual trap"
    assert any(t.kind == 'pocket' for t in traps)


def test_residual_traps_unsealed_corridor():
    """An open long alley still wraps through the channel core."""
    keep = _side_by_side_rects(40.0, 40.0, gap=4.0)
    traps = _residual_traps_for(keep, weed=QPainterPath())
    assert any(t.kind == 'channel' for t in traps), traps


def test_residual_traps_unsealed_cluster_bay():
    """A wide non-corridor gutter still wraps under if no T4 mouth seal."""
    keep = _wide_stem_pair()
    traps = _residual_traps_for(keep, weed=QPainterPath())
    assert any(t.kind == 'cluster' for t in traps), traps


def test_residual_traps_shallow_notch_not_a_trap():
    """Shallow+smooth stays below the detach gate even with no weeds."""
    keep = _shallow_smooth_notch_body()
    traps = _residual_traps_for(keep, weed=QPainterPath())
    assert not traps, traps


def test_residual_traps_letter_o_zero():
    """O hole is keep-enclosed; outer waste is a simple collar gutter."""
    assert _residual_traps_for(_letter_o()) == []


def test_residual_traps_star12_zero():
    """Star valleys are keep-tip valleys, not residual traps."""
    assert _residual_traps_for(_star12(), padding=[12.0, 12.0, 12.0, 12.0]) == []


def test_residual_traps_hi_zero():
    """HI counters and the channel core are sealed after auto weeds."""
    assert _residual_traps_for(_letters_hi()) == []


def test_residual_traps_quoted_blocks_zero():
    """Quoted geometric blocks have no leftover detachable wrap."""
    assert _residual_traps_for(_quoted_blocks()) == []


def _stem_comma_stem_t():
    """i-stem, comma, i-stem, t — frame-attached peninsulas under the baseline."""
    p = QPainterPath()
    p.addPath(_rect_path(10, 10, 6, 36))   # first stem
    p.addPath(_rect_path(22, 34, 6, 14))   # hanging comma-like mark
    p.addPath(_rect_path(40, 10, 6, 36))   # second stem
    p.addPath(_rect_path(52, 8, 6, 38))    # t stem
    p.addPath(_rect_path(52, 8, 14, 6))    # t bar
    return p


def _quoted_in_frame_with_holes():
    """Quoted block letters inside a keep frame with circular punches."""
    p = QPainterPath()
    p.addRect(QRectF(0, 0, 200, 90))
    p.addRect(QRectF(8, 8, 184, 74))
    # Circular punches in the frame border (even-odd → waste holes in keep ring).
    for cx, cy, r in ((20, 20, 5), (100, 16, 6), (180, 20, 5),
                      (20, 70, 5), (100, 74, 6), (180, 70, 5)):
        p.addPath(_circle_path(cx, cy, r))
    p.addPath(_quoted_blocks())
    # Shift quoted blocks into the frame counter (they already start near 8,16).
    return p


def test_seg_spans_pair_rejects_same_body_stub():
    """A cut with both ends on one island is not a two-body seal."""
    a = _rect_path(0, 0, 10, 40)
    b = _rect_path(20, 0, 10, 40)
    # Across the gap: spans both.
    assert weeds_mod._seg_spans_pair((9.5, 20.0, 20.5, 20.0), a, b)
    # Under one body only: stub.
    assert not weeds_mod._seg_spans_pair((0.5, 41.0, 9.5, 41.0), a, b)


def test_frame_peninsula_chain_seals_bottom_wrap():
    """Consecutive stems + hanging mark: bottom necks detach frame peninsulas."""
    keep = _stem_comma_stem_t()
    weed = island_hop_weeds(keep, padding=[10, 10, 10, 10], collar=4.0)
    keep_fill = even_odd_keep_fill(keep)
    # Comma (x~22-28) → second stem (x~40-46) near bottoms (y~40-48).
    comma_i = _alley_gap_seals(
        weed, keep_fill, 20.0, 48.0, 38.0, 50.0, min_len=4.0)
    assert comma_i, "missing comma→stem frame-peninsula seal: %s" % (
        _line_segments(weed),)
    # Second stem → t near bottoms.
    i_t = _alley_gap_seals(
        weed, keep_fill, 44.0, 58.0, 38.0, 50.0, min_len=3.0)
    assert i_t, "missing stem→t frame-peninsula seal"
    assert _residual_traps_for(keep, weed=weed) == []


def test_multi_island_opens_collar_frame_once():
    """Peel frame around a word cluster gets a keep→frame opening."""
    keep = _letters_hi()
    pad = [10, 10, 10, 10]
    weed = island_hop_weeds(keep, padding=pad, collar=4.0)
    bodies = list_closed_subpaths(keep)
    delta = min(weeds_mod.DEFAULT_FRAME_CLEARANCE, min(pad) - 2.0)
    rings = weeds_mod._cluster_offset_rings(bodies, delta)
    assert rings, "expected a cluster peel-frame ring"
    assert weeds_mod._has_keep_to_collar_channel(
        weed, bodies, rings, DEFAULT_CHANNEL_STANDOFF), (
        "multi-island cluster missing one frame-opening channel")


def test_quoted_in_frame_no_residual_traps():
    """Quoted geometric blocks inside a hollow keep frame peel cleanly."""
    p = QPainterPath()
    p.addRect(QRectF(0, 0, 200, 90))
    p.addRect(QRectF(8, 8, 184, 74))
    p.addPath(_quoted_blocks())
    assert _residual_traps_for(p, padding=[12.0, 12.0, 12.0, 12.0]) == []


def test_quoted_frame_with_holes_auto_smoke():
    """Punched frame + quoted blocks: auto runs, connected ends, low in-keep."""
    keep = _quoted_in_frame_with_holes()
    pad = [12.0, 12.0, 12.0, 12.0]
    weed = island_hop_weeds(keep, padding=pad, collar=4.0)
    assert not weed.isEmpty()
    keep_fill = even_odd_keep_fill(keep)
    work = padded_work_rect(keep, pad)
    st = weed_sample_stats(weed, keep_fill=keep_fill, work_rect=work, step=1.0)
    assert st['outside_work'] == 0
    assert st['in_keep_frac'] < _IN_KEEP_BUDGET
    cleaned = weeds_mod._require_connected_ends(weed, keep, tol=1.5, work=work)
    assert cleaned.elementCount() > 0

def test_corridor_seals_do_not_emit_same_body_stubs():
    """H–i style alley must not leave a keep-to-keep stub on one stem only."""
    keep = QPainterPath()
    keep.addPath(_rect_path(0, 0, 20, 40))   # H-ish block
    keep.addPath(_rect_path(28, 8, 6, 32))   # i stem
    weed = island_hop_weeds(keep, padding=[10, 10, 10, 10], collar=4.0)
    bodies = list_closed_subpaths(keep)
    a, b = bodies[0], bodies[1]
    for x0, y0, x1, y1 in _line_segments(weed):
        if math.hypot(x1 - x0, y1 - y0) > 10.0:
            continue
        if weeds_mod._point_near_path(x0, y0, a, 2.0) and weeds_mod._point_near_path(
                x1, y1, a, 2.0):
            if not weeds_mod._point_near_path(x0, y0, b, 2.0) and not (
                    weeds_mod._point_near_path(x1, y1, b, 2.0)):
                # Allow pocket seals wholly on one body (serif / bay).
                # Flag only near the alley bottom where the bad stub lived.
                my = 0.5 * (y0 + y1)
                if my >= a.boundingRect().bottom() - 2.0:
                    raise AssertionError(
                        "same-body stub under stem: %s" % ((x0, y0, x1, y1),))


# --- C9 G0: shared cut-geometry helpers (synthetic) ---


def test_included_angle_square_vs_tangent():
    """α ≈ 90° on a square join; near-tangent weed on a smooth edge ≈ 0°."""
    rect = _rect_path(0, 0, 40, 30)
    # Mid-bottom edge, weed straight down (outward) → square to horizontal edge.
    mid = QPointF(20.0, 30.0)
    a_sq = _included_angle_deg(mid, (0.0, 1.0), rect)
    assert a_sq is not None
    assert abs(a_sq - 90.0) < 1.0
    # Same point, weed along the edge → tangent.
    a_tan = _included_angle_deg(mid, (1.0, 0.0), rect)
    assert a_tan is not None
    assert a_tan < 5.0
    # Circle-ish: radial weed at a sample ≈ square; tangential ≈ 0.
    circ = _circle_path(50, 50, 20)
    rim = QPointF(70.0, 50.0)
    a_rad = _included_angle_deg(rim, (1.0, 0.0), circ)
    a_tg = _included_angle_deg(rim, (0.0, 1.0), circ)
    assert a_rad is not None and a_tg is not None
    assert a_rad > 70.0
    assert a_tg < 25.0


def test_convex_corners_rectangle():
    """Rectangle yields four sharp corners; mid-edge points are absent."""
    rect = _rect_path(10, 20, 30, 40)
    corners = _convex_corners(rect, min_turn=40)
    assert len(corners) == 4
    expected = {(10.0, 20.0), (40.0, 20.0), (40.0, 60.0), (10.0, 60.0)}
    got = {(round(c.x(), 6), round(c.y(), 6)) for c in corners}
    assert got == expected
    mid = QPointF(25.0, 20.0)
    assert all(math.hypot(c.x() - mid.x(), c.y() - mid.y()) > 1.0
               for c in corners)
    frame = _keep_frame_at(rect, mid)
    assert frame is not None and frame.vertex is None


def test_peel_axis_side_by_side_rects():
    """Two side-by-side rects: n̂ across the gap, ĉ along the alley."""
    a = _rect_path(0, 0, 20, 50)
    b = _rect_path(28, 0, 20, 50)
    c_hat, n_hat = _peel_axis(a, b)
    # Across ≈ ±X; along ≈ ±Y.
    assert abs(n_hat[0]) > 0.9 and abs(n_hat[1]) < 0.1
    assert abs(c_hat[1]) > 0.9 and abs(c_hat[0]) < 0.1
    assert abs(c_hat[0] * n_hat[0] + c_hat[1] * n_hat[1]) < 1e-9
    # Peel dir along corridor toward far end from a bottom mouth.
    mouth = QPointF(24.0, 50.0)
    p = QPointF(24.0, 25.0)
    d = _peel_dir_at(p, {'kind': 'corridor', 'c_hat': c_hat, 'mouth': mouth})
    assert d is not None
    # From bottom mouth toward mid → opposite +ĉ if ĉ points +Y.
    assert d[1] * c_hat[1] < 0.0 or abs(d[1]) > 0.9


def test_vertex_weed_degree_counts_endpoints():
    """Empty weed → 0; two seal ends at a vertex → 2."""
    v = QPointF(10.0, 10.0)
    empty = QPainterPath()
    assert _vertex_weed_degree(v, empty) == 0
    assert _vertex_weed_degree(v, None) == 0
    weed = QPainterPath()
    weed.moveTo(10.0, 10.0)
    weed.lineTo(20.0, 10.0)
    weed.moveTo(10.0, 10.0)
    weed.lineTo(10.0, 20.0)
    assert _vertex_weed_degree(v, weed, r=1.2) == 2
    assert _vertex_weed_degree(QPointF(50.0, 50.0), weed, r=1.2) == 0


# --- Bay peel-wall: corner → opposite coast (generic) ---


def _tangent_bay_with_bar():
    """Undercut bowl whose hull mouth chord is tangent (α→0) + nearby bar."""
    # Mouth on y=0 is collinear with the top flanges → α=0 at the lips.
    body = _poly_path((
        (0, 0), (22, 0),
        (22, 8), (12, 20), (12, 40), (48, 40), (48, 20), (38, 8), (38, 0),
        (60, 0), (60, 52), (0, 52),
    ))
    keep = QPainterPath()
    keep.addPath(body)
    keep.addPath(_rect_path(24, -14, 12, 10))
    return keep


def _rect_pocket_body():
    """Rect keep with a deep top U: mouth 16, depth 16 — clear bay corners."""
    return _deep_smooth_bay_body()


def test_bay_corner_to_opposite_coast_one_seal():
    """Constructed U-bay: one dam from a run corner toward the opposite coast."""
    body = _rect_pocket_body()
    mouths = _hull_bay_mouths(body, min_depth=1.0, min_width=4.0)
    assert mouths, "fixture needs a hull bay"
    left, right, deep, run = mouths[0]
    assert _bay_should_seal(left, right, deep, run)
    primary = _closest_bay_mouth_corner(body, left, right, run)
    assert primary is not None
    # >180° weed-side corner near the mouth (lip or bay-facing), not an outer tip.
    d_mouth = _point_seg_dist(
        primary.x(), primary.y(), left.x(), left.y(), right.x(), right.y())
    assert d_mouth <= 2.5, "primary should sit at the mouth, d=%s" % d_mouth

    keep_fill = even_odd_keep_fill(body)
    work = padded_work_rect(body, [8.0, 8.0, 8.0, 8.0])
    pockets = _body_pocket_seals(
        body, keep_fill, work, DEFAULT_CHANNEL_STANDOFF, 2.0, None)
    segs = _line_segments(pockets)
    assert len(segs) == 1, "exactly one dam per mouth, got %s" % segs
    x0, y0, x1, y1 = segs[0]
    # Must cross toward the opposite shore (not graze one wall).
    mid_x = 0.5 * (x0 + x1)
    assert left.x() + 2.0 < mid_x < right.x() - 2.0, (
        "dam should span the bay, got %s" % segs[0])
    # Created peel angles (D012) — not graze-α vs a collinear flange edge.
    ln = math.hypot(x1 - x0, y1 - y0) or 1.0
    ends = (
        (QPointF(x0, y0), (x1 - x0) / ln, (y1 - y0) / ln),
        (QPointF(x1, y1), (x0 - x1) / ln, (y0 - y1) / ln),
    )
    far_ok = False
    for p, wx, wy in ends:
        angles = _created_peel_angles(p, (wx, wy), body)
        if angles is not None and min(angles) >= _ALPHA_MIN_PEEL - 1e-6:
            far_ok = True
    assert far_ok, "coast/wall end should meet α_min=%s" % _ALPHA_MIN_PEEL


def test_bay_mouth_corners_preferred_over_inset_lip():
    """U/C bay: convex-keep mouth corners seal the mouth, not a mid-lip inset."""
    for body in (_deep_smooth_bay_body(), _deep_smooth_c_bay_body()):
        mouths = _hull_bay_mouths(body, min_depth=1.0, min_width=4.0)
        assert mouths, "fixture needs a hull bay"
        left, right, deep, run = mouths[0]
        assert _bay_should_seal(left, right, deep, run)
        keep_fill = even_odd_keep_fill(body)
        work = padded_work_rect(body, [8.0, 8.0, 8.0, 8.0])
        pockets = _body_pocket_seals(
            body, keep_fill, work, DEFAULT_CHANNEL_STANDOFF, 2.0, None)
        segs = _line_segments(pockets)
        assert len(segs) == 1, "exactly one dam per mouth, got %s" % segs
        x0, y0, x1, y1 = segs[0]
        lips = ((left.x(), left.y()), (right.x(), right.y()))

        def _near(a, b, tol=2.5):
            return math.hypot(a[0] - b[0], a[1] - b[1]) <= tol

        ends = ((x0, y0), (x1, y1))
        cornered = (
            (_near(ends[0], lips[0]) and _near(ends[1], lips[1]))
            or (_near(ends[0], lips[1]) and _near(ends[1], lips[0])))
        assert cornered, (
            "expected mouth-corner chord, got %s vs lips %s" % (segs[0], lips))
        mx, my = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
        d_mid = _point_seg_dist(
            mx, my, left.x(), left.y(), right.x(), right.y())
        assert d_mid < 2.0, (
            "seal should sit on the mouth, not ≥2 mm inset: %s d=%s" % (
                segs[0], d_mid))


def test_uneven_tops_mouth_seal_stays_corner_corner():
    """t-bar (y=28) ↔ taller quote (y=26): diagonal corners, not y=26.5 mid-edge.

    Axis-hit slides + loose corner tol used to rank a horizontal mid-edge
    (false class-0 within 1.5 of a vertex) over the real corner pair.
    """
    tbar = _rect_path(88.0, 28.0, 16.0, 8.0)
    quote = _rect_path(120.0, 26.0, 4.0, 16.0)
    keep = QPainterPath()
    keep.addPath(tbar)
    keep.addPath(quote)
    keep_fill = even_odd_keep_fill(keep)
    work = padded_work_rect(keep, [8.0, 8.0, 8.0, 8.0])
    seg = weeds_mod._mouth_seal(
        tbar, quote, QPointF(104.0, 28.0), QPointF(120.0, 26.0),
        1.0, 0.0, 32.0, DEFAULT_CHANNEL_STANDOFF, keep_fill, work, 2.0, None)
    assert seg is not None
    ends = ((seg[0], seg[1]), (seg[2], seg[3]))
    corners = {(104.0, 28.0), (120.0, 26.0)}

    def _near(a, b, tol=1e-6):
        return math.hypot(a[0] - b[0], a[1] - b[1]) <= tol

    assert (
        (_near(ends[0], (104.0, 28.0)) and _near(ends[1], (120.0, 26.0)))
        or (_near(ends[0], (120.0, 26.0)) and _near(ends[1], (104.0, 28.0)))
    ), "expected corner–corner, got %s" % (seg,)
    # Mid-edge impostor must not win class-0.
    assert not weeds_mod._near_waste_reflex_corner(
        tbar, QPointF(104.0, 26.5))
    assert weeds_mod._endpoint_class(
        QPointF(104.0, 26.5), tbar, path_b=quote) == weeds_mod._EP_EDGE


def test_bay_collinear_flange_mouth_is_true_corner_chord():
    """H-like U: mouth chord collinear with flanges still lands on both corners.

    ``_included_angle_deg`` reports α=0 on that chord (edge continuation);
    created peel angles are (90°, 180°) — legal under D012. Regression for
    sliding ~1 unit down the opposite stem.
    """
    body = _deep_smooth_bay_body()
    mouths = _hull_bay_mouths(body, min_depth=1.0, min_width=4.0)
    assert mouths, "fixture needs a hull bay"
    left, right, deep, run = mouths[0]
    assert _bay_should_seal(left, right, deep, run)
    keep_fill = even_odd_keep_fill(body)
    work = padded_work_rect(body, [8.0, 8.0, 8.0, 8.0])
    pockets = _body_pocket_seals(
        body, keep_fill, work, DEFAULT_CHANNEL_STANDOFF, 2.0, None)
    segs = _line_segments(pockets)
    assert len(segs) == 1, "exactly one dam, got %s" % segs
    x0, y0, x1, y1 = segs[0]
    lips = ((left.x(), left.y()), (right.x(), right.y()))
    # Exact corner–corner (no fuse pullback).
    tol = 1e-6

    def _near(a, b):
        return math.hypot(a[0] - b[0], a[1] - b[1]) <= tol

    ends = ((x0, y0), (x1, y1))
    cornered = (
        (_near(ends[0], lips[0]) and _near(ends[1], lips[1]))
        or (_near(ends[0], lips[1]) and _near(ends[1], lips[0])))
    assert cornered, (
        "expected exact corner–corner, got %s vs lips %s" % (
            segs[0], lips))
    d_mid = _point_seg_dist(
        0.5 * (x0 + x1), 0.5 * (y0 + y1),
        left.x(), left.y(), right.x(), right.y())
    assert d_mid < 1e-6, (
        "chord must lie on the mouth line, not inset: %s d=%s" % (
            segs[0], d_mid))


def test_bay_mouth_already_sealed_blocks_second_pass():
    """Multi-pass guard: an existing side↔side dam skips another seal."""
    body = _rect_pocket_body()
    mouths = _hull_bay_mouths(body, min_depth=1.0, min_width=4.0)
    left, right, deep, run = mouths[0]
    keep_fill = even_odd_keep_fill(body)
    work = padded_work_rect(body, [8.0, 8.0, 8.0, 8.0])
    first = _body_pocket_seals(
        body, keep_fill, work, DEFAULT_CHANNEL_STANDOFF, 2.0, None)
    assert _line_segments(first), "expected an initial dam"
    assert _bay_mouth_already_sealed(first, left, right, run=run)
    second = _body_pocket_seals(
        body, keep_fill, work, DEFAULT_CHANNEL_STANDOFF, 2.0, None,
        against=first)
    assert _line_segments(second) == [], "must not fan a second dam"


def test_tangent_bay_seal_has_hard_alpha():
    """Tangent hull mouth reroutes via corner→coast (far end α ≥ peel min)."""
    keep = _tangent_bay_with_bar()
    bodies = list_closed_subpaths(keep)
    body = max(bodies, key=lambda p: p.boundingRect().height()
               * p.boundingRect().width())
    mouths = _hull_bay_mouths(body, min_depth=1.0, min_width=4.0)
    assert mouths, "fixture needs a hull bay mouth"
    left, right, deep, run = mouths[0]
    mw = math.hypot(right.x() - left.x(), right.y() - left.y()) or 1.0
    a_mouth = min(
        _included_angle_deg(
            left,
            ((right.x() - left.x()) / mw, (right.y() - left.y()) / mw),
            body) or 0.0,
        _included_angle_deg(
            right,
            ((left.x() - right.x()) / mw, (left.y() - right.y()) / mw),
            body) or 0.0,
    )
    assert a_mouth < _ALPHA_HARD, (
        "fixture mouth should be near-tangent, got α=%s" % a_mouth)

    pad = [12.0, 12.0, 12.0, 12.0]
    keep_fill = even_odd_keep_fill(keep)
    work = padded_work_rect(keep, pad)
    pockets = _body_pocket_seals(
        body, keep_fill, work, DEFAULT_CHANNEL_STANDOFF, 2.0, None)
    segs = _line_segments(pockets)
    assert segs, "expected a pocket seal on the tangent bay"
    assert len(segs) == 1, "one dam only, got %s" % segs
    x0, y0, x1, y1 = segs[0]
    ln = math.hypot(x1 - x0, y1 - y0) or 1.0
    a0 = _included_angle_deg(
        QPointF(x0, y0), ((x1 - x0) / ln, (y1 - y0) / ln), body)
    a1 = _included_angle_deg(
        QPointF(x1, y1), ((x0 - x1) / ln, (y0 - y1) / ln), body)
    assert a0 is not None and a1 is not None
    # At least one end (coast/wall) meets peel α; corner primary may be tiny.
    assert max(a0, a1) >= _ALPHA_MIN_PEEL - 1e-6, (
        "far-end α below peel min: %s α=(%s,%s)" % (
            (x0, y0, x1, y1), a0, a1))
    assert min(a0, a1) >= 0.0

    weed = island_hop_weeds(keep, padding=pad, collar=4.0)
    assert _residual_traps_for(keep, weed=weed, padding=pad) == []


# --- C9 G2: edge-lift + peel J / widened corridor endpoints ---


def _edge_lift_stick_keep():
    """Round-ish left + vertical rect right; core mid-band hits mid-stick."""
    keep = QPainterPath()
    keep.addPath(_circle_path(40.0, 40.0, 20.0))
    keep.addPath(_rect_path(66.0, 22.0, 10.0, 36.0))
    return keep


def test_edge_lift_stick_seals_at_alley_corners():
    """Plan #2: corridor seals land on rect alley corners, not mid-edge."""
    keep = _edge_lift_stick_keep()
    bodies = list_closed_subpaths(keep)
    assert len(bodies) == 2
    a, b = bodies[0], bodies[1]
    if a.boundingRect().center().x() > b.boundingRect().center().x():
        a, b = b, a
    assert _is_corridor_pair(a, b)
    core = _channel_core(a, b)
    assert core is not None
    br = b.boundingRect()
    mid0 = br.top() + 0.25 * br.height()
    mid1 = br.top() + 0.75 * br.height()
    # Precondition: thin core mouths sit in the mid 50% of the stick edge.
    assert mid0 < core.pb0.y() < mid1 and mid0 < core.pb1.y() < mid1

    alley_corners = [
        c for c in _convex_corners(b, min_turn=40)
        if abs(c.x() - br.left()) <= 0.75
    ]
    assert len(alley_corners) == 2

    keep_fill = even_odd_keep_fill(keep)
    work = padded_work_rect(keep, [10.0, 10.0, 10.0, 10.0])
    segs = _seal_corridor_pair(
        a, b, keep_fill, work, DEFAULT_CHANNEL_STANDOFF, 2.0, None)
    assert len(segs) == 2, "two retargeted end seals, not one merge"

    rect_ends = []
    for x0, y0, x1, y1 in segs:
        for x, y in ((x0, y0), (x1, y1)):
            if (br.left() - 2.0 <= x <= br.right() + 2.0
                    and br.top() - 2.0 <= y <= br.bottom() + 2.0):
                rect_ends.append((x, y))
    assert len(rect_ends) == 2
    for x, y in rect_ends:
        d_corner = min(
            math.hypot(x - c.x(), y - c.y()) for c in alley_corners)
        assert d_corner <= 1.5, (
            "seal end %s should be within 1.5 mm of an alley corner, got %s"
            % ((x, y), d_corner))
        assert not (mid0 < y < mid1), (
            "seal end %s must not sit in mid 50%% of the stick edge"
            % ((x, y),))

    pad = [10.0, 10.0, 10.0, 10.0]
    weed = island_hop_weeds(keep, padding=pad, collar=4.0)
    assert _residual_traps_for(keep, weed=weed, padding=pad) == []


# --- C9 G3: graze ≠ anchor + parallel hug drop ---


def test_parallel_hug_dropped_radial_kept():
    """Plan #4: 1 mm inset parallel of a long keep side drops; radial stays."""
    keep = _rect_path(0.0, 0.0, 40.0, 80.0)
    # Long hug along the left edge (x=0), inset 1 mm into waste (x=-1).
    hug = (-1.0, 8.0, -1.0, 72.0)
    assert weeds_mod._is_parallel_hug(hug, keep, 2.0)
    weed = QPainterPath()
    weed.moveTo(hug[0], hug[1])
    weed.lineTo(hug[2], hug[3])
    # Radial keep→collar stand-in: square join from left edge into waste.
    radial = (0.0, 40.0, -6.0, 40.0)
    weed.moveTo(radial[0], radial[1])
    weed.lineTo(radial[2], radial[3])
    a_rad = _included_angle_deg(
        QPointF(radial[0], radial[1]), (-1.0, 0.0), keep)
    assert a_rad is not None and a_rad >= 60.0
    assert not weeds_mod._is_parallel_hug(radial, keep, 2.0)

    cleaned = weeds_mod._drop_parallel_hugs(weed, keep, 2.0)
    segs = _line_segments(cleaned)
    assert len(segs) == 1, "hug should drop, radial remain: %s" % segs
    x0, y0, x1, y1 = segs[0]
    assert abs(y0 - 40.0) < 0.5 and abs(y1 - 40.0) < 0.5


def test_graze_not_anchor_square_join_kept():
    """Plan #5: side graze removed by connected-ends; exact square join kept."""
    keep = _rect_path(0.0, 0.0, 40.0, 80.0)
    # Outer end of the radial meets the work frame (collar stand-in).
    work = QRectF(-6.0, -4.0, 52.0, 88.0)
    weed = QPainterPath()
    # Graze: parallel to left edge, both ends within 1.5 mm sideways, α→0.
    weed.moveTo(-1.0, 10.0)
    weed.lineTo(-1.0, 50.0)
    # True meet: exact square join keep → work edge.
    weed.moveTo(0.0, 40.0)
    weed.lineTo(work.left(), 40.0)

    a_graze = _included_angle_deg(QPointF(-1.0, 10.0), (0.0, 1.0), keep)
    assert a_graze is not None and a_graze < _ALPHA_HARD
    a_sq = _included_angle_deg(QPointF(0.0, 40.0), (-1.0, 0.0), keep)
    assert a_sq is not None and a_sq >= 60.0

    cleaned = weeds_mod._require_connected_ends(weed, keep, tol=1.5, work=work)
    segs = _line_segments(cleaned)
    assert len(segs) == 1, "graze should drop, square join remain: %s" % segs
    x0, y0, x1, y1 = segs[0]
    assert min(x0, x1) <= 0.05
    assert abs(y0 - 40.0) < 0.5 and abs(y1 - 40.0) < 0.5


# --- C9 G4: sliver hard drop + cheap necessity ---


def test_sliver_second_seal_dropped():
    """Plan #6: stem + 6×12 hanging; second seal closing <8 mm² is dropped."""
    keep = QPainterPath()
    keep.addPath(_rect_path(0.0, 20.0, 10.0, 50.0))
    keep.addPath(_rect_path(14.0, 20.0, 6.0, 12.0))
    good = (10.0, 30.0, 14.0, 30.0)
    sliver = (10.0, 31.2, 14.0, 31.2)

    weed = QPainterPath()
    weed.moveTo(good[0], good[1])
    weed.lineTo(good[2], good[3])
    assert weeds_mod._is_sliver_seal(sliver, weed, keep)
    area, alt, kappa = weeds_mod._sliver_triangle_metrics(sliver, good)
    assert area < weeds_mod._A_SLIVER
    assert alt < weeds_mod._H_SLIVER
    assert kappa < 2.0

    weed.moveTo(sliver[0], sliver[1])
    weed.lineTo(sliver[2], sliver[3])
    cleaned = weeds_mod._drop_slivers_and_needless(weed, keep)
    segs = _line_segments(cleaned)
    assert len(segs) == 1, "sliver should drop, good gutter remain: %s" % segs
    assert abs(segs[0][1] - 30.0) < 0.5 and abs(segs[0][3] - 30.0) < 0.5


def test_necessity_extra_parallel_dropped():
    """Plan #8: sealed corridor; near extra with Δn=0 drops; far mouth stays."""
    keep = QPainterPath()
    keep.addPath(_rect_path(0.0, 0.0, 8.0, 40.0))
    keep.addPath(_rect_path(16.0, 0.0, 8.0, 40.0))
    good = (8.0, 20.0, 16.0, 20.0)
    near = (8.0, 22.0, 16.0, 22.0)
    far = (8.0, 1.0, 16.0, 1.0)

    weed = QPainterPath()
    weed.moveTo(good[0], good[1])
    weed.lineTo(good[2], good[3])
    assert weeds_mod._is_needless_optional_seal(near, weed, keep)
    assert not weeds_mod._is_needless_optional_seal(far, weed, keep), (
        "far alley mouth must stay (both mouths on long corridor)")

    weed.moveTo(near[0], near[1])
    weed.lineTo(near[2], near[3])
    weed.moveTo(far[0], far[1])
    weed.lineTo(far[2], far[3])
    cleaned = weeds_mod._drop_slivers_and_needless(weed, keep)
    segs = _line_segments(cleaned)
    assert len(segs) == 2, "near extra drops; good + far remain: %s" % segs
    mids = sorted(0.5 * (s[1] + s[3]) for s in segs)
    assert abs(mids[0] - 1.0) < 0.5 and abs(mids[1] - 20.0) < 0.5

    # Frame-open (keep→collar, no span pair) is never a necessity drop.
    frame_open = (0.0, 20.0, -6.0, 20.0)
    assert not weeds_mod._is_needless_optional_seal(frame_open, weed, keep)


# --- D012: body clearance, α floor, peel-frame-first, ranking ---


def test_body_clearance_rejects_mid_hug_keeps_short_span():
    """Long mid-seg near keep fails; short keep-to-keep has no interior."""
    keep = _rect_path(0.0, 0.0, 40.0, 80.0)
    hug = (-2.0, 10.0, -2.0, 70.0)
    assert not weeds_mod._seg_body_clearance_ok(hug, keep, clearance=5.0)
    short = (40.0, 40.0, 48.0, 40.0)
    assert weeds_mod._seg_body_clearance_ok(short, keep, clearance=5.0)
    square = (0.0, 40.0, -12.0, 40.0)
    assert weeds_mod._seg_body_clearance_ok(square, keep, clearance=5.0)


def test_alpha_floor_rejects_graze_keeps_square():
    keep = _rect_path(0.0, 0.0, 40.0, 80.0)
    graze = (-1.0, 10.0, -1.0, 50.0)
    assert not weeds_mod._seg_alpha_ok(graze, keep, 30.0)
    square = (0.0, 40.0, -10.0, 40.0)
    assert weeds_mod._seg_alpha_ok(square, keep, 30.0)


def test_peel_rank_cost_prefers_closer_to_180():
    """Square outranks shallow: E = 180 − min created (graze is not 180°)."""
    keep = _rect_path(0.0, 0.0, 40.0, 80.0)
    other = _rect_path(60.0, 0.0, 40.0, 80.0)
    square = (40.0, 40.0, 60.0, 40.0)
    shallow = (40.0, 10.0, 60.0, 25.0)
    a_sq = _included_angle_deg(QPointF(40.0, 40.0), (1.0, 0.0), keep)
    a_sh = _included_angle_deg(QPointF(40.0, 10.0), (0.8, 0.6), keep)
    assert a_sq is not None and a_sh is not None
    assert a_sh < a_sq
    e_sq = weeds_mod._created_angle_error(
        QPointF(40.0, 40.0), (1.0, 0.0), keep)
    e_sh = weeds_mod._created_angle_error(
        QPointF(40.0, 10.0), (0.8, 0.6), keep)
    assert e_sq < e_sh
    c_sq = weeds_mod._peel_rank_cost(square, keep, other)
    c_sh = weeds_mod._peel_rank_cost(shallow, keep, other)
    assert c_sq < c_sh
    picked = weeds_mod._pick_ranked_seg([square, shallow], keep, other)
    assert picked == square


def test_forced_ok_rejects_clearance_failure():
    """α-ok but mid-body too close to another island is not a last resort."""
    keep = QPainterPath()
    keep.addPath(_rect_path(0.0, 0.0, 20.0, 40.0))
    keep.addPath(_rect_path(40.0, 0.0, 20.0, 40.0))
    keep.addPath(_rect_path(22.0, 20.6, 16.0, 3.0))
    span = (20.0, 20.0, 40.0, 20.0)
    rules = weeds_mod._cut_rules()
    assert weeds_mod._seg_alpha_ok(span, keep, 30.0)
    assert not weeds_mod._seg_body_clearance_ok(span, keep, clearance=5.0)
    assert not weeds_mod._seg_emit_ok(span, keep, None, rules)
    assert not weeds_mod._seg_forced_ok(span, keep, None, rules)


def test_no_double_collar_when_design_already_bounds():
    """Tight design hole: no second closed rail around the inner keep."""
    keep = QPainterPath()
    keep.addRect(QRectF(0.0, 0.0, 100.0, 70.0))
    keep.addRect(QRectF(8.0, 8.0, 84.0, 54.0))
    keep.addRect(QRectF(12.0, 12.0, 76.0, 46.0))
    pad = [10.0, 10.0, 10.0, 10.0]
    weed = island_hop_weeds(
        keep, padding=pad, collar=4.0, frame_clearance=20.0)
    hole = QPainterPath()
    hole.addRect(QRectF(8.0, 8.0, 84.0, 54.0))
    inner = QPainterPath()
    inner.addRect(QRectF(12.0, 12.0, 76.0, 46.0))
    band = 0
    for p in sample_points_on_path(weed, step=1.0):
        if not hole.contains(p) or inner.contains(p):
            continue
        band += 1
    assert band <= 8, "double collar inside design frame: %s samples" % band


def test_quoted_in_frame_no_interior_corner_scrap():
    """No peel-frame clip scrap chord across a design-frame interior corner."""
    p = QPainterPath()
    p.addRect(QRectF(0, 0, 200, 100))
    p.addRect(QRectF(8, 8, 184, 84))
    p.addPath(_quoted_blocks())
    pad = [20.0, 20.0, 20.0, 20.0]
    weed = island_hop_weeds(p, padding=pad, collar=4.0, frame_clearance=20.0)
    scraps = []
    for seg in weeds_mod._iter_line_segs(weed):
        x0, y0, x1, y1 = seg
        on_right = abs(x0 - 192.0) < 1.0 or abs(x1 - 192.0) < 1.0
        on_bot = abs(y0 - 92.0) < 1.0 or abs(y1 - 92.0) < 1.0
        on_left = abs(x0 - 8.0) < 1.0 or abs(x1 - 8.0) < 1.0
        on_top = abs(y0 - 8.0) < 1.0 or abs(y1 - 8.0) < 1.0
        corner = (
            (on_right and on_bot) or (on_right and on_top)
            or (on_left and on_bot) or (on_left and on_top))
        if not corner:
            continue
        mx = 0.5 * (x0 + x1)
        my = 0.5 * (y0 + y1)
        if 8.0 < mx < 192.0 and 8.0 < my < 92.0:
            scraps.append(seg)
    assert not scraps, "interior frame-corner scrap: %s" % scraps


def test_peel_frame_opens_at_full_clearance():
    """Keep→peel-frame radial still emits when clearance gap exceeds 12."""
    keep = _rect_path(0.0, 0.0, 80.0, 50.0)
    pad = [20.0, 20.0, 20.0, 20.0]
    weed = island_hop_weeds(
        keep, padding=pad, collar=4.0, frame_clearance=20.0)
    bodies = list_closed_subpaths(keep)
    delta = min(20.0, min(pad) - 2.0)
    rings = weeds_mod._cluster_offset_rings(bodies, delta)
    assert rings
    assert weeds_mod._has_keep_to_collar_channel(
        weed, bodies, rings, DEFAULT_CHANNEL_STANDOFF), (
        "full-clearance peel frame missing corridor opening")


def test_peel_rail_stays_continuous_at_channel():
    """Auto peel rail stays continuous; keep→frame radial opens the collar."""
    keep = _rect_path(0.0, 0.0, 80.0, 50.0)
    pad = [20.0, 20.0, 20.0, 20.0]
    weed = island_hop_weeds(
        keep, padding=pad, collar=4.0, frame_clearance=20.0)
    bodies = list_closed_subpaths(keep)
    delta = min(20.0, min(pad) - 2.0)
    rings = weeds_mod._cluster_offset_rings(bodies, delta)
    lands = weeds_mod._keep_to_collar_landings(
        weed, bodies, rings, DEFAULT_CHANNEL_STANDOFF)
    assert lands, "missing keep→frame channel landing"
    lx, ly = lands[0]
    rail_through = 0
    for seg in weeds_mod._iter_line_segs(weed):
        mx = 0.5 * (seg[0] + seg[2])
        my = 0.5 * (seg[1] + seg[3])
        hit = weeds_mod._nearest_on_rings(mx, my, rings)
        if hit is None or hit[2] > 2.0:
            continue
        # Long rail chords: landing can sit far from the midpoint.
        if weeds_mod._point_seg_dist(lx, ly, *seg) < 1.5:
            rail_through += 1
    assert rail_through >= 1, (
        "peel rail discontinuous at channel landing (%s hits)" % rail_through)


def test_container_cluster_opens_to_wall():
    """Interior design-container cluster gets a keep↔container-wall channel."""
    keep = QPainterPath()
    keep.addRect(QRectF(0.0, 0.0, 200.0, 100.0))
    keep.addRect(QRectF(8.0, 8.0, 184.0, 84.0))
    keep.addPath(_rect_path(60.0, 30.0, 50.0, 40.0))
    pad = [12.0, 12.0, 12.0, 12.0]
    weed = island_hop_weeds(keep, padding=pad, collar=4.0)
    nodes = weeds_mod._nest_closed_paths(list_closed_subpaths(keep))
    groups = weeds_mod._enclosure_groups(nodes, 4.0)
    opened = False
    for cluster, container in groups:
        if container is None or container.isEmpty():
            continue
        rings = weeds_mod._path_to_rings(container)
        assert rings, "expected container outline rings"
        assert weeds_mod._has_keep_to_collar_channel(
            weed, cluster, rings, DEFAULT_CHANNEL_STANDOFF), (
            "container cluster missing keep↔wall corridor")
        opened = True
    assert opened, "expected a container-bound interior cluster"


def test_legacy_frame_mode_stays_closed_box():
    """Legacy frame mode is still a closed padded box (not auto peel)."""
    keep = _rect_path(20.0, 20.0, 60.0, 40.0)
    weed = frame_weeds(keep, padding=[12, 12, 12, 12])
    segs = list(weeds_mod._iter_line_segs(weed))
    # addRect may be one closed subpath or four edges; either way closed box.
    assert not weed.isEmpty()
    br = weed.boundingRect()
    assert abs(br.width() - 84.0) < 0.5 and abs(br.height() - 64.0) < 0.5


def test_keep_fill_svg_d_uses_evenodd_holes():
    """Preview keep-fill polygons need evenodd (same-winding outer+hole)."""
    from weedlib.svg_paths import keep_fill_to_svg_d
    keep = QPainterPath()
    keep.addRect(QRectF(0.0, 0.0, 200.0, 100.0))
    keep.addRect(QRectF(8.0, 8.0, 184.0, 84.0))
    fill = even_odd_keep_fill(keep)
    assert not fill.contains(QPointF(100.0, 50.0))
    d = keep_fill_to_svg_d(fill)
    assert d.count('Z') >= 2
    assert 'M ' in d


def test_peel_frame_placed_in_open_water():
    """Open keep: peel rail sits outside keep, inside work, not on work edge."""
    keep = _rect_path(20.0, 20.0, 60.0, 40.0)
    pad = [12.0, 12.0, 12.0, 12.0]
    weed = island_hop_weeds(
        keep, padding=pad, collar=4.0, frame_clearance=20.0)
    work = padded_work_rect(keep, pad)
    keep_fill = even_odd_keep_fill(keep)
    on_work = 0
    outside_keep = 0
    for p in sample_points_on_path(weed, step=1.0):
        if keep_fill.contains(p):
            continue
        outside_keep += 1
        if (abs(p.x() - work.left()) < 0.6 or abs(p.x() - work.right()) < 0.6
                or abs(p.y() - work.top()) < 0.6
                or abs(p.y() - work.bottom()) < 0.6):
            on_work += 1
    assert outside_keep > 0
    assert on_work == 0, "peel frame sat on the padded work edge"


def test_hug_rejects_mid_body_parallel_outside_ring():
    """Mouth-collinear and long stem-parallel rails are visual hugs."""
    keep = _rect_path(0.0, 0.0, 40.0, 80.0)
    # Along the top edge, just outside: mid-body close and parallel.
    along_top = (2.0, -2.0, 38.0, -2.2)
    assert weeds_mod._is_parallel_hug(along_top, keep, 2.0)
    # Long vertical 1.5 mm off the right wall (quote-stem style).
    long_vert = (41.5, 8.0, 41.5, 72.0)
    assert weeds_mod._is_parallel_hug(long_vert, keep, 2.0)
    radial = (0.0, 40.0, -10.0, 40.0)
    assert not weeds_mod._is_parallel_hug(radial, keep, 2.0)


def test_compact_island_gets_short_square_tie():
    """Small compact keep in water ties short to the nearest letter/frame."""
    keep = QPainterPath()
    keep.addPath(_rect_path(0.0, 20.0, 24.0, 50.0))
    keep.addPath(_rect_path(8.0, 2.0, 10.0, 10.0))
    pad = [12.0, 12.0, 12.0, 12.0]
    weed = island_hop_weeds(keep, padding=pad, collar=4.0)
    keep_fill = even_odd_keep_fill(keep)
    specks = []
    letters = []
    for b in list_closed_subpaths(keep):
        if weeds_mod._is_compact_island(
                b, list_closed_subpaths(keep)):
            specks.append(b)
        else:
            letters.append(b)
    assert specks and letters
    ties = []
    for seg in weeds_mod._iter_line_segs(weed):
        if weeds_mod._seg_spans_pair(seg, specks[0], letters[0], tol=2.5):
            ties.append(seg)
    assert ties, "compact island should get a keep-to-keep tie"
    ln = min(math.hypot(s[2] - s[0], s[3] - s[1]) for s in ties)
    assert ln < 20.0, "tie should be short, got %s" % ties
    # No long rail parallel to the letter stem.
    for seg in weeds_mod._iter_line_segs(weed):
        ln = math.hypot(seg[2] - seg[0], seg[3] - seg[1])
        if ln < 20.0:
            continue
        assert not weeds_mod._is_parallel_hug(seg, keep_fill, 2.0), (
            "long hug survived: %s" % (seg,))


def test_thin_tick_islands_are_compact_not_stub_sources():
    """Small thin ticks (quote-like) count as compact — square ties, no leaps."""
    keep = QPainterPath()
    keep.addPath(_rect_path(0.0, 10.0, 20.0, 40.0))
    keep.addPath(_rect_path(28.0, 12.0, 3.4, 9.3))
    keep.addPath(_rect_path(34.6, 12.0, 3.4, 9.3))
    bodies = list_closed_subpaths(keep)
    ticks = [b for b in bodies if weeds_mod._is_compact_island(b, bodies)
             and b.boundingRect().width() < 5.0]
    assert len(ticks) == 2, "both quote ticks should be compact"
    weed = island_hop_weeds(keep, padding=[10.0, 10.0, 10.0, 10.0], collar=4.0)
    # No long free-looking leap from a tick across open water.
    for seg in weeds_mod._iter_line_segs(weed):
        ln = math.hypot(seg[2] - seg[0], seg[3] - seg[1])
        if ln <= 10.0:
            continue
        on_tick = any(
            weeds_mod._point_near_path(seg[0], seg[1], t, tol=2.0)
            or weeds_mod._point_near_path(seg[2], seg[3], t, tol=2.0)
            for t in ticks)
        assert not on_tick, "thin tick still has long leap: %s" % (seg,)


def test_horizontal_pocket_mouth_emits_chord():
    """When a bay mouth is horizontal, the seal is the lip–lip chord."""
    body = _deep_smooth_bay_body()
    keep_fill = even_odd_keep_fill(body)
    work = padded_work_rect(body, [8.0, 8.0, 8.0, 8.0])
    pockets = _body_pocket_seals(
        body, keep_fill, work, DEFAULT_CHANNEL_STANDOFF, 2.0, None)
    segs = _line_segments(pockets)
    assert len(segs) == 1, segs
    x0, y0, x1, y1 = segs[0]
    assert abs(y0 - y1) < 0.5, "mouth chord should be horizontal: %s" % (segs[0],)
    mouths = _hull_bay_mouths(body, min_depth=1.0, min_width=4.0)
    left, right, _d, _r = mouths[0]
    ends = ((x0, y0), (x1, y1))
    lips = ((left.x(), left.y()), (right.x(), right.y()))

    def near(a, b, tol=1.5):
        return math.hypot(a[0] - b[0], a[1] - b[1]) <= tol

    assert (
        (near(ends[0], lips[0]) and near(ends[1], lips[1]))
        or (near(ends[0], lips[1]) and near(ends[1], lips[0]))
    ), "expected lip–lip chord, got %s vs %s" % (segs[0], lips)


def test_bay_seal_anchors_at_mouth_corner_vertex():
    """Primary mouth corner is an exact emit end (not a mid-edge walk-in)."""
    body = _deep_smooth_c_bay_body()
    mouths = _hull_bay_mouths(body, min_depth=1.0, min_width=4.0)
    assert mouths
    left, right, deep, run = mouths[0]
    primary = _closest_bay_mouth_corner(body, left, right, run)
    assert primary is not None
    keep_fill = even_odd_keep_fill(body)
    work = padded_work_rect(body, [8.0, 8.0, 8.0, 8.0])
    pockets = _body_pocket_seals(
        body, keep_fill, work, DEFAULT_CHANNEL_STANDOFF, 2.0, None)
    segs = _line_segments(pockets)
    assert segs, "expected a bay seal"
    hit = False
    for x0, y0, x1, y1 in segs:
        if (math.hypot(x0 - primary.x(), y0 - primary.y()) <= 1.25
                or math.hypot(x1 - primary.x(), y1 - primary.y()) <= 1.25):
            hit = True
    assert hit, "seal must anchor at corner %s, got %s" % (
        (primary.x(), primary.y()), segs)


def test_compact_prefers_large_host_over_thin_stem():
    """Near-equidistant: speck ties to the larger elongated host (K-leg class)."""
    keep = QPainterPath()
    keep.addPath(_rect_path(0.0, 0.0, 20.0, 40.0))   # major
    keep.addPath(_rect_path(24.0, 0.0, 4.0, 28.0))    # thin stem
    keep.addPath(_rect_path(23.5, 32.0, 5.0, 5.0))    # compact speck
    bodies = list_closed_subpaths(keep)
    speck = [b for b in bodies if weeds_mod._is_compact_island(b, bodies)][0]
    major = max(
        (b for b in bodies if not weeds_mod._is_compact_island(b, bodies)),
        key=lambda b: abs(weeds_mod._path_area(b)))
    weed = island_hop_weeds(keep, padding=[10.0, 10.0, 10.0, 10.0], collar=4.0)
    to_major = [
        s for s in weeds_mod._iter_line_segs(weed)
        if weeds_mod._seg_spans_pair(s, speck, major, tol=2.5)]
    assert to_major, "speck should bridge to the large host, not only the stem"


def test_compact_hanging_tick_gets_two_divergent_ties():
    """Hanging tick between two majors: ≥2 ties so alleys above/below cannot fork."""
    keep = QPainterPath()
    keep.addPath(_rect_path(0.0, 10.0, 18.0, 40.0))    # left major
    keep.addPath(_rect_path(36.0, 10.0, 18.0, 40.0))   # right major
    keep.addPath(_rect_path(24.0, 14.0, 3.4, 9.3))     # hanging tick
    bodies = list_closed_subpaths(keep)
    ticks = [b for b in bodies if weeds_mod._is_compact_island(b, bodies)]
    assert len(ticks) == 1, "expected one compact hanging tick"
    tick = ticks[0]
    majors = [b for b in bodies if b is not tick]
    weed = island_hop_weeds(keep, padding=[10.0, 10.0, 10.0, 10.0], collar=4.0)
    ties = weeds_mod._compact_tie_segs(weed, tick, majors + bodies)
    assert len(ties) >= 2, (
        "hanging tick needs ≥2 ties to stop peel fork, got %s" % (ties,))
    # The two shortest ties should leave the tick in divergent directions.
    ties = sorted(
        ties, key=lambda s: math.hypot(s[2] - s[0], s[3] - s[1]))[:2]
    assert weeds_mod._ties_diverge(ties[0], ties[1], tick), (
        "second tie must diverge from the first, got %s" % (ties,))


def test_seg_redundant_requires_collinear_overlap():
    """Both ends near a host must not mark a non-aligned T-land as redundant."""
    host = QPainterPath()
    host.moveTo(0.0, 0.0)
    host.lineTo(10.0, 0.0)
    # Tip sits just off the host; tip→left-end is steep vs the host axis.
    tip_host = (2.0, 1.4, 0.0, 0.0)
    assert weeds_mod._point_seg_dist(2.0, 1.4, 0.0, 0.0, 10.0, 0.0) <= 1.5
    assert not weeds_mod._seg_redundant(host, tip_host)
    # True overlap along the same support stays redundant.
    overlap = (1.0, 0.0, 6.0, 0.0)
    assert weeds_mod._seg_redundant(host, overlap)


def test_square_tie_seeds_convex_corners():
    """Compact square-tie cands include convex-corner → host bridges."""
    keep = QPainterPath()
    keep.addPath(_rect_path(0.0, 10.0, 12.0, 30.0))
    keep.addPath(_rect_path(18.0, 28.0, 6.0, 10.0))  # hanging mark
    bodies = list_closed_subpaths(keep)
    speck = [b for b in bodies if weeds_mod._is_compact_island(b, bodies)][0]
    host = [b for b in bodies if b is not speck][0]
    work = padded_work_rect(keep, [8.0, 8.0, 8.0, 8.0])
    kf = even_odd_keep_fill(keep)
    cands = weeds_mod._square_tie_cands(
        speck, [host], kf, work, 2.0, None)
    corners = weeds_mod._convex_corners(speck)
    assert corners and cands
    hit = False
    for seg in cands:
        for c in corners:
            if (math.hypot(seg[0] - c.x(), seg[1] - c.y()) <= 0.35
                    or math.hypot(seg[2] - c.x(), seg[3] - c.y()) <= 0.35):
                hit = True
    assert hit, "expected a corner-seeded cand, got %s" % (cands,)


def test_major_gap_necks_through_tied_compact():
    """Well-tied compact in a major↔major AABB must not block a bottom neck."""
    keep = QPainterPath()
    keep.addPath(_rect_path(0.0, 10.0, 20.0, 40.0))
    keep.addPath(_rect_path(40.0, 10.0, 20.0, 40.0))
    keep.addPath(_rect_path(26.0, 12.0, 4.0, 10.0))  # high tick in the gap
    bodies = list_closed_subpaths(keep)
    majors = [b for b in bodies if not weeds_mod._is_compact_island(b, bodies)]
    tick = [b for b in bodies if weeds_mod._is_compact_island(b, bodies)][0]
    assert len(majors) == 2
    weed = island_hop_weeds(keep, padding=[10.0, 10.0, 10.0, 10.0], collar=4.0)
    assert len(weeds_mod._compact_tie_segs(weed, tick, majors)) >= 2
    seals = [
        s for s in weeds_mod._iter_line_segs(weed)
        if weeds_mod._seg_spans_pair(s, majors[0], majors[1], tol=3.0)]
    assert seals, "major↔major bottom neck missing through tied tick"
    # Prefer a seal in the lower half of the alley (open-bay end).
    mid_y = 0.5 * (
        min(majors[0].boundingRect().top(), majors[1].boundingRect().top())
        + max(majors[0].boundingRect().bottom(),
              majors[1].boundingRect().bottom()))
    assert any(0.5 * (s[1] + s[3]) >= mid_y - 1.0 for s in seals), seals


def test_design_frame_skips_outer_peel():
    """Hollow design frame must not get a second outer peel collar."""
    import io
    import logging
    from weedlib.solvers import _is_design_frame_node, list_closed_subpaths, _nest_closed_paths

    keep = QPainterPath()
    keep.addRect(QRectF(0, 0, 200, 120))
    keep.addRect(QRectF(10, 10, 180, 100))
    keep.addRect(QRectF(40, 40, 30, 30))
    nodes = _nest_closed_paths(list_closed_subpaths(keep))
    roots = [n for n in nodes if n['depth'] == 0]
    assert roots and _is_design_frame_node(roots[0])

    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(logging.Formatter('%(message)s'))
    log = logging.getLogger('weedlib')
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)
    prev = os.environ.get('WEEDLINES_LOG')
    os.environ['WEEDLINES_LOG'] = '1'
    try:
        # reset debug configured so handler path works
        import weedlib.debug as d
        d._configured = False
        weed = island_hop_weeds(keep, padding=[4, 4, 4, 4], collar=4.0)
    finally:
        log.removeHandler(handler)
        if prev is None:
            os.environ.pop('WEEDLINES_LOG', None)
        else:
            os.environ['WEEDLINES_LOG'] = prev
        d._configured = False
    text = buf.getvalue()
    assert 'design_frame_outer' in text
    assert 'peel_frame.emit' not in text
    assert not weed.isEmpty()


def _inkscape_fill_stroke_twin(path):
    """Duplicate every closed outline (Inkscape fill path + stroke path)."""
    twin = QPainterPath()
    twin.addPath(path)
    for sp in list_closed_subpaths(path):
        twin.addPath(sp)
    return twin


@requires_clipper
def test_fill_stroke_twins_deduped_for_framed_keep():
    """Fill+stroke duplicate outers must not solid-fill the frame counter."""
    keep = _inkscape_fill_stroke_twin(_framed_hi())
    # Without dedupe there would be 8 closed outlines; keep one of each.
    assert len(list_closed_subpaths(keep)) == 4
    fill = even_odd_keep_fill(keep)
    assert fill.contains(QPointF(3, 3))  # frame band
    assert not fill.contains(QPointF(60, 50))  # counter waste
    assert fill.contains(QPointF(40, 50))  # H keep


@requires_clipper
def test_fill_stroke_twins_island_hop_no_outer_peel():
    """Duplicate framed keep still skips outer peel and emits interior seals."""
    import io
    import logging

    keep = _inkscape_fill_stroke_twin(_framed_hi())
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(logging.Formatter('%(message)s'))
    log = logging.getLogger('weedlib')
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)
    prev = os.environ.get('WEEDLINES_LOG')
    os.environ['WEEDLINES_LOG'] = '1'
    try:
        import weedlib.debug as d
        d._configured = False
        weed = island_hop_weeds(keep, padding=[12, 12, 12, 12], collar=4.0)
    finally:
        log.removeHandler(handler)
        if prev is None:
            os.environ.pop('WEEDLINES_LOG', None)
        else:
            os.environ['WEEDLINES_LOG'] = prev
        d._configured = False
    text = buf.getvalue()
    assert 'design_frame_outer' in text
    assert 'peel_frame.emit' not in text
    assert weed_path_stats(weed)['segments'] > 0


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
