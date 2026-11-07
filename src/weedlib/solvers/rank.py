# -*- coding: utf-8 -*-
"""Ranks candidate seals."""
from __future__ import division

import math

from .. import debug as _wdbg
from ..qt import QPointF

from .rules import (
    _EP_CORNER,
    _EP_EDGE,
    _EP_FRAME,
)
from . import geom as _sol_geom
from . import peel as _sol_peel


# Prefer this created-min after a harder coast search; below is α≈40 junk.
_CREATED_PREFER = 55.0
# Mouth joins: drop mediocre created-min when a square-ish cand exists.
_CREATED_MOUTH_PREFER = 70.0


def _alpha_min_at_anchors(pa, pb, path_a, path_b):
    """Min created peel angle at anchors *pa*/*pb*, or None if unmeasurable."""
    if pa is None or pb is None or path_a is None or path_b is None:
        return None
    dx = pb.x() - pa.x()
    dy = pb.y() - pa.y()
    ln = math.hypot(dx, dy)
    if ln < 1e-12:
        return None
    ux, uy = dx / ln, dy / ln
    a0 = _created_peel_angles(pa, (ux, uy), path_a)
    a1 = _created_peel_angles(pb, (-ux, -uy), path_b)
    if a0 is None or a1 is None:
        return None
    return min(min(a0), min(a1))


# Endpoint must sit on the vertex — not 0.5–1.5 mm down the edge (mouth-seal
# slides used to steal class-0 that way and beat true corner–corner ranks).
_CORNER_HIT_TOL = 0.35


def _near_waste_reflex_corner(path, p, tol=None, min_turn=40):
    """True if *p* sits on a >180° weed-side (convex keep) corner."""
    if path is None or p is None:
        return False
    tt = _CORNER_HIT_TOL if tol is None else float(tol)
    for c in _sol_geom._convex_corners(path, min_turn=min_turn):
        if math.hypot(c.x() - p.x(), c.y() - p.y()) <= tt:
            return True
    return False


def _measure_alpha_at(p, w_hat, path):
    """Included α at *p*; snap to the true corner vertex when near one."""
    if p is None or path is None or w_hat is None:
        return None
    frame = _sol_geom._keep_frame_at(path, p)
    if frame is not None and frame.vertex is not None:
        return _sol_geom._included_angle_deg(frame.vertex, w_hat, path)
    return _sol_geom._included_angle_deg(p, w_hat, path)


def _created_peel_angles(p, w_hat, path):
    """Water-side peel angles the cut creates at *p*, or None.

    Mid-edge: (α, 180−α) with included α in 0–90 (0 = graze). Vertex: the
    two 0–180° angles from ŵ to the incident keep tangents. A wall
    continuation is ~180° vs that edge, not 0°.
    """
    if p is None or path is None or w_hat is None:
        return None
    frame = _sol_geom._keep_frame_at(path, p)
    if frame is None or frame.t0 is None:
        return None
    wx, wy = float(w_hat[0]), float(w_hat[1])
    wn = math.hypot(wx, wy)
    if wn < 1e-12:
        return None
    wx, wy = wx / wn, wy / wn

    def ang180(t):
        if t is None:
            return None
        dot = max(-1.0, min(1.0, wx * t[0] + wy * t[1]))
        return math.degrees(math.acos(dot))

    if frame.vertex is None:
        a = ang180(frame.t0)
        if a is None:
            return None
        inc = min(a, 180.0 - a)
        return (inc, 180.0 - inc)
    a0 = ang180(frame.t0)
    a1 = ang180(frame.t1)
    if a0 is None or a1 is None:
        return None
    return (a0, a1)


def _seg_end_dirs(seg):
    x0, y0, x1, y1 = seg
    dx, dy = x1 - x0, y1 - y0
    ln = math.hypot(dx, dy)
    if ln < 1e-12:
        return None
    ux, uy = dx / ln, dy / ln
    return (
        (QPointF(x0, y0), (ux, uy)),
        (QPointF(x1, y1), (-ux, -uy)),
    )


