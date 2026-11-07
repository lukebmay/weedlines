# -*- coding: utf-8 -*-
"""Union of surrounds that meet."""
from __future__ import division

import math

from .. import progress
from ..qt import QPainterPath, QPointF, Qt

from .offset import (
    _TANGENT_EPS,
    _closed_path,
    _distance_to_segments,
    _edge_sample,
    _focus_outline,
    _near,
    _nested_loops,
    _outer_boundaries,
    _point_inside_ring,
    _point_segment_distance,
    _ring_area,
    _ring_points,
    _ring_segments,
    _segments,
    _signed_area,
)

# A right turn steeper than this is a corner, not stroker noise.
_SHARP_TURN = 20.0


def _bridge_outlines(outers):
    """Join outlines across the gap between them.

    Each bridge is an external tangent grown from the closest points.
    The walk stops at a reflex vertex, then each outer keeps its own
    boundary between the bridges. Two convex rings have no reflex, so
    that tangent can be the hull edge across a step. The ends of the
    facing overlap are the bridges then, and the straight offset stays.
    """
    rings = [
        ring for ring in (_ring_points(outer) for outer in outers)
        if len(ring) >= 3
    ]
    if len(rings) < 2:
        return None
    pending = rings
    while len(pending) > 1:
        nearest = None
        for left in range(len(pending)):
            for right in range(left + 1, len(pending)):
                progress.check()
                gap, _ia, _ib = _closest_vertices(pending[left], pending[right])
                if nearest is None or gap < nearest[0]:
                    nearest = (gap, left, right)
        _gap, left, right = nearest
        merged = _merge_gap(pending[left], pending[right])
        if merged is None:
            return None
        pending = [
            pending[index]
            for index in range(len(pending))
            if index != left and index != right
        ]
        pending.append(merged)
    if len(pending[0]) < 3:
        return None
    return _closed_path(pending[0])


def _closest_vertices(ring_a, ring_b):
    best = None
    for index_a, point_a in enumerate(ring_a):
        progress.check()
        for index_b, point_b in enumerate(ring_b):
            gap = math.hypot(point_a[0] - point_b[0], point_a[1] - point_b[1])
            if best is None or gap < best[0]:
                best = (gap, index_a, index_b)
    return best


def _gap_tangent(ring_a, ring_b, index_a, index_b, direction):
    """One external tangent, walking out from the closest points.

    The rings advance in opposite directions. A reflex vertex is not
    a bridge end, so the walk cannot cut across a notch.
    """
    step_a = direction
    step_b = -direction
    sign_a = -float(direction)
    sign_b = float(direction)
    count_a = len(ring_a)
    count_b = len(ring_b)
    for _step in range(count_a + count_b + 3):
        moved = False
        next_a = (index_a + step_a) % count_a
        if (
            not _reflex_vertex(ring_a, next_a)
            and _cross(ring_b[index_b], ring_a[index_a], ring_a[next_a]) * sign_a
            > 1e-9
        ):
            index_a = next_a
            moved = True
            continue
        next_b = (index_b + step_b) % count_b
        if (
            not _reflex_vertex(ring_b, next_b)
            and _cross(ring_a[index_a], ring_b[index_b], ring_b[next_b]) * sign_b
            > 1e-9
        ):
            index_b = next_b
            moved = True
            continue
        if not moved:
            break
    return index_a, index_b


def _reflex_vertex(points, index):
    return _signed_turn(points, index) <= -_SHARP_TURN


def _cross(origin, first, second):
    return (
        (first[0] - origin[0]) * (second[1] - origin[1])
        - (first[1] - origin[1]) * (second[0] - origin[0])
    )


def _index_chain(count, start, end):
    indices = [start]
    cursor = start
    while cursor != end:
        cursor = (cursor + 1) % count
        indices.append(cursor)
        if len(indices) > count + 1:
            break
    return indices


def _chain_gap(ring, indices, other):
    sample = indices[1:-1] if len(indices) > 2 else indices
    if not sample:
        sample = indices
    segments = [
        (other[index], other[(index + 1) % len(other)])
        for index in range(len(other))
    ]
    total = 0.0
    for index in sample:
        progress.check()
        total += _distance_to_segments(ring[index], segments)
    return total / float(len(sample))


