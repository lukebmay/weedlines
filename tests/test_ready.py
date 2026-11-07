# -*- coding: utf-8 -*-
"""Correction marks: one label per present kind, at that kind origin."""
from __future__ import division

import inspect

import pytest

pytest.importorskip('PyQt5', reason='Qt binding required')

from weedlib.arrows import arrow_origin
from weedlib.ready import build_correction_marks
import weedlib.ready as ready_mod

_SQUARE = 'M 0,0 L 10,0 L 10,10 L 0,10 Z'
_OPEN = 'M 5,6 L 15,6 L 15,20'


def _square():
    return {
        'id': 'square',
        'd': _SQUARE,
        'closed': [True],
        'fill': 'none',
    }


def _open_path():
    return {
        'id': 'gap',
        'd': _OPEN,
        'closed': [True],
        'fill': 'none',
    }


def test_clear_check_has_no_labels():
    marks = build_correction_marks([_square()])
    assert marks.check.defects == []
    assert marks.arrows == {}
    assert marks.labels == []
    assert marks.bounds.left() == pytest.approx(0.0)
    assert marks.bounds.top() == pytest.approx(0.0)
    assert marks.bounds.width() == pytest.approx(10.0)
    assert marks.bounds.height() == pytest.approx(10.0)


def test_one_dangling_end_has_one_label_at_the_dangling_origin(monkeypatch):
    assert list(inspect.signature(build_correction_marks).parameters) == [
        'records',
    ]
    calls = []
    real = ready_mod.classify_figures

    def _once(records):
        calls.append(records)
        return real(records)

    monkeypatch.setattr(ready_mod, 'classify_figures', _once)
    marks = build_correction_marks([_open_path()])
    assert len(calls) == 1
    dangling = [
        defect for defect in marks.check.defects if defect.kind == 'dangling'
    ]
    assert dangling
    assert len(marks.labels) == 1
    label = marks.labels[0]
    origin = arrow_origin('dangling', marks.bounds)
    assert label.text == 'Dangling ends'
    assert label.color == '#FF00FF'
    assert label.point == pytest.approx(origin)
    assert origin == pytest.approx((marks.bounds.left(), marks.bounds.top()))
    assert list(marks.arrows) == ['dangling']
    assert len(marks.arrows['dangling']) == len(dangling)
    assert marks.arrows['dangling'][0].color == '#FF00FF'
    assert 'overlap' not in marks.arrows
    assert 'self-overlap' not in marks.arrows
