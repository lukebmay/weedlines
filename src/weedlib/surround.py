# -*- coding: utf-8 -*-
"""Surrounds: one smoothed outline around each subject cluster."""
from __future__ import division

import math

from .paths import split_painter_path
from .qt import QPainterPath, QPainterPathStroker, QPointF, QTransform, Qt

# Boolean ops and the stroker flatten curves. Scale, and a tight
# curve threshold, keep the inward error to rounding. The threshold
# is in scaled units, so a length in user units uses it over the scale.
_CLIP_SCALE = 32.0
_CURVE_FLATNESS = 0.01
_CHORD_PAD = _CURVE_FLATNESS / _CLIP_SCALE
_CLOSED_TOL = 1e-4
_AREA_EPS = 1e-8
_TANGENT_EPS = 1e-12
_ARC_STEP = math.radians(4.0)
# A right turn steeper than this is a corner, not stroker noise.
_SHARP_TURN = 20.0
_FILLET_ERR = 0.05


def build_surrounds(subject, distance, join_gap=0.0):
    """One smoothed outline for each cluster, as closed paths.

    ``subject`` is the subject region in document user units, holes
    included. ``distance`` and ``join_gap`` are lengths in those
    units and are never negative. Zero distance is that region's
    outer boundary. A positive distance expands it with a round
    join. Surrounds that meet, overlap, or lie within ``join_gap``
    are one outline. That outline stays at least ``distance`` from
    the subject. A loop that only follows a hole is not returned.
    """
    if not isinstance(subject, QPainterPath):
        raise TypeError(
            'subject must be a QPainterPath, got: {}'.format(
                type(subject).__name__))
    distance = float(distance)
    join_gap = float(join_gap)
    if distance < 0.0:
        raise ValueError(
            'surround distance must not be negative, got: {}'.format(distance))
    if join_gap < 0.0:
        raise ValueError(
            'join gap must not be negative, got: {}'.format(join_gap))
    if subject.isEmpty():
        return []
    if distance == 0.0:
        dilated = None
        outers = _meeting_outers(subject)
    else:
        dilated = _dilate(subject, distance)
        outers = _outer_boundaries(dilated)
    surrounds = []
    for group in _join_groups(subject, outers, distance, join_gap):
        kept, inner = _separate_inner_outers(group)
        for piece, merged in _bridge_inner_outers(
            inner, subject, distance, join_gap):
            if distance == 0.0:
                surrounds.append(piece)
            else:
                surrounds.append(_finish_outline(
                    piece, distance, dilated, not merged))
        if not kept:
            continue
        if len(kept) == 1:
            outline = kept[0]
        else:
            outline = _bridge_outlines(kept)
            if outline is None:
                if distance == 0.0:
                    surrounds.extend(kept)
                else:
                    surrounds.extend(
                        _finish_outline(outer, distance, dilated)
                        for outer in kept)
                continue
        if distance == 0.0:
            surrounds.append(outline)
        else:
            # A merged step is not a channel mouth. Capping it would
            # fill the pocket the bridges just kept open.
            surrounds.append(_finish_outline(
                outline, distance, dilated, len(kept) == 1))
    return surrounds


def _join_groups(subject, outers, distance, join_gap):
    """Outers whose surrounds fall within ``join_gap``, as groups.

    One wider round dilation sees every piece. A pairwise union
    would repeat a boolean per piece and still leave the crossing
    dent. Eroding that dilation back off drops a corner touch: the
    neck is thinner than the disk that has to fit.
    """
    if join_gap == 0.0 or len(outers) < 2:
        return [[outer] for outer in outers]
    # Chords sit inside the arc by the scaled curve threshold.
    # Adding that threshold in user units joins a straight gap early.
    wide = _dilate(subject, distance + join_gap * 0.5 + _CHORD_PAD)
    components = _components(wide)
    groups = [[] for _component in components]
    missed = []
    for outer in outers:
        point = _contained_point(outer)
        placed = False
        if point is not None:
            for index, component in enumerate(components):
                if component.contains(point):
                    groups[index].append(outer)
                    placed = True
                    break
        if not placed:
            missed.append([outer])
    return [group for group in groups if group] + missed


def _separate_inner_outers(outers):
    """Rings that sit inside another, and the rings around them.

    A span from an inner ring to that outer cuts the frame. The
    inner rings can still bridge each other.
    """
    rings = [_ring_points(outer) for outer in outers]
    inner = []
    kept = []
    for index, outer in enumerate(outers):
        if any(
            other != index and _ring_sits_inside(rings[other], rings[index])
            for other in range(len(outers))
        ):
            inner.append(outer)
        else:
            kept.append(outer)
    return kept, inner


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
    for index in range(count):
        start = merged[index]
        end = merged[(index + 1) % count]
        if _edge_on_segments(start, end, rings):
            continue
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
    for kind, points in _segments(subject):
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


def _bridge_outlines(outers):
    """Join outlines across the gap between them.

    Each bridge is an external tangent grown from the closest points.
    The walk stops at a reflex vertex, then each outer keeps its own
    boundary between the bridges. Two convex rings have no reflex, so
    that tangent can be the hull edge across a step. The ends of the
    facing overlap are the bridges then, and the straight offset stays.
    """
    rings = [
        ring for ring in (_ring_points(outer) for outer in outers)
        if len(ring) >= 3
    ]
    if len(rings) < 2:
        return None
    pending = rings
    while len(pending) > 1:
        nearest = None
        for left in range(len(pending)):
            for right in range(left + 1, len(pending)):
                gap, _ia, _ib = _closest_vertices(pending[left], pending[right])
                if nearest is None or gap < nearest[0]:
                    nearest = (gap, left, right)
        _gap, left, right = nearest
        merged = _merge_gap(pending[left], pending[right])
        if merged is None:
            return None
        pending = [
            pending[index]
            for index in range(len(pending))
            if index != left and index != right
        ]
        pending.append(merged)
    if len(pending[0]) < 3:
        return None
    return _closed_path(pending[0])


def _closest_vertices(ring_a, ring_b):
    best = None
    for index_a, point_a in enumerate(ring_a):
        for index_b, point_b in enumerate(ring_b):
            gap = math.hypot(point_a[0] - point_b[0], point_a[1] - point_b[1])
            if best is None or gap < best[0]:
                best = (gap, index_a, index_b)
    return best


def _gap_tangent(ring_a, ring_b, index_a, index_b, direction):
    """One external tangent, walking out from the closest points.

    The rings advance in opposite directions. A reflex vertex is not
    a bridge end, so the walk cannot cut across a notch.
    """
    step_a = direction
    step_b = -direction
    sign_a = -float(direction)
    sign_b = float(direction)
    count_a = len(ring_a)
    count_b = len(ring_b)
    for _step in range(count_a + count_b + 3):
        moved = False
        next_a = (index_a + step_a) % count_a
        if (
            not _reflex_vertex(ring_a, next_a)
            and _cross(ring_b[index_b], ring_a[index_a], ring_a[next_a]) * sign_a
            > 1e-9
        ):
            index_a = next_a
            moved = True
            continue
        next_b = (index_b + step_b) % count_b
        if (
            not _reflex_vertex(ring_b, next_b)
            and _cross(ring_a[index_a], ring_b[index_b], ring_b[next_b]) * sign_b
            > 1e-9
        ):
            index_b = next_b
            moved = True
            continue
        if not moved:
            break
    return index_a, index_b


def _reflex_vertex(points, index):
    return _signed_turn(points, index) <= -_SHARP_TURN