def _merge_gap(ring_a, ring_b):
    """One outline: the far boundary of each ring, plus two gap bridges."""
    tangent = _tangent_points(ring_a, ring_b)
    if tangent is None or _boundary_hidden(tangent, ring_a, ring_b):
        # A walk that ends on one vertex drops the rest of that ring.
        # A hull edge can also cut off a straight offset. Either way
        # the bridges are the facing overlap.
        spanned = _span_points(ring_a, ring_b)
        if spanned is not None:
            return spanned
    return tangent


def _tangent_points(ring_a, ring_b):
    """External tangents. None when either ring has one bridge end."""
    _gap, index_a, index_b = _closest_vertices(ring_a, ring_b)
    ends = [
        _gap_tangent(ring_a, ring_b, index_a, index_b, direction)
        for direction in (1, -1)
    ]
    if ends[0][0] == ends[1][0] or ends[0][1] == ends[1][1]:
        return None
    return _assemble_gap(ring_a, ring_b, {
        ends[0][0]: ends[0][1],
        ends[1][0]: ends[1][1],
    })


def _assemble_gap(ring_a, ring_b, bridges):
    if len(bridges) < 2:
        return None
    # Looked up on the package each call. A test replaces it.
    from . import _chain_gap
    first, second = list(bridges.keys())
    chain_ab = _index_chain(len(ring_a), first, second)
    chain_ba = _index_chain(len(ring_a), second, first)
    if _chain_gap(ring_a, chain_ab, ring_b) >= _chain_gap(ring_a, chain_ba, ring_b):
        far = chain_ab
    else:
        far = chain_ba
    start_b = bridges[far[-1]]
    end_b = bridges[far[0]]
    forward = _index_chain(len(ring_b), start_b, end_b)
    backward = _index_chain(len(ring_b), end_b, start_b)
    if _chain_gap(ring_b, forward, ring_a) < _chain_gap(ring_b, backward, ring_a):
        far = list(reversed(far))
        start_b = bridges[far[-1]]
        end_b = bridges[far[0]]
        forward = _index_chain(len(ring_b), start_b, end_b)
    points = [ring_a[index] for index in far]
    points.extend(ring_b[index] for index in forward)
    return points


def _parallel_overlap(a0, a1, b0, b1):
    """The facing overlap of two parallel edges, or None."""
    adx = a1[0] - a0[0]
    ady = a1[1] - a0[1]
    length_a = math.hypot(adx, ady)
    bdx = b1[0] - b0[0]
    bdy = b1[1] - b0[1]
    length_b = math.hypot(bdx, bdy)
    if length_a <= _TANGENT_EPS or length_b <= _TANGENT_EPS:
        return None
    ux = adx / length_a
    uy = ady / length_a
    if abs(ux * bdy - uy * bdx) / length_b > 1e-6:
        return None
    nx = -uy
    ny = ux
    signed = (b0[0] - a0[0]) * nx + (b0[1] - a0[1]) * ny
    signed_end = (b1[0] - a0[0]) * nx + (b1[1] - a0[1]) * ny
    if abs(signed - signed_end) > 1e-4:
        return None
    dist = abs(signed)
    if signed < 0.0:
        nx = -nx
        ny = -ny

    def along(point):
        return (point[0] - a0[0]) * ux + (point[1] - a0[1]) * uy

    lo = min(along(b0), along(b1))
    hi = max(along(b0), along(b1))
    start = max(0.0, lo)
    end = min(length_a, hi)
    if end < start + 1e-6:
        return None

    def at(t):
        return (a0[0] + ux * t, a0[1] + uy * t)

    p0 = at(start)
    p1 = at(end)
    q0 = (p0[0] + nx * dist, p0[1] + ny * dist)
    q1 = (p1[0] + nx * dist, p1[1] + ny * dist)
    return dist, end - start, p0, q0, p1, q1


def _run_continues(points, index):
    """The next edge lies on this edge. An arc chord turns off the line."""
    count = len(points)
    a0 = points[index]
    a1 = points[(index + 1) % count]
    b1 = points[(index + 2) % count]
    adx = a1[0] - a0[0]
    ady = a1[1] - a0[1]
    bdx = b1[0] - a1[0]
    bdy = b1[1] - a1[1]
    length_a = math.hypot(adx, ady)
    length_b = math.hypot(bdx, bdy)
    if length_a <= _TANGENT_EPS or length_b <= _TANGENT_EPS:
        return False
    ux = adx / length_a
    uy = ady / length_a
    if ux * bdx + uy * bdy < (1.0 - 1e-8) * length_b:
        return False
    if abs(ux * bdy - uy * bdx) > 1e-6:
        return False
    return True


