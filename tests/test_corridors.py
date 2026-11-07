# -*- coding: utf-8 -*-
"""Corridors, agglomerate, and gutters."""
from __future__ import division

import math

import pytest

from weedlib.qt import QPainterPath, QPointF, QRectF
from weedlib.solvers import (
    DEFAULT_CHANNEL_STANDOFF,
    island_hop_weeds,
    even_odd_keep_fill,
    list_closed_subpaths,
    padded_work_rect,
)
from weedlib.solvers.agglomerate import _agglomerate_islands
from weedlib.solvers.cluster import _is_stacked_satellite
from weedlib.solvers.corridors import (
    _channel_core,
    _is_corridor_pair,
    _seal_corridor_pair,
)
from weedlib.solvers.gaps import _gap_mouths
from weedlib.solvers.geom import _convex_corners
from weedlib.keep import _nest_closed_paths
import weedlib.solvers.cluster as mod_cluster
import weedlib.solvers.corridors as mod_corridors
import weedlib.solvers.emit as mod_emit
import weedlib.solvers.gaps as mod_gaps
import weedlib.solvers.geom as mod_geom
import weedlib.solvers.rules as mod_rules

pytest.importorskip('PyQt5', reason='Qt binding required for weedlib geometry')

from tests.weed_shapes import (
    requires_clipper,
    _quoted_blocks,
    _rect_path,
    _circle_path,
    _alley_with_serif_pocket,
    _alley_gap_seals,
    _residual_traps_for,
    _letter_t,
    _wide_stem_pair,
    _keep_bodies,
    _three_stem_gutter,
    _end_near_keep,
    _side_by_side_rects,
    _close_satellite_pair,
    _line_segments,
    _letters_hi,
    _waste_flood,
)

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
    assert mod_corridors._is_corridor_pair(h, stem)
    mouths = mod_gaps._gap_mouths(h, stem, cluster=bodies)
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
    rules = mod_rules._cut_rules()
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
        if len(bodies) >= 2 and mod_gaps._seg_spans_pair(
                seg, bodies[0], bodies[1], tol=2.5):
            keep_keeps.append(seg)
    assert keep_keeps, "no keep-to-keep H–I fuse in the gap"
    for x0, y0, x1, y1 in keep_keeps:
        assert _end_near_keep(x0, y0, keep_fill), "cut misses keep at %s" % (
            (x0, y0),)
        assert _end_near_keep(x1, y1, keep_fill), "cut misses keep at %s" % (
            (x1, y1),)


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
    cleaned = mod_emit._require_connected_ends(weed, keep, tol=1.5)
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
    cleaned = mod_emit._require_connected_ends(weed, keep, tol=1.5)
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


def test_wide_stem_gap_gets_one_bottom_seal():
    """Two stems + open bottom (wide gap): one bottom-ish mouth after islands."""
    keep = _wide_stem_pair()
    bodies = list_closed_subpaths(keep)
    assert len(bodies) == 2
    assert not _is_corridor_pair(bodies[0], bodies[1])
    nodes = _nest_closed_paths(bodies)
    groups = mod_cluster._enclosure_groups(nodes, 4.0)
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
    cleaned = mod_emit._require_connected_ends(weed, keep, tol=1.5)
    assert _alley_gap_seals(cleaned, keep_fill, 7.0, 25.0, 19.0, 26.0, min_len=10.0)


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
    cleaned = mod_emit._require_connected_ends(weed, keep, tol=1.5)
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
    cleaned = mod_emit._require_connected_ends(weed, keep, tol=1.5)
    assert len(_alley_gap_seals(
        cleaned, keep_fill, 19.0, 27.0, 25.5, 28.5, min_len=1.2)) == 1


def test_three_stem_gutter_fork_stops_wrap():
    """Three stems + bottom gutter: branch necks stop wrap into both alleys."""
    keep = _three_stem_gutter()
    bodies = list_closed_subpaths(keep)
    assert len(bodies) == 3
    assert _is_corridor_pair(bodies[0], bodies[1])
    assert _is_corridor_pair(bodies[1], bodies[2])
    assert mod_corridors._fork_branch_mouths(bodies)
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
    cleaned = mod_emit._require_connected_ends(weed, keep, tol=1.5)
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


def test_seg_spans_pair_rejects_same_body_stub():
    """A cut with both ends on one island is not a two-body seal."""
    a = _rect_path(0, 0, 10, 40)
    b = _rect_path(20, 0, 10, 40)
    # Across the gap: spans both.
    assert mod_gaps._seg_spans_pair((9.5, 20.0, 20.5, 20.0), a, b)
    # Under one body only: stub.
    assert not mod_gaps._seg_spans_pair((0.5, 41.0, 9.5, 41.0), a, b)


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
        if mod_geom._point_near_path(x0, y0, a, 2.0) and mod_geom._point_near_path(
                x1, y1, a, 2.0):
            if not mod_geom._point_near_path(x0, y0, b, 2.0) and not (
                    mod_geom._point_near_path(x1, y1, b, 2.0)):
                # Allow pocket seals wholly on one body (serif / bay).
                # Flag only near the alley bottom where the bad stub lived.
                my = 0.5 * (y0 + y1)
                if my >= a.boundingRect().bottom() - 2.0:
                    raise AssertionError(
                        "same-body stub under stem: %s" % ((x0, y0, x1, y1),))


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
