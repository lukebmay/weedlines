# -*- coding: utf-8 -*-
"""Classify path records into figures and figure-check defects."""
from __future__ import division

import math
from dataclasses import dataclass

from .paths import join_painter_paths, split_painter_path
from .qt import QPainterPath, QPointF, QRectF, QTransform, Qt
from .solvers import _dedupe_closed_subpaths, _subpath_is_closed
from .svg_paths import svg_d_to_qpainterpath

# Same start/end coincidence _subpath_is_closed uses.
_SAME_POINT_TOL = 1e-4
# Below this, a boolean sliver is a touch or a shared edge, not area.
_AREA_EPS = 1e-6
# A chord this close to its curve can stand in for that curve.
_CURVE_FLAT = 1e-6
# Controls this close to the segment between the ends lie on it.
_STRAIGHT_CUBIC = 1e-9
_CORRECTION_PREFIX = "weedlines-correction"


@dataclass
class Figure:
    """One path element after twin outlines are collapsed."""

    id: str
    path: QPainterPath
    fill: object


@dataclass
class Defect:
    """One figure-check defect. ``target`` is the arrow point."""

    kind: str
    target: QPointF


@dataclass
class FigureCheck:
    """Figures from the records, and the defects on those figures."""

    figures: list
    defects: list


@dataclass
class SubjectWeed:
    """Subject path, weed-area path, and the design bounds around both."""

    subject: QPainterPath
    weed_area: QPainterPath
    bounds: QRectF


def classify_figures(records):
    """One figure per path record, and every figure-check defect.

    ``d`` is parsed by the SVG path helper. A closed flag does not add a
    closepath. Twins use the keep-fill near-duplicate collapse. An id
    starting with ``weedlines-correction`` is not a figure.

    Dangling ends, separate-figure overlaps, and self-overlaps are all
    reported. Overlap uses the painted interior. A self-overlap uses the
    real border, not the segment an open subpath is painted as if closed by.
    """
    figures = []
    defects = []
    kept_closed = []
    kept_parts = []
    for record in records or []:
        element_id = _element_id(record)
        if element_id.startswith(_CORRECTION_PREFIX):
            continue
        # Path data decides. Do not closeSubpath from the record's closed flags.
        path = _path_from_record(record)
        subpaths = split_painter_path(path)
        kept = _without_twins(subpaths, kept_closed)
        if not kept:
            continue
        figures.append(Figure(
            id=element_id,
            path=_figure_path(path, subpaths, kept),
            fill=_lookup(record, "fill"),
        ))
        defects.extend(_dangling_defects(kept))
        kept_parts.append(kept)
    for subpaths in kept_parts:
        defects.extend(_self_overlap_defects(subpaths))
    painted = [_painted_parts(subpaths) for subpaths in kept_parts]
    for index, left in enumerate(painted):
        for right in painted[index + 1:]:
            defects.extend(_overlap_defects(left, right))
    return FigureCheck(figures=figures, defects=defects)


def subject_weed_regions(figures, swap):
    """Subject, weed area, and design bounds for classified figures.

    ``figures`` is the list from ``classify_figures``. A fill is paint
    when it is a color or ``other``; ``none`` is not. Painted interiors
    start as subject. When no figure has paint, every interior does.
    Weed area is the design bounds minus that subject. ``swap``
    exchanges the two inside those bounds and does not move the bounds.
    """
    figures = list(figures or [])
    any_paint = any(_is_paint(figure.fill) for figure in figures)
    subject = _union_interiors(figures, any_paint)
    bounds = _design_bounds(figures)
    weed_area = _bounds_minus(bounds, subject)
    if swap:
        subject, weed_area = weed_area, subject
    return SubjectWeed(subject=subject, weed_area=weed_area, bounds=bounds)


def _is_paint(fill):
    # Job fill is none, a #rrggbb color, or other (a gradient).
    if not isinstance(fill, str):
        return False
    token = " ".join(fill.split()).lower()
    return token not in ("", "none", "transparent")


def _union_interiors(figures, require_paint):
    acc = QPainterPath()
    for figure in figures:
        if require_paint and not _is_paint(figure.fill):
            continue
        # Painted interior, including an open subpath. Not solver keep.
        interior = _painted_parts(split_painter_path(figure.path))
        if not _has_area(interior):
            continue
        acc = interior if acc.isEmpty() else acc.united(interior)
    acc.setFillRule(Qt.OddEvenFill)
    return acc


def _design_bounds(figures):
    box = QRectF()
    for figure in figures:
        rect = figure.path.boundingRect()
        # A null seed is the origin, not a figure. Do not union with it.
        box = rect if box.isNull() else box.united(rect)
    return box.normalized()


