# -*- coding: utf-8 -*-
"""One inner bridge and its clearance test."""
from __future__ import division

import math

from .. import progress
from ..qt import QPointF

from .offset import (
    _CURVE_FLATNESS,
    _closed_path,
    _cubic_coeffs,
    _point_segment_distance,
    _quad_coeffs,
    _ring_points,
    _ring_segments,
    _segments,
)
from .union import _merge_gap, _min_ring_distance, _ring_sits_inside


def _bridge_inner_outers(outers, subject, distance, join_gap):
    """Join inner rings that sit outside each other.

    The separation has to fall within the join gap, and the bridge
    has to stay at least ``distance`` from the subject. A span
    through a wall does not.
    """
    pending = []
    for outer in outers:
        ring = _ring_points(outer)
        if len(ring) >= 3:
            pending.append((outer, ring, False))
    while len(pending) > 1:
        best = None
        for left in range(len(pending)):
            for right in range(left + 1, len(pending)):
                progress.check()
                ring_a = pending[left][1]
                ring_b = pending[right][1]
                if (
                    _ring_sits_inside(ring_a, ring_b)
                    or _ring_sits_inside(ring_b, ring_a)
                ):
                    continue
                gap = _min_ring_distance(ring_a, ring_b)
                if gap > join_gap + 1e-4:
                    continue
                if best is not None and gap >= best[0]:
                    continue
                merged = _merge_gap(ring_a, ring_b)
                if merged is None:
                    continue
                if not _bridge_clears(
                    merged, ring_a, ring_b, subject, distance):
                    continue
                best = (gap, left, right, merged)
        if best is None:
            break
        _gap, left, right, merged = best
        pending = [
            pending[index]
            for index in range(len(pending))
            if index != left and index != right
        ]
        pending.append((None, merged, True))
    outlines = []
    for path, ring, merged in pending:
        if path is None:
            path = _closed_path(ring)
        if path is not None:
            outlines.append((path, merged))
    return outlines


def _bridge_clears(merged, ring_a, ring_b, subject, distance):
    """Each new edge stays at least ``distance`` from the subject.

    The edge is one segment. Samples leave a gap a finger can fill.
    A chord of the subject sits inside a curve, so the gap is to the
    curve, not to those chords.
    """
    rings = _ring_segments(ring_a) + _ring_segments(ring_b)
    limit = distance - _CURVE_FLATNESS
    if limit < 0.0:
        limit = 0.0
    count = len(merged)
    named = merged if len(merged) >= 3 else None
    for index in range(count):
        start = merged[index]
        end = merged[(index + 1) % count]
        if _edge_on_segments(start, end, rings):
            progress.check(outline=named)
            continue
        progress.check(
            outline=named,
            line=(start[0], start[1], end[0], end[1]),
        )
        if not _edge_clears_subject(start, end, subject, limit):
            return False
    return True


def _edge_on_segments(start, end, segments):
    """True when the edge is a piece of one segment."""
    for origin, dest in segments:
        if _point_segment_distance(start, origin, dest) > 1e-3:
            continue
        if _point_segment_distance(end, origin, dest) > 1e-3:
            continue
        return True
    return False


def _edge_clears_subject(start, end, subject, limit):
    """The whole edge misses the subject and stays ``limit`` away.

    Contact only at an endpoint is not a hit. The open edge still
    fails when it crosses the curve or lies in the subject.
    """
    line = (start[0], start[1], end[0], end[1])
    for kind, points in _segments(subject):
        progress.check(line=line)
        dist, hit = _primitive_gap(start, end, kind, points)
        if hit or dist < limit:
            return False
    return not _open_edge_inside(start, end, subject)


def _open_edge_inside(start, end, subject):
    """True when the midpoint lies in the subject, off the boundary."""
    mid = (
        (start[0] + end[0]) * 0.5,
        (start[1] + end[1]) * 0.5,
    )
    if not subject.contains(QPointF(mid[0], mid[1])):
        return False
    return _point_subject_distance(mid, subject) > 1e-4


