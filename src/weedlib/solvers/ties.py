# -*- coding: utf-8 -*-
"""A compact island tied to a host."""
from __future__ import division

import math

from .. import debug as _wdbg
from ..qt import QPainterPath, QPointF
from ..keep import _path_area

from . import geom as _sol_geom
from . import rank as _sol_rank
from . import rules as _sol_rules
from . import stats as _sol_stats


def _is_compact_island(body, cluster):
    """Small compact keep speck in water (not an elongated stem/mark).

    Thin short ticks (quote marks) count as compact when area is tiny and
    the long side is short — they get square ties, not hanging gutters.
    """
    if body is None or body.isEmpty() or not cluster:
        return False
    br = body.boundingRect()
    w, h = float(br.width()), float(br.height())
    if w < 1e-6 or h < 1e-6:
        return False
    area = abs(_path_area(body))
    peak = 0.0
    for b in cluster:
        if b is None or b.isEmpty():
            continue
        peak = max(peak, abs(_path_area(b)))
    if peak < 1e-6 or area >= 0.22 * peak:
        return False
    aspect = min(w, h) / max(w, h)
    if aspect < 0.55:
        # Thin tick speck (not a long stem).
        return area < 0.08 * peak and max(w, h) <= 14.0
    return True


def _square_tie_cands(island, targets, keep_fill, work, min_cut, container):
    """Short near-normal seals from a compact island to nearby coasts."""
    from . import agglomerate as _sol_agglomerate
    if island is None or island.isEmpty() or not targets:
        return []
    samples = _sol_geom._outline_samples(island, max_pts=10)
    corners = _sol_geom._convex_corners(island)
    cands = []
    seen = set()

    def add(ha, hb):
        if ha is None or hb is None:
            return
        key = (round(ha.x(), 2), round(ha.y(), 2),
               round(hb.x(), 2), round(hb.y(), 2))
        if key in seen:
            return
        seen.add(key)
        seg = _sol_agglomerate._fuse_bridge(
            ha, hb, 0.0, keep_fill, work, min_cut, container)
        if seg is not None:
            cands.append(seg)

    live = [t for t in targets
            if t is not None and not t.isEmpty() and t is not island]
    # Prefer the closest few coasts (letter / frame / rail).
    ranked = []
    ir = island.boundingRect()
    for tgt in live:
        tr = tgt.boundingRect()
        dx = max(0.0, tr.left() - ir.right(), ir.left() - tr.right())
        dy = max(0.0, tr.top() - ir.bottom(), ir.top() - tr.bottom())
        if math.hypot(dx, dy) > 32.0:
            continue
        pair = _sol_geom._nearest_pair(island, tgt)
        if pair is not None and pair[2] <= 28.0:
            ranked.append((pair[2], tgt, pair))
    ranked.sort(key=lambda t: t[0])
    if ranked:
        # Near-equidistant: try larger hosts first (elongated stem over tick).
        d0 = ranked[0][0]
        near = [t for t in ranked if t[0] <= 1.35 * d0 + 1e-9]
        near.sort(key=lambda t: (-abs(_path_area(t[1])), t[0]))
        far = [t for t in ranked if t[0] > 1.35 * d0 + 1e-9]
        ranked = near + far
    for _d, tgt, pair in ranked[:4]:
        add(pair[0], pair[1])
    # Seed convex corners: nearest-host fuse so class-0 can win rank.
    near_tgts = [t for _d, t, _p in ranked[:4]] or live
    for c in corners:
        for tgt in near_tgts:
            hit = _sol_geom._closest_on_line_segs(c.x(), c.y(), tgt)
            if hit is None or hit[2] > 28.0:
                continue
            add(c, QPointF(hit[0], hit[1]))
    # Outward rays from outline samples + convex corners.
    ray_pts = list(samples)
    for c in corners:
        if all(math.hypot(c.x() - p.x(), c.y() - p.y()) > 0.2
               for p in ray_pts):
            ray_pts.append(c)
    for p in ray_pts:
        frame = _sol_geom._keep_frame_at(island, p)
        if frame is None or frame.n_hat is None:
            continue
        nx, ny = frame.n_hat
        for deg in (0.0, 25.0, -25.0):
            ux, uy = _sol_geom._rotate_hat(nx, ny, deg)
            for tgt in near_tgts:
                hit = _sol_geom._ray_hit_path(p, ux, uy, tgt, max_t=24.0)
                if hit is not None:
                    add(p, hit)
        # Peel frames are open polylines — `_ray_hit_path` needs closed
        # rings — so also project onto line segs along the outward normal.
        for tgt in near_tgts:
            if _sol_geom._path_to_rings(tgt):
                continue
            hit = _sol_geom._closest_on_line_segs(p.x(), p.y(), tgt)
            if hit is None or hit[2] > 24.0 or hit[2] < 0.8:
                continue
            hx, hy = hit[0] - p.x(), hit[1] - p.y()
            # Must leave the speck roughly outward (not through the body).
            if hx * nx + hy * ny <= 0.15 * hit[2]:
                continue
            add(p, QPointF(hit[0], hit[1]))
    return cands


