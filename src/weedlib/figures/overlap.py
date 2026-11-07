# -*- coding: utf-8 -*-
"""One connected shared area between two figures."""
from __future__ import division

import math

from .. import progress
from ..keep import _subpath_is_closed
from ..qt import QPointF

from .types import Defect
from .borders import (
    _SAME_POINT_TOL,
    _border_pieces,
    _borders_cross,
    _cubic_distance,
    _param_on_piece,
    _piece_end,
    _piece_hits,
    _piece_length,
    _pieces_outline,
    _point_on_piece,
    _same_point,
    _segment_borders,
    _segment_distance,
    _tangent_on_piece,
    _unique_points,
)
from .interior import _component_points, _has_area, _interior_point, _outside_fill

# Samples along a shared border, in user units. A thin lens still meets one.
_REGION_SAMPLE = 0.05
# Stop a border walk once the remaining step is this short.
_BORDER_LINK = 1e-4
# Qt's cubic circle misses a true touch by about 6e-5 of its radius.
_CURVE_MEET = 2e-4


def _overlap_defects(left, right, left_parts, right_parts):
    # Two figures. Name neither outline.
    # Looked up on the package each call. A test replaces it.
    from . import _one_point_per_region
    progress.check()
    # Piece lists are reused for every chord of this pair. A later call
    # must not keep them: a freed path can reuse the id.
    _segment_borders.cache = {}
    shared = left.intersected(right).simplified()
    if _has_area(shared):
        # A leftover the other fill contains is not exclusive area.
        # Outlines that cross still share a partial interior.
        both_outside = (
            _outside_fill(left, right) and _outside_fill(right, left)
        )
        if not both_outside and not _outlines_cross(left_parts, right_parts):
            return []
        # A boolean vertex can sit outside one fill. That piece is not
        # shared interior, so it is not its own overlap.
        polygon_points = [
            point for point in _component_points(shared)
            if left.contains(point) and right.contains(point)
        ]
    elif not _rects_meet(left.boundingRect(), right.boundingRect()):
        return []
    else:
        polygon_points = []
    # One connected shared region is one overlap. A boolean piece of that
    # region is not another overlap, and outlines that do not cross do
    # not split it. A nearer pair of crossings is not a region.
    points = _one_point_per_region(
        left, right, left_parts, right_parts, polygon_points,
    )
    points = _unique_points(points)
    points.sort(key=lambda point: (point.x(), point.y()))
    return [Defect(kind="overlap", target=point) for point in points]


def _outlines_cross(left_parts, right_parts):
    for left in left_parts:
        for right in right_parts:
            if _borders_cross(left, right):
                return True
    return False


def _rects_meet(left, right):
    """True when the rectangles touch or overlap.

    ``QRectF.intersects`` needs a shared area, so a shared edge is a miss.
    """
    left = left.normalized()
    right = right.normalized()
    return (
        left.left() <= right.right()
        and right.left() <= left.right()
        and left.top() <= right.bottom()
        and right.top() <= left.bottom()
    )