def _primitive_gap(start, end, kind, points):
    """Distance from the closed segment, and an open-segment hit."""
    if kind == 'line':
        return (
            _lines_gap(start, end, points[0], points[1]),
            _open_segment_hits(start, end, points),
        )
    return _curve_segment_gap(start, end, points)


def _lines_gap(start, end, origin, dest):
    """Least distance between two segments."""
    best = None
    for point, left, right in (
        (start, origin, dest),
        (end, origin, dest),
        (origin, start, end),
        (dest, start, end),
    ):
        dist = _point_segment_distance(point, left, right)
        if best is None or dist < best:
            best = dist
    if best is None:
        return 0.0
    return best


def _point_subject_distance(point, subject):
    best = None
    for kind, points in _segments(subject):
        if kind == 'line':
            dist = _point_segment_distance(point, points[0], points[1])
        else:
            basis = _curve_basis(points)
            dist = _point_curve_distance(point, basis[0], basis[1])
        if best is None or dist < best:
            best = dist
    if best is None:
        return 0.0
    return best


def _curve_basis(points):
    """Power basis ``(t**3, t**2, t, const)`` of one quad or cubic."""
    if len(points) == 4:
        return (
            _cubic_coeffs(
                points[0][0], points[1][0], points[2][0], points[3][0]),
            _cubic_coeffs(
                points[0][1], points[1][1], points[2][1], points[3][1]),
        )
    return (
        _quad_coeffs(points[0][0], points[1][0], points[2][0]),
        _quad_coeffs(points[0][1], points[1][1], points[2][1]),
    )


def _curve_point(basis_x, basis_y, t):
    return (_horner(basis_x, t), _horner(basis_y, t))


def _horner(coeff, t):
    cubic, quad, linear, constant = coeff
    return ((cubic * t + quad) * t + linear) * t + constant


def _curve_segment_gap(start, end, points):
    """Distance to one quad or cubic, and whether the open edge meets it.

    The closest point is an endpoint or a critical point. On a cubic,
    ``(C - P) · C'`` is a quintic. A tangent parallel to the edge is a
    quadratic, and a crossing of the edge's line is a cubic. None of
    those is a sample spacing.
    """
    basis_x, basis_y = _curve_basis(points)
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length_sq = dx * dx + dy * dy
    best = None

    def keep(dist):
        nonlocal best
        if best is None or dist < best:
            best = dist

    for t in (0.0, 1.0):
        keep(_point_segment_distance(
            _curve_point(basis_x, basis_y, t), start, end))
    for point in (start, end):
        keep(_point_curve_distance(point, basis_x, basis_y))
    if length_sq <= 1e-18:
        if best is None:
            return 0.0, False
        return best, False
    direction = (dx, dy)
    if _tangent_always_parallel(basis_x, basis_y, direction, length_sq):
        # No isolated parallel root. The curve stays on one parallel line,
        # so the gap is the perpendicular plus any along-line separation.
        keep(_parallel_curve_gap(
            start, basis_x, basis_y, direction, length_sq))
        hit = _curve_hits_segment(
            start, basis_x, basis_y, direction, length_sq)
        if hit:
            keep(0.0)
        if best is None:
            return 0.0, hit
        return best, hit
    for t in _unit_poly_roots(_parallel_coeffs(basis_x, basis_y, direction)):
        point = _curve_point(basis_x, basis_y, _clamp_unit(t))
        scale = (
            (point[0] - start[0]) * dx + (point[1] - start[1]) * dy
        ) / length_sq
        if scale < -1e-8 or scale > 1.0 + 1e-8:
            continue
        keep(_point_segment_distance(point, start, end))
    hit = _curve_hits_segment(
        start, basis_x, basis_y, direction, length_sq)
    if hit:
        keep(0.0)
    if best is None:
        return 0.0, hit
    return best, hit


