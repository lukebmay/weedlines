# -*- coding: utf-8 -*-
"""Surrounds: one outer boundary around each subject cluster."""
from __future__ import division

import math

from .paths import split_painter_path
from .qt import QPainterPath, QPainterPathStroker, QPointF, QTransform, Qt

# Boolean ops and the stroker flatten curves. Scale, and a tight
# curve threshold, keep the inward error to rounding.
_CLIP_SCALE = 32.0
_CURVE_FLATNESS = 0.01
_CLOSED_TOL = 1e-4
_AREA_EPS = 1e-8
_TANGENT_EPS = 1e-12
# Duplicate hits of one crossing, not two corners of a merge.
_CROSS_CLUSTER = 0.02
_CROSS_SNAP = 0.15
_ARC_STEP = math.radians(4.0)
# A right turn steeper than this is a corner, not stroker noise.
_SHARP_TURN = 20.0
_FILLET_ERR = 0.05


def build_surrounds(subject, distance):
    """One outer surround for each cluster, as closed paths.

    ``subject`` is the subject region in document user units, holes
    included. ``distance`` is a length in those units and is never
    negative. Zero is that region's outer boundary. A positive
    distance expands it with a round join. A reflex corner is
    rounded to that distance. Two reflex corners too close for
    two setbacks become one turn of that radius. Where two
    surrounds cross, one connector joins the smoothed crossings.
    A loop that only follows a hole is not returned.
    """
    if not isinstance(subject, QPainterPath):
        raise TypeError(
            'subject must be a QPainterPath, got: {}'.format(
                type(subject).__name__))
    distance = float(distance)
    if distance < 0.0:
        raise ValueError(
            'surround distance must not be negative, got: {}'.format(distance))
    if subject.isEmpty():
        return []
    if distance == 0.0:
        return _outer_boundaries(subject)
    dilated = _dilate(subject, distance)
    outers = _outer_boundaries(dilated)
    pairs = _crossing_pairs(subject, distance)
    return [
        _finish_outline(outer, pairs, distance, dilated)
        for outer in outers
    ]


def _dilate(subject, distance):
    scale = _CLIP_SCALE
    scaled = QTransform().scale(scale, scale).map(subject)
    scaled.setFillRule(subject.fillRule())
    stroker = QPainterPathStroker()
    stroker.setWidth(2.0 * distance * scale)
    stroker.setJoinStyle(Qt.RoundJoin)
    stroker.setCapStyle(Qt.RoundCap)
    stroker.setCurveThreshold(_CURVE_FLATNESS)
    stroke = stroker.createStroke(scaled)
    expanded = scaled.united(stroke).simplified()
    expanded.setFillRule(Qt.OddEvenFill)
    return QTransform().scale(1.0 / scale, 1.0 / scale).map(expanded)


def _outer_boundaries(path):
    """Even-depth outlines. A hole in a curve is not one of them.

    A flattened chord sits inside its curve, so a hole vertex in that
    gap is outside the polygon and still inside the subject. Nest by
    a point the subpath contains. Only a larger outline counts.
    """
    loops, depths = _nested_loops(path)
    return [
        subpath
        for (subpath, _area, _point), depth in zip(loops, depths)
        if depth % 2 == 0
    ]


def _nested_loops(path):
    """Closed subpaths with area, an interior point, and nest depth."""
    loops = []
    for subpath in _closed_subpaths(path):
        area = abs(_signed_area(subpath))
        if area <= _AREA_EPS:
            continue
        point = _contained_point(subpath)
        if point is None:
            continue
        loops.append((subpath, area, point))

    depths = []
    for index, (_subpath, area, point) in enumerate(loops):
        depth = 0
        for other, (outline, other_area, _other_point) in enumerate(loops):
            if other == index or other_area <= area:
                continue
            if outline.contains(point):
                depth += 1
        depths.append(depth)
    return loops, depths


def _closed_subpaths(path):
    return [
        subpath for subpath in split_painter_path(path)
        if _is_closed(subpath)
    ]


