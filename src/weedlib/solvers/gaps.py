# -*- coding: utf-8 -*-
"""The gap between two keep bodies."""
from __future__ import division

import math

from ..qt import QPointF, QRectF

from .rank import _CREATED_MOUTH_PREFER
from .ties import _MIN_COMPACT_TIES
from . import channels as _sol_channels
from . import cluster_bays as _sol_cluster_bays
from . import geom as _sol_geom
from . import peel as _sol_peel
from . import rank as _sol_rank
from . import rules as _sol_rules
from . import ties as _sol_ties


def _pair_spanning_segs(path, path_a, path_b, tol=2.5):
    """Weed segments in *path* that already bridge *path_a* to *path_b*."""
    out = []
    if path is None or path.isEmpty() or path_a is None or path_b is None:
        return out
    for seg in _sol_geom._iter_line_segs(path):
        if _seg_spans_pair(seg, path_a, path_b, tol=tol):
            out.append(seg)
    return out


def _pair_has_spanning_seal(path, path_a, path_b, tol=2.5):
    """True if *path* already has a keep-to-keep seal across this pair."""
    return bool(_pair_spanning_segs(path, path_a, path_b, tol=tol))


def _pair_related_spanning_segs(path, path_a, path_b, cluster=None, tol=2.5):
    """Seals across *path_a*–*path_b*, or either body to the other's satellite.

    A bang-dot pocket on K covers the same alley as a K–! frame neck; treat
    it as an existing join when deciding whether another seal is needed.
    """
    from . import cluster as _sol_cluster
    segs = list(_pair_spanning_segs(path, path_a, path_b, tol=tol))
    if not cluster:
        return segs
    seen = set(segs)
    for body, other in ((path_a, path_b), (path_b, path_a)):
        for sat in cluster:
            if sat is body or sat is other or sat is None or sat.isEmpty():
                continue
            if not _sol_cluster._is_stacked_satellite(sat, other):
                continue
            for seg in _pair_spanning_segs(path, body, sat, tol=tol):
                if seg not in seen:
                    seen.add(seg)
                    segs.append(seg)
    return segs


def _seal_midpoint(seg):
    return (0.5 * (seg[0] + seg[2]), 0.5 * (seg[1] + seg[3]))


def _mouth_near_spanning_seals(path, path_a, path_b, mouth, tol=None,
                               cluster=None):
    """True if an existing pair-spanning seal sits near *mouth*.

    Default *tol* scales with gap width and facing length so a mid-frame
    seal is dropped when a bay/corridor seal already necks the same alley
    (K–! mid cut next to a bottom bay), while a far open-end mouth on a
    tall stem pair (top fuse, bottom wrap) still seals.
    """
    from . import corridors as _sol_corridors
    if mouth is None:
        return False
    mx = _sol_cluster_bays._gap_mouth_mid_x(mouth)
    my = _sol_cluster_bays._gap_mouth_mid_y(mouth)
    if tol is None:
        facing = _sol_corridors._corridor_facing(path_a, path_b)
        if facing is not None:
            width = float(facing[3])
            overlap = float(facing[0])
        else:
            width = float(mouth[2])
            overlap = 0.0
        tol = max(6.0, 1.25 * max(width, 1e-6), 0.45 * overlap)
    for seg in _pair_related_spanning_segs(
            path, path_a, path_b, cluster=cluster):
        sx, sy = _seal_midpoint(seg)
        if math.hypot(sx - mx, sy - my) <= tol:
            return True
    return False