def _bounds_minus(bounds, subject):
    if not bounds.isValid():
        return QPainterPath()
    rect = QPainterPath()
    rect.addRect(bounds)
    rect.setFillRule(Qt.OddEvenFill)
    if not _has_area(subject):
        return rect
    weed_area = rect.subtracted(subject)
    weed_area.setFillRule(Qt.OddEvenFill)
    return weed_area


def _element_id(record):
    value = _lookup(record, "id", "")
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _path_from_record(record):
    path = _lookup(record, "path")
    if isinstance(path, QPainterPath):
        return QPainterPath(path)
    d = _lookup(record, "d")
    if isinstance(d, str):
        return svg_d_to_qpainterpath(d)
    raise ValueError("figure record has no path data")


def _lookup(record, name, default=None):
    if isinstance(record, dict):
        return record.get(name, default)
    return getattr(record, name, default)


def _without_twins(subpaths, kept_closed):
    kept = []
    for subpath in subpaths:
        if _subpath_is_closed(subpath):
            if not _is_new_outline(subpath, kept_closed):
                continue
            kept_closed.append(subpath)
        kept.append(subpath)
    return kept


def _is_new_outline(subpath, kept_closed):
    """False when the keep-fill twin collapse drops *subpath*."""
    unique = _dedupe_closed_subpaths(kept_closed + [subpath])
    return any(item is subpath for item in unique)


def _figure_path(path, subpaths, kept):
    if len(kept) == len(subpaths):
        return QPainterPath(path)
    return join_painter_paths(kept)


def _dangling_defects(subpaths):
    endpoints = []
    for subpath in subpaths:
        if _subpath_is_closed(subpath):
            continue
        endpoints.extend(_endpoints(subpath))
    defects = []
    for index, point in enumerate(endpoints):
        if _meets_other(point, endpoints, index):
            continue
        defects.append(Defect(kind="dangling", target=point))
    return defects


def _endpoints(subpath):
    count = subpath.elementCount()
    if count <= 0:
        return []
    start = _point_at(subpath, 0)
    if count == 1:
        return [start]
    return [start, _point_at(subpath, count - 1)]


def _point_at(subpath, index):
    element = subpath.elementAt(index)
    return QPointF(element.x, element.y)


def _meets_other(point, endpoints, index):
    for other_index, other in enumerate(endpoints):
        if other_index == index:
            continue
        if _same_point(point, other):
            return True
    return False


def _same_point(a, b):
    return (
        abs(a.x() - b.x()) <= _SAME_POINT_TOL
        and abs(a.y() - b.y()) <= _SAME_POINT_TOL
    )


def _painted_parts(subpaths):
    """Union of painted subpaths, minus a counter that does not cross.

    Global odd-even would drop the lens where two subpaths cross. That lens
    is not a counter. A counter is contained, and its real border does not
    cross the border around it.
    """
    fills = [_fill_subpath(subpath) for subpath in subpaths]
    count = len(fills)
    if count == 0:
        return QPainterPath()
    if count == 1:
        return fills[0]
    areas = [_area_of(fill) for fill in fills]
    parent = [None] * count
    for index in range(count):
        best = None
        best_area = None
        for other in range(count):
            if index == other or areas[other] <= areas[index]:
                continue
            if _has_area(fills[index].subtracted(fills[other]).simplified()):
                continue
            if _borders_cross(subpaths[index], subpaths[other]):
                continue
            if best is None or areas[other] < best_area:
                best = other
                best_area = areas[other]
        parent[index] = best
    acc = QPainterPath()
    for index, fill in enumerate(fills):
        if _nest_depth(parent, index) % 2 != 0:
            continue
        solid = QPainterPath(fill)
        for child, owner in enumerate(parent):
            if owner == index:
                solid = solid.subtracted(fills[child])
        if not _has_area(solid):
            continue
        acc = solid if acc.isEmpty() else acc.united(solid)
    return acc


def _fill_subpath(subpath):
    """Painted interior of one subpath. The close is fill-only."""
    filled = QPainterPath(subpath)
    if not _subpath_is_closed(subpath):
        filled.closeSubpath()
    filled.setFillRule(Qt.OddEvenFill)
    return filled


def _borders_cross(left, right):
    left_pieces = _border_pieces(left)
    right_pieces = _border_pieces(right)
    for piece in left_pieces:
        for other in right_pieces:
            if _piece_hits(piece, other):
                return True
    return False


def _nest_depth(parent, index):
    seen = 0
    node = parent[index]
    while node is not None and seen <= len(parent):
        seen += 1
        node = parent[node]
    return seen


