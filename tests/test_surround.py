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


def _connector_ends(points):
    """Straight runs whose both ends meet the outline at a hard angle.

    A round-join step is a few degrees, so those chords are not runs.
    A blended crossing is one sharp vertex, not a run with two hard ends.
    One connector stroked twice is two runs on the same segment.
    """
    count = len(points)
    angles = []
    directions = []
    for index in range(count):
        previous = points[(index - 1) % count]
        point = points[index]
        nxt = points[(index + 1) % count]
        angles.append(_turn_angle(previous, point, nxt))
        dx = nxt[0] - point[0]
        dy = nxt[1] - point[1]
        length = math.hypot(dx, dy)
        directions.append((dx / length, dy / length))
    limit = math.cos(math.radians(2.0))

    def colinear(index):
        before = directions[(index - 1) % count]
        here = directions[index]
        return before[0] * here[0] + before[1] * here[1] >= limit

    breaks = [index for index in range(count) if not colinear(index)]
    found = []
    for position, start in enumerate(breaks):
        end = breaks[(position + 1) % len(breaks)]
        if (
            45.0 <= angles[start] <= 135.0
            and 45.0 <= angles[end] <= 135.0
        ):
            found.append((points[start], points[end], angles[start], angles[end]))
    return found, angles


def _same_segment(one, two):
    start, end = one[0], one[1]
    other_start, other_end = two[0], two[1]

    def near(left, right):
        return math.hypot(left[0] - right[0], left[1] - right[1]) <= 1e-4

    return (
        near(start, other_start) and near(end, other_end)
        or near(start, other_end) and near(end, other_start)
    )


def _unique_connectors(runs):
    unique = []
    for run in runs:
        if any(_same_segment(run, kept) for kept in unique):
            continue
        unique.append(run)
    return unique


def _segment_position(px, py, ax, ay, bx, by):
    dx = bx - ax
    dy = by - ay
    length_sq = dx * dx + dy * dy
    if length_sq <= 1e-18:
        return math.hypot(px - ax, py - ay), 0.0
    t = ((px - ax) * dx + (py - ay) * dy) / length_sq
    clamped = t
    if clamped < 0.0:
        clamped = 0.0
    elif clamped > 1.0:
        clamped = 1.0
    dist = math.hypot(px - (ax + clamped * dx), py - (ay + clamped * dy))
    return dist, t


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


def _assert_merged_on_connectors(subject, rects, distance):
    surrounds = build_surrounds(subject, distance)
    assert len(surrounds) == 1
    path = surrounds[0]
    assert _moves(path) == 1
    points = _ring_points(path)
    runs, angles = _connector_ends(points)
    connectors = _unique_connectors(runs)
    # One pair of crossings is one connector, even though the stroke
    # traverses it twice. Two local bridges stay two segments.
    assert len(connectors) == 1
    start, end, angle_start, angle_end = connectors[0]
    assert 45.0 <= angle_start <= 135.0
    assert 45.0 <= angle_end <= 135.0
    assert min(angles) >= 45.0
    # The hard angles are the connector ends. The rest of the outline is smooth.
    assert len([angle for angle in angles if angle < 150.0]) == 4
    crossings = _boundary_crossings(
        _separate_surround(rects[0], distance),
        _separate_surround(rects[1], distance),
    )
    assert len(crossings) == 2
    for x, y in crossings:
        dist, _t = _segment_position(x, y, start[0], start[1], end[0], end[1])
        assert dist <= distance
    mid_x = 0.5 * (start[0] + end[0])
    mid_y = 0.5 * (start[1] + end[1])
    mid_clearance = min(
        _distance_to_rect(mid_x, mid_y, left, bottom, right, top)
        for left, bottom, right, top in rects
    )
    # The connector is the overlap exception: it enters the gap.
    assert mid_clearance < distance - _ROUNDING
    for x, y in _boundary_samples(path):
        dist, t = _segment_position(x, y, start[0], start[1], end[0], end[1])
        if dist <= 0.05 and 0.02 < t < 0.98:
            continue
        clearance = min(
            _distance_to_rect(x, y, left, bottom, right, top)
            for left, bottom, right, top in rects
        )
        assert clearance >= distance - _ROUNDING
    assert _distance_to_path(_SIDE * 0.5, -distance, path) <= _ROUNDING
    assert _distance_to_path(-distance, _SIDE * 0.5, path) <= _ROUNDING


