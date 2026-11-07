# -*- coding: utf-8 -*-
"""Bay and peninsula predicates."""
from __future__ import division

import math
from collections import namedtuple

from ..qt import QPointF
from ..keep import (
    _polyline_points,
    _signed_area,
    _unique_ring,
)

from .rules import (
    DEFAULT_DELICATE_ANGLE_DEG,
    DEFAULT_PENINSULA_RATIO,
)
from . import geom as _sol_geom


# Waste pockets: font-H ~0.85, t-open ~0.24. Keep tips stay a true spike.
_WASTE_PENINSULA_MIN_RATIO = DEFAULT_PENINSULA_RATIO
_KEEP_PENINSULA_MIN_RATIO = 1.0
# Legacy frontier metrics (ρ / tips); bay seal uses D007 κ (below).
_FRONTIER_RHO_MAX = 1.6
_FRONTIER_TIP_MIN = 3
# Hull-bay discovery floor. Old 4 mm / 3×standoff hid shallow jagged bays.
_BAY_DISCOVERY_MIN_DEPTH = 1.0
# D007 coastline closure: classify if κ ≥ min; seal if undercut or κ ≥ cut.
_KAPPA_MIN = 2.0
_KAPPA_CUT = 3.0

FrontierRunMetrics = namedtuple(
    'FrontierRunMetrics', ('rho', 'length', 'chord', 'tip_count'))


def _run_arc_length(pts):
    """Sum of segment lengths along a densified frontier run."""
    if not pts or len(pts) < 2:
        return 0.0
    total = 0.0
    for i in range(len(pts) - 1):
        x0, y0 = _sol_geom._pt_xy(pts[i])
        x1, y1 = _sol_geom._pt_xy(pts[i + 1])
        total += math.hypot(x1 - x0, y1 - y0)
    return total


def _run_chord_length(pts):
    """Straight-line distance first→last sample of a frontier run."""
    if not pts or len(pts) < 2:
        return 0.0
    x0, y0 = _sol_geom._pt_xy(pts[0])
    x1, y1 = _sol_geom._pt_xy(pts[-1])
    return math.hypot(x1 - x0, y1 - y0)


def _frontier_complexity(pts, eps=1e-9):
    """Frontier complexity ρ = L / max(C, ε). Empty/tiny → 1.0."""
    if not pts or len(pts) < 2:
        return 1.0
    length = _run_arc_length(pts)
    chord = _run_chord_length(pts)
    if length < eps and chord < eps:
        return 1.0
    return length / max(chord, eps)


def _frontier_tip_count(pts, angle_deg=None, waste_dir=None, eps=1e-12):
    """Count sharp tips on an open run whose exterior bisector faces waste.

    *waste_dir* is a preferred waste direction (default: left normal of the
    first→last chord). Tips reuse the turn threshold used for convex keep
    tips (DEFAULT_DELICATE_ANGLE_DEG).
    """
    if angle_deg is None:
        angle_deg = DEFAULT_DELICATE_ANGLE_DEG
    if not pts or len(pts) < 3:
        return 0
    if waste_dir is None:
        x0, y0 = _sol_geom._pt_xy(pts[0])
        x1, y1 = _sol_geom._pt_xy(pts[-1])
        cx, cy = x1 - x0, y1 - y0
        cl = math.hypot(cx, cy)
        if cl < eps:
            return 0
        # Left normal of chord (waste side of a L→R keep-below run).
        waste_dir = (-cy / cl, cx / cl)
    else:
        wx, wy = float(waste_dir[0]), float(waste_dir[1])
        wl = math.hypot(wx, wy)
        if wl < eps:
            return 0
        waste_dir = (wx / wl, wy / wl)
    wx, wy = waste_dir
    count = 0
    for i in range(1, len(pts) - 1):
        p0 = QPointF(*_sol_geom._pt_xy(pts[i - 1]))
        p1 = QPointF(*_sol_geom._pt_xy(pts[i]))
        p2 = QPointF(*_sol_geom._pt_xy(pts[i + 1]))
        turn = _sol_geom._angle_turn_deg(p0, p1, p2)
        if turn < angle_deg:
            continue
        v1x, v1y = p0.x() - p1.x(), p0.y() - p1.y()
        v2x, v2y = p2.x() - p1.x(), p2.y() - p1.y()
        n1 = math.hypot(v1x, v1y)
        n2 = math.hypot(v2x, v2y)
        if n1 < eps or n2 < eps:
            continue
        v1x, v1y = v1x / n1, v1y / n1
        v2x, v2y = v2x / n2, v2y / n2
        bx, by = v1x + v2x, v1y + v2y
        bn = math.hypot(bx, by)
        if bn < eps:
            # Straight reverse: exterior ≈ either side normal.
            bx, by = -v1y, v1x
            bn = 1.0
        # Exterior bisector points out of the wedge (into waste for a tip).
        ex, ey = -bx / bn, -by / bn
        if ex * wx + ey * wy <= 0.0:
            continue
        count += 1
    return count