def _pair_join_already_effective(path, path_a, path_b, cluster, tol=2.5):
    """True if a second *same-site* seal across this gap would be redundant.

    Direct keep-to-keep on the pair counts (leftover gutters). Stacked
    satellite whose host is already sealed to the neighbor also counts
    (speck→neighbor is a duplicate of the host alley). Callers that seal a
    *specific mouth* (cluster bay / frame open end) should not use this to
    block a far open-side mouth — use ``_mouth_near_spanning_seals`` so a
    top fuse can still get a bottom wrap seal.
    """
    from . import cluster as _sol_cluster
    if _pair_has_spanning_seal(path, path_a, path_b, tol=tol):
        return True
    if not cluster:
        return False
    for body, other in ((path_a, path_b), (path_b, path_a)):
        for host in cluster:
            if host is body or host is other or host is None or host.isEmpty():
                continue
            if not _sol_cluster._is_stacked_satellite(body, host):
                continue
            if _pair_has_spanning_seal(path, host, other, tol=tol):
                return True
    return False


def _satellite_neighbor_already_sealed(path, path_a, path_b, cluster, tol=2.5):
    """True if a stacked speck's host is already sealed to the neighbor nearby.

    Only treat the host alley seal as covering the speck when that seal sits
    within the speck's band along the alley (plus a small margin). A top
    host→neighbor fuse must not suppress a bottom bang-dot pocket.
    """
    from . import cluster as _sol_cluster
    if not cluster:
        return False
    for body, other in ((path_a, path_b), (path_b, path_a)):
        for host in cluster:
            if host is body or host is other or host is None or host.isEmpty():
                continue
            if not _sol_cluster._is_stacked_satellite(body, host):
                continue
            segs = _pair_spanning_segs(path, host, other, tol=tol)
            if not segs:
                continue
            br = body.boundingRect()
            # Alley axis from host→other; project speck and seals.
            ax, ay = _dominant_gap_axis(host, other)
            tx, ty = -ay, ax
            lo = min(br.left() * tx + br.top() * ty,
                     br.left() * tx + br.bottom() * ty,
                     br.right() * tx + br.top() * ty,
                     br.right() * tx + br.bottom() * ty)
            hi = max(br.left() * tx + br.top() * ty,
                     br.left() * tx + br.bottom() * ty,
                     br.right() * tx + br.top() * ty,
                     br.right() * tx + br.bottom() * ty)
            margin = max(4.0, 0.5 * (hi - lo))
            for seg in segs:
                sx, sy = _seal_midpoint(seg)
                t = sx * tx + sy * ty
                if lo - margin <= t <= hi + margin:
                    return True
    return False


def _pullback_for_gap(ln, standoff, min_cut):
    """Standoff and leftover-cut floor that still fit *ln*."""
    standoff = float(standoff)
    min_cut = float(min_cut)
    if ln >= 2.0 * standoff + min_cut:
        return standoff, min_cut
    remain = max(0.8, min(min_cut, 0.5 * ln))
    if ln < remain + 0.3:
        return None, None
    pull = min(standoff, 0.5 * (ln - remain))
    leftover = ln - 2.0 * pull
    return pull, min(min_cut, leftover)


def _bridge_seg(pa, pb, standoff, keep_fill, work, min_cut, container):
    """Segment between two keep outlines, both ends pulled back."""
    dx, dy = pb.x() - pa.x(), pb.y() - pa.y()
    ln = math.hypot(dx, dy)
    if ln < 1e-9:
        return None
    pull, floor = _pullback_for_gap(ln, standoff, min_cut)
    if pull is None:
        return None
    ux, uy = dx / ln, dy / ln
    while pull >= 0.0:
        x0 = pa.x() + ux * pull
        y0 = pa.y() + uy * pull
        x1 = pb.x() - ux * pull
        y1 = pb.y() - uy * pull
        leftover = math.hypot(x1 - x0, y1 - y0)
        use_floor = min(floor, leftover)
        seg = _sol_channels._waste_seg_or_none(
            x0, y0, x1, y1, keep_fill, work, use_floor, container=container)
        if seg is not None:
            return seg
        if pull < 0.25:
            break
        pull *= 0.5
    return None


