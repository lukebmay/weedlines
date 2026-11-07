# -*- coding: utf-8 -*-
"""Offset, join gap, and the preamble. No Inkscape."""
from __future__ import division

import math

import pytest

try:
    from weedlib.qt import QPainterPath  # noqa: F401
except ImportError:
    pytest.skip('Qt cannot load', allow_module_level=True)

import weedlib.surround as surround
from weedlib import build_surrounds, progress
from weedlib.progress import WeedCancelled
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


def _distance_to_rect(x, y, left, bottom, right, top):
    cx = min(max(x, left), right)
    cy = min(max(y, bottom), top)
    return math.hypot(x - cx, y - cy)


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


def test_negative_join_gap_is_rejected():
    with pytest.raises(ValueError):
        build_surrounds(_square(), 1.0, -0.1)
    with pytest.raises(ValueError):
        build_surrounds(_square(), -0.1)


def test_cancel_before_a_long_stage_returns_no_outline():
    progress.clear()
    try:
        progress.install(cancel=lambda: True)
        with pytest.raises(WeedCancelled):
            build_surrounds(_two_squares(_SIDE + 5, 0), 2.0)
    finally:
        progress.clear()


def test_multi_cluster_records_a_check_before_return():
    seen = []
    progress.clear()
    try:
        progress.install(
            focus=lambda outline, line: seen.append((outline, line)))
        build_surrounds(_two_squares(_SIDE + 5, 0), 2.0)
        assert seen
    finally:
        progress.clear()


def _ellipse(x, y, width, height):
    path = QPainterPath()
    path.addEllipse(x, y, width, height)
    return path


def test_cancel_after_the_preamble_returns_no_outline():
    # Cancel stays false through the checks that already sit
    # outside the walk. It has to be raised from inside it.
    path = _ellipse(0, 0, 400, 220)
    seen = {'inside': False, 'before': 0, 'during': 0}
    real = surround._straighten_colinear

    def wrapped(points):
        seen['inside'] = True
        try:
            return real(points)
        finally:
            seen['inside'] = False

    def focus(outline, line):
        if seen['inside']:
            seen['during'] += 1
        else:
            seen['before'] += 1

    def cancel():
        return seen['inside']

    surround._straighten_colinear = wrapped
    returned = None
    progress.clear()
    try:
        progress.install(focus=focus, cancel=cancel)
        with pytest.raises(WeedCancelled):
            returned = build_surrounds(path, 8)
        assert returned is None
        assert seen['before'] >= 1
        assert seen['during'] >= 1
    finally:
        surround._straighten_colinear = real
        progress.clear()
