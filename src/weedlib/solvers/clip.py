# -*- coding: utf-8 -*-
"""Clips a segment to a rectangle or a region."""
from __future__ import division

import math

from ..qt import QPainterPath, QPointF

from . import geom as _sol_geom


def _rect_contains_inclusive(rect, x, y, eps=1e-6):
    return (
        rect.left() - eps <= x <= rect.right() + eps
        and rect.top() - eps <= y <= rect.bottom() + eps)


def _clip_seg_to_rect(x0, y0, x1, y1, rect):
    """Liang-Barsky clip of a segment to *rect*. None if fully outside."""
    dx = x1 - x0
    dy = y1 - y0
    t0, t1 = 0.0, 1.0
    edges = (
        (-dx, x0 - rect.left()),
        (dx, rect.right() - x0),
        (-dy, y0 - rect.top()),
        (dy, rect.bottom() - y0),
    )
    for p, q in edges:
        if abs(p) < 1e-15:
            if q < 0.0:
                return None
            continue
        t = q / p
        if p < 0.0:
            if t > t1:
                return None
            if t > t0:
                t0 = t
        else:
            if t < t0:
                return None
            if t < t1:
                t1 = t
    return (x0 + t0 * dx, y0 + t0 * dy, x0 + t1 * dx, y0 + t1 * dy)


def _clip_path_to_rect(path, rect):
    """Clip every line segment of *path* to *rect* (curves become end lines)."""
    out = QPainterPath()
    if path is None or path.isEmpty() or rect is None or rect.isEmpty():
        return out
    x0 = y0 = None
    for i in range(path.elementCount()):
        e = path.elementAt(i)
        if e.isMoveTo():
            x0, y0 = e.x, e.y
            continue
        x1, y1 = e.x, e.y
        if x0 is not None:
            seg = _clip_seg_to_rect(x0, y0, x1, y1, rect)
            if seg is not None:
                if math.hypot(seg[2] - seg[0], seg[3] - seg[1]) >= 1e-9:
                    out.moveTo(seg[0], seg[1])
                    out.lineTo(seg[2], seg[3])
        x0, y0 = x1, y1
    return out


def _point_allowed(x, y, region_path, invert_keep):
    """If invert_keep, region is keep-fill (allow outside). Else allow inside."""
    if region_path is None or region_path.isEmpty():
        return True
    inside = region_path.contains(QPointF(x, y))
    return (not inside) if invert_keep else inside


def _refine_allowed_end(xa, ya, xb, yb, region_path, invert_keep, steps=24):
    """Last allowed point on segment a→b (*a* allowed, *b* forbidden)."""
    ax, ay, fx, fy = xa, ya, xb, yb
    for _ in range(steps):
        mx = 0.5 * (ax + fx)
        my = 0.5 * (ay + fy)
        if _point_allowed(mx, my, region_path, invert_keep):
            ax, ay = mx, my
        else:
            fx, fy = mx, my
    return ax, ay


def _clip_line_to_region(x0, y0, x1, y1, region_path, invert_keep,
                        samples=64, min_len=0.5):
    """Return list of (x0,y0,x1,y1) segments allowed by region test."""
    n = max(int(samples), 8)
    flags = []
    pts = []
    for i in range(n + 1):
        t = i / float(n)
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * t
        pts.append((x, y))
        flags.append(_point_allowed(x, y, region_path, invert_keep))

    def _run_seg(i0, i1, refine_start, refine_end_to):
        xa, ya = pts[i0]
        xb, yb = pts[i1]
        if refine_start and i0 > 0:
            xa, ya = _refine_allowed_end(
                xa, ya, pts[i0 - 1][0], pts[i0 - 1][1],
                region_path, invert_keep)
        if refine_end_to is not None:
            xb, yb = _refine_allowed_end(
                xb, yb, refine_end_to[0], refine_end_to[1],
                region_path, invert_keep)
        if math.hypot(xb - xa, yb - ya) >= min_len:
            return (xa, ya, xb, yb)
        return None

    segs = []
    run = None
    for i, ok in enumerate(flags):
        if ok:
            if run is None:
                run = i
        else:
            if run is not None and i - 1 >= run:
                seg = _run_seg(
                    run, i - 1, refine_start=True, refine_end_to=pts[i])
                if seg is not None:
                    segs.append(seg)
            run = None
    if run is not None and n >= run:
        seg = _run_seg(run, n, refine_start=True, refine_end_to=None)
        if seg is not None:
            segs.append(seg)
    return segs


def _clip_path_to_waste(path, keep_fill, container=None):
    """Keep only segments in waste, and inside *container* when set."""
    out = QPainterPath()
    if path is None or path.isEmpty():
        return out
    x0 = y0 = None
    for i in range(path.elementCount()):
        e = path.elementAt(i)
        if e.isMoveTo():
            x0, y0 = e.x, e.y
            continue
        x1, y1 = e.x, e.y
        if x0 is not None:
            segs = [(x0, y0, x1, y1)]
            if keep_fill is not None and not keep_fill.isEmpty():
                nxt = []
                for s in segs:
                    nxt.extend(_clip_line_to_region(
                        s[0], s[1], s[2], s[3], keep_fill, invert_keep=True,
                        samples=32, min_len=0.4))
                segs = nxt
            if container is not None and not container.isEmpty():
                nxt = []
                for s in segs:
                    nxt.extend(_clip_line_to_region(
                        s[0], s[1], s[2], s[3], container, invert_keep=False,
                        samples=32, min_len=0.4))
                segs = nxt
            _sol_geom._add_line_segs(out, segs)
        x0, y0 = x1, y1
    return out
