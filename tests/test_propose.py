# -*- coding: utf-8 -*-
"""Proposals: a dangling end joins its open ends. A self-overlap has no path."""
from __future__ import division

import pytest

try:
    from weedlib.figures import classify_figures
    from weedlib.propose import propose
    from weedlib.qt import QPointF
except ImportError as exc:
    pytest.skip("Qt cannot load: %s" % exc, allow_module_level=True)

_BOWTIE = "M 0,0 L 10,10 L 0,10 L 10,0 Z"
_OPEN = "M 0,0 L 5,0 L 5.01,0.01 L 4.99,-0.01 L 5.01,-0.01 L 4.99,0.01 L 10,0"
_GAP = "M 0,0 L 10,0 L 10,5"
_OUTER = "M 0,0 L 80,0 L 80,50 L 0,50 Z"
_HOLE = "M 25,15 L 55,15 L 55,35 L 25,35"


def _anchors(path):
    points = []
    for index in range(path.elementCount()):
        element = path.elementAt(index)
        points.append((element.x, element.y))
    return points


def test_figure_eight_is_kept():
    check = classify_figures([{
        "id": "eight",
        "d": _BOWTIE,
        "closed": [True],
        "fill": "#336699",
    }])
    defects = check.defects
    elements = check.figures[0].path.elementCount()
    proposals = propose(check)
    assert check.defects is defects
    assert check.figures[0].path.elementCount() == elements
    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal.defect is defects[0]
    assert proposal.defect.kind == "self-overlap"
    assert proposal.defect.target.x() == pytest.approx(5.0)
    assert proposal.defect.target.y() == pytest.approx(5.0)
    assert proposal.path is None


def test_self_overlaps_follow_the_check_and_carry_no_path():
    check = classify_figures([
        {
            "id": "eight",
            "d": _BOWTIE,
            "closed": [True],
            "fill": "#336699",
        },
        {
            "id": "open",
            "d": _OPEN,
            "closed": [False],
            "fill": "#336699",
        },
    ])
    defects = check.defects
    proposals = propose(check)
    assert check.defects is defects
    self_overlaps = [item for item in defects if item.kind == "self-overlap"]
    assert len(self_overlaps) == 2
    assert any(item.kind == "dangling" for item in defects)
    assert [item.defect for item in proposals] == list(defects)
    self_proposals = [
        item for item in proposals if item.defect.kind == "self-overlap"
    ]
    assert [item.defect for item in self_proposals] == self_overlaps
    assert [item.path for item in self_proposals] == [None, None]
    assert all(
        item.path is not None
        for item in proposals
        if item.defect.kind != "self-overlap"
    )


def test_dangling_end_joins_the_two_open_ends():
    check = classify_figures([{
        "id": "gap",
        "d": _GAP,
        "closed": [False],
        "fill": "none",
    }])
    defects = check.defects
    assert [(item.kind, item.target.x(), item.target.y()) for item in defects] == [
        ("dangling", 0.0, 0.0),
        ("dangling", 10.0, 5.0),
    ]
    elements = check.figures[0].path.elementCount()
    proposals = propose(check)
    assert check.defects is defects
    assert check.figures[0].path.elementCount() == elements
    assert [item.defect for item in proposals] == list(defects)
    expect = [(0.0, 0.0), (10.0, 0.0), (10.0, 5.0), (0.0, 0.0)]
    for proposal in proposals:
        assert proposal.path is not None
        assert _anchors(proposal.path) == pytest.approx(expect)
    fixed = classify_figures([{
        "id": "joined",
        "path": proposals[0].path,
        "closed": [True],
        "fill": "none",
    }])
    assert [item.kind for item in fixed.defects if item.kind == "dangling"] == []


def test_open_hole_joins_its_ends_and_keeps_the_outline():
    check = classify_figures([{
        "id": "letter",
        "d": _OUTER + " " + _HOLE,
        "closed": [True, False],
        "fill": "#222222",
    }])
    defects = check.defects
    assert [(item.target.x(), item.target.y()) for item in defects] == [
        (25.0, 15.0),
        (25.0, 35.0),
    ]
    proposals = propose(check)
    assert [item.defect for item in proposals] == list(defects)
    expect = [
        (0.0, 0.0), (80.0, 0.0), (80.0, 50.0), (0.0, 50.0), (0.0, 0.0),
        (25.0, 15.0), (55.0, 15.0), (55.0, 35.0), (25.0, 35.0), (25.0, 15.0),
    ]
    for proposal in proposals:
        assert _anchors(proposal.path) == pytest.approx(expect)
    fixed = classify_figures([{
        "id": "joined",
        "path": proposals[0].path,
        "closed": [True, True],
        "fill": "#222222",
    }])
    assert [item.kind for item in fixed.defects if item.kind == "dangling"] == []


def _square(element_id, d):
    return {
        "id": element_id,
        "d": d,
        "closed": [True],
        "fill": "#111111",
    }


def test_overlap_welds_the_two_figures():
    check = classify_figures([
        _square("left", "M 0,0 L 4,0 L 4,4 L 0,4 Z"),
        _square("right", "M 2,2 L 6,2 L 6,6 L 2,6 Z"),
    ])
    defects = check.defects
    assert [item.kind for item in defects] == ["overlap"]
    counts = [figure.path.elementCount() for figure in check.figures]
    proposals = propose(check)
    assert check.defects is defects
    assert [figure.path.elementCount() for figure in check.figures] == counts
    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal.defect is defects[0]
    path = proposal.path
    assert path is not None
    assert path.contains(QPointF(1, 1))
    assert path.contains(QPointF(3, 3))
    assert path.contains(QPointF(5, 5))
    assert path.contains(QPointF(5, 1)) is False
    assert path.contains(QPointF(1, 5)) is False
    fixed = classify_figures([{
        "id": "weld",
        "path": path,
        "closed": [True],
        "fill": "#111111",
    }])
    assert fixed.defects == []