def _one_point_per_region(left, right, left_parts, right_parts, polygon_points):
    """One interior point for each connected region of shared area.

    A crossing component is one region. So is a border that lies in the
    other fill, crossings or not. Polygon pieces that meet it through
    both fills are that same region. A piece with no such path stays
    its own region.
    """
    # Looked up on the package each call. A test replaces it.
    from . import _meets_region, _sample_sets_meet
    regions = _crossing_regions(left, right, left_parts, right_parts)
    poly_count = len(polygon_points)
    region_count = len(regions)
    total = poly_count + region_count
    if total == 0:
        return []
    parent = list(range(total))
    for index in range(poly_count):
        # One point. The chords against later points are the long stretch.
        progress.check()
        for other in range(index + 1, poly_count):
            if _segment_in_both(
                polygon_points[index], polygon_points[other], left, right,
            ):
                _unite(parent, index, other)
    for region_index, (target, samples) in enumerate(regions):
        node = poly_count + region_index
        for index, point in enumerate(polygon_points):
            # One point against this region. Name neither figure.
            progress.check()
            if _find_root(parent, index) == _find_root(parent, node):
                continue
            if _meets_region(point, target, samples, left, right):
                _unite(parent, index, node)
    for region_index in range(region_count):
        for other in range(region_index + 1, region_count):
            # One region pair. Name neither figure.
            progress.check()
            left_node = poly_count + region_index
            right_node = poly_count + other
            if _find_root(parent, left_node) == _find_root(parent, right_node):
                continue
            if _sample_sets_meet(
                regions[region_index][1], regions[other][1], left, right,
            ):
                _unite(parent, left_node, right_node)
    # Polygon points already lie in the painted intersection. Prefer one
    # of those. An empty lens keeps the crossing target instead.
    polygon_groups = {}
    for index, point in enumerate(polygon_points):
        polygon_groups.setdefault(_find_root(parent, index), []).append(point)
    region_groups = {}
    for region_index, (target, _samples) in enumerate(regions):
        root = _find_root(parent, poly_count + region_index)
        region_groups.setdefault(root, []).append(target)
    points = []
    for root in set(polygon_groups) | set(region_groups):
        pool = polygon_groups.get(root) or region_groups.get(root)
        points.append(min(pool, key=lambda point: (point.x(), point.y())))
    return points


def _meets_region(point, target, samples, left, right):
    """True when *point* and this region meet through both fills."""
    if _segment_in_both(point, target, left, right):
        return True
    if not samples:
        return False
    nearest = min(samples, key=lambda sample: _point_dist2(point, sample))
    if _segment_in_both(point, nearest, left, right):
        return True
    for sample in samples:
        if _segment_in_both(point, sample, left, right):
            return True
    return False


def _sample_sets_meet(first, second, left, right):
    """True when a straight run between the two sets lies in both fills."""
    if not first or not second:
        return False
    for start in first:
        nearest = min(second, key=lambda point: _point_dist2(start, point))
        if _segment_in_both(start, nearest, left, right):
            return True
    return False


def _point_dist2(start, end):
    dx = start.x() - end.x()
    dy = start.y() - end.y()
    return dx * dx + dy * dy


def _crossing_regions(left, right, left_parts, right_parts):
    """Each crossing component that bounds shared interior, with samples.

    The sample list lies in both fills along an arc that joins the
    component, or on a chord that does. A chord alone does not walk the
    outside of the other fill. A border with no crossing can still lie
    in the other fill and bound the same region.
    """
    left_borders, right_borders, hits = _located_crossings(
        left_parts, right_parts,
    )
    count = len(hits)
    if count < 2:
        return _contained_border_regions(
            left, right, left_parts, right_parts,
            left_borders, right_borders, hits,
        )
    parent = list(range(count))
    arcs = []
    _join_shared_arcs(
        parent, arcs, hits, left_borders, left_parts, "left", left, right,
        right_borders,
    )
    _join_shared_arcs(
        parent, arcs, hits, right_borders, right_parts, "right", left, right,
        left_borders,
    )
    groups = {}
    for index in range(count):
        root = _find_root(parent, index)
        groups.setdefault(root, []).append(index)
    regions = []
    for members in groups.values():
        if len(members) < 2:
            continue
        root = _find_root(parent, members[0])
        candidates = []
        samples = []
        for left_index, right_index, sample, arc_inside, span in arcs:
            if _find_root(parent, left_index) != root:
                continue
            mid = _midpoint(hits[left_index][0], hits[right_index][0])
            if left.contains(mid) and right.contains(mid):
                candidates.append(mid)
                samples.append(mid)
            elif sample is not None:
                nudged = _offset_into_both(sample[0], sample[1], left, right)
                if nudged is not None:
                    candidates.append(nudged)
            if not arc_inside:
                continue
            samples.extend(_border_span_samples(span, left, right))
        if not candidates:
            continue
        chosen = _region_target(hits, members, candidates, left, right)
        regions.append((chosen, samples))
    regions.extend(_contained_border_regions(
        left, right, left_parts, right_parts,
        left_borders, right_borders, hits,
    ))
    return regions


