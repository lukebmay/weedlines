# -*- coding: utf-8 -*-
"""Piece border rectangles. No Inkscape."""
from __future__ import division

import math

import pytest

try:
    from weedlib.qt import QPainterPath  # noqa: F401
except ImportError:
    pytest.skip('Qt cannot load', allow_module_level=True)

import weedlib
from weedlib import piece_border
from weedlib.qt import QPainterPath


def _points(path):
    points = []
    for index in range(path.elementCount()):
        element = path.elementAt(index)
        points.append((element.x, element.y))
    return points


def _open_points(path):
    points = []
    for point in _points(path):
        if points and abs(points[-1][0] - point[0]) <= 1e-9 and abs(
                points[-1][1] - point[1]) <= 1e-9:
            continue
        points.append(point)
    if len(points) >= 2 and abs(points[0][0] - points[-1][0]) <= 1e-9 and abs(
            points[0][1] - points[-1][1]) <= 1e-9:
        points.pop()
    return points


def _assert_rect(path, x, y, width, height):
    assert isinstance(path, QPainterPath)
    bounds = path.boundingRect()
    assert bounds.x() == pytest.approx(x)
    assert bounds.y() == pytest.approx(y)
    assert bounds.width() == pytest.approx(width)
    assert bounds.height() == pytest.approx(height)
    points = _open_points(path)
    assert len(points) == 4
    expected = (
        (x, y),
        (x + width, y),
        (x, y + height),
        (x + width, y + height),
    )
    for ex, ey in expected:
        assert any(
            px == pytest.approx(ex) and py == pytest.approx(ey)
            for px, py in points)
    loop = points + points[:1]
    for (x0, y0), (x1, y1) in zip(loop, loop[1:]):
        assert x0 == pytest.approx(x1) or y0 == pytest.approx(y1)
    move = QPainterPath.MoveToElement
    line = QPainterPath.LineToElement
    for index in range(path.elementCount()):
        assert path.elementAt(index).type in (move, line)


def test_lengths_stay_user_units():
    """2 and 3 expand the bounds. They are not converted from inches."""
    subject = QPainterPath()
    subject.addRect(4, 5, 10, 20)
    inner, outer = piece_border(subject, 2, 3)
    _assert_rect(inner, 2, 3, 14, 24)
    _assert_rect(outer, -1, 0, 20, 30)


def test_diagonal_subject_stays_axis_aligned():
    subject = QPainterPath()
    subject.moveTo(0, 0)
    subject.lineTo(10, 4)
    inner, outer = piece_border(subject, 1, 2)
    _assert_rect(inner, -1, -1, 12, 6)
    _assert_rect(outer, -3, -3, 16, 10)


def test_line_is_not_an_empty_subject():
    subject = QPainterPath()
    subject.moveTo(4, 1)
    subject.lineTo(4, 11)
    inner, outer = piece_border(subject, 2, 1)
    _assert_rect(inner, 2, -1, 4, 14)
    _assert_rect(outer, 1, -2, 6, 16)


def test_empty_subject_returns_nothing():
    assert piece_border(QPainterPath(), 4, 5) == ()
    # A lone move is empty. Its bounding rect is that point, and
    # expanding it would invent a rectangle.
    moved = QPainterPath()
    moved.moveTo(12, 34)
    assert moved.isEmpty()
    assert piece_border(moved, 4, 5) == ()


def test_other_path_does_not_grow_the_bounds():
    subject = QPainterPath()
    subject.addRect(0, 0, 10, 10)
    subject.addRect(30, 5, 10, 20)
    other = QPainterPath()
    other.addRect(-100, -100, 500, 500)
    assert not other.isEmpty()
    inner, outer = piece_border(subject, 1, 3)
    _assert_rect(inner, -1, -1, 42, 27)
    _assert_rect(outer, -4, -4, 48, 33)


def test_hole_does_not_shrink_the_bounds():
    subject = QPainterPath()
    subject.addRect(0, 0, 40, 20)
    subject.addRect(5, 5, 10, 8)
    inner, outer = piece_border(subject, 2, 1)
    _assert_rect(inner, -2, -2, 44, 24)
    _assert_rect(outer, -3, -3, 46, 26)


def test_curve_uses_the_drawn_bounds():
    subject = QPainterPath()
    subject.moveTo(0, 0)
    subject.cubicTo(0, 30, 10, 30, 10, 0)
    bounds = subject.boundingRect()
    inner, outer = piece_border(subject, 1, 2)
    _assert_rect(
        inner,
        bounds.x() - 1,
        bounds.y() - 1,
        bounds.width() + 2,
        bounds.height() + 2)
    _assert_rect(
        outer,
        bounds.x() - 3,
        bounds.y() - 3,
        bounds.width() + 6,
        bounds.height() + 6)
    assert inner.boundingRect().height() == pytest.approx(24.5)
    assert inner.boundingRect().height() != pytest.approx(32)