def _overlap_defects(left, right):
    shared = left.intersected(right).simplified()
    if not _has_area(shared):
        return []
    # Each interior must keep a point the other does not. That excludes
    # nesting, where one painted interior lies inside the other.
    if not _has_area(left.subtracted(right).simplified()):
        return []
    if not _has_area(right.subtracted(left).simplified()):
        return []
    points = _unique_points(_component_points(shared))
    points.sort(key=lambda point: (point.x(), point.y()))
    return [Defect(kind="overlap", target=point) for point in points]


def _has_area(path):
    return (
        path is not None
        and not path.isEmpty()
        and _area_of(path) > _AREA_EPS
    )


def _area_of(path):
    if path is None or path.isEmpty():
        return 0.0
    area = 0.0
    for polygon in _polygons(path):
        area += _abs_area(_clean_ring(polygon))
    return area


def _component_points(path):
    points = []
    for polygon in _polygons(path):
        ring = _clean_ring(polygon)
        if len(ring) < 3 or _abs_area(ring) <= _AREA_EPS:
            continue
        point = _filled_point(ring, path)
        if point is not None:
            points.append(point)
    return points


def _filled_point(ring, path):
    """A point of this ring that the fill actually contains.

    The centroid of an outer ring can sit in a hole. A hole ring's own
    interior is not filled, so it yields no point.
    """
    centroid = _centroid(ring)
    if _in_fill(centroid, ring, path):
        return centroid
    count = len(ring)
    for index in range(count):
        start = ring[index]
        end = ring[(index + 1) % count]
        ex = end.x() - start.x()
        ey = end.y() - start.y()
        length = math.hypot(ex, ey)
        if length <= _SAME_POINT_TOL:
            continue
        nx = -ey / length
        ny = ex / length
        mx = 0.5 * (start.x() + end.x())
        my = 0.5 * (start.y() + end.y())
        for dist in (1e-3, 1e-2, 0.1, 0.5):
            for sign in (1.0, -1.0):
                point = QPointF(mx + sign * nx * dist, my + sign * ny * dist)
                if _in_fill(point, ring, path):
                    return point
    min_x = min(point.x() for point in ring)
    min_y = min(point.y() for point in ring)
    max_x = max(point.x() for point in ring)
    max_y = max(point.y() for point in ring)
    for row in range(1, 8):
        for col in range(1, 8):
            point = QPointF(
                min_x + (max_x - min_x) * col / 8.0,
                min_y + (max_y - min_y) * row / 8.0,
            )
            if _in_fill(point, ring, path):
                return point
    return None


def _in_fill(point, ring, path):
    return path.contains(point) and _point_in_ring(point, ring)


def _self_overlap_defects(subpaths):
    # Neighbors are compared. A shared endpoint is not a crossing; the
    # hit tests drop it.
    pieces = []
    for subpath in subpaths:
        pieces.extend(_border_pieces(subpath))
    points = []
    for left, piece in enumerate(pieces):
        points.extend(_self_piece_hits(piece))
        for other in pieces[left + 1:]:
            points.extend(_piece_hits(piece, other))
    points = _unique_points(points)
    points.sort(key=lambda point: (point.x(), point.y()))
    return [Defect(kind="self-overlap", target=point) for point in points]


def _border_pieces(subpath):
    """Line and curve pieces of the real border.

    An open subpath's painted close is not a piece. A curve is not the
    chords ``toSubpathPolygons`` puts inside it.
    """
    move_to = QPainterPath.MoveToElement
    line_to = QPainterPath.LineToElement
    curve_to = QPainterPath.CurveToElement
    curve_data = QPainterPath.CurveToDataElement
    pieces = []
    start = None
    current = None
    index = 0
    count = subpath.elementCount()
    while index < count:
        element = subpath.elementAt(index)
        if element.type == move_to:
            if start is not None:
                break
            current = (element.x, element.y)
            start = current
            index += 1
            continue
        if element.type == line_to:
            end = (element.x, element.y)
            if current is not None and not _same_tuple(current, end):
                pieces.append(("line", current, end))
            current = end
            index += 1
            continue
        if element.type != curve_to or current is None:
            index += 1
            continue
        if index + 1 >= count or subpath.elementAt(index + 1).type != curve_data:
            index += 1
            continue
        control = (element.x, element.y)
        follow = subpath.elementAt(index + 1)
        if index + 2 < count and subpath.elementAt(index + 2).type == curve_data:
            end_element = subpath.elementAt(index + 2)
            end = (end_element.x, end_element.y)
            piece = ("cubic", current, control, (follow.x, follow.y), end)
            if not _degenerate_cubic(piece):
                pieces.append(piece)
            current = end
            index += 3
            continue
        cubic = _quad_to_cubic(current, control, (follow.x, follow.y))
        if not _degenerate_cubic(cubic):
            pieces.append(cubic)
        current = cubic[4]
        index += 2
    if (
        _subpath_is_closed(subpath)
        and start is not None
        and current is not None
        and not _same_tuple(current, start)
    ):
        pieces.append(("line", current, start))
    return pieces