def _cross(origin, first, second):
    return (
        (first[0] - origin[0]) * (second[1] - origin[1])
        - (first[1] - origin[1]) * (second[0] - origin[0])
    )


def _index_chain(count, start, end):
    indices = [start]
    cursor = start
    while cursor != end:
        cursor = (cursor + 1) % count
        indices.append(cursor)
        if len(indices) > count + 1:
            break
    return indices


def _chain_gap(ring, indices, other):
    sample = indices[1:-1] if len(indices) > 2 else indices
    if not sample:
        sample = indices
    segments = [
        (other[index], other[(index + 1) % len(other)])
        for index in range(len(other))
    ]
    total = 0.0
    for index in sample:
        total += _distance_to_segments(ring[index], segments)
    return total / float(len(sample))


def _merge_gap(ring_a, ring_b):
    """One outline: the far boundary of each ring, plus two gap bridges."""
    tangent = _tangent_points(ring_a, ring_b)
    if tangent is None or _boundary_hidden(tangent, ring_a, ring_b):
        # A walk that ends on one vertex drops the rest of that ring.
        # A hull edge can also cut off a straight offset. Either way
        # the bridges are the facing overlap.
        spanned = _span_points(ring_a, ring_b)
        if spanned is not None:
            return spanned
    return tangent


def _tangent_points(ring_a, ring_b):
    """External tangents. None when either ring has one bridge end."""
    _gap, index_a, index_b = _closest_vertices(ring_a, ring_b)
    ends = [
        _gap_tangent(ring_a, ring_b, index_a, index_b, direction)
        for direction in (1, -1)
    ]
    if ends[0][0] == ends[1][0] or ends[0][1] == ends[1][1]:
        return None
    return _assemble_gap(ring_a, ring_b, {
        ends[0][0]: ends[0][1],
        ends[1][0]: ends[1][1],
    })


def _assemble_gap(ring_a, ring_b, bridges):
    if len(bridges) < 2:
        return None
    first, second = list(bridges.keys())
    chain_ab = _index_chain(len(ring_a), first, second)
    chain_ba = _index_chain(len(ring_a), second, first)
    if _chain_gap(ring_a, chain_ab, ring_b) >= _chain_gap(ring_a, chain_ba, ring_b):
        far = chain_ab
    else:
        far = chain_ba
    start_b = bridges[far[-1]]
    end_b = bridges[far[0]]
    forward = _index_chain(len(ring_b), start_b, end_b)
    backward = _index_chain(len(ring_b), end_b, start_b)
    if _chain_gap(ring_b, forward, ring_a) < _chain_gap(ring_b, backward, ring_a):
        far = list(reversed(far))
        start_b = bridges[far[-1]]
        end_b = bridges[far[0]]
        forward = _index_chain(len(ring_b), start_b, end_b)
    points = [ring_a[index] for index in far]
    points.extend(ring_b[index] for index in forward)
    return points


def _point_segment_distance(point, start, end):
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length_sq = dx * dx + dy * dy
    if length_sq <= 1e-18:
        return math.hypot(point[0] - start[0], point[1] - start[1])
    scale = (
        (point[0] - start[0]) * dx + (point[1] - start[1]) * dy
    ) / length_sq
    if scale < 0.0:
        scale = 0.0
    elif scale > 1.0:
        scale = 1.0
    return math.hypot(
        point[0] - (start[0] + scale * dx),
        point[1] - (start[1] + scale * dy),
    )


def _parallel_overlap(a0, a1, b0, b1):
    """The facing overlap of two parallel edges, or None."""
    adx = a1[0] - a0[0]
    ady = a1[1] - a0[1]
    length_a = math.hypot(adx, ady)
    bdx = b1[0] - b0[0]
    bdy = b1[1] - b0[1]
    length_b = math.hypot(bdx, bdy)
    if length_a <= _TANGENT_EPS or length_b <= _TANGENT_EPS:
        return None
    ux = adx / length_a
    uy = ady / length_a
    if abs(ux * bdy - uy * bdx) / length_b > 1e-6:
        return None
    nx = -uy
    ny = ux
    signed = (b0[0] - a0[0]) * nx + (b0[1] - a0[1]) * ny
    signed_end = (b1[0] - a0[0]) * nx + (b1[1] - a0[1]) * ny
    if abs(signed - signed_end) > 1e-4:
        return None
    dist = abs(signed)
    if signed < 0.0:
        nx = -nx
        ny = -ny

    def along(point):
        return (point[0] - a0[0]) * ux + (point[1] - a0[1]) * uy

    lo = min(along(b0), along(b1))
    hi = max(along(b0), along(b1))
    start = max(0.0, lo)
    end = min(length_a, hi)
    if end < start + 1e-6:
        return None

    def at(t):
        return (a0[0] + ux * t, a0[1] + uy * t)

    p0 = at(start)
    p1 = at(end)
    q0 = (p0[0] + nx * dist, p0[1] + ny * dist)
    q1 = (p1[0] + nx * dist, p1[1] + ny * dist)
    return dist, end - start, p0, q0, p1, q1


def _run_continues(points, index):
    """The next edge lies on this edge. An arc chord turns off the line."""
    count = len(points)
    a0 = points[index]
    a1 = points[(index + 1) % count]
    b1 = points[(index + 2) % count]
    adx = a1[0] - a0[0]
    ady = a1[1] - a0[1]
    bdx = b1[0] - a1[0]
    bdy = b1[1] - a1[1]
    length_a = math.hypot(adx, ady)
    length_b = math.hypot(bdx, bdy)
    if length_a <= _TANGENT_EPS or length_b <= _TANGENT_EPS:
        return False
    ux = adx / length_a
    uy = ady / length_a
    if ux * bdx + uy * bdy < (1.0 - 1e-8) * length_b:
        return False
    if abs(ux * bdy - uy * bdx) > 1e-6:
        return False
    return True


def _straight_runs(ring):
    """Each run is one straight side, including across a colinear seam."""
    count = len(ring)
    if count < 2:
        return []
    continues = [_run_continues(ring, index) for index in range(count)]
    start = 0
    for index in range(count):
        if not continues[(index - 1) % count]:
            start = index
            break
    runs = []
    index = start
    for _step in range(count):
        end = index
        while continues[end]:
            nxt = (end + 1) % count
            if nxt == index:
                break
            end = nxt
        run_end = (end + 1) % count
        if not _near(ring[index], ring[run_end], 1e-12):
            runs.append((ring[index], ring[run_end]))
        nxt = (end + 1) % count
        if nxt == start:
            break
        index = nxt
    return runs


def _gap_overlap(ring_a, ring_b):
    """Longest parallel overlap that realizes the minimum separation.

    A ring inside the other is a piece in a hole, not a gap.
    """
    if _ring_sits_inside(ring_a, ring_b) or _ring_sits_inside(ring_b, ring_a):
        return None
    min_d = None
    best = None
    runs_a = _straight_runs(ring_a)
    runs_b = _straight_runs(ring_b)
    for a0, a1 in runs_a:
        for b0, b1 in runs_b:
            overlap = _parallel_overlap(a0, a1, b0, b1)
            if overlap is not None:
                dist, length = overlap[0], overlap[1]
                if best is None or dist < best[0] - 1e-6 or (
                    abs(dist - best[0]) <= 1e-4 and length > best[1]
                ):
                    best = overlap
    count_a = len(ring_a)
    count_b = len(ring_b)
    for index_a in range(count_a):
        a0 = ring_a[index_a]
        a1 = ring_a[(index_a + 1) % count_a]
        for index_b in range(count_b):
            b0 = ring_b[index_b]
            b1 = ring_b[(index_b + 1) % count_b]
            for point, start, end in (
                (a0, b0, b1),
                (b0, a0, a1),
            ):
                dist = _point_segment_distance(point, start, end)
                if min_d is None or dist < min_d:
                    min_d = dist
    if best is None or min_d is None:
        return None
    if best[0] > min_d + 1e-3 or best[1] <= 1e-3:
        return None
    return best