def _is_closed(subpath):
    count = subpath.elementCount()
    if count < 4:
        return False
    first = subpath.elementAt(0)
    last = subpath.elementAt(count - 1)
    return (
        abs(first.x - last.x) <= _CLOSED_TOL
        and abs(first.y - last.y) <= _CLOSED_TOL
    )


def _segments(path):
    """Line, quad, and cubic segments as ``(kind, points)``."""
    move_to = QPainterPath.MoveToElement
    line_to = QPainterPath.LineToElement
    curve_to = QPainterPath.CurveToElement
    curve_data = QPainterPath.CurveToDataElement
    current = None
    index = 0
    count = path.elementCount()
    while index < count:
        element = path.elementAt(index)
        if element.type == move_to:
            current = (element.x, element.y)
            index += 1
            continue
        if element.type == line_to:
            end = (element.x, element.y)
            if current is not None:
                yield ('line', (current, end))
            current = end
            index += 1
            continue
        if element.type != curve_to or current is None:
            index += 1
            continue
        if index + 1 >= count or path.elementAt(index + 1).type != curve_data:
            index += 1
            continue
        control = (element.x, element.y)
        follow = path.elementAt(index + 1)
        if index + 2 < count and path.elementAt(index + 2).type == curve_data:
            end_element = path.elementAt(index + 2)
            end = (end_element.x, end_element.y)
            yield ('cubic', (current, control, (follow.x, follow.y), end))
            current = end
            index += 3
            continue
        end = (follow.x, follow.y)
        yield ('quad', (current, control, end))
        current = end
        index += 2


def _signed_area(path):
    """Algebraic area from the path elements, not from chord vertices."""
    area = 0.0
    start = None
    current = None
    for kind, points in _segments(path):
        if start is None:
            start = points[0]
        current = points[-1]
        area += _segment_area(kind, points)
    if start is None or current is None:
        return 0.0
    if (
        abs(start[0] - current[0]) > _CLOSED_TOL
        or abs(start[1] - current[1]) > _CLOSED_TOL
    ):
        area += _segment_area('line', (current, start))
    return area


def _segment_area(kind, points):
    if kind == 'line':
        return _line_integral(points[0], points[1])
    if kind == 'quad':
        return _polynomial_integral(
            _quad_coeffs(points[0][0], points[1][0], points[2][0]),
            _quad_coeffs(points[0][1], points[1][1], points[2][1]),
        )
    return _polynomial_integral(
        _cubic_coeffs(
            points[0][0], points[1][0], points[2][0], points[3][0]),
        _cubic_coeffs(
            points[0][1], points[1][1], points[2][1], points[3][1]),
    )


def _line_integral(start, end):
    # ∫ x dy along the segment. Closed loops make this the signed area.
    return (start[0] + end[0]) * (end[1] - start[1]) * 0.5


def _quad_coeffs(p0, p1, p2):
    return (
        0.0,
        p0 - 2.0 * p1 + p2,
        2.0 * (p1 - p0),
        p0,
    )


def _cubic_coeffs(p0, p1, p2, p3):
    return (
        -p0 + 3.0 * p1 - 3.0 * p2 + p3,
        3.0 * (p0 - 2.0 * p1 + p2),
        3.0 * (p1 - p0),
        p0,
    )


def _polynomial_integral(x_coeff, y_coeff):
    """∫ x dy for x(t), y(t) on t in [0, 1]."""
    a, b, c, d = x_coeff
    cubic, quad, linear, _constant = y_coeff
    return (
        a * cubic / 2.0
        + (2.0 * a * quad + 3.0 * b * cubic) / 5.0
        + (
            a * linear / 4.0
            + b * quad / 2.0
            + 3.0 * c * cubic / 4.0
        )
        + (b * linear / 3.0 + 2.0 * c * quad / 3.0 + d * cubic)
        + (c * linear / 2.0 + d * quad)
        + d * linear
    )


