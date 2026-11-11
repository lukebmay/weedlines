# -*- coding: utf-8 -*-
"""Self-overlap proposals carry no replacement path."""
from __future__ import division

import pytest

try:
    from weedlib.figures import classify_figures
    from weedlib.propose import propose
except ImportError as exc:
    pytest.skip("Qt cannot load: %s" % exc, allow_module_level=True)

_BOWTIE = "M 0,0 L 10,10 L 0,10 L 10,0 Z"
_OPEN = "M 0,0 L 5,0 L 5.01,0.01 L 4.99,-0.01 L 5.01,-0.01 L 4.99,0.01 L 10,0"


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
    assert [item.defect for item in proposals] == self_overlaps
    assert [item.path for item in proposals] == [None, None]
