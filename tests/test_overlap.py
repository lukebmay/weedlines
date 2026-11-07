# -*- coding: utf-8 -*-
"""Separate-figure overlap: one defect for each connected shared area."""
from __future__ import division

import math

import pytest

try:
    from weedlib.qt import QPainterPath, QPointF, QTransform, Qt
except ImportError:
    pytest.skip("Qt cannot load", allow_module_level=True)

from weedlib import figures, progress
from weedlib.figures import classify_figures, subject_weed_regions
from weedlib.progress import WeedCancelled
from weedlib.svg_paths import svg_d_to_qpainterpath

_SQUARE = "M 0,0 L 10,0 L 10,10 L 0,10 Z"

_OUTER = "M 0,0 L 80,0 L 80,50 L 0,50 Z"

_HOLE = "M 25,15 L 55,15 L 55,35 L 25,35"

_CLOSED_LETTER = _OUTER + " " + _HOLE + " Z"

_ISLANDS = "M 0,0 L 10,0 L 10,10 L 0,10 Z M 20,0 L 30,0 L 30,10 L 20,10 Z"

_BAR = "M 0,3 L 30,3 L 30,7 L 0,7 Z"

_MED = "M 20,10 L 60,10 L 60,40 L 20,40 Z"

_LENS = "M 0,0 L 10,0 L 10,10 L 0,10 Z M 5,5 L 15,5 L 15,15 L 5,15 Z"

_THROUGH = "M 4,6 L 16,6 L 16,9 L 4,9 Z"

_INNER = "M 2,2 L 6,2 L 6,6 L 2,6 Z"

_CORNER = "M 10,10 L 20,10 L 20,20 L 10,20 Z"

_SHARE = "M 10,0 L 20,0 L 20,10 L 10,10 Z"

def _points(defects):
    return [(defect.target.x(), defect.target.y()) for defect in defects]

def _by_kind(result):
    found = {}
    for defect in result.defects:
        found.setdefault(defect.kind, []).append(
            (defect.target.x(), defect.target.y()))
    return found

def _fill(d):
    path = svg_d_to_qpainterpath(d)
    path.setFillRule(Qt.OddEvenFill)
    return path

def _matches(points, expected):
    pending = list(points)
    for ex, ey in expected:
        found = None
        for index, (x, y) in enumerate(pending):
            if x == pytest.approx(ex) and y == pytest.approx(ey):
                found = index
                break
        if found is None:
            return False
        pending.pop(found)
    return not pending

def test_nesting_point_touch_and_shared_boundary_are_not_overlaps():
    nested = classify_figures([
        {"id": "outer", "d": _SQUARE, "closed": [True], "fill": "#336699"},
        {"id": "inner", "d": _INNER, "closed": [True], "fill": "none"},
    ])
    assert [figure.id for figure in nested.figures] == ["outer", "inner"]
    assert nested.defects == []

    touched = classify_figures([
        {"id": "left", "d": _SQUARE, "closed": [True], "fill": "none"},
        {"id": "right", "d": _CORNER, "closed": [True], "fill": "none"},
    ])
    assert [figure.id for figure in touched.figures] == ["left", "right"]
    assert touched.defects == []

    shared = classify_figures([
        {"id": "left", "d": _SQUARE, "closed": [True], "fill": "none"},
        {"id": "right", "d": _SHARE, "closed": [True], "fill": "none"},
    ])
    assert [figure.id for figure in shared.figures] == ["left", "right"]
    assert shared.defects == []