def _contained_border_regions(
    left, right, left_parts, right_parts, left_borders, right_borders, hits,
):
    """Borders that lie in the other fill and never cross it.

    A run of that border is one shared-region anchor when a walk along
    it stays in both fills. A straight jump that leaves, and cannot be
    walked around, is another region. Boolean pieces that meet a run
    through both fills are that same overlap.
    """
    left_hits = {hit[1][0] for hit in hits}
    right_hits = {hit[2][0] for hit in hits}
    regions = []
    regions.extend(_contained_side(
        left_parts, left_borders, right, left_hits, left, right,
    ))
    regions.extend(_contained_side(
        right_parts, right_borders, left, right_hits, left, right,
    ))
    return regions


def _contained_side(parts, borders, other, hit_subs, left, right):
    # Looked up on the package each call. A test replaces it.
    from . import _linked_mark_groups
    regions = []
    for sub, pieces in enumerate(borders):
        if sub in hit_subs or not _border_lies_inside(pieces, other):
            continue
        closed = _subpath_is_closed(parts[sub])
        marks = _border_span_marks(
            _full_border_span(pieces, closed), left, right,
        )
        for group in _linked_mark_groups(pieces, marks, closed, left, right):
            samples = [mark[0] for mark in group]
            regions.append((samples[0], samples))
    return regions


def _border_lies_inside(pieces, other):
    """True when every piece midpoint of this border lies in *other*."""
    if not pieces:
        return False
    for piece in pieces:
        if not other.contains(_point_on_piece(piece, 0.5)):
            return False
    return True


def _full_border_span(pieces, closed):
    if closed:
        return (pieces, (0, 0.0), (0, 0.0), True)
    last = len(pieces) - 1
    return (pieces, (0, 0.0), (last, 1.0), False)


def _border_span_samples(span, left, right):
    """Points just inside both fills along one shared border span."""
    return [mark[0] for mark in _border_span_marks(span, left, right)]


def _border_span_marks(span, left, right):
    """Those points, in border order, with the piece and parameter."""
    pieces, start, end, closed = span
    marks = []
    count = len(pieces)
    for index, t0, t1 in _span_ranges(count, start, end, closed):
        piece = pieces[index]
        length = _piece_length(piece) * (t1 - t0)
        steps = max(1, int(math.ceil(length / _REGION_SAMPLE)))
        if steps > 256:
            steps = 256
        for step in range(steps):
            t = t0 + (t1 - t0) * (step + 0.5) / float(steps)
            nudged = _offset_into_both(
                _point_on_piece(piece, t),
                _tangent_on_piece(piece, t),
                left,
                right,
            )
            if nudged is not None:
                marks.append((nudged, index, t))
    return marks


def _linked_mark_groups(pieces, marks, closed, left, right):
    """Consecutive marks that still lie in one shared region.

    A straight segment that leaves does not split a bend the border
    itself can walk while staying in both fills. The ends of a closed
    border are consecutive.
    """
    # Looked up on the package each call. A test replaces it.
    from . import _marks_share_region
    count = len(marks)
    if count == 0:
        return []
    # One border. A check on every hit inside a mark is the long work.
    outline = _pieces_outline(pieces)
    parent = list(range(count))
    limit = count if closed else count - 1
    for index in range(limit):
        progress.check(outline=outline)
        nxt = (index + 1) % count
        if _marks_share_region(
            pieces, marks[index], marks[nxt], closed and nxt == 0,
            left, right,
        ):
            _unite(parent, index, nxt)
    groups = {}
    order = []
    for index, mark in enumerate(marks):
        root = _find_root(parent, index)
        if root not in groups:
            order.append(root)
            groups[root] = []
        groups[root].append(mark)
    return [groups[root] for root in order]


def _mark_side(pieces, mark):
    """Signed offset from the border. Positive is left of the tangent."""
    piece = pieces[mark[1]]
    tangent = _tangent_on_piece(piece, mark[2])
    border = _point_on_piece(piece, mark[2])
    return (
        tangent[0] * (mark[0].y() - border.y())
        - tangent[1] * (mark[0].x() - border.x())
    )


