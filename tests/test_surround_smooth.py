# -*- coding: utf-8 -*-
"""Fillets out to the surround distance. No Inkscape."""
from __future__ import division

import math

import pytest

try:
    from weedlib.qt import QPainterPath  # noqa: F401
except ImportError:
    pytest.skip('Qt cannot load', allow_module_level=True)

import weedlib.surround as surround
from weedlib import build_surrounds, progress
from weedlib.qt import QPainterPath, QPointF, QTransform

# Chord error of the round join stays under this. A miter misses by more.
_ROUNDING = 0.01
_SIDE = 10.0


def _two_squares(x, y):
    path = QPainterPath()
    path.addRect(0, 0, _SIDE, _SIDE)
    path.addRect(x, y, _SIDE, _SIDE)
    return path


def _moves(path):
    move = QPainterPath.MoveToElement
    return sum(
        1 for index in range(path.elementCount())
        if path.elementAt(index).type == move
    )


def _segment_distance(px, py, ax, ay, bx, by):
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


def _distance_to_path(x, y, path):
    best = None
    for polygon in path.toSubpathPolygons():
        points = [(point.x(), point.y()) for point in polygon]
        if len(points) < 2:
            continue
        for index in range(len(points) - 1):
            ax, ay = points[index]
            bx, by = points[index + 1]
            dist = _segment_distance(x, y, ax, ay, bx, by)
            if best is None or dist < best:
                best = dist
    if best is None:
        return 1e9
    return best


def _boundary_samples(path):
    samples = []
    for polygon in path.toSubpathPolygons():
        points = [(point.x(), point.y()) for point in polygon]
        for index in range(len(points) - 1):
            ax, ay = points[index]
            bx, by = points[index + 1]
            samples.append((ax, ay))
            samples.append((0.5 * (ax + bx), 0.5 * (ay + by)))
    return samples


def _rect(x, y, width, height):
    path = QPainterPath()
    path.addRect(x, y, width, height)
    return path


def _ring_points(path):
    try:
        polygons = path.toSubpathPolygons()
    except TypeError:
        polygons = path.toSubpathPolygons(QTransform())
    points = [(point.x(), point.y()) for point in polygons[0]]
    if len(points) >= 2 and math.hypot(
            points[0][0] - points[-1][0],
            points[0][1] - points[-1][1]) <= 1e-9:
        points.pop()
    return points


def _turn_angle(before, point, after):
    first = (before[0] - point[0], before[1] - point[1])
    second = (after[0] - point[0], after[1] - point[1])
    left = math.hypot(first[0], first[1])
    right = math.hypot(second[0], second[1])
    dot = (first[0] * second[0] + first[1] * second[1]) / (left * right)
    dot = max(-1.0, min(1.0, dot))
    return math.degrees(math.acos(dot))


def _angles(path):
    points = _ring_points(path)
    return [
        _turn_angle(
            points[index - 1],
            points[index],
            points[(index + 1) % len(points)],
        )
        for index in range(len(points))
    ]


def _assert_one_smooth_outline(subject, distance, clearance_at, join_gap=0.0):
    surrounds = build_surrounds(subject, distance, join_gap)
    assert len(surrounds) == 1
    path = surrounds[0]
    assert _moves(path) == 1
    # A connector meets the outline at a hard angle and enters the gap.
    assert min(_angles(path)) > 150.0
    for x, y in _boundary_samples(path):
        assert clearance_at(x, y) >= distance - _ROUNDING
    return path


def _segment_intersection(a, b, c, d):
    rx = b[0] - a[0]
    ry = b[1] - a[1]
    sx = d[0] - c[0]
    sy = d[1] - c[1]
    den = rx * sy - ry * sx
    if abs(den) <= 1e-12:
        return None
    t = ((c[0] - a[0]) * sy - (c[1] - a[1]) * sx) / den
    u = ((c[0] - a[0]) * ry - (c[1] - a[1]) * rx) / den
    if t < -1e-8 or t > 1.0 + 1e-8 or u < -1e-8 or u > 1.0 + 1e-8:
        return None
    return (a[0] + t * rx, a[1] + t * ry)


def _cluster_points(points, tol):
    groups = []
    for point in points:
        for group in groups:
            if math.hypot(point[0] - group[0], point[1] - group[1]) <= tol:
                break
        else:
            groups.append(point)
    return groups