# Compact keep specks: one tie leaves waste free to fork around the island
# (corridors above/below or left/right). Prefer two divergent seals.
_MIN_COMPACT_TIES = 2
# Second-tie direction vs first: reject near-parallel (cos ~70°).
_COMPACT_TIE_MAX_DOT = 0.35


def _compact_tie_segs(weed_path, speck, targets, max_ln=28.0):
    """Short weed segs that already join *speck* to some target coast."""
    from . import gaps as _sol_gaps
    out = []
    if weed_path is None or weed_path.isEmpty() or speck is None:
        return out
    seen = set()
    for tgt in targets:
        if tgt is None or tgt.isEmpty() or tgt is speck:
            continue
        for seg in _sol_gaps._pair_spanning_segs(weed_path, speck, tgt):
            ln = math.hypot(seg[2] - seg[0], seg[3] - seg[1])
            if ln > float(max_ln):
                continue
            key = (round(seg[0], 2), round(seg[1], 2),
                   round(seg[2], 2), round(seg[3], 2))
            if key in seen:
                continue
            seen.add(key)
            out.append(seg)
    return out


def _compact_already_tied(weed_path, speck, targets, max_ln=24.0):
    """True if *speck* already has a short seal to some target coast."""
    return bool(_compact_tie_segs(weed_path, speck, targets, max_ln=max_ln))


def _tie_outward_hat(seg, speck):
    """Unit vector from *speck* coast toward the far end of *seg*."""
    if seg is None or speck is None or speck.isEmpty():
        return None
    a_on = _sol_geom._point_near_path(seg[0], seg[1], speck, tol=2.5)
    b_on = _sol_geom._point_near_path(seg[2], seg[3], speck, tol=2.5)
    if a_on and not b_on:
        dx, dy = seg[2] - seg[0], seg[3] - seg[1]
    elif b_on and not a_on:
        dx, dy = seg[0] - seg[2], seg[1] - seg[3]
    else:
        c = speck.boundingRect().center()
        mx, my = 0.5 * (seg[0] + seg[2]), 0.5 * (seg[1] + seg[3])
        dx, dy = mx - c.x(), my - c.y()
    ln = math.hypot(dx, dy)
    if ln < 1e-9:
        return None
    return (dx / ln, dy / ln)


def _ties_diverge(seg_a, seg_b, speck, max_dot=_COMPACT_TIE_MAX_DOT):
    """True if two ties leave *speck* in substantially different directions."""
    ha = _tie_outward_hat(seg_a, speck)
    hb = _tie_outward_hat(seg_b, speck)
    if ha is None or hb is None:
        return True
    return ha[0] * hb[0] + ha[1] * hb[1] <= float(max_dot)