def _same_border_side(pieces, start, end):
    """False when the offsets sit on opposite sides of the border.

    The other side of a corner is another region. A walk that flips
    the offset there has left the interior it was in.
    """
    left = _mark_side(pieces, start)
    right = _mark_side(pieces, end)
    if abs(left) <= 1e-18 or abs(right) <= 1e-18:
        return True
    return left * right > 0.0


def _marks_share_region(pieces, start, end, wrapped, left, right):
    if not _same_border_side(pieces, start, end):
        return False
    ranges = _span_ranges(
        len(pieces),
        (start[1], start[2]),
        (end[1], end[2]),
        wrapped,
    )
    if not ranges:
        return _segment_in_both(start[0], end[0], left, right)
    return _ranges_in_both(
        pieces, ranges, start[0], end[0], left, right, 0,
    )


def _ranges_in_both(pieces, ranges, start, end, left, right, depth):
    """True when a walk along *ranges* stays in both fills."""
    if start is None or end is None:
        return False
    if _segment_in_both(start, end, left, right):
        return True
    length = _ranges_length(pieces, ranges)
    if not ranges or depth >= 16 or length <= _BORDER_LINK:
        return False
    mid = _param_at_length(pieces, ranges, 0.5 * length)
    if mid is None:
        return False
    mid_point = _offset_into_both(
        _point_on_piece(pieces[mid[0]], mid[1]),
        _tangent_on_piece(pieces[mid[0]], mid[1]),
        left,
        right,
    )
    if mid_point is None or not _interior_point(mid_point, left, right):
        return False
    left_ranges, right_ranges = _split_ranges(ranges, mid)
    return (
        _ranges_in_both(
            pieces, left_ranges, start, mid_point, left, right, depth + 1,
        )
        and _ranges_in_both(
            pieces, right_ranges, mid_point, end, left, right, depth + 1,
        )
    )


def _ranges_length(pieces, ranges):
    total = 0.0
    for index, t0, t1 in ranges:
        total += _piece_length(pieces[index]) * (t1 - t0)
    return total


def _param_at_length(pieces, ranges, distance):
    """Piece and parameter *distance* along *ranges*, or None."""
    if not ranges:
        return None
    remaining = distance
    for index, t0, t1 in ranges:
        span = t1 - t0
        length = _piece_length(pieces[index]) * span
        if remaining <= length or (index, t0, t1) == ranges[-1]:
            if length <= 1e-15:
                return index, t0
            t = t0 + span * (remaining / length)
            return index, min(t1, max(t0, t))
        remaining -= length
    index, _t0, t1 = ranges[-1]
    return index, t1


def _split_ranges(ranges, mid):
    """Ranges before *mid* ``(piece, param)`` and ranges after it."""
    left = []
    right = []
    seen = False
    for index, t0, t1 in ranges:
        if seen:
            right.append((index, t0, t1))
            continue
        if index != mid[0] or mid[1] < t0 - 1e-12 or mid[1] > t1 + 1e-12:
            left.append((index, t0, t1))
            continue
        seen = True
        if mid[1] > t0 + 1e-12:
            left.append((index, t0, mid[1]))
        if t1 > mid[1] + 1e-12:
            right.append((index, mid[1], t1))
    return left, right


def _span_ranges(count, start, end, closed):
    """Piece slices from *start* ``(index, param)`` to *end*, in order."""
    if count <= 0:
        return []
    start_at = start[0] + min(1.0, max(0.0, start[1]))
    end_at = end[0] + min(1.0, max(0.0, end[1]))
    if closed and end_at <= start_at + 1e-15:
        end_at += count
    if end_at <= start_at + 1e-15:
        return []
    if not closed:
        end_at = min(end_at, count - 1e-12)
        start_at = min(max(start_at, 0.0), end_at)
    first = int(math.floor(start_at))
    last = int(math.floor(end_at - 1e-15))
    ranges = []
    for piece_at in range(first, last + 1):
        local_start = start_at - piece_at if piece_at == first else 0.0
        local_end = end_at - piece_at if piece_at == last else 1.0
        if local_end <= local_start + 1e-15:
            continue
        ranges.append((
            piece_at % count,
            local_start,
            min(1.0, local_end),
        ))
    return ranges