def _frontier_run_metrics(pts, angle_deg=None, waste_dir=None, eps=1e-9):
    """ρ, L, chord, tip_count for a densified frontier run."""
    length = _run_arc_length(pts)
    chord = _run_chord_length(pts)
    rho = _frontier_complexity(pts, eps=eps)
    tips = _frontier_tip_count(
        pts, angle_deg=angle_deg, waste_dir=waste_dir, eps=eps)
    return FrontierRunMetrics(rho, length, chord, tips)


def _peninsula_is_deep(depth, mouth_w, ratio=_WASTE_PENINSULA_MIN_RATIO, eps=1e-6):
    """Deep when depth exceeds *ratio* of the mouth."""
    return float(depth) > float(ratio) * float(mouth_w) + eps


def _bay_coast_pts(left, right, run):
    """Mouth-left → coast samples → mouth-right as (x, y) pairs."""
    pts = []

    def add(p):
        if p is None:
            return
        xy = _sol_geom._pt_xy(p)
        if pts:
            px, py = pts[-1]
            if abs(xy[0] - px) < 1e-12 and abs(xy[1] - py) < 1e-12:
                return
        pts.append(xy)

    add(left)
    if run:
        for p in run:
            add(p)
    add(right)
    return pts


def _bay_coast_length(left, right, run):
    """L_coast along the keep↔waste frontier between mouth ends."""
    return _run_arc_length(_bay_coast_pts(left, right, run))


def _bay_mouth_width(left, right):
    """L_mouth = distance between mouth endpoints."""
    lx, ly = _sol_geom._pt_xy(left)
    rx, ry = _sol_geom._pt_xy(right)
    return math.hypot(rx - lx, ry - ly)


def _bay_kappa(left, right, run, mouth_w=None, eps=1e-9):
    """Closure κ = L_coast / L_mouth (D007)."""
    if mouth_w is None:
        mouth_w = _bay_mouth_width(left, right)
    mouth_w = float(mouth_w)
    if mouth_w < eps:
        return 0.0
    return _bay_coast_length(left, right, run) / mouth_w


def _approx_bay_kappa(depth, mouth_w, frontier_pts=None, eps=1e-9):
    """κ when only depth/mouth (and optional one-wall frontier) are known.

    Models an open multi-body bay as a U: two walls of *depth* plus a far
    chord ≈ mouth → κ = 2·depth/mouth + 1. A denser facing frontier may
    raise κ further.
    """
    mw = max(float(mouth_w), eps)
    kappa = 2.0 * float(depth) / mw + 1.0
    if frontier_pts and len(frontier_pts) >= 2:
        kappa = max(kappa, _run_arc_length(frontier_pts) / mw)
    return kappa


