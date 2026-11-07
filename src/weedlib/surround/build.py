# -*- coding: utf-8 -*-
"""Dilate, cluster, bridge, and smooth, in today's order."""
from __future__ import division

from .. import progress
from ..qt import QPainterPath, Qt

from .offset import (
    _CHORD_PAD,
    _contained_point,
    _dilate,
    _focus_outline,
    _nested_loops,
    _outer_boundaries,
    _ring_points,
)
from .union import _bridge_outlines, _meeting_outers, _ring_sits_inside
from .bridge import _bridge_inner_outers
from .smooth import _finish_outline


def build_surrounds(subject, distance, join_gap=0.0):
    """One smoothed outline for each cluster, as closed paths.

    ``subject`` is the subject region in document user units, holes
    included. ``distance`` and ``join_gap`` are lengths in those
    units and are never negative. Zero distance is that region's
    outer boundary. A positive distance expands it with a round
    join. Surrounds that meet, overlap, or lie within ``join_gap``
    are one outline. That outline stays at least ``distance`` from
    the subject. A loop that only follows a hole is not returned.
    """
    if not isinstance(subject, QPainterPath):
        raise TypeError(
            'subject must be a QPainterPath, got: {}'.format(
                type(subject).__name__))
    distance = float(distance)
    join_gap = float(join_gap)
    if distance < 0.0:
        raise ValueError(
            'surround distance must not be negative, got: {}'.format(distance))
    if join_gap < 0.0:
        raise ValueError(
            'join gap must not be negative, got: {}'.format(join_gap))
    if subject.isEmpty():
        return []
    progress.check()
    if distance == 0.0:
        dilated = None
        outers = _meeting_outers(subject)
    else:
        dilated = _dilate(subject, distance)
        outers = _outer_boundaries(dilated)
    progress.check()
    groups = _join_groups(subject, outers, distance, join_gap)
    surrounds = []
    for group in groups:
        named = _focus_outline(group[0]) if len(group) == 1 else None
        progress.check(outline=named)
        kept, inner = _separate_inner_outers(group)
        for piece, merged in _bridge_inner_outers(
            inner, subject, distance, join_gap):
            progress.check(outline=_focus_outline(piece))
            if distance == 0.0:
                surrounds.append(piece)
            else:
                surrounds.append(_finish_outline(
                    piece, distance, dilated, not merged))
        if not kept:
            continue
        progress.check(
            outline=_focus_outline(kept[0]) if len(kept) == 1 else None)
        if len(kept) == 1:
            outline = kept[0]
        else:
            outline = _bridge_outlines(kept)
            if outline is None:
                for outer in kept:
                    progress.check(outline=_focus_outline(outer))
                    if distance == 0.0:
                        surrounds.append(outer)
                    else:
                        surrounds.append(
                            _finish_outline(outer, distance, dilated))
                continue
        progress.check(outline=_focus_outline(outline))
        if distance == 0.0:
            surrounds.append(outline)
        else:
            # A merged step is not a channel mouth. Capping it would
            # fill the pocket the bridges just kept open.
            surrounds.append(_finish_outline(
                outline, distance, dilated, len(kept) == 1))
    return surrounds


def _join_groups(subject, outers, distance, join_gap):
    """Outers whose surrounds fall within ``join_gap``, as groups.

    One wider round dilation sees every piece. A pairwise union
    would repeat a boolean per piece and still leave the crossing
    dent. Eroding that dilation back off drops a corner touch: the
    neck is thinner than the disk that has to fit.
    """
    if join_gap == 0.0 or len(outers) < 2:
        return [[outer] for outer in outers]
    progress.check()
    # Chords sit inside the arc by the scaled curve threshold.
    # Adding that threshold in user units joins a straight gap early.
    wide = _dilate(subject, distance + join_gap * 0.5 + _CHORD_PAD)
    components = _components(wide)
    groups = [[] for _component in components]
    missed = []
    for outer in outers:
        progress.check(outline=_focus_outline(outer))
        point = _contained_point(outer)
        placed = False
        if point is not None:
            for index, component in enumerate(components):
                if component.contains(point):
                    groups[index].append(outer)
                    placed = True
                    break
        if not placed:
            missed.append([outer])
    return [group for group in groups if group] + missed


def _separate_inner_outers(outers):
    """Rings that sit inside another, and the rings around them.

    A span from an inner ring to that outer cuts the frame. The
    inner rings can still bridge each other.
    """
    rings = [_ring_points(outer) for outer in outers]
    inner = []
    kept = []
    for index, outer in enumerate(outers):
        if any(
            other != index and _ring_sits_inside(rings[other], rings[index])
            for other in range(len(outers))
        ):
            inner.append(outer)
        else:
            kept.append(outer)
    return kept, inner


def _components(subject):
    """Even outlines, each with the holes it directly owns."""
    loops, depths = _nested_loops(subject)
    components = []
    for index, (subpath, _area, _point) in enumerate(loops):
        if depths[index] % 2 != 0:
            continue
        path = QPainterPath()
        path.setFillRule(Qt.OddEvenFill)
        path.addPath(subpath)
        path.closeSubpath()
        for other, (hole, _hole_area, hole_point) in enumerate(loops):
            if depths[other] != depths[index] + 1:
                continue
            if not subpath.contains(hole_point):
                continue
            path.addPath(hole)
            path.closeSubpath()
        components.append(path)
    return components