def _dominant_gap_axis(path_a, path_b):
    """Unit axis across the waste between two islands (side-by-side → ±X)."""
    ra, rb = path_a.boundingRect(), path_b.boundingRect()
    dx = rb.center().x() - ra.center().x()
    dy = rb.center().y() - ra.center().y()
    x_ov = min(ra.right(), rb.right()) - max(ra.left(), rb.left())
    y_ov = min(ra.bottom(), rb.bottom()) - max(ra.top(), rb.top())
    if y_ov >= x_ov:
        return (1.0 if dx >= 0 else -1.0), 0.0
    return 0.0, (1.0 if dy >= 0 else -1.0)


def _facing_along_range(path_a, path_b, c_hat):
    """(lo, hi) of facing AABB overlap projected onto ĉ."""
    if path_a is None or path_b is None or c_hat is None:
        return None
    ra, rb = path_a.boundingRect(), path_b.boundingRect()
    cx, cy = float(c_hat[0]), float(c_hat[1])
    if abs(cy) >= abs(cx):
        y0 = max(ra.top(), rb.top())
        y1 = min(ra.bottom(), rb.bottom())
        if y1 < y0:
            return None
        a0, a1 = y0 * cy, y1 * cy
    else:
        x0 = max(ra.left(), rb.left())
        x1 = min(ra.right(), rb.right())
        if x1 < x0:
            return None
        a0, a1 = x0 * cx, x1 * cx
    return (min(a0, a1), max(a0, a1))


def _alley_facing_corners(path, other, c_hat, along_lo, along_hi, r_hunt,
                          mouth=None):
    """Convex corners on the alley face within overlap ± R_hunt (mouth-local)."""
    if path is None or other is None or c_hat is None:
        return []
    cx, cy = float(c_hat[0]), float(c_hat[1])
    lo = float(along_lo) - float(r_hunt)
    hi = float(along_hi) + float(r_hunt)
    pc = path.boundingRect().center()
    oc = other.boundingRect().center()
    dx, dy = oc.x() - pc.x(), oc.y() - pc.y()
    mouth_along = None
    if mouth is not None:
        mouth_along = mouth.x() * cx + mouth.y() * cy
    out = []
    for c in _sol_geom._convex_corners(path, min_turn=40):
        along = c.x() * cx + c.y() * cy
        if along < lo or along > hi:
            continue
        if (c.x() - pc.x()) * dx + (c.y() - pc.y()) * dy <= 0.0:
            continue
        if mouth_along is not None:
            if abs(along - mouth_along) > float(r_hunt) + 1e-9:
                if math.hypot(c.x() - mouth.x(), c.y() - mouth.y()) > float(
                        r_hunt):
                    continue
        out.append(QPointF(c))
    return out


def _body_along_extent(path, c_hat):
    """(lo, hi) of *path* AABB projected onto ĉ."""
    if path is None or path.isEmpty() or c_hat is None:
        return None
    r = path.boundingRect()
    cx, cy = float(c_hat[0]), float(c_hat[1])
    corners = (
        (r.left(), r.top()), (r.right(), r.top()),
        (r.left(), r.bottom()), (r.right(), r.bottom()))
    vals = [x * cx + y * cy for x, y in corners]
    return (min(vals), max(vals))


def _core_along_span(core, c_hat):
    """(lo, hi) of thin-core mouths on ĉ, or None."""
    if core is None or c_hat is None:
        return None
    cx, cy = float(c_hat[0]), float(c_hat[1])
    pts = (core.pa0, core.pb0, core.pa1, core.pb1)
    vals = [p.x() * cx + p.y() * cy for p in pts]
    return (min(vals), max(vals))