def _endpoint_class(p, keep_path, peel_frame=None, path_b=None):
    """0 = >180° weed-side corner, 1 = peel-frame, 2 = design edge."""
    if _near_waste_reflex_corner(keep_path, p):
        return _EP_CORNER
    if path_b is not None and _near_waste_reflex_corner(path_b, p):
        return _EP_CORNER
    # On design coast: not a frame landing even if a rail nicks the same point.
    if _sol_geom._point_near_path(p.x(), p.y(), keep_path, tol=2.0):
        return _EP_EDGE
    if path_b is not None and _sol_geom._point_near_path(p.x(), p.y(), path_b, tol=2.0):
        return _EP_EDGE
    if peel_frame is not None and not peel_frame.isEmpty():
        if _sol_geom._point_near_path(p.x(), p.y(), peel_frame, tol=2.0):
            return _EP_FRAME
    return _EP_EDGE


def _seg_both_class0(seg, keep_path, peel_frame=None, path_b=None):
    """True if both ends are >180° weed-side (convex keep) corners."""
    ends = _seg_end_dirs(seg)
    if ends is None:
        return False
    (p0, _w0), (p1, _w1) = ends
    pb = path_b if path_b is not None else keep_path
    return (
        _endpoint_class(p0, keep_path, peel_frame, path_b=pb) == _EP_CORNER
        and _endpoint_class(p1, keep_path, peel_frame, path_b=pb) == _EP_CORNER)


def _created_angle_error(p, w_hat, keep_path, peel_frame=None):
    """Distance of the worst created peel angle from 180°. Unknown → 90.

    Included α is small on a graze and ~90° on a square landing. E is
    180 − min(created) so shallow grazes lose to nearer-180° / square.
    """
    angles = _created_peel_angles(p, w_hat, keep_path)
    if angles is None and peel_frame is not None:
        angles = _created_peel_angles(p, w_hat, peel_frame)
    if angles is None:
        return 90.0
    return 180.0 - min(angles)


def _seg_min_created(seg, keep_path, peel_frame=None):
    """Smallest created peel angle at either landing, or None."""
    ends = _seg_end_dirs(seg)
    if ends is None:
        return None
    worst = None
    for p, w_hat in ends:
        angles = _created_peel_angles(p, w_hat, keep_path)
        if angles is None and peel_frame is not None:
            angles = _created_peel_angles(p, w_hat, peel_frame)
        if angles is None:
            continue
        m = min(angles)
        if worst is None or m < worst:
            worst = m
    return worst


def _pick_quality_seg(cands, keep_path, path_b=None, peel_frame=None,
                      prefer=None):
    """Ranked pick; prefer created-min ≥ *prefer* when any candidate has it."""
    if not cands:
        return None
    floor = _CREATED_PREFER if prefer is None else float(prefer)
    good = []
    for seg in cands:
        if seg is None:
            continue
        mc = _seg_min_created(seg, keep_path, peel_frame)
        if mc is not None and mc + 1e-9 >= floor:
            good.append(seg)
    pool = good if good else list(cands)
    return _pick_ranked_seg(pool, keep_path, path_b, peel_frame)


def _peel_rank_cost(seg, keep_path, path_b=None, peel_frame=None):
    """cost ≈ E√L; E is sum of |created peel − 180°| at both ends."""
    ends = _seg_end_dirs(seg)
    if ends is None:
        return float('inf')
    (p0, w0), (p1, w1) = ends
    pb = path_b if path_b is not None else keep_path
    e0 = _created_angle_error(p0, w0, keep_path, peel_frame)
    e1 = _created_angle_error(p1, w1, pb, peel_frame)
    x0, y0, x1, y1 = seg
    ln = math.hypot(x1 - x0, y1 - y0)
    return (e0 + e1) * math.sqrt(max(ln, 1e-9))


def _corner_miss_penalty(seg, keep_path, path_b=None):
    """Sum of distances from ends to nearest convex corners (tie-break)."""
    ends = _seg_end_dirs(seg)
    if ends is None:
        return 0.0
    paths = [keep_path]
    if path_b is not None and path_b is not keep_path:
        paths.append(path_b)
    total = 0.0
    for p, _w in ends:
        best = None
        for path in paths:
            if path is None or path.isEmpty():
                continue
            for c in _sol_geom._convex_corners(path, min_turn=40):
                d = math.hypot(c.x() - p.x(), c.y() - p.y())
                if best is None or d < best:
                    best = d
        total += 0.0 if best is None else best
    return total