def _ring_segments(ring):
    count = len(ring)
    return [
        (ring[index], ring[(index + 1) % count])
        for index in range(count)
    ]


def _ring_sits_inside(outer, inner):
    """True when ``inner`` lies in ``outer``."""
    if len(inner) < 3 or len(outer) < 3:
        return False
    if abs(_ring_area(inner)) >= abs(_ring_area(outer)):
        return False
    left = min(point[0] for point in outer)
    bottom = min(point[1] for point in outer)
    right = max(point[0] for point in outer)
    top = max(point[1] for point in outer)
    for point in inner:
        if (
            point[0] < left - 1e-6
            or point[0] > right + 1e-6
            or point[1] < bottom - 1e-6
            or point[1] > top + 1e-6
        ):
            return False
    segments = _ring_segments(outer)
    for point in inner:
        if _distance_to_segments(point, segments) <= 1e-4:
            continue
        if not _point_inside_ring(point, outer):
            return False
    return True


def _point_inside_ring(point, ring):
    if _distance_to_segments(point, _ring_segments(ring)) <= 1e-4:
        return False
    x, y = point
    inside = False
    count = len(ring)
    for index in range(count):
        x0, y0 = ring[index]
        x1, y1 = ring[(index + 1) % count]
        if (y0 > y) == (y1 > y):
            continue
        cross_x = (x1 - x0) * (y - y0) / (y1 - y0) + x0
        if x < cross_x:
            inside = not inside
    return inside


def _min_ring_distance(ring_a, ring_b):
    best = None
    segments = _ring_segments(ring_b)
    for point in ring_a:
        dist = _distance_to_segments(point, segments)
        if best is None or dist < best:
            best = dist
    segments = _ring_segments(ring_a)
    for point in ring_b:
        dist = _distance_to_segments(point, segments)
        if best is None or dist < best:
            best = dist
    if best is None:
        return 0.0
    return best


def _straight_side(points, index):
    """A real offset side, including one shorter than the old cutoff of 1.

    Arc chords match their neighbors. A unit side can measure just under 1.
    """
    count = len(points)
    start = points[index]
    end = points[(index + 1) % count]
    length = math.hypot(end[0] - start[0], end[1] - start[1])
    if length <= 1e-8:
        return False
    if abs(_signed_turn(points, index)) >= _SHARP_TURN:
        return True
    if abs(_signed_turn(points, (index + 1) % count)) >= _SHARP_TURN:
        return True
    if length >= 1.0 - 1e-6:
        return True
    prev = points[(index - 1) % count]
    nxt = points[(index + 2) % count]
    prev_len = math.hypot(start[0] - prev[0], start[1] - prev[1])
    next_len = math.hypot(nxt[0] - end[0], nxt[1] - end[1])
    return length > prev_len * 2.0 and length > next_len * 2.0


def _side_samples(start, end):
    """Points on the side, including a step in from each end.

    Whole-unit steps miss a free end shorter than that step.
    """
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.hypot(dx, dy)
    if length <= 1e-12:
        return
    inset = min(0.05, length * 0.25)
    fractions = [inset / length, 0.5, 1.0 - inset / length]
    steps = int(math.ceil(length))
    for step in range(1, steps):
        fractions.append(step / float(steps))
    for fraction in fractions:
        yield (
            start[0] + dx * fraction,
            start[1] + dy * fraction,
        )


def _boundary_hidden(merged, ring_a, ring_b):
    """A straight offset that does not face the gap fell inside.

    Corner arcs inside an external tangent are the smooth outline.
    A straight side inside that tangent is the step the hull cut off.
    """
    if not merged or len(merged) < 3:
        return False
    limit = _min_ring_distance(ring_a, ring_b) + 1e-3
    for ring, other in ((ring_a, ring_b), (ring_b, ring_a)):
        other_segments = _ring_segments(other)
        count = len(ring)
        for index in range(count):
            if not _straight_side(ring, index):
                continue
            start = ring[index]
            end = ring[(index + 1) % count]
            for point in _side_samples(start, end):
                if _distance_to_segments(point, other_segments) <= limit:
                    continue
                if _point_inside_ring(point, merged):
                    return True
    return False


def _insert_points(ring, extras):
    """Ring with boundary points inserted, and each extra's index."""
    count = len(ring)
    on_vertex = {}
    additions = [[] for _index in range(count)]
    for extra_index, point in enumerate(extras):
        found = None
        for index in range(count):
            start = ring[index]
            end = ring[(index + 1) % count]
            dist = _point_segment_distance(point, start, end)
            if dist > 1e-4:
                continue
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            length_sq = dx * dx + dy * dy
            if length_sq <= 1e-18:
                t = 0.0
            else:
                t = (
                    (point[0] - start[0]) * dx + (point[1] - start[1]) * dy
                ) / length_sq
            if t < -1e-5 or t > 1.0 + 1e-5:
                continue
            found = (index, max(0.0, min(1.0, t)))
            break
        if found is None:
            return None
        edge, t = found
        if t <= 1e-6:
            on_vertex[extra_index] = edge
        elif t >= 1.0 - 1e-6:
            on_vertex[extra_index] = (edge + 1) % count
        else:
            additions[edge].append((t, extra_index))
    new_ring = []
    origin_at = {}
    extra_at = {}
    for index in range(count):
        origin_at[index] = len(new_ring)
        new_ring.append(ring[index])
        start = ring[index]
        end = ring[(index + 1) % count]
        for t, extra_index in sorted(additions[index]):
            new_ring.append((
                start[0] + (end[0] - start[0]) * t,
                start[1] + (end[1] - start[1]) * t,
            ))
            extra_at[extra_index] = len(new_ring) - 1
    for extra_index, index in on_vertex.items():
        extra_at[extra_index] = origin_at[index]
    if len(extra_at) != len(extras):
        return None
    return new_ring, extra_at


def _span_points(ring_a, ring_b):
    overlap = _gap_overlap(ring_a, ring_b)
    if overlap is None:
        return None
    _dist, _length, p0, q0, p1, q1 = overlap
    placed_a = _insert_points(ring_a, [p0, p1])
    placed_b = _insert_points(ring_b, [q0, q1])
    if placed_a is None or placed_b is None:
        return None
    ring_a, index_a = placed_a
    ring_b, index_b = placed_b
    if index_a[0] == index_a[1] or index_b[0] == index_b[1]:
        return None
    bridges = {
        index_a[0]: index_b[0],
        index_a[1]: index_b[1],
    }
    return _assemble_gap(ring_a, ring_b, bridges)


def _dilate(subject, distance):
    scale = _CLIP_SCALE
    scaled = QTransform().scale(scale, scale).map(subject)
    scaled.setFillRule(subject.fillRule())
    stroker = QPainterPathStroker()
    stroker.setWidth(2.0 * distance * scale)
    stroker.setJoinStyle(Qt.RoundJoin)
    stroker.setCapStyle(Qt.RoundCap)
    stroker.setCurveThreshold(_CURVE_FLATNESS)
    stroke = stroker.createStroke(scaled)
    expanded = scaled.united(stroke).simplified()
    expanded.setFillRule(Qt.OddEvenFill)
    return QTransform().scale(1.0 / scale, 1.0 / scale).map(expanded)