def _straight_runs(ring):
    """Each run is one straight side, including across a colinear seam."""
    count = len(ring)
    if count < 2:
        return []
    continues = [_run_continues(ring, index) for index in range(count)]
    start = 0
    for index in range(count):
        if not continues[(index - 1) % count]:
            start = index
            break
    runs = []
    index = start
    for _step in range(count):
        end = index
        while continues[end]:
            nxt = (end + 1) % count
            if nxt == index:
                break
            end = nxt
        run_end = (end + 1) % count
        if not _near(ring[index], ring[run_end], 1e-12):
            runs.append((ring[index], ring[run_end]))
        nxt = (end + 1) % count
        if nxt == start:
            break
        index = nxt
    return runs


def _gap_overlap(ring_a, ring_b):
    """Longest parallel overlap that realizes the minimum separation.

    A ring inside the other is a piece in a hole, not a gap.
    """
    if _ring_sits_inside(ring_a, ring_b) or _ring_sits_inside(ring_b, ring_a):
        return None
    min_d = None
    best = None
    runs_a = _straight_runs(ring_a)
    runs_b = _straight_runs(ring_b)
    # Looked up on the package each call. A test replaces it.
    from . import _parallel_overlap
    for a0, a1 in runs_a:
        # One check per run. A check on every pair is the long work.
        progress.check()
        for b0, b1 in runs_b:
            overlap = _parallel_overlap(a0, a1, b0, b1)
            if overlap is not None:
                dist, length = overlap[0], overlap[1]
                if best is None or dist < best[0] - 1e-6 or (
                    abs(dist - best[0]) <= 1e-4 and length > best[1]
                ):
                    best = overlap
    count_a = len(ring_a)
    count_b = len(ring_b)
    for index_a in range(count_a):
        progress.check()
        a0 = ring_a[index_a]
        a1 = ring_a[(index_a + 1) % count_a]
        for index_b in range(count_b):
            b0 = ring_b[index_b]
            b1 = ring_b[(index_b + 1) % count_b]
            for point, start, end in (
                (a0, b0, b1),
                (b0, a0, a1),
            ):
                dist = _point_segment_distance(point, start, end)
                if min_d is None or dist < min_d:
                    min_d = dist
    if best is None or min_d is None:
        return None
    if best[0] > min_d + 1e-3 or best[1] <= 1e-3:
        return None
    return best


def _ring_sits_inside(outer, inner):
    """True when ``inner`` lies in ``outer``."""
    if len(inner) < 3 or len(outer) < 3:
        return False
    if abs(_ring_area(inner)) >= abs(_ring_area(outer)):
        return False
    left = min(point[0] for point in outer)
    bottom = min(point[1] for point in outer)
    right = max(point[0] for point in outer)
    top = max(point[1] for point in outer)
    for point in inner:
        if (
            point[0] < left - 1e-6
            or point[0] > right + 1e-6
            or point[1] < bottom - 1e-6
            or point[1] > top + 1e-6
        ):
            return False
    segments = _ring_segments(outer)
    for point in inner:
        if _distance_to_segments(point, segments) <= 1e-4:
            continue
        if not _point_inside_ring(point, outer):
            return False
    return True


def _min_ring_distance(ring_a, ring_b):
    best = None
    segments = _ring_segments(ring_b)
    for point in ring_a:
        progress.check()
        dist = _distance_to_segments(point, segments)
        if best is None or dist < best:
            best = dist
    segments = _ring_segments(ring_a)
    for point in ring_b:
        progress.check()
        dist = _distance_to_segments(point, segments)
        if best is None or dist < best:
            best = dist
    if best is None:
        return 0.0
    return best


