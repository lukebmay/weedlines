# -*- coding: utf-8 -*-
"""Closed subpaths, the one twin collapse, nesting, and keep fill."""
from __future__ import division

import math

from .paths import split_painter_path
from .qt import QPainterPath, QPointF, QRectF, QTransform, Qt

# padding indices match job.models.Padding
_LEFT, _TOP, _RIGHT, _BOTTOM = 0, 1, 2, 3


def even_odd_keep_fill(path):
    """Design keep fill: rings keep holes, sibling keep islands *union*.

    Nested holes (letter O counter, frame interior) stay waste. Overlapping
    design islands stay keep — keep∩keep is still design vinyl, never
    weedable. (Plain even-odd XOR would punch an overlap into waste.)

    Historical name kept for callers; nesting is containment-based, not a
    global even-odd of every subpath.
    """
    return design_keep_fill(path)


def design_keep_fill(path):
    """Union of keep islands (each island = body minus its direct holes)."""
    fill = QPainterPath()
    closed = list_closed_subpaths(path)
    if not closed:
        return fill
    nodes = _nest_closed_paths(closed)
    for node in nodes:
        if node['depth'] % 2 != 0:
            continue
        solid = QPainterPath(node['path'])
        for child in node['children']:
            # Direct hole in this keep body (odd relative nesting).
            if child['depth'] == node['depth'] + 1:
                try:
                    solid = solid.subtracted(child['path'])
                except Exception:
                    # Older Qt: fall back to even-odd of body+hole only.
                    hole_fill = QPainterPath()
                    hole_fill.setFillRule(Qt.OddEvenFill)
                    hole_fill.addPath(node['path'])
                    hole_fill.addPath(child['path'])
                    solid = hole_fill
        if solid.isEmpty():
            continue
        fill = solid if fill.isEmpty() else fill.united(solid)
    if fill.isEmpty():
        # Degenerate: single open strokes / empty nest — last resort.
        fill.setFillRule(Qt.OddEvenFill)
        for sp in closed:
            fill.addPath(sp)
    return fill


# Older name; same design keep fill (not a solid disk of every outline).
closed_fill_union = even_odd_keep_fill


def list_closed_subpaths(path, tol=1e-4):
    """Return closed subpaths of *path* (start≈end, enough elements).

    Near-duplicate outlines (Inkscape fill+stroke twins, etc.) are collapsed
    so nesting / keep-fill do not treat a second copy as a solid slab that
    paints over hollow frame waste.
    """
    result = []
    for sp in split_painter_path(path):
        if _subpath_is_closed(sp, tol=tol):
            result.append(sp)
    return _dedupe_closed_subpaths(result)


def _dedupe_closed_subpaths(closed, tol=0.05):
    """Drop near-identical closed outlines, keeping the first of each twin."""
    if len(closed) < 2:
        return list(closed)
    kept = []
    meta = []  # (path, bbox, area, centroid)
    for sp in closed:
        if sp is None or sp.isEmpty():
            continue
        br = sp.boundingRect()
        area = _path_area(sp)
        c = _path_centroid(sp)
        dup = False
        for other, obr, oarea, oc in meta:
            area_tol = max(tol, 0.01 * max(area, oarea, 1.0))
            if abs(area - oarea) > area_tol:
                continue
            if (abs(br.x() - obr.x()) > tol
                    or abs(br.y() - obr.y()) > tol
                    or abs(br.width() - obr.width()) > tol
                    or abs(br.height() - obr.height()) > tol):
                continue
            if math.hypot(c.x() - oc.x(), c.y() - oc.y()) > max(2.0 * tol, 1.0):
                continue
            # Same place + same size: treat as a twin even if winding differs.
            probe_a = _interior_point(sp)
            probe_b = _interior_point(other)
            if other.contains(probe_a) or sp.contains(probe_b):
                dup = True
                break
        if dup:
            continue
        kept.append(sp)
        meta.append((sp, br, area, c))
    return kept


def padded_work_rect(keep_path, padding=None):
    """Padded work rectangle around keep bbox."""
    return _padded_rect(keep_path.boundingRect(), _normalize_padding(padding))


def _normalize_padding(padding):
    if not padding:
        return [0.0, 0.0, 0.0, 0.0]
    pad = list(padding)
    while len(pad) < 4:
        pad.append(0.0)
    return [float(pad[i]) for i in range(4)]


def _padded_rect(bbox, padding):
    x = bbox.x() - padding[_LEFT]
    y = bbox.y() - padding[_TOP]
    w = bbox.width() + padding[_LEFT] + padding[_RIGHT]
    h = bbox.height() + padding[_TOP] + padding[_BOTTOM]
    return QRectF(x, y, w, h)


def _subpath_is_closed(sp, tol=1e-4):
    n = sp.elementCount()
    if n < 3:
        return False
    e0 = sp.elementAt(0)
    eN = sp.elementAt(n - 1)
    return (abs(e0.x - eN.x) <= tol and abs(e0.y - eN.y) <= tol)