def _facing_end_mouths(path_a, path_b):
    """First/last near outline pairs along the facing band (AABB fallback)."""
    pairs = _sol_geom._outline_pairs(path_a, path_b)
    if not pairs:
        return []
    dmin = pairs[0][2]
    slack = max(2.0, 0.25 * dmin)
    facing = [(pa, pb, d) for pa, pb, d in pairs if d <= dmin + slack]
    if not facing:
        return []
    ux, uy = _dominant_gap_axis(path_a, path_b)
    tx, ty = -uy, ux

    def along(pa, pb):
        mx = 0.5 * (pa.x() + pb.x())
        my = 0.5 * (pa.y() + pb.y())
        return mx * tx + my * ty

    facing.sort(key=lambda t: along(t[0], t[1]))
    first, last = facing[0], facing[-1]
    span = abs(along(last[0], last[1]) - along(first[0], first[1]))
    if span < max(3.0, 0.5 * dmin):
        return [first]
    return [first, last]


def _gap_mouths(path_a, path_b, cluster=None):
    """Keep-point pairs at each end of the channel core (else facing ends).

    When *cluster* is given, each side is expanded with stacked satellites
    so an i-dot above a stem extends the alley mouth to the dot (H→dot
    rather than H→top-of-stem only).
    """
    from . import cluster as _sol_cluster, corridors as _sol_corridors
    a_use = _sol_cluster._with_stacked_satellites(path_a, cluster) if cluster else path_a
    b_use = _sol_cluster._with_stacked_satellites(path_b, cluster) if cluster else path_b
    # Prefer facing ends on the expanded outlines when satellites grew the
    # island beyond the thin core (core would still stop at the stem top).
    expanded = (a_use is not path_a) or (b_use is not path_b)
    if expanded:
        faces = _facing_end_mouths(a_use, b_use)
        if faces:
            return faces
    core = _sol_corridors._channel_core(a_use, b_use)
    if core is None and expanded:
        core = _sol_corridors._channel_core(path_a, path_b)
    if core is not None:
        d0 = math.hypot(
            core.pa0.x() - core.pb0.x(), core.pa0.y() - core.pb0.y())
        d1 = math.hypot(
            core.pa1.x() - core.pb1.x(), core.pa1.y() - core.pb1.y())
        return [(core.pa0, core.pb0, d0), (core.pa1, core.pb1, d1)]
    return _facing_end_mouths(a_use, b_use)


def _axis_hit_pair(pa, pb, ux, uy, path_a, path_b, max_t=32.0):
    """Rebuild pa–pb along the gap axis so the seal meets keep square-on."""
    rings_a = _sol_geom._path_to_rings(path_a)
    rings_b = _sol_geom._path_to_rings(path_b)
    if not rings_a or not rings_b:
        return pa, pb
    best = None
    best_ln = None

    def consider(qa, qb):
        nonlocal best, best_ln
        ln = math.hypot(qb.x() - qa.x(), qb.y() - qa.y())
        if ln < 1e-6 or ln > max_t:
            return
        if best_ln is None or ln < best_ln:
            best_ln = ln
            best = (qa, qb)

    for sgn in (1.0, -1.0):
        hit = _sol_geom._ray_intersect_rings(
            pa.x(), pa.y(), sgn * ux, sgn * uy, rings_b, max_t=max_t)
        if hit is not None:
            consider(QPointF(pa.x(), pa.y()), QPointF(hit[0], hit[1]))
    for sgn in (1.0, -1.0):
        hit = _sol_geom._ray_intersect_rings(
            pb.x(), pb.y(), sgn * ux, sgn * uy, rings_a, max_t=max_t)
        if hit is not None:
            consider(QPointF(hit[0], hit[1]), QPointF(pb.x(), pb.y()))
    return best if best is not None else (pa, pb)