def _meeting_outers(subject):
    """Outer boundary of each cluster when the distance is zero.

    Sibling pieces share one winding-fill simplify, so a meet or an
    overlap becomes that union. A zero stroke leaves the overlap
    empty, and a pairwise union repeats a boolean per piece. One
    piece is returned as drawn. A piece in a hole is its own group.
    """
    loops, _depths = _nested_loops(subject)
    depths = _strict_depths(loops)
    groups = {}
    for index, (subpath, _area, point) in enumerate(loops):
        if depths[index] % 2 != 0:
            continue
        parent = _parent_index(loops, depths, index, point)
        groups.setdefault(parent, []).append(subpath)
    outers = []
    for group in groups.values():
        outers.extend(_winding_union(group))
    return outers


def _strict_depths(loops):
    """Nest only a loop that sits inside a larger one.

    One interior probe lands in an overlap and would hide the piece
    that still sticks out. Vertices and an edge sample have to be in.
    """
    depths = []
    for index, (subpath, area, point) in enumerate(loops):
        depth = 0
        for other, (outline, other_area, _other_point) in enumerate(loops):
            if other == index or other_area <= area:
                continue
            if _loop_inside(outline, subpath, point):
                depth += 1
        depths.append(depth)
    return depths


def _parent_index(loops, depths, index, point):
    depth = depths[index]
    if depth == 0:
        return -1
    subpath = loops[index][0]
    parent = -1
    parent_area = None
    for other, (outline, other_area, _other_point) in enumerate(loops):
        if depths[other] != depth - 1:
            continue
        if not _loop_inside(outline, subpath, point):
            continue
        if parent_area is None or other_area < parent_area:
            parent = other
            parent_area = other_area
    return parent


def _loop_inside(outer, inner, inner_point):
    if not outer.contains(inner_point):
        return False
    for kind, points in _segments(inner):
        for vertex in (points[0], points[-1]):
            if not outer.contains(QPointF(vertex[0], vertex[1])):
                return False
        sample = _edge_sample(kind, points)
        if sample is None:
            continue
        if not outer.contains(QPointF(sample[0], sample[1])):
            return False
    return True


def _winding_union(loops):
    if len(loops) == 1:
        return loops
    combined = QPainterPath()
    combined.setFillRule(Qt.WindingFill)
    for loop in loops:
        piece = loop
        if _signed_area(loop) < 0.0:
            piece = _reversed_closed(loop)
        combined.addPath(piece)
    merged = combined.simplified()
    outers = _outer_boundaries(merged)
    if not outers:
        return loops
    return outers


def _reversed_closed(path):
    commands = []
    for kind, points in _segments(path):
        commands.append((kind, points))
    if not commands:
        return path
    reversed_path = QPainterPath()
    end = commands[-1][1][-1]
    reversed_path.moveTo(end[0], end[1])
    for kind, points in reversed(commands):
        start = points[0]
        if kind == 'line':
            reversed_path.lineTo(start[0], start[1])
        elif kind == 'quad':
            control = points[1]
            reversed_path.quadTo(control[0], control[1], start[0], start[1])
        else:
            reversed_path.cubicTo(
                points[2][0], points[2][1],
                points[1][0], points[1][1],
                start[0], start[1],
            )
    reversed_path.closeSubpath()
    return reversed_path


def _outer_boundaries(path):
    """Even-depth outlines. A hole in a curve is not one of them.

    A flattened chord sits inside its curve, so a hole vertex in that
    gap is outside the polygon and still inside the subject. Nest by
    a point the subpath contains. Only a larger outline counts.
    """
    loops, depths = _nested_loops(path)
    return [
        subpath
        for (subpath, _area, _point), depth in zip(loops, depths)
        if depth % 2 == 0
    ]


def _nested_loops(path):
    """Closed subpaths with area, an interior point, and nest depth."""
    loops = []
    for subpath in _closed_subpaths(path):
        area = abs(_signed_area(subpath))
        if area <= _AREA_EPS:
            continue
        point = _contained_point(subpath)
        if point is None:
            continue
        loops.append((subpath, area, point))

    depths = []
    for index, (_subpath, area, point) in enumerate(loops):
        depth = 0
        for other, (outline, other_area, _other_point) in enumerate(loops):
            if other == index or other_area <= area:
                continue
            if outline.contains(point):
                depth += 1
        depths.append(depth)
    return loops, depths


def _closed_subpaths(path):
    return [
        subpath for subpath in split_painter_path(path)
        if _is_closed(subpath)
    ]


def _is_closed(subpath):
    count = subpath.elementCount()
    if count < 4:
        return False
    first = subpath.elementAt(0)
    last = subpath.elementAt(count - 1)
    return (
        abs(first.x - last.x) <= _CLOSED_TOL
        and abs(first.y - last.y) <= _CLOSED_TOL
    )


def _segments(path):
    """Line, quad, and cubic segments as ``(kind, points)``."""
    move_to = QPainterPath.MoveToElement
    line_to = QPainterPath.LineToElement
    curve_to = QPainterPath.CurveToElement
    curve_data = QPainterPath.CurveToDataElement
    current = None
    index = 0
    count = path.elementCount()
    while index < count:
        element = path.elementAt(index)
        if element.type == move_to:
            current = (element.x, element.y)
            index += 1
            continue
        if element.type == line_to:
            end = (element.x, element.y)
            if current is not None:
                yield ('line', (current, end))
            current = end
            index += 1
            continue
        if element.type != curve_to or current is None:
            index += 1
            continue
        if index + 1 >= count or path.elementAt(index + 1).type != curve_data:
            index += 1
            continue
        control = (element.x, element.y)
        follow = path.elementAt(index + 1)
        if index + 2 < count and path.elementAt(index + 2).type == curve_data:
            end_element = path.elementAt(index + 2)
            end = (end_element.x, end_element.y)
            yield ('cubic', (current, control, (follow.x, follow.y), end))
            current = end
            index += 3
            continue
        end = (follow.x, follow.y)
        yield ('quad', (current, control, end))
        current = end
        index += 2


def _signed_area(path):
    """Algebraic area from the path elements, not from chord vertices."""
    area = 0.0
    start = None
    current = None
    for kind, points in _segments(path):
        if start is None:
            start = points[0]
        current = points[-1]
        area += _segment_area(kind, points)
    if start is None or current is None:
        return 0.0
    if (
        abs(start[0] - current[0]) > _CLOSED_TOL
        or abs(start[1] - current[1]) > _CLOSED_TOL
    ):
        area += _segment_area('line', (current, start))
    return area


def _segment_area(kind, points):
    if kind == 'line':
        return _line_integral(points[0], points[1])
    if kind == 'quad':
        return _polynomial_integral(
            _quad_coeffs(points[0][0], points[1][0], points[2][0]),
            _quad_coeffs(points[0][1], points[1][1], points[2][1]),
        )
    return _polynomial_integral(
        _cubic_coeffs(
            points[0][0], points[1][0], points[2][0], points[3][0]),
        _cubic_coeffs(
            points[0][1], points[1][1], points[2][1], points[3][1]),
    )


def _line_integral(start, end):
    # ∫ x dy along the segment. Closed loops make this the signed area.
    return (start[0] + end[0]) * (end[1] - start[1]) * 0.5


def _quad_coeffs(p0, p1, p2):
    return (
        0.0,
        p0 - 2.0 * p1 + p2,
        2.0 * (p1 - p0),
        p0,
    )


