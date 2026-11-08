# -*- coding: utf-8 -*-
"""Surround clip to the inner rectangle. No Inkscape."""
from __future__ import division

import math

import pytest

try:
    from weedlib.qt import QPainterPath  # noqa: F401
except ImportError:
    pytest.skip('Qt cannot load', allow_module_level=True)

from weedlib import build_surrounds, piece_border
from weedlib.qt import QPainterPath, QPointF


_DISTANCE = 4.0
_INNER = 1.0
_ROUNDING = 0.02


def _square():
    path = QPainterPath()
    path.addRect(0, 0, 10, 10)
    return path


def _four_squares():
    path = QPainterPath()
    for x_coord, y_coord in ((0, 0), (30, 0), (0, 30), (30, 30)):
        path.addRect(x_coord, y_coord, 10, 10)
    return path


def _plus():
    path = QPainterPath()
    path.addRect(0, 15, 40, 10)
    path.addRect(15, 0, 10, 40)
    return path


def _is_closed(path):
    if path.elementCount() < 2:
        return False
    start = path.elementAt(0)
    end = path.elementAt(path.elementCount() - 1)
    return (
        abs(start.x - end.x) <= 1e-6
        and abs(start.y - end.y) <= 1e-6
    )


def _moves(path):
    move = QPainterPath.MoveToElement
    return sum(
        1 for index in range(path.elementCount())
        if path.elementAt(index).type == move
    )


def _same_path(left, right):
    assert left.elementCount() == right.elementCount()
    for index in range(left.elementCount()):
        got = left.elementAt(index)
        expected = right.elementAt(index)
        assert got.type == expected.type
        assert got.x == pytest.approx(expected.x)
        assert got.y == pytest.approx(expected.y)


def _inner_rect(subject, inner_distance):
    inner, _outer = piece_border(subject, inner_distance, 1.0)
    return inner.boundingRect()


def _ends(path):
    start = path.elementAt(0)
    end = path.elementAt(path.elementCount() - 1)
    return (start.x, start.y), (end.x, end.y)


def _on_rect(x_coord, y_coord, rect, eps=1e-3):
    inside = (
        rect.left() - eps <= x_coord <= rect.right() + eps
        and rect.top() - eps <= y_coord <= rect.bottom() + eps
    )
    on_side = (
        abs(x_coord - rect.left()) <= eps
        or abs(x_coord - rect.right()) <= eps
        or abs(y_coord - rect.top()) <= eps
        or abs(y_coord - rect.bottom()) <= eps
    )
    return inside and on_side


def _inside_rect(x_coord, y_coord, rect, eps=1e-3):
    return (
        rect.left() - eps <= x_coord <= rect.right() + eps
        and rect.top() - eps <= y_coord <= rect.bottom() + eps
    )


def _perimeter_pos(x_coord, y_coord, rect, eps=1e-3):
    left, top = rect.left(), rect.top()
    right, bottom = rect.right(), rect.bottom()
    width = right - left
    height = bottom - top
    if abs(y_coord - top) <= eps and left - eps <= x_coord <= right + eps:
        return x_coord - left
    if abs(x_coord - right) <= eps and top - eps <= y_coord <= bottom + eps:
        return width + (y_coord - top)
    if abs(y_coord - bottom) <= eps and left - eps <= x_coord <= right + eps:
        return width + height + (right - x_coord)
    if abs(x_coord - left) <= eps and top - eps <= y_coord <= bottom + eps:
        return 2 * width + height + (bottom - y_coord)
    raise AssertionError(
        'end is not on the inner rectangle: {}, {}'.format(x_coord, y_coord))


def _point_at(position, rect):
    left, top = rect.left(), rect.top()
    right, bottom = rect.right(), rect.bottom()
    width = right - left
    height = bottom - top
    length = 2.0 * (width + height)
    position = position % length
    if position <= width:
        return (left + position, top)
    position -= width
    if position <= height:
        return (right, top + position)
    position -= height
    if position <= width:
        return (right - position, bottom)
    position -= width
    return (left, bottom - position)


