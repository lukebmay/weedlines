# -*- coding: utf-8 -*-
"""Figure check: classify, dangling ends, twins, subject, and swap."""
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

_OPEN = "M 5,6 L 15,6 L 15,20"

_SQUARE = "M 0,0 L 10,0 L 10,10 L 0,10 Z"

_OUTER = "M 0,0 L 80,0 L 80,50 L 0,50 Z"

_HOLE = "M 25,15 L 55,15 L 55,35 L 25,35"

_CLOSED_LETTER = _OUTER + " " + _HOLE + " Z"

_OPEN_HOLE = _OUTER + " " + _HOLE

def _assert_same_path(got, expected):
    assert got.elementCount() == expected.elementCount()
    for index in range(expected.elementCount()):
        left = got.elementAt(index)
        right = expected.elementAt(index)
        assert left.type == right.type
        assert left.x == pytest.approx(right.x)
        assert left.y == pytest.approx(right.y)

def _dangling(result):
    kinds = [defect.kind for defect in result.defects]
    assert kinds == ["dangling"] * len(result.defects)
    return [(defect.target.x(), defect.target.y()) for defect in result.defects]

def test_open_subpath_stays_open_when_closed_flag_is_set():
    parsed = svg_d_to_qpainterpath(_OPEN)
    result = classify_figures([{
        "id": "gap",
        "d": _OPEN,
        "closed": [True],
        "fill": "none",
    }])
    assert len(result.figures) == 1
    assert result.figures[0].fill == "none"
    _assert_same_path(result.figures[0].path, parsed)
    assert _dangling(result) == [(5.0, 6.0), (15.0, 20.0)]

def test_twin_outline_is_one_figure_and_not_a_defect():
    result = classify_figures([
        {
            "id": "keep",
            "d": _SQUARE,
            "closed": [True],
            "fill": "#336699",
        },
        {
            "id": "twin",
            "path": svg_d_to_qpainterpath(_SQUARE),
            "closed": [True],
            "fill": "none",
        },
    ])
    assert [figure.id for figure in result.figures] == ["keep"]
    assert result.figures[0].fill == "#336699"
    assert result.defects == []
    _assert_same_path(result.figures[0].path, svg_d_to_qpainterpath(_SQUARE))

def test_closed_hole_has_no_dangling_end_and_open_hole_does():
    closed = classify_figures([{
        "id": "letter",
        "d": _CLOSED_LETTER,
        "closed": [True, True],
        "fill": "#222222",
    }])
    assert [figure.id for figure in closed.figures] == ["letter"]
    assert closed.figures[0].fill == "#222222"
    assert closed.defects == []

    opened = classify_figures([{
        "id": "letter",
        "d": _OPEN_HOLE,
        "closed": [True, True],
        "fill": "#222222",
    }])
    assert len(opened.figures) == 1
    _assert_same_path(opened.figures[0].path, svg_d_to_qpainterpath(_OPEN_HOLE))
    assert _dangling(opened) == [(25.0, 15.0), (25.0, 35.0)]

def test_correction_id_is_not_a_figure():
    result = classify_figures([
        {
            "id": "weedlines-correction-1",
            "d": _OPEN,
            "closed": [False],
            "fill": "none",
        },
        {
            "id": "panel",
            "d": _SQUARE,
            "closed": [True],
            "fill": "other",
        },
    ])
    assert [figure.id for figure in result.figures] == ["panel"]
    assert result.figures[0].fill == "other"
    assert result.defects == []

_OPEN_TRI = "M 0,0 L 10,0 L 10,10"

_BLOCK = "M 8,-2 L 14,-2 L 14,4 L 8,4 Z"

_CROSS = (
    "M 100,100 L 110,100 L 110,110 L 100,110 Z "
    "M 105,105 L 115,105 L 115,115 L 105,115 Z"
)

_CORNER = "M 10,10 L 20,10 L 20,20 L 10,20 Z"

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

def _combined_records():
    return [
        {"id": "gap", "d": _OPEN_TRI, "closed": [False], "fill": "none"},
        {"id": "block", "d": _BLOCK, "closed": [True], "fill": "#336699"},
        {"id": "cross", "d": _CROSS, "closed": [True, True], "fill": "#222222"},
    ]

def test_one_result_holds_dangling_overlap_and_self_overlap():
    result = classify_figures(_combined_records())
    assert [figure.id for figure in result.figures] == ["gap", "block", "cross"]
    found = _by_kind(result)
    assert set(found) == {"dangling", "overlap", "self-overlap"}
    assert found["dangling"] == [(0.0, 0.0), (10.0, 10.0)]
    assert _matches(found["self-overlap"], [(105.0, 110.0), (110.0, 105.0)])
    assert len(found["overlap"]) == 1
    x, y = found["overlap"][0]
    assert 8.0 < x < 10.0
    assert 0.0 < y < 4.0
    assert _fill(_OPEN_TRI).contains(QPointF(x, y))
    assert _fill(_BLOCK).contains(QPointF(x, y))

