# -*- coding: utf-8 -*-
"""Shared shapes for the weed solver tests."""
from __future__ import division

import math

import pytest

from weedlib.qt import QPainterPath, QPointF, QRectF
from weedlib.solvers import (
    island_hop_weeds,
    residual_waste_traps,
    sample_points_on_path,
    list_closed_subpaths,
    padded_work_rect,
)
from weedlib.keep import (
    _nest_closed_paths,
)
import weedlib.solvers.geom as mod_geom

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


def _star12_valleys(cx=50, cy=50, r_inner=16):
    valleys = []
    n = 12
    for i in range(n):
        ang = -math.pi / 2.0 + (i + 0.5) * 2.0 * math.pi / float(n)
        valleys.append(QPointF(cx + r_inner * math.cos(ang),
                               cy + r_inner * math.sin(ang)))
    return valleys


def _keep_bodies(path):
    nodes = _nest_closed_paths(list_closed_subpaths(path))
    return [n['path'] for n in nodes if n['depth'] % 2 == 0]


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


def _letter_t():
    """United stem + crossbar; open sides are shallow waste peninsulas."""
    stem = _rect_path(40, 18, 8, 54)
    bar = _rect_path(28, 18, 32, 8)
    return stem.united(bar)


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


def _end_near_keep(x, y, keep_fill, tol=0.25):
    """True if the weed end meets keep (outline or fill); boundary OK."""
    if mod_geom._point_near_path(x, y, keep_fill, tol=tol):
        return True
    if keep_fill.contains(QPointF(x, y)):
        return True
    for dx, dy in ((tol, 0), (-tol, 0), (0, tol), (0, -tol)):
        if keep_fill.contains(QPointF(x + dx, y + dy)):
            return True
    return False


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


def _shallow_smooth_notch_body():
    """Rect 40×24 with a top U-notch: mouth 24, depth 6 (ratio 0.25)."""
    return _poly_path((
        (0, 0), (8, 0), (8, 6), (32, 6), (32, 0), (40, 0),
        (40, 24), (0, 24),
    ))


def _wide_stem_pair():
    """Two stems, wide gap (not a corridor) that still share one enclosure.

    Height 24 / gap 16: gap > 0.6×overlap (not a corridor) and
    gap ≤ word-cluster threshold at default collar (one enclosure).
    """
    return _side_by_side_rects(8.0, 24.0, gap=16.0)


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


def _three_stem_gutter(w=8.0, h=24.0, gap=12.0, n=3):
    """Three vertical stems; adjacent alleys are short corridors (L/W=2)."""
    p = QPainterPath()
    x = 0.0
    for _i in range(n):
        p.addPath(_rect_path(x, 0.0, w, h))
        x += w + gap
    return p


def _residual_traps_for(keep, weed=None, padding=None, **auto_kw):
    pad = list(padding) if padding is not None else [10.0, 10.0, 10.0, 10.0]
    if weed is None:
        weed = island_hop_weeds(keep, padding=pad, collar=4.0, **auto_kw)
    work = padded_work_rect(keep, pad)
    return residual_waste_traps(
        keep, weed, work=work, padding=pad, collar=4.0, step=1.5)


def _inkscape_fill_stroke_twin(path):
    """Duplicate every closed outline (Inkscape fill path + stroke path)."""
    twin = QPainterPath()
    twin.addPath(path)
    for sp in list_closed_subpaths(path):
        twin.addPath(sp)
    return twin
