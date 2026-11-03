# -*- coding: utf-8 -*-
"""Surrounds from the subject and a distance. No Inkscape."""
from __future__ import division

import math

import pytest

try:
    from weedlib.qt import QPainterPath  # noqa: F401
except ImportError:
    pytest.skip('Qt cannot load', allow_module_level=True)

from weedlib import build_surrounds
from weedlib.qt import QPainterPath, QPointF, QTransform, Qt
from weedlib.surround import _bridge_clears

# Chord error of the round join stays under this. A miter misses by more.
_ROUNDING = 0.01
_SIDE = 10.0


def _square():
    path = QPainterPath()
    path.addRect(0, 0, _SIDE, _SIDE)
    return path


def _ring():
    path = QPainterPath()
    path.setFillRule(Qt.OddEvenFill)
    path.addRect(0, 0, 40, 40)
    path.addRect(10, 10, 20, 20)
    return path


def _two_squares(x, y):
    path = QPainterPath()
    path.addRect(0, 0, _SIDE, _SIDE)
    path.addRect(x, y, _SIDE, _SIDE)
    return path


def _island():
    # Outer, a hole, and a piece in that hole. The piece's gap to the
    # hole wall is 7.
    path = QPainterPath()
    path.setFillRule(Qt.OddEvenFill)
    path.addRect(0, 0, 40, 40)
    path.addRect(10, 10, 20, 20)
    path.addRect(17, 17, 6, 6)
    return path


def _moves(path):
    move = QPainterPath.MoveToElement
    return sum(
        1 for index in range(path.elementCount())
        if path.elementAt(index).type == move
    )


def _polygon_area(path):
    area = 0.0
    for polygon in path.toSubpathPolygons():
        points = [(point.x(), point.y()) for point in polygon]
        if len(points) < 2:
            continue
        for index in range(len(points) - 1):
            x0, y0 = points[index]
            x1, y1 = points[index + 1]
            area += x0 * y1 - x1 * y0
    return abs(area) * 0.5


