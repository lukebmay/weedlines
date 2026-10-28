# -*- coding: utf-8 -*-
"""Figure check: open paths stay open, twins collapse, dangling ends."""
from __future__ import division

import pytest

try:
    from weedlib.qt import QPainterPath  # noqa: F401
except ImportError:
    pytest.skip("Qt cannot load", allow_module_level=True)

from weedlib.figures import classify_figures
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
