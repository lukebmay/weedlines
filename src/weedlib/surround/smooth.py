# -*- coding: utf-8 -*-
"""Fillets out to the surround distance."""
from __future__ import division

import math

from .. import progress
from ..qt import QPointF

from .offset import (
    _TANGENT_EPS,
    _boundary_segments,
    _closed_path,
    _distance_to_segments,
    _near,
    _point_inside_ring,
    _ring_points,
)
from .union import _SHARP_TURN, _index_chain, _signed_turn, _straight_side

_ARC_STEP = math.radians(4.0)
_FILLET_ERR = 0.05


def _cumulative(points):
    lengths = [0.0]
    for index in range(len(points) - 1):
        start = points[index]
        end = points[index + 1]
        lengths.append(lengths[-1] + math.hypot(end[0] - start[0], end[1] - start[1]))
    total = lengths[-1] + math.hypot(
        points[0][0] - points[-1][0], points[0][1] - points[-1][1])
    return lengths, total


def _walk(points, start, distance, direction):
    """A point ``distance`` along the ring, and the forward tangent there."""
    count = len(points)
    remaining = distance
    index = start
    for _step in range(count + 1):
        if direction > 0:
            begin = points[index % count]
            end = points[(index + 1) % count]
        else:
            end = points[index % count]
            begin = points[(index - 1) % count]
        dx = end[0] - begin[0]
        dy = end[1] - begin[1]
        length = math.hypot(dx, dy)
        if length <= _TANGENT_EPS:
            index += direction
            continue
        if remaining <= length + 1e-9:
            tangent = (dx / length, dy / length)
            scale = remaining / length
            if direction > 0:
                point = (begin[0] + dx * scale, begin[1] + dy * scale)
            else:
                point = (end[0] - dx * scale, end[1] - dy * scale)
            return point, tangent
        remaining -= length
        index += direction
    return None


def _rotate_cw(x, y, phi):
    cosine = math.cos(phi)
    sine = math.sin(phi)
    return (x * cosine + y * sine, -x * sine + y * cosine)


def _clockwise_angle(start, end):
    cross = start[0] * end[1] - start[1] * end[0]
    dot = start[0] * end[0] + start[1] * end[1]
    clockwise = -math.atan2(cross, dot)
    if clockwise < 0.0:
        clockwise += 2.0 * math.pi
    return clockwise


def _sharp_gap(points, index, sharp):
    """Arc length along the ring to the nearest other sharp corner."""
    count = len(points)
    best = None
    for direction in (1, -1):
        total = 0.0
        current = index
        for _step in range(count):
            nxt = (current + direction) % count
            total += math.hypot(
                points[nxt][0] - points[current][0],
                points[nxt][1] - points[current][1],
            )
            if nxt == index or nxt in sharp:
                break
            current = nxt
        if best is None or total < best:
            best = total
    if best is None:
        return 0.0
    return best


def _center_pair(points, index, back_a, back_b, radius):
    incoming = _walk(points, index, back_a, -1)
    outgoing = _walk(points, index, back_b, 1)
    if incoming is None or outgoing is None:
        return None
    (ax, ay), (tax, tay) = incoming
    (bx, by), (tbx, tby) = outgoing
    center_a = (ax + tay * radius, ay - tax * radius)
    center_b = (bx + tby * radius, by - tbx * radius)
    err = math.hypot(center_a[0] - center_b[0], center_a[1] - center_b[1])
    center = (
        0.5 * (center_a[0] + center_b[0]),
        0.5 * (center_a[1] + center_b[1]),
    )
    return err, (ax, ay), (bx, by), center


def _fillet_arc(center, start, end):
    toward_start = (start[0] - center[0], start[1] - center[1])
    toward_end = (end[0] - center[0], end[1] - center[1])
    phi = _clockwise_angle(toward_start, toward_end)
    # A single corner sweeps less than half a turn. A chain of
    # parallel walls meets on a semicircle, which is included.
    # Anything longer is the long way around the center.
    if phi <= 1e-3 or phi > math.pi + 1e-3:
        return None
    count = max(2, int(math.ceil(phi / _ARC_STEP - 1e-12)))
    points = [start]
    for step in range(1, count):
        angle = phi * step / float(count)
        rx, ry = _rotate_cw(toward_start[0], toward_start[1], angle)
        points.append((center[0] + rx, center[1] + ry))
    points.append(end)
    return points