def _region_target(hits, members, candidates, left, right):
    """A point of this region that both fills contain."""
    count = len(members)
    cx = sum(hits[index][0].x() for index in members) / float(count)
    cy = sum(hits[index][0].y() for index in members) / float(count)
    center = QPointF(cx, cy)
    if left.contains(center) and right.contains(center):
        return center
    return min(
        candidates,
        key=lambda point: (
            math.hypot(point.x() - cx, point.y() - cy),
            point.x(),
            point.y(),
        ),
    )


def _meet_tol(length):
    return max(_SAME_POINT_TOL, _CURVE_MEET * length)


def _slice_distance(piece, t0, t1, point):
    """Distance from *point* to the open slice, or None on a clamped end."""
    if piece[0] == "line":
        x0, y0 = piece[1]
        x1, y1 = piece[2]
        dx = x1 - x0
        dy = y1 - y0
        length2 = dx * dx + dy * dy
        if length2 <= 1e-24:
            return None
        param = ((point[0] - x0) * dx + (point[1] - y0) * dy) / length2
        if param <= t0 + 1e-9 or param >= t1 - 1e-9:
            return None
        return math.hypot(
            point[0] - (x0 + param * dx),
            point[1] - (y0 + param * dy),
        )
    param = _param_on_piece(piece, QPointF(*point))
    if param <= t0 + 1e-9 or param >= t1 - 1e-9:
        return None
    place = _point_on_piece(piece, param)
    return math.hypot(place.x() - point[0], place.y() - point[1])


def _piece_point_distance(piece, point):
    if piece[0] == "line":
        return _segment_distance(point, piece[1], piece[2])
    return _cubic_distance(piece, point)


def _span_joints(pieces, span):
    """Vertices where consecutive pieces of the span meet."""
    ranges = _span_ranges(len(pieces), span[1], span[2], span[3])
    joints = []
    last = len(ranges) - 1
    for pos, (index, t0, t1) in enumerate(ranges):
        piece = pieces[index]
        if pos > 0 and t0 <= 1e-8:
            joints.append(piece[1])
        if pos < last and t1 >= 1.0 - 1e-8:
            joints.append(_piece_end(piece))
    return joints


def _near_span_end(point, span_pieces, span):
    start = _point_on_piece(span_pieces[span[1][0]], span[1][1])
    end = _point_on_piece(span_pieces[span[2][0]], span[2][1])
    return (
        math.hypot(point[0] - start.x(), point[1] - start.y())
        <= _SAME_POINT_TOL
        or math.hypot(point[0] - end.x(), point[1] - end.y())
        <= _SAME_POINT_TOL
    )


def _span_has_touch(pieces, span, other_pieces):
    """True when the outlines meet inside the span and do not cross there.

    The hit test drops a vertex that only touches. That meeting still
    ends the shared run.
    """
    if not other_pieces:
        return False
    ranges = _span_ranges(len(pieces), span[1], span[2], span[3])
    if not ranges:
        return False
    for joint in _span_joints(pieces, span):
        if _near_span_end(joint, pieces, span):
            continue
        for other in other_pieces:
            dist = _piece_point_distance(other, joint)
            tol = _meet_tol(max(
                _piece_length(other),
                _piece_length(pieces[span[1][0]]),
            ))
            if dist <= tol:
                return True
    seen = set()
    for other in other_pieces:
        for vertex in (other[1], _piece_end(other)):
            key = (round(vertex[0], 6), round(vertex[1], 6))
            if key in seen or _near_span_end(vertex, pieces, span):
                continue
            seen.add(key)
            for index, t0, t1 in ranges:
                dist = _slice_distance(pieces[index], t0, t1, vertex)
                if dist is None:
                    continue
                tol = _meet_tol(max(
                    _piece_length(pieces[index]),
                    _piece_length(other),
                ))
                if dist <= tol:
                    return True
    return False