def test_same_records_produce_the_same_defects():
    records = _combined_records()
    first = classify_figures(records)
    second = classify_figures(records)
    assert len(first.defects) == len(second.defects)
    for left, right in zip(first.defects, second.defects):
        assert left.kind == right.kind
        assert left.target.x() == pytest.approx(right.target.x())
        assert left.target.y() == pytest.approx(right.target.y())

_FRAME = "M 0,0 L 80,0 L 80,50 L 0,50 Z"

_LETTER_A = "M 10,10 L 24,10 L 24,30 L 10,30 Z"

_LETTER_B = "M 50,12 L 68,12 L 68,32 L 50,32 Z"

_BAND = (
    _FRAME + " M 12,12 L 28,12 L 28,28 L 12,28 Z"
    " M 50,18 L 66,18 L 66,36 L 50,36 Z"
)

_LEFT_SQ = "M 0,0 L 10,0 L 10,10 L 0,10 Z"

_RIGHT_SQ = "M 20,0 L 30,0 L 30,10 L 20,10 Z"

_OVER_A = "M 40,40 L 50,40 L 50,50 L 40,50 Z"

_OVER_B = "M 45,40 L 55,40 L 55,50 L 45,50 Z"

_PAINTED_OPEN = "M 0,20 L 10,20 L 10,30"

def _regions(records, swap):
    return subject_weed_regions(classify_figures(records).figures, swap)

def _assert_regions(regions, subject, weed, outside):
    for x, y in subject:
        assert regions.subject.contains(QPointF(x, y))
        assert not regions.weed_area.contains(QPointF(x, y))
    for x, y in weed:
        assert regions.weed_area.contains(QPointF(x, y))
        assert not regions.subject.contains(QPointF(x, y))
    for x, y in outside:
        assert not regions.subject.contains(QPointF(x, y))
        assert not regions.weed_area.contains(QPointF(x, y))

def _assert_bounds(bounds, x, y, width, height):
    assert bounds.x() == pytest.approx(x)
    assert bounds.y() == pytest.approx(y)
    assert bounds.width() == pytest.approx(width)
    assert bounds.height() == pytest.approx(height)

def test_painted_interiors_start_as_subject():
    painted = _regions([
        {"id": "color", "d": _LEFT_SQ, "closed": [True], "fill": "#ff0000"},
        {"id": "gradient", "d": _RIGHT_SQ, "closed": [True], "fill": "other"},
        {"id": "stroke", "d": _CORNER, "closed": [True], "fill": "none"},
        {"id": "open", "d": _PAINTED_OPEN, "closed": [False], "fill": "#00ff00"},
        {"id": "over-a", "d": _OVER_A, "closed": [True], "fill": "#ff0000"},
        {"id": "over-b", "d": _OVER_B, "closed": [True], "fill": "#00ff00"},
    ], False)
    _assert_regions(
        painted,
        subject=[(5.0, 5.0), (25.0, 5.0), (9.0, 21.0), (47.0, 45.0)],
        weed=[(15.0, 15.0)],
        outside=[],
    )

    bare = _regions([
        {"id": "color", "d": _LEFT_SQ, "closed": [True], "fill": "none"},
        {"id": "gradient", "d": _RIGHT_SQ, "closed": [True], "fill": "none"},
        {"id": "stroke", "d": _CORNER, "closed": [True], "fill": "none"},
        {"id": "open", "d": _PAINTED_OPEN, "closed": [False], "fill": "none"},
    ], False)
    _assert_regions(
        bare,
        subject=[(5.0, 5.0), (25.0, 5.0), (15.0, 15.0), (9.0, 21.0)],
        weed=[(15.0, 5.0)],
        outside=[],
    )

def test_weed_area_is_the_bounds_minus_the_subject():
    regions = _regions([
        {"id": "left", "d": _LEFT_SQ, "closed": [True], "fill": "#112233"},
        {"id": "right", "d": _RIGHT_SQ, "closed": [True], "fill": "#112233"},
    ], False)
    _assert_bounds(regions.bounds, 0.0, 0.0, 30.0, 10.0)
    _assert_regions(
        regions,
        subject=[(5.0, 5.0), (25.0, 5.0)],
        weed=[(15.0, 5.0)],
        outside=[(-5.0, 5.0), (40.0, 5.0), (15.0, 20.0)],
    )