def test_each_connected_shared_area_is_one_overlap():
    separate = classify_figures([
        {"id": "islands", "d": _ISLANDS, "closed": [True, True], "fill": "#336699"},
        {"id": "bar", "d": _BAR, "closed": [True], "fill": "none"},
    ])
    assert [figure.id for figure in separate.figures] == ["islands", "bar"]
    assert [defect.kind for defect in separate.defects] == ["overlap", "overlap"]
    boxes = ((0.0, 10.0, 3.0, 7.0), (20.0, 30.0, 3.0, 7.0))
    seen = [False, False]
    for x, y in _points(separate.defects):
        hits = [
            index for index, (xmin, xmax, ymin, ymax) in enumerate(boxes)
            if xmin < x < xmax and ymin < y < ymax
        ]
        assert hits == [0] or hits == [1]
        assert seen[hits[0]] is False
        seen[hits[0]] = True
    assert seen == [True, True]

    band = classify_figures([
        {"id": "letter", "d": _CLOSED_LETTER, "closed": [True, True], "fill": "#222222"},
        {"id": "med", "d": _MED, "closed": [True], "fill": "none"},
    ])
    assert [figure.id for figure in band.figures] == ["letter", "med"]
    assert [defect.kind for defect in band.defects] == ["overlap"]
    x, y = _points(band.defects)[0]
    assert _fill(_CLOSED_LETTER).contains(QPointF(x, y))
    assert _fill(_MED).contains(QPointF(x, y))
    assert not (25.0 < x < 55.0 and 15.0 < y < 35.0)

    crossed = classify_figures([
        {"id": "cross", "d": _LENS, "closed": [True, True], "fill": "#336699"},
        {"id": "through", "d": _THROUGH, "closed": [True], "fill": "none"},
    ])
    found = _by_kind(crossed)
    assert _matches(found["self-overlap"], [(5.0, 10.0), (10.0, 5.0)])
    assert len(found.get("overlap", [])) == 1
    x, y = found["overlap"][0]
    assert 4.0 < x < 15.0 and 6.0 < y < 9.0
    assert "dangling" not in found

def _cubic_mid_miss(path, x, y):
    curve = QPainterPath.CurveToElement
    data = QPainterPath.CurveToDataElement
    best = None
    current = None
    index = 0
    count = path.elementCount()
    while index < count:
        element = path.elementAt(index)
        if element.type == QPainterPath.MoveToElement:
            current = (element.x, element.y)
            index += 1
            continue
        if (
            element.type == curve
            and index + 2 < count
            and path.elementAt(index + 1).type == data
            and path.elementAt(index + 2).type == data
        ):
            control = (element.x, element.y)
            follow = path.elementAt(index + 1)
            end = path.elementAt(index + 2)
            mid = _bezier_mid(
                current, control, (follow.x, follow.y), (end.x, end.y),
            )
            miss = math.hypot(mid[0] - x, mid[1] - y)
            best = miss if best is None else min(best, miss)
            current = (end.x, end.y)
            index += 3
            continue
        if element.type != data:
            current = (element.x, element.y)
        index += 1
    return best

def _bezier_mid(p0, p1, p2, p3):
    return (
        0.125 * p0[0] + 0.375 * p1[0] + 0.375 * p2[0] + 0.125 * p3[0],
        0.125 * p0[1] + 0.375 * p1[1] + 0.375 * p2[1] + 0.125 * p3[1],
    )

def _circle(cx, cy, radius):
    path = QPainterPath()
    path.addEllipse(cx - radius, cy - radius, radius * 2.0, radius * 2.0)
    return path

def _two_circles(center_dist):
    center = center_dist / math.sqrt(2.0)
    return classify_figures([
        {
            "id": "outer",
            "path": _circle(0.0, 0.0, 10.0),
            "closed": [True],
            "fill": "#336699",
        },
        {
            "id": "inner",
            "path": _circle(center, center, 3.0),
            "closed": [True],
            "fill": "none",
        },
    ])

def _assert_one_overlap(result, center_dist):
    assert [figure.id for figure in result.figures] == ["outer", "inner"]
    found = _by_kind(result)
    assert set(found) == {"overlap"}
    assert len(found["overlap"]) == 1
    x, y = found["overlap"][0]
    point = QPointF(x, y)
    center = center_dist / math.sqrt(2.0)
    assert _circle(0.0, 0.0, 10.0).contains(point)
    assert _circle(center, center, 3.0).contains(point)