def test_crossed_surrounds_join_on_a_connector():
    distance = 2.0
    side = _SIDE
    # Edge gap 3 is inside twice the distance. The raw union corner is a
    # blend; the spike at 3.9 is sharper than 45 degrees. The diagonal
    # pair crosses off the axis. Each case is one connector between the
    # two crossings, not a bridge at each crossing.
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
        _assert_merged_on_connectors(subject, rects, distance)


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


def _assert_one_connector(path, distance, clearance_at, crossings):
    assert _moves(path) == 1
    points = _ring_points(path)
    runs, angles = _connector_ends(points)
    connectors = _unique_connectors(runs)
    assert len(connectors) == 1
    start, end, angle_start, angle_end = connectors[0]
    assert 45.0 <= angle_start <= 135.0
    assert 45.0 <= angle_end <= 135.0
    assert min(angles) >= 45.0
    # Hard angles are the connector ends. The rest of the outline is smooth.
    assert len([angle for angle in angles if angle < 150.0]) == 4
    for x, y in crossings:
        dist, _t = _segment_position(x, y, start[0], start[1], end[0], end[1])
        assert dist <= distance
    mid_x = 0.5 * (start[0] + end[0])
    mid_y = 0.5 * (start[1] + end[1])
    # The connector is the overlap exception: it may enter the gap.
    assert clearance_at(mid_x, mid_y) < distance - _ROUNDING
    for x, y in _boundary_samples(path):
        dist, t = _segment_position(x, y, start[0], start[1], end[0], end[1])
        if dist <= 0.05 and 0.02 < t < 0.98:
            continue
        assert clearance_at(x, y) >= distance - _ROUNDING


def _clearance_to_rects(rects):
    def clearance(x, y):
        return min(
            _distance_to_rect(x, y, left, bottom, right, top)
            for left, bottom, right, top in rects
        )
    return clearance


def test_shallow_and_unequal_crossings_join_on_a_connector():
    distance = 2.0
    side = _SIDE
    # Gap 0.5 turns about 13 degrees, under the old sharp cutoff.
    # The 10 by 4 meets the square on one fillet and misses the other.
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
        surrounds = build_surrounds(subject, distance)
        assert len(surrounds) == 1
        crossings = _boundary_crossings(
            _separate_surround(rects[0], distance),
            _separate_surround(rects[1], distance),
        )
        assert len(crossings) == 2
        _assert_one_connector(
            surrounds[0], distance, _clearance_to_rects(rects), crossings)
        # Straight offset of the first square survives the fillets.
        assert _distance_to_path(side * 0.5, -distance, surrounds[0]) <= _ROUNDING
        assert _distance_to_path(-distance, side * 0.5, surrounds[0]) <= _ROUNDING


def _rect_beside(width, height, x):
    path = QPainterPath()
    path.addRect(0, 0, _SIDE, _SIDE)
    path.addRect(x, 0, width, height)
    return path


def test_square_beside_a_circle_joins_on_a_connector():
    distance = 2.0
    # Circle diameter 10, left side at x = 12. Both fillets used to miss.
    subject = QPainterPath()
    subject.addRect(0, 0, _SIDE, _SIDE)
    subject.addEllipse(12, 0, _SIDE, _SIDE)
    surrounds = build_surrounds(subject, distance)
    assert len(surrounds) == 1
    circle = build_surrounds(_circle_at(12, 0, _SIDE), distance)[0]
    square = _separate_surround((0.0, 0.0, _SIDE, _SIDE), distance)
    crossings = _boundary_crossings(square, circle)
    assert len(crossings) == 2

    def clearance(x, y):
        radial = math.hypot(x - 17.0, y - 5.0) - 5.0
        if radial < 0.0:
            radial = 0.0
        return min(radial, _distance_to_rect(x, y, 0.0, 0.0, _SIDE, _SIDE))

    _assert_one_connector(surrounds[0], distance, clearance, crossings)


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
