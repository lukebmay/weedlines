# -*- coding: utf-8 -*-
"""Self-overlap on the real border, not the painted close."""
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

def _dangling(result):
    kinds = [defect.kind for defect in result.defects]
    assert kinds == ["dangling"] * len(result.defects)
    return [(defect.target.x(), defect.target.y()) for defect in result.defects]

_BOWTIE = "M 0,0 L 10,10 L 0,10 L 10,0 Z"

_SQUARE4 = "M 0,0 L 4,0 L 4,4 L 0,4 Z"

_PAINTED = "M -1,2 L -1,5 L 5,5 L 5,2"

def _by_kind(result):
    found = {}
    for defect in result.defects:
        found.setdefault(defect.kind, []).append(
            (defect.target.x(), defect.target.y()))
    return found

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

def test_one_subpath_bowtie_is_a_self_overlap():
    result = classify_figures([{
        "id": "bowtie",
        "d": _BOWTIE,
        "closed": [True],
        "fill": "#336699",
    }])
    assert [figure.id for figure in result.figures] == ["bowtie"]
    found = _by_kind(result)
    assert set(found) == {"self-overlap"}
    assert _matches(found["self-overlap"], [(5.0, 5.0)])

def test_painted_closing_chord_is_not_a_border():
    result = classify_figures([{
        "id": "open",
        "d": _SQUARE4 + " " + _PAINTED,
        "closed": [True, False],
        "fill": "none",
    }])
    assert [figure.id for figure in result.figures] == ["open"]
    assert _dangling(result) == [(-1.0, 2.0), (5.0, 2.0)]

def _figure(path, closed):
    return classify_figures([{
        "id": "shape",
        "path": path,
        "closed": closed,
        "fill": "#222222",
    }])

def _self_overlaps(path, closed):
    return _by_kind(_figure(path, closed)).get("self-overlap", [])

def _near(points, expected, tol):
    pending = list(points)
    for ex, ey in expected:
        found = None
        for index, (x, y) in enumerate(pending):
            if abs(x - ex) <= tol and abs(y - ey) <= tol:
                found = index
                break
        if found is None:
            return False
        pending.pop(found)
    return not pending

def test_neighboring_pieces_that_cross_are_a_self_overlap():
    path = QPainterPath()
    path.moveTo(0, 0)
    path.lineTo(10, 0)
    path.cubicTo(10, 5, 0, -5, 0, 2)
    found = _by_kind(_figure(path, [False]))
    assert _near(found["self-overlap"], [(0.51, 0.0), (4.36, 0.0)], 0.01)
    assert found["dangling"] == [(0.0, 0.0), (0.0, 2.0)]

    joint = QPainterPath()
    joint.moveTo(0, 0)
    joint.lineTo(10, 0)
    joint.cubicTo(11, 1, 12, 1, 13, 0.5)
    assert _self_overlaps(joint, [False]) == []

    curves = QPainterPath()
    curves.moveTo(0, 0)
    curves.cubicTo(0, 4, 4, 4, 4, 0)
    curves.cubicTo(4, 2, 0, 2, 0, 3)
    assert _near(_self_overlaps(curves, [False]), [(0.708, 2.354)], 0.001)

def test_line_touching_a_cubic_is_not_a_self_overlap():
    def hump(y):
        path = QPainterPath()
        path.moveTo(0, 0)
        path.cubicTo(0, 3, 3, 3, 3, 0)
        path.moveTo(-1, y)
        path.lineTo(4, y)
        return path

    assert _self_overlaps(hump(2.25), [False, False]) == []
    assert _near(
        _self_overlaps(hump(2.05), [False, False]),
        [(0.849056, 2.05), (2.150944, 2.05)],
        1e-5,
    )

    flat = QPainterPath()
    flat.moveTo(0, -0.125)
    flat.cubicTo(1.0 / 3.0, 0.125, 2.0 / 3.0, -0.125, 1, 0.125)
    flat.moveTo(-0.2, 0)
    flat.lineTo(1.2, 0)
    assert _near(_self_overlaps(flat, [False, False]), [(0.5, 0.0)], 1e-4)

def test_straight_cubic_crosses_when_its_line_does():
    def hump(y):
        path = QPainterPath()
        path.moveTo(0, 0)
        path.cubicTo(0, 3, 3, 3, 3, 0)
        path.moveTo(-1, y)
        path.cubicTo(1, y, 2, y, 4, y)
        return path

    assert _self_overlaps(hump(2.25), [False, False]) == []
    assert _near(
        _self_overlaps(hump(2.05), [False, False]),
        [(0.849056, 2.05), (2.150944, 2.05)],
        1e-5,
    )

    slant = QPainterPath()
    slant.moveTo(0, -1)
    slant.cubicTo(3, -1, 7, 1, 10, 1)
    slant.moveTo(0, 0)
    slant.cubicTo(0.2, 0, 0.4, 0, 10, 0)
    assert _near(_self_overlaps(slant, [False, False]), [(5.0, 0.0)], 1e-5)

def test_flat_inflection_against_an_even_straight_cubic():
    flat = QPainterPath()
    flat.moveTo(0, -0.125)
    flat.cubicTo(1.0 / 3.0, 0.125, 2.0 / 3.0, -0.125, 1, 0.125)
    span = 1.4
    flat.moveTo(-0.2, 0)
    flat.cubicTo(
        -0.2 + span / 3.0, 0.0,
        -0.2 + 2.0 * span / 3.0, 0.0,
        1.2, 0.0,
    )
    assert _near(_self_overlaps(flat, [False, False]), [(0.5, 0.0)], 1e-4)

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

