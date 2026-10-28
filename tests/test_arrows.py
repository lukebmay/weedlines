# -*- coding: utf-8 -*-
"""Correction arrows: origin, tip, and kind color."""
from __future__ import division

import inspect
import math

import pytest

pytest.importorskip('PyQt5', reason='Qt binding required')

from weedlib.arrows import build_arrow_paths
from weedlib.qt import QPointF, QRectF


def _vertices(path):
    points = []
    for i in range(path.elementCount()):
        element = path.elementAt(i)
        point = (element.x, element.y)
        if points and math.hypot(point[0] - points[-1][0], point[1] - points[-1][1]) <= 1e-9:
            continue
        points.append(point)
    if len(points) >= 2 and math.hypot(
            points[0][0] - points[-1][0], points[0][1] - points[-1][1]) <= 1e-9:
        points.pop()
    return points


def _tip(head, origin, target):
    """Apex: farthest along origin→target, or nearest when those coincide."""
    points = _vertices(head)
    ox, oy = origin
    tx, ty = target
    dx, dy = tx - ox, ty - oy
    if math.hypot(dx, dy) <= 1e-9:
        return min(points, key=lambda p: math.hypot(p[0] - tx, p[1] - ty))
    return max(points, key=lambda p: (p[0] - ox) * dx + (p[1] - oy) * dy)


def _area(points):
    total = 0.0
    for i, (x, y) in enumerate(points):
        nx, ny = points[(i + 1) % len(points)]
        total += x * ny - nx * y
    return abs(total) * 0.5


def test_shaft_starts_at_kind_origin_and_head_tip_is_target():
    # Stored top is not minimum y. The origin uses the minimum.
    bounds = QRectF(0, 80, 100, -30)
    cases = (
        ('dangling', (0.0, 50.0), [QPointF(30, 60), (70, 55)]),
        ('overlap', (100.0, 50.0), [(40, 60)]),
        ('self-overlap', (100.0, 80.0), [(20, 70)]),
    )
    for kind, origin, targets in cases:
        arrows = build_arrow_paths(kind, targets, bounds)
        assert len(arrows) == len(targets)
        for arrow, target in zip(arrows, targets):
            target = (target.x(), target.y()) if isinstance(target, QPointF) else target
            shaft = _vertices(arrow.shaft)
            assert len(shaft) >= 2
            assert shaft[0] == pytest.approx(origin)
            assert math.hypot(shaft[-1][0] - shaft[0][0], shaft[-1][1] - shaft[0][1]) > 0
            assert _tip(arrow.head, origin, target) == pytest.approx(target)


def test_target_on_origin_has_visible_tip():
    bounds = QRectF(0, 0, 200, 100)
    origins = {
        'dangling': (0.0, 0.0),
        'overlap': (200.0, 0.0),
        'self-overlap': (200.0, 100.0),
    }
    for kind, origin in origins.items():
        arrow = build_arrow_paths(kind, [origin], bounds)[0]
        shaft = _vertices(arrow.shaft)
        head = _vertices(arrow.head)
        # The tip is the forward end of the mark, not a base corner.
        direction = (shaft[-1][0] - shaft[0][0], shaft[-1][1] - shaft[0][1])
        forward = (shaft[0][0] + direction[0], shaft[0][1] + direction[1])
        assert _tip(arrow.head, shaft[0], forward) == pytest.approx(origin)
        assert _area(head) > 0


def test_colors_match_preview_and_are_not_arguments():
    assert list(inspect.signature(build_arrow_paths).parameters) == [
        'kind', 'targets', 'bounds',
    ]
    bounds = QRectF(0, 0, 80, 40)
    target = [(10, 10)]
    expect = {
        'dangling': '#FF00FF',
        'overlap': '#FF6A00',
        'self-overlap': '#00E5FF',
    }
    for kind, color in expect.items():
        with pytest.raises(TypeError):
            build_arrow_paths(kind, target, bounds, color=color)
        arrows = build_arrow_paths(kind, target, bounds)
        assert arrows[0].color == color