def _contained_point(subpath):
    """A point ``subpath.contains`` accepts, off the chord vertices."""
    rect = subpath.boundingRect()
    span = max(rect.width(), rect.height(), 1e-6)
    scales = (
        1e-4, 1e-3, 0.01, 0.05,
        span * 1e-4, span * 1e-3, span * 0.01, span * 0.05,
    )
    for kind, points in _segments(subpath):
        sample = _edge_sample(kind, points)
        if sample is None:
            continue
        mx, my, tx, ty = sample
        length = math.hypot(tx, ty)
        if length <= _TANGENT_EPS:
            continue
        nx = -ty / length
        ny = tx / length
        for scale in scales:
            for sign in (1.0, -1.0):
                probe = QPointF(mx + sign * nx * scale, my + sign * ny * scale)
                if subpath.contains(probe):
                    return probe
    for row in range(1, 16):
        for column in range(1, 16):
            probe = QPointF(
                rect.left() + rect.width() * column / 16.0,
                rect.top() + rect.height() * row / 16.0,
            )
            if subpath.contains(probe):
                return probe
    center = rect.center()
    if subpath.contains(center):
        return center
    return None


def _edge_sample(kind, points):
    if kind == 'line':
        start, end = points
        return (
            0.5 * (start[0] + end[0]),
            0.5 * (start[1] + end[1]),
            end[0] - start[0],
            end[1] - start[1],
        )
    if kind == 'quad':
        p0, p1, p2 = points
        return (
            0.25 * p0[0] + 0.5 * p1[0] + 0.25 * p2[0],
            0.25 * p0[1] + 0.5 * p1[1] + 0.25 * p2[1],
            p2[0] - p0[0],
            p2[1] - p0[1],
        )
    p0, p1, p2, p3 = points
    return (
        0.125 * p0[0] + 0.375 * p1[0] + 0.375 * p2[0] + 0.125 * p3[0],
        0.125 * p0[1] + 0.375 * p1[1] + 0.375 * p2[1] + 0.125 * p3[1],
        (
            0.75 * (p1[0] - p0[0])
            + 1.5 * (p2[0] - p1[0])
            + 0.75 * (p3[0] - p2[0])
        ),
        (
            0.75 * (p1[1] - p0[1])
            + 1.5 * (p2[1] - p1[1])
            + 0.75 * (p3[1] - p2[1])
        ),
    )


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


def _boundary_segments(path):
    segments = []
    for subpath in _closed_subpaths(path):
        for kind, points in _segments(subpath):
            if kind == 'line':
                segments.append(points)
    return segments


def _boxes_miss(first, second):
    a, b = first
    c, d = second
    return (
        max(a[0], b[0]) < min(c[0], d[0]) - 1e-9
        or max(c[0], d[0]) < min(a[0], b[0]) - 1e-9
        or max(a[1], b[1]) < min(c[1], d[1]) - 1e-9
        or max(c[1], d[1]) < min(a[1], b[1]) - 1e-9
    )


def _segment_intersection(first, second):
    """A point where the segments cross, including a shared endpoint."""
    if _boxes_miss(first, second):
        return None
    ax, ay = first[0]
    bx, by = first[1]
    cx, cy = second[0]
    dx, dy = second[1]
    rx = bx - ax
    ry = by - ay
    sx = dx - cx
    sy = dy - cy
    den = rx * sy - ry * sx
    if abs(den) <= 1e-12:
        return None
    qpx = cx - ax
    qpy = cy - ay
    t = (qpx * sy - qpy * sx) / den
    u = (qpx * ry - qpy * rx) / den
    if t < -1e-8 or t > 1.0 + 1e-8 or u < -1e-8 or u > 1.0 + 1e-8:
        return None
    return (ax + t * rx, ay + t * ry)


def _cluster_points(points, tol):
    groups = []
    for point in points:
        for group in groups:
            if math.hypot(point[0] - group[0], point[1] - group[1]) <= tol:
                break
        else:
            groups.append(point)
    return groups


def _crossing_pairs(subject, distance):
    """Crossing pairs of dilated components.

    Two points are one pair. Parallel contact, including a gap of
    exactly twice the distance, is not a crossing.
    """
    components = _components(subject)
    if len(components) < 2:
        return []
    boundaries = [
        _boundary_segments(_dilate(component, distance))
        for component in components
    ]
    pairs = []
    for left in range(len(boundaries)):
        for right in range(left + 1, len(boundaries)):
            found = []
            for first in boundaries[left]:
                for second in boundaries[right]:
                    point = _segment_intersection(first, second)
                    if point is not None:
                        found.append(point)
            found = _cluster_points(found, _CROSS_CLUSTER)
            pairs.extend(_match_crossings(found))
    return pairs