def test_touching_contained_circles_are_not_a_separate_overlap():
    center = 7.0 / math.sqrt(2.0)
    meet = 10.0 / math.sqrt(2.0)
    outer = _circle(0.0, 0.0, 10.0)
    inner = _circle(center, center, 3.0)
    # Float leaves the shared midpoint just past 1e-10.
    assert _cubic_mid_miss(outer, meet, meet) <= 2e-10
    assert _cubic_mid_miss(inner, meet, meet) <= 2e-10
    touched = _two_circles(7.0)
    assert [figure.id for figure in touched.figures] == ["outer", "inner"]
    assert touched.defects == []
    assert _two_circles(6.0).defects == []
    # The outlines cross here while the inner leftover is still contained.
    _assert_one_overlap(_two_circles(7.001), 7.001)
    _assert_one_overlap(_two_circles(7.07), 7.07)
    _assert_one_overlap(_two_circles(8.0), 8.0)

def test_shallow_crossing_circles_are_one_overlap():
    # The outlines still cross after the intersection polygon loses its area.
    _assert_one_overlap(_two_circles(12.97), 12.97)
    _assert_one_overlap(_two_circles(12.96), 12.96)
    for center_dist in (13.0, 7.0):
        result = _two_circles(center_dist)
        assert [figure.id for figure in result.figures] == ["outer", "inner"]
        assert result.defects == []

def test_rotated_shallow_band_is_one_overlap():
    # Four crossings of one sliver. The segment between the ends is one region.
    outer = _circle(0.0, 0.0, 10.0)
    band = QPainterPath()
    band.addRect(-3.0, 9.99, 6.0, 0.005)
    band = QTransform().rotate(45.0).map(band)
    result = classify_figures([
        {"id": "outer", "path": outer, "closed": [True], "fill": "#336699"},
        {"id": "band", "path": band, "closed": [True], "fill": "none"},
    ])
    assert [figure.id for figure in result.figures] == ["outer", "band"]
    found = _by_kind(result)
    assert set(found) == {"overlap"}
    assert len(found["overlap"]) == 1
    x, y = found["overlap"][0]
    point = QPointF(x, y)
    assert outer.contains(point)
    assert band.contains(point)

def test_two_subpath_circles_are_two_overlaps():
    # The deep lens keeps polygon area. The shallow lens does not.
    center = 12.97 / math.sqrt(2.0)
    outer = _circle(0.0, 0.0, 10.0)
    pair = QPainterPath()
    pair.addEllipse(5.0, -3.0, 6.0, 6.0)
    pair.addEllipse(center - 3.0, center - 3.0, 6.0, 6.0)
    result = classify_figures([
        {"id": "outer", "path": outer, "closed": [True], "fill": "#336699"},
        {"id": "pair", "path": pair, "closed": [True, True], "fill": "none"},
    ])
    assert [figure.id for figure in result.figures] == ["outer", "pair"]
    found = _by_kind(result)
    assert set(found) == {"overlap"}
    assert len(found["overlap"]) == 2
    side = _circle(8.0, 0.0, 3.0)
    diagonal = _circle(center, center, 3.0)
    hits = [0, 0]
    for x, y in found["overlap"]:
        point = QPointF(x, y)
        assert outer.contains(point)
        assert pair.contains(point)
        in_side = side.contains(point)
        in_diagonal = diagonal.contains(point)
        assert in_side != in_diagonal
        hits[0 if in_side else 1] += 1
    assert hits == [1, 1]