def _boundary_between(start, end, rect):
    """Samples of both rectangle chains between two ends, ends excluded."""
    length = 2.0 * (
        (rect.right() - rect.left()) + (rect.bottom() - rect.top()))
    pos_start = _perimeter_pos(start[0], start[1], rect)
    pos_end = _perimeter_pos(end[0], end[1], rect)
    forward = (pos_end - pos_start) % length
    samples = []
    for span in (forward, forward - length):
        if abs(span) <= 1e-6:
            continue
        for step in (1, 2, 3):
            samples.append(_point_at(pos_start + span * step / 4.0, rect))
    return samples


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


def _distance_to_path(x_coord, y_coord, path):
    best = None
    for polygon in path.toSubpathPolygons():
        points = [(point.x(), point.y()) for point in polygon]
        if len(points) < 2:
            continue
        for index in range(len(points) - 1):
            ax, ay = points[index]
            bx, by = points[index + 1]
            dist = _segment_distance(x_coord, y_coord, ax, ay, bx, by)
            if best is None or dist < best:
                best = dist
    if best is None:
        return 1e9
    return best


def _distance_to_subject(x_coord, y_coord, subject):
    if subject.contains(QPointF(x_coord, y_coord)):
        return 0.0
    best = None
    for polygon in subject.toSubpathPolygons():
        points = [(point.x(), point.y()) for point in polygon]
        if len(points) < 2:
            continue
        for index in range(len(points) - 1):
            ax, ay = points[index]
            bx, by = points[index + 1]
            dist = _segment_distance(x_coord, y_coord, ax, ay, bx, by)
            if best is None or dist < best:
                best = dist
    if best is None:
        return 1e9
    return best


def _assert_open_run(path, rect, subject, distance):
    assert _moves(path) == 1
    assert not _is_closed(path)
    start, end = _ends(path)
    assert _on_rect(start[0], start[1], rect)
    assert _on_rect(end[0], end[1], rect)
    for x_coord, y_coord in _boundary_between(start, end, rect):
        assert _distance_to_path(x_coord, y_coord, path) > 0.25
    for index in range(path.elementCount()):
        element = path.elementAt(index)
        assert _inside_rect(element.x, element.y, rect)
        if index == 0 or index == path.elementCount() - 1:
            continue
        assert _distance_to_subject(
            element.x, element.y, subject) >= distance - _ROUNDING


def _cubic_at(start, first, second, end, t):
    u = 1.0 - t
    return (
        u * u * u * start[0]
        + 3 * u * u * t * first[0]
        + 3 * u * t * t * second[0]
        + t * t * t * end[0],
        u * u * u * start[1]
        + 3 * u * u * t * first[1]
        + 3 * u * t * t * second[1]
        + t * t * t * end[1],
    )


def _interiors(path):
    """Midpoints of lines and curves, not the element knots."""
    move = QPainterPath.MoveToElement
    line = QPainterPath.LineToElement
    curve = QPainterPath.CurveToElement
    data = QPainterPath.CurveToDataElement
    current = None
    samples = []
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
            samples.append((
                0.5 * (current[0] + end[0]),
                0.5 * (current[1] + end[1]),
            ))
            current = end
            index += 1
            continue
        if element.type != curve or current is None:
            index += 1
            continue
        follow = path.elementAt(index + 1)
        if (
            index + 2 < count
            and path.elementAt(index + 2).type == data
        ):
            end_element = path.elementAt(index + 2)
            end = (end_element.x, end_element.y)
            samples.append(_cubic_at(
                current,
                (element.x, element.y),
                (follow.x, follow.y),
                end,
                0.5,
            ))
            current = end
            index += 3
            continue
        index += 1
    return samples


