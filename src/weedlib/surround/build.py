# -*- coding: utf-8 -*-
"""Dilate, cluster, bridge, and smooth, then clip to the inner border."""
from __future__ import division

import math

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


def build_surrounds(subject, distance, join_gap=0.0, inner_distance=None,
                    corner_radius=None):
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
    piece border. A run that meets the border is left open, without
    the border between its ends. A run that stays inside stays
    closed. A run the clip removes is absent. ``corner_radius``
    rounds that border. Omitted, it stays square. The radius is
    user units and is capped on the inner rectangle.
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
    return _clip_to_inner_border(
        subject, surrounds, inner_distance, corner_radius)


# A point this close to a side lies on the inner rectangle.
_CLIP_EDGE = 1e-4
# Bounds at least this far inside are not clipped.
_INSIDE_MARGIN = 1e-6
# A border chord from the boolean is not this close to the surround.
_SOURCE_TOL = 1e-2


def _clip_to_inner_border(subject, surrounds, inner_distance, corner_radius):
    """Clip each surround to the inner piece border.

    The border width is not this clip. ``piece_border`` still
    builds the border, and only the inner path is used. A rounded
    corner is that path, not the bounding box.
    """
    if corner_radius is None:
        border = piece_border(subject, inner_distance, 0.0)
    else:
        border = piece_border(
            subject, inner_distance, 0.0, corner_radius)
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
    if _fully_inside(path, inner, rect):
        return [path]
    inter = path.intersected(inner)
    if inter.isEmpty():
        return []
    # A flattened curve's chords fall inside the subject. Keep the
    # lines and curves from the intersection, and drop only a side
    # of the inner border. The boolean also closes a rounded corner
    # with chords of that corner. Those chords are not the surround.
    runs, dropped = _kept_runs(inter, inner, rect, path)
    if not dropped:
        return [path]
    return [run for run in runs if run.elementCount() > 1]


def _fully_inside(path, inner, rect):
    if not _bounds_inside(path, rect):
        return False
    if not _path_has_curve(inner):
        return True
    return inner.contains(path)


def _path_has_curve(path):
    curve = QPainterPath.CurveToElement
    for index in range(path.elementCount()):
        if path.elementAt(index).type == curve:
            return True
    return False


def _bounds_inside(path, rect):
    bounds = path.boundingRect()
    margin = _INSIDE_MARGIN
    return (
        bounds.left() >= rect.left() + margin
        and bounds.top() >= rect.top() + margin
        and bounds.right() <= rect.right() - margin
        and bounds.bottom() <= rect.bottom() - margin
    )


def _kept_runs(path, inner, rect, source):
    """Open runs of lines and curves that are not the inner border.

    Nothing dropped means the surround never lay on the border,
    so the caller returns the original outline.
    """
    border_segs = None
    source_segs = None
    if _path_has_curve(inner):
        border_segs = list(_segments(inner))
        source_segs = list(_segments(source))
    runs = []
    dropped = False
    for subpath in split_painter_path(path):
        segments = list(_segments(subpath))
        if not segments:
            continue
        chains, sub_dropped = _chain_segments(
            segments, rect, border_segs, source_segs)
        dropped = dropped or sub_dropped
        for chain in chains:
            run = _path_from_segments(chain)
            if run is not None:
                runs.append(run)
    return runs, dropped


def _chain_segments(segments, rect, border_segs, source_segs):
    dropped = False
    runs = []
    current = []
    for kind, points in segments:
        if _drop_border_segment(
                kind, points, rect, border_segs, source_segs):
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


def _drop_border_segment(kind, points, rect, border_segs, source_segs):
    """True when *points* is the inner border, not the surround."""
    if border_segs is None:
        return _lies_on_rectangle(points, rect)
    if _samples_on_segments(kind, points, border_segs, _CLIP_EDGE):
        return True
    # The boolean closes the cut with the border. A chord of a
    # rounded corner is not on the surround.
    return not _samples_on_segments(kind, points, source_segs, _SOURCE_TOL)


def _samples_on_segments(kind, points, segments, tol):
    for x_coord, y_coord in _segment_samples(kind, points):
        if _dist_to_segments(x_coord, y_coord, segments) > tol:
            return False
    return True


def _segment_samples(kind, points):
    if kind == 'line':
        start, end = points[0], points[-1]
        return (
            start,
            (0.5 * (start[0] + end[0]), 0.5 * (start[1] + end[1])),
            end,
        )
    if kind == 'cubic':
        return tuple(_bezier(points, step / 4.0) for step in range(5))
    if kind == 'quad':
        return tuple(_quad_at(points, step / 4.0) for step in range(5))
    return points


def _bezier(points, t):
    u = 1.0 - t
    p0, p1, p2, p3 = points
    return (
        u * u * u * p0[0] + 3 * u * u * t * p1[0]
        + 3 * u * t * t * p2[0] + t * t * t * p3[0],
        u * u * u * p0[1] + 3 * u * u * t * p1[1]
        + 3 * u * t * t * p2[1] + t * t * t * p3[1],
    )


def _quad_at(points, t):
    u = 1.0 - t
    p0, p1, p2 = points
    return (
        u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
        u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1],
    )


def _dist_to_segments(x_coord, y_coord, segments):
    best = None
    for kind, points in segments:
        if kind == 'line':
            dist = _point_seg_dist(
                x_coord, y_coord, points[0], points[-1])
        elif kind == 'cubic':
            dist = _dist_to_curve(x_coord, y_coord, points, _bezier)
        elif kind == 'quad':
            dist = _dist_to_curve(x_coord, y_coord, points, _quad_at)
        else:
            continue
        if best is None or dist < best:
            best = dist
            if best <= _CLIP_EDGE:
                return best
    if best is None:
        return 1e9
    return best


def _dist_to_curve(x_coord, y_coord, points, at):
    steps = 32
    best_t = 0.0
    best = None
    for step in range(steps + 1):
        t = step / float(steps)
        sx, sy = at(points, t)
        dist = (sx - x_coord) * (sx - x_coord) + (sy - y_coord) * (sy - y_coord)
        if best is None or dist < best:
            best = dist
            best_t = t
    span = 1.0 / steps
    lo = best_t - span
    if lo < 0.0:
        lo = 0.0
    hi = best_t + span
    if hi > 1.0:
        hi = 1.0
    for _step in range(40):
        left = (2.0 * lo + hi) / 3.0
        right = (lo + 2.0 * hi) / 3.0
        lx, ly = at(points, left)
        rx, ry = at(points, right)
        left_dist = (lx - x_coord) ** 2 + (ly - y_coord) ** 2
        right_dist = (rx - x_coord) ** 2 + (ry - y_coord) ** 2
        if left_dist <= right_dist:
            hi = right
        else:
            lo = left
    sx, sy = at(points, 0.5 * (lo + hi))
    return math.hypot(sx - x_coord, sy - y_coord)


def _point_seg_dist(px, py, start, end):
    ax, ay = start
    bx, by = end
    dx = bx - ax
    dy = by - ay
    length_sq = dx * dx + dy * dy
    if length_sq <= 1e-18:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / length_sq
    if t < 0.0:
        t = 0.0
    elif t > 1.0:
        t = 1.0
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


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
