# -*- coding: utf-8 -*-
"""Candidate numbers for each cavern on one outline."""
from __future__ import division

import math
from dataclasses import dataclass


@dataclass
class CavernCandidates:
    """Length, turn, and turn per unit length for one cavern."""

    length: float
    turn: float
    turn_rate: float


def probe(points, closed=True, hole=False):
    """Candidates for each cavern on *points*.

    *hole* is the caller's mark. When *closed* is false the
    ends are not joined, and that span is not an edge.
    """
    if hole:
        return []
    ring = _ring(points, closed)
    if len(ring) < 3:
        return []
    if closed and _signed_area(ring) < 0.0:
        ring.reverse()
    runs = _closed_runs(ring) if closed else _open_runs(ring)
    return [_candidates(ring, run, closed) for run in runs]


def _ring(points, closed):
    ring = [(float(point[0]), float(point[1])) for point in points]
    if closed and len(ring) >= 2 and ring[0] == ring[-1]:
        ring.pop()
    return ring


def _signed_area(ring):
    total = 0.0
    count = len(ring)
    for index in range(count):
        x1, y1 = ring[index]
        x2, y2 = ring[(index + 1) % count]
        total += x1 * y2 - x2 * y1
    return total * 0.5


def _turn(before, point, after):
    incoming = (point[0] - before[0], point[1] - before[1])
    outgoing = (after[0] - point[0], after[1] - point[1])
    left = math.hypot(incoming[0], incoming[1])
    right = math.hypot(outgoing[0], outgoing[1])
    if left == 0.0 or right == 0.0:
        return 0.0
    dot = (incoming[0] * outgoing[0] + incoming[1] * outgoing[1]) / (left * right)
    cross = (incoming[0] * outgoing[1] - incoming[1] * outgoing[0]) / (left * right)
    dot = max(-1.0, min(1.0, dot))
    return math.atan2(cross, dot)


def _closed_runs(ring):
    count = len(ring)
    reflex = [
        _turn(ring[index - 1], ring[index], ring[(index + 1) % count]) < 0.0
        for index in range(count)
    ]
    if not any(reflex):
        return []
    if all(reflex):
        return [list(range(count))]
    start = reflex.index(False)
    runs = []
    run = []
    for step in range(1, count + 1):
        index = (start + step) % count
        if reflex[index]:
            run.append(index)
        elif run:
            runs.append(run)
            run = []
    if run:
        runs.append(run)
    return runs


def _open_runs(ring):
    runs = []
    run = []
    for index in range(1, len(ring) - 1):
        if _turn(ring[index - 1], ring[index], ring[index + 1]) < 0.0:
            run.append(index)
        elif run:
            runs.append(run)
            run = []
    if run:
        runs.append(run)
    return runs


def _candidates(ring, run, closed):
    count = len(ring)
    if closed and len(run) == count:
        indices = list(range(count)) + [0]
    elif closed:
        indices = [(run[0] - 1) % count] + list(run) + [(run[-1] + 1) % count]
    else:
        indices = [run[0] - 1] + list(run) + [run[-1] + 1]
    length = 0.0
    for left, right in zip(indices, indices[1:]):
        length += math.hypot(
            ring[right][0] - ring[left][0],
            ring[right][1] - ring[left][1],
        )
    turn = 0.0
    for index in run:
        if closed:
            amount = _turn(
                ring[(index - 1) % count],
                ring[index],
                ring[(index + 1) % count],
            )
        else:
            amount = _turn(ring[index - 1], ring[index], ring[index + 1])
        turn -= amount
    rate = turn / length if length else 0.0
    return CavernCandidates(length, turn, rate)
