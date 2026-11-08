# -*- coding: utf-8 -*-
"""Dilate, cluster, bridge, and smooth, then clip to the inner rectangle."""
from __future__ import division

from .. import progress
from ..paths import split_painter_path
from ..piece_border import piece_border
from ..qt import QPainterPath, Qt

from .offset import (
    _CHORD_PAD,
    _contained_point,
    _dilate,
    _focus_outline,
    _nested_loops,
    _outer_boundaries,
    _ring_points,
    _segments,
)
from .union import _bridge_outlines, _meeting_outers, _ring_sits_inside
from .bridge import _bridge_inner_outers
from .smooth import _finish_outline


def build_surrounds(subject, distance, join_gap=0.0, inner_distance=None):
    """One smoothed outline for each cluster.

    ``subject`` is the subject region in document user units, holes
    included. ``distance`` and ``join_gap`` are lengths in those
    units and are never negative. Zero distance is that region's
    outer boundary. A positive distance expands it with a round
    join. Surrounds that meet, overlap, or lie within ``join_gap``
    are one outline. That outline stays at least ``distance`` from
    the subject. A loop that only follows a hole is not returned.

    When ``inner_distance`` is omitted, those outlines stay as they
    are. When it is passed, each outline is clipped to the inner
    piece-border rectangle. A run that meets the rectangle is left
    open, without the rectangle side between its ends. A run that
    stays inside stays closed. A run the clip removes is absent.
    """
    if not isinstance(subject, QPainterPath):
        raise TypeError(
            'subject must be a QPainterPath, got: {}'.format(
                type(subject).__name__))
    distance = float(distance)
    join_gap = float(join_gap)
    if inner_distance is not None:
        inner_distance = float(inner_distance)
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
    if inner_distance is None:
        return surrounds
    return _clip_to_inner_rectangle(subject, surrounds, inner_distance)


# A point this close to a side lies on the inner rectangle.
_CLIP_EDGE = 1e-4
# Bounds at least this far inside are not clipped.
_INSIDE_MARGIN = 1e-6


def _clip_to_inner_rectangle(subject, surrounds, inner_distance):
    """Clip each surround to the inner piece-border rectangle.

    The border width is not this clip. ``piece_border`` still
    builds the rectangle, and only the inner one is used.
    """
    border = piece_border(subject, inner_distance, 0.0)
    if not border:
        return []
    inner = border[0]
    rect = inner.boundingRect()
    if not rect.isValid():
        return []
    clipped = []
    for surround in surrounds:
        clipped.extend(_clip_surround(surround, inner, rect))
    return clipped


def _clip_surround(path, inner, rect):
    if _bounds_inside(path, rect):
        return [path]
    inter = path.intersected(inner)
    if inter.isEmpty():
        return []
    # A flattened curve's chords fall inside the subject. Keep the
    # lines and curves from the intersection, and drop only a side
    # of the inner rectangle.
    runs, dropped = _kept_runs(inter, rect)
    if not dropped:
        return [path]
    return [run for run in runs if run.elementCount() > 1]


def _bounds_inside(path, rect):
    bounds = path.boundingRect()
    margin = _INSIDE_MARGIN
    return (
        bounds.left() >= rect.left() + margin
        and bounds.top() >= rect.top() + margin
        and bounds.right() <= rect.right() - margin
        and bounds.bottom() <= rect.bottom() - margin
    )


def _kept_runs(path, rect):
    """Open runs of lines and curves that are not a rectangle side.

    Nothing dropped means the surround never lay on the rectangle,
    so the caller returns the original outline.
    """
    runs = []
    dropped = False
    for subpath in split_painter_path(path):
        segments = list(_segments(subpath))
        if not segments:
            continue
        chains, sub_dropped = _chain_segments(segments, rect)
        dropped = dropped or sub_dropped
        for chain in chains:
            run = _path_from_segments(chain)
            if run is not None:
                runs.append(run)
    return runs, dropped


def _chain_segments(segments, rect):
    dropped = False
    runs = []
    current = []
    for kind, points in segments:
        if _lies_on_rectangle(points, rect):
            dropped = True
            if current:
                runs.append(current)
                current = []
            continue
        current.append((kind, points))
    if current:
        runs.append(current)
    if (
        len(runs) >= 2
        and _near(runs[-1][-1][1][-1], runs[0][0][1][0])
    ):
        runs[0] = runs[-1] + runs[0]
        del runs[-1]
    return runs, dropped


def _lies_on_rectangle(points, rect):
    shared = None
    for point in points:
        sides = _sides(point, rect)
        if shared is None:
            shared = sides
        else:
            shared &= sides
        if not shared:
            return False
    return True


def _sides(point, rect):
    x_coord, y_coord = point
    edge = _CLIP_EDGE
    sides = set()
    if abs(x_coord - rect.left()) <= edge:
        sides.add('left')
    if abs(x_coord - rect.right()) <= edge:
        sides.add('right')
    if abs(y_coord - rect.top()) <= edge:
        sides.add('top')
    if abs(y_coord - rect.bottom()) <= edge:
        sides.add('bottom')
    return sides


def _near(left, right, tol=1e-6):
    return (
        abs(left[0] - right[0]) <= tol
        and abs(left[1] - right[1]) <= tol
    )


def _path_from_segments(segments):
    if not segments:
        return None
    path = QPainterPath()
    start = segments[0][1][0]
    path.moveTo(start[0], start[1])
    for kind, points in segments:
        end = points[-1]
        if kind == 'line':
            path.lineTo(end[0], end[1])
        elif kind == 'quad':
            control = points[1]
            path.quadTo(control[0], control[1], end[0], end[1])
        else:
            first = points[1]
            second = points[2]
            path.cubicTo(
                first[0], first[1], second[0], second[1], end[0], end[1])
    if _near(start, segments[-1][1][-1]):
        path.closeSubpath()
    return path


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