def _arc_band(inner, outer, start, end, pieces=24):
    """Annular sector as straight pieces. The inner arc runs back."""
    path = QPainterPath()
    path.moveTo(outer * math.cos(start), outer * math.sin(start))
    for index in range(1, pieces + 1):
        angle = start + (end - start) * index / float(pieces)
        path.lineTo(outer * math.cos(angle), outer * math.sin(angle))
    for index in range(pieces + 1):
        angle = end - (end - start) * index / float(pieces)
        path.lineTo(inner * math.cos(angle), inner * math.sin(angle))
    path.closeSubpath()
    return path

def _assert_curved_band(start, end):
    # The boolean splits this one lens into pieces. The pieces are not regions.
    outer = _circle(0.0, 0.0, 10.0)
    band = _arc_band(9.99, 10.05, start, end)
    result = classify_figures([
        {"id": "outer", "path": outer, "closed": [True], "fill": "#336699"},
        {"id": "band", "path": band, "closed": [True], "fill": "none"},
    ])
    assert [figure.id for figure in result.figures] == ["outer", "band"]
    found = _by_kind(result)
    assert set(found) == {"overlap"}
    assert len(found["overlap"]) == 1
    x, y = found["overlap"][0]
    point = QPointF(x, y)
    assert outer.contains(point)
    assert band.contains(point)
    assert outer.contains(QPointF(0.0, 0.0))
    assert not band.contains(QPointF(0.0, 0.0))
    assert band.contains(QPointF(10.04, 0.0))
    assert not outer.contains(QPointF(10.04, 0.0))

def test_curved_shallow_band_is_one_overlap():
    _assert_curved_band(-1.0, 1.0)
    _assert_curved_band(-0.2, 0.2)

def _ngon(radius, sides, reverse=False):
    path = QPainterPath()
    step = 2.0 * math.pi / float(sides)
    order = range(sides)
    if reverse:
        order = range(sides - 1, -1, -1)
    started = False
    for index in order:
        angle = step * index
        point = (radius * math.cos(angle), radius * math.sin(angle))
        if not started:
            path.moveTo(*point)
            started = True
        else:
            path.lineTo(*point)
    path.closeSubpath()
    return path

def _ring(sides, inner, outer):
    path = QPainterPath()
    path.addPath(_ngon(outer, sides))
    path.addPath(_ngon(inner, sides, reverse=True))
    return path

def test_thin_ring_without_crossings_is_one_overlap():
    # The outlines do not cross. Boolean pieces of the band are one region.
    outer = _circle(0.0, 0.0, 10.0)
    for sides in (64, 48, 96):
        ring = _ring(sides, 9.99, 10.05)
        result = classify_figures([
            {"id": "outer", "path": outer, "closed": [True], "fill": "#336699"},
            {"id": "ring", "path": ring, "closed": [True, True], "fill": "none"},
        ])
        assert [figure.id for figure in result.figures] == ["outer", "ring"]
        found = _by_kind(result)
        assert set(found) == {"overlap"}
        assert len(found["overlap"]) == 1
        x, y = found["overlap"][0]
        point = QPointF(x, y)
        assert outer.contains(point)
        assert ring.contains(point)
        assert outer.contains(QPointF(0.0, 0.0))
        assert not ring.contains(QPointF(0.0, 0.0))
        assert ring.contains(QPointF(10.04, 0.0))
        assert not outer.contains(QPointF(10.04, 0.0))

def test_two_distant_shallow_lenses_are_two_overlaps():
    # Both lenses lose their polygon. They stay two regions.
    center = 12.97 / math.sqrt(2.0)
    big = QPainterPath()
    big.addEllipse(-10.0, -10.0, 20.0, 20.0)
    big.addEllipse(30.0, -10.0, 20.0, 20.0)
    smalls = QPainterPath()
    smalls.addEllipse(center - 3.0, center - 3.0, 6.0, 6.0)
    smalls.addEllipse(40.0 + center - 3.0, center - 3.0, 6.0, 6.0)
    result = classify_figures([
        {"id": "big", "path": big, "closed": [True, True], "fill": "#336699"},
        {
            "id": "smalls",
            "path": smalls,
            "closed": [True, True],
            "fill": "none",
        },
    ])
    assert [figure.id for figure in result.figures] == ["big", "smalls"]
    found = _by_kind(result)
    assert set(found) == {"overlap"}
    assert len(found["overlap"]) == 2
    left = _circle(center, center, 3.0)
    right = _circle(40.0 + center, center, 3.0)
    hits = [0, 0]
    for x, y in found["overlap"]:
        point = QPointF(x, y)
        assert big.contains(point)
        assert smalls.contains(point)
        in_left = left.contains(point)
        in_right = right.contains(point)
        assert in_left != in_right
        hits[0 if in_left else 1] += 1
    assert hits == [1, 1]