def _peel_rank_key(seg, keep_path, path_b=None, peel_frame=None):
    """(class pair, cost, corner miss) — lower is better."""
    ends = _seg_end_dirs(seg)
    if ends is None:
        return ((_EP_EDGE, _EP_EDGE), float('inf'), float('inf'))
    (p0, _w0), (p1, _w1) = ends
    pb = path_b if path_b is not None else keep_path
    c0 = _endpoint_class(p0, keep_path, peel_frame, path_b=pb)
    c1 = _endpoint_class(p1, keep_path, peel_frame, path_b=pb)
    klass = (min(c0, c1), max(c0, c1))
    return (
        klass,
        _peel_rank_cost(seg, keep_path, pb, peel_frame),
        _corner_miss_penalty(seg, keep_path, pb),
    )


def _pick_ranked_seg(cands, keep_path, path_b=None, peel_frame=None,
                     prefer=None):
    """Lowest D012 rank among *cands*; *prefer* is a same-class created-min."""
    scored = []
    for seg in cands:
        if seg is None:
            continue
        klass, cost, miss = _peel_rank_key(seg, keep_path, path_b, peel_frame)
        mc = _seg_min_created(seg, keep_path, peel_frame)
        scored.append((klass, cost, miss, mc, seg))
    if not scored:
        return None
    best_klass = min(s[0] for s in scored)
    same = [s for s in scored if s[0] == best_klass]
    if prefer is not None:
        floor = float(prefer)
        good = [s for s in same if s[3] is not None and s[3] + 1e-9 >= floor]
        if good:
            same = good
    winner = min(same, key=lambda s: (s[1], s[2]))
    if _wdbg.enabled():
        # Corner vs edge preference is a hard ranking rule; log the pool.
        corner_pool = [
            s for s in scored if s[0][0] == _EP_CORNER or s[0][1] == _EP_CORNER]
        top = sorted(scored, key=lambda s: (s[0], s[1], s[2]))[:5]
        _wdbg.log(
            'rank.pick', n=len(scored),
            winner_class=(_wdbg.ep_name(winner[0][0]),
                          _wdbg.ep_name(winner[0][1])),
            winner_cost=winner[1], winner_miss=winner[2],
            winner_created=winner[3], winner=winner[4],
            corner_cands=len(corner_pool),
            top=[
                '%s/%s c=%.1f m=%.2f %s' % (
                    _wdbg.ep_name(s[0][0]), _wdbg.ep_name(s[0][1]),
                    s[1], s[2], _wdbg.seg_fmt(s[4]))
                for s in top])
        if (winner[0][0] != _EP_CORNER and winner[0][1] != _EP_CORNER
                and corner_pool):
            best_corner = min(corner_pool, key=lambda s: (s[0], s[1], s[2]))
            _wdbg.log(
                'rank.corner_available_but_lost',
                winner_class=(_wdbg.ep_name(winner[0][0]),
                              _wdbg.ep_name(winner[0][1])),
                corner_class=(_wdbg.ep_name(best_corner[0][0]),
                              _wdbg.ep_name(best_corner[0][1])),
                corner_cost=best_corner[1], corner=best_corner[4],
                winner=winner[4])
    return winner[4]


# C9 G2: edge-lift + peel ranking (α_hard still wins).
_ALPHA_SOFT = 35.0
_PEEL_ALIGN_E = 25.0
_PEEL_ALIGN_C = 35.0
_CUT_PERP_E = 65.0
_R_SNAP = 1.5
_C_CORNER_MISS = 0.4
_E_SOFT_HUGE = 8.0


def _edge_lift_E(p, w_hat, path, peel_hat, d_corner, r_snap=None,
                 body_len=None):
    """True when a mid-edge seal dams peel along a peel-aligned keep edge."""
    rs = _R_SNAP if r_snap is None else float(r_snap)
    if p is None or w_hat is None or peel_hat is None or path is None:
        return False
    if float(d_corner) <= rs:
        return False
    # Near a body end along ĉ — not mid-stick.
    if body_len is not None and float(body_len) > 1e-6:
        if float(d_corner) <= 0.2 * float(body_len):
            return False
    frame = _sol_geom._keep_frame_at(path, p)
    t = _sol_peel._keep_tangent_for_peel(frame, peel_hat)
    if t is None:
        return False
    px, py = float(peel_hat[0]), float(peel_hat[1])
    pl = math.hypot(px, py)
    if pl < 1e-12:
        return False
    px, py = px / pl, py / pl
    if abs(t[0] * px + t[1] * py) < math.cos(math.radians(_PEEL_ALIGN_E)):
        return False
    wx, wy = float(w_hat[0]), float(w_hat[1])
    wn = math.hypot(wx, wy)
    if wn < 1e-12:
        return False
    wx, wy = wx / wn, wy / wn
    if abs(wx * px + wy * py) > math.cos(math.radians(_CUT_PERP_E)):
        return False
    return True