def _bay_has_undercut(left, right, deep, run, n_samples=12, eps=1e-6):
    """True if some water chord parallel to the mouth is longer than the mouth."""
    mouth_w = _bay_mouth_width(left, right)
    if mouth_w < eps:
        return False
    lx, ly = _sol_geom._pt_xy(left)
    rx, ry = _sol_geom._pt_xy(right)
    tx, ty = (rx - lx) / mouth_w, (ry - ly) / mouth_w
    mx, my = 0.5 * (lx + rx), 0.5 * (ly + ry)
    dpx, dpy = _sol_geom._pt_xy(deep)
    nx, ny = dpx - mx, dpy - my
    depth = math.hypot(nx, ny)
    if depth < eps:
        return False
    nx, ny = nx / depth, ny / depth
    coast = _bay_coast_pts(left, right, run)
    if len(coast) < 2:
        return False
    n_samples = max(int(n_samples), 3)
    for i in range(1, n_samples):
        t = depth * (i / float(n_samples))
        ox, oy = mx + nx * t, my + ny * t
        hits = []
        for j in range(len(coast) - 1):
            ax, ay = coast[j]
            bx, by = coast[j + 1]
            s = _sol_geom._line_line_s(ox, oy, tx, ty, ax, ay, bx, by)
            if s is not None:
                hits.append(s)
        if len(hits) < 2:
            continue
        hits.sort()
        span = hits[-1] - hits[0]
        if span > mouth_w + eps:
            return True
    return False


def _bay_should_seal(left, right, deep, run, depth=None, mouth_w=None,
                     ratio=_WASTE_PENINSULA_MIN_RATIO,
                     kappa_min=_KAPPA_MIN, kappa_cut=_KAPPA_CUT, eps=1e-9):
    """Seal a body bay mouth (D007): κ ≥ min and (undercut or κ ≥ cut or deep)."""
    if left is None or right is None:
        return False
    if mouth_w is None:
        mouth_w = _bay_mouth_width(left, right)
    mouth_w = float(mouth_w)
    if mouth_w < eps:
        return False
    if depth is None and deep is not None:
        depth = _sol_geom._point_seg_dist(
            _sol_geom._pt_xy(deep)[0], _sol_geom._pt_xy(deep)[1],
            _sol_geom._pt_xy(left)[0], _sol_geom._pt_xy(left)[1],
            _sol_geom._pt_xy(right)[0], _sol_geom._pt_xy(right)[1])
    depth = float(depth or 0.0)
    kappa = _bay_kappa(left, right, run, mouth_w=mouth_w, eps=eps)
    if kappa + eps < float(kappa_min):
        return False
    if kappa + eps >= float(kappa_cut):
        return True
    if deep is not None and _bay_has_undercut(left, right, deep, run):
        return True
    if _peninsula_is_deep(depth, mouth_w, ratio=ratio):
        return True
    return False


def _peninsula_should_detach(depth, mouth_w, frontier_pts,
                             ratio=_WASTE_PENINSULA_MIN_RATIO,
                             rho_max=_FRONTIER_RHO_MAX,
                             tip_min=_FRONTIER_TIP_MIN,
                             waste_dir=None,
                             left=None, right=None, deep=None,
                             kappa_min=_KAPPA_MIN, kappa_cut=_KAPPA_CUT):
    """Seal waste bay when D007 κ/undercut/depth gates fire.

    Full mouth geometry (*left*, *right*, *deep*, *frontier_pts* as coast)
    uses true κ. Callers with only depth/mouth use the U approx. *rho_max*
    / *tip_min* are accepted for API compat but no longer seal by themselves.
    """
    _ = rho_max, tip_min, waste_dir
    if left is not None and right is not None:
        return _bay_should_seal(
            left, right, deep, frontier_pts, depth=depth, mouth_w=mouth_w,
            ratio=ratio, kappa_min=kappa_min, kappa_cut=kappa_cut)
    kappa = _approx_bay_kappa(depth, mouth_w, frontier_pts)
    if kappa + 1e-9 < float(kappa_min):
        return False
    if kappa + 1e-9 >= float(kappa_cut):
        return True
    return _peninsula_is_deep(depth, mouth_w, ratio=ratio)