def _diamond(radius, reverse=False):
    points = [(radius, 0.0), (0.0, radius), (-radius, 0.0), (0.0, -radius)]
    if reverse:
        points.reverse()
    path = QPainterPath()
    path.moveTo(*points[0])
    for point in points[1:]:
        path.lineTo(*point)
    path.closeSubpath()
    return path

def test_four_vertex_ring_is_four_overlaps():
    # Inner vertices lie on the circle. Four lenses meet only at a point.
    outer = _circle(0.0, 0.0, 10.0)
    ring = QPainterPath()
    ring.addPath(_diamond(15.0))
    ring.addPath(_diamond(10.0, reverse=True))
    result = classify_figures([
        {"id": "outer", "path": outer, "closed": [True], "fill": "#336699"},
        {"id": "ring", "path": ring, "closed": [True, True], "fill": "none"},
    ])
    assert [figure.id for figure in result.figures] == ["outer", "ring"]
    found = _by_kind(result)
    assert set(found) == {"overlap"}
    assert len(found["overlap"]) == 4
    quadrants = [0, 0, 0, 0]
    for x, y in found["overlap"]:
        point = QPointF(x, y)
        assert outer.contains(point)
        assert ring.contains(point)
        assert abs(x) > 1.0 and abs(y) > 1.0
        quadrants[(0 if x > 0.0 else 1) + (0 if y > 0.0 else 2)] += 1
    assert quadrants == [1, 1, 1, 1]
    assert outer.contains(QPointF(0.0, 0.0))
    assert not ring.contains(QPointF(0.0, 0.0))
    assert ring.contains(QPointF(12.0, 0.0))
    assert not outer.contains(QPointF(12.0, 0.0))

def test_gapped_rectangles_are_two_overlaps():
    # The gap is narrower than a fixed probe step along the long chord.
    wide = QPainterPath()
    wide.addRect(0.0, 0.0, 30.0, 4.0)
    pair = QPainterPath()
    pair.addRect(-2.0, 1.0, 10.0, 2.0)
    pair.addRect(8.5, 1.0, 24.0, 2.0)
    result = classify_figures([
        {"id": "wide", "path": wide, "closed": [True], "fill": "#336699"},
        {"id": "pair", "path": pair, "closed": [True, True], "fill": "none"},
    ])
    assert [figure.id for figure in result.figures] == ["wide", "pair"]
    found = _by_kind(result)
    assert set(found) == {"overlap"}
    assert len(found["overlap"]) == 2
    sides = [0, 0]
    for x, y in found["overlap"]:
        point = QPointF(x, y)
        assert wide.contains(point)
        assert pair.contains(point)
        assert 1.0 < y < 3.0
        assert x < 8.0 or x > 8.5
        sides[0 if x < 8.0 else 1] += 1
    assert sides == [1, 1]
    assert wide.contains(QPointF(8.2, 2.0))
    assert not pair.contains(QPointF(8.2, 2.0))

def _closed_polygon(points):
    path = QPainterPath()
    path.moveTo(*points[0])
    for point in points[1:]:
        path.lineTo(*point)
    path.closeSubpath()
    return path

