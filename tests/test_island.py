# -*- coding: utf-8 -*-
"""Island-hop through generate_weeds."""
from __future__ import division

import math
import os

import pytest

from weedlib.qt import QPainterPath, QPointF, QRectF
from weedlib import solvers as weeds_mod
from weedlib.solvers import (
    DEFAULT_CHANNEL_STANDOFF,
    DEFAULT_COLLAR,
    generate_weeds,
    grid_weeds,
    island_hop_weeds,
    sample_points_on_path,
    weed_path_stats,
    weed_sample_stats,
    even_odd_keep_fill,
    list_closed_subpaths,
    padded_work_rect,
)
from weedlib.solvers.clipper import _isolation_collar_rings
from weedlib.solvers.cluster import (
    _cluster_keep_bodies,
    _word_cluster_gap,
)
from weedlib.solvers.geom import _seg_proper_cross
from weedlib.keep import _nest_closed_paths
import weedlib.solvers.channels as mod_channels
import weedlib.solvers.clipper as mod_clipper
import weedlib.solvers.cluster as mod_cluster
import weedlib.solvers.emit as mod_emit
import weedlib.solvers.geom as mod_geom
import weedlib.keep as mod_keep

pytest.importorskip('PyQt5', reason='Qt binding required for weedlib geometry')

from tests.weed_shapes import (
    requires_clipper,
    _IN_KEEP_BUDGET,
    _quoted_blocks,
    _rect_path,
    _circle_path,
    _star12_valleys,
    _alley_with_serif_pocket,
    _letter_o,
    _fraction_inside,
    _keep_bodies,
    _letter_k,
    _three_stem_gutter,
    _star12,
    _close_satellite_pair,
    _line_segments,
    _letters_hi,
    _mid_ring_samples,
    _letter_a,
    _framed_hi,
)

def _wreath_hi():
    """Ornaments around HI (siblings, not a nested hole)."""
    p = QPainterPath()
    for x, y in ((4, 4), (54, 2), (104, 4), (4, 40), (104, 40),
                 (4, 76), (54, 80), (104, 76)):
        p.addPath(_rect_path(x, y, 12, 12))
    p.addPath(_letters_hi(ox=26, oy=10))
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
    groups = mod_cluster._enclosure_groups(nodes, 4.0)
    assert len(groups) == 1, "punctuation split the word into %s groups" % len(groups)
    weed = island_hop_weeds(keep, padding=[10, 10, 10, 10], collar=4.0)
    keep_fill = even_odd_keep_fill(keep)
    assert _fraction_inside(weed, keep_fill, step=0.8) < _IN_KEEP_BUDGET
    work = padded_work_rect(keep, [10, 10, 10, 10])
    st = weed_sample_stats(weed, keep_fill=keep_fill, work_rect=work, step=1.0)
    assert st['outside_work'] == 0


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
def test_wreath_still_weeds_inner_text():
    keep = _wreath_hi()
    nodes = _nest_closed_paths(list_closed_subpaths(keep))
    groups = mod_cluster._enclosure_groups(nodes, 4.0)
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
        keep_edges = mod_emit._keep_outline_edges(keep)
        bodies = list_closed_subpaths(keep)
        delta = min(weeds_mod.DEFAULT_FRAME_CLEARANCE, 10.0 - 2.0)
        rings = mod_clipper._cluster_offset_rings(bodies, delta) if bodies else []
        for seg in segs:
            for px, py in ((seg[0], seg[1]), (seg[2], seg[3])):
                on_keep = mod_emit._point_near_edges(px, py, keep_edges, tol)
                on_weed = mod_emit._point_near_weed_segs(
                    px, py, segs, skip=seg, tol=tol)
                if on_keep or on_weed:
                    continue
                # Keep→frame radial tip lands on the continuous peel rail.
                corridor_ok = False
                if rings:
                    hit = mod_geom._nearest_on_rings(px, py, rings)
                    corridor_ok = hit is not None and hit[2] <= tol
                assert corridor_ok, (
                    "dangling weed end at %.2f,%.2f seg=%s" % (
                        px, py, seg))


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


def test_multi_island_opens_collar_frame_once():
    """Peel frame around a word cluster gets a keep→frame opening."""
    keep = _letters_hi()
    pad = [10, 10, 10, 10]
    weed = island_hop_weeds(keep, padding=pad, collar=4.0)
    bodies = list_closed_subpaths(keep)
    delta = min(weeds_mod.DEFAULT_FRAME_CLEARANCE, min(pad) - 2.0)
    rings = mod_clipper._cluster_offset_rings(bodies, delta)
    assert rings, "expected a cluster peel-frame ring"
    assert mod_channels._has_keep_to_collar_channel(
        weed, bodies, rings, DEFAULT_CHANNEL_STANDOFF), (
        "multi-island cluster missing one frame-opening channel")


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
    cleaned = mod_emit._require_connected_ends(weed, keep, tol=1.5, work=work)
    assert cleaned.elementCount() > 0


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
    for seg in mod_geom._iter_line_segs(weed):
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


def test_container_cluster_opens_to_wall():
    """Interior design-container cluster gets a keep↔container-wall channel."""
    keep = QPainterPath()
    keep.addRect(QRectF(0.0, 0.0, 200.0, 100.0))
    keep.addRect(QRectF(8.0, 8.0, 184.0, 84.0))
    keep.addPath(_rect_path(60.0, 30.0, 50.0, 40.0))
    pad = [12.0, 12.0, 12.0, 12.0]
    weed = island_hop_weeds(keep, padding=pad, collar=4.0)
    nodes = mod_keep._nest_closed_paths(list_closed_subpaths(keep))
    groups = mod_cluster._enclosure_groups(nodes, 4.0)
    opened = False
    for cluster, container in groups:
        if container is None or container.isEmpty():
            continue
        rings = mod_geom._path_to_rings(container)
        assert rings, "expected container outline rings"
        assert mod_channels._has_keep_to_collar_channel(
            weed, cluster, rings, DEFAULT_CHANNEL_STANDOFF), (
            "container cluster missing keep↔wall corridor")
        opened = True
    assert opened, "expected a container-bound interior cluster"