def _elements(path):
    items = []
    for index in range(path.elementCount()):
        element = path.elementAt(index)
        items.append((element.type, element.x, element.y))
    return items


def _cubics(path):
    move = QPainterPath.MoveToElement
    line = QPainterPath.LineToElement
    curve = QPainterPath.CurveToElement
    current = None
    found = []
    index = 0
    count = path.elementCount()
    while index < count:
        element = path.elementAt(index)
        if element.type in (move, line):
            current = (element.x, element.y)
            index += 1
            continue
        if element.type != curve or current is None:
            index += 1
            continue
        first = (element.x, element.y)
        second = (
            path.elementAt(index + 1).x, path.elementAt(index + 1).y)
        end = (path.elementAt(index + 2).x, path.elementAt(index + 2).y)
        found.append((current, first, second, end))
        current = end
        index += 3
    return found


def _cubic_at(start, first, second, end, t):
    u = 1.0 - t
    return (
        u * u * u * start[0] + 3 * u * u * t * first[0]
        + 3 * u * t * t * second[0] + t * t * t * end[0],
        u * u * u * start[1] + 3 * u * u * t * first[1]
        + 3 * u * t * t * second[1] + t * t * t * end[1],
    )


# Qt's quarter-circle handle, as a fraction of the radius.
_HANDLE = 0.5522847498307936


def _assert_rounded(path, x, y, width, height, radius):
    bounds = path.boundingRect()
    assert bounds.x() == pytest.approx(x)
    assert bounds.y() == pytest.approx(y)
    assert bounds.width() == pytest.approx(width)
    assert bounds.height() == pytest.approx(height)
    centers = (
        (x + radius, y + radius),
        (x + width - radius, y + radius),
        (x + width - radius, y + height - radius),
        (x + radius, y + height - radius),
    )
    seen = []
    cubics = _cubics(path)
    assert len(cubics) == 4
    handle = _HANDLE * radius
    for start, first, second, end in cubics:
        mid = _cubic_at(start, first, second, end, 0.5)
        matched = None
        for center in centers:
            if abs(math.hypot(
                    start[0] - center[0], start[1] - center[1]) - radius) > 1e-4:
                continue
            if abs(math.hypot(
                    end[0] - center[0], end[1] - center[1]) - radius) > 1e-4:
                continue
            radial = math.hypot(mid[0] - center[0], mid[1] - center[1])
            if abs(radial - radius) <= 0.02:
                matched = center
                break
        assert matched is not None
        seen.append(matched)
        assert math.hypot(
            first[0] - start[0], first[1] - start[1]
        ) == pytest.approx(handle, abs=1e-3)
        assert math.hypot(
            second[0] - end[0], second[1] - end[1]
        ) == pytest.approx(handle, abs=1e-3)
    # A side of length 2 radii shares one center across two quarters.
    assert set(seen) == set(centers)


def test_zero_radius_is_square():
    """Omitted, None, zero, and below stay the rectangles already emitted."""
    subject = QPainterPath()
    subject.addRect(4, 5, 10, 20)
    plain = piece_border(subject, 2, 3)
    others = (
        piece_border(subject, 2, 3, None),
        piece_border(subject, 2, 3, 0),
        piece_border(subject, 2, 3, -2),
        piece_border(subject, 2, 3, corner_radius=0),
    )
    for other in others:
        assert len(other) == 2
        for left, right in zip(plain, other):
            assert _elements(left) == _elements(right)


def test_both_rectangles_round_by_the_given_radius():
    subject = QPainterPath()
    subject.addRect(4, 5, 10, 20)
    inner, outer = piece_border(subject, 2, 3, 4)
    _assert_rounded(inner, 2, 3, 14, 24, 4)
    # Same radius on the outer rectangle, not radius plus the width.
    _assert_rounded(outer, -1, 0, 20, 30, 4)


def test_radius_above_half_the_shorter_side_is_not_used():
    """10 is the shorter side, so half of it is the arc that is used."""
    subject = QPainterPath()
    subject.addRect(0, 0, 10, 40)
    capped = piece_border(subject, 0, 2, 5)
    over = piece_border(subject, 0, 2, 9)
    assert _elements(capped[0]) == _elements(over[0])
    assert _elements(capped[1]) == _elements(over[1])
    _assert_rounded(over[0], 0, 0, 10, 40, 5)
    _assert_rounded(over[1], -2, -2, 14, 44, 5)


def test_exported_from_weedlib():
    assert weedlib.piece_border is piece_border
    assert 'piece_border' in weedlib.__all__