def test_omitted_inner_distance_keeps_the_outline(monkeypatch):
    """Omitting the length does not clip and does not ask for the rectangle."""
    def boom(*_args, **_kwargs):
        raise AssertionError('piece_border was called')

    monkeypatch.setattr(
        'weedlib.surround.build.piece_border', boom)
    subject = _four_squares()
    omitted = build_surrounds(subject, _DISTANCE, 0)
    explicit = build_surrounds(subject, _DISTANCE, 0.0, None)
    assert len(omitted) == 4
    assert len(explicit) == 4
    rect = _inner_rect(subject, _INNER)
    for left, right in zip(omitted, explicit):
        assert _is_closed(left)
        _same_path(left, right)
        # The unclipped outline still passes outside the inner rectangle.
        bounds = left.boundingRect()
        assert (
            bounds.left() < rect.left() - 1.0
            or bounds.right() > rect.right() + 1.0
            or bounds.top() < rect.top() - 1.0
            or bounds.bottom() > rect.bottom() + 1.0
        )
    assert min(
        path.boundingRect().left() for path in omitted
    ) == pytest.approx(-_DISTANCE)


def test_zero_inner_distance_still_clips():
    """Zero is a passed length, not the omitted default."""
    omitted = build_surrounds(_square(), _DISTANCE)
    assert len(omitted) == 1
    assert _is_closed(omitted[0])
    assert build_surrounds(_square(), _DISTANCE, 0, 0.0) == []


def test_four_squares_lose_their_outer_sides():
    """Outer sides of four squares are not the surround, and the run is open."""
    subject = _four_squares()
    paths = build_surrounds(subject, _DISTANCE, 0, _INNER)
    assert len(paths) == 4
    rect = _inner_rect(subject, _INNER)
    for path in paths:
        _assert_open_run(path, rect, subject, _DISTANCE)
    # Sides that lie on the piece bounds. The surround must not trace them.
    outer_midpoints = (
        (0, 5), (5, 0),
        (40, 5), (35, 0),
        (0, 35), (5, 40),
        (40, 35), (35, 40),
    )
    for x_coord, y_coord in outer_midpoints:
        nearest = min(
            _distance_to_path(x_coord, y_coord, path) for path in paths)
        assert nearest > 1.0
    # The inward sides are still surrounded, at the surround distance.
    inner_midpoints = ((10, 5), (5, 10))
    for x_coord, y_coord in inner_midpoints:
        nearest = min(
            _distance_to_path(x_coord, y_coord, path) for path in paths)
        assert nearest == pytest.approx(_DISTANCE, abs=0.05)


def test_inside_stays_closed_and_outside_is_absent():
    """A surround inside the rectangle stays closed. One outside is absent."""
    removed = build_surrounds(_square(), _DISTANCE, 0, _INNER)
    assert removed == []

    scene = QPainterPath()
    for x_coord, y_coord in ((0, 0), (50, 0), (0, 50), (50, 50)):
        scene.addRect(x_coord, y_coord, 10, 10)
    scene.addRect(25, 25, 10, 10)
    raw = build_surrounds(scene, 3, 0)
    clipped = build_surrounds(scene, 3, 0, 2)
    assert len(raw) == 5
    assert len(clipped) == 5
    closed = [path for path in clipped if _is_closed(path)]
    opened = [path for path in clipped if not _is_closed(path)]
    assert len(closed) == 1
    assert len(opened) == 4
    same_bounds = closed[0].boundingRect()
    matched = [
        path for path in raw
        if path.boundingRect().left() == pytest.approx(same_bounds.left())
        and path.boundingRect().top() == pytest.approx(same_bounds.top())
    ]
    assert len(matched) == 1
    _same_path(closed[0], matched[0])
    rect = _inner_rect(scene, 2)
    for path in opened:
        _assert_open_run(path, rect, scene, 3)
    # The clip does not substitute a subject square for a removed outline.
    squares = ((0, 0), (50, 0), (0, 50), (50, 50), (25, 25))
    for path in clipped:
        bounds = path.boundingRect()
        for origin_x, origin_y in squares:
            assert not (
                bounds.left() == pytest.approx(origin_x)
                and bounds.top() == pytest.approx(origin_y)
                and bounds.width() == pytest.approx(10)
                and bounds.height() == pytest.approx(10)
            )

    circle = QPainterPath()
    circle.addEllipse(0, 0, 20, 20)
    raw_circle = build_surrounds(circle, 0)
    clipped_circle = build_surrounds(circle, 0, 0, 2)
    assert len(clipped_circle) == 1
    assert _is_closed(clipped_circle[0])
    _same_path(clipped_circle[0], raw_circle[0])