def _same_tuple(a, b):
    return (
        abs(a[0] - b[0]) <= _SAME_POINT_TOL
        and abs(a[1] - b[1]) <= _SAME_POINT_TOL
    )


def _degenerate_cubic(piece):
    origin = piece[1]
    return all(_same_tuple(origin, point) for point in piece[2:])


def _quad_to_cubic(p0, p1, p2):
    def weight(start, control):
        return (
            start[0] + (2.0 / 3.0) * (control[0] - start[0]),
            start[1] + (2.0 / 3.0) * (control[1] - start[1]),
        )

    return ("cubic", p0, weight(p0, p1), weight(p2, p1), p2)


def _self_piece_hits(piece):
    if piece[0] != "cubic":
        return []
    point = _cubic_loop_point(piece)
    if point is None:
        return []
    return [point]


def _piece_hits(left, right):
    if left[0] == "line" and right[0] == "line":
        point = _proper_cross(
            QPointF(*left[1]), QPointF(*left[2]),
            QPointF(*right[1]), QPointF(*right[2]),
        )
        if point is None:
            return []
        return [point]
    if left[0] == "line" and right[0] == "cubic":
        return _line_cubic_hits(left, right)
    if left[0] == "cubic" and right[0] == "line":
        return _line_cubic_hits(right, left)
    if left[0] == "cubic" and right[0] == "cubic":
        return _cubic_pair_hits(left, right)
    return []


def _line_cubic_hits(line, cubic):
    """Proper crossings of one line piece and one cubic piece.

    A root counts only when the cubic changes sides of the line. A touch
    stays on one side. A flat inflection changes sides and counts once.
    """
    x0, y0 = line[1]
    x1, y1 = line[2]
    dx = x1 - x0
    dy = y1 - y0
    length2 = dx * dx + dy * dy
    if length2 <= 1e-24:
        return []
    xs = _cubic_power(*[point[0] for point in cubic[1:]])
    ys = _cubic_power(*[point[1] for point in cubic[1:]])
    poly = (
        xs[0] * dy - ys[0] * dx,
        xs[1] * dy - ys[1] * dx,
        xs[2] * dy - ys[2] * dx,
        (xs[3] - x0) * dy - (ys[3] - y0) * dx,
    )
    scale = max(math.sqrt(length2), 1.0)
    if max(abs(coeff) for coeff in poly) <= 1e-9 * scale:
        return []
    ends = (line[1], line[2], cubic[1], cubic[4])
    roots = []
    for param in _cubic_roots(*poly):
        if math.isfinite(param) and 0.0 < param < 1.0:
            roots.append(param)
    hits = []
    for param in _sign_change_params(poly, roots):
        px = _horner(xs, param)
        py = _horner(ys, param)
        if not math.isfinite(px) or not math.isfinite(py):
            continue
        along = ((px - x0) * dx + (py - y0) * dy) / length2
        if along <= 0.0 or along >= 1.0:
            continue
        point = QPointF(px, py)
        if any(_same_point(point, QPointF(*end)) for end in ends):
            continue
        hits.append(point)
    return hits


def _sign_change_params(poly, roots):
    """One parameter per sign change. A same-side cluster is a touch.

    A triple root splits into two close parameters. They are one odd
    contact, so the samples sit outside the whole cluster.
    """
    if not roots:
        return []
    ordered = sorted(roots)
    clusters = []
    for param in ordered:
        if clusters and param - clusters[-1][-1] <= 5e-5:
            clusters[-1].append(param)
        else:
            clusters.append([param])
    kept = []
    step = 1e-4
    for cluster in clusters:
        start = cluster[0]
        end = cluster[-1]
        left = _horner(poly, start - step)
        right = _horner(poly, end + step)
        if left * right < 0.0:
            kept.append(0.5 * (start + end))
    return kept


def _cubic_power(p0, p1, p2, p3):
    # Power basis of (1-t)^3 P0 + 3(1-t)^2 t P1 + 3(1-t) t^2 P2 + t^3 P3.
    return (
        p3 - 3.0 * p2 + 3.0 * p1 - p0,
        3.0 * p0 - 6.0 * p1 + 3.0 * p2,
        3.0 * (p1 - p0),
        p0,
    )


def _horner(coeffs, param):
    acc = coeffs[0]
    for coeff in coeffs[1:]:
        acc = acc * param + coeff
    return acc


