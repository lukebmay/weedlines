# -*- coding: utf-8 -*-
"""Clearance, alpha, hugs, slivers, and rank."""
from __future__ import division

import math

import pytest

from weedlib.qt import QPainterPath, QPointF, QRectF
from weedlib.solvers.geom import (
    _convex_corners,
    _included_angle_deg,
    _keep_frame_at,
    _vertex_weed_degree,
)
from weedlib.solvers.rules import _ALPHA_HARD
import weedlib.solvers.emit as mod_emit
import weedlib.solvers.geom as mod_geom
import weedlib.solvers.rank as mod_rank
import weedlib.solvers.rules as mod_rules

pytest.importorskip('PyQt5', reason='Qt binding required for weedlib geometry')

from tests.weed_shapes import (
    _rect_path,
    _circle_path,
    _line_segments,
)

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
    cleaned = mod_emit._require_connected_ends(weed, keep, tol=1.0)
    segs = _line_segments(cleaned)
    assert len(segs) == 1, "expected only the keep-to-keep seal, got %s" % segs
    x0, y0, x1, y1 = segs[0]
    assert min(x0, x1) <= 20.5 and max(x0, x1) >= 39.5


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


def test_parallel_hug_dropped_radial_kept():
    """Plan #4: 1 mm inset parallel of a long keep side drops; radial stays."""
    keep = _rect_path(0.0, 0.0, 40.0, 80.0)
    # Long hug along the left edge (x=0), inset 1 mm into waste (x=-1).
    hug = (-1.0, 8.0, -1.0, 72.0)
    assert mod_emit._is_parallel_hug(hug, keep, 2.0)
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
    assert not mod_emit._is_parallel_hug(radial, keep, 2.0)

    cleaned = mod_emit._drop_parallel_hugs(weed, keep, 2.0)
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

    cleaned = mod_emit._require_connected_ends(weed, keep, tol=1.5, work=work)
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
    assert mod_emit._is_sliver_seal(sliver, weed, keep)
    area, alt, kappa = mod_emit._sliver_triangle_metrics(sliver, good)
    assert area < mod_emit._A_SLIVER
    assert alt < mod_emit._H_SLIVER
    assert kappa < 2.0

    weed.moveTo(sliver[0], sliver[1])
    weed.lineTo(sliver[2], sliver[3])
    cleaned = mod_emit._drop_slivers_and_needless(weed, keep)
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
    assert mod_emit._is_needless_optional_seal(near, weed, keep)
    assert not mod_emit._is_needless_optional_seal(far, weed, keep), (
        "far alley mouth must stay (both mouths on long corridor)")

    weed.moveTo(near[0], near[1])
    weed.lineTo(near[2], near[3])
    weed.moveTo(far[0], far[1])
    weed.lineTo(far[2], far[3])
    cleaned = mod_emit._drop_slivers_and_needless(weed, keep)
    segs = _line_segments(cleaned)
    assert len(segs) == 2, "near extra drops; good + far remain: %s" % segs
    mids = sorted(0.5 * (s[1] + s[3]) for s in segs)
    assert abs(mids[0] - 1.0) < 0.5 and abs(mids[1] - 20.0) < 0.5

    # Frame-open (keep→collar, no span pair) is never a necessity drop.
    frame_open = (0.0, 20.0, -6.0, 20.0)
    assert not mod_emit._is_needless_optional_seal(frame_open, weed, keep)


# --- D012: body clearance, α floor, peel-frame-first, ranking ---


def test_body_clearance_rejects_mid_hug_keeps_short_span():
    """Long mid-seg near keep fails; short keep-to-keep has no interior."""
    keep = _rect_path(0.0, 0.0, 40.0, 80.0)
    hug = (-2.0, 10.0, -2.0, 70.0)
    assert not mod_emit._seg_body_clearance_ok(hug, keep, clearance=5.0)
    short = (40.0, 40.0, 48.0, 40.0)
    assert mod_emit._seg_body_clearance_ok(short, keep, clearance=5.0)
    square = (0.0, 40.0, -12.0, 40.0)
    assert mod_emit._seg_body_clearance_ok(square, keep, clearance=5.0)


def test_alpha_floor_rejects_graze_keeps_square():
    keep = _rect_path(0.0, 0.0, 40.0, 80.0)
    graze = (-1.0, 10.0, -1.0, 50.0)
    assert not mod_emit._seg_alpha_ok(graze, keep, 30.0)
    square = (0.0, 40.0, -10.0, 40.0)
    assert mod_emit._seg_alpha_ok(square, keep, 30.0)


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
    e_sq = mod_rank._created_angle_error(
        QPointF(40.0, 40.0), (1.0, 0.0), keep)
    e_sh = mod_rank._created_angle_error(
        QPointF(40.0, 10.0), (0.8, 0.6), keep)
    assert e_sq < e_sh
    c_sq = mod_rank._peel_rank_cost(square, keep, other)
    c_sh = mod_rank._peel_rank_cost(shallow, keep, other)
    assert c_sq < c_sh
    picked = mod_rank._pick_ranked_seg([square, shallow], keep, other)
    assert picked == square


def test_forced_ok_rejects_clearance_failure():
    """α-ok but mid-body too close to another island is not a last resort."""
    keep = QPainterPath()
    keep.addPath(_rect_path(0.0, 0.0, 20.0, 40.0))
    keep.addPath(_rect_path(40.0, 0.0, 20.0, 40.0))
    keep.addPath(_rect_path(22.0, 20.6, 16.0, 3.0))
    span = (20.0, 20.0, 40.0, 20.0)
    rules = mod_rules._cut_rules()
    assert mod_emit._seg_alpha_ok(span, keep, 30.0)
    assert not mod_emit._seg_body_clearance_ok(span, keep, clearance=5.0)
    assert not mod_emit._seg_emit_ok(span, keep, None, rules)
    assert not mod_emit._seg_forced_ok(span, keep, None, rules)


def test_hug_rejects_mid_body_parallel_outside_ring():
    """Mouth-collinear and long stem-parallel rails are visual hugs."""
    keep = _rect_path(0.0, 0.0, 40.0, 80.0)
    # Along the top edge, just outside: mid-body close and parallel.
    along_top = (2.0, -2.0, 38.0, -2.2)
    assert mod_emit._is_parallel_hug(along_top, keep, 2.0)
    # Long vertical 1.5 mm off the right wall (quote-stem style).
    long_vert = (41.5, 8.0, 41.5, 72.0)
    assert mod_emit._is_parallel_hug(long_vert, keep, 2.0)
    radial = (0.0, 40.0, -10.0, 40.0)
    assert not mod_emit._is_parallel_hug(radial, keep, 2.0)


def test_seg_redundant_requires_collinear_overlap():
    """Both ends near a host must not mark a non-aligned T-land as redundant."""
    host = QPainterPath()
    host.moveTo(0.0, 0.0)
    host.lineTo(10.0, 0.0)
    # Tip sits just off the host; tip→left-end is steep vs the host axis.
    tip_host = (2.0, 1.4, 0.0, 0.0)
    assert mod_geom._point_seg_dist(2.0, 1.4, 0.0, 0.0, 10.0, 0.0) <= 1.5
    assert not mod_emit._seg_redundant(host, tip_host)
    # True overlap along the same support stays redundant.
    overlap = (1.0, 0.0, 6.0, 0.0)
    assert mod_emit._seg_redundant(host, overlap)