def _polyline_points(path, max_pts=256):
    """Flattened outline vertices (curves sampled; Bezier controls omitted)."""
    pts = []
    polys = _subpath_polygons(path)
    if not polys:
        return pts
    for p in polys[0]:
        pt = QPointF(p)
        if pts and abs(pts[-1].x() - pt.x()) < 1e-12 and abs(
                pts[-1].y() - pt.y()) < 1e-12:
            continue
        pts.append(pt)
    if len(pts) <= max_pts:
        return pts
    step = max(len(pts) // max_pts, 1)
    return pts[::step]


def _subpath_polygons(path):
    if path is None or path.isEmpty():
        return []
    try:
        polys = path.toSubpathPolygons()
    except TypeError:
        polys = path.toSubpathPolygons(QTransform())
    return list(polys)


def _unique_ring(pts, tol=1e-6):
    """Drop a closing duplicate so the ring can be indexed modulo n."""
    if len(pts) >= 2 and math.hypot(
            pts[0].x() - pts[-1].x(), pts[0].y() - pts[-1].y()) <= tol:
        return pts[:-1]
    return pts


def _signed_area(pts):
    ring = _unique_ring(pts)
    n = len(ring)
    if n < 3:
        return 0.0
    acc = 0.0
    for i in range(n):
        j = (i + 1) % n
        acc += ring[i].x() * ring[j].y() - ring[j].x() * ring[i].y()
    return acc * 0.5


def _shoelace_area(pts):
    return abs(_signed_area(pts))


def _polygon_centroid(pts):
    ring = _unique_ring(pts)
    n = len(ring)
    if n < 1:
        return QPointF(0.0, 0.0)
    if n < 3:
        sx = sum(p.x() for p in ring) / float(n)
        sy = sum(p.y() for p in ring) / float(n)
        return QPointF(sx, sy)
    acc = 0.0
    cx = cy = 0.0
    for i in range(n):
        j = (i + 1) % n
        cross = ring[i].x() * ring[j].y() - ring[j].x() * ring[i].y()
        acc += cross
        cx += (ring[i].x() + ring[j].x()) * cross
        cy += (ring[i].y() + ring[j].y()) * cross
    if abs(acc) < 1e-18:
        sx = sum(p.x() for p in ring) / float(n)
        sy = sum(p.y() for p in ring) / float(n)
        return QPointF(sx, sy)
    return QPointF(cx / (3.0 * acc), cy / (3.0 * acc))


def _path_area(path):
    """Polygon area (not bbox)."""
    pts = _unique_ring(_polyline_points(path))
    area = _shoelace_area(pts)
    if area > 1e-12:
        return area
    r = path.boundingRect()
    return abs(r.width() * r.height())


def _path_centroid(path):
    pts = _polyline_points(path)
    if len(pts) >= 3:
        return _polygon_centroid(pts)
    r = path.boundingRect()
    return QPointF(r.center())


def _interior_point(path):
    """A point inside the filled path — not bbox-center (may lie outside)."""
    pts = _unique_ring(_polyline_points(path))
    if len(pts) >= 3:
        c = _polygon_centroid(pts)
        if path.contains(c):
            return c
        n = len(pts)
        for i in range(n):
            a, b = pts[i], pts[(i + 1) % n]
            mx = 0.5 * (a.x() + b.x())
            my = 0.5 * (a.y() + b.y())
            ex, ey = b.x() - a.x(), b.y() - a.y()
            nx, ny = -ey, ex
            ln = math.hypot(nx, ny) or 1.0
            nx, ny = nx / ln, ny / ln
            for sign in (1.0, -1.0):
                probe = QPointF(mx + sign * nx * 0.75, my + sign * ny * 0.75)
                if path.contains(probe):
                    return probe
    br = path.boundingRect()
    for i in range(1, 8):
        for j in range(1, 8):
            p = QPointF(
                br.left() + br.width() * i / 8.0,
                br.top() + br.height() * j / 8.0)
            if path.contains(p):
                return p
    return QPointF(br.center())


def _nest_closed_paths(closed_paths):
    """Parent/children by interior-point containment + smaller polygon area."""
    nodes = []
    for p in closed_paths:
        nodes.append({
            'path': p,
            'area': _path_area(p),
            'inside': _interior_point(p),
            'parent': None,
            'children': [],
            'depth': 0,
        })
    for i, child in enumerate(nodes):
        best = None
        best_area = None
        probe = child['inside']
        for j, parent in enumerate(nodes):
            if i == j:
                continue
            if parent['area'] <= child['area']:
                continue
            if not parent['path'].contains(probe):
                continue
            if best is None or parent['area'] < best_area:
                best = parent
                best_area = parent['area']
        if best is not None:
            child['parent'] = best
            best['children'].append(child)
    for node in nodes:
        depth = 0
        p = node['parent']
        while p is not None:
            depth += 1
            p = p['parent']
        node['depth'] = depth
    return nodes
