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
    left_segments = _border_segments(left)[0]
    right_segments = _border_segments(right)[0]
    for start, end in left_segments:
        for other, finish in right_segments:
            if _proper_cross(start, end, other, finish) is not None:
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
    flat = []
    for group, subpath in enumerate(subpaths):
        segments, closed = _border_segments(subpath)
        count = len(segments)
        for index, segment in enumerate(segments):
            flat.append((group, index, count, closed, segment))
    points = []
    for left in range(len(flat)):
        group, i0, n0, closed, (a, b) = flat[left]
        for right in range(left + 1, len(flat)):
            other, i1, _n1, _closed, (c, d) = flat[right]
            if group == other and _adjacent_segments(i0, i1, n0, closed):
                continue
            point = _proper_cross(a, b, c, d)
            if point is None:
                continue
            points.append(point)
    points = _unique_points(points)
    points.sort(key=lambda point: (point.x(), point.y()))
    return [Defect(kind="self-overlap", target=point) for point in points]


def _border_segments(subpath):
    """Real border only. An open subpath's painted close is not a segment."""
    polygons = _polygons(subpath)
    if not polygons:
        return [], False
    raw = [QPointF(point.x(), point.y()) for point in polygons[0]]
    segments = []
    for start, end in zip(raw, raw[1:]):
        if not _same_point(start, end):
            segments.append((start, end))
    closed = _subpath_is_closed(subpath)
    if not closed and segments and _same_point(segments[-1][1], segments[0][0]):
        segments.pop()
    elif closed and segments and not _same_point(segments[-1][1], segments[0][0]):
        segments.append((segments[-1][1], segments[0][0]))
    return segments, closed


def _adjacent_segments(left, right, count, closed):
    if abs(left - right) == 1:
        return True
    return bool(closed and count > 1 and {left, right} == {0, count - 1})


def _proper_cross(a, b, c, d):
    """Intersection in the interior of both segments, or None.

    A shared endpoint, a T-junction, and a collinear overlap are not crossings.
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
    if t <= 0.0 or t >= 1.0 or u <= 0.0 or u >= 1.0:
        return None
    point = QPointF(a.x() + t * rx, a.y() + t * ry)
    if (_same_point(point, a) or _same_point(point, b)
            or _same_point(point, c) or _same_point(point, d)):
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