def _boundary_crossings(left, right):
    first = _ring_points(left)
    second = _ring_points(right)
    hits = []
    for left_index in range(len(first)):
        a = first[left_index]
        b = first[(left_index + 1) % len(first)]
        for right_index in range(len(second)):
            c = second[right_index]
            d = second[(right_index + 1) % len(second)]
            point = _segment_intersection(a, b, c, d)
            if point is not None:
                hits.append(point)
    return _cluster_points(hits, 0.05)


def _circumradius(before, point, after):
    ab = math.hypot(point[0] - before[0], point[1] - before[1])
    bc = math.hypot(after[0] - point[0], after[1] - point[1])
    ca = math.hypot(before[0] - after[0], before[1] - after[1])
    cross = (
        (point[0] - before[0]) * (after[1] - before[1])
        - (point[1] - before[1]) * (after[0] - before[0])
    )
    area2 = abs(cross)
    if area2 <= 1e-8 or ab <= 1e-6 or bc <= 1e-6:
        return None
    return (ab * bc * ca) / (2.0 * area2)


def _distance_to_rect(x, y, left, bottom, right, top):
    cx = min(max(x, left), right)
    cy = min(max(y, bottom), top)
    return math.hypot(x - cx, y - cy)


def _separate_surround(bounds, distance):
    left, bottom, right, top = bounds
    return build_surrounds(_rect(left, bottom, right - left, top - bottom), distance)[0]


def test_crossed_surrounds_are_one_smooth_outline():
    distance = 2.0
    side = _SIDE
    # Edge gap 3 blends. Gap 3.9 spikes. The diagonal pair crosses off
    # the axis. Each pair is one outline, not a connector.
    cases = (
        (
            _two_squares(side + 3.0, 0.0),
            (
                (0.0, 0.0, side, side),
                (side + 3.0, 0.0, side + 3.0 + side, side),
            ),
        ),
        (
            _two_squares(side + 3.9, 0.0),
            (
                (0.0, 0.0, side, side),
                (side + 3.9, 0.0, side + 3.9 + side, side),
            ),
        ),
        (
            _two_squares(side + 2.0, side + 2.0),
            (
                (0.0, 0.0, side, side),
                (side + 2.0, side + 2.0, side + 2.0 + side, side + 2.0 + side),
            ),
        ),
    )
    for subject, rects in cases:
        path = _assert_one_smooth_outline(
            subject, distance, _clearance_to_rects(rects))
        crossings = _boundary_crossings(
            _separate_surround(rects[0], distance),
            _separate_surround(rects[1], distance),
        )
        assert len(crossings) == 2
        assert _distance_to_path(side * 0.5, -distance, path) <= _ROUNDING
        assert _distance_to_path(-distance, side * 0.5, path) <= _ROUNDING


def _subject_distance(x, y, subject):
    if subject.contains(QPointF(x, y)):
        return 0.0
    points = _ring_points(subject)
    best = None
    for index in range(len(points)):
        ax, ay = points[index]
        bx, by = points[(index + 1) % len(points)]
        dist = _segment_distance(x, y, ax, ay, bx, by)
        if best is None or dist < best:
            best = dist
    if best is None:
        return 1e9
    return best


def test_inner_corner_is_not_sharp():
    distance = 2.0
    # Reflex corner at (10, 10). Round join leaves that corner sharp.
    subject = QPainterPath()
    subject.moveTo(0, 0)
    subject.lineTo(20, 0)
    subject.lineTo(20, 10)
    subject.lineTo(10, 10)
    subject.lineTo(10, 20)
    subject.lineTo(0, 20)
    subject.closeSubpath()
    surrounds = build_surrounds(subject, distance)
    assert len(surrounds) == 1
    path = surrounds[0]
    assert _moves(path) == 1
    points = _ring_points(path)
    angles = [
        _turn_angle(
            points[index - 1],
            points[index],
            points[(index + 1) % len(points)],
        )
        for index in range(len(points))
    ]
    assert min(angles) > 150.0
    corner = (10.0, 10.0)
    radii = []
    for index in range(len(points)):
        before = points[index - 1]
        point = points[index]
        after = points[(index + 1) % len(points)]
        if math.hypot(point[0] - corner[0], point[1] - corner[1]) > 5.0:
            continue
        if _turn_angle(before, point, after) > 179.0:
            continue
        radius = _circumradius(before, point, after)
        if radius is None:
            continue
        radii.append(radius)
    assert radii
    assert min(radii) >= distance - 0.05
    for x, y in _boundary_samples(path):
        assert _subject_distance(x, y, subject) >= distance - _ROUNDING