def test_bridged_rectangles_are_three_overlaps():
    # One outline. The bridge outside the wide rectangle leaves three regions.
    wide = QPainterPath()
    wide.addRect(0.0, 0.0, 30.0, 4.0)
    bridge = _closed_polygon((
        (-2.0, 1.0), (8.0, 1.0), (8.0, 6.0), (8.5, 6.0), (8.5, 1.0),
        (32.5, 1.0), (32.5, 3.0), (8.5, 3.0), (8.0, 3.0), (-2.0, 3.0),
    ))
    result = classify_figures([
        {"id": "wide", "path": wide, "closed": [True], "fill": "#336699"},
        {"id": "bridge", "path": bridge, "closed": [True], "fill": "none"},
    ])
    assert [figure.id for figure in result.figures] == ["wide", "bridge"]
    found = _by_kind(result)
    assert set(found) == {"overlap"}
    assert len(found["overlap"]) == 3
    zones = [0, 0, 0]
    for x, y in found["overlap"]:
        point = QPointF(x, y)
        assert wide.contains(point)
        assert bridge.contains(point)
        if x < 8.0:
            zones[0] += 1
        elif x > 8.5:
            zones[1] += 1
        else:
            assert y > 3.0
            zones[2] += 1
    assert zones == [1, 1, 1]
    assert wide.contains(QPointF(8.25, 2.0))
    assert not bridge.contains(QPointF(8.25, 2.0))

def test_overlap_walk_records_a_check_while_marks_remain():
    # The mark walk is the long stretch of one pair. A check
    # before that walk, or after it, does not count.
    seen = {
        'in_walk': False,
        'done': 0,
        'limit': 0,
        'walks': 0,
        'during': 0,
    }
    real_groups = figures._linked_mark_groups
    real_share = figures._marks_share_region

    def wrap_groups(pieces, marks, closed, left, right):
        limit = len(marks) if closed else max(len(marks) - 1, 0)
        seen['limit'] = limit
        seen['done'] = 0
        seen['in_walk'] = True
        if limit > 1:
            seen['walks'] += 1
        try:
            return real_groups(pieces, marks, closed, left, right)
        finally:
            seen['in_walk'] = False

    def wrap_share(pieces, start, end, wrapped, left, right):
        if seen['in_walk']:
            seen['done'] += 1
        return real_share(pieces, start, end, wrapped, left, right)

    def focus(outline, line):
        if not seen['in_walk']:
            return
        if not 0 < seen['done'] < seen['limit']:
            return
        seen['during'] += 1
        assert line is None
        if outline is not None:
            assert isinstance(outline, tuple)

    figures._linked_mark_groups = wrap_groups
    figures._marks_share_region = wrap_share
    progress.clear()
    try:
        progress.install(focus=focus)
        result = classify_figures([
            {
                "id": "left",
                "d": _SQUARE,
                "closed": [True],
                "fill": "#336699",
            },
            {
                "id": "right",
                "d": "M 5,5 L 15,5 L 15,15 L 5,15 Z",
                "closed": [True],
                "fill": "none",
            },
        ])
        assert seen['walks'] >= 1
        assert seen['during'] >= 1
        assert any(defect.kind == "overlap" for defect in result.defects)
    finally:
        figures._linked_mark_groups = real_groups
        figures._marks_share_region = real_share
        progress.clear()

def _two_lenses():
    left = QPainterPath()
    left.addRect(0.0, 0.0, 10.0, 6.0)
    left.addRect(20.0, 0.0, 10.0, 6.0)
    right = QPainterPath()
    right.addRect(4.0, 1.0, 10.0, 6.0)
    right.addRect(24.0, 1.0, 10.0, 6.0)
    return [
        {
            "id": "left",
            "path": left,
            "closed": [True, True],
            "fill": "#336699",
        },
        {
            "id": "right",
            "path": right,
            "closed": [True, True],
            "fill": "none",
        },
    ]