def test_swap_exchanges_subject_and_weed_inside_the_bounds():
    letters = [
        {"id": "frame", "d": _FRAME, "closed": [True], "fill": "none"},
        {"id": "a", "d": _LETTER_A, "closed": [True], "fill": "#111111"},
        {"id": "b", "d": _LETTER_B, "closed": [True], "fill": "other"},
    ]
    subject = [(16.0, 20.0), (58.0, 22.0)]
    weed = [(40.0, 25.0), (2.0, 2.0)]
    outside = [(-4.0, 10.0), (40.0, 60.0)]
    first = _regions(letters, False)
    _assert_bounds(first.bounds, 0.0, 0.0, 80.0, 50.0)
    _assert_regions(first, subject, weed, outside)
    swapped = _regions(letters, True)
    _assert_bounds(swapped.bounds, 0.0, 0.0, 80.0, 50.0)
    _assert_regions(swapped, weed, subject, outside)
    restored = _regions(letters, False)
    _assert_bounds(restored.bounds, 0.0, 0.0, 80.0, 50.0)
    _assert_regions(restored, subject, weed, outside)

    band = [{
        "id": "band",
        "d": _BAND,
        "closed": [True, True, True],
        "fill": "#336699",
    }]
    band_subject = [(4.0, 25.0), (40.0, 4.0)]
    holes = [(20.0, 20.0), (58.0, 26.0)]
    band_outside = [(40.0, -5.0), (90.0, 25.0)]
    band_first = _regions(band, False)
    _assert_bounds(band_first.bounds, 0.0, 0.0, 80.0, 50.0)
    _assert_regions(band_first, band_subject, holes, band_outside)
    band_swapped = _regions(band, True)
    _assert_bounds(band_swapped.bounds, 0.0, 0.0, 80.0, 50.0)
    _assert_regions(band_swapped, holes, band_subject, band_outside)
    band_restored = _regions(band, False)
    _assert_bounds(band_restored.bounds, 0.0, 0.0, 80.0, 50.0)
    _assert_regions(band_restored, band_subject, holes, band_outside)

def test_swap_does_not_add_or_remove_defects():
    records = _combined_records()
    result = classify_figures(records)
    before = [(defect.kind, defect.target.x(), defect.target.y())
              for defect in result.defects]
    assert {kind for kind, _x, _y in before} == {
        "dangling", "overlap", "self-overlap",
    }
    subject_weed_regions(result.figures, False)
    subject_weed_regions(result.figures, True)
    after = [(defect.kind, defect.target.x(), defect.target.y())
             for defect in result.defects]
    assert after == before
    fresh = classify_figures(records)
    assert len(fresh.defects) == len(result.defects)
    for left, right in zip(result.defects, fresh.defects):
        assert left.kind == right.kind
        assert left.target.x() == pytest.approx(right.target.x())
        assert left.target.y() == pytest.approx(right.target.y())

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

def _triangle_at_radius(mid_x, mid_y, vertex_radius):
    aim = math.hypot(mid_x, mid_y)
    vx = mid_x * vertex_radius / aim
    vy = mid_y * vertex_radius / aim
    px = -mid_y / aim
    py = mid_x / aim
    base = 7.0
    spread = 1.2
    first = (
        mid_x * base / aim + spread * px,
        mid_y * base / aim + spread * py,
    )
    second = (
        mid_x * base / aim - spread * px,
        mid_y * base / aim - spread * py,
    )
    triangle = QPainterPath()
    triangle.moveTo(vx, vy)
    triangle.lineTo(first[0], first[1])
    triangle.lineTo(second[0], second[1])
    triangle.closeSubpath()
    return QPointF(vx, vy), triangle

def _triangle_centroid(triangle):
    points = []
    for index in range(triangle.elementCount()):
        element = triangle.elementAt(index)
        if element.type == QPainterPath.MoveToElement and points:
            break
        points.append((element.x, element.y))
    if len(points) >= 2 and points[0] == points[-1]:
        points.pop()
    count = float(len(points))
    return QPointF(
        sum(point[0] for point in points) / count,
        sum(point[1] for point in points) / count,
    )

def _moves(path):
    move = QPainterPath.MoveToElement
    return sum(
        1 for index in range(path.elementCount())
        if path.elementAt(index).type == move
    )

def _assert_curved_counter(ellipse, hole):
    path = QPainterPath()
    path.addPath(ellipse)
    path.addPath(hole)
    result = classify_figures([{
        "id": "ring",
        "path": path,
        "closed": [True, True],
        "fill": "#222222",
    }])
    assert [figure.id for figure in result.figures] == ["ring"]
    assert _moves(result.figures[0].path) == 2
    assert result.defects == []
    regions = subject_weed_regions(result.figures, False)
    assert _moves(regions.subject) == 2
    centroid = _triangle_centroid(hole)
    assert regions.weed_area.contains(centroid)
    assert not regions.subject.contains(centroid)
    assert not hole.contains(QPointF(0.0, 0.0))
    assert regions.subject.contains(QPointF(0.0, 0.0))
    assert not regions.weed_area.contains(QPointF(0.0, 0.0))

