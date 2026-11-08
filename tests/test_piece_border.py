# -*- coding: utf-8 -*-
"""Piece border rectangles. No Inkscape."""
from __future__ import division

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


def test_exported_from_weedlib():
    assert weedlib.piece_border is piece_border
    assert 'piece_border' in weedlib.__all__