def _c_alpha(amin):
    if amin is None:
        return 0.0
    return (max(0.0, _ALPHA_SOFT - float(amin)) / _ALPHA_SOFT) ** 2


def _c_peel(p, w_hat, path, peel_hat, d_corner, gap_w):
    """Soft peel cost; 0 when keep edge is not peel-aligned."""
    if p is None or w_hat is None or peel_hat is None or path is None:
        return 0.0
    frame = _sol_geom._keep_frame_at(path, p)
    t = _sol_peel._keep_tangent_for_peel(frame, peel_hat)
    if t is None:
        return 0.0
    px, py = float(peel_hat[0]), float(peel_hat[1])
    pl = math.hypot(px, py)
    if pl < 1e-12:
        return 0.0
    px, py = px / pl, py / pl
    if abs(t[0] * px + t[1] * py) < math.cos(math.radians(_PEEL_ALIGN_C)):
        return 0.0
    wx, wy = float(w_hat[0]), float(w_hat[1])
    wn = math.hypot(wx, wy)
    if wn < 1e-12:
        return 0.0
    wx, wy = wx / wn, wy / wn
    dot = max(-1.0, min(1.0, px * wx + py * wy))
    psi = math.degrees(math.acos(dot))
    return (psi / 90.0) ** 2 * (
        1.0 + float(d_corner) / max(float(gap_w), 1.0))


def _c_corner(d_corner, r_snap=None):
    rs = _R_SNAP if r_snap is None else float(r_snap)
    return 0.0 if float(d_corner) <= rs else _C_CORNER_MISS


def _peel_straight_J(pa, pb, path_a, path_b, peel_hat, gap_w, corners_a,
                     corners_b, has_legal_corner, mouth_mid=None,
                     d_cap=None, body_len_a=None, body_len_b=None):
    """Peel J for an α-legal straight; None if E-hard rejected."""
    if pa is None or pb is None or peel_hat is None:
        return None
    dx = pb.x() - pa.x()
    dy = pb.y() - pa.y()
    ln = math.hypot(dx, dy)
    if ln < 1e-12:
        return None
    w_a = (dx / ln, dy / ln)
    w_b = (-dx / ln, -dy / ln)
    # Cap when a body has no hunt corners (smooth O) so J stays finite.
    cap = max(float(gap_w), 8.0) if d_cap is None else float(d_cap)
    if corners_a:
        d_a = min(_sol_peel._dist_to_points(pa, corners_a, default=cap), cap * 4.0)
    else:
        d_a = cap
    if corners_b:
        d_b = min(_sol_peel._dist_to_points(pb, corners_b, default=cap), cap * 4.0)
    else:
        d_b = cap
    e_a = _edge_lift_E(
        pa, w_a, path_a, peel_hat, d_a, body_len=body_len_a)
    e_b = _edge_lift_E(
        pb, w_b, path_b, peel_hat, d_b, body_len=body_len_b)
    # Hard E only when that body has a lift target (outside-core corner).
    if (e_a and corners_a and has_legal_corner) or (
            e_b and corners_b and has_legal_corner):
        return None
    amin = _alpha_min_at_anchors(pa, pb, path_a, path_b)
    cp = max(
        _c_peel(pa, w_a, path_a, peel_hat, d_a, gap_w),
        _c_peel(pb, w_b, path_b, peel_hat, d_b, gap_w))
    cc_a = _c_corner(d_a) if corners_a else 0.0
    cc_b = _c_corner(d_b) if corners_b else 0.0
    cc = max(cc_a, cc_b) if (corners_a or corners_b) else 0.0
    j = 3.0 * _c_alpha(amin) + 1.5 * cp + cc
    j += 0.4 * ln / max(float(gap_w), 1.0)
    if ((e_a and corners_a) or (e_b and corners_b)) and not has_legal_corner:
        j += _E_SOFT_HUGE
    if mouth_mid is not None:
        mx = 0.5 * (pa.x() + pb.x()) - mouth_mid.x()
        my = 0.5 * (pa.y() + pb.y()) - mouth_mid.y()
        j += 0.15 * math.hypot(mx, my)
    return j