def _cubic_roots(a, b, c, d):
    """Real roots of a t^3 + b t^2 + c t + d."""
    if abs(a) <= 1e-14:
        return _quadratic_roots(b, c, d)
    b /= a
    c /= a
    d /= a
    shift = -b / 3.0
    p = c - b * b / 3.0
    q = d + (2.0 * b * b * b - 9.0 * b * c) / 27.0
    disc = q * q / 4.0 + p * p * p / 27.0
    if disc > 1e-12:
        root = math.sqrt(disc)
        return [_cbrt(-q / 2.0 + root) + _cbrt(-q / 2.0 - root) + shift]
    if disc < -1e-12:
        if p >= 0.0:
            return []
        radius = math.sqrt(-p / 3.0)
        arg = (-q / 2.0) / (radius * radius * radius)
        arg = max(-1.0, min(1.0, arg))
        angle = math.acos(arg)
        scale = 2.0 * radius
        return [
            scale * math.cos((angle + offset) / 3.0) + shift
            for offset in (0.0, 2.0 * math.pi, 4.0 * math.pi)
        ]
    turn = _cbrt(-q / 2.0)
    return [2.0 * turn + shift, -turn + shift]


def _quadratic_roots(a, b, c):
    if abs(a) <= 1e-14:
        if abs(b) <= 1e-14:
            return []
        return [-c / b]
    disc = b * b - 4.0 * a * c
    if disc < 0.0:
        return []
    root = math.sqrt(disc)
    if b >= 0.0:
        span = -0.5 * (b + root)
    else:
        span = -0.5 * (b - root)
    if abs(span) <= 1e-18:
        return [-b / (2.0 * a)]
    return [span / a, c / span]


def _cbrt(value):
    return math.copysign(abs(value) ** (1.0 / 3.0), value)


def _cubic_loop_point(piece):
    """Point where one cubic crosses itself, or None."""
    p0, p1, p2, p3 = piece[1:]
    ax, bx, cx, _dx = _cubic_power(p0[0], p1[0], p2[0], p3[0])
    ay, by, cy, _dy = _cubic_power(p0[1], p1[1], p2[1], p3[1])
    cross_ab = ax * by - ay * bx
    cross_ac = ax * cy - ay * cx
    scale = math.hypot(ax, ay) * math.hypot(bx, by) + 1.0
    if abs(cross_ab) <= 1e-12 * scale:
        return None
    sigma = -cross_ac / cross_ab
    adot = ax * ax + ay * ay
    if adot <= 1e-18:
        return None
    product = sigma * sigma + (
        sigma * (bx * ax + by * ay) + (cx * ax + cy * ay)
    ) / adot
    disc = sigma * sigma - 4.0 * product
    if disc <= 1e-14:
        return None
    root = math.sqrt(disc)
    left = 0.5 * (sigma - root)
    right = 0.5 * (sigma + root)
    if not (0.0 < left < 1.0 and 0.0 < right < 1.0):
        return None
    if abs(left - right) <= 1e-8:
        return None
    first = _bezier_at(piece, left)
    second = _bezier_at(piece, right)
    if math.hypot(first[0] - second[0], first[1] - second[1]) > _SAME_POINT_TOL:
        return None
    return QPointF(0.5 * (first[0] + second[0]), 0.5 * (first[1] + second[1]))


def _bezier_at(piece, param):
    p0, p1, p2, p3 = piece[1:]
    rest = 1.0 - param
    rest2 = rest * rest
    param2 = param * param
    return (
        rest2 * rest * p0[0]
        + 3.0 * rest2 * param * p1[0]
        + 3.0 * rest * param2 * p2[0]
        + param2 * param * p3[0],
        rest2 * rest * p0[1]
        + 3.0 * rest2 * param * p1[1]
        + 3.0 * rest * param2 * p2[1]
        + param2 * param * p3[1],
    )


def _bezier_deriv(piece, param):
    p0, p1, p2, p3 = piece[1:]
    rest = 1.0 - param

    def axis(index):
        return 3.0 * (
            rest * rest * (p1[index] - p0[index])
            + 2.0 * rest * param * (p2[index] - p1[index])
            + param * param * (p3[index] - p2[index])
        )

    return (axis(0), axis(1))


def _bezier_second(piece, param):
    p0, p1, p2, p3 = piece[1:]
    rest = 1.0 - param

    def axis(index):
        return 6.0 * (
            rest * (p2[index] - 2.0 * p1[index] + p0[index])
            + param * (p3[index] - 2.0 * p2[index] + p1[index])
        )

    return (axis(0), axis(1))


