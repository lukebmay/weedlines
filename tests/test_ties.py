# -*- coding: utf-8 -*-
"""Compact ties."""
from __future__ import division

import math

import pytest

from weedlib.qt import QPainterPath
from weedlib.solvers import (
    island_hop_weeds,
    even_odd_keep_fill,
    list_closed_subpaths,
    padded_work_rect,
)
import weedlib.solvers.emit as mod_emit
import weedlib.solvers.gaps as mod_gaps
import weedlib.solvers.geom as mod_geom
import weedlib.keep as mod_keep
import weedlib.solvers.ties as mod_ties

pytest.importorskip('PyQt5', reason='Qt binding required for weedlib geometry')

from tests.weed_shapes import _rect_path

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
        if mod_ties._is_compact_island(
                b, list_closed_subpaths(keep)):
            specks.append(b)
        else:
            letters.append(b)
    assert specks and letters
    ties = []
    for seg in mod_geom._iter_line_segs(weed):
        if mod_gaps._seg_spans_pair(seg, specks[0], letters[0], tol=2.5):
            ties.append(seg)
    assert ties, "compact island should get a keep-to-keep tie"
    ln = min(math.hypot(s[2] - s[0], s[3] - s[1]) for s in ties)
    assert ln < 20.0, "tie should be short, got %s" % ties
    # No long rail parallel to the letter stem.
    for seg in mod_geom._iter_line_segs(weed):
        ln = math.hypot(seg[2] - seg[0], seg[3] - seg[1])
        if ln < 20.0:
            continue
        assert not mod_emit._is_parallel_hug(seg, keep_fill, 2.0), (
            "long hug survived: %s" % (seg,))


def test_thin_tick_islands_are_compact_not_stub_sources():
    """Small thin ticks (quote-like) count as compact — square ties, no leaps."""
    keep = QPainterPath()
    keep.addPath(_rect_path(0.0, 10.0, 20.0, 40.0))
    keep.addPath(_rect_path(28.0, 12.0, 3.4, 9.3))
    keep.addPath(_rect_path(34.6, 12.0, 3.4, 9.3))
    bodies = list_closed_subpaths(keep)
    ticks = [b for b in bodies if mod_ties._is_compact_island(b, bodies)
             and b.boundingRect().width() < 5.0]
    assert len(ticks) == 2, "both quote ticks should be compact"
    weed = island_hop_weeds(keep, padding=[10.0, 10.0, 10.0, 10.0], collar=4.0)
    # No long free-looking leap from a tick across open water.
    for seg in mod_geom._iter_line_segs(weed):
        ln = math.hypot(seg[2] - seg[0], seg[3] - seg[1])
        if ln <= 10.0:
            continue
        on_tick = any(
            mod_geom._point_near_path(seg[0], seg[1], t, tol=2.0)
            or mod_geom._point_near_path(seg[2], seg[3], t, tol=2.0)
            for t in ticks)
        assert not on_tick, "thin tick still has long leap: %s" % (seg,)


def test_compact_prefers_large_host_over_thin_stem():
    """Near-equidistant: speck ties to the larger elongated host (K-leg class)."""
    keep = QPainterPath()
    keep.addPath(_rect_path(0.0, 0.0, 20.0, 40.0))   # major
    keep.addPath(_rect_path(24.0, 0.0, 4.0, 28.0))    # thin stem
    keep.addPath(_rect_path(23.5, 32.0, 5.0, 5.0))    # compact speck
    bodies = list_closed_subpaths(keep)
    speck = [b for b in bodies if mod_ties._is_compact_island(b, bodies)][0]
    major = max(
        (b for b in bodies if not mod_ties._is_compact_island(b, bodies)),
        key=lambda b: abs(mod_keep._path_area(b)))
    weed = island_hop_weeds(keep, padding=[10.0, 10.0, 10.0, 10.0], collar=4.0)
    to_major = [
        s for s in mod_geom._iter_line_segs(weed)
        if mod_gaps._seg_spans_pair(s, speck, major, tol=2.5)]
    assert to_major, "speck should bridge to the large host, not only the stem"


def test_compact_hanging_tick_gets_two_divergent_ties():
    """Hanging tick between two majors: ≥2 ties so alleys above/below cannot fork."""
    keep = QPainterPath()
    keep.addPath(_rect_path(0.0, 10.0, 18.0, 40.0))    # left major
    keep.addPath(_rect_path(36.0, 10.0, 18.0, 40.0))   # right major
    keep.addPath(_rect_path(24.0, 14.0, 3.4, 9.3))     # hanging tick
    bodies = list_closed_subpaths(keep)
    ticks = [b for b in bodies if mod_ties._is_compact_island(b, bodies)]
    assert len(ticks) == 1, "expected one compact hanging tick"
    tick = ticks[0]
    majors = [b for b in bodies if b is not tick]
    weed = island_hop_weeds(keep, padding=[10.0, 10.0, 10.0, 10.0], collar=4.0)
    ties = mod_ties._compact_tie_segs(weed, tick, majors + bodies)
    assert len(ties) >= 2, (
        "hanging tick needs ≥2 ties to stop peel fork, got %s" % (ties,))
    # The two shortest ties should leave the tick in divergent directions.
    ties = sorted(
        ties, key=lambda s: math.hypot(s[2] - s[0], s[3] - s[1]))[:2]
    assert mod_ties._ties_diverge(ties[0], ties[1], tick), (
        "second tie must diverge from the first, got %s" % (ties,))


def test_square_tie_seeds_convex_corners():
    """Compact square-tie cands include convex-corner → host bridges."""
    keep = QPainterPath()
    keep.addPath(_rect_path(0.0, 10.0, 12.0, 30.0))
    keep.addPath(_rect_path(18.0, 28.0, 6.0, 10.0))  # hanging mark
    bodies = list_closed_subpaths(keep)
    speck = [b for b in bodies if mod_ties._is_compact_island(b, bodies)][0]
    host = [b for b in bodies if b is not speck][0]
    work = padded_work_rect(keep, [8.0, 8.0, 8.0, 8.0])
    kf = even_odd_keep_fill(keep)
    cands = mod_ties._square_tie_cands(
        speck, [host], kf, work, 2.0, None)
    corners = mod_geom._convex_corners(speck)
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
    majors = [b for b in bodies if not mod_ties._is_compact_island(b, bodies)]
    tick = [b for b in bodies if mod_ties._is_compact_island(b, bodies)][0]
    assert len(majors) == 2
    weed = island_hop_weeds(keep, padding=[10.0, 10.0, 10.0, 10.0], collar=4.0)
    assert len(mod_ties._compact_tie_segs(weed, tick, majors)) >= 2
    seals = [
        s for s in mod_geom._iter_line_segs(weed)
        if mod_gaps._seg_spans_pair(s, majors[0], majors[1], tol=3.0)]
    assert seals, "major↔major bottom neck missing through tied tick"
    # Prefer a seal in the lower half of the alley (open-bay end).
    mid_y = 0.5 * (
        min(majors[0].boundingRect().top(), majors[1].boundingRect().top())
        + max(majors[0].boundingRect().bottom(),
              majors[1].boundingRect().bottom()))
    assert any(0.5 * (s[1] + s[3]) >= mid_y - 1.0 for s in seals), seals