def _arc_stays_out(arc, dilated):
    boundary = _boundary_segments(dilated)
    for point in arc[1:-1]:
        if not dilated.contains(QPointF(point[0], point[1])):
            continue
        if _distance_to_segments(point, boundary) > 0.05:
            return False
    return True


def _fit_fillet(points, index, radius, max_back, dilated):
    best = None
    back = 0.05
    while back <= max_back + 1e-9:
        progress.check(outline=points)
        got = _center_pair(points, index, back, back, radius)
        if got is None:
            break
        err = got[0]
        if best is None or err < best[0]:
            best = (err, back, back, got)
        if err < 1e-4:
            break
        back += 0.05
    if best is None:
        return None
    err, back_a, back_b, got = best
    base_a = back_a
    base_b = back_b
    for step_a in range(-12, 13):
        progress.check(outline=points)
        for step_b in range(-12, 13):
            trial_a = base_a + step_a * 0.01
            trial_b = base_b + step_b * 0.01
            if trial_a <= 0.02 or trial_b <= 0.02:
                continue
            if trial_a > max_back + 1e-9 or trial_b > max_back + 1e-9:
                continue
            trial = _center_pair(points, index, trial_a, trial_b, radius)
            if trial is None or trial[0] >= err:
                continue
            err = trial[0]
            back_a = trial_a
            back_b = trial_b
            got = trial
    if err > _FILLET_ERR:
        return None
    _err, start, end, center = got
    start_radius = math.hypot(start[0] - center[0], start[1] - center[1])
    end_radius = math.hypot(end[0] - center[0], end[1] - center[1])
    if abs(start_radius - radius) > 0.05 or abs(end_radius - radius) > 0.05:
        return None
    arc = _fillet_arc(center, start, end)
    if arc is None or not _arc_stays_out(arc, dilated):
        return None
    return {
        'index': index,
        'back_a': back_a,
        'back_b': back_b,
        'arc': arc,
        'mid': arc[len(arc) // 2],
        'corner': points[index],
    }


def _fillet_record(index, back_a, back_b, arc, corner):
    return {
        'index': index,
        'back_a': back_a,
        'back_b': back_b,
        'arc': arc,
        'mid': arc[len(arc) // 2],
        'corner': corner,
    }


def _junction_angles(incoming, outgoing, arc):
    """Vertex angles where the arc meets the outline tangents."""
    (_ax, _ay), (tax, tay) = incoming
    (_bx, _by), (tbx, tby) = outgoing
    first = (arc[1][0] - arc[0][0], arc[1][1] - arc[0][1])
    last = (arc[-1][0] - arc[-2][0], arc[-1][1] - arc[-2][1])

    def angle(left, right):
        left_len = math.hypot(left[0], left[1])
        right_len = math.hypot(right[0], right[1])
        if left_len <= _TANGENT_EPS or right_len <= _TANGENT_EPS:
            return 0.0
        dot = (left[0] * right[0] + left[1] * right[1]) / (left_len * right_len)
        dot = max(-1.0, min(1.0, dot))
        return math.degrees(math.acos(dot))

    at_start = angle((-tax, -tay), first)
    at_end = angle((-last[0], -last[1]), (tbx, tby))
    return at_start, at_end


def _candidate_fillet(points, index, radius, dilated, back_a, back_b, loose):
    """A fillet for these setbacks, or None when it misses the outline."""
    got = _center_pair(points, index, back_a, back_b, radius)
    if got is None:
        return None
    err, start, end, center = got
    start_radius = math.hypot(start[0] - center[0], start[1] - center[1])
    end_radius = math.hypot(end[0] - center[0], end[1] - center[1])
    if min(start_radius, end_radius) < radius - 0.05:
        return None
    if abs(start_radius - radius) > (0.12 if loose else 0.05):
        return None
    if abs(end_radius - radius) > (0.12 if loose else 0.05):
        return None
    arc = _fillet_arc(center, start, end)
    if arc is None or not _arc_stays_out(arc, dilated):
        return None
    incoming = _walk(points, index, back_a, -1)
    outgoing = _walk(points, index, back_b, 1)
    if incoming is None or outgoing is None:
        return None
    at_start, at_end = _junction_angles(incoming, outgoing, arc)
    # A step under about 30 degrees still counts as smooth.
    if loose and (at_start < 150.0 or at_end < 150.0):
        return None
    return _fillet_record(index, back_a, back_b, arc, points[index]), err


def _fit_fillet_loose(points, index, radius, max_back, dilated):
    """Wider setbacks for a crossing the equal-back search cannot seat.

    Unequal sides miss by more than the tight center tolerance. The
    turn is still owed, including when that miss stays above 0.05.
    """
    if max_back <= 0.05:
        return None
    best = None
    step = 0.2
    back = 0.1
    grid = []
    while back <= max_back + 1e-9:
        grid.append(back)
        back += step
    for back_a in grid:
        progress.check(outline=points)
        for back_b in grid:
            got = _center_pair(points, index, back_a, back_b, radius)
            if got is None:
                continue
            if best is None or got[0] < best[0]:
                best = (got[0], back_a, back_b)
    if best is None:
        return None
    err, back_a, back_b = best
    for step_a in range(-10, 11):
        progress.check(outline=points)
        for step_b in range(-10, 11):
            trial_a = back_a + step_a * 0.02
            trial_b = back_b + step_b * 0.02
            if trial_a <= 0.02 or trial_b <= 0.02:
                continue
            if trial_a > max_back + 1e-9 or trial_b > max_back + 1e-9:
                continue
            trial = _center_pair(points, index, trial_a, trial_b, radius)
            if trial is None or trial[0] >= err:
                continue
            err = trial[0]
            back_a = trial_a
            back_b = trial_b
    # Nearby setbacks can seat a center the coarse grid only approached.
    found = None
    for step_a in range(-6, 7):
        progress.check(outline=points)
        for step_b in range(-6, 7):
            trial_a = back_a + step_a * 0.02
            trial_b = back_b + step_b * 0.02
            if trial_a <= 0.02 or trial_b <= 0.02:
                continue
            if trial_a > max_back + 1e-9 or trial_b > max_back + 1e-9:
                continue
            seated = _candidate_fillet(
                points, index, radius, dilated, trial_a, trial_b, True)
            if seated is None:
                continue
            record, seat_err = seated
            if found is None or seat_err < found[0]:
                found = (seat_err, record)
    if found is None or found[0] > 0.35:
        return None
    return found[1]


def _forward_span(points, start, end):
    """Arc length from ``start`` to ``end`` along the ring."""
    lengths, total = _cumulative(points)
    if end >= start:
        return lengths[end] - lengths[start], total
    return total - lengths[start] + lengths[end], total


def _close_chains(points, failed, radius):
    """Runs of reflex corners too close for a setback each."""
    ordered = sorted(set(failed))
    count = len(ordered)
    if count < 2:
        return []
    limit = 2.0 * radius
    small = []
    for index, corner in enumerate(ordered):
        nxt = ordered[(index + 1) % count]
        gap, _total = _forward_span(points, corner, nxt)
        small.append(gap <= limit + 1e-6)
    if not any(small) or all(small):
        return []
    chains = []
    seen = [False] * count
    for index in range(count):
        if seen[index] or not small[index]:
            continue
        start = index
        while small[(start - 1) % count]:
            start = (start - 1) % count
            if start == index:
                break
        run = [ordered[start]]
        cursor = start
        seen[cursor] = True
        while small[cursor]:
            cursor = (cursor + 1) % count
            run.append(ordered[cursor])
            seen[cursor] = True
            if cursor == start:
                break
        if len(run) >= 2:
            chains.append(run)
    return chains


def _bridge_chain(points, chain, radius, dilated):
    """One turn of radius ``radius`` in place of a tight reflex chain.

    The setbacks walk out until both normals meet on that circle.
    Parallel walls closer than two radii meet only once the outline
    opens up, so the straight run between the corners is replaced
    along with them.
    """
    start_index = chain[0]
    end_index = chain[-1]
    chain_len, total = _forward_span(points, start_index, end_index)
    if chain_len <= 1e-6 or chain_len > total * 0.5:
        return None
    limit = min(total * 0.45, chain_len + 40.0 * radius)
    best = None
    back = 0.5
    while back <= limit + 1e-9:
        progress.check(outline=points)
        incoming = _walk(points, start_index, back, -1)
        outgoing = _walk(points, end_index, back, 1)
        if incoming is None or outgoing is None:
            break
        (_ax, _ay), (tax, tay) = incoming
        (_bx, _by), (tbx, tby) = outgoing
        center_a = (_ax + tay * radius, _ay - tax * radius)
        center_b = (_bx + tby * radius, _by - tbx * radius)
        err = math.hypot(center_a[0] - center_b[0], center_a[1] - center_b[1])
        if best is None or err < best[0]:
            best = (err, back, incoming, outgoing, center_a, center_b)
        if err < 0.02:
            break
        back += 0.25
    if best is None:
        return None
    err, back, incoming, outgoing, center_a, center_b = best
    # Refine both sides. The opening is symmetric on a U and is not
    # on a diagonal notch, so each side keeps its own setback.
    back_a = back
    back_b = back
    for _pass in range(2):
        step = 0.05 if _pass == 0 else 0.01
        for step_a in range(-8, 9):
            progress.check(outline=points)
            for step_b in range(-8, 9):
                trial_a = back_a + step_a * step
                trial_b = back_b + step_b * step
                if trial_a <= 0.05 or trial_b <= 0.05 or trial_a > limit or trial_b > limit:
                    continue
                trial_in = _walk(points, start_index, trial_a, -1)
                trial_out = _walk(points, end_index, trial_b, 1)
                if trial_in is None or trial_out is None:
                    continue
                (ax, ay), (tax, tay) = trial_in
                (bx, by), (tbx, tby) = trial_out
                trial_center_a = (ax + tay * radius, ay - tax * radius)
                trial_center_b = (bx + tby * radius, by - tbx * radius)
                trial_err = math.hypot(
                    trial_center_a[0] - trial_center_b[0],
                    trial_center_a[1] - trial_center_b[1],
                )
                if trial_err + 1e-9 < err:
                    err = trial_err
                    back_a = trial_a
                    back_b = trial_b
                    incoming = trial_in
                    outgoing = trial_out
                    center_a = trial_center_a
                    center_b = trial_center_b
    if err > 0.12:
        return None
    (ax, ay), _tangent_a = incoming
    (bx, by), _tangent_b = outgoing
    center = (
        0.5 * (center_a[0] + center_b[0]),
        0.5 * (center_a[1] + center_b[1]),
    )
    arc = _fillet_arc(center, (ax, ay), (bx, by))
    if arc is None or not _arc_stays_out(arc, dilated):
        return None
    at_start, at_end = _junction_angles(incoming, outgoing, arc)
    if at_start < 150.0 or at_end < 150.0:
        return None
    corner = (
        0.5 * (points[start_index][0] + points[end_index][0]),
        0.5 * (points[start_index][1] + points[end_index][1]),
    )
    return _fillet_record(start_index, back_a, chain_len + back_b, arc, corner)


def _span_inside(length, start, end):
    if start <= end:
        return start + 1e-7 < length < end - 1e-7
    return length > start + 1e-7 or length < end - 1e-7


def _apply_fillets(points, fillets):
    lengths, total = _cumulative(points)
    spans = []
    for fillet in fillets:
        pos = lengths[fillet['index']]
        start = (pos - fillet['back_a']) % total
        end = (pos + fillet['back_b']) % total
        spans.append((start, end, fillet))
    seam = None
    for length in lengths:
        if not any(_span_inside(length, start, end) for start, end, _fillet in spans):
            seam = length
            break
    if seam is None:
        return None

    def unwrap(length):
        return (length - seam) % total

    open_spans = []
    for start, end, fillet in spans:
        start_u = unwrap(start)
        end_u = unwrap(end)
        if start_u >= end_u:
            return None
        open_spans.append((start_u, end_u, fillet))

    def covered(length):
        for start, end, _fillet in open_spans:
            if start + 1e-7 < length < end - 1e-7:
                return True
        return False

    events = []
    for index, length in enumerate(lengths):
        position = unwrap(length)
        if covered(position):
            continue
        events.append((position, 1, points[index]))
    for start, _end, fillet in open_spans:
        events.append((start, 0, fillet))
    events.sort(key=lambda item: (item[0], item[1]))

    output = []
    attachments = []

    def push(point):
        if output and _near(output[-1], point, 1e-8):
            return len(output) - 1
        output.append((point[0], point[1]))
        return len(output) - 1

    for _pos, kind, payload in events:
        if kind == 1:
            push(payload)
            continue
        mid_at = None
        for point in payload['arc']:
            index = push(point)
            if mid_at is None and _near(point, payload['mid'], 1e-6):
                mid_at = index
        if mid_at is None:
            mid_at = push(payload['mid'])
        attachments.append((payload['corner'], mid_at))
    if len(output) >= 2 and _near(output[0], output[-1], 1e-8):
        output.pop()
        fixed = []
        for corner, index in attachments:
            if index >= len(output):
                index = 0
            fixed.append((corner, index))
        attachments = fixed
    if len(output) < 3:
        return None
    return output, attachments


def _edges_colinear(points, first, second):
    count = len(points)
    a0 = points[first]
    a1 = points[(first + 1) % count]
    b0 = points[second]
    b1 = points[(second + 1) % count]
    adx = a1[0] - a0[0]
    ady = a1[1] - a0[1]
    bdx = b1[0] - b0[0]
    bdy = b1[1] - b0[1]
    length_a = math.hypot(adx, ady)
    length_b = math.hypot(bdx, bdy)
    if length_a <= _TANGENT_EPS or length_b <= _TANGENT_EPS:
        return False
    ux = adx / length_a
    uy = ady / length_a
    if ux * bdx + uy * bdy < 0.999 * length_b:
        return False
    if abs(ux * (b0[1] - a0[1]) - uy * (b0[0] - a0[0])) > 1e-3:
        return False
    if abs(ux * (b1[1] - a0[1]) - uy * (b1[0] - a0[0])) > 1e-3:
        return False
    return True


def _short_dip(points, edge, chain):
    """The chain is a dent of arc chords under a straight offset."""
    count = len(points)
    start = points[edge]
    end = points[(edge + 1) % count]
    length = math.hypot(end[0] - start[0], end[1] - start[1])
    if length <= _TANGENT_EPS:
        return False
    ux = (end[0] - start[0]) / length
    uy = (end[1] - start[1]) / length
    dipped = False
    for index in chain[1:-1]:
        point = points[index]
        cross = ux * (point[1] - start[1]) - uy * (point[0] - start[0])
        if cross < -1e-3:
            return False
        # A crossing of close pieces sits just under the line.
        if cross > 1e-3:
            dipped = True
    for index in range(len(chain) - 1):
        a = points[chain[index]]
        b = points[chain[index + 1]]
        edge_length = math.hypot(b[0] - a[0], b[1] - a[1])
        if edge_length <= 0.75:
            continue
        if abs(ux * (a[1] - start[1]) - uy * (a[0] - start[0])) > 1e-3:
            return False
        if abs(ux * (b[1] - start[1]) - uy * (b[0] - start[0])) > 1e-3:
            return False
        if ux * (b[0] - a[0]) + uy * (b[1] - a[1]) < 0.999 * edge_length:
            return False
    return dipped


def _shortcut_is_outer(points, chain, edge):
    count = len(points)
    start = points[edge]
    end = points[(edge + 1) % count]
    length = math.hypot(end[0] - start[0], end[1] - start[1])
    if length <= _TANGENT_EPS:
        return False
    ux = (end[0] - start[0]) / length
    uy = (end[1] - start[1]) / length
    # Exterior is to the right of a counterclockwise edge.
    ox = uy
    oy = -ux
    a = points[chain[0]]
    b = points[chain[-1]]
    for t in (0.25, 0.5, 0.75):
        sample = (
            a[0] + (b[0] - a[0]) * t + ox * 0.01,
            a[1] + (b[1] - a[1]) * t + oy * 0.01,
        )
        if _point_inside_ring(sample, points):
            return False
    return True


def _straighten_colinear(points):
    """Keep a shared straight offset across the gaps between its pieces.

    A fillet at each crossing leaves a bump. The line already clears
    the subject where it stays outside the offset.
    """
    count = len(points)
    if count < 4:
        return points
    _lengths, total = _cumulative(points)
    sides = []
    for index in range(count):
        # A short top anchors the line the same way a long one does.
        if _straight_side(points, index):
            sides.append(index)
    gaps = []
    for pos, edge in enumerate(sides):
        progress.check(outline=points)
        end_vertex = (edge + 1) % count
        for later in sides[pos + 1:] + sides[:pos]:
            chain = _index_chain(count, end_vertex, later)
            span = 0.0
            for index in range(len(chain) - 1):
                a = points[chain[index]]
                b = points[chain[index + 1]]
                span += math.hypot(b[0] - a[0], b[1] - a[1])
            if span > total * 0.5:
                break
            if not _edges_colinear(points, edge, later):
                continue
            if not _short_dip(points, edge, chain):
                continue
            if not _shortcut_is_outer(points, chain, edge):
                continue
            gaps.append((chain[0], chain[-1]))
            break
    if not gaps:
        return points
    drop = [False] * count
    for start, end in gaps:
        cursor = (start + 1) % count
        guard = 0
        while cursor != end and guard < count:
            drop[cursor] = True
            cursor = (cursor + 1) % count
            guard += 1
    kept = [
        point for index, point in enumerate(points) if not drop[index]
    ]
    if len(kept) < 3:
        return points
    return kept


def _kept_outline(points, fallback):
    path = _closed_path(points)
    if path is None:
        return fallback
    return path


def _finish_outline(outer, distance, dilated, cap_mouth=True):
    """Round reflex corners outward to the surround distance.

    The arc stays outside the offset, including at a crossing dent.
    A connector through that dent would come closer than the distance.
    Colinear straight offsets are one line before that fillet. A mouth
    on one dilation is still one turn. A gap bridge is not a mouth.
    """
    # Looked up on the package each call. A test replaces it.
    from . import _straighten_colinear
    points = _straighten_colinear(_ring_points(outer))
    progress.check(outline=points or None)
    if len(points) < 4:
        return outer
    corners = [
        index for index in range(len(points))
        if _signed_turn(points, index) <= -_SHARP_TURN
    ]
    if not corners:
        return _kept_outline(points, outer)
    # Half the gap lets two fillets meet. The old 0.45 cap dropped a
    # corner whose setback fit in the space that was left.
    sharp_set = set(corners)
    fillets = []
    failed = []
    for index in corners:
        progress.check(outline=points)
        gap = _sharp_gap(points, index, sharp_set)
        max_back = min(0.5 * gap, 8.0 * distance)
        fillet = _fit_fillet(points, index, distance, max_back, dilated)
        if fillet is None:
            failed.append(index)
        else:
            fillets.append(fillet)
    consumed = set()
    if cap_mouth:
        for chain in _close_chains(points, failed, distance):
            progress.check(outline=points)
            bridge = _bridge_chain(points, chain, distance, dilated)
            if bridge is None:
                continue
            fillets.append(bridge)
            consumed.update(chain)
    for index in failed:
        if index in consumed:
            continue
        progress.check(outline=points)
        gap = _sharp_gap(points, index, sharp_set)
        max_back = min(0.5 * gap, 8.0 * distance)
        fillet = _fit_fillet_loose(points, index, distance, max_back, dilated)
        if fillet is not None:
            fillets.append(fillet)
    if not fillets:
        return _kept_outline(points, outer)
    applied = _apply_fillets(points, fillets)
    if applied is None:
        return _kept_outline(points, outer)
    outline, _attachments = applied
    path = _closed_path(outline)
    return outer if path is None else path