def _pick_square_tie(cands, keep_fill, against, rules, peel_frame=None,
                     hosts=None):
    """Best legal (prefer square) short tie; short forced only as last resort."""
    from . import emit as _sol_emit
    if not cands:
        return None
    use_rules = rules if rules is not None else _sol_rules._cut_rules()
    others = _sol_emit._other_weed_segs(against)
    cands = sorted(
        (s for s in cands if s is not None),
        key=lambda s: math.hypot(s[2] - s[0], s[3] - s[1]))[:16]
    legal = []
    forced = []
    rejected = []
    for seg in cands:
        if seg is None:
            continue
        # T-junction onto an existing weed is wanted; only reject crosses.
        if against is not None and _sol_geom._seg_crosses_path(against, seg):
            rejected.append(('cross_weed', seg))
            continue
        if _sol_emit._seg_emit_ok(
                seg, keep_fill, against, use_rules, peel_frame=peel_frame,
                other_segs=others):
            legal.append(seg)
        elif _sol_emit._seg_forced_ok(
                seg, keep_fill, against, use_rules, peel_frame=peel_frame,
                other_segs=others):
            forced.append(seg)
        else:
            rejected.append((
                _sol_emit._seg_emit_fail_reason(
                    seg, keep_fill, against, use_rules,
                    peel_frame=peel_frame, other_segs=others) or 'forced_fail',
                seg))

    def _prefer_host(pool):
        if not pool:
            return None
        if not hosts:
            return _sol_rank._pick_quality_seg(pool, keep_fill, peel_frame=peel_frame)
        lens = [math.hypot(s[2] - s[0], s[3] - s[1]) for s in pool]
        d0 = min(lens)
        near = [s for s, ln in zip(pool, lens) if ln <= 1.35 * d0 + 1e-9]

        def host_hit(seg):
            best = 0.0
            for h in hosts:
                if h is None or h.isEmpty():
                    continue
                # Other end of the tie sits on keep_fill; detect host by
                # endpoint proximity.
                if (_sol_geom._point_near_path(seg[0], seg[1], h, tol=2.5)
                        or _sol_geom._point_near_path(seg[2], seg[3], h, tol=2.5)):
                    best = max(best, abs(_path_area(h)))
            return best

        near.sort(key=lambda s: (
            -host_hit(s),
            _sol_rank._peel_rank_key(s, keep_fill, peel_frame=peel_frame)))
        return near[0] if near else _sol_rank._pick_quality_seg(
            pool, keep_fill, peel_frame=peel_frame)

    picked = _prefer_host(legal)
    source = 'legal'
    if picked is None:
        short_f = []
        for seg in forced:
            ln = math.hypot(seg[2] - seg[0], seg[3] - seg[1])
            if ln <= 24.0:
                short_f.append(seg)
        picked = _prefer_host(short_f)
        source = 'forced'
    if _wdbg.enabled():
        _wdbg.log(
            'square_tie.pick', source=source if picked else 'none',
            legal=len(legal), forced=len(forced), rejected=len(rejected),
            picked=picked,
            reject_sample=[
                '%s:%s' % (r, _wdbg.seg_fmt(s)) for r, s in rejected[:4]])
    return picked


def _compact_tie_hits_target(seg, target, tol=2.5):
    """True if either end of *seg* lands on *target*."""
    if seg is None or target is None or target.isEmpty():
        return False
    return (
        _sol_geom._point_near_path(seg[0], seg[1], target, tol=tol)
        or _sol_geom._point_near_path(seg[2], seg[3], target, tol=tol))


def _path_near_seg(path, seg, tol=2.0):
    """True if any outline sample of *path* lies within *tol* of *seg*."""
    if path is None or path.isEmpty() or seg is None:
        return False
    br = path.boundingRect().adjusted(-tol, -tol, tol, tol)
    x0, y0, x1, y1 = seg
    if (max(x0, x1) < br.left() or min(x0, x1) > br.right()
            or max(y0, y1) < br.top() or min(y0, y1) > br.bottom()):
        return False
    for p in _sol_geom._outline_samples(path, max_pts=12):
        if _sol_geom._point_seg_dist(p.x(), p.y(), *seg) <= tol:
            return True
    return False


def _compact_t_on_target_seals(weed_path, speck, targets, tol=2.0):
    """Target↔target weed seals that *speck* already T-meets."""
    out = []
    if weed_path is None or weed_path.isEmpty() or speck is None:
        return out
    live = [t for t in targets
            if t is not None and not t.isEmpty() and t is not speck]
    if len(live) < 2:
        return out
    seen = set()
    ep_tol = max(float(tol), 2.5)
    for seg in _sol_geom._iter_line_segs(weed_path):
        if not _path_near_seg(speck, seg, tol=tol):
            continue
        a_hit = [t for t in live
                 if _sol_geom._point_near_path(seg[0], seg[1], t, tol=ep_tol)]
        if not a_hit:
            continue
        b_hit = [t for t in live
                 if _sol_geom._point_near_path(seg[2], seg[3], t, tol=ep_tol)]
        if not b_hit:
            continue
        if not any(a is not b for a in a_hit for b in b_hit):
            continue
        key = (round(seg[0], 2), round(seg[1], 2),
               round(seg[2], 2), round(seg[3], 2))
        if key in seen:
            continue
        seen.add(key)
        out.append(seg)
    return out


def _compact_tie_count(weed_path, speck, targets):
    """Spanning ties plus T-meets onto existing target↔target seals."""
    n = len(_compact_tie_segs(weed_path, speck, targets))
    n += len(_compact_t_on_target_seals(weed_path, speck, targets))
    return n