def _gap_aabb(path_a, path_b):
    """AABB of the waste corridor between two islands, or None."""
    if path_a is None or path_b is None:
        return None
    ra, rb = path_a.boundingRect(), path_b.boundingRect()
    ux, uy = _dominant_gap_axis(path_a, path_b)
    if abs(ux) >= abs(uy):
        x0 = min(ra.right(), rb.right())
        x1 = max(ra.left(), rb.left())
        if x1 - x0 < 0.5:
            return None
        y0 = max(ra.top(), rb.top()) - 4.0
        y1 = min(ra.bottom(), rb.bottom()) + 4.0
        return QRectF(x0, min(y0, y1), x1 - x0, abs(y1 - y0))
    y0 = min(ra.bottom(), rb.bottom())
    y1 = max(ra.top(), rb.top())
    if y1 - y0 < 0.5:
        return None
    x0 = max(ra.left(), rb.left()) - 4.0
    x1 = min(ra.right(), rb.right()) + 4.0
    return QRectF(min(x0, x1), y0, abs(x1 - x0), y1 - y0)


def _gap_blockers(path_a, path_b, others):
    """Islands that occupy a meaningful fraction of the a–b gap AABB."""
    out = []
    gap = _gap_aabb(path_a, path_b)
    if gap is None or not others:
        return out
    for o in others:
        if o is None or o.isEmpty():
            continue
        ro = o.boundingRect()
        inter = gap.intersected(ro)
        if inter.isEmpty():
            continue
        ia = inter.width() * inter.height()
        oa = max(ro.width() * ro.height(), 1e-6)
        if ia >= 0.2 * oa:
            out.append(o)
    return out


def _gap_blocked(path_a, path_b, others):
    """True if another island sits in the waste between *path_a* and *path_b*."""
    return bool(_gap_blockers(path_a, path_b, others))


def _gap_blocked_only_by_tied_compacts(path_a, path_b, others, cluster,
                                       weed_path, walls=None):
    """True when gap blockers are only compact islands with ≥2 ties.

    Major↔major bottom necks may still seal through such ticks.
    """
    blockers = _gap_blockers(path_a, path_b, others)
    if not blockers:
        return False
    wall_tgts = [w for w in (walls or ()) if w is not None and not w.isEmpty()]
    for o in blockers:
        if not _sol_ties._is_compact_island(o, cluster):
            return False
        tgts = [b for b in cluster
                if b is not None and not b.isEmpty() and b is not o]
        tgts.extend(wall_tgts)
        if _sol_ties._compact_tie_count(weed_path, o, tgts) < _MIN_COMPACT_TIES:
            return False
    return True


def _seg_spans_pair(seg, path_a, path_b, tol=2.5):
    """True when one endpoint meets *path_a* and the other meets *path_b*."""
    if seg is None or path_a is None or path_b is None:
        return False
    x0, y0, x1, y1 = seg
    a0 = _sol_geom._point_near_path(x0, y0, path_a, tol)
    b0 = _sol_geom._point_near_path(x0, y0, path_b, tol)
    a1 = _sol_geom._point_near_path(x1, y1, path_a, tol)
    b1 = _sol_geom._point_near_path(x1, y1, path_b, tol)
    return (a0 and b1) or (b0 and a1)