def test_several_runs_stay_open():
    """One surround that meets the rectangle in several runs leaves each open."""
    subject = _plus()
    paths = build_surrounds(subject, 3, 0, _INNER)
    assert len(paths) == 4
    rect = _inner_rect(subject, _INNER)
    for path in paths:
        _assert_open_run(path, rect, subject, 3)
        assert _distance_to_subject(
            *_ends(path)[0], subject) > 0.5
        assert _distance_to_subject(
            *_ends(path)[1], subject) > 0.5


def test_join_still_runs_before_the_clip():
    subject = QPainterPath()
    subject.addRect(0, 0, 10, 10)
    subject.addRect(12, 0, 10, 10)
    paths = build_surrounds(subject, _DISTANCE, 0, 30)
    assert len(paths) == 1
    assert _is_closed(paths[0])


def test_clip_follows_piece_border(monkeypatch):
    """The clip uses the rectangle ``piece_border`` returns."""
    def wide(subject, inner_distance, border_width):
        assert inner_distance == _INNER
        assert subject.boundingRect().width() == pytest.approx(10)
        path = QPainterPath()
        path.addRect(-20, -20, 50, 50)
        outer = QPainterPath()
        outer.addRect(-30, -30, 70, 70)
        return (path, outer)

    monkeypatch.setattr('weedlib.surround.build.piece_border', wide)
    paths = build_surrounds(_square(), _DISTANCE, 0, _INNER)
    assert len(paths) == 1
    assert _is_closed(paths[0])
    assert paths[0].boundingRect().left() == pytest.approx(-_DISTANCE)


def test_curve_clip_does_not_cut_the_subject():
    """A distance-0 curve that meets the rectangle keeps its arcs."""
    circle = QPainterPath()
    circle.addEllipse(0, 0, 20, 20)
    raw = build_surrounds(circle, 0)
    clipped = build_surrounds(circle, 0, 0, 0.0)
    assert len(clipped) == 1
    assert _is_closed(clipped[0])
    _same_path(clipped[0], raw[0])
    for x_coord, y_coord in _interiors(clipped[0]):
        assert math.hypot(x_coord - 10.0, y_coord - 10.0) >= 10.0 - 0.02

    rounded = QPainterPath()
    rounded.addRoundedRect(0, 0, 40, 20, 6, 6)
    paths = build_surrounds(rounded, 0, 0, 0.0)
    assert len(paths) == 4
    curve = QPainterPath.CurveToElement
    for path in paths:
        assert not _is_closed(path)
        assert any(
            path.elementAt(index).type == curve
            for index in range(path.elementCount())
        )
        # The corner is a radius-6 arc. A chord of that arc sits
        # about 0.12 inside the subject. The curve must not.
        centers = ((6.0, 6.0), (34.0, 6.0), (6.0, 14.0), (34.0, 14.0))
        for x_coord, y_coord in _interiors(path):
            for center_x, center_y in centers:
                radial = math.hypot(
                    x_coord - center_x, y_coord - center_y)
                assert radial >= 6.0 - 0.02
    for x_coord, y_coord in ((20, 0), (20, 20), (0, 10), (40, 10)):
        nearest = min(
            _distance_to_path(x_coord, y_coord, path) for path in paths)
        assert nearest > 0.5