def test_curved_hole_in_a_chord_gap_stays_a_counter():
    radius = 10.0
    ellipse = QPainterPath()
    ellipse.addEllipse(-radius, -radius, radius * 2.0, radius * 2.0)
    ring = _ring_points(ellipse)
    chord, mx, my = _deepest_chord(ring)
    vertex, gap = _triangle_at_radius(mx, my, chord + 0.05)
    assert math.hypot(vertex.x(), vertex.y()) < radius
    assert ellipse.contains(vertex)
    assert not _point_in_ring(vertex.x(), vertex.y(), ring)
    _assert_curved_counter(ellipse, gap)

    inward_vertex, inward = _triangle_at_radius(mx, my, 9.0)
    assert ellipse.contains(inward_vertex)
    assert _point_in_ring(inward_vertex.x(), inward_vertex.y(), ring)
    _assert_curved_counter(ellipse, inward)

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

def _near_element(path, x, y, tol):
    for index in range(path.elementCount()):
        element = path.elementAt(index)
        if math.hypot(element.x - x, element.y - y) <= tol:
            return True
    return False

def test_touching_circles_keep_the_hole_as_the_counter():
    radius = 10.0
    inner_radius = 3.0

    def pair(center_dist):
        outer = QPainterPath()
        outer.addEllipse(-radius, -radius, radius * 2.0, radius * 2.0)
        center = center_dist / math.sqrt(2.0)
        inner = QPainterPath()
        inner.addEllipse(
            center - inner_radius,
            center - inner_radius,
            inner_radius * 2.0,
            inner_radius * 2.0,
        )
        path = QPainterPath()
        path.addPath(outer)
        path.addPath(inner)
        return outer, inner, path, QPointF(center, center)

    def assert_counter(center_dist):
        _outer, _inner, path, center = pair(center_dist)
        result = classify_figures([{
            "id": "ring",
            "path": path,
            "closed": [True, True],
            "fill": "#222222",
        }])
        assert [figure.id for figure in result.figures] == ["ring"]
        assert _moves(result.figures[0].path) == 2
        assert result.defects == []
        regions = subject_weed_regions(result.figures, False)
        assert regions.weed_area.contains(center)
        assert not regions.subject.contains(center)
        assert regions.subject.contains(QPointF(0.0, 0.0))
        assert not regions.weed_area.contains(QPointF(0.0, 0.0))
        assert _near_element(regions.subject, -radius, 0.0, 0.05)
        assert _near_element(
            regions.subject,
            center.x() - inner_radius,
            center.y(),
            0.05,
        )

    outer, inner, _path, center = pair(7.0)
    meet = radius / math.sqrt(2.0)
    assert math.hypot(center.x(), center.y()) == pytest.approx(7.0, abs=1e-10)
    # Float leaves the shared midpoint just past 1e-10.
    assert _cubic_mid_miss(outer, meet, meet) <= 2e-10
    assert _cubic_mid_miss(inner, meet, meet) <= 2e-10
    assert_counter(7.0)
    assert_counter(6.0)

def _two_squares():
    return [
        {
            "id": "left",
            "d": _SQUARE,
            "closed": [True],
            "fill": "#336699",
        },
        {
            "id": "right",
            "d": "M 20,0 L 30,0 L 30,10 L 20,10 Z",
            "closed": [True],
            "fill": "none",
        },
    ]

def _has_point(points, x, y):
    return any(
        abs(point[0] - x) < 1e-6 and abs(point[1] - y) < 1e-6
        for point in points
    )

def test_cancel_at_the_start_of_several_figures_raises():
    returned = None
    progress.clear()
    try:
        progress.install(cancel=lambda: True)
        with pytest.raises(WeedCancelled):
            returned = classify_figures(_two_squares())
        assert returned is None
    finally:
        progress.clear()

def test_host_records_a_check_before_several_figures_return():
    seen = []
    progress.clear()
    try:
        progress.install(
            focus=lambda outline, line: seen.append((outline, line)))
        result = classify_figures(_two_squares())
        assert [figure.id for figure in result.figures] == ["left", "right"]
        assert result.defects == []
        assert seen
        named = []
        for outline, line in seen:
            assert line is None
            if outline is None:
                continue
            assert isinstance(outline, tuple)
            assert not isinstance(outline, QPainterPath)
            assert all(
                isinstance(point, tuple) and len(point) == 2
                for point in outline
            )
            assert not (
                _has_point(outline, 0.0, 0.0)
                and _has_point(outline, 20.0, 0.0)
            )
            named.append(outline)
        assert any(_has_point(outline, 0.0, 0.0) for outline in named)
        assert any(_has_point(outline, 20.0, 0.0) for outline in named)
    finally:
        progress.clear()
