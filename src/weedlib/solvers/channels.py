# -*- coding: utf-8 -*-
"""Keep-to-wall channel and tip spokes."""
from __future__ import division

import math

from ..qt import QPainterPath, QPointF
from ..keep import (
    _polyline_points,
    _unique_ring,
)

from .rules import (
    DEFAULT_CHANNEL_STANDOFF,
    _SEARCH_PROBE,
)
from . import clip as _sol_clip
from . import geom as _sol_geom


def _keep_to_collar_landings(weed_path, cluster, collar_rings, standoff,
                             tol=None, ring_tol=2.0):
    """Wall-ring (x, y) ends of keep→wall radials (not peel-rail edges)."""
    from . import emit as _sol_emit
    if weed_path is None or weed_path.isEmpty() or not collar_rings:
        return []
    tol = float(standoff + 1.5 if tol is None else tol)
    keep_edges = []
    for b in cluster:
        if b is None or b.isEmpty():
            continue
        keep_edges.extend(_sol_emit._keep_outline_edges(b))
    if not keep_edges:
        return []
    out = []
    for x0, y0, x1, y1 in _sol_geom._iter_line_segs(weed_path):
        # Rail edges sit on the ring at mid; radials cross waste.
        mx, my = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
        mid = _sol_geom._nearest_on_rings(mx, my, collar_rings)
        if mid is not None and mid[2] <= ring_tol:
            continue
        a_keep = _sol_emit._point_near_edges(x0, y0, keep_edges, tol)
        b_keep = _sol_emit._point_near_edges(x1, y1, keep_edges, tol)
        a_col = _sol_geom._nearest_on_rings(x0, y0, collar_rings)
        b_col = _sol_geom._nearest_on_rings(x1, y1, collar_rings)
        a_on = a_col is not None and a_col[2] <= tol
        b_on = b_col is not None and b_col[2] <= tol
        if a_keep and b_on and not b_keep:
            out.append((x1, y1))
        elif b_keep and a_on and not a_keep:
            out.append((x0, y0))
    return out


def _has_keep_to_collar_channel(weed_path, cluster, collar_rings, standoff,
                                tol=None):
    """True if some open weed already runs from keep to the wall rings."""
    from . import emit as _sol_emit
    if weed_path is None or weed_path.isEmpty() or not collar_rings:
        return False
    tol = float(standoff + 1.5 if tol is None else tol)
    keep_edges = []
    for b in cluster:
        if b is None or b.isEmpty():
            continue
        keep_edges.extend(_sol_emit._keep_outline_edges(b))
    if not keep_edges:
        return False
    for x0, y0, x1, y1 in _sol_geom._iter_line_segs(weed_path):
        a_keep = _sol_emit._point_near_edges(x0, y0, keep_edges, tol)
        b_keep = _sol_emit._point_near_edges(x1, y1, keep_edges, tol)
        a_col = _sol_geom._nearest_on_rings(x0, y0, collar_rings)
        b_col = _sol_geom._nearest_on_rings(x1, y1, collar_rings)
        a_on = a_col is not None and a_col[2] <= tol
        b_on = b_col is not None and b_col[2] <= tol
        if (a_keep and b_on) or (b_keep and a_on):
            return True
    return False


def _waste_seg_or_none(x0, y0, x1, y1, keep_fill, work, min_cut,
                       container=None):
    capped = _sol_clip._clip_seg_to_rect(x0, y0, x1, y1, work)
    if capped is None:
        return None
    if math.hypot(capped[2] - capped[0], capped[3] - capped[1]) < min_cut:
        return None
    n = 12
    for i in range(1, n):
        t = i / float(n)
        x = capped[0] + (capped[2] - capped[0]) * t
        y = capped[1] + (capped[3] - capped[1]) * t
        p = QPointF(x, y)
        if _sol_geom._in_keep_interior(keep_fill, p):
            return None
        if container is not None and not container.contains(p):
            return None
    return capped