def _clearance_to_rects(rects):
    def clearance(x, y):
        return min(
            _distance_to_rect(x, y, left, bottom, right, top)
            for left, bottom, right, top in rects
        )
    return clearance


def test_shallow_and_unequal_crossings_are_one_smooth_outline():
    distance = 2.0
    side = _SIDE
    # Gap 0.5 is a shallow dent. The 10 by 4 meets the square on
    # unequal fillets. Neither outline is a connector.
    cases = (
        (
            _two_squares(side + 0.5, 0.0),
            (
                (0.0, 0.0, side, side),
                (side + 0.5, 0.0, side + 0.5 + side, side),
            ),
        ),
        (
            _rect_beside(_SIDE, 4.0, side + 3.9),
            (
                (0.0, 0.0, side, side),
                (side + 3.9, 0.0, side + 3.9 + side, 4.0),
            ),
        ),
    )
    for subject, rects in cases:
        path = _assert_one_smooth_outline(
            subject, distance, _clearance_to_rects(rects))
        crossings = _boundary_crossings(
            _separate_surround(rects[0], distance),
            _separate_surround(rects[1], distance),
        )
        assert len(crossings) == 2
        assert _distance_to_path(side * 0.5, -distance, path) <= _ROUNDING
        assert _distance_to_path(-distance, side * 0.5, path) <= _ROUNDING


def _rect_beside(width, height, x):
    path = QPainterPath()
    path.addRect(0, 0, _SIDE, _SIDE)
    path.addRect(x, 0, width, height)
    return path


def test_square_beside_a_circle_is_one_smooth_outline():
    distance = 2.0
    # Circle diameter 10, left side at x = 12.
    subject = QPainterPath()
    subject.addRect(0, 0, _SIDE, _SIDE)
    subject.addEllipse(12, 0, _SIDE, _SIDE)
    circle = build_surrounds(_circle_at(12, 0, _SIDE), distance)[0]
    square = _separate_surround((0.0, 0.0, _SIDE, _SIDE), distance)
    crossings = _boundary_crossings(square, circle)
    assert len(crossings) == 2

    def clearance(x, y):
        radial = math.hypot(x - 17.0, y - 5.0) - 5.0
        if radial < 0.0:
            radial = 0.0
        return min(radial, _distance_to_rect(x, y, 0.0, 0.0, _SIDE, _SIDE))

    _assert_one_smooth_outline(subject, distance, clearance)


def _circle_at(x, y, diameter):
    path = QPainterPath()
    path.addEllipse(x, y, diameter, diameter)
    return path


def _u_channel(mouth):
    """A block U. The channel floor is y = 8 and the mouth is ``mouth`` wide."""
    inner_left = 12.0
    inner_right = inner_left + mouth
    outer_right = inner_right + 12.0
    top = 20.0
    path = QPainterPath()
    path.moveTo(0, 0)
    path.lineTo(outer_right, 0)
    path.lineTo(outer_right, top)
    path.lineTo(inner_right, top)
    path.lineTo(inner_right, 8)
    path.lineTo(inner_left, 8)
    path.lineTo(inner_left, top)
    path.lineTo(0, top)
    path.closeSubpath()
    return path


def test_close_reflex_corners_become_one_turn():
    distance = 2.0
    # Mouth 6. Offset corners land at (14, 10) and (16, 10), two units
    # apart, so two radius-2 setbacks do not fit.
    subject = _u_channel(6.0)
    surrounds = build_surrounds(subject, distance)
    assert len(surrounds) == 1
    path = surrounds[0]
    assert _moves(path) == 1
    points = _ring_points(path)
    angles = [
        _turn_angle(
            points[index - 1],
            points[index],
            points[(index + 1) % len(points)],
        )
        for index in range(len(points))
    ]
    assert min(angles) > 150.0
    # The chain becomes one turn across the mouth. The arc meets the
    # flattened outline on a short step; that step is not the turn.
    radii = []
    for index in range(len(points)):
        point = points[index]
        if not (12.0 <= point[0] <= 18.0 and 18.0 <= point[1] <= 24.0):
            continue
        before = points[index - 1]
        after = points[(index + 1) % len(points)]
        if math.hypot(point[0] - before[0], point[1] - before[1]) < 0.05:
            continue
        if math.hypot(after[0] - point[0], after[1] - point[1]) < 0.05:
            continue
        if angles[index] > 179.0:
            continue
        radius = _circumradius(before, point, after)
        if radius is None:
            continue
        radii.append(radius)
    assert radii
    assert min(radii) >= distance - 0.05
    for x, y in _boundary_samples(path):
        assert _subject_distance(x, y, subject) >= distance - _ROUNDING
    # Outer straight edges stay put. The cap does not replace them.
    assert _distance_to_path(15.0, -distance, path) <= _ROUNDING
    assert _distance_to_path(-distance, 10.0, path) <= _ROUNDING