def _straight_side(points, index):
    """A real offset side, including one shorter than the old cutoff of 1.

    Arc chords match their neighbors. A unit side can measure just under 1.
    """
    count = len(points)
    start = points[index]
    end = points[(index + 1) % count]
    length = math.hypot(end[0] - start[0], end[1] - start[1])
    if length <= 1e-8:
        return False
    if abs(_signed_turn(points, index)) >= _SHARP_TURN:
        return True
    if abs(_signed_turn(points, (index + 1) % count)) >= _SHARP_TURN:
        return True
    if length >= 1.0 - 1e-6:
        return True
    prev = points[(index - 1) % count]
    nxt = points[(index + 2) % count]
    prev_len = math.hypot(start[0] - prev[0], start[1] - prev[1])
    next_len = math.hypot(nxt[0] - end[0], nxt[1] - end[1])
    return length > prev_len * 2.0 and length > next_len * 2.0


def _side_samples(start, end):
    """Points on the side, including a step in from each end.

    Whole-unit steps miss a free end shorter than that step.
    """
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.hypot(dx, dy)
    if length <= 1e-12:
        return
    inset = min(0.05, length * 0.25)
    fractions = [inset / length, 0.5, 1.0 - inset / length]
    steps = int(math.ceil(length))
    for step in range(1, steps):
        fractions.append(step / float(steps))
    for fraction in fractions:
        yield (
            start[0] + dx * fraction,
            start[1] + dy * fraction,
        )


def _boundary_hidden(merged, ring_a, ring_b):
    """A straight offset that does not face the gap fell inside.

    Corner arcs inside an external tangent are the smooth outline.
    A straight side inside that tangent is the step the hull cut off.
    """
    if not merged or len(merged) < 3:
        return False
    limit = _min_ring_distance(ring_a, ring_b) + 1e-3
    for ring, other in ((ring_a, ring_b), (ring_b, ring_a)):
        other_segments = _ring_segments(other)
        count = len(ring)
        for index in range(count):
            if not _straight_side(ring, index):
                continue
            start = ring[index]
            end = ring[(index + 1) % count]
            for point in _side_samples(start, end):
                if _distance_to_segments(point, other_segments) <= limit:
                    continue
                if _point_inside_ring(point, merged):
                    return True
    return False


def _insert_points(ring, extras):
    """Ring with boundary points inserted, and each extra's index."""
    count = len(ring)
    on_vertex = {}
    additions = [[] for _index in range(count)]
    for extra_index, point in enumerate(extras):
        found = None
        for index in range(count):
            start = ring[index]
            end = ring[(index + 1) % count]
            dist = _point_segment_distance(point, start, end)
            if dist > 1e-4:
                continue
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            length_sq = dx * dx + dy * dy
            if length_sq <= 1e-18:
                t = 0.0
            else:
                t = (
                    (point[0] - start[0]) * dx + (point[1] - start[1]) * dy
                ) / length_sq
            if t < -1e-5 or t > 1.0 + 1e-5:
                continue
            found = (index, max(0.0, min(1.0, t)))
            break
        if found is None:
            return None
        edge, t = found
        if t <= 1e-6:
            on_vertex[extra_index] = edge
        elif t >= 1.0 - 1e-6:
            on_vertex[extra_index] = (edge + 1) % count
        else:
            additions[edge].append((t, extra_index))
    new_ring = []
    origin_at = {}
    extra_at = {}
    for index in range(count):
        origin_at[index] = len(new_ring)
        new_ring.append(ring[index])
        start = ring[index]
        end = ring[(index + 1) % count]
        for t, extra_index in sorted(additions[index]):
            new_ring.append((
                start[0] + (end[0] - start[0]) * t,
                start[1] + (end[1] - start[1]) * t,
            ))
            extra_at[extra_index] = len(new_ring) - 1
    for extra_index, index in on_vertex.items():
        extra_at[extra_index] = origin_at[index]
    if len(extra_at) != len(extras):
        return None
    return new_ring, extra_at


def _span_points(ring_a, ring_b):
    # Looked up on the package each call. A test replaces it.
    from . import _gap_overlap
    overlap = _gap_overlap(ring_a, ring_b)
    if overlap is None:
        return None
    _dist, _length, p0, q0, p1, q1 = overlap
    placed_a = _insert_points(ring_a, [p0, p1])
    placed_b = _insert_points(ring_b, [q0, q1])
    if placed_a is None or placed_b is None:
        return None
    ring_a, index_a = placed_a
    ring_b, index_b = placed_b
    if index_a[0] == index_a[1] or index_b[0] == index_b[1]:
        return None
    bridges = {
        index_a[0]: index_b[0],
        index_a[1]: index_b[1],
    }
    return _assemble_gap(ring_a, ring_b, bridges)