def _bay_waste_dir(left, right, deep):
    """Vector from the mouth midpoint toward the bay (into waste / water)."""
    wx = deep.x() - 0.5 * (left.x() + right.x())
    wy = deep.y() - 0.5 * (left.y() + right.y())
    if wx * wx + wy * wy <= 1e-18:
        return None
    return (wx, wy)


def _bay_min_depth(standoff):
    """Discovery floor so shallow complex bays are still candidates."""
    return max(_BAY_DISCOVERY_MIN_DEPTH, float(standoff))


def _vertex_is_concave(pts, i, ccw):
    n = len(pts)
    p0, p1, p2 = pts[(i - 1) % n], pts[i], pts[(i + 1) % n]
    ix, iy = p1.x() - p0.x(), p1.y() - p0.y()
    ox, oy = p2.x() - p1.x(), p2.y() - p1.y()
    cross = ix * oy - iy * ox
    if abs(cross) < 1e-12:
        return False
    is_convex = (cross > 0) == ccw
    return not is_convex


def _keep_peninsula_mouth(pts, i, ccw):
    """Base of a keep tip: first reflex vertex each side, else neighbors."""
    n = len(pts)
    left = right = None
    for k in range(1, n - 1):
        j = (i - k) % n
        if _vertex_is_concave(pts, j, ccw):
            left = pts[j]
            break
    for k in range(1, n - 1):
        j = (i + k) % n
        if _vertex_is_concave(pts, j, ccw):
            right = pts[j]
            break
    if left is None or right is None:
        left = pts[(i - 1) % n]
        right = pts[(i + 1) % n]
    return left, right


def _mouth_has_body_beyond(pa, pb, tip, outline):
    """True if keep continues past the mouth (a neck, not the whole body)."""
    mx = 0.5 * (pa.x() + pb.x())
    my = 0.5 * (pa.y() + pb.y())
    dx, dy = mx - tip.x(), my - tip.y()
    ln = math.hypot(dx, dy)
    if ln < 1e-9:
        return False
    ux, uy = dx / ln, dy / ln
    mouth_w = math.hypot(pb.x() - pa.x(), pb.y() - pa.y())
    step = max(0.75, 0.15 * mouth_w)
    return outline.contains(QPointF(mx + ux * step, my + uy * step))


def _deep_keep_peninsula_tips(outline, angle_deg):
    """Convex tips whose protrusion is deeper than the neck is wide."""
    tips = _sol_geom._convex_tips(outline, angle_deg)
    if not tips:
        return []
    pts = _unique_ring(_polyline_points(outline))
    if len(pts) < 3:
        return []
    ccw = _signed_area(pts) > 0
    out = []
    for tip in tips:
        i = _sol_geom._nearest_pt_index(pts, tip['pt'])
        pa, pb = _keep_peninsula_mouth(pts, i, ccw)
        mouth_w = math.hypot(pb.x() - pa.x(), pb.y() - pa.y())
        depth = _sol_geom._point_seg_dist(
            tip['pt'].x(), tip['pt'].y(), pa.x(), pa.y(), pb.x(), pb.y())
        if not _peninsula_is_deep(
                depth, mouth_w, ratio=_KEEP_PENINSULA_MIN_RATIO):
            continue
        if not _mouth_has_body_beyond(pa, pb, tip['pt'], outline):
            continue
        out.append(tip)
    return out


def _bay_chain(pts, i0, i1, hull_idx):
    """Outline walk from i0 to i1 that does not pass other hull vertices."""
    n = len(pts)
    if n < 2 or i0 == i1:
        return None
    others = set(hull_idx) - {i0, i1}

    def walk(step):
        chain = [pts[i0]]
        i = i0
        for _ in range(n):
            i = (i + step) % n
            if i in others:
                return None
            chain.append(pts[i])
            if i == i1:
                return chain
        return None

    a, b = walk(1), walk(-1)
    if a and b:
        return a if len(a) <= len(b) else b
    return a or b