def test_uneven_cubic_just_off_the_segment_is_a_self_overlap():
    def hump(y, upper, lower):
        path = QPainterPath()
        path.moveTo(0, 0)
        path.cubicTo(0, 3, 3, 3, 3, 0)
        path.moveTo(-1, y)
        path.cubicTo(1, upper, 2, lower, 4, y)
        return path

    assert _self_overlaps(hump(2.25, 2.2501, 2.2499), [False, False]) == []
    assert _near(
        _self_overlaps(hump(2.05, 2.0501, 2.0499), [False, False]),
        [(0.849, 2.05), (2.151, 2.05)],
        1e-3,
    )

    ellipse = QPainterPath()
    ellipse.addEllipse(-10, -10, 20, 20)
    ellipse.moveTo(-12, 1)
    ellipse.cubicTo(-11.5, 1.01, -11, 0.99, 12, 1)
    assert _near(
        _self_overlaps(ellipse, [True, False]),
        [(-9.950, 1.001), (9.951, 0.999)],
        1e-3,
    )

def test_shallow_curve_side_change_is_a_self_overlap():
    flat = QPainterPath()
    flat.moveTo(0, -0.125)
    flat.cubicTo(1.0 / 3.0, 0.125, 2.0 / 3.0, -0.125, 1, 0.125)
    flat.moveTo(0, 0)
    flat.cubicTo(1.0 / 3.0, 5e-6, 2.0 / 3.0, -5e-6, 1, 0)
    assert _near(_self_overlaps(flat, [False, False]), [(0.5, 0.0)], 1e-4)

def test_collinear_cubic_past_its_ends_is_a_self_overlap():
    def pair(bow):
        path = QPainterPath()
        path.moveTo(0, 0)
        path.cubicTo(-1, bow, 2, -bow, 1, 0)
        path.moveTo(0.6, -0.4)
        path.cubicTo(1.4, -0.3, 0.9, 0.2, 1.6, 0.5)
        return path

    for bow in (0.0, 1e-6, 2e-6, 3e-6):
        assert _near(
            _self_overlaps(pair(bow), [False, False]), [(1.146, 0.0)], 1e-3,
        )

    # x=1.5 is past the curve, which ends near x=1.207.
    past = QPainterPath()
    past.moveTo(0, 0)
    past.cubicTo(-1, 1e-6, 2, -1e-6, 1, 0)
    past.moveTo(1.5, -0.4)
    past.cubicTo(1.55, -0.1, 1.45, 0.1, 1.5, 0.4)
    assert _self_overlaps(past, [False, False]) == []

def test_curves_that_only_touch_are_not_a_self_overlap():
    radius = 10.0
    outer = QPainterPath()
    outer.addEllipse(-radius, -radius, radius * 2.0, radius * 2.0)
    center = 7.0 / math.sqrt(2.0)
    inner_radius = 3.0
    inner = QPainterPath()
    inner.addEllipse(
        center - inner_radius, center - inner_radius,
        inner_radius * 2.0, inner_radius * 2.0,
    )
    meet = radius / math.sqrt(2.0)
    # Float leaves the shared midpoint just past 1e-10.
    assert _cubic_mid_miss(outer, meet, meet) <= 2e-10
    assert _cubic_mid_miss(inner, meet, meet) <= 2e-10
    path = QPainterPath()
    path.addPath(outer)
    path.addPath(inner)
    # The outlines only touch. Whether the hole stays the counter is
    # touching-hole-counter, not this check.
    assert _self_overlaps(path, [True, True]) == []

def test_self_overlap_checks_while_pieces_remain():
    # The piece walk is the long stretch of one figure. A check
    # before the first pair, or after the last, does not count.
    seen = {
        'in_walk': False,
        'hits': 0,
        'limit': 0,
        'during': 0,
    }
    real_self = figures._self_overlap_defects
    real_hits = figures._piece_hits

    def wrap_self(subpaths):
        pieces = []
        for subpath in subpaths:
            pieces.extend(figures._border_pieces(subpath))
        count = len(pieces)
        seen['limit'] = count * (count - 1) // 2
        seen['hits'] = 0
        seen['in_walk'] = True
        try:
            return real_self(subpaths)
        finally:
            seen['in_walk'] = False

    def wrap_hits(left, right):
        if seen['in_walk']:
            seen['hits'] += 1
        return real_hits(left, right)

    def focus(outline, line):
        if not seen['in_walk']:
            return
        if not 0 < seen['hits'] < seen['limit']:
            return
        seen['during'] += 1
        assert line is None

    figures._self_overlap_defects = wrap_self
    figures._piece_hits = wrap_hits
    progress.clear()
    try:
        progress.install(focus=focus)
        result = classify_figures([{
            "id": "square",
            "d": _SQUARE,
            "closed": [True],
            "fill": "none",
        }])
        assert seen['limit'] > 1
        assert seen['hits'] == seen['limit']
        assert seen['during'] >= 1
        assert result.defects == []
    finally:
        figures._self_overlap_defects = real_self
        figures._piece_hits = real_hits
        progress.clear()
