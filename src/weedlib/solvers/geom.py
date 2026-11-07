# -*- coding: utf-8 -*-
"""Point, ray, and ring predicates with no stage policy."""
from __future__ import division

import math
from collections import namedtuple

from ..qt import QPainterPath, QPointF
from ..keep import (
    _path_centroid,
    _polyline_points,
    _signed_area,
    _subpath_polygons,
    _unique_ring,
)


def _add_line_segs(out, segs):
    for x0, y0, x1, y1 in segs:
        out.moveTo(x0, y0)
        out.lineTo(x1, y1)


def _path_to_rings(path):
    """Closed rings as lists of QPointF (no closing duplicate)."""
    rings = []
    for poly in _subpath_polygons(path):
        pts = [QPointF(p) for p in poly]
        ring = _unique_ring(pts)
        if len(ring) >= 3:
            rings.append(ring)
    return rings


def _rings_to_path(rings):
    out = QPainterPath()
    for ring in rings:
        if len(ring) < 3:
            continue
        out.moveTo(ring[0])
        for p in ring[1:]:
            out.lineTo(p)
        out.closeSubpath()
    return out


def _ensure_ccw(ring):
    if _signed_area(ring) < 0:
        return list(reversed(ring))
    return list(ring)


def _rect_as_ring(rect):
    return [
        QPointF(rect.left(), rect.top()),
        QPointF(rect.right(), rect.top()),
        QPointF(rect.right(), rect.bottom()),
        QPointF(rect.left(), rect.bottom()),
    ]


def _rdp(pts, epsilon):
    if len(pts) < 3:
        return list(pts)
    ax, ay = pts[0].x(), pts[0].y()
    bx, by = pts[-1].x(), pts[-1].y()
    dx, dy = bx - ax, by - ay
    ln = math.hypot(dx, dy)
    max_d = -1.0
    idx = 0
    for i in range(1, len(pts) - 1):
        if ln < 1e-15:
            d = math.hypot(pts[i].x() - ax, pts[i].y() - ay)
        else:
            d = abs((pts[i].x() - ax) * dy - (pts[i].y() - ay) * dx) / ln
        if d > max_d:
            max_d = d
            idx = i
    if max_d > epsilon:
        left = _rdp(pts[:idx + 1], epsilon)
        right = _rdp(pts[idx:], epsilon)
        return left[:-1] + right
    return [pts[0], pts[-1]]


def _simplify_ring(ring, epsilon, max_pts=36):
    if len(ring) <= 4:
        return ring
    pts = list(ring) + [ring[0]]
    simple = _rdp(pts, epsilon)
    if simple and math.hypot(
            simple[0].x() - simple[-1].x(),
            simple[0].y() - simple[-1].y()) <= 1e-9:
        simple = simple[:-1]
    if len(simple) < 3:
        return ring
    if len(simple) > max_pts:
        n = len(simple)
        simple = [
            simple[int(i * n / float(max_pts)) % n]
            for i in range(max_pts)
        ]
    return simple


def _convex_hull(points):
    pts = sorted(set((p.x(), p.y()) for p in points))
    if len(pts) <= 2:
        return [QPointF(x, y) for x, y in pts]

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    ring = lower[:-1] + upper[:-1]
    return [QPointF(x, y) for x, y in ring]


def _point_in_convex(pt, hull, margin=0.0):
    """True if *pt* is inside convex *hull* by at least *margin*."""
    n = len(hull)
    if n < 3:
        return False
    ring = _ensure_ccw(hull)
    for i in range(n):
        a, b = ring[i], ring[(i + 1) % n]
        ex, ey = b.x() - a.x(), b.y() - a.y()
        ln = math.hypot(ex, ey) or 1.0
        # inward normal for CCW
        nx, ny = -ey / ln, ex / ln
        dist = (pt.x() - a.x()) * nx + (pt.y() - a.y()) * ny
        if dist < margin:
            return False
    return True


def _angle_turn_deg(p0, p1, p2):
    """Exterior turn angle at p1 in degrees (0 = straight, 180 = reverse)."""
    v1x, v1y = p0.x() - p1.x(), p0.y() - p1.y()
    v2x, v2y = p2.x() - p1.x(), p2.y() - p1.y()
    n1 = math.hypot(v1x, v1y)
    n2 = math.hypot(v2x, v2y)
    if n1 < 1e-12 or n2 < 1e-12:
        return 0.0
    v1x, v1y = v1x / n1, v1y / n1
    v2x, v2y = v2x / n2, v2y / n2
    dot = max(-1.0, min(1.0, v1x * v2x + v1y * v2y))
    interior = math.degrees(math.acos(dot))
    return 180.0 - interior


