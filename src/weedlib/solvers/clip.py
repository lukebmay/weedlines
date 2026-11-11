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


def _path_has_curve(path):
    if path is None or path.isEmpty():
        return False
    curve = QPainterPath.CurveToElement
    for index in range(path.elementCount()):
        if path.elementAt(index).type == curve:
            return True
    return False


# A corner cubic's handles sit outside the arc. Chords stay this close.
_CURVE_FLAT = 0.02


def _clip_path_to_border(path, shape):
    """Clip *path* to the inner piece border.

    A square border uses its rectangle. A rounded border does not
    use that rectangle's bounding box.
    """
    if path is None or path.isEmpty() or shape is None or shape.isEmpty():
        return QPainterPath()
    if not _path_has_curve(shape):
        return _clip_path_to_rect(path, shape.boundingRect())
    out = QPainterPath()
    for seg in _sol_geom._iter_line_segs(path):
        parts = _clip_line_to_region(
            seg[0], seg[1], seg[2], seg[3], shape, False,
            samples=64, min_len=1e-9)
        for part in parts:
            if math.hypot(part[2] - part[0], part[3] - part[1]) < 1e-9:
                continue
            out.moveTo(part[0], part[1])
            out.lineTo(part[2], part[3])
    return out


def _outline_segs(path, flat=_CURVE_FLAT):
    """Line segments along the path. Curve handles are not vertices."""
    move = QPainterPath.MoveToElement
    line = QPainterPath.LineToElement
    curve = QPainterPath.CurveToElement
    data = QPainterPath.CurveToDataElement
    current = None
    index = 0
    count = path.elementCount()
    while index < count:
        element = path.elementAt(index)
        if element.type == move:
            current = (element.x, element.y)
            index += 1
            continue
        if element.type == line:
            end = (element.x, element.y)
            if current is not None:
                yield (current[0], current[1], end[0], end[1])
            current = end
            index += 1
            continue
        if element.type != curve or current is None:
            index += 1
            continue
        controls = [(element.x, element.y)]
        index += 1
        while index < count and path.elementAt(index).type == data:
            follow = path.elementAt(index)
            controls.append((follow.x, follow.y))
            index += 1
        if len(controls) == 3:
            for seg in _flatten_cubic(
                    current, controls[0], controls[1], controls[2], flat, 0):
                yield seg
            current = controls[2]
            continue
        if len(controls) == 2:
            for seg in _flatten_quad(
                    current, controls[0], controls[1], flat, 0):
                yield seg
            current = controls[1]
            continue
        current = controls[-1]


def _flatten_cubic(p0, p1, p2, p3, flat, depth):
    if depth >= 8 or _controls_near_chord(p0, p1, p2, p3, flat):
        if math.hypot(p3[0] - p0[0], p3[1] - p0[1]) >= 1e-9:
            yield (p0[0], p0[1], p3[0], p3[1])
        return
    left, right = _split_cubic(p0, p1, p2, p3)
    for seg in _flatten_cubic(left[0], left[1], left[2], left[3], flat, depth + 1):
        yield seg
    for seg in _flatten_cubic(
            right[0], right[1], right[2], right[3], flat, depth + 1):
        yield seg


def _flatten_quad(p0, p1, p2, flat, depth):
    if depth >= 8 or _point_seg_dist(p1[0], p1[1], p0, p2) <= flat:
        if math.hypot(p2[0] - p0[0], p2[1] - p0[1]) >= 1e-9:
            yield (p0[0], p0[1], p2[0], p2[1])
        return
    # Same split a cubic uses, with the quadratic lifted to a cubic.
    c1 = (
        p0[0] + 2.0 / 3.0 * (p1[0] - p0[0]),
        p0[1] + 2.0 / 3.0 * (p1[1] - p0[1]),
    )
    c2 = (
        p2[0] + 2.0 / 3.0 * (p1[0] - p2[0]),
        p2[1] + 2.0 / 3.0 * (p1[1] - p2[1]),
    )
    for seg in _flatten_cubic(p0, c1, c2, p2, flat, depth):
        yield seg


def _controls_near_chord(p0, p1, p2, p3, flat):
    return (
        _point_seg_dist(p1[0], p1[1], p0, p3) <= flat
        and _point_seg_dist(p2[0], p2[1], p0, p3) <= flat
    )


def _point_seg_dist(px, py, start, end):
    ax, ay = start
    bx, by = end
    dx = bx - ax
    dy = by - ay
    length_sq = dx * dx + dy * dy
    if length_sq <= 1e-18:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / length_sq
    if t < 0.0:
        t = 0.0
    elif t > 1.0:
        t = 1.0
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _split_cubic(p0, p1, p2, p3):
    def mid(left, right):
        return (
            0.5 * (left[0] + right[0]),
            0.5 * (left[1] + right[1]),
        )

    p01 = mid(p0, p1)
    p12 = mid(p1, p2)
    p23 = mid(p2, p3)
    p012 = mid(p01, p12)
    p123 = mid(p12, p23)
    p0123 = mid(p012, p123)
    return (p0, p01, p012, p0123), (p0123, p123, p23, p3)


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