def _meeting_outers(subject):
    """Outer boundary of each cluster when the distance is zero.

    Sibling pieces share one winding-fill simplify, so a meet or an
    overlap becomes that union. A zero stroke leaves the overlap
    empty, and a pairwise union repeats a boolean per piece. One
    piece is returned as drawn. A piece in a hole is its own group.
    """
    loops, _depths = _nested_loops(subject)
    depths = _strict_depths(loops)
    groups = {}
    for index, (subpath, _area, point) in enumerate(loops):
        if depths[index] % 2 != 0:
            continue
        parent = _parent_index(loops, depths, index, point)
        groups.setdefault(parent, []).append(subpath)
    outers = []
    for group in groups.values():
        named = _focus_outline(group[0]) if len(group) == 1 else None
        progress.check(outline=named)
        outers.extend(_winding_union(group))
    return outers


def _strict_depths(loops):
    """Nest only a loop that sits inside a larger one.

    One interior probe lands in an overlap and would hide the piece
    that still sticks out. Vertices and an edge sample have to be in.
    """
    depths = []
    for index, (subpath, area, point) in enumerate(loops):
        progress.check(outline=_focus_outline(subpath))
        depth = 0
        for other, (outline, other_area, _other_point) in enumerate(loops):
            if other == index or other_area <= area:
                continue
            if _loop_inside(outline, subpath, point):
                depth += 1
        depths.append(depth)
    return depths


def _parent_index(loops, depths, index, point):
    depth = depths[index]
    if depth == 0:
        return -1
    subpath = loops[index][0]
    parent = -1
    parent_area = None
    for other, (outline, other_area, _other_point) in enumerate(loops):
        if depths[other] != depth - 1:
            continue
        if not _loop_inside(outline, subpath, point):
            continue
        if parent_area is None or other_area < parent_area:
            parent = other
            parent_area = other_area
    return parent


def _loop_inside(outer, inner, inner_point):
    if not outer.contains(inner_point):
        return False
    for kind, points in _segments(inner):
        for vertex in (points[0], points[-1]):
            if not outer.contains(QPointF(vertex[0], vertex[1])):
                return False
        sample = _edge_sample(kind, points)
        if sample is None:
            continue
        if not outer.contains(QPointF(sample[0], sample[1])):
            return False
    return True


def _winding_union(loops):
    if len(loops) == 1:
        return loops
    combined = QPainterPath()
    combined.setFillRule(Qt.WindingFill)
    for loop in loops:
        piece = loop
        if _signed_area(loop) < 0.0:
            piece = _reversed_closed(loop)
        combined.addPath(piece)
    merged = combined.simplified()
    outers = _outer_boundaries(merged)
    if not outers:
        return loops
    return outers


def _reversed_closed(path):
    commands = []
    for kind, points in _segments(path):
        commands.append((kind, points))
    if not commands:
        return path
    reversed_path = QPainterPath()
    end = commands[-1][1][-1]
    reversed_path.moveTo(end[0], end[1])
    for kind, points in reversed(commands):
        start = points[0]
        if kind == 'line':
            reversed_path.lineTo(start[0], start[1])
        elif kind == 'quad':
            control = points[1]
            reversed_path.quadTo(control[0], control[1], start[0], start[1])
        else:
            reversed_path.cubicTo(
                points[2][0], points[2][1],
                points[1][0], points[1][1],
                start[0], start[1],
            )
    reversed_path.closeSubpath()
    return reversed_path


def _signed_turn(points, index):
    count = len(points)
    previous = points[(index - 1) % count]
    point = points[index]
    nxt = points[(index + 1) % count]
    first = (point[0] - previous[0], point[1] - previous[1])
    second = (nxt[0] - point[0], nxt[1] - point[1])
    left = math.hypot(first[0], first[1])
    right = math.hypot(second[0], second[1])
    if left <= _TANGENT_EPS or right <= _TANGENT_EPS:
        return 0.0
    dot = (first[0] * second[0] + first[1] * second[1]) / (left * right)
    cross = (first[0] * second[1] - first[1] * second[0]) / (left * right)
    dot = max(-1.0, min(1.0, dot))
    return math.degrees(math.atan2(cross, dot))
