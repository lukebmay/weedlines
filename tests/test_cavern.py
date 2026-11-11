# -*- coding: utf-8 -*-
"""Candidate numbers for one zig-zag cavern."""
from __future__ import division

import math
from dataclasses import astuple

from weedlib.cavern import probe

# 90-degree tooth. The two inner corners are the cavern.
TOOTH = [
    (0, 0),
    (30, 0),
    (30, 20),
    (18, 20),
    (18, 8),
    (12, 8),
    (12, 20),
    (0, 20),
]

# Open stand-in for the piece-border clip. Built here, not by the
# piece border or the surround clip. Joining the ends is a reflex.
STAND_IN = [(0, 0), (3, 0), (3, 2), (1, 2), (1, -1)]

_FLOOR = 6.0
_DEPTH = 12.0
_GAP = 4.0
_MARGIN = 2.0
_HEIGHT = 20.0


def _scale(points, scale):
    return [(point[0] * scale, point[1] * scale) for point in points]


def _comb(count):
    """One outline: *count* copies of the tooth, separated by convex lips."""
    pitch = _FLOOR + _GAP
    width = _MARGIN + count * pitch + _MARGIN
    points = [(0.0, 0.0), (width, 0.0), (width, _HEIGHT)]
    x = width - _MARGIN
    for _ in range(count):
        right = x
        left = x - _FLOOR
        points.append((right, _HEIGHT))
        points.append((right, _HEIGHT - _DEPTH))
        points.append((left, _HEIGHT - _DEPTH))
        points.append((left, _HEIGHT))
        x = left - _GAP
    points.append((0.0, _HEIGHT))
    return points


def test_large_and_small_teeth_are_not_only_the_same_numbers():
    large = probe(TOOTH)
    small = probe(_scale(TOOTH, 0.01))
    assert len(large) == 1
    assert len(small) == 1
    assert len(astuple(large[0])) > 1
    assert astuple(large[0]) != astuple(small[0])
    assert math.isclose(large[0].length, 30.0)
    assert math.isclose(small[0].length, large[0].length * 0.01)
    assert math.isclose(large[0].turn, math.pi)
    assert math.isclose(small[0].turn, large[0].turn)
    assert not math.isclose(small[0].turn_rate, large[0].turn_rate)


def test_rectangle_has_no_cavern():
    ccw = [(0, 0), (4, 0), (4, 3), (0, 3)]
    cw = [(0, 0), (0, 3), (4, 3), (4, 0)]
    assert probe(ccw) == []
    assert probe(cw) == []
    assert probe(ccw + [ccw[0]]) == []


def test_marked_concave_hole_has_no_cavern():
    # The caller marks the hole. The walk does not search for one.
    assert len(probe(TOOTH)) == 1
    assert probe(TOOTH, hole=True) == []


def test_open_clip_stand_in_has_no_cavern():
    assert probe(STAND_IN, closed=False) == []
    assert len(probe(STAND_IN, closed=True)) == 1


def test_open_tooth_still_has_its_cavern():
    found = probe(TOOTH, closed=False)
    assert len(found) == 1
    assert math.isclose(found[0].length, 30.0)
    assert math.isclose(found[0].turn, math.pi)


def test_comb_is_one_group_per_tooth():
    found = probe(_comb(5))
    assert len(found) == 5
    for group in found:
        assert len(astuple(group)) > 1
        assert math.isclose(group.length, 30.0)
        assert math.isclose(group.turn, math.pi)