def _straight_cubic_line(piece):
    """Endpoint segment when both controls lie on it, else None.

    The crossing is the line through those ends. A chord sample is
    the wrong place on an uneven cubic, and it drops a flat inflection.
    """
    start, control, follow, end = piece[1:]
    for point in (control, follow):
        if _line_distance(point, start, end) > _STRAIGHT_CUBIC:
            return None
        if not _projects_onto_segment(point, start, end):
            return None
    return ("line", start, end)


def _collinear_extent_hits(left, right):
    """Crossings of a collinear cubic that runs past its ends, or None.

    None lets the chord walk run. The segment between the extreme points
    is the curve, and ``_line_cubic_hits`` counts where the other crosses.
    """
    left_line = _collinear_extent(left)
    right_line = _collinear_extent(right)
    if left_line is None and right_line is None:
        return None
    if left_line is not None and right_line is not None:
        point = _proper_cross(
            QPointF(*left_line[1]), QPointF(*left_line[2]),
            QPointF(*right_line[1]), QPointF(*right_line[2]),
        )
        if point is None:
            return []
        return [(point.x(), point.y())]
    line = left_line if left_line is not None else right_line
    cubic = right if left_line is not None else left
    return [(point.x(), point.y()) for point in _line_cubic_hits(line, cubic)]


