# -*- coding: utf-8 -*-
"""A channel-core seal."""
from __future__ import division

import math
from collections import namedtuple

from ..qt import QPainterPath, QPointF

from .rules import _SEARCH_PROBE
from .ties import _MIN_COMPACT_TIES
from . import emit as _sol_emit
from . import gaps as _sol_gaps
from . import geom as _sol_geom
from . import ties as _sol_ties


# Corridor: facing overlap is a large fraction of *both* islands.
_CORRIDOR_MIN_OVERLAP = 0.5
# Gap must be small vs that facing length.
_CORRIDOR_MAX_GAP = 0.6
# End-seal span ≤ k×width → one mid seal. 2.0 keeps HI dual-mouth (L/W≈2.25).
_CORRIDOR_SHORT_K = 2.0

ChannelCore = namedtuple(
    'ChannelCore',
    ('width', 'length', 'along0', 'along1',
     'pa0', 'pb0', 'pa1', 'pb1',
     'stations', 'thin', 'hx', 'hy'))


def _corridor_facing(path_a, path_b):
    """(overlap, size_a, size_b, gap) along the facing axis, or None."""
    if path_a is None or path_b is None or path_a.isEmpty() or path_b.isEmpty():
        return None
    ra, rb = path_a.boundingRect(), path_b.boundingRect()
    ux, uy = _sol_gaps._dominant_gap_axis(path_a, path_b)
    if abs(ux) >= abs(uy):
        overlap = min(ra.bottom(), rb.bottom()) - max(ra.top(), rb.top())
        size_a, size_b = ra.height(), rb.height()
        gap = max(0.0, ra.left() - rb.right(), rb.left() - ra.right())
    else:
        overlap = min(ra.right(), rb.right()) - max(ra.left(), rb.left())
        size_a, size_b = ra.width(), rb.width()
        gap = max(0.0, ra.top() - rb.bottom(), rb.top() - ra.bottom())
    if overlap <= 0.0 or size_a < 1e-6 or size_b < 1e-6:
        return None
    return overlap, size_a, size_b, gap


def _alley_width_profile(path_a, path_b, step=None):
    """(stations, hx, hy) along the facing overlap, or None."""
    facing = _corridor_facing(path_a, path_b)
    if facing is None:
        return None
    overlap, _size_a, _size_b, gap = facing
    if step is None:
        step = max(1.5, min(2.5, float(overlap) / 16.0))
    ax, ay = _sol_gaps._dominant_gap_axis(path_a, path_b)
    ra, rb = path_a.boundingRect(), path_b.boundingRect()
    rings_a = _sol_geom._path_to_rings(path_a)
    rings_b = _sol_geom._path_to_rings(path_b)
    if not rings_a or not rings_b:
        return None
    if abs(ax) >= abs(ay):
        t0 = max(ra.top(), rb.top())
        t1 = min(ra.bottom(), rb.bottom())
        if ra.center().x() <= rb.center().x():
            gx = 0.5 * (ra.right() + rb.left())
            left_rings, right_rings = rings_a, rings_b
        else:
            gx = 0.5 * (rb.right() + ra.left())
            left_rings, right_rings = rings_b, rings_a
        hx, hy = 1.0, 0.0

        def origin(t):
            return gx, t
    else:
        t0 = max(ra.left(), rb.left())
        t1 = min(ra.right(), rb.right())
        if ra.center().y() <= rb.center().y():
            gy = 0.5 * (ra.bottom() + rb.top())
            left_rings, right_rings = rings_a, rings_b
        else:
            gy = 0.5 * (rb.bottom() + ra.top())
            left_rings, right_rings = rings_b, rings_a
        hx, hy = 0.0, 1.0

        def origin(t):
            return t, gy
    if t1 - t0 < 1e-6:
        return None
    max_t = max(32.0, 2.0 * (float(gap) + 16.0))
    n = max(int(math.ceil((t1 - t0) / float(step))), 2)
    stations = []
    for i in range(n + 1):
        t = t0 + (t1 - t0) * i / float(n)
        ox, oy = origin(t)
        hit_l = _sol_geom._ray_intersect_rings(ox, oy, -hx, -hy, left_rings, max_t)
        hit_r = _sol_geom._ray_intersect_rings(ox, oy, hx, hy, right_rings, max_t)
        if hit_l is None or hit_r is None:
            continue
        width = math.hypot(hit_r[0] - hit_l[0], hit_r[1] - hit_l[1])
        stations.append((
            t, width,
            QPointF(hit_l[0], hit_l[1]),
            QPointF(hit_r[0], hit_r[1])))
    if len(stations) < 2:
        return None
    return stations, hx, hy