def _cubic_coeffs(p0, p1, p2, p3):
    return (
        -p0 + 3.0 * p1 - 3.0 * p2 + p3,
        3.0 * (p0 - 2.0 * p1 + p2),
        3.0 * (p1 - p0),
        p0,
    )


def _polynomial_integral(x_coeff, y_coeff):
    """∫ x dy for x(t), y(t) on t in [0, 1]."""
    a, b, c, d = x_coeff
    cubic, quad, linear, _constant = y_coeff
    return (
        a * cubic / 2.0
        + (2.0 * a * quad + 3.0 * b * cubic) / 5.0
        + (
            a * linear / 4.0
            + b * quad / 2.0
            + 3.0 * c * cubic / 4.0
        )
        + (b * linear / 3.0 + 2.0 * c * quad / 3.0 + d * cubic)
        + (c * linear / 2.0 + d * quad)
        + d * linear
    )


def _contained_point(subpath):
    """A point ``subpath.contains`` accepts, off the chord vertices."""
    rect = subpath.boundingRect()
    span = max(rect.width(), rect.height(), 1e-6)
    scales = (
        1e-4, 1e-3, 0.01, 0.05,
        span * 1e-4, span * 1e-3, span * 0.01, span * 0.05,
    )
    for kind, points in _segments(subpath):
        sample = _edge_sample(kind, points)
        if sample is None:
            continue
        mx, my, tx, ty = sample
        length = math.hypot(tx, ty)
        if length <= _TANGENT_EPS:
            continue
        nx = -ty / length
        ny = tx / length
        for scale in scales:
            for sign in (1.0, -1.0):
                probe = QPointF(mx + sign * nx * scale, my + sign * ny * scale)
                if subpath.contains(probe):
                    return probe
    for row in range(1, 16):
        for column in range(1, 16):
            probe = QPointF(
                rect.left() + rect.width() * column / 16.0,
                rect.top() + rect.height() * row / 16.0,
            )
            if subpath.contains(probe):
                return probe
    center = rect.center()
    if subpath.contains(center):
        return center
    return None


def _edge_sample(kind, points):
    if kind == 'line':
        start, end = points
        return (
            0.5 * (start[0] + end[0]),
            0.5 * (start[1] + end[1]),
            end[0] - start[0],
            end[1] - start[1],
        )
    if kind == 'quad':
        p0, p1, p2 = points
        return (
            0.25 * p0[0] + 0.5 * p1[0] + 0.25 * p2[0],
            0.25 * p0[1] + 0.5 * p1[1] + 0.25 * p2[1],
            p2[0] - p0[0],
            p2[1] - p0[1],
        )
    p0, p1, p2, p3 = points
    return (
        0.125 * p0[0] + 0.375 * p1[0] + 0.375 * p2[0] + 0.125 * p3[0],
        0.125 * p0[1] + 0.375 * p1[1] + 0.375 * p2[1] + 0.125 * p3[1],
        (
            0.75 * (p1[0] - p0[0])
            + 1.5 * (p2[0] - p1[0])
            + 0.75 * (p3[0] - p2[0])
        ),
        (
            0.75 * (p1[1] - p0[1])
            + 1.5 * (p2[1] - p1[1])
            + 0.75 * (p3[1] - p2[1])
        ),
    )


def _components(subject):
    """Even outlines, each with the holes it directly owns."""
    loops, depths = _nested_loops(subject)
    components = []
    for index, (subpath, _area, _point) in enumerate(loops):
        if depths[index] % 2 != 0:
            continue
        path = QPainterPath()
        path.setFillRule(Qt.OddEvenFill)
        path.addPath(subpath)
        path.closeSubpath()
        for other, (hole, _hole_area, hole_point) in enumerate(loops):
            if depths[other] != depths[index] + 1:
                continue
            if not subpath.contains(hole_point):
                continue
            path.addPath(hole)
            path.closeSubpath()
        components.append(path)
    return components


def _boundary_segments(path):
    segments = []
    for subpath in _closed_subpaths(path):
        for kind, points in _segments(subpath):
            if kind == 'line':
                segments.append(points)
    return segments


def _ring_area(points):
    area = 0.0
    previous = points[-1]
    for point in points:
        area += previous[0] * point[1] - point[0] * previous[1]
        previous = point
    return area * 0.5


def _ring_points(path):
    """Vertices of a flattened loop, counterclockwise, without the repeat."""
    points = []
    for _kind, segment in _segments(path):
        if not points:
            points.append(segment[0])
        end = segment[-1]
        if math.hypot(end[0] - points[-1][0], end[1] - points[-1][1]) > 1e-9:
            points.append(end)
    if (
        len(points) >= 2
        and math.hypot(points[0][0] - points[-1][0], points[0][1] - points[-1][1])
        <= _CLOSED_TOL
    ):
        points.pop()
    if len(points) < 3:
        return []
    if _ring_area(points) < 0.0:
        points.reverse()
    return points


def _cumulative(points):
    lengths = [0.0]
    for index in range(len(points) - 1):
        start = points[index]
        end = points[index + 1]
        lengths.append(lengths[-1] + math.hypot(end[0] - start[0], end[1] - start[1]))
    total = lengths[-1] + math.hypot(
        points[0][0] - points[-1][0], points[0][1] - points[-1][1])
    return lengths, total


def _walk(points, start, distance, direction):
    """A point ``distance`` along the ring, and the forward tangent there."""
    count = len(points)
    remaining = distance
    index = start
    for _step in range(count + 1):
        if direction > 0:
            begin = points[index % count]
            end = points[(index + 1) % count]
        else:
            end = points[index % count]
            begin = points[(index - 1) % count]
        dx = end[0] - begin[0]
        dy = end[1] - begin[1]
        length = math.hypot(dx, dy)
        if length <= _TANGENT_EPS:
            index += direction
            continue
        if remaining <= length + 1e-9:
            tangent = (dx / length, dy / length)
            scale = remaining / length
            if direction > 0:
                point = (begin[0] + dx * scale, begin[1] + dy * scale)
            else:
                point = (end[0] - dx * scale, end[1] - dy * scale)
            return point, tangent
        remaining -= length
        index += direction
    return None


def _rotate_cw(x, y, phi):
    cosine = math.cos(phi)
    sine = math.sin(phi)
    return (x * cosine + y * sine, -x * sine + y * cosine)


def _distance_to_segments(point, segments):
    px, py = point
    best = None
    for start, end in segments:
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length_sq = dx * dx + dy * dy
        if length_sq <= 1e-18:
            dist = math.hypot(px - start[0], py - start[1])
        else:
            scale = ((px - start[0]) * dx + (py - start[1]) * dy) / length_sq
            if scale < 0.0:
                scale = 0.0
            elif scale > 1.0:
                scale = 1.0
            dist = math.hypot(px - (start[0] + scale * dx), py - (start[1] + scale * dy))
        if best is None or dist < best:
            best = dist
    if best is None:
        return 0.0
    return best


def _near(first, second, tol):
    return math.hypot(first[0] - second[0], first[1] - second[1]) <= tol


def _signed_turn(points, index):
    count = len(points)
    previous = points[(index - 1) % count]
    point = points[index]
    nxt = points[(index + 1) % count]
    first = (point[0] - previous[0], point[1] - previous[1])
    second = (nxt[0] - point[0], nxt[1] - point[1])
    left = math.hypot(first[0], first[1])
    right = math.hypot(second[0], second[1])
    if left <= _TANGENT_EPS or right <= _TANGENT_EPS:
        return 0.0
    dot = (first[0] * second[0] + first[1] * second[1]) / (left * right)
    cross = (first[0] * second[1] - first[1] * second[0]) / (left * right)
    dot = max(-1.0, min(1.0, dot))
    return math.degrees(math.atan2(cross, dot))