def test_colinear_offsets_cross_the_gaps_in_one_line():
    # Each top sits on y = 12. The line across a gap stays clear, so
    # the outline keeps it. The outer corner stays the round join.
    distance = 2.0
    subject = QPainterPath()
    for origin in (0.0, 13.0, 26.0, 39.0, 52.0):
        subject.addRect(origin, 0.0, _SIDE, _SIDE)
    surrounds = build_surrounds(subject, distance)
    assert len(surrounds) == 1
    path = surrounds[0]
    assert _moves(path) == 1
    assert _distance_to_path(11.5, _SIDE + distance, path) <= _ROUNDING
    arc = (
        -distance / math.sqrt(2.0),
        _SIDE + distance / math.sqrt(2.0),
    )
    assert _distance_to_path(arc[0], arc[1], path) <= _ROUNDING
    for x, y in _boundary_samples(path):
        assert _subject_distance(x, y, subject) >= distance - _ROUNDING

    wider = QPainterPath()
    wider.addRect(0.0, 0.0, _SIDE, _SIDE)
    wider.addRect(_SIDE + 3.9, 0.0, _SIDE, _SIDE)
    joined = build_surrounds(wider, distance)
    assert len(joined) == 1
    mid = _SIDE + 1.95
    assert _distance_to_path(mid, _SIDE + distance, joined[0]) <= _ROUNDING

    # A dent of 0.015 still sits under the line. The line stays clear.
    close = QPainterPath()
    close.addRect(0.0, 0.0, _SIDE, _SIDE)
    close.addRect(_SIDE + 0.5, 0.0, _SIDE, _SIDE)
    near = build_surrounds(close, distance)
    assert len(near) == 1
    assert _distance_to_path(
        _SIDE + 0.25, _SIDE + distance, near[0]) <= _ROUNDING

    # Tops shorter than 1 still anchor the same line. The corner arc stays.
    narrow = QPainterPath()
    narrow.addRect(0.0, 0.0, 0.9, _SIDE)
    narrow.addRect(1.4, 0.0, 0.9, _SIDE)
    thin = build_surrounds(narrow, distance)
    assert len(thin) == 1
    assert _distance_to_path(1.15, _SIDE + distance, thin[0]) <= _ROUNDING
    arc = (
        -distance / math.sqrt(2.0),
        _SIDE + distance / math.sqrt(2.0),
    )
    assert _distance_to_path(arc[0], arc[1], thin[0]) <= _ROUNDING
    for x, y in _boundary_samples(thin[0]):
        assert _subject_distance(x, y, narrow) >= distance - _ROUNDING


def _ellipse(x, y, width, height):
    path = QPainterPath()
    path.addEllipse(x, y, width, height)
    return path


def _straight_sides(points):
    if len(points) < 4:
        return 0
    return sum(
        1 for index in range(len(points))
        if surround._straight_side(points, index)
    )


def test_fine_outline_checks_during_straighten():
    # This offset is one fine ring. The long stretch is the
    # straighten walk, so a check outside that walk does not count.
    path = _ellipse(0, 0, 400, 220)
    seen = {'sides': 0, 'checks': 0, 'named': 0}
    real = surround._straighten_colinear

    def wrapped(points):
        seen['sides'] += _straight_sides(points)
        seen['expect'] = tuple(points)
        seen['inside'] = True
        try:
            return real(points)
        finally:
            seen['inside'] = False

    def focus(outline, line):
        if not seen.get('inside'):
            return
        seen['checks'] += 1
        if line is None and outline == seen['expect']:
            seen['named'] += 1

    surround._straighten_colinear = wrapped
    progress.clear()
    try:
        progress.install(focus=focus)
        surrounds = build_surrounds(path, 8)
        assert len(surrounds) == 1
        assert seen['sides'] > 1
        assert seen['checks'] == seen['sides']
        assert seen['named'] == seen['sides']
    finally:
        surround._straighten_colinear = real
        progress.clear()