def _seal_compact_islands(cluster, keep_fill, work, standoff, min_cut,
                          container, against=None, rules=None, peel_frame=None):
    """Square seals from compact keep specks (≥2 divergent ties when possible)."""
    from . import cluster as _sol_cluster, emit as _sol_emit
    _ = standoff
    out = QPainterPath()
    seen = QPainterPath()
    if against is not None:
        seen.addPath(against)
    specks = [b for b in cluster if _is_compact_island(b, cluster)]
    if not specks:
        return out
    others = [b for b in cluster
              if b is not None and not b.isEmpty() and b not in specks]
    walls = []
    if container is not None and not container.isEmpty():
        walls.append(container)
    if peel_frame is not None and not peel_frame.isEmpty():
        walls.append(peel_frame)
    base_targets = list(others) + list(walls)
    if not base_targets and len(specks) < 2:
        return out
    for speck in specks:
        targets = list(base_targets)
        # Nearby fellow ticks (quote pairs) — avoid long leaps over them.
        for other in specks:
            if other is speck:
                continue
            pair = _sol_geom._nearest_pair(speck, other)
            if pair is not None and pair[2] <= 12.0:
                targets.append(other)
        if not targets:
            continue
        host = _sol_cluster._stacked_host_of(speck, cluster)
        for _attempt in range(_MIN_COMPACT_TIES):
            if _compact_tie_count(seen, speck, targets) >= _MIN_COMPACT_TIES:
                break
            existing = _compact_tie_segs(seen, speck, targets)
            # Inside a design container: after the stacked host is tied,
            # second ties prefer the container wall — not other letters.
            use_targets = targets
            in_container = (
                container is not None and not container.isEmpty())
            if existing and host is not None and in_container:
                host_tied = any(
                    _compact_tie_hits_target(e, host) for e in existing)
                if host_tied:
                    wallish = [container]
                    if peel_frame is not None and not peel_frame.isEmpty():
                        wallish.append(peel_frame)
                    for other in specks:
                        if other is speck:
                            continue
                        pair = _sol_geom._nearest_pair(speck, other)
                        if pair is not None and pair[2] <= 12.0:
                            wallish.append(other)
                    wallish.append(host)
                    use_targets = wallish
            cands = _square_tie_cands(
                speck, use_targets, keep_fill, work, min_cut, container)
            # Do not drop T-junction-near segs via _seg_redundant — square
            # ties may land on an existing peninsula/weed end (pick rejects
            # only true crosses).
            cands = [s for s in cands if s is not None]
            short = [s for s in cands
                     if math.hypot(s[2] - s[0], s[3] - s[1]) <= 10.0]
            pools = []
            if existing:
                def _divergent(pool_):
                    return [
                        s for s in pool_
                        if all(_ties_diverge(s, e, speck) for e in existing)]

                divergent_short = _divergent(short)
                divergent_all = _divergent(cands)
                if not divergent_short and not divergent_all:
                    break
                first_ln = min(
                    math.hypot(e[2] - e[0], e[3] - e[1]) for e in existing)
                max_second = max(14.0, 2.5 * first_ln)
                capped = [
                    s for s in divergent_all
                    if math.hypot(s[2] - s[0], s[3] - s[1]) <= max_second]
                # Container wall first when host already tied (framed word).
                if use_targets is not targets and in_container:
                    def _wall_hit(seg):
                        return _compact_tie_hits_target(seg, container)

                    wall_short = [s for s in divergent_short if _wall_hit(s)]
                    wall_all = [s for s in capped if _wall_hit(s)]
                    for p in (wall_short, wall_all):
                        if p and p not in pools:
                            pools.append(p)
                for p in (divergent_short, capped, divergent_all):
                    if p and p not in pools:
                        pools.append(p)
            else:
                pools.append(short if short else cands)
            # First tie: prefer large letter hosts. Later: wall coasts win
            # via filtered targets / wall-first pools above.
            prefer_hosts = None if existing else list(others)
            picked = None
            for pool in pools:
                picked = _pick_square_tie(
                    pool, keep_fill, seen, rules, peel_frame=peel_frame,
                    hosts=prefer_hosts)
                if picked is not None:
                    break
            if picked is None:
                break
            # Emit onto *seen* first so firm rejects cannot leak into *out*.
            before_n = _sol_stats.weed_path_stats(seen)['segments']
            _sol_emit._add_seg(seen, picked, 0.0, keep_path=keep_fill, report=False)
            if _sol_stats.weed_path_stats(seen)['segments'] <= before_n:
                break
            _sol_emit._add_seg(out, picked, 0.0, keep_path=keep_fill)
    return out