def _match_crossings(points):
    if len(points) < 2:
        return []
    if len(points) == 2:
        return [(points[0], points[1])]
    remaining = list(points)
    pairs = []
    while len(remaining) >= 2:
        best = None
        for left in range(len(remaining)):
            for right in range(left + 1, len(remaining)):
                dist = math.hypot(
                    remaining[left][0] - remaining[right][0],
                    remaining[left][1] - remaining[right][1],
                )
                if best is None or dist < best[0]:
                    best = (dist, left, right)
        _dist, left, right = best
        pairs.append((remaining[left], remaining[right]))
        for index in sorted((left, right), reverse=True):
            remaining.pop(index)
    return pairs


def _ring_area(points):
    area = 0.0
    previous = points[-1]
    for point in points:
        area += previous[0] * point[1] - point[0] * previous[1]
        previous = point
    return area * 0.5


def _ring_points(path):
    """Vertices of a flattened loop, counterclockwise, without the repeat."""
    points = []
    for _kind, segment in _segments(path):
        if not points:
            points.append(segment[0])
        end = segment[-1]
        if math.hypot(end[0] - points[-1][0], end[1] - points[-1][1]) > 1e-9:
            points.append(end)
    if (
        len(points) >= 2
        and math.hypot(points[0][0] - points[-1][0], points[0][1] - points[-1][1])
        <= _CLOSED_TOL
    ):
        points.pop()
    if len(points) < 3:
        return []
    if _ring_area(points) < 0.0:
        points.reverse()
    return points


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


def _distance_to_segments(point, segments):
    px, py = point
    best = None
    for start, end in segments:
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length_sq = dx * dx + dy * dy
        if length_sq <= 1e-18:
            dist = math.hypot(px - start[0], py - start[1])
        else:
            scale = ((px - start[0]) * dx + (py - start[1]) * dy) / length_sq
            if scale < 0.0:
                scale = 0.0
            elif scale > 1.0:
                scale = 1.0
            dist = math.hypot(px - (start[0] + scale * dx), py - (start[1] + scale * dy))
        if best is None or dist < best:
            best = dist
    if best is None:
        return 0.0
    return best


def _near(first, second, tol):
    return math.hypot(first[0] - second[0], first[1] - second[1]) <= tol


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


def _crossing_corner_indices(points, pairs):
    """Outline vertices where two surrounds actually cross.

    A shallow kink is still a crossing. Stroker noise is a degree
    or two and does not sit on the crossing point.
    """
    chosen = []
    for pair in pairs:
        for crossing in pair:
            best = None
            for index, point in enumerate(points):
                dist = math.hypot(point[0] - crossing[0], point[1] - crossing[1])
                if dist > _CROSS_SNAP:
                    continue
                turn = _signed_turn(points, index)
                if best is None or turn < best[0] - 1e-6 or (
                    abs(turn - best[0]) <= 1e-6 and dist < best[1]
                ):
                    best = (turn, dist, index)
            if best is None:
                continue
            turn, dist, index = best
            if turn >= -0.5:
                continue
            if dist > 0.02 and turn > -4.0:
                continue
            chosen.append(index)
    return chosen


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


def _snap_chords(pairs, attachments):
    chords = []
    for pair in pairs:
        ends = []
        used = set()
        missed = False
        for crossing in pair:
            best = None
            for slot, (corner, index) in enumerate(attachments):
                if slot in used:
                    continue
                dist = math.hypot(
                    corner[0] - crossing[0], corner[1] - crossing[1])
                if best is None or dist < best[0]:
                    best = (dist, slot, index)
            if best is None or best[0] > _CROSS_SNAP:
                missed = True
                break
            used.add(best[1])
            ends.append(best[2])
        if missed or len(ends) != 2 or ends[0] == ends[1]:
            continue
        chords.append((ends[0], ends[1]))
    return chords