def _hull_bay_mouths(body, min_depth, min_width):
    """Mouths of concave bays: hull edges the outline dents away from."""
    pts = _unique_ring(_polyline_points(body, max_pts=256))
    pts = _sol_geom._densify_ring(pts, max_edge=8.0)
    if len(pts) < 4:
        return []
    hull = _sol_geom._convex_hull(pts)
    if len(hull) < 3:
        return []
    hull_idx = [_sol_geom._nearest_pt_index(pts, h) for h in hull]
    if len(set(hull_idx)) < 3:
        return []
    mouths = []
    n_h = len(hull)
    on_tol = 0.6
    for k in range(n_h):
        i0, i1 = hull_idx[k], hull_idx[(k + 1) % n_h]
        ha, hb = pts[i0], pts[i1]
        chain = _bay_chain(pts, i0, i1, hull_idx)
        if chain is None or len(chain) < 3:
            continue
        mouth_w = math.hypot(hb.x() - ha.x(), hb.y() - ha.y())
        if mouth_w < min_width:
            continue
        depths = [
            _sol_geom._point_seg_dist(p.x(), p.y(), ha.x(), ha.y(), hb.x(), hb.y())
            for p in chain
        ]
        max_d = max(depths)
        if max_d < min_depth:
            continue
        on_edge = [
            _sol_geom._point_seg_dist(p.x(), p.y(), ha.x(), ha.y(), hb.x(), hb.y())
            <= on_tol
            for p in chain
        ]
        i = 0
        n_c = len(chain)
        while i < n_c:
            if on_edge[i]:
                i += 1
                continue
            left = chain[i - 1] if i > 0 else chain[0]
            j = i
            while j < n_c and not on_edge[j]:
                j += 1
            right = chain[j] if j < n_c else chain[-1]
            run_d = max(depths[i:j]) if j > i else 0.0
            span = math.hypot(right.x() - left.x(), right.y() - left.y())
            if run_d >= min_depth and span >= min_width:
                deep = chain[i + depths[i:j].index(run_d)]
                # Off-edge walk only: mouth endpoints would inflate ρ on a U.
                mouths.append((left, right, deep, chain[i:j]))
            i = j
    return mouths


def _has_independent_waste_bays(body, tips, standoff, min_cut,
                                peninsula_ratio=None):
    """Bays that seal under D007 and are not valleys between keep tips."""
    min_width = 2.0 * float(standoff) + float(min_cut)
    min_depth = _bay_min_depth(standoff)
    ratio = (DEFAULT_PENINSULA_RATIO if peninsula_ratio is None
             else float(peninsula_ratio))
    for left, right, deep, run in _hull_bay_mouths(body, min_depth, min_width):
        mouth_w = math.hypot(right.x() - left.x(), right.y() - left.y())
        depth = _sol_geom._point_seg_dist(
            deep.x(), deep.y(), left.x(), left.y(), right.x(), right.y())
        if not _bay_should_seal(
                left, right, deep, run, depth=depth, mouth_w=mouth_w,
                ratio=ratio):
            continue
        # Fixed tol: large mouths must not treat nearby coast teeth as valley tips.
        if _mouth_between_keep_tips(left, right, tips, tol=2.0):
            continue
        return True
    return False


def _mouth_between_keep_tips(pa, pb, tips, tol=2.0):
    """True when both mouth ends sit on keep-peninsula tips (a star valley)."""
    if not tips:
        return False

    def near(p):
        for tip in tips:
            q = tip['pt'] if isinstance(tip, dict) else tip
            if math.hypot(p.x() - q.x(), p.y() - q.y()) <= tol:
                return True
        return False

    return near(pa) and near(pb)