def _orient_outward(px, py, nx, ny, keep_path):
    """Flip (nx, ny) so it points out of keep at (px, py)."""
    ln = math.hypot(nx, ny) or 1.0
    nx, ny = nx / ln, ny / ln
    probe = 2.0
    a = QPointF(px + nx * probe, py + ny * probe)
    b = QPointF(px - nx * probe, py - ny * probe)
    a_in = keep_path.contains(a)
    b_in = keep_path.contains(b)
    if a_in and not b_in:
        return -nx, -ny
    if b_in and not a_in:
        return nx, ny
    c = _path_centroid(keep_path)
    if nx * (c.x() - px) + ny * (c.y() - py) > 0:
        return -nx, -ny
    return nx, ny


def _outward_normal_at_corner(p0, p1, p2, keep_path):
    """Unit direction from corner into waste (away from keep interior)."""
    v1x, v1y = p0.x() - p1.x(), p0.y() - p1.y()
    v2x, v2y = p2.x() - p1.x(), p2.y() - p1.y()
    n1 = math.hypot(v1x, v1y) or 1.0
    n2 = math.hypot(v2x, v2y) or 1.0
    v1x, v1y = v1x / n1, v1y / n1
    v2x, v2y = v2x / n2, v2y / n2
    bx, by = v1x + v2x, v1y + v2y
    bn = math.hypot(bx, by)
    if bn < 1e-9:
        bx, by = -v1y, v1x
        bn = 1.0
    return _orient_outward(p1.x(), p1.y(), bx / bn, by / bn, keep_path)


def _iter_line_segs(path):
    if path is None or path.isEmpty():
        return
    x0 = y0 = None
    for i in range(path.elementCount()):
        e = path.elementAt(i)
        if e.isMoveTo():
            x0, y0 = e.x, e.y
            continue
        x1, y1 = e.x, e.y
        if x0 is not None:
            yield (x0, y0, x1, y1)
        x0, y0 = x1, y1


def _seg_proper_cross(ax, ay, bx, by, cx, cy, dx, dy, eps=1e-4):
    """True if interiors of ab and cd cross (T-junctions are not a cross)."""
    den = (bx - ax) * (dy - cy) - (by - ay) * (dx - cx)
    if abs(den) < 1e-18:
        return False
    t = ((cx - ax) * (dy - cy) - (cy - ay) * (dx - cx)) / den
    u = ((cx - ax) * (by - ay) - (cy - ay) * (bx - ax)) / den
    return eps < t < 1.0 - eps and eps < u < 1.0 - eps


def _seg_crosses_path(path, seg):
    x0, y0, x1, y1 = seg
    for s in _iter_line_segs(path):
        if _seg_proper_cross(x0, y0, x1, y1, s[0], s[1], s[2], s[3]):
            return True
    return False


def _one_outline(path):
    """One ring as ``(x, y)`` points, or None. Not a cut."""
    pts = _polyline_points(path)
    if len(pts) < 2:
        return None
    return [(p.x(), p.y()) for p in pts]


def _convex_tips(outline, angle_deg):
    """Convex outline vertices whose exterior turn is at least *angle_deg*."""
    pts = _unique_ring(_polyline_points(outline))
    n = len(pts)
    if n < 3:
        return []
    ccw = _signed_area(pts) > 0
    tips = []
    for i in range(n):
        p0, p1, p2 = pts[(i - 1) % n], pts[i], pts[(i + 1) % n]
        ix, iy = p1.x() - p0.x(), p1.y() - p0.y()
        ox, oy = p2.x() - p1.x(), p2.y() - p1.y()
        cross = ix * oy - iy * ox
        is_convex = (cross > 0) == ccw
        if not is_convex:
            continue
        turn = _angle_turn_deg(p0, p1, p2)
        if turn < angle_deg:
            continue
        dx, dy = _outward_normal_at_corner(p0, p1, p2, outline)
        tips.append({
            'pt': p1, 'turn': turn, 'dx': dx, 'dy': dy,
            'p0': p0, 'p2': p2,
        })
    return tips


def _ray_hit_segment(ox, oy, dx, dy, ax, ay, bx, by, min_t=1e-9):
    """t along unit ray o+t d, or None if the segment is missed."""
    ex, ey = bx - ax, by - ay
    det = dx * ey - dy * ex
    if abs(det) < 1e-18:
        return None
    rx, ry = ax - ox, ay - oy
    t = (rx * ey - ry * ex) / det
    u = (rx * dy - ry * dx) / det
    if t >= min_t and 0.0 <= u <= 1.0:
        return t
    return None