def _clockwise_angle(start, end):
    cross = start[0] * end[1] - start[1] * end[0]
    dot = start[0] * end[0] + start[1] * end[1]
    clockwise = -math.atan2(cross, dot)
    if clockwise < 0.0:
        clockwise += 2.0 * math.pi
    return clockwise


def _sharp_gap(points, index, sharp):
    """Arc length along the ring to the nearest other sharp corner."""
    count = len(points)
    best = None
    for direction in (1, -1):
        total = 0.0
        current = index
        for _step in range(count):
            nxt = (current + direction) % count
            total += math.hypot(
                points[nxt][0] - points[current][0],
                points[nxt][1] - points[current][1],
            )
            if nxt == index or nxt in sharp:
                break
            current = nxt
        if best is None or total < best:
            best = total
    if best is None:
        return 0.0
    return best


def _center_pair(points, index, back_a, back_b, radius):
    incoming = _walk(points, index, back_a, -1)
    outgoing = _walk(points, index, back_b, 1)
    if incoming is None or outgoing is None:
        return None
    (ax, ay), (tax, tay) = incoming
    (bx, by), (tbx, tby) = outgoing
    center_a = (ax + tay * radius, ay - tax * radius)
    center_b = (bx + tby * radius, by - tbx * radius)
    err = math.hypot(center_a[0] - center_b[0], center_a[1] - center_b[1])
    center = (
        0.5 * (center_a[0] + center_b[0]),
        0.5 * (center_a[1] + center_b[1]),
    )
    return err, (ax, ay), (bx, by), center


def _fillet_arc(center, start, end):
    toward_start = (start[0] - center[0], start[1] - center[1])
    toward_end = (end[0] - center[0], end[1] - center[1])
    phi = _clockwise_angle(toward_start, toward_end)
    # A single corner sweeps less than half a turn. A chain of
    # parallel walls meets on a semicircle, which is included.
    # Anything longer is the long way around the center.
    if phi <= 1e-3 or phi > math.pi + 1e-3:
        return None
    count = max(2, int(math.ceil(phi / _ARC_STEP - 1e-12)))
    points = [start]
    for step in range(1, count):
        angle = phi * step / float(count)
        rx, ry = _rotate_cw(toward_start[0], toward_start[1], angle)
        points.append((center[0] + rx, center[1] + ry))
    points.append(end)
    return points


def _arc_stays_out(arc, dilated):
    boundary = _boundary_segments(dilated)
    for point in arc[1:-1]:
        if not dilated.contains(QPointF(point[0], point[1])):
            continue
        if _distance_to_segments(point, boundary) > 0.05:
            return False
    return True