def _point_curve_distance(point, basis_x, basis_y):
    best = None
    candidates = [0.0, 1.0]
    candidates.extend(
        _unit_poly_roots(_approach_coeffs(point, basis_x, basis_y)))
    for t in candidates:
        curve = _curve_point(basis_x, basis_y, _clamp_unit(t))
        dist = math.hypot(curve[0] - point[0], curve[1] - point[1])
        if best is None or dist < best:
            best = dist
    if best is None:
        return 0.0
    return best


def _dot(first, second):
    return first[0] * second[0] + first[1] * second[1]


def _approach_coeffs(point, basis_x, basis_y):
    """``(C(t) - P) · C'(t)``, highest degree first."""
    cubic = (basis_x[0], basis_y[0])
    quad = (basis_x[1], basis_y[1])
    linear = (basis_x[2], basis_y[2])
    end = (
        basis_x[3] - point[0],
        basis_y[3] - point[1],
    )
    return [
        3.0 * _dot(cubic, cubic),
        5.0 * _dot(cubic, quad),
        4.0 * _dot(cubic, linear) + 2.0 * _dot(quad, quad),
        3.0 * _dot(quad, linear) + 3.0 * _dot(cubic, end),
        _dot(linear, linear) + 2.0 * _dot(quad, end),
        _dot(end, linear),
    ]


def _parallel_coeffs(basis_x, basis_y, direction):
    """``C'(t) × direction``, highest degree first."""
    dx, dy = direction
    return [
        3.0 * (basis_x[0] * dy - basis_y[0] * dx),
        2.0 * (basis_x[1] * dy - basis_y[1] * dx),
        basis_x[2] * dy - basis_y[2] * dx,
    ]


def _crossing_coeffs(start, basis_x, basis_y, direction):
    """``(C(t) - start) × direction``, highest degree first."""
    dx, dy = direction
    return [
        basis_x[0] * dy - basis_y[0] * dx,
        basis_x[1] * dy - basis_y[1] * dx,
        basis_x[2] * dy - basis_y[2] * dx,
        (basis_x[3] - start[0]) * dy - (basis_y[3] - start[1]) * dx,
    ]


def _coeffs_vanish(coeffs, span):
    return max(abs(coeff) for coeff in coeffs) <= 1e-9 * span


def _tangent_always_parallel(basis_x, basis_y, direction, length_sq):
    """True when ``C'(t) × direction`` is identically zero."""
    span = max(math.sqrt(length_sq), 1.0)
    return _coeffs_vanish(
        _parallel_coeffs(basis_x, basis_y, direction), span)


def _curve_on_line(start, basis_x, basis_y, direction, length_sq):
    """True when the whole curve lies on the edge's infinite line."""
    span = max(math.sqrt(length_sq), 1.0)
    return _coeffs_vanish(
        _crossing_coeffs(start, basis_x, basis_y, direction), span)


def _parallel_curve_gap(start, basis_x, basis_y, direction, length_sq):
    """Gap to a curve whose tangent stays parallel to the edge."""
    point = _curve_point(basis_x, basis_y, 0.0)
    cross = (
        (point[0] - start[0]) * direction[1]
        - (point[1] - start[1]) * direction[0]
    )
    length = math.sqrt(length_sq)
    perp = abs(cross) / length
    low, high = _projection_span(
        start, basis_x, basis_y, direction, length_sq)
    if high >= 0.0 and low <= 1.0:
        along = 0.0
    elif high < 0.0:
        along = -high * length
    else:
        along = (low - 1.0) * length
    return math.hypot(perp, along)


def _curve_hits_segment(start, basis_x, basis_y, direction, length_sq):
    """True when the curve meets the open segment."""
    if _curve_on_line(start, basis_x, basis_y, direction, length_sq):
        return _flat_curve_hits(
            start, basis_x, basis_y, direction, length_sq)
    for t in _real_poly_roots(
            _crossing_coeffs(start, basis_x, basis_y, direction)):
        if t < -1e-8 or t > 1.0 + 1e-8:
            continue
        point = _curve_point(basis_x, basis_y, _clamp_unit(t))
        scale = (
            (point[0] - start[0]) * direction[0]
            + (point[1] - start[1]) * direction[1]
        ) / length_sq
        if 1e-8 < scale < 1.0 - 1e-8:
            return True
    return False


