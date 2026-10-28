# -*- coding: utf-8 -*-
"""Figure check: open paths, twins, dangling ends, and overlap."""
from __future__ import division

import pytest

try:
    from weedlib.qt import QPainterPath  # noqa: F401
except ImportError:
    pytest.skip("Qt cannot load", allow_module_level=True)

from weedlib.figures import classify_figures, subject_weed_regions
from weedlib.qt import QPointF, Qt
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
_ISLANDS = "M 0,0 L 10,0 L 10,10 L 0,10 Z M 20,0 L 30,0 L 30,10 L 20,10 Z"
_BAR = "M 0,3 L 30,3 L 30,7 L 0,7 Z"
_MED = "M 20,10 L 60,10 L 60,40 L 20,40 Z"
_LENS = "M 0,0 L 10,0 L 10,10 L 0,10 Z M 5,5 L 15,5 L 15,15 L 5,15 Z"
_THROUGH = "M 4,6 L 16,6 L 16,9 L 4,9 Z"
_INNER = "M 2,2 L 6,2 L 6,6 L 2,6 Z"
_CORNER = "M 10,10 L 20,10 L 20,20 L 10,20 Z"
_SHARE = "M 10,0 L 20,0 L 20,10 L 10,10 Z"
_BOWTIE = "M 0,0 L 10,10 L 0,10 L 10,0 Z"
_SQUARE4 = "M 0,0 L 4,0 L 4,4 L 0,4 Z"
_PAINTED = "M -1,2 L -1,5 L 5,5 L 5,2"


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