def test_region_merge_checks_while_a_comparison_remains():
    # The merge after the crossings compares regions. A check
    # before that merge, or after the last comparison, does not count.
    seen = {
        'in_merge': False,
        'compares': 0,
        'limit': 0,
        'record': True,
        'arm': False,
        'cancel': False,
        'during': 0,
        'events': [],
        'marks': [],
    }
    real_one = figures._one_point_per_region
    real_meet = figures._meets_region
    real_sets = figures._sample_sets_meet

    def wrap_one(left, right, left_parts, right_parts, polygon_points):
        seen['in_merge'] = True
        try:
            return real_one(
                left, right, left_parts, right_parts, polygon_points,
            )
        finally:
            seen['in_merge'] = False

    def wrap_meet(point, target, samples, left, right):
        if seen['in_merge']:
            seen['compares'] += 1
            if seen['record']:
                seen['events'].append('compare')
        return real_meet(point, target, samples, left, right)

    def wrap_sets(first, second, left, right):
        if seen['in_merge']:
            seen['compares'] += 1
            if seen['record']:
                seen['events'].append('compare')
        return real_sets(first, second, left, right)

    def focus(outline, line):
        if not seen['in_merge']:
            return
        if seen['record']:
            seen['events'].append(('check', outline, line))
        if not seen['arm']:
            return
        if not 0 < seen['compares'] < seen['limit']:
            return
        seen['during'] += 1
        seen['marks'].append((outline, line))
        seen['cancel'] = True

    figures._one_point_per_region = wrap_one
    figures._meets_region = wrap_meet
    figures._sample_sets_meet = wrap_sets
    progress.clear()
    try:
        progress.install(focus=focus, cancel=lambda: seen['cancel'])
        result = classify_figures(_two_lenses())
        compare_at = [
            index for index, event in enumerate(seen['events'])
            if event == 'compare'
        ]
        window = [
            event for index, event in enumerate(seen['events'])
            if (
                isinstance(event, tuple)
                and compare_at
                and compare_at[0] < index < compare_at[-1]
            )
        ]
        assert len(compare_at) > 1
        assert window
        assert all(
            outline is None and line is None
            for _kind, outline, line in window
        )
        assert sum(
            defect.kind == "overlap" for defect in result.defects
        ) == 2

        seen['limit'] = len(compare_at)
        seen['compares'] = 0
        seen['record'] = False
        seen['arm'] = True
        seen['cancel'] = False
        returned = None
        with pytest.raises(WeedCancelled):
            returned = classify_figures(_two_lenses())
        assert returned is None
        assert seen['during'] >= 1
        assert 0 < seen['compares'] < seen['limit']
        assert seen['marks']
        assert all(
            outline is None and line is None
            for outline, line in seen['marks']
        )
    finally:
        figures._one_point_per_region = real_one
        figures._meets_region = real_meet
        figures._sample_sets_meet = real_sets
        progress.clear()

def test_two_arm_outline_is_two_overlaps():
    # The outlines meet at the notch corner. That touch is two regions.
    outer = _circle(0.0, 0.0, 10.0)
    arms = _closed_polygon((
        (2.0, 14.0), (2.0, 0.0), (4.0, 0.0), (4.0, 8.0),
        (6.0, 8.0), (6.0, 0.0), (8.0, 0.0), (8.0, 14.0),
    ))
    result = classify_figures([
        {"id": "outer", "path": outer, "closed": [True], "fill": "#336699"},
        {"id": "arms", "path": arms, "closed": [True], "fill": "none"},
    ])
    assert [figure.id for figure in result.figures] == ["outer", "arms"]
    found = _by_kind(result)
    assert set(found) == {"overlap"}
    assert len(found["overlap"]) == 2
    sides = [0, 0]
    for x, y in found["overlap"]:
        point = QPointF(x, y)
        assert outer.contains(point)
        assert arms.contains(point)
        sides[0 if x < 6.0 else 1] += 1
    assert sides == [1, 1]
