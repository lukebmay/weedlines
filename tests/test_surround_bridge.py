# -*- coding: utf-8 -*-
"""Inner bridges and their clearance. No Inkscape."""
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
from weedlib.surround import _bridge_clears

# Chord error of the round join stays under this. A miter misses by more.
_ROUNDING = 0.01


def _island():
    # Outer, a hole, and a piece in that hole. The piece's gap to the
    # hole wall is 7.
    path = QPainterPath()
    path.setFillRule(Qt.OddEvenFill)
    path.addRect(0, 0, 40, 40)
    path.addRect(10, 10, 20, 20)
    path.addRect(17, 17, 6, 6)
    return path


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


def _ellipse(x, y, width, height):
    path = QPainterPath()
    path.addEllipse(x, y, width, height)
    return path


def _chain_samples(indices):
    sample = indices[1:-1] if len(indices) > 2 else indices
    if not sample:
        sample = indices
    return sample


def test_joined_fine_rings_check_during_the_gap_walk():
    # Two fine rings. The long stretch is the overlap walk or
    # the chain walk. A check that names either ring is wrong.
    subject = QPainterPath()
    subject.addPath(_ellipse(0, 0, 400, 220))
    subject.addPath(_ellipse(420, 0, 400, 220))
    seen = {
        'phase': None,
        'gap': 0,
        'chain': 0,
        'gap_clear': 0,
        'chain_clear': 0,
        'expect_gap': 0,
        'expect_chain': 0,
    }
    real_gap = surround._gap_overlap
    real_chain = surround._chain_gap

    def wrap_gap(ring_a, ring_b):
        if not (
            surround._ring_sits_inside(ring_a, ring_b)
            or surround._ring_sits_inside(ring_b, ring_a)
        ):
            # One check per straight run, then one per edge.
            seen['expect_gap'] += (
                len(ring_a) + len(surround._straight_runs(ring_a))
            )
        seen['phase'] = 'gap'
        try:
            return real_gap(ring_a, ring_b)
        finally:
            seen['phase'] = None

    def wrap_chain(ring, indices, other):
        seen['expect_chain'] += len(_chain_samples(indices))
        seen['phase'] = 'chain'
        try:
            return real_chain(ring, indices, other)
        finally:
            seen['phase'] = None

    def focus(outline, line):
        phase = seen['phase']
        if phase is None:
            return
        seen[phase] += 1
        if outline is None and line is None:
            seen[phase + '_clear'] += 1

    surround._gap_overlap = wrap_gap
    surround._chain_gap = wrap_chain
    progress.clear()
    try:
        progress.install(focus=focus)
        surrounds = build_surrounds(subject, 8, 40)
        assert len(surrounds) == 1
        assert seen['expect_gap'] > 1
        assert seen['expect_chain'] > 1
        assert seen['gap'] == seen['expect_gap']
        assert seen['chain'] == seen['expect_chain']
        assert seen['gap_clear'] == seen['gap']
        assert seen['chain_clear'] == seen['chain']
    finally:
        surround._gap_overlap = real_gap
        surround._chain_gap = real_chain
        progress.clear()


def _joined_ellipses():
    subject = QPainterPath()
    subject.addPath(_ellipse(0, 0, 400, 220))
    subject.addPath(_ellipse(420, 0, 400, 220))
    return subject


def _open_pair_walk(seen, real_gap, real_parallel):
    def wrap_gap(ring_a, ring_b):
        if (
            surround._ring_sits_inside(ring_a, ring_b)
            or surround._ring_sits_inside(ring_b, ring_a)
        ):
            return real_gap(ring_a, ring_b)
        runs_a = surround._straight_runs(ring_a)
        runs_b = surround._straight_runs(ring_b)
        seen['in_gap'] = True
        seen['pairs'] = 0
        seen['total'] = len(runs_a) * len(runs_b)
        seen['during'] = []
        try:
            return real_gap(ring_a, ring_b)
        finally:
            seen['in_gap'] = False

    def wrap_parallel(a0, a1, b0, b1):
        if seen['in_gap']:
            seen['pairs'] += 1
        return real_parallel(a0, a1, b0, b1)

    return wrap_gap, wrap_parallel


def test_pair_walk_records_a_check_before_it_finishes():
    # The straight-run pair loop is the long stretch. A check
    # before the first comparison, or after the last, does not count.
    seen = {
        'in_gap': False,
        'pairs': 0,
        'total': 0,
        'during': [],
    }
    real_gap = surround._gap_overlap
    real_parallel = surround._parallel_overlap
    wrap_gap, wrap_parallel = _open_pair_walk(seen, real_gap, real_parallel)

    def focus(outline, line):
        if not seen['in_gap']:
            return
        if 0 < seen['pairs'] < seen['total']:
            seen['during'].append((outline, line))

    surround._gap_overlap = wrap_gap
    surround._parallel_overlap = wrap_parallel
    progress.clear()
    try:
        progress.install(focus=focus)
        surrounds = build_surrounds(_joined_ellipses(), 8, 40)
        assert len(surrounds) == 1
        assert seen['total'] > 1
        assert seen['pairs'] == seen['total']
        assert seen['during']
        assert all(
            outline is None and line is None
            for outline, line in seen['during']
        )
    finally:
        surround._gap_overlap = real_gap
        surround._parallel_overlap = real_parallel
        progress.clear()


def test_cancel_during_the_pair_walk_returns_no_outline():
    # Cancel stays false outside this sweep. It has to be raised
    # from a check while comparisons are still left.
    seen = {
        'in_gap': False,
        'pairs': 0,
        'total': 0,
        'during': [],
    }
    real_gap = surround._gap_overlap
    real_parallel = surround._parallel_overlap
    wrap_gap, wrap_parallel = _open_pair_walk(seen, real_gap, real_parallel)

    def cancel():
        return (
            seen['in_gap']
            and seen['pairs'] > 0
            and seen['pairs'] < seen['total']
        )

    surround._gap_overlap = wrap_gap
    surround._parallel_overlap = wrap_parallel
    returned = None
    progress.clear()
    try:
        progress.install(cancel=cancel)
        with pytest.raises(WeedCancelled):
            returned = build_surrounds(_joined_ellipses(), 8, 40)
        assert returned is None
        assert seen['pairs'] > 0
        assert seen['pairs'] < seen['total']
    finally:
        surround._gap_overlap = real_gap
        surround._parallel_overlap = real_parallel
        progress.clear()