def _mouth_seal(path_a, path_b, pa, pb, ax, ay, hit_t, standoff, keep_fill,
                work, min_cut, container, rules=None, against=None,
                peel_frame=None, near_mouth=False):
    """Keep-to-keep alley seal: D012 floors + class / E√L rank."""
    from . import agglomerate as _sol_agglomerate, corridors as _sol_corridors, emit as _sol_emit
    tx, ty = -ay, ax
    c_hat = (tx, ty)
    gap_w = math.hypot(pb.x() - pa.x(), pb.y() - pa.y())
    facing = _sol_corridors._corridor_facing(path_a, path_b)
    overlap_l = float(facing[0]) if facing is not None else 0.0
    r_hunt = _sol_rules._hunt_radius(gap_w, overlap_l)
    along_span = _facing_along_range(path_a, path_b, c_hat)
    if along_span is None:
        along_lo = along_hi = 0.5 * (
            (pa.x() + pb.x()) * tx + (pa.y() + pb.y()) * ty)
    else:
        along_lo, along_hi = along_span
    mouth_mid = QPointF(0.5 * (pa.x() + pb.x()), 0.5 * (pa.y() + pb.y()))
    peel_hat = _sol_peel._peel_dir_at(
        mouth_mid, {'kind': 'corridor', 'c_hat': c_hat, 'mouth': mouth_mid})
    if peel_hat is None:
        peel_hat = c_hat

    core = _sol_corridors._channel_core(path_a, path_b)
    core_span = _core_along_span(core, c_hat)
    ext_a = _body_along_extent(path_a, c_hat)
    ext_b = _body_along_extent(path_b, c_hat)
    len_a = (ext_a[1] - ext_a[0]) if ext_a else None
    len_b = (ext_b[1] - ext_b[0]) if ext_b else None

    mouth_along = mouth_mid.x() * tx + mouth_mid.y() * ty

    def is_lift_corner(c):
        """Outside thin core, and mouth still at/inside that core end."""
        if core_span is None:
            return True
        clo, chi = core_span
        along = c.x() * tx + c.y() * ty
        if along < clo - 0.35:
            return mouth_along >= clo - 1.0
        if along > chi + 0.35:
            return mouth_along <= chi + 1.0
        return False

    raw_a = _alley_facing_corners(
        path_a, path_b, c_hat, along_lo, along_hi, r_hunt, mouth=mouth_mid)
    raw_b = _alley_facing_corners(
        path_b, path_a, c_hat, along_lo, along_hi, r_hunt, mouth=mouth_mid)
    for c in _sol_peel._corners_near(path_a, pa, r_hunt, other=pb):
        if all(math.hypot(c.x() - q.x(), c.y() - q.y()) > 0.35
               for q in raw_a):
            raw_a.append(QPointF(c))
    for c in _sol_peel._corners_near(path_b, pb, r_hunt, other=pa):
        if all(math.hypot(c.x() - q.x(), c.y() - q.y()) > 0.35
               for q in raw_b):
            raw_b.append(QPointF(c))
    # Peel lift targets: alley corners beyond the thin core (O–K widen).
    lift_a = [c for c in raw_a if is_lift_corner(c)]
    lift_b = [c for c in raw_b if is_lift_corner(c)]

    pairs = []
    seen_pair = set()

    along_cap = max(0.5 * gap_w, 2.0)
    short_mouth = overlap_l <= 2.5 * max(gap_w, 1e-6)
    if near_mouth:
        short_mouth = True
        along_cap = max(0.6 * gap_w, 3.0)

    def add_pair(ha, hb):
        if ha is None or hb is None:
            return
        dx, dy = hb.x() - ha.x(), hb.y() - ha.y()
        if math.hypot(dx, dy) < max(float(min_cut), 1e-6):
            return
        if abs(dx * ax + dy * ay) < 0.35 * max(gap_w, 1.0):
            return
        if short_mouth:
            mid_along = (
                0.5 * (ha.x() + hb.x()) * tx + 0.5 * (ha.y() + hb.y()) * ty)
            if abs(mid_along - mouth_along) > along_cap + 1e-9:
                return
        key = (round(ha.x(), 3), round(ha.y(), 3),
               round(hb.x(), 3), round(hb.y(), 3))
        if key in seen_pair:
            return
        seen_pair.add(key)
        pairs.append((QPointF(ha), QPointF(hb)))

    def add_corner_pairs(corners_a, corners_b, slide_hits):
        for ca in corners_a:
            hit_b = _sol_geom._ray_hit_path(ca, ax, ay, path_b, hit_t)
            if hit_b is not None:
                add_pair(ca, hit_b)
            for cb in corners_b:
                add_pair(ca, cb)
            for _ha, hb in slide_hits:
                add_pair(ca, hb)
        for cb in corners_b:
            hit_a = _sol_geom._ray_hit_path(cb, ax, ay, path_a, hit_t)
            if hit_a is not None:
                add_pair(hit_a, cb)
            for ha, _hb in slide_hits:
                add_pair(ha, cb)

    # Keep the caller mouth anchors (often true corners / diagonal).
    # Axis-hit slides alone can replace them with mid-edge "square" chords.
    add_pair(pa, pb)
    slide_hits = []
    for step in (0.0, 1.5, 3.0, -1.5, -3.0):
        qa = QPointF(pa.x() + tx * step, pa.y() + ty * step)
        qb = QPointF(pb.x() + tx * step, pb.y() + ty * step)
        ha, hb = _axis_hit_pair(
            qa, qb, ax, ay, path_a, path_b, max_t=hit_t)
        add_pair(ha, hb)
        slide_hits.append((ha, hb))

    # Lift only when the primary mouth landing is an edge-lift mid-stick.
    use_lift_a, use_lift_b = [], []
    if slide_hits:
        ha0, hb0 = slide_hits[0]
        dx0, dy0 = hb0.x() - ha0.x(), hb0.y() - ha0.y()
        ln0 = math.hypot(dx0, dy0)
        if ln0 > 1e-12:
            w_a0 = (dx0 / ln0, dy0 / ln0)
            w_b0 = (-dx0 / ln0, -dy0 / ln0)
            d_a0 = _sol_peel._dist_to_points(ha0, lift_a, default=max(gap_w, 8.0))
            d_b0 = _sol_peel._dist_to_points(hb0, lift_b, default=max(gap_w, 8.0))
            if lift_a and _sol_rank._edge_lift_E(
                    ha0, w_a0, path_a, peel_hat, d_a0, body_len=len_a):
                use_lift_a = lift_a
            if lift_b and _sol_rank._edge_lift_E(
                    hb0, w_b0, path_b, peel_hat, d_b0, body_len=len_b):
                use_lift_b = lift_b
    add_corner_pairs(use_lift_a, use_lift_b, slide_hits)
    add_corner_pairs(raw_a, raw_b, slide_hits)
    lift_a, lift_b = use_lift_a, use_lift_b
    def evaluate_pairs():
        legal = []
        forced = []
        use_rules = rules if rules is not None else _sol_rules._cut_rules()
        emit_keep = keep_fill if keep_fill is not None else path_a
        others = _sol_emit._other_weed_segs(against)
        for ha, hb in pairs:
            # Two bodies, so the trial line only. Not either outline.
            _sol_emit._progress_check(line=(ha.x(), ha.y(), hb.x(), hb.y()))
            seg = _sol_agglomerate._fuse_bridge(
                ha, hb, standoff, keep_fill, work, min_cut, container)
            if seg is None or not _seg_spans_pair(seg, path_a, path_b):
                continue
            if _sol_emit._seg_emit_ok(
                    seg, emit_keep, against, use_rules,
                    peel_frame=peel_frame, other_segs=others):
                legal.append(seg)
            elif _sol_emit._seg_forced_ok(
                    seg, emit_keep, against, use_rules,
                    peel_frame=peel_frame, other_segs=others):
                forced.append(seg)
        return legal, forced

    legal, forced = evaluate_pairs()
    if not legal and not forced:
        add_corner_pairs(raw_a, raw_b, slide_hits)
        legal, forced = evaluate_pairs()
    emit_keep = keep_fill if keep_fill is not None else path_a
    picked = _sol_rank._pick_ranked_seg(
        legal, emit_keep, path_b, peel_frame, prefer=_CREATED_MOUTH_PREFER)
    if picked is not None:
        return picked
    short_f = []
    for seg in forced:
        ln = math.hypot(seg[2] - seg[0], seg[3] - seg[1])
        if ln <= 24.0:
            short_f.append(seg)
    return _sol_rank._pick_ranked_seg(
        short_f, emit_keep, path_b, peel_frame, prefer=_CREATED_MOUTH_PREFER)