def _mark_distance(pieces, ranges, mark):
    """Distance along *ranges* to this mark, or the end when it is past them."""
    covered = 0.0
    for index, t0, t1 in ranges:
        length = _piece_length(pieces[index])
        if index == mark[1] and t0 - 1e-9 <= mark[2] <= t1 + 1e-9:
            return covered + length * (mark[2] - t0)
        covered += length * (t1 - t0)
    return covered


def _marks_cover_span(pieces, span, marks):
    """True when kept samples run from one end of the span to the other.

    A sample that merely falls inside does not make the whole arc one run.
    """
    ranges = _span_ranges(len(pieces), span[1], span[2], span[3])
    length = _ranges_length(pieces, ranges)
    if length <= _BORDER_LINK:
        return bool(marks)
    gap = max(_REGION_SAMPLE * 2.0, _BORDER_LINK)
    positions = [_mark_distance(pieces, ranges, mark) for mark in marks]
    if not positions or positions[0] > gap or length - positions[-1] > gap:
        return False
    for earlier, later in zip(positions, positions[1:]):
        if later - earlier > gap:
            return False
    return True


def _arc_is_one_run(pieces, span, other_pieces, left, right):
    """True when one walk along the span stays in both interiors."""
    # Looked up on the package each call. A test replaces it.
    from . import _linked_mark_groups
    if _span_has_touch(pieces, span, other_pieces):
        return False
    marks = _border_span_marks(span, left, right)
    if not _marks_cover_span(pieces, span, marks):
        return False
    groups = _linked_mark_groups(pieces, marks, False, left, right)
    return len(groups) == 1


def _join_shared_arcs(
    parent, arcs, hits, borders, parts, side, left, right, other_borders,
):
    """Join crossings while one walk along the arc stays in both interiors.

    Where that walk leaves either interior, the arc is another region.
    A nearer pair of crossings is not joined across the break.
    """
    other_pieces = []
    for group in other_borders:
        other_pieces.extend(group)
    groups = {}
    for index, hit in enumerate(hits):
        sub, piece, param = hit[1] if side == "left" else hit[2]
        groups.setdefault(sub, []).append((piece, param, index))
    for sub, items in groups.items():
        items.sort()
        if len(items) < 2:
            continue
        pieces = borders[sub]
        closed = _subpath_is_closed(parts[sub])
        pairs = [
            (items[index], items[index + 1])
            for index in range(len(items) - 1)
        ]
        if closed:
            pairs.append((items[-1], items[0]))
        for start, end in pairs:
            span = (
                pieces,
                (start[0], start[1]),
                (end[0], end[1]),
                closed,
            )
            if not _arc_is_one_run(pieces, span, other_pieces, left, right):
                continue
            _unite(parent, start[2], end[2])
            arcs.append((
                start[2],
                end[2],
                _arc_sample(
                    pieces, (start[0], start[1]), (end[0], end[1]), closed,
                ),
                True,
                span,
            ))


def _located_crossings(left_parts, right_parts):
    left_borders = [_border_pieces(subpath) for subpath in left_parts]
    right_borders = [_border_pieces(subpath) for subpath in right_parts]
    found = []
    for left_index, left_pieces in enumerate(left_borders):
        for right_index, right_pieces in enumerate(right_borders):
            for left_at, left_piece in enumerate(left_pieces):
                for right_at, right_piece in enumerate(right_pieces):
                    for point in _piece_hits(left_piece, right_piece):
                        found.append((
                            point,
                            (
                                left_index,
                                left_at,
                                _param_on_piece(left_piece, point),
                            ),
                            (
                                right_index,
                                right_at,
                                _param_on_piece(right_piece, point),
                            ),
                        ))
    unique = []
    for hit in found:
        if any(_same_point(hit[0], kept[0]) for kept in unique):
            continue
        unique.append(hit)
    return left_borders, right_borders, unique


def _find_root(parent, index):
    while parent[index] != index:
        parent[index] = parent[parent[index]]
        index = parent[index]
    return index


def _unite(parent, left, right):
    left = _find_root(parent, left)
    right = _find_root(parent, right)
    if left != right:
        parent[right] = left