def _ray_intersect_rings(ox, oy, dx, dy, rings, max_t=1e7):
    """First hit of a ray with any ring edge. (x, y, t) or None."""
    ln = math.hypot(dx, dy)
    if ln < 1e-15 or not rings:
        return None
    ux, uy = dx / ln, dy / ln
    best_t = None
    for ring in rings:
        n = len(ring)
        if n < 2:
            continue
        for i in range(n):
            a, b = ring[i], ring[(i + 1) % n]
            t = _ray_hit_segment(
                ox, oy, ux, uy, a.x(), a.y(), b.x(), b.y())
            if t is None or t > max_t:
                continue
            if best_t is None or t < best_t:
                best_t = t
    if best_t is None:
        return None
    return (ox + ux * best_t, oy + uy * best_t, best_t)


def _nearest_pair(path_a, path_b):
    """Closest sample points on two outlines. (pa, pb, dist) or None."""
    pairs = _outline_pairs(path_a, path_b)
    return pairs[0] if pairs else None


def _densify_ring(pts, max_edge=8.0):
    """Add vertices so no ring edge is longer than *max_edge*."""
    n = len(pts)
    if n < 2:
        return list(pts)
    out = []
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        out.append(a)
        dx, dy = b.x() - a.x(), b.y() - a.y()
        ln = math.hypot(dx, dy)
        if ln <= max_edge:
            continue
        steps = int(math.ceil(ln / max_edge))
        for k in range(1, steps):
            t = k / float(steps)
            out.append(QPointF(a.x() + dx * t, a.y() + dy * t))
    return out


def _outline_samples(path, max_pts=96):
    """Outline vertices and densified edges (on-path only).

    Bounding-box corners are *not* added: on curved glyphs they sit in
    empty waste and turn fuse bridges into cuts to nowhere. Multi-subpath
    bodies (host united with stacked satellites) contribute every ring.
    """
    if path is None or path.isEmpty():
        return []
    rings = _path_to_rings(path)
    if not rings:
        pts = list(_unique_ring(_polyline_points(path, max_pts=512)))
        rings = [pts] if pts else []
    pts = []
    for ring in rings:
        dens = _densify_ring(list(ring), max_edge=8.0)
        pts.extend(dens)
    if not pts:
        return []
    if len(pts) > max_pts:
        step = max(int(math.ceil(len(pts) / float(max_pts))), 1)
        pts = pts[::step]
    return pts


def _outline_pairs(path_a, path_b):
    """All sample pairs (pa, pb, dist), nearest first."""
    pts_a = _outline_samples(path_a)
    pts_b = _outline_samples(path_b)
    if not pts_a or not pts_b:
        return []
    pairs = []
    for pa in pts_a:
        for pb in pts_b:
            d = math.hypot(pb.x() - pa.x(), pb.y() - pa.y())
            pairs.append((pa, pb, d))
    pairs.sort(key=lambda t: t[2])
    return pairs


# Local keep frame at a point (C9 G0).
KeepFrameAt = namedtuple(
    'KeepFrameAt',
    ('t0', 't1', 'n_hat', 'vertex', 'turn_deg'))


def _unit_xy(dx, dy):
    ln = math.hypot(dx, dy)
    if ln < 1e-12:
        return None
    return (dx / ln, dy / ln)