def _connector_tour(count, chords):
    """Ring once, each connector twice, ring and connector alternating.

    Doubling the connector makes the outline one closed stroke. Each
    end meets the connector from the surround, not from a reversal.
    """
    adj = [[] for _index in range(count)]

    def add(start, end, kind):
        forward = [end, kind, False]
        back = [start, kind, False]
        forward.append(back)
        back.append(forward)
        adj[start].append(forward)
        adj[end].append(back)

    for index in range(count):
        add(index, (index + 1) % count, 'r')
    for start, end in chords:
        add(start, end, 'c')
        add(start, end, 'c')

    def pick(vertex, arrived):
        options = [edge for edge in adj[vertex] if not edge[2]]
        if not options:
            return None
        if arrived is None:
            for edge in options:
                if edge[1] == 'r':
                    return edge
            return options[0]
        want = 'c' if arrived == 'r' else 'r'
        for edge in options:
            if edge[1] == want:
                return edge
        return options[0]

    start = chords[0][0]
    path = []
    trail = []
    arrived_stack = []
    vertex = start
    arrived = None
    guard = 0
    limit = (count + 2 * len(chords)) * 4 + 8
    while guard < limit:
        guard += 1
        edge = pick(vertex, arrived)
        if edge is not None:
            edge[2] = True
            edge[3][2] = True
            trail.append(vertex)
            arrived_stack.append(arrived)
            arrived = edge[1]
            vertex = edge[0]
            continue
        path.append(vertex)
        if not trail:
            break
        vertex = trail.pop()
        arrived = arrived_stack.pop()
    else:
        return None
    path.reverse()
    if len(path) >= 2 and path[0] == path[-1]:
        path.pop()
    if len(path) != count + 2 * len(chords):
        return None
    return path


def _closed_path(points):
    cleaned = [points[0]]
    for point in points[1:]:
        if not _near(cleaned[-1], point, 1e-8):
            cleaned.append(point)
    if len(cleaned) >= 2 and _near(cleaned[0], cleaned[-1], 1e-8):
        cleaned.pop()
    if len(cleaned) < 3:
        return None
    path = QPainterPath()
    path.moveTo(cleaned[0][0], cleaned[0][1])
    for point in cleaned[1:]:
        path.lineTo(point[0], point[1])
    path.closeSubpath()
    return path


def _finish_outline(outer, pairs, distance, dilated):
    """Round reflex corners, then one connector per crossing pair.

    The connector may come closer than the surround distance. That is
    the overlap exception. The rest of the outline may not.
    """
    points = _ring_points(outer)
    if len(points) < 4:
        return outer
    sharp = [
        index for index in range(len(points))
        if _signed_turn(points, index) <= -_SHARP_TURN
    ]
    crossing_corners = set(_crossing_corner_indices(points, pairs))
    corners = sorted(set(sharp) | crossing_corners)
    if not corners:
        return outer
    # Half the gap lets two fillets meet. The old 0.45 cap dropped a
    # corner whose setback fit in the space that was left.
    sharp_set = set(corners)
    fillets = []
    failed = []
    for index in corners:
        gap = _sharp_gap(points, index, sharp_set)
        max_back = min(0.5 * gap, 8.0 * distance)
        fillet = _fit_fillet(points, index, distance, max_back, dilated)
        if fillet is None and index in crossing_corners:
            fillet = _fit_fillet_loose(points, index, distance, max_back, dilated)
        if fillet is None:
            failed.append(index)
        else:
            fillets.append(fillet)
    for chain in _close_chains(points, failed, distance):
        bridge = _bridge_chain(points, chain, distance, dilated)
        if bridge is not None:
            fillets.append(bridge)
    if not fillets:
        return outer
    applied = _apply_fillets(points, fillets)
    if applied is None:
        return outer
    outline, attachments = applied
    chords = _snap_chords(pairs, attachments)
    if not chords:
        path = _closed_path(outline)
        return outer if path is None else path
    indices = _connector_tour(len(outline), chords)
    if indices is None:
        path = _closed_path(outline)
        return outer if path is None else path
    path = _closed_path([outline[index] for index in indices])
    return outer if path is None else path
