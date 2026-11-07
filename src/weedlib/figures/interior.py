# -*- coding: utf-8 -*-
"""Sample points and area tests for a painted interior."""
from __future__ import division

import math

from ..qt import QPointF, QTransform

from .borders import (
    _SAME_POINT_TOL,
    _cubic_distance,
    _same_point,
    _segment_borders,
    _segment_distance,
)

# Below this, a boolean sliver is a touch or a shared edge, not area.
_AREA_EPS = 1e-6
# A point this close to a border is not an interior point.
_ON_BORDER = 1e-6


def _outside_fill(inner, outer):
    """True when *inner* has painted area outside *outer*.

    Subtracting a curve can leave a sliver that the outer fill still
    contains. That sliver is the chord gap, not area outside.
    """
    leftover = inner.subtracted(outer).simplified()
    if not _has_area(leftover):
        return False
    saw_inside = False
    for polygon in _polygons(leftover):
        ring = _clean_ring(polygon)
        if len(ring) < 3 or _abs_area(ring) <= _AREA_EPS:
            continue
        point = _filled_point(ring, leftover)
        if point is None:
            continue
        if not outer.contains(point):
            return True
        saw_inside = True
    return not saw_inside


def _interior_point(point, left, right):
    """False when *point* only touches a border of either fill."""
    if not (left.contains(point) and right.contains(point)):
        return False
    if _border_distance(point, left) <= _ON_BORDER:
        return False
    if _border_distance(point, right) <= _ON_BORDER:
        return False
    return True


def _border_distance(point, path):
    """Distance from *point* to the nearest border piece of *path*."""
    target = (point.x(), point.y())
    best = None
    for piece in _segment_borders(path):
        if piece[0] == "line":
            dist = _segment_distance(target, piece[1], piece[2])
        else:
            dist = _cubic_distance(piece, target)
        if best is None or dist < best:
            best = dist
            if best <= _ON_BORDER:
                return best
    if best is None:
        return 1.0
    return best


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