def _tip_spokes(tips, collar_rings, frame_ring, keep_fill, work,
                clearance, min_cut, max_spokes, against=None):
    """One spoke per convex tip: tip → nearest of collar or frame."""
    from . import emit as _sol_emit
    out = QPainterPath()
    ranked = sorted(tips, key=lambda t: -t['turn'])
    used = []
    targets = list(collar_rings or [])
    extra = [frame_ring] if frame_ring else []
    for tip in ranked:
        if len(used) >= max_spokes:
            break
        p1 = tip['pt']
        if any(math.hypot(p1.x() - u.x(), p1.y() - u.y()) < min_cut * 3
               for u in used):
            continue
        dx, dy = tip['dx'], tip['dy']
        standoff = max(float(clearance), min_cut * 0.25)
        sx = p1.x() + dx * standoff
        sy = p1.y() + dy * standoff
        hit_c = _sol_geom._ray_intersect_rings(sx, sy, dx, dy, targets)
        hit_f = _sol_geom._ray_intersect_rings(sx, sy, dx, dy, extra)
        hit = None
        if hit_c is not None and hit_f is not None:
            hit = hit_c if hit_c[2] <= hit_f[2] else hit_f
        else:
            hit = hit_c if hit_c is not None else hit_f
        if hit is None:
            continue
        seg = _waste_seg_or_none(sx, sy, hit[0], hit[1], keep_fill, work, min_cut)
        if seg is None:
            continue
        if against is not None and _sol_geom._seg_crosses_path(against, seg):
            continue
        _sol_emit._add_seg(out, seg, min_cut)
        used.append(p1)
    return out


def _shortest_outer_channel(outline, collar_rings, keep_fill, work, min_cut,
                            clearance=0.0, container=None):
    """Shortest waste cut from keep to wall rings (peel frame or container).

    Keep end is the outline point. Channel standoff is only a ray-search
    probe — not a permanent gap at keep. *collar_rings* may be a grown peel
    rail or the design-container coast (D013).
    """
    pts = _unique_ring(_polyline_points(outline, max_pts=64))
    n = len(pts)
    if n < 3 or not collar_rings:
        return None
    standoff = max(float(clearance), DEFAULT_CHANNEL_STANDOFF, 0.15)
    # Allow keep→collar length up to the real peel-frame gap (D013).
    max_ln = max(12.0, 8.0 * standoff)
    for p in pts:
        near = _sol_geom._nearest_on_rings(p.x(), p.y(), collar_rings)
        if near is not None and near[2] > 1e-9:
            max_ln = max(max_ln, near[2] * 1.2 + float(min_cut))
    best = None
    best_len = None

    def consider(ox, oy, dx, dy):
        """*ox,oy* on the keep outline; ray along unit *(dx,dy)* to collar."""
        nonlocal best, best_len
        probe = QPointF(ox + dx * _SEARCH_PROBE, oy + dy * _SEARCH_PROBE)
        if keep_fill is not None and keep_fill.contains(probe):
            return
        if container is not None and not container.contains(probe):
            return
        px = ox + dx * standoff
        py = oy + dy * standoff
        hit = _sol_geom._ray_intersect_rings(px, py, dx, dy, collar_rings)
        if hit is None:
            hit = _sol_geom._ray_intersect_rings(
                probe.x(), probe.y(), dx, dy, collar_rings)
        if hit is None:
            return
        seg = _waste_seg_or_none(
            ox, oy, hit[0], hit[1], keep_fill, work, 0.0,
            container=container)
        if seg is None:
            return
        ln = math.hypot(seg[2] - seg[0], seg[3] - seg[1])
        if ln < min_cut or ln > max_ln:
            return
        if best_len is None or ln < best_len - 1e-9:
            best_len = ln
            best = seg

    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        ex, ey = b.x() - a.x(), b.y() - a.y()
        eln = math.hypot(ex, ey)
        if eln < 1e-9:
            continue
        mx = 0.5 * (a.x() + b.x())
        my = 0.5 * (a.y() + b.y())
        dx, dy = _sol_geom._orient_outward(mx, my, -ey, ex, outline)
        consider(mx, my, dx, dy)

    if best is not None:
        return best
    for p in pts:
        near = _sol_geom._nearest_on_rings(p.x(), p.y(), collar_rings)
        if near is None or near[2] < 1e-9:
            continue
        dx, dy = (near[0] - p.x()) / near[2], (near[1] - p.y()) / near[2]
        consider(p.x(), p.y(), dx, dy)
    return best