def _keep_frame_at(path, p, edge_max=1.5):
    """Tangents and outward normal of *path* nearest *p*.

    Densifies each ring with max_edge=*edge_max*. Mid-edge: *t0* along the
    original edge, *t1* = -*t0*, *vertex* is None. Vertex with turn ≥ 25°:
    *t0*/*t1* along both *original* incident edges (not densified chords).
    Returns KeepFrameAt(t0, t1, n_hat, vertex, turn_deg) or None.
    """
    if path is None or path.isEmpty() or p is None:
        return None
    rings = _path_to_rings(path)
    if not rings:
        pts = _unique_ring(_polyline_points(path, max_pts=512))
        if len(pts) >= 3:
            rings = [pts]
    if not rings:
        return None
    px, py = p.x(), p.y()
    vtx_tol = max(0.35, 0.5 * float(edge_max))
    best = None  # (dist, qx, qy, orig_ring)
    for orig in rings:
        dens = _densify_ring(list(orig), max_edge=float(edge_max))
        hit = _nearest_on_rings(px, py, [dens])
        if hit is None:
            continue
        qx, qy, d = hit
        if best is None or d < best[0]:
            best = (d, qx, qy, orig)
    if best is None:
        return None
    _d, qx, qy, orig = best
    n = len(orig)
    # Prefer a sharp original vertex when the hit sits on it.
    best_vtx = None
    best_vtx_d = None
    for i in range(n):
        v = orig[i]
        vd = math.hypot(qx - v.x(), qy - v.y())
        if vd > vtx_tol:
            continue
        p0, p1, p2 = orig[(i - 1) % n], v, orig[(i + 1) % n]
        turn = _angle_turn_deg(p0, p1, p2)
        if turn < 25.0:
            continue
        if best_vtx_d is None or vd < best_vtx_d:
            best_vtx_d = vd
            best_vtx = (i, p0, p1, p2, turn)
    if best_vtx is not None:
        _i, p0, p1, p2, turn = best_vtx
        t0 = _unit_xy(p0.x() - p1.x(), p0.y() - p1.y())
        t1 = _unit_xy(p2.x() - p1.x(), p2.y() - p1.y())
        if t0 is None or t1 is None:
            return None
        nx, ny = _outward_normal_at_corner(p0, p1, p2, path)
        return KeepFrameAt(t0, t1, (nx, ny), QPointF(p1), turn)
    # Mid-edge: nearest *original* edge (not a densified chord).
    best_e = None
    best_ed = None
    for i in range(n):
        a, b = orig[i], orig[(i + 1) % n]
        ed = _point_seg_dist(qx, qy, a.x(), a.y(), b.x(), b.y())
        if best_ed is None or ed < best_ed:
            best_ed = ed
            best_e = (a, b)
    if best_e is None:
        return None
    a, b = best_e
    t0 = _unit_xy(b.x() - a.x(), b.y() - a.y())
    if t0 is None:
        return None
    t1 = (-t0[0], -t0[1])
    nx, ny = _orient_outward(qx, qy, -t0[1], t0[0], path)
    return KeepFrameAt(t0, t1, (nx, ny), None, 0.0)


def _included_angle_deg(p, w_hat, path):
    """Included angle α between weed direction *w_hat* and keep at *p*.

    *w_hat* is unit, away from keep into waste. Mid-edge:
    α = acos(clip(|ŵ·t̂|, 0, 1)) — 0° tangent, 90° square. Vertex: min of
    that vs both incident edges (thin-wedge risk). Returns degrees or None.
    """
    if w_hat is None or path is None or p is None:
        return None
    wx, wy = float(w_hat[0]), float(w_hat[1])
    wn = math.hypot(wx, wy)
    if wn < 1e-12:
        return None
    wx, wy = wx / wn, wy / wn
    frame = _keep_frame_at(path, p)
    if frame is None:
        return None

    def alpha_vs(t):
        dot = abs(wx * t[0] + wy * t[1])
        return math.degrees(math.acos(max(0.0, min(1.0, dot))))

    if frame.vertex is None:
        return alpha_vs(frame.t0)
    return min(alpha_vs(frame.t0), alpha_vs(frame.t1))


def _convex_corners(path, min_turn=40):
    """Convex outline vertices with exterior turn ≥ *min_turn* degrees."""
    if path is None or path.isEmpty():
        return []
    rings = _path_to_rings(path)
    if not rings:
        pts = _unique_ring(_polyline_points(path, max_pts=256))
        rings = [pts] if len(pts) >= 3 else []
    out = []
    for ring in rings:
        n = len(ring)
        if n < 3:
            continue
        ccw = _signed_area(ring) > 0
        for i in range(n):
            p0, p1, p2 = ring[(i - 1) % n], ring[i], ring[(i + 1) % n]
            cross = ((p1.x() - p0.x()) * (p2.y() - p1.y())
                     - (p1.y() - p0.y()) * (p2.x() - p1.x()))
            is_convex = (cross > 0) == ccw
            turn = _angle_turn_deg(p0, p1, p2)
            if is_convex and turn >= float(min_turn):
                out.append(QPointF(p1))
    return out


def _vertex_weed_degree(p, weed_path, r=1.2):
    """Count weed segment endpoints within *r* of *p*."""
    if p is None or weed_path is None or weed_path.isEmpty():
        return 0
    px, py = p.x(), p.y()
    rr = float(r)
    count = 0
    for x0, y0, x1, y1 in _iter_line_segs(weed_path):
        if math.hypot(x0 - px, y0 - py) <= rr:
            count += 1
        if math.hypot(x1 - px, y1 - py) <= rr:
            count += 1
    return count