def _channel_core(path_a, path_b):
    """Thin through-channel between two keep walls, or None."""
    prof = _alley_width_profile(path_a, path_b)
    if prof is None:
        return None
    stations, hx, hy = prof
    wmin = min(s[1] for s in stations)
    slack = max(2.0, 0.25 * wmin)
    thin = [s[1] <= wmin + slack + 1e-9 for s in stations]
    if not any(thin):
        return None
    i0 = next(i for i, flag in enumerate(thin) if flag)
    i1 = (len(thin) - 1
          - next(i for i, flag in enumerate(reversed(thin)) if flag))
    s0, s1 = stations[i0], stations[i1]
    length = abs(s1[0] - s0[0])
    if length < max(3.0, 0.5 * max(wmin, 1e-6)):
        return None
    return ChannelCore(
        wmin, length, s0[0], s1[0], s0[2], s0[3], s1[2], s1[3],
        stations, thin, hx, hy)


def _channel_side_opening_seals(path_a, path_b, core, keep_fill, work,
                                standoff, min_cut, container,
                                peninsula_ratio=None):
    """Side-seal corridor openings when flare depth > local core width (D007)."""
    from . import agglomerate as _sol_agglomerate
    out = []
    _ = peninsula_ratio
    if core is None or not core.stations or not core.thin:
        return out
    stations = core.stations
    thin = core.thin
    hx, hy = core.hx, core.hy
    first = next((i for i, flag in enumerate(thin) if flag), None)
    if first is None:
        return out
    last = (len(thin) - 1
            - next(i for i, flag in enumerate(reversed(thin)) if flag))

    def across(p):
        return p.x() * hx + p.y() * hy

    thin_left = []
    thin_right = []
    for i, flag in enumerate(thin):
        if not flag:
            continue
        thin_left.append(across(stations[i][2]))
        thin_right.append(across(stations[i][3]))
    if not thin_left:
        return out
    thin_left.sort()
    thin_right.sort()
    ntl = len(thin_left)
    base_l = (thin_left[ntl // 2] if ntl % 2
              else 0.5 * (thin_left[ntl // 2 - 1] + thin_left[ntl // 2]))
    ntr = len(thin_right)
    base_r = (thin_right[ntr // 2] if ntr % 2
              else 0.5 * (thin_right[ntr // 2 - 1] + thin_right[ntr // 2]))
    local_w = max(float(core.width), 1e-6)

    i = first
    while i <= last:
        if thin[i]:
            i += 1
            continue
        j = i
        while j <= last and not thin[j]:
            j += 1
        # End flare: core mouth already necks the channel; skip end bands.
        if i <= first or j - 1 >= last:
            i = j
            continue
        flare = stations[i:j]
        if not flare:
            i = j
            continue
        # Opening depth into the side = max width gain over the thin core.
        extra = max(s[1] for s in flare) - core.width
        span = abs(stations[j - 1][0] - stations[i][0])
        if extra < 1.0 or span < 2.0:
            i = j
            continue
        # D007 corridor stop: seal when opening depth > local corridor width.
        if extra <= local_w + 1e-9:
            i = j
            continue
        n_f = float(len(flare))
        flare_l = sum(across(s[2]) for s in flare) / n_f
        flare_r = sum(across(s[3]) for s in flare) / n_f
        left_rec = base_l - flare_l
        right_rec = flare_r - base_r
        if right_rec >= left_rec and right_rec >= 1.0:
            receding = 3
        elif left_rec > right_rec and left_rec >= 1.0:
            receding = 2
        else:
            i = j
            continue
        base = base_r if receding == 3 else base_l
        a0, a1 = stations[i][0], stations[j - 1][0]
        pull = (hx, hy) if receding == 3 else (-hx, -hy)
        if abs(hx) >= abs(hy):
            mid = QPointF(base + pull[0] * _SEARCH_PROBE, 0.5 * (a0 + a1))
            lx, ly = 0.0, 1.0
        else:
            mid = QPointF(0.5 * (a0 + a1), base + pull[1] * _SEARCH_PROBE)
            lx, ly = 1.0, 0.0
        rings = _sol_geom._path_to_rings(path_a) + _sol_geom._path_to_rings(path_b)
        max_t = span + 8.0
        hit0 = _sol_geom._ray_intersect_rings(mid.x(), mid.y(), -lx, -ly, rings, max_t)
        hit1 = _sol_geom._ray_intersect_rings(mid.x(), mid.y(), lx, ly, rings, max_t)
        if hit0 is None or hit1 is None:
            i = j
            continue
        pa, pb = QPointF(hit0[0], hit0[1]), QPointF(hit1[0], hit1[1])
        seg = _sol_agglomerate._fuse_bridge(
            pa, pb, standoff, keep_fill, work, min_cut, container)
        if seg is not None:
            out.append(seg)
        i = j
    return out


def _is_corridor_pair(path_a, path_b):
    """Thin channel core between two keep walls; satellites are not corridors."""
    from . import cluster as _sol_cluster
    if _sol_cluster._is_stacked_satellite(path_a, path_b) or _sol_cluster._is_stacked_satellite(
            path_b, path_a):
        return False
    facing = _corridor_facing(path_a, path_b)
    if facing is None:
        return False
    overlap, size_a, size_b, gap = facing
    if (overlap < _CORRIDOR_MIN_OVERLAP * size_a
            or overlap < _CORRIDOR_MIN_OVERLAP * size_b):
        return False
    if gap > _CORRIDOR_MAX_GAP * overlap:
        return False
    if _channel_core(path_a, path_b) is not None:
        return True
    return len(_sol_gaps._facing_end_mouths(path_a, path_b)) >= 2


def _mouth_body_end(mouth, body, band):
    """Which AABB end of *body* a mouth sits on, or None."""
    if body is None or body.isEmpty() or not mouth:
        return None
    br = body.boundingRect()
    pa, pb = mouth[0], mouth[1]
    mx = 0.5 * (pa.x() + pb.x())
    my = 0.5 * (pa.y() + pb.y())
    if br.height() >= br.width():
        dt = abs(my - br.top())
        db = abs(my - br.bottom())
        if dt <= db and dt <= band:
            return 'top'
        if db <= band:
            return 'bottom'
        return None
    dl = abs(mx - br.left())
    dr = abs(mx - br.right())
    if dl <= dr and dl <= band:
        return 'left'
    if dr <= band:
        return 'right'
    return None


def _fork_branch_mouths(cluster):
    """Corridor mouths that share a body end with another corridor (T)."""
    from . import cluster as _sol_cluster
    bodies = [b for b in cluster if b is not None and not b.isEmpty()]
    n = len(bodies)
    if n < 3:
        return []
    entries = []
    for i in range(n):
        for j in range(i + 1, n):
            a, b = bodies[i], bodies[j]
            if _sol_cluster._is_stacked_satellite(a, b) or _sol_cluster._is_stacked_satellite(b, a):
                continue
            others = [bodies[k] for k in range(n) if k != i and k != j]
            if _sol_gaps._gap_blocked(a, b, others):
                continue
            if not _is_corridor_pair(a, b):
                continue
            mouths = _sol_gaps._gap_mouths(a, b)
            if len(mouths) < 2:
                continue
            entries.append((a, b, mouths))
    if len(entries) < 2:
        return []
    at = {}
    for a, b, mouths in entries:
        facing = _corridor_facing(a, b)
        width = facing[3] if facing is not None else 0.0
        band = max(3.0, 0.5 * max(width, 1e-6))
        for mouth in mouths:
            for body in (a, b):
                end = _mouth_body_end(mouth, body, band)
                if end is None:
                    continue
                at.setdefault((id(body), end), []).append((a, b, mouth))
    seen = set()
    out = []
    for items in at.values():
        pair_ids = set()
        for a, b, _m in items:
            ia, ib = id(a), id(b)
            pair_ids.add((ia, ib) if ia <= ib else (ib, ia))
        if len(pair_ids) < 2:
            continue
        for a, b, mouth in items:
            ia, ib = id(a), id(b)
            pid = (ia, ib) if ia <= ib else (ib, ia)
            key = (
                pid,
                round(0.5 * (mouth[0].x() + mouth[1].x()), 3),
                round(0.5 * (mouth[0].y() + mouth[1].y()), 3),
            )
            if key in seen:
                continue
            seen.add(key)
            out.append((a, b, mouth[0], mouth[1], mouth[2]))
    return out


def _pair_fork_mouth_indices(path_a, path_b, mouths, fork_mouths):
    """Indices into *mouths* that are T-junction branch necks."""
    if not fork_mouths or not mouths:
        return set()
    ia, ib = id(path_a), id(path_b)
    want = (ia, ib) if ia <= ib else (ib, ia)
    hit = set()
    for fa, fb, pa, pb, _d in fork_mouths:
        fa_id, fb_id = id(fa), id(fb)
        key = (fa_id, fb_id) if fa_id <= fb_id else (fb_id, fa_id)
        if key != want:
            continue
        fmx = 0.5 * (pa.x() + pb.x())
        fmy = 0.5 * (pa.y() + pb.y())
        for i, (qa, qb, _dist) in enumerate(mouths):
            mx = 0.5 * (qa.x() + qb.x())
            my = 0.5 * (qa.y() + qb.y())
            if math.hypot(mx - fmx, my - fmy) <= 4.0:
                hit.add(i)
    return hit


def _corridor_chunk_seals(path_a, path_b, mouths, max_chunk, ax, ay, hit_t,
                          standoff, keep_fill, work, min_cut, container,
                          rules=None, against=None, peel_frame=None):
    """Extra seals between the two mouths when the alley is longer than *max_chunk*."""
    from . import agglomerate as _sol_agglomerate
    if max_chunk is None or len(mouths) != 2:
        return []
    (pa0, pb0, _), (pa1, pb1, _) = mouths
    mx0 = 0.5 * (pa0.x() + pb0.x())
    my0 = 0.5 * (pa0.y() + pb0.y())
    mx1 = 0.5 * (pa1.x() + pb1.x())
    my1 = 0.5 * (pa1.y() + pb1.y())
    span = math.hypot(mx1 - mx0, my1 - my0)
    if span <= float(max_chunk) + 1e-6:
        return []
    n = max(int(math.ceil(span / float(max_chunk))), 2)
    extra = []
    for i in range(1, n):
        t = i / float(n)
        pa = QPointF(pa0.x() + t * (pa1.x() - pa0.x()),
                     pa0.y() + t * (pa1.y() - pa0.y()))
        pb = QPointF(pb0.x() + t * (pb1.x() - pb0.x()),
                     pb0.y() + t * (pb1.y() - pb0.y()))
        ha, hb = _sol_gaps._axis_hit_pair(
            pa, pb, ax, ay, path_a, path_b, max_t=hit_t)
        seg = None
        if ha is not None and hb is not None:
            seg = _sol_agglomerate._fuse_bridge(
                ha, hb, standoff, keep_fill, work, min_cut, container)
        if seg is None:
            seg = _sol_gaps._mouth_seal(
                path_a, path_b, pa, pb, ax, ay, hit_t, standoff, keep_fill,
                work, min_cut, container, rules=rules, against=against,
                peel_frame=peel_frame)
        if seg is not None:
            extra.append(seg)
    return extra


def _order_mouth_to_paths(pa, pb, path_a, path_b):
    """Return (end_on_a, end_on_b); core mouths are geometric L/R, not arg order."""
    if pa is None or pb is None:
        return pa, pb
    a_on_a = _sol_geom._point_near_path(pa.x(), pa.y(), path_a)
    b_on_b = _sol_geom._point_near_path(pb.x(), pb.y(), path_b)
    if a_on_a and b_on_b:
        return pa, pb
    a_on_b = _sol_geom._point_near_path(pa.x(), pa.y(), path_b)
    b_on_a = _sol_geom._point_near_path(pb.x(), pb.y(), path_a)
    if a_on_b and b_on_a:
        return pb, pa
    return pa, pb


def _seal_corridor_pair(path_a, path_b, keep_fill, work, standoff, min_cut,
                        container, max_chunk=None, fork_mouths=None,
                        cluster=None, rules=None, against=None,
                        peel_frame=None):
    """Seal the channel core: short → one mid; else core ends (+ max_chunk).

    Fork mouths (T-junction branches) keep their necks; no mid collapse.
    Seals that collapse onto a single body are dropped (no cuts to nowhere).
    *cluster* expands each side with stacked satellites so mouths reach a
    host's dots (H→i-dot, not only H→stem top).
    """
    from . import cluster as _sol_cluster
    out = []
    expand_sats = bool(cluster)
    # Framed word: once stacked specks are host+wall tied, seal host mouths
    # only (stem↔H) — do not re-open via the speck coast (H↔i-dot).
    if (expand_sats and container is not None and not container.isEmpty()
            and against is not None and not against.isEmpty()):
        sats = (_sol_cluster._stacked_satellites_of(path_a, cluster)
                + _sol_cluster._stacked_satellites_of(path_b, cluster))
        if sats:
            done = True
            for sat in sats:
                if not _sol_ties._is_compact_island(sat, cluster):
                    done = False
                    break
                host = _sol_cluster._stacked_host_of(sat, cluster)
                tgts = [container]
                if host is not None:
                    tgts.append(host)
                if peel_frame is not None and not peel_frame.isEmpty():
                    tgts.append(peel_frame)
                if len(_sol_ties._compact_tie_segs(against, sat, tgts)) < _MIN_COMPACT_TIES:
                    done = False
                    break
            if done:
                expand_sats = False
    use_cluster = cluster if expand_sats else None
    a_use = (_sol_cluster._with_stacked_satellites(path_a, cluster)
             if use_cluster else path_a)
    b_use = (_sol_cluster._with_stacked_satellites(path_b, cluster)
             if use_cluster else path_b)
    mouths = _sol_gaps._gap_mouths(path_a, path_b, cluster=use_cluster)
    if not mouths:
        return out
    ax, ay = _sol_gaps._dominant_gap_axis(a_use, b_use)
    span = max(m[2] for m in mouths)
    hit_t = max(32.0, 2.0 * span)

    def mouth_done(pa, pb, dist):
        if against is None or against.isEmpty():
            return False
        mouth = (pa, pb, dist)
        if _sol_gaps._mouth_near_spanning_seals(
                against, path_a, path_b, mouth, cluster=cluster):
            return True
        # Satellite already sealed to the neighbor — skip duplicate H↔i-dot.
        if cluster:
            for body, other in ((path_a, path_b), (path_b, path_a)):
                for sat in _sol_cluster._stacked_satellites_of(body, cluster):
                    on_sat = (
                        _sol_geom._point_near_path(pa.x(), pa.y(), sat, tol=2.5)
                        or _sol_geom._point_near_path(pb.x(), pb.y(), sat, tol=2.5))
                    if not on_sat:
                        continue
                    if _sol_gaps._pair_has_spanning_seal(against, sat, other):
                        return True
        return False

    def accept_pair(seg):
        """Across-alley mouth: must meet both keep walls (host or sat)."""
        if seg is None:
            return
        if not _sol_gaps._seg_spans_pair(seg, a_use, b_use):
            return
        out.append(seg)

    def accept_any(seg):
        """Side-pocket necks may both land on one wall."""
        if seg is not None:
            out.append(seg)

    aligned = []
    for pa, pb, dist in mouths:
        pa, pb = _order_mouth_to_paths(pa, pb, a_use, b_use)
        qa, qb = _sol_gaps._axis_hit_pair(
            pa, pb, ax, ay, a_use, b_use, max_t=hit_t)
        aligned.append((qa, qb, dist))
    mouths = aligned
    raw_mouths = list(mouths)
    fork_mis = _pair_fork_mouth_indices(
        path_a, path_b, mouths, fork_mouths)
    if len(mouths) == 2:
        (pa0, pb0, d0), (pa1, pb1, d1) = mouths
        m0x = 0.5 * (pa0.x() + pb0.x())
        m0y = 0.5 * (pa0.y() + pb0.y())
        m1x = 0.5 * (pa1.x() + pb1.x())
        m1y = 0.5 * (pa1.y() + pb1.y())
        dx, dy = m1x - m0x, m1y - m0y
        ln = math.hypot(dx, dy)
        # Width = facing gap; fall back to mean keep-to-keep mouth length.
        facing = _corridor_facing(a_use, b_use)
        if facing is None:
            facing = _corridor_facing(path_a, path_b)
        width = facing[3] if facing is not None else 0.0
        if width < 1e-6:
            la = math.hypot(pa0.x() - pb0.x(), pa0.y() - pb0.y())
            lb = math.hypot(pa1.x() - pb1.x(), pa1.y() - pb1.y())
            width = 0.5 * (la + lb)
            if width < 1e-6:
                width = 0.5 * (float(d0) + float(d1))
        short = width > 1e-6 and ln <= _CORRIDOR_SHORT_K * width
        if short and not fork_mis:
            t = 0.5
            pa = QPointF(pa0.x() + t * (pa1.x() - pa0.x()),
                         pa0.y() + t * (pa1.y() - pa0.y()))
            pb = QPointF(pb0.x() + t * (pb1.x() - pb0.x()),
                         pb0.y() + t * (pb1.y() - pb0.y()))
            mid_dist = 0.5 * (float(d0) + float(d1))
            if not mouth_done(pa, pb, mid_dist):
                accept_pair(_sol_gaps._mouth_seal(
                    a_use, b_use, pa, pb, ax, ay, hit_t, standoff, keep_fill,
                    work, min_cut, container, rules=rules, against=against,
                    peel_frame=peel_frame))
            for seg in _channel_side_opening_seals(
                    path_a, path_b, _channel_core(path_a, path_b), keep_fill,
                    work, standoff, min_cut, container):
                accept_any(seg)
            return out
        if short and fork_mis:
            keep_idx = sorted(i for i in fork_mis if 0 <= i < len(mouths))
            if keep_idx:
                mouths = [mouths[i] for i in keep_idx]
                raw_mouths = list(mouths)
                for pa, pb, dist in mouths:
                    if mouth_done(pa, pb, dist):
                        continue
                    accept_pair(_sol_gaps._mouth_seal(
                        a_use, b_use, pa, pb, ax, ay, hit_t, standoff,
                        keep_fill, work, min_cut, container, rules=rules,
                        against=against, peel_frame=peel_frame))
                for seg in _channel_side_opening_seals(
                        path_a, path_b, _channel_core(path_a, path_b),
                        keep_fill, work, standoff, min_cut, container):
                    accept_any(seg)
                return out
    for pa, pb, dist in mouths:
        if mouth_done(pa, pb, dist):
            continue
        accept_pair(_sol_gaps._mouth_seal(
            a_use, b_use, pa, pb, ax, ay, hit_t, standoff, keep_fill,
            work, min_cut, container, rules=rules, against=against,
            peel_frame=peel_frame))
    for seg in _corridor_chunk_seals(
            a_use, b_use, raw_mouths, max_chunk, ax, ay, hit_t, standoff,
            keep_fill, work, min_cut, container, rules=rules,
            against=against, peel_frame=peel_frame):
        accept_pair(seg)
    core = _channel_core(path_a, path_b)
    for seg in _channel_side_opening_seals(
            path_a, path_b, core, keep_fill, work, standoff, min_cut,
            container):
        accept_any(seg)
    return out


def _seal_divergent_corridors(cluster, keep_fill, work, standoff, min_cut,
                              container, against=None, max_chunk=None,
                              rules=None, peel_frame=None):
    """Seal leftover wrap alleys (both mouths) after islands are one piece."""
    from . import cluster as _sol_cluster
    out = QPainterPath()
    seen = QPainterPath()
    if against is not None:
        seen.addPath(against)
    n = len(cluster)
    fork_mouths = _fork_branch_mouths(cluster)
    for i in range(n):
        for j in range(i + 1, n):
            others = [cluster[k] for k in range(n) if k != i and k != j]
            if _sol_gaps._gap_blocked(cluster[i], cluster[j], others):
                continue
            if _sol_cluster._is_hanging(cluster[i], cluster[j]):
                continue
            if _sol_cluster._is_stacked_satellite(cluster[i], cluster[j]) or (
                    _sol_cluster._is_stacked_satellite(cluster[j], cluster[i])):
                continue
            if not _is_corridor_pair(cluster[i], cluster[j]):
                continue
            for seg in _seal_corridor_pair(
                    cluster[i], cluster[j], keep_fill, work, standoff,
                    min_cut, container, max_chunk=max_chunk,
                    fork_mouths=fork_mouths, cluster=cluster,
                    rules=rules, against=seen, peel_frame=peel_frame):
                if _sol_emit._seg_redundant(seen, seg) or _sol_geom._seg_crosses_path(seen, seg):
                    continue
                _sol_emit._add_seg(out, seg, 0.0, keep_path=keep_fill)
                _sol_emit._add_seg(seen, seg, 0.0, keep_path=keep_fill, report=False)
    return out