def _flat_curve_hits(start, basis_x, basis_y, direction, length_sq):
    """The curve lies on the edge's line. True when the spans overlap."""
    low, high = _projection_span(
        start, basis_x, basis_y, direction, length_sq)
    return high > 1e-8 and low < 1.0 - 1e-8


def _projection_span(start, basis_x, basis_y, direction, length_sq):
    samples = [0.0, 1.0]
    samples.extend(_unit_poly_roots(
        _speed_coeffs(basis_x, basis_y, direction)))
    low = None
    high = None
    for t in samples:
        point = _curve_point(basis_x, basis_y, _clamp_unit(t))
        scale = (
            (point[0] - start[0]) * direction[0]
            + (point[1] - start[1]) * direction[1]
        ) / length_sq
        if low is None or scale < low:
            low = scale
        if high is None or scale > high:
            high = scale
    if low is None:
        return 0.0, 0.0
    return low, high


def _speed_coeffs(basis_x, basis_y, direction):
    """``C'(t) · direction``, highest degree first."""
    return [
        3.0 * (basis_x[0] * direction[0] + basis_y[0] * direction[1]),
        2.0 * (basis_x[1] * direction[0] + basis_y[1] * direction[1]),
        basis_x[2] * direction[0] + basis_y[2] * direction[1],
    ]


def _clamp_unit(value):
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def _trim_coeffs(coeffs):
    scale = 0.0
    for coeff in coeffs:
        if abs(coeff) > scale:
            scale = abs(coeff)
    tol = 1e-12 * scale
    index = 0
    last = len(coeffs) - 1
    while index < last and abs(coeffs[index]) <= tol:
        index += 1
    return coeffs[index:]


def _eval_poly(coeffs, t):
    value = 0.0
    for coeff in coeffs:
        value = value * t + coeff
    return value


def _deriv_coeffs(coeffs):
    degree = len(coeffs) - 1
    return [
        coeffs[index] * (degree - index)
        for index in range(degree)
    ]


def _cube_root(value):
    return math.copysign(abs(value) ** (1.0 / 3.0), value)


def _quadratic_roots(a, b, c):
    if abs(a) <= 1e-18:
        if abs(b) <= 1e-18:
            return []
        return [-c / b]
    disc = b * b - 4.0 * a * c
    if disc < 0.0:
        if disc > -1e-14:
            disc = 0.0
        else:
            return []
    root = math.sqrt(disc)
    return [(-b + root) / (2.0 * a), (-b - root) / (2.0 * a)]


def _cubic_roots(a, b, c, d):
    scale = max(1.0, abs(b), abs(c), abs(d))
    if abs(a) <= 1e-14 * scale:
        return _quadratic_roots(b, c, d)
    aa = a * a
    shift = b / (3.0 * a)
    p = (3.0 * a * c - b * b) / (3.0 * aa)
    q = (
        2.0 * b * b * b - 9.0 * a * b * c + 27.0 * aa * d
    ) / (27.0 * aa * a)
    disc = (q * 0.5) ** 2 + (p / 3.0) ** 3
    if p < 0.0 and disc <= 1e-14:
        radius = math.sqrt(-p / 3.0)
        arg = (-0.5 * q) / (radius ** 3)
        if arg > 1.0:
            arg = 1.0
        elif arg < -1.0:
            arg = -1.0
        theta = math.acos(arg)
        return [
            2.0 * radius * math.cos(
                (theta - 2.0 * math.pi * k) / 3.0) - shift
            for k in range(3)
        ]
    root = math.sqrt(disc) if disc > 0.0 else 0.0
    left = _cube_root(-0.5 * q + root)
    right = _cube_root(-0.5 * q - root)
    return [left + right - shift]