def _ray_hit_path(p, ux, uy, path, max_t):
    """Nearest ring hit from *p* along ±(ux,uy), or None."""
    rings = _path_to_rings(path)
    if not rings or p is None:
        return None
    best = None
    best_t = None
    for sgn in (1.0, -1.0):
        hit = _ray_intersect_rings(
            p.x(), p.y(), sgn * ux, sgn * uy, rings, max_t=max_t)
        if hit is None:
            continue
        t = float(hit[2]) if len(hit) > 2 else math.hypot(
            hit[0] - p.x(), hit[1] - p.y())
        if t < 1e-6:
            continue
        if best_t is None or t < best_t:
            best_t = t
            best = QPointF(hit[0], hit[1])
    return best


def _pt_xy(p):
    """(x, y) from a QPointF-like or (x, y) pair."""
    if hasattr(p, 'x'):
        return float(p.x()), float(p.y())
    return float(p[0]), float(p[1])


def _line_line_s(ox, oy, tx, ty, ax, ay, bx, by, eps=1e-12):
    """Parameter s for o+s·t̂ intersecting segment ab, or None."""
    dx, dy = bx - ax, by - ay
    den = tx * dy - ty * dx
    if abs(den) < eps:
        return None
    sx, sy = ax - ox, ay - oy
    s = (sx * dy - sy * dx) / den
    u = (sx * ty - sy * tx) / den
    if u < -eps or u > 1.0 + eps:
        return None
    return s


def _point_near_path(px, py, path, tol=2.5):
    """True if (px, py) lies within *tol* of *path*'s outline.

    Closed rings are preferred; open polylines (peel frames) fall back to
    iterated line segments so frame landings still count.
    """
    if path is None or path.isEmpty():
        return False
    br = path.boundingRect().adjusted(-tol, -tol, tol, tol)
    if not br.contains(QPointF(px, py)):
        return False
    rings = _path_to_rings(path)
    if rings:
        for ring in rings:
            n = len(ring)
            if n < 2:
                continue
            for i in range(n):
                a, b = ring[i], ring[(i + 1) % n]
                if _point_seg_dist(px, py, a.x(), a.y(), b.x(), b.y()) <= tol:
                    return True
        return False
    for x0, y0, x1, y1 in _iter_line_segs(path):
        if _point_seg_dist(px, py, x0, y0, x1, y1) <= tol:
            return True
    return False


def _rotate_hat(ux, uy, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return (c * ux - s * uy, s * ux + c * uy)


def _closest_on_line_segs(px, py, path):
    """Closest point on any line segment of *path*, or None."""
    if path is None or path.isEmpty():
        return None
    best = None
    for x0, y0, x1, y1 in _iter_line_segs(path):
        vx, vy = x1 - x0, y1 - y0
        ln2 = vx * vx + vy * vy
        if ln2 < 1e-12:
            qx, qy = x0, y0
        else:
            t = ((px - x0) * vx + (py - y0) * vy) / ln2
            t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
            qx, qy = x0 + t * vx, y0 + t * vy
        d = math.hypot(px - qx, py - qy)
        if best is None or d < best[0]:
            best = (d, qx, qy)
    if best is None:
        return None
    return (best[1], best[2], best[0])


def _point_seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    ln2 = dx * dx + dy * dy
    if ln2 < 1e-18:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / ln2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _nearest_pt_index(pts, q):
    best_i = 0
    best_d = None
    for i, p in enumerate(pts):
        d = math.hypot(p.x() - q.x(), p.y() - q.y())
        if best_d is None or d < best_d:
            best_d = d
            best_i = i
    return best_i


def _in_keep_interior(keep_fill, p, coast_tol=0.05):
    """True if *p* is clearly inside keep (not on/near the coast)."""
    if keep_fill is None or keep_fill.isEmpty() or p is None:
        return False
    if not keep_fill.contains(p):
        return False
    # contains() is unreliable on the outline; exact corner landings sit there.
    return not _point_near_path(p.x(), p.y(), keep_fill, tol=coast_tol)


def _nearest_on_rings(px, py, rings):
    """Closest point on any ring edge. (x, y, dist) or None."""
    best = None
    best_d = None
    for ring in rings:
        n = len(ring)
        if n < 2:
            continue
        for i in range(n):
            a, b = ring[i], ring[(i + 1) % n]
            ax, ay, bx, by = a.x(), a.y(), b.x(), b.y()
            dx, dy = bx - ax, by - ay
            ln2 = dx * dx + dy * dy
            if ln2 < 1e-18:
                qx, qy = ax, ay
            else:
                t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / ln2))
                qx, qy = ax + t * dx, ay + t * dy
            d = math.hypot(qx - px, qy - py)
            if best_d is None or d < best_d:
                best_d = d
                best = (qx, qy, d)
    return best