def _collinear_extent(piece):
    """Extreme-point segment of a collinear cubic, or None.

    Controls on the endpoint line but past those ends still pull the
    curve past them. Controls off the line are not this segment. A cubic
    whose controls already lie on the endpoint segment is not one either.
    """
    start, control, follow, end = piece[1:]
    if (end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2 <= 1e-24:
        return None
    if _line_distance(control, start, end) > _STRAIGHT_CUBIC:
        return None
    if _line_distance(follow, start, end) > _STRAIGHT_CUBIC:
        return None
    if (
        _projects_onto_segment(control, start, end)
        and _projects_onto_segment(follow, start, end)
    ):
        return None
    return _extreme_segment(piece)


def _extreme_segment(piece):
    start = piece[1]
    end = piece[4]
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length2 = dx * dx + dy * dy

    def along(point):
        return (
            (point[0] - start[0]) * dx + (point[1] - start[1]) * dy
        ) / length2

    coeffs = _cubic_power(*(along(point) for point in piece[1:]))
    samples = [0.0, 1.0]
    for param in _quadratic_roots(3.0 * coeffs[0], 2.0 * coeffs[1], coeffs[2]):
        if math.isfinite(param) and 0.0 < param < 1.0:
            samples.append(param)
    places = [(param, _horner(coeffs, param)) for param in samples]
    low = min(places, key=lambda item: item[1])
    high = max(places, key=lambda item: item[1])
    if high[1] - low[1] <= 1e-12:
        return None
    return ("line", _bezier_at(piece, low[0]), _bezier_at(piece, high[0]))


def _projects_onto_segment(point, start, end):
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length2 = dx * dx + dy * dy
    if length2 <= 1e-24:
        return (
            math.hypot(point[0] - start[0], point[1] - start[1])
            <= _STRAIGHT_CUBIC
        )
    along = (
        (point[0] - start[0]) * dx + (point[1] - start[1]) * dy
    ) / length2
    return -1e-9 <= along <= 1.0 + 1e-9


def _cubic_pair_hits(left, right):
    """Crossings of two cubics. A touch that stays on one side is not one."""
    left_line = _straight_cubic_line(left)
    right_line = _straight_cubic_line(right)
    if left_line is not None and right_line is not None:
        point = _proper_cross(
            QPointF(*left_line[1]), QPointF(*left_line[2]),
            QPointF(*right_line[1]), QPointF(*right_line[2]),
        )
        if point is None:
            return []
        return [point]
    if left_line is not None:
        return _line_cubic_hits(left_line, right)
    if right_line is not None:
        return _line_cubic_hits(right_line, left)
    ends = (left[1], left[4], right[1], right[4])
    found = []
    _cubic_pair_walk(
        left, right, left, right, (0.0, 1.0), (0.0, 1.0), ends, found, 0,
    )
    return [QPointF(x, y) for x, y in found]


def _controls_lie_on_segment(piece):
    """True when both controls project onto the segment between the ends."""
    start, control, follow, end = piece[1:]
    return (
        _projects_onto_segment(control, start, end)
        and _projects_onto_segment(follow, start, end)
    )


def _cubic_pair_walk(
    left, right, orig_left, orig_right, span_left, span_right, ends, found,
    depth,
):
    # The endpoint chord misses a collinear cubic that runs past its ends.
    if depth == 0:
        extra = _collinear_extent_hits(left, right)
        if extra is not None:
            found.extend(extra)
            return
    if not _boxes_meet(_piece_box(left), _piece_box(right)):
        return
    left_flat = _cubic_flatness(left)
    right_flat = _cubic_flatness(right)
    # Flatness alone hides curve past an end. That chord stops at the end.
    left_ready = left_flat <= _CURVE_FLAT and _controls_lie_on_segment(left)
    right_ready = right_flat <= _CURVE_FLAT and _controls_lie_on_segment(right)
    if depth >= 32 or (left_ready and right_ready):
        point = _proper_cross(
            QPointF(*left[1]), QPointF(*left[4]),
            QPointF(*right[1]), QPointF(*right[4]),
            include_ends=True,
        )
        if point is None:
            return
        if any(_same_point(point, QPointF(*end)) for end in ends):
            return
        if not _cubics_change_sides(
            orig_left, orig_right, left, right, span_left, span_right,
        ):
            return
        found.append((point.x(), point.y()))
        return
    if not left_ready and (right_ready or left_flat >= right_flat):
        first, second = _split_cubic(left)
        mid = 0.5 * (span_left[0] + span_left[1])
        _cubic_pair_walk(
            first, right, orig_left, orig_right,
            (span_left[0], mid), span_right, ends, found, depth + 1,
        )
        _cubic_pair_walk(
            second, right, orig_left, orig_right,
            (mid, span_left[1]), span_right, ends, found, depth + 1,
        )
    else:
        first, second = _split_cubic(right)
        mid = 0.5 * (span_right[0] + span_right[1])
        _cubic_pair_walk(
            left, first, orig_left, orig_right,
            span_left, (span_right[0], mid), ends, found, depth + 1,
        )
        _cubic_pair_walk(
            left, second, orig_left, orig_right,
            span_left, (mid, span_right[1]), ends, found, depth + 1,
        )


def _cubics_change_sides(
    orig_left, orig_right, left, right, span_left, span_right,
):
    """True when each curve changes sides at this chord crossing.

    The chord fraction is not the parameter of that point on the curve.
    """
    params = _chord_params(left, right)
    if params is None:
        return False
    local_t, local_u = params
    point = _chord_point(left, local_t)
    param_t = _span_param(span_left, _project_cubic(left, point, local_t))
    param_u = _span_param(span_right, _project_cubic(right, point, local_u))
    return (
        _curve_changes_side(orig_left, param_t, orig_right, param_u)
        and _curve_changes_side(orig_right, param_u, orig_left, param_t)
    )


def _span_param(span, local):
    local = min(1.0, max(0.0, local))
    return span[0] + local * (span[1] - span[0])


def _chord_point(piece, local):
    start = piece[1]
    end = piece[4]
    return (
        start[0] + local * (end[0] - start[0]),
        start[1] + local * (end[1] - start[1]),
    )


def _chord_params(left, right):
    ax, ay = left[1]
    bx, by = left[4]
    cx, cy = right[1]
    dx, dy = right[4]
    rx = bx - ax
    ry = by - ay
    sx = dx - cx
    sy = dy - cy
    denom = rx * sy - ry * sx
    if abs(denom) <= 1e-12:
        return None
    qpx = cx - ax
    qpy = cy - ay
    return (
        (qpx * sy - qpy * sx) / denom,
        (qpx * ry - qpy * rx) / denom,
    )


def _curve_changes_side(curve, param, other, hint):
    """True when samples just off ``param`` lie on opposite sides of ``other``."""
    room = min(param, 1.0 - param)
    delta = min(1e-4, room * 0.5)
    if delta < 1e-8:
        return False
    before = _curve_side(_bezier_at(curve, param - delta), other, hint)
    after = _curve_side(_bezier_at(curve, param + delta), other, hint)
    # A real crossing can be shallower than 1e-9. The same sign is a touch.
    return before * after < 0.0


def _curve_side(point, curve, hint):
    param = _project_cubic(curve, point, hint)
    place = _bezier_at(curve, param)
    deriv = _bezier_deriv(curve, param)
    speed = math.hypot(deriv[0], deriv[1])
    if speed <= 1e-15:
        return 0.0
    return (
        deriv[0] * (point[1] - place[1])
        - deriv[1] * (point[0] - place[0])
    ) / speed


def _project_cubic(piece, point, hint):
    param = min(1.0, max(0.0, hint))
    for _ in range(12):
        place = _bezier_at(piece, param)
        deriv = _bezier_deriv(piece, param)
        second = _bezier_second(piece, param)
        vx = place[0] - point[0]
        vy = place[1] - point[1]
        slope = vx * deriv[0] + vy * deriv[1]
        curve = (
            deriv[0] * deriv[0] + deriv[1] * deriv[1]
            + vx * second[0] + vy * second[1]
        )
        if abs(curve) <= 1e-18:
            break
        step = slope / curve
        param = min(1.0, max(0.0, param - step))
        if abs(step) < 1e-14:
            break
    return param


def _split_cubic(piece):
    p0, p1, p2, p3 = piece[1:]

    def mid(start, end):
        return ((start[0] + end[0]) * 0.5, (start[1] + end[1]) * 0.5)

    a = mid(p0, p1)
    b = mid(p1, p2)
    c = mid(p2, p3)
    d = mid(a, b)
    e = mid(b, c)
    f = mid(d, e)
    return (("cubic", p0, a, d, f), ("cubic", f, e, c, p3))


def _cubic_flatness(piece):
    p0, p1, p2, p3 = piece[1:]
    return max(_line_distance(p1, p0, p3), _line_distance(p2, p0, p3))


def _line_distance(point, start, end):
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.hypot(dx, dy)
    if length <= 1e-12:
        return math.hypot(point[0] - start[0], point[1] - start[1])
    return abs(
        (point[0] - start[0]) * dy - (point[1] - start[1]) * dx
    ) / length


def _piece_box(piece):
    points = piece[1:] if piece[0] == "cubic" else (piece[1], piece[2])
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return (min(xs), min(ys), max(xs), max(ys))


def _boxes_meet(left, right):
    pad = 1e-8
    return not (
        left[2] < right[0] - pad
        or right[2] < left[0] - pad
        or left[3] < right[1] - pad
        or right[3] < left[1] - pad
    )


def _proper_cross(a, b, c, d, include_ends=False):
    """Intersection of two chords, or None.

    A shared endpoint, a T-junction, and a collinear overlap are not
    crossings. Curve subdivision passes ``include_ends`` so a hit on a
    split point is kept; the caller still drops a real piece's endpoint.
    """
    rx = b.x() - a.x()
    ry = b.y() - a.y()
    sx = d.x() - c.x()
    sy = d.y() - c.y()
    denom = rx * sy - ry * sx
    if abs(denom) <= 1e-12:
        return None
    qpx = c.x() - a.x()
    qpy = c.y() - a.y()
    t = (qpx * sy - qpy * sx) / denom
    u = (qpx * ry - qpy * rx) / denom
    if include_ends:
        outside = (
            t < -1e-9 or t > 1.0 + 1e-9 or u < -1e-9 or u > 1.0 + 1e-9
        )
    else:
        outside = t <= 0.0 or t >= 1.0 or u <= 0.0 or u >= 1.0
    if outside:
        return None
    point = QPointF(a.x() + t * rx, a.y() + t * ry)
    if not include_ends and (
        _same_point(point, a) or _same_point(point, b)
        or _same_point(point, c) or _same_point(point, d)
    ):
        return None
    return point


def _polygons(path):
    if path is None or path.isEmpty():
        return []
    try:
        polygons = path.toSubpathPolygons()
    except TypeError:
        polygons = path.toSubpathPolygons(QTransform())
    return list(polygons)


def _clean_ring(polygon):
    points = []
    for point in polygon:
        current = QPointF(point.x(), point.y())
        if points and _same_point(points[-1], current):
            continue
        points.append(current)
    if len(points) >= 2 and _same_point(points[0], points[-1]):
        points.pop()
    return points


def _abs_area(ring):
    count = len(ring)
    if count < 3:
        return 0.0
    acc = 0.0
    for index in range(count):
        nxt = ring[(index + 1) % count]
        acc += ring[index].x() * nxt.y() - nxt.x() * ring[index].y()
    return abs(acc) * 0.5


def _centroid(ring):
    count = len(ring)
    acc = 0.0
    cx = 0.0
    cy = 0.0
    for index in range(count):
        nxt = ring[(index + 1) % count]
        cross = ring[index].x() * nxt.y() - nxt.x() * ring[index].y()
        acc += cross
        cx += (ring[index].x() + nxt.x()) * cross
        cy += (ring[index].y() + nxt.y()) * cross
    if abs(acc) < 1e-18:
        return QPointF(
            sum(point.x() for point in ring) / float(count),
            sum(point.y() for point in ring) / float(count),
        )
    return QPointF(cx / (3.0 * acc), cy / (3.0 * acc))


def _point_in_ring(point, ring):
    x = point.x()
    y = point.y()
    inside = False
    count = len(ring)
    previous = count - 1
    for index in range(count):
        xi = ring[index].x()
        yi = ring[index].y()
        xj = ring[previous].x()
        yj = ring[previous].y()
        if (yi > y) != (yj > y):
            cross_x = (xj - xi) * (y - yi) / (yj - yi) + xi
            if x < cross_x:
                inside = not inside
        previous = index
    return inside


def _unique_points(points):
    unique = []
    for point in points:
        if any(_same_point(point, kept) for kept in unique):
            continue
        unique.append(point)
    return unique