def _real_poly_roots(coeffs):
    """Real roots of a polynomial of degree at most 3."""
    coeffs = _trim_coeffs(coeffs)
    degree = len(coeffs) - 1
    if degree <= 0:
        return []
    if degree == 1:
        lead, constant = coeffs
        if abs(lead) <= 1e-18:
            return []
        return [-constant / lead]
    if degree == 2:
        return _quadratic_roots(coeffs[0], coeffs[1], coeffs[2])
    return _cubic_roots(coeffs[0], coeffs[1], coeffs[2], coeffs[3])


def _unit_poly_roots(coeffs):
    """Real roots in ``[0, 1]``. Degree above 3 is split by its derivative."""
    coeffs = _trim_coeffs(coeffs)
    degree = len(coeffs) - 1
    if degree <= 0:
        return []
    if degree <= 3:
        return [
            root for root in _real_poly_roots(coeffs)
            if -1e-10 <= root <= 1.0 + 1e-10
        ]
    splits = [0.0, 1.0]
    for root in _unit_poly_roots(_deriv_coeffs(coeffs)):
        if 0.0 < root < 1.0:
            splits.append(root)
    splits.sort()
    scale = 0.0
    for coeff in coeffs:
        if abs(coeff) > scale:
            scale = abs(coeff)
    tol = 1e-9 * max(scale, 1.0)
    found = []
    previous = None
    for split in splits:
        if previous is not None and split - previous <= 1e-14:
            continue
        if previous is not None:
            found.extend(_bisect_root(coeffs, previous, split, tol))
        if abs(_eval_poly(coeffs, split)) <= tol:
            found.append(split)
        previous = split
    return found


def _bisect_root(coeffs, left, right, tol):
    start = _eval_poly(coeffs, left)
    end = _eval_poly(coeffs, right)
    if abs(start) <= tol or abs(end) <= tol:
        return []
    if start * end > 0.0:
        return []
    for _step in range(60):
        mid = 0.5 * (left + right)
        value = _eval_poly(coeffs, mid)
        if abs(value) <= tol or right - left < 1e-14:
            return [mid]
        if start * value <= 0.0:
            right = mid
        else:
            left = mid
            start = value
    return [0.5 * (left + right)]


def _open_segment_hits(start, end, edge):
    """True when the open segment meets ``edge``, ends excluded."""
    ax, ay = start
    bx, by = end
    cx, cy = edge[0]
    dx, dy = edge[1]
    rx = bx - ax
    ry = by - ay
    sx = dx - cx
    sy = dy - cy
    denom = rx * sy - ry * sx
    qx = cx - ax
    qy = cy - ay
    if abs(denom) <= 1e-9:
        if abs(qx * ry - qy * rx) > 1e-7:
            return False
        length_sq = rx * rx + ry * ry
        if length_sq <= 1e-18:
            return False
        t0 = (qx * rx + qy * ry) / length_sq
        t1 = ((dx - ax) * rx + (dy - ay) * ry) / length_sq
        if t0 > t1:
            t0, t1 = t1, t0
        left = t0 if t0 > 0.0 else 0.0
        right = t1 if t1 < 1.0 else 1.0
        return right - left > 1e-8
    t = (qx * sy - qy * sx) / denom
    u = (qx * ry - qy * rx) / denom
    if t <= 1e-8 or t >= 1.0 - 1e-8:
        return False
    return -1e-8 <= u <= 1.0 + 1e-8


def _segment_gap(start, end, edges):
    """Least distance between the segment and the edges."""
    best = None
    for origin, dest in edges:
        for point, left, right in (
            (start, origin, dest),
            (end, origin, dest),
            (origin, start, end),
            (dest, start, end),
        ):
            dist = _point_segment_distance(point, left, right)
            if best is None or dist < best:
                best = dist
    if best is None:
        return 0.0
    return best


def _point_edge_distance(point, edges):
    best = None
    for start, end in edges:
        dist = _point_segment_distance(point, start, end)
        if best is None or dist < best:
            best = dist
    if best is None:
        return 0.0
    return best