def _fit_fillet(points, index, radius, max_back, dilated):
    best = None
    back = 0.05
    while back <= max_back + 1e-9:
        got = _center_pair(points, index, back, back, radius)
        if got is None:
            break
        err = got[0]
        if best is None or err < best[0]:
            best = (err, back, back, got)
        if err < 1e-4:
            break
        back += 0.05
    if best is None:
        return None
    err, back_a, back_b, got = best
    base_a = back_a
    base_b = back_b
    for step_a in range(-12, 13):
        for step_b in range(-12, 13):
            trial_a = base_a + step_a * 0.01
            trial_b = base_b + step_b * 0.01
            if trial_a <= 0.02 or trial_b <= 0.02:
                continue
            if trial_a > max_back + 1e-9 or trial_b > max_back + 1e-9:
                continue
            trial = _center_pair(points, index, trial_a, trial_b, radius)
            if trial is None or trial[0] >= err:
                continue
            err = trial[0]
            back_a = trial_a
            back_b = trial_b
            got = trial
    if err > _FILLET_ERR:
        return None
    _err, start, end, center = got
    start_radius = math.hypot(start[0] - center[0], start[1] - center[1])
    end_radius = math.hypot(end[0] - center[0], end[1] - center[1])
    if abs(start_radius - radius) > 0.05 or abs(end_radius - radius) > 0.05:
        return None
    arc = _fillet_arc(center, start, end)
    if arc is None or not _arc_stays_out(arc, dilated):
        return None
    return {
        'index': index,
        'back_a': back_a,
        'back_b': back_b,
        'arc': arc,
        'mid': arc[len(arc) // 2],
        'corner': points[index],
    }


def _fillet_record(index, back_a, back_b, arc, corner):
    return {
        'index': index,
        'back_a': back_a,
        'back_b': back_b,
        'arc': arc,
        'mid': arc[len(arc) // 2],
        'corner': corner,
    }


def _junction_angles(incoming, outgoing, arc):
    """Vertex angles where the arc meets the outline tangents."""
    (_ax, _ay), (tax, tay) = incoming
    (_bx, _by), (tbx, tby) = outgoing
    first = (arc[1][0] - arc[0][0], arc[1][1] - arc[0][1])
    last = (arc[-1][0] - arc[-2][0], arc[-1][1] - arc[-2][1])

    def angle(left, right):
        left_len = math.hypot(left[0], left[1])
        right_len = math.hypot(right[0], right[1])
        if left_len <= _TANGENT_EPS or right_len <= _TANGENT_EPS:
            return 0.0
        dot = (left[0] * right[0] + left[1] * right[1]) / (left_len * right_len)
        dot = max(-1.0, min(1.0, dot))
        return math.degrees(math.acos(dot))

    at_start = angle((-tax, -tay), first)
    at_end = angle((-last[0], -last[1]), (tbx, tby))
    return at_start, at_end


def _candidate_fillet(points, index, radius, dilated, back_a, back_b, loose):
    """A fillet for these setbacks, or None when it misses the outline."""
    got = _center_pair(points, index, back_a, back_b, radius)
    if got is None:
        return None
    err, start, end, center = got
    start_radius = math.hypot(start[0] - center[0], start[1] - center[1])
    end_radius = math.hypot(end[0] - center[0], end[1] - center[1])
    if min(start_radius, end_radius) < radius - 0.05:
        return None
    if abs(start_radius - radius) > (0.12 if loose else 0.05):
        return None
    if abs(end_radius - radius) > (0.12 if loose else 0.05):
        return None
    arc = _fillet_arc(center, start, end)
    if arc is None or not _arc_stays_out(arc, dilated):
        return None
    incoming = _walk(points, index, back_a, -1)
    outgoing = _walk(points, index, back_b, 1)
    if incoming is None or outgoing is None:
        return None
    at_start, at_end = _junction_angles(incoming, outgoing, arc)
    # A step under about 30 degrees still counts as smooth.
    if loose and (at_start < 150.0 or at_end < 150.0):
        return None
    return _fillet_record(index, back_a, back_b, arc, points[index]), err


def _fit_fillet_loose(points, index, radius, max_back, dilated):
    """Wider setbacks for a crossing the equal-back search cannot seat.

    Unequal sides miss by more than the tight center tolerance. The
    turn is still owed, including when that miss stays above 0.05.
    """
    if max_back <= 0.05:
        return None
    best = None
    step = 0.2
    back = 0.1
    grid = []
    while back <= max_back + 1e-9:
        grid.append(back)
        back += step
    for back_a in grid:
        for back_b in grid:
            got = _center_pair(points, index, back_a, back_b, radius)
            if got is None:
                continue
            if best is None or got[0] < best[0]:
                best = (got[0], back_a, back_b)
    if best is None:
        return None
    err, back_a, back_b = best
    for step_a in range(-10, 11):
        for step_b in range(-10, 11):
            trial_a = back_a + step_a * 0.02
            trial_b = back_b + step_b * 0.02
            if trial_a <= 0.02 or trial_b <= 0.02:
                continue
            if trial_a > max_back + 1e-9 or trial_b > max_back + 1e-9:
                continue
            trial = _center_pair(points, index, trial_a, trial_b, radius)
            if trial is None or trial[0] >= err:
                continue
            err = trial[0]
            back_a = trial_a
            back_b = trial_b
    # Nearby setbacks can seat a center the coarse grid only approached.
    found = None
    for step_a in range(-6, 7):
        for step_b in range(-6, 7):
            trial_a = back_a + step_a * 0.02
            trial_b = back_b + step_b * 0.02
            if trial_a <= 0.02 or trial_b <= 0.02:
                continue
            if trial_a > max_back + 1e-9 or trial_b > max_back + 1e-9:
                continue
            seated = _candidate_fillet(
                points, index, radius, dilated, trial_a, trial_b, True)
            if seated is None:
                continue
            record, seat_err = seated
            if found is None or seat_err < found[0]:
                found = (seat_err, record)
    if found is None or found[0] > 0.35:
        return None
    return found[1]


def _forward_span(points, start, end):
    """Arc length from ``start`` to ``end`` along the ring."""
    lengths, total = _cumulative(points)
    if end >= start:
        return lengths[end] - lengths[start], total
    return total - lengths[start] + lengths[end], total


def _close_chains(points, failed, radius):
    """Runs of reflex corners too close for a setback each."""
    ordered = sorted(set(failed))
    count = len(ordered)
    if count < 2:
        return []
    limit = 2.0 * radius
    small = []
    for index, corner in enumerate(ordered):
        nxt = ordered[(index + 1) % count]
        gap, _total = _forward_span(points, corner, nxt)
        small.append(gap <= limit + 1e-6)
    if not any(small) or all(small):
        return []
    chains = []
    seen = [False] * count
    for index in range(count):
        if seen[index] or not small[index]:
            continue
        start = index
        while small[(start - 1) % count]:
            start = (start - 1) % count
            if start == index:
                break
        run = [ordered[start]]
        cursor = start
        seen[cursor] = True
        while small[cursor]:
            cursor = (cursor + 1) % count
            run.append(ordered[cursor])
            seen[cursor] = True
            if cursor == start:
                break
        if len(run) >= 2:
            chains.append(run)
    return chains


def _bridge_chain(points, chain, radius, dilated):
    """One turn of radius ``radius`` in place of a tight reflex chain.

    The setbacks walk out until both normals meet on that circle.
    Parallel walls closer than two radii meet only once the outline
    opens up, so the straight run between the corners is replaced
    along with them.
    """
    start_index = chain[0]
    end_index = chain[-1]
    chain_len, total = _forward_span(points, start_index, end_index)
    if chain_len <= 1e-6 or chain_len > total * 0.5:
        return None
    limit = min(total * 0.45, chain_len + 40.0 * radius)
    best = None
    back = 0.5
    while back <= limit + 1e-9:
        incoming = _walk(points, start_index, back, -1)
        outgoing = _walk(points, end_index, back, 1)
        if incoming is None or outgoing is None:
            break
        (_ax, _ay), (tax, tay) = incoming
        (_bx, _by), (tbx, tby) = outgoing
        center_a = (_ax + tay * radius, _ay - tax * radius)
        center_b = (_bx + tby * radius, _by - tbx * radius)
        err = math.hypot(center_a[0] - center_b[0], center_a[1] - center_b[1])
        if best is None or err < best[0]:
            best = (err, back, incoming, outgoing, center_a, center_b)
        if err < 0.02:
            break
        back += 0.25
    if best is None:
        return None
    err, back, incoming, outgoing, center_a, center_b = best
    # Refine both sides. The opening is symmetric on a U and is not
    # on a diagonal notch, so each side keeps its own setback.
    back_a = back
    back_b = back
    for _pass in range(2):
        step = 0.05 if _pass == 0 else 0.01
        for step_a in range(-8, 9):
            for step_b in range(-8, 9):
                trial_a = back_a + step_a * step
                trial_b = back_b + step_b * step
                if trial_a <= 0.05 or trial_b <= 0.05 or trial_a > limit or trial_b > limit:
                    continue
                trial_in = _walk(points, start_index, trial_a, -1)
                trial_out = _walk(points, end_index, trial_b, 1)
                if trial_in is None or trial_out is None:
                    continue
                (ax, ay), (tax, tay) = trial_in
                (bx, by), (tbx, tby) = trial_out
                trial_center_a = (ax + tay * radius, ay - tax * radius)
                trial_center_b = (bx + tby * radius, by - tbx * radius)
                trial_err = math.hypot(
                    trial_center_a[0] - trial_center_b[0],
                    trial_center_a[1] - trial_center_b[1],
                )
                if trial_err + 1e-9 < err:
                    err = trial_err
                    back_a = trial_a
                    back_b = trial_b
                    incoming = trial_in
                    outgoing = trial_out
                    center_a = trial_center_a
                    center_b = trial_center_b
    if err > 0.12:
        return None
    (ax, ay), _tangent_a = incoming
    (bx, by), _tangent_b = outgoing
    center = (
        0.5 * (center_a[0] + center_b[0]),
        0.5 * (center_a[1] + center_b[1]),
    )
    arc = _fillet_arc(center, (ax, ay), (bx, by))
    if arc is None or not _arc_stays_out(arc, dilated):
        return None
    at_start, at_end = _junction_angles(incoming, outgoing, arc)
    if at_start < 150.0 or at_end < 150.0:
        return None
    corner = (
        0.5 * (points[start_index][0] + points[end_index][0]),
        0.5 * (points[start_index][1] + points[end_index][1]),
    )
    return _fillet_record(start_index, back_a, chain_len + back_b, arc, corner)


def _span_inside(length, start, end):
    if start <= end:
        return start + 1e-7 < length < end - 1e-7
    return length > start + 1e-7 or length < end - 1e-7


def _apply_fillets(points, fillets):
    lengths, total = _cumulative(points)
    spans = []
    for fillet in fillets:
        pos = lengths[fillet['index']]
        start = (pos - fillet['back_a']) % total
        end = (pos + fillet['back_b']) % total
        spans.append((start, end, fillet))
    seam = None
    for length in lengths:
        if not any(_span_inside(length, start, end) for start, end, _fillet in spans):
            seam = length
            break
    if seam is None:
        return None

    def unwrap(length):
        return (length - seam) % total

    open_spans = []
    for start, end, fillet in spans:
        start_u = unwrap(start)
        end_u = unwrap(end)
        if start_u >= end_u:
            return None
        open_spans.append((start_u, end_u, fillet))

    def covered(length):
        for start, end, _fillet in open_spans:
            if start + 1e-7 < length < end - 1e-7:
                return True
        return False

    events = []
    for index, length in enumerate(lengths):
        position = unwrap(length)
        if covered(position):
            continue
        events.append((position, 1, points[index]))
    for start, _end, fillet in open_spans:
        events.append((start, 0, fillet))
    events.sort(key=lambda item: (item[0], item[1]))

    output = []
    attachments = []

    def push(point):
        if output and _near(output[-1], point, 1e-8):
            return len(output) - 1
        output.append((point[0], point[1]))
        return len(output) - 1

    for _pos, kind, payload in events:
        if kind == 1:
            push(payload)
            continue
        mid_at = None
        for point in payload['arc']:
            index = push(point)
            if mid_at is None and _near(point, payload['mid'], 1e-6):
                mid_at = index
        if mid_at is None:
            mid_at = push(payload['mid'])
        attachments.append((payload['corner'], mid_at))
    if len(output) >= 2 and _near(output[0], output[-1], 1e-8):
        output.pop()
        fixed = []
        for corner, index in attachments:
            if index >= len(output):
                index = 0
            fixed.append((corner, index))
        attachments = fixed
    if len(output) < 3:
        return None
    return output, attachments


def _closed_path(points):
    cleaned = [points[0]]
    for point in points[1:]:
        if not _near(cleaned[-1], point, 1e-8):
            cleaned.append(point)
    if len(cleaned) >= 2 and _near(cleaned[0], cleaned[-1], 1e-8):
        cleaned.pop()
    if len(cleaned) < 3:
        return None
    path = QPainterPath()
    path.moveTo(cleaned[0][0], cleaned[0][1])
    for point in cleaned[1:]:
        path.lineTo(point[0], point[1])
    path.closeSubpath()
    return path


def _edges_colinear(points, first, second):
    count = len(points)
    a0 = points[first]
    a1 = points[(first + 1) % count]
    b0 = points[second]
    b1 = points[(second + 1) % count]
    adx = a1[0] - a0[0]
    ady = a1[1] - a0[1]
    bdx = b1[0] - b0[0]
    bdy = b1[1] - b0[1]
    length_a = math.hypot(adx, ady)
    length_b = math.hypot(bdx, bdy)
    if length_a <= _TANGENT_EPS or length_b <= _TANGENT_EPS:
        return False
    ux = adx / length_a
    uy = ady / length_a
    if ux * bdx + uy * bdy < 0.999 * length_b:
        return False
    if abs(ux * (b0[1] - a0[1]) - uy * (b0[0] - a0[0])) > 1e-3:
        return False
    if abs(ux * (b1[1] - a0[1]) - uy * (b1[0] - a0[0])) > 1e-3:
        return False
    return True


def _short_dip(points, edge, chain):
    """The chain is a dent of arc chords under a straight offset."""
    count = len(points)
    start = points[edge]
    end = points[(edge + 1) % count]
    length = math.hypot(end[0] - start[0], end[1] - start[1])
    if length <= _TANGENT_EPS:
        return False
    ux = (end[0] - start[0]) / length
    uy = (end[1] - start[1]) / length
    dipped = False
    for index in chain[1:-1]:
        point = points[index]
        cross = ux * (point[1] - start[1]) - uy * (point[0] - start[0])
        if cross < -1e-3:
            return False
        # A crossing of close pieces sits just under the line.
        if cross > 1e-3:
            dipped = True
    for index in range(len(chain) - 1):
        a = points[chain[index]]
        b = points[chain[index + 1]]
        edge_length = math.hypot(b[0] - a[0], b[1] - a[1])
        if edge_length <= 0.75:
            continue
        if abs(ux * (a[1] - start[1]) - uy * (a[0] - start[0])) > 1e-3:
            return False
        if abs(ux * (b[1] - start[1]) - uy * (b[0] - start[0])) > 1e-3:
            return False
        if ux * (b[0] - a[0]) + uy * (b[1] - a[1]) < 0.999 * edge_length:
            return False
    return dipped


def _shortcut_is_outer(points, chain, edge):
    count = len(points)
    start = points[edge]
    end = points[(edge + 1) % count]
    length = math.hypot(end[0] - start[0], end[1] - start[1])
    if length <= _TANGENT_EPS:
        return False
    ux = (end[0] - start[0]) / length
    uy = (end[1] - start[1]) / length
    # Exterior is to the right of a counterclockwise edge.
    ox = uy
    oy = -ux
    a = points[chain[0]]
    b = points[chain[-1]]
    for t in (0.25, 0.5, 0.75):
        sample = (
            a[0] + (b[0] - a[0]) * t + ox * 0.01,
            a[1] + (b[1] - a[1]) * t + oy * 0.01,
        )
        if _point_inside_ring(sample, points):
            return False
    return True


def _straighten_colinear(points):
    """Keep a shared straight offset across the gaps between its pieces.

    A fillet at each crossing leaves a bump. The line already clears
    the subject where it stays outside the offset.
    """
    count = len(points)
    if count < 4:
        return points
    _lengths, total = _cumulative(points)
    sides = []
    for index in range(count):
        # A short top anchors the line the same way a long one does.
        if _straight_side(points, index):
            sides.append(index)
    gaps = []
    for pos, edge in enumerate(sides):
        end_vertex = (edge + 1) % count
        for later in sides[pos + 1:] + sides[:pos]:
            chain = _index_chain(count, end_vertex, later)
            span = 0.0
            for index in range(len(chain) - 1):
                a = points[chain[index]]
                b = points[chain[index + 1]]
                span += math.hypot(b[0] - a[0], b[1] - a[1])
            if span > total * 0.5:
                break
            if not _edges_colinear(points, edge, later):
                continue
            if not _short_dip(points, edge, chain):
                continue
            if not _shortcut_is_outer(points, chain, edge):
                continue
            gaps.append((chain[0], chain[-1]))
            break
    if not gaps:
        return points
    drop = [False] * count
    for start, end in gaps:
        cursor = (start + 1) % count
        guard = 0
        while cursor != end and guard < count:
            drop[cursor] = True
            cursor = (cursor + 1) % count
            guard += 1
    kept = [
        point for index, point in enumerate(points) if not drop[index]
    ]
    if len(kept) < 3:
        return points
    return kept


def _kept_outline(points, fallback):
    path = _closed_path(points)
    if path is None:
        return fallback
    return path


def _finish_outline(outer, distance, dilated, cap_mouth=True):
    """Round reflex corners outward to the surround distance.

    The arc stays outside the offset, including at a crossing dent.
    A connector through that dent would come closer than the distance.
    Colinear straight offsets are one line before that fillet. A mouth
    on one dilation is still one turn. A gap bridge is not a mouth.
    """
    points = _straighten_colinear(_ring_points(outer))
    if len(points) < 4:
        return outer
    corners = [
        index for index in range(len(points))
        if _signed_turn(points, index) <= -_SHARP_TURN
    ]
    if not corners:
        return _kept_outline(points, outer)
    # Half the gap lets two fillets meet. The old 0.45 cap dropped a
    # corner whose setback fit in the space that was left.
    sharp_set = set(corners)
    fillets = []
    failed = []
    for index in corners:
        gap = _sharp_gap(points, index, sharp_set)
        max_back = min(0.5 * gap, 8.0 * distance)
        fillet = _fit_fillet(points, index, distance, max_back, dilated)
        if fillet is None:
            failed.append(index)
        else:
            fillets.append(fillet)
    consumed = set()
    if cap_mouth:
        for chain in _close_chains(points, failed, distance):
            bridge = _bridge_chain(points, chain, distance, dilated)
            if bridge is None:
                continue
            fillets.append(bridge)
            consumed.update(chain)
    for index in failed:
        if index in consumed:
            continue
        gap = _sharp_gap(points, index, sharp_set)
        max_back = min(0.5 * gap, 8.0 * distance)
        fillet = _fit_fillet_loose(points, index, distance, max_back, dilated)
        if fillet is not None:
            fillets.append(fillet)
    if not fillets:
        return _kept_outline(points, outer)
    applied = _apply_fillets(points, fillets)
    if applied is None:
        return _kept_outline(points, outer)
    outline, _attachments = applied
    path = _closed_path(outline)
    return outer if path is None else path