def _arc_sample(pieces, start, end, closed):
    """Point and tangent halfway along the border from *start* to *end*."""
    count = len(pieces)
    if count == 0:
        return None
    start_at = start[0] + min(1.0, max(0.0, start[1]))
    end_at = end[0] + min(1.0, max(0.0, end[1]))
    if closed and end_at <= start_at + 1e-15:
        end_at += count
    if end_at <= start_at + 1e-15:
        return None
    mid = start_at + 0.5 * (end_at - start_at)
    if closed:
        mid = math.fmod(mid, count)
    piece_index = int(mid)
    if piece_index >= count:
        piece_index = 0
        param = 0.0
    else:
        param = mid - piece_index
    piece = pieces[piece_index]
    return (
        _point_on_piece(piece, param),
        _tangent_on_piece(piece, param),
    )


def _midpoint(start, end):
    return QPointF(
        0.5 * (start.x() + end.x()),
        0.5 * (start.y() + end.y()),
    )


def _segment_in_both(start, end, left, right):
    """True when the whole chord between the two points lies in both fills.

    The chord is cut where it meets either border. A fixed row of probes
    can step over a gap; the piece between two cuts cannot.
    """
    if not (left.contains(start) and right.contains(start)):
        return False
    if not (left.contains(end) and right.contains(end)):
        return False
    if _same_point(start, end):
        return True
    params = [0.0, 1.0]
    params.extend(_segment_border_params(start, end, left))
    params.extend(_segment_border_params(start, end, right))
    params.sort()
    cuts = []
    for param in params:
        if cuts and param - cuts[-1] <= 1e-8:
            continue
        cuts.append(param)
    for index in range(len(cuts) - 1):
        t = 0.5 * (cuts[index] + cuts[index + 1])
        point = QPointF(
            start.x() + (end.x() - start.x()) * t,
            start.y() + (end.y() - start.y()) * t,
        )
        if not _interior_point(point, left, right):
            return False
    return True


def _segment_border_params(start, end, path):
    """Parameters where the chord meets *path*'s border, including ends.

    A proper crossing is not enough. A gap can open at a vertex the chord
    runs through, or along an edge the chord overlaps.
    """
    params = []
    piece = ("line", (start.x(), start.y()), (end.x(), end.y()))
    for border in _segment_borders(path):
        if border[0] == "cubic":
            ends = (border[1], border[4])
        else:
            ends = (border[1], border[2])
        for point in ends:
            param = _param_on_segment(start, end, point[0], point[1])
            if param is not None:
                params.append(param)
        for hit in _piece_hits(piece, border):
            param = _param_on_segment(start, end, hit.x(), hit.y())
            if param is not None:
                params.append(param)
    return params


def _param_on_segment(start, end, x, y):
    """Parameter of ``(x, y)`` on the chord, or None when it misses."""
    dx = end.x() - start.x()
    dy = end.y() - start.y()
    length2 = dx * dx + dy * dy
    if length2 <= 1e-24:
        return None
    vx = x - start.x()
    vy = y - start.y()
    cross = vx * dy - vy * dx
    if cross * cross > 1e-12 * length2:
        return None
    param = (vx * dx + vy * dy) / length2
    if param < -1e-8 or param > 1.0 + 1e-8:
        return None
    return min(1.0, max(0.0, param))


def _offset_into_both(point, tangent, left, right):
    """Step off a border point into both fills, or None."""
    speed = math.hypot(tangent[0], tangent[1])
    if speed <= 1e-15:
        if left.contains(point) and right.contains(point):
            return point
        return None
    normal_x = -tangent[1] / speed
    normal_y = tangent[0] / speed
    for dist in (1e-4, 1e-3, 1e-2, 0.05):
        for sign in (1.0, -1.0):
            candidate = QPointF(
                point.x() + sign * normal_x * dist,
                point.y() + sign * normal_y * dist,
            )
            if left.contains(candidate) and right.contains(candidate):
                return candidate
    if left.contains(point) and right.contains(point):
        return point
    return None
