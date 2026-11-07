# -*- coding: utf-8 -*-
"""Dilate the subject and take its outer loops."""
from __future__ import division

import math

from .. import progress
from ..paths import split_painter_path
from ..qt import QPainterPath, QPainterPathStroker, QPointF, QTransform, Qt

# Boolean ops and the stroker flatten curves. Scale, and a tight
# curve threshold, keep the inward error to rounding. The threshold
# is in scaled units, so a length in user units uses it over the scale.
_CLIP_SCALE = 32.0
_CURVE_FLATNESS = 0.01
_CHORD_PAD = _CURVE_FLATNESS / _CLIP_SCALE
_CLOSED_TOL = 1e-4
_AREA_EPS = 1e-8
_TANGENT_EPS = 1e-12


def _focus_outline(path):
    """Points of one ring, or None when there is nothing to name."""
    if path is None:
        return None
    points = _ring_points(path)
    if not points:
        return None
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


def _ring_segments(ring):
    count = len(ring)
    return [
        (ring[index], ring[(index + 1) % count])
        for index in range(count)
    ]


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
    for index, (subpath, area, point) in enumerate(loops):
        progress.check(outline=_focus_outline(subpath))
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