def _symmetric_area(left, right):
    return (
        _polygon_area(left.subtracted(right).simplified())
        + _polygon_area(right.subtracted(left).simplified())
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


def _distance_to_square(x, y):
    cx = min(max(x, 0.0), _SIDE)
    cy = min(max(y, 0.0), _SIDE)
    return math.hypot(x - cx, y - cy)


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


def test_zero_distance_is_the_outer_boundary():
    outer = _rect(0, 0, 40, 40)
    surrounds = build_surrounds(_ring(), 0)
    assert len(surrounds) == 1
    assert _moves(surrounds[0]) == 1
    assert _symmetric_area(surrounds[0], outer) == pytest.approx(0.0, abs=1e-4)

    # The piece in the hole is a cluster. The hole loop is not.
    piece = _rect(17, 17, 6, 6)
    surrounds = build_surrounds(_island(), 0)
    assert len(surrounds) == 2
    assert all(_moves(path) == 1 for path in surrounds)
    assert any(
        _symmetric_area(path, outer) == pytest.approx(0.0, abs=1e-4)
        for path in surrounds
    )
    assert any(
        _symmetric_area(path, piece) == pytest.approx(0.0, abs=1e-4)
        for path in surrounds
    )

    expanded = build_surrounds(_ring(), 3)
    assert len(expanded) == 1
    assert _moves(expanded[0]) == 1
    bounds = expanded[0].boundingRect()
    assert bounds.left() == pytest.approx(-3.0, abs=1e-3)
    assert bounds.top() == pytest.approx(-3.0, abs=1e-3)
    assert bounds.right() == pytest.approx(43.0, abs=1e-3)
    assert bounds.bottom() == pytest.approx(43.0, abs=1e-3)


def test_positive_distance_uses_a_round_join():
    distance = 2.0
    surrounds = build_surrounds(_square(), distance)
    assert len(surrounds) == 1
    assert _moves(surrounds[0]) == 1
    path = surrounds[0]

    side = (_SIDE * 0.5, -distance)
    arc = (_SIDE + distance / math.sqrt(2.0), _SIDE + distance / math.sqrt(2.0))
    miter = (_SIDE + distance, _SIDE + distance)
    assert _distance_to_path(side[0], side[1], path) <= _ROUNDING
    assert _distance_to_path(arc[0], arc[1], path) <= _ROUNDING
    assert _distance_to_path(miter[0], miter[1], path) > 0.5

    for x, y in _boundary_samples(path):
        assert _distance_to_square(x, y) >= distance - _ROUNDING

    circle = QPainterPath()
    circle.addEllipse(0, 0, 20, 20)
    curved = build_surrounds(circle, distance)
    assert len(curved) == 1
    assert _moves(curved[0]) == 1
    for x, y in _boundary_samples(curved[0]):
        radial = math.hypot(x - 10.0, y - 10.0) - 10.0
        assert radial >= distance - _ROUNDING


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


def _deepest_chord(ring):
    best = None
    count = len(ring)
    for index in range(count):
        ax, ay = ring[index]
        bx, by = ring[(index + 1) % count]
        mx = 0.5 * (ax + bx)
        my = 0.5 * (ay + by)
        radius = math.hypot(mx, my)
        if best is None or radius < best[0]:
            best = (radius, mx, my)
    return best


def _point_in_ring(x, y, ring):
    inside = False
    previous = len(ring) - 1
    for index in range(len(ring)):
        xi, yi = ring[index]
        xj, yj = ring[previous]
        if (yi > y) != (yj > y):
            cross_x = (xj - xi) * (y - yi) / (yj - yi) + xi
            if x < cross_x:
                inside = not inside
        previous = index
    return inside


def _triangle_in_chord_gap(ellipse):
    """A hole whose vertex lies inside the curve and outside its chords."""
    ring = _ring_points(ellipse)
    chord, mx, my = _deepest_chord(ring)
    aim = math.hypot(mx, my)
    vertex_radius = chord + 0.05
    vx = mx * vertex_radius / aim
    vy = my * vertex_radius / aim
    px = -my / aim
    py = mx / aim
    base = 7.0
    spread = 1.2
    first = (
        mx * base / aim + spread * px,
        my * base / aim + spread * py,
    )
    second = (
        mx * base / aim - spread * px,
        my * base / aim - spread * py,
    )
    triangle = QPainterPath()
    triangle.moveTo(vx, vy)
    triangle.lineTo(first[0], first[1])
    triangle.lineTo(second[0], second[1])
    triangle.closeSubpath()
    return QPointF(vx, vy), triangle, ring


def test_zero_distance_unions_an_overlap():
    # Half of the second square sits on the first. Distance 0 is the
    # outer boundary of that union, not two outlines.
    subject = _two_squares(_SIDE * 0.5, 0.0)
    surrounds = build_surrounds(subject, 0, 0)
    assert len(surrounds) == 1
    assert _moves(surrounds[0]) == 1
    union = _rect(0.0, 0.0, _SIDE * 1.5, _SIDE)
    assert _symmetric_area(surrounds[0], union) == pytest.approx(0.0, abs=1e-4)


def test_zero_distance_omits_a_hole_in_the_chord_gap():
    radius = 10.0
    ellipse = QPainterPath()
    ellipse.addEllipse(-radius, -radius, radius * 2.0, radius * 2.0)
    vertex, triangle, ring = _triangle_in_chord_gap(ellipse)
    assert math.hypot(vertex.x(), vertex.y()) < radius
    assert ellipse.contains(vertex)
    assert not _point_in_ring(vertex.x(), vertex.y(), ring)

    subject = QPainterPath()
    subject.setFillRule(Qt.OddEvenFill)
    subject.addPath(ellipse)
    subject.addPath(triangle)
    surrounds = build_surrounds(subject, 0)
    assert len(surrounds) == 1
    assert _moves(surrounds[0]) == 1
    assert _symmetric_area(surrounds[0], ellipse) == pytest.approx(0.0, abs=1e-4)


def test_close_pieces_share_one_surround():
    distance = 2.0
    # Edge gaps 3 and 5. Twice the distance is 4.
    close = build_surrounds(_two_squares(_SIDE + 3, 0), distance)
    far = build_surrounds(_two_squares(_SIDE + 5, 0), distance)
    # Corner gap 3 * sqrt(2) is greater than 4, so the expansions do not meet.
    diagonal_far = build_surrounds(
        _two_squares(_SIDE + 3, _SIDE + 3), distance)
    diagonal_close = build_surrounds(
        _two_squares(_SIDE + 2, _SIDE + 2), distance)

    assert len(close) == 1
    assert len(far) == 2
    assert len(diagonal_far) == 2
    assert len(diagonal_close) == 1
    for path in close + far + diagonal_far + diagonal_close:
        assert _moves(path) == 1


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


def test_join_keeps_a_step_beside_a_near_square():
    # The stepped union meets a square across a 0.05 gap. The bridge
    # is that strip. A hull edge would drop the step.
    subject = QPainterPath()
    subject.addRect(0, 0, 10, 10)
    subject.addRect(5, 5, 10, 10)
    subject.addRect(-10.05, 0, 10, 10)
    surrounds = build_surrounds(subject, 0, 0.1)
    assert len(surrounds) == 1
    assert _moves(surrounds[0]) == 1
    assert _polygon_area(surrounds[0]) == pytest.approx(275.5, abs=1e-4)
    assert not surrounds[0].contains(QPointF(2.0, 12.0))


def test_join_keeps_an_l_notch():
    # The upright offset is x = 12. The square joins across the base.
    distance = 2.0
    subject = QPainterPath()
    subject.moveTo(0, 0)
    subject.lineTo(20, 0)
    subject.lineTo(20, 10)
    subject.lineTo(10, 10)
    subject.lineTo(10, 20)
    subject.lineTo(0, 20)
    subject.closeSubpath()
    subject.addRect(25, 0, 10, 10)
    surrounds = build_surrounds(subject, distance, 1.0)
    assert len(surrounds) == 1
    path = surrounds[0]
    assert _moves(path) == 1
    assert _distance_to_path(12.0, 15.0, path) <= _ROUNDING
    assert not path.contains(QPointF(15.0, 15.0))
    for x, y in _boundary_samples(path):
        assert _subject_distance(x, y, subject) >= distance - _ROUNDING


def test_join_keeps_the_step_above_a_wide_square():
    # The upper square covers part of the wide top. The bridge is the
    # 0.05 strip. A tangent from the free corner fills the pocket.
    subject = QPainterPath()
    subject.addRect(0, 0, 20, 10)
    subject.addRect(0, 10.05, 10, 10)
    surrounds = build_surrounds(subject, 0, 0.1)
    assert len(surrounds) == 1
    path = surrounds[0]
    assert _moves(path) == 1
    assert _polygon_area(path) == pytest.approx(300.5, abs=1e-4)
    assert _distance_to_path(15.0, 10.0, path) <= 1e-4
    assert not path.contains(QPointF(12.0, 12.0))
    assert not path.contains(QPointF(15.0, 15.0))

    distance = 2.0
    offset = QPainterPath()
    offset.addRect(0, 0, 30, 10)
    offset.addRect(0, 15, 10, 10)
    joined = build_surrounds(offset, distance, 1.0)
    assert len(joined) == 1
    outline = joined[0]
    assert _moves(outline) == 1
    assert _distance_to_path(20.0, 12.0, outline) <= _ROUNDING
    assert not outline.contains(QPointF(20.0, 18.0))
    for x, y in _boundary_samples(outline):
        assert _subject_distance(x, y, offset) >= distance - _ROUNDING


def test_join_keeps_a_short_side_beside_a_wide_top():
    # The free end past the overlap is shorter than the sample step,
    # and the upper side is shorter than 1. The hull fills that corner.
    subject = QPainterPath()
    subject.addRect(0, 0, 30, 10)
    subject.addRect(0, 10.05, 29.2, 0.9)
    surrounds = build_surrounds(subject, 0, 0.1)
    assert len(surrounds) == 1
    path = surrounds[0]
    assert _moves(path) == 1
    assert _polygon_area(path) == pytest.approx(327.74, abs=1e-4)
    assert not path.contains(QPointF(29.6, 10.3))

    distance = 2.0
    offset = QPainterPath()
    offset.addRect(0, 0, 30, 10)
    offset.addRect(0, 15, 29.2, 0.5)
    joined = build_surrounds(offset, distance, 1.0)
    assert len(joined) == 1
    outline = joined[0]
    assert _moves(outline) == 1
    assert not outline.contains(QPointF(29.6, 12.5))
    for x, y in _boundary_samples(outline):
        assert _subject_distance(x, y, offset) >= distance - _ROUNDING


def test_join_bridges_a_colinear_run():
    # The two lower tops meet across 0.05 and stay one line. The
    # overlap with the upper square runs from x = 4 to x = 14.
    subject = QPainterPath()
    subject.addRect(0, 0, 10, 10)
    subject.addRect(10.05, 0, 10, 10)
    subject.addRect(4, 10.05, 10, 10)
    surrounds = build_surrounds(subject, 0, 0.1)
    assert len(surrounds) == 1
    path = surrounds[0]
    assert _moves(path) == 1
    assert _polygon_area(path) == pytest.approx(301.0, abs=1e-4)
    assert path.contains(QPointF(12.0, 10.02))


def test_join_keeps_both_steps_on_a_wide_top():
    # The second square meets a concave outline. One walk stops on
    # the same vertex, and that tangent would drop the wide square.
    subject = QPainterPath()
    subject.addRect(0, 0, 30, 10)
    subject.addRect(0, 10.05, 10, 10)
    subject.addRect(20, 10.05, 10, 10)
    surrounds = build_surrounds(subject, 0, 0.1)
    assert len(surrounds) == 1
    path = surrounds[0]
    assert _moves(path) == 1
    assert _polygon_area(path) == pytest.approx(501.0, abs=1e-4)
    assert _distance_to_path(15.0, 10.0, path) <= 1e-4
    assert not path.contains(QPointF(15.0, 15.0))
    assert path.contains(QPointF(5.0, 5.0))


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


def test_zero_distance_join_keeps_a_concave_overlap():
    # Corner overlap. The union steps in. A hull would cut that off.
    subject = _two_squares(5.0, 5.0)
    surrounds = build_surrounds(subject, 0, 0.1)
    assert len(surrounds) == 1
    assert _moves(surrounds[0]) == 1
    assert _polygon_area(surrounds[0]) == pytest.approx(175.0, abs=1e-4)
    assert surrounds[0].contains(QPointF(7.0, 2.0))
    assert not surrounds[0].contains(QPointF(12.0, 2.0))
    assert not surrounds[0].contains(QPointF(2.0, 12.0))


def test_join_gap_unions_a_near_miss():
    distance = 2.0
    # Edge gap 5. The surrounds are 1 apart. 0.02 short of that stays two.
    near = _two_squares(_SIDE + 5.0, 0.0)
    assert len(build_surrounds(near, distance)) == 2
    assert len(build_surrounds(near, distance, 1.0 - 0.02)) == 2
    # The piece in the hole stays 3 from the hole surround.
    assert len(build_surrounds(_island(), distance, 1.0)) == 2

    def clearance(x, y):
        return min(
            _distance_to_rect(x, y, 0.0, 0.0, _SIDE, _SIDE),
            _distance_to_rect(
                x, y, _SIDE + 5.0, 0.0, _SIDE + 5.0 + _SIDE, _SIDE),
        )

    path = _assert_one_smooth_outline(near, distance, clearance, 1.0)
    assert path.contains(QPointF(5.0, 5.0))
    assert path.contains(QPointF(_SIDE + 7.5, 5.0))
    assert path.contains(QPointF(_SIDE + 2.5, 5.0))
    assert _distance_to_path(_SIDE * 0.5, -distance, path) <= _ROUNDING

    gap = 5.0
    separation = math.hypot(gap, gap) - 2.0 * distance
    diagonal = _two_squares(_SIDE + gap, _SIDE + gap)
    assert len(build_surrounds(diagonal, distance, separation - 0.02)) == 2
    joined = build_surrounds(diagonal, distance, separation)
    assert len(joined) == 1
    assert min(_angles(joined[0])) > 150.0
    for x, y in _boundary_samples(joined[0]):
        assert min(
            _distance_to_rect(x, y, 0.0, 0.0, _SIDE, _SIDE),
            _distance_to_rect(
                x, y, _SIDE + gap, _SIDE + gap,
                _SIDE + gap + _SIDE, _SIDE + gap + _SIDE),
        ) >= distance - _ROUNDING


def test_join_keeps_a_piece_inside_the_frame():
    # The piece is 7 from the hole wall and sits inside the frame
    # outline. A span from that ring to y = -2 cuts the frame. The
    # square beside the frame still joins.
    distance = 2.0
    subject = _island()
    assert len(build_surrounds(subject, distance, 2.99)) == 2
    apart = build_surrounds(subject, distance, 3.0)
    assert len(apart) == 2
    frame = max(apart, key=_polygon_area)
    piece = min(apart, key=_polygon_area)
    assert _distance_to_path(20.0, -distance, frame) <= _ROUNDING
    assert _distance_to_path(23.0, 6.5, frame) > 1.0
    assert piece.contains(QPointF(20.0, 20.0))
    for path in apart:
        for x, y in _boundary_samples(path):
            assert _subject_distance(x, y, subject) >= distance - _ROUNDING

    assert len(build_surrounds(subject, 0, 6.35)) == 2
    raw = build_surrounds(subject, 0, 7.0)
    assert len(raw) == 2
    outer = max(raw, key=_polygon_area)
    inner = min(raw, key=_polygon_area)
    assert _distance_to_path(20.0, 0.0, outer) <= 1e-4
    assert outer.contains(QPointF(5.0, 5.0))
    assert inner.contains(QPointF(20.0, 20.0))

    beside = _island()
    beside.addRect(45, 0, 10, 10)
    joined = build_surrounds(beside, distance, 6.35)
    assert len(joined) == 2
    outline = max(joined, key=_polygon_area)
    island = min(joined, key=_polygon_area)
    assert outline.contains(QPointF(50.0, 5.0))
    assert outline.contains(QPointF(5.0, 5.0))
    assert island.contains(QPointF(20.0, 20.0))
    assert _distance_to_path(20.0, -distance, outline) <= _ROUNDING
    assert _distance_to_path(23.0, 6.5, outline) > 1.0
    for path in joined:
        for x, y in _boundary_samples(path):
            assert _subject_distance(x, y, beside) >= distance - _ROUNDING


def _frame_with_pieces(outer, hole, pieces):
    path = QPainterPath()
    path.setFillRule(Qt.OddEvenFill)
    path.addRect(*outer)
    path.addRect(*hole)
    for piece in pieces:
        path.addRect(*piece)
    return path


def test_join_bridges_pieces_inside_one_frame():
    # Two pieces sit outside each other inside the frame ring. The
    # bridge across the gap stays clear. A wall, or a gap past the
    # join gap, stays split.
    distance = 2.0
    close = _frame_with_pieces(
        (0, 0, 80, 80),
        (10, 10, 60, 60),
        ((17, 17, 4, 4), (25.5, 17, 4, 4)),
    )
    for join_gap in (0.5, 6.35):
        surrounds = build_surrounds(close, distance, join_gap)
        assert len(surrounds) == 2
        piece = min(surrounds, key=_polygon_area)
        assert _polygon_area(piece) == pytest.approx(128.5686, abs=1e-3)
        assert piece.contains(QPointF(23.25, 19.0))
        for path in surrounds:
            for x, y in _boundary_samples(path):
                assert _subject_distance(x, y, close) >= distance - _ROUNDING

    raw = _frame_with_pieces(
        (0, 0, 40, 40),
        (10, 10, 20, 20),
        ((17, 17, 2.95, 2.95), (20.05, 17, 2.95, 2.95)),
    )
    for join_gap in (6.35, 7.0):
        areas = sorted(
            _polygon_area(path) for path in build_surrounds(raw, 0, join_gap))
        assert areas == pytest.approx([17.7, 1600.0], abs=1e-3)

    apart = _frame_with_pieces(
        (0, 0, 80, 80),
        (10, 10, 60, 60),
        ((17, 17, 4, 4), (41, 17, 4, 4)),
    )
    assert len(build_surrounds(apart, distance, 6.35)) == 3

    # Wall thickness 1 between two holes. The straight bridge cuts it.
    walled = _frame_with_pieces(
        (0, 0, 50, 40),
        (5, 5, 15, 20),
        (),
    )
    walled.addRect(21, 5, 15, 20)
    walled.addRect(12.9, 12, 3, 4)
    walled.addRect(25.1, 12, 3, 4)
    walled_out = build_surrounds(walled, distance, 6.35)
    assert len(walled_out) == 3
    for path in walled_out:
        for x, y in _boundary_samples(path):
            assert _subject_distance(x, y, walled) >= distance - _ROUNDING


def _frame_with_finger(outer, hole, finger, pieces):
    # The finger reaches the hole's far side, so it stays frame.
    path = QPainterPath()
    path.setFillRule(Qt.OddEvenFill)
    path.addRect(*outer)
    hx, hy, hw, hh = hole
    fx, fy, fw, fh = finger
    top = hy + hh
    right = hx + hw
    notch = QPainterPath()
    notch.moveTo(hx, hy)
    notch.lineTo(right, hy)
    notch.lineTo(right, top)
    notch.lineTo(fx + fw, top)
    notch.lineTo(fx + fw, fy)
    notch.lineTo(fx, fy)
    notch.lineTo(fx, top)
    notch.lineTo(hx, top)
    notch.closeSubpath()
    path.addPath(notch)
    for piece in pieces:
        path.addRect(*piece)
    return path


def test_join_rejects_a_bridge_through_a_finger():
    # The whole edge is the test. A finger between the old probes
    # still cuts the bridge, and the pieces stay apart.
    raw = _frame_with_finger(
        (-10, -10, 50, 40),
        (-5, -5, 40, 25),
        (12.05, 8, 1, 12),
        ((0, 0, 10, 10), (16.35, 0, 10, 10)),
    )
    for join_gap in (6.34, 6.35):
        surrounds = build_surrounds(raw, 0, join_gap)
        assert len(surrounds) == 3
        assert any(path.contains(QPointF(5.0, 5.0)) for path in surrounds)
        assert any(path.contains(QPointF(21.35, 5.0)) for path in surrounds)
        for path in surrounds:
            assert _distance_to_path(12.5, 10.0, path) > 1.0

    apart = _frame_with_finger(
        (-15, -15, 90, 60),
        (-5, -5, 60, 35),
        (20, 11, 1, 19),
        ((0, 0, 10, 10), (40, 0, 10, 10)),
    )
    distance = 2.0
    for join_gap in (25.9, 26.0):
        surrounds = build_surrounds(apart, distance, join_gap)
        assert len(surrounds) == 3
        assert any(path.contains(QPointF(5.0, 5.0)) for path in surrounds)
        assert any(path.contains(QPointF(45.0, 5.0)) for path in surrounds)
        for path in surrounds:
            assert _distance_to_path(20.5, 12.0, path) > 1.0
            for x, y in _boundary_samples(path):
                assert _subject_distance(x, y, apart) >= distance - _ROUNDING


def test_bridge_gap_uses_the_subject_curve():
    # The chord gap is 2.048. The circle itself is 1.848 away, inside
    # the limit distance - 0.01. An edge a full 2 away still clears.
    circle = QPainterPath()
    circle.addEllipse(-10, -10, 20, 20)
    start = (13.197260, -5.488972)
    end = (10.030895, 10.194590)
    ring = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]
    near = [start, end, (40.0, 12.0), (40.0, -8.0)]
    assert _bridge_clears(near, ring, ring, circle, 2.0) is False
    axial = [(12.0, -8.0), (12.0, 8.0), (40.0, 8.0), (40.0, -8.0)]
    assert _bridge_clears(axial, ring, ring, circle, 2.0) is True


def test_negative_join_gap_is_rejected():
    with pytest.raises(ValueError):
        build_surrounds(_square(), 1.0, -0.1)
    with pytest.raises(ValueError):
        build_surrounds(_square(), -0.1)
