# -*- coding: utf-8 -*-
"""Joins until one island remains."""
from __future__ import division

import math

from ..qt import QPainterPath
from ..keep import _path_area

from .cluster import _HANGING_HEIGHT
from . import cluster as _sol_cluster
from . import cluster_bays as _sol_cluster_bays
from . import corridors as _sol_corridors
from . import emit as _sol_emit
from . import gaps as _sol_gaps
from . import geom as _sol_geom
from . import ties as _sol_ties


def _fuse_bridge(pa, pb, standoff, keep_fill, work, min_cut, container):
    """Keep-to-keep join at the chosen anchors (exact endpoints)."""
    _ = standoff
    return _sol_gaps._bridge_seg(pa, pb, 0.0, keep_fill, work, min_cut, container)


def _bodies_touch(path_a, path_b, tol=1.0):
    """True if two keep outlines already meet (no weed cut needed)."""
    pair = _sol_geom._nearest_pair(path_a, path_b)
    return pair is not None and pair[2] <= tol


def _blocker_is_high(path_a, path_b, others):
    """True if gap blockers sit in the upper half of the alley."""
    ra, rb = path_a.boundingRect(), path_b.boundingRect()
    mid_y = 0.5 * (
        max(ra.top(), rb.top()) + min(ra.bottom(), rb.bottom()))
    ys = []
    for o in others:
        if o is None or o.isEmpty():
            continue
        # Reuse the gap test: only count bodies that actually block.
        if not _sol_gaps._gap_blocked(path_a, path_b, [o]):
            continue
        ys.append(o.boundingRect().center().y())
    if not ys:
        return True
    return (sum(ys) / float(len(ys))) < mid_y


def _fuse_kind(path_a, path_b, others, cluster=None):
    """How two islands join, or None if this pair should be skipped."""
    if _bodies_touch(path_a, path_b):
        return 'touch'
    if _sol_cluster._is_stacked_satellite(path_a, path_b) or _sol_cluster._is_stacked_satellite(
            path_b, path_a):
        return 'satellite'
    a_use = _sol_cluster._with_stacked_satellites(path_a, cluster) if cluster else path_a
    b_use = _sol_cluster._with_stacked_satellites(path_b, cluster) if cluster else path_b
    block_others = []
    for o in others or []:
        if o is None or o is path_a or o is path_b:
            continue
        if o is a_use or o is b_use:
            continue
        if _sol_cluster._is_stacked_satellite(o, path_a) or _sol_cluster._is_stacked_satellite(
                o, path_b):
            continue
        block_others.append(o)
    if a_use is not path_a or b_use is not path_b:
        if _bodies_touch(a_use, b_use):
            return 'touch'
    if _sol_gaps._gap_blocked(a_use, b_use, block_others):
        if _sol_cluster._is_hanging(a_use, b_use):
            return None
        # Hanging/compact blockers are chain links — do not around-fuse
        # a long bypass over them (quote alley → O stub class).
        if _gap_blockers_are_ticks(a_use, b_use, block_others, clus=cluster):
            return None
        return 'around'
    if _sol_corridors._is_corridor_pair(a_use, b_use):
        return 'corridor'
    if _sol_cluster._is_hanging(a_use, b_use):
        return 'hanging'
    return 'bridge'


def _gap_blockers_are_ticks(path_a, path_b, others, clus=None):
    """True if every body in the a–b gap is hanging or compact vs the pair."""
    if not others:
        return False
    cluster = clus if clus else ([path_a, path_b] + list(others))
    host_h = max(path_a.boundingRect().height(), path_b.boundingRect().height())
    saw = False
    for o in others:
        if o is None or o.isEmpty():
            continue
        if not _sol_gaps._gap_blocked(path_a, path_b, [o]):
            continue
        saw = True
        if _sol_ties._is_compact_island(o, cluster):
            continue
        if host_h > 1e-6 and o.boundingRect().height() < _HANGING_HEIGHT * host_h:
            continue
        return False
    return saw


def _apply_fuse(kind, path_a, path_b, keep_fill, work, standoff, min_cut,
                container, others=None, max_chunk=None, fork_mouths=None,
                cluster=None, rules=None, against=None, peel_frame=None):
    if kind == 'touch':
        return []
    clus = cluster if cluster else [path_a, path_b]
    compact_a = _sol_ties._is_compact_island(path_a, clus)
    compact_b = _sol_ties._is_compact_island(path_b, clus)
    if compact_a or compact_b:
        # Square ties own speck geometry; always merge the group here.
        return []
    a_use = _sol_cluster._with_stacked_satellites(path_a, clus)
    b_use = _sol_cluster._with_stacked_satellites(path_b, clus)
    if kind == 'corridor':
        return _sol_corridors._seal_corridor_pair(
            path_a, path_b, keep_fill, work, standoff, min_cut, container,
            max_chunk=max_chunk, fork_mouths=fork_mouths, cluster=cluster,
            rules=rules, against=against, peel_frame=peel_frame)
    pair = None
    if kind in ('hanging', 'around'):
        top = True
        block_others = []
        for o in others or []:
            if o is None:
                continue
            if _sol_cluster._is_stacked_satellite(o, path_a) or _sol_cluster._is_stacked_satellite(
                    o, path_b):
                continue
            block_others.append(o)
        if kind == 'around' and block_others:
            top = not _blocker_is_high(a_use, b_use, block_others)
        elif kind == 'hanging':
            ha, hb = a_use, b_use
            if ha.boundingRect().height() > hb.boundingRect().height():
                ha, hb = hb, ha
            top = ha.boundingRect().center().y() < hb.boundingRect().center().y()
            a_use, b_use = ha, hb
        mouths = _sol_gaps._gap_mouths(path_a, path_b, cluster=clus)
        if mouths:
            if top:
                pair = min(mouths, key=lambda m: 0.5 * (m[0].y() + m[1].y()))
            else:
                pair = max(mouths, key=lambda m: 0.5 * (m[0].y() + m[1].y()))
        if pair is None:
            pair = _sol_cluster_bays._gutter_pair(a_use, b_use, top)
    if pair is None:
        pair = _sol_geom._nearest_pair(a_use, b_use)
    if pair is None:
        return None
    ax, ay = _sol_gaps._dominant_gap_axis(a_use, b_use)
    span = float(pair[2]) if len(pair) > 2 else math.hypot(
        pair[1].x() - pair[0].x(), pair[1].y() - pair[0].y())
    hit_t = max(32.0, 2.0 * span)
    pa, pb = _sol_corridors._order_mouth_to_paths(pair[0], pair[1], a_use, b_use)
    qa, qb = _sol_gaps._axis_hit_pair(pa, pb, ax, ay, a_use, b_use, max_t=hit_t)
    seg = _sol_gaps._mouth_seal(
        a_use, b_use, qa, qb, ax, ay, hit_t, standoff, keep_fill,
        work, min_cut, container, rules=rules, against=against,
        peel_frame=peel_frame, near_mouth=True)
    if seg is not None:
        return [seg]
    seg = _fuse_bridge(
        pa, pb, standoff, keep_fill, work, min_cut, container)
    if seg is None or not _sol_gaps._seg_spans_pair(seg, a_use, b_use):
        return None
    if rules is not None:
        emit_keep = keep_fill if keep_fill is not None else a_use
        if not _sol_emit._seg_emit_ok(
                seg, emit_keep, against, rules, peel_frame=peel_frame):
            if not _sol_emit._seg_forced_ok(
                    seg, emit_keep, against, rules, peel_frame=peel_frame):
                return None
    return [seg]


def _group_is_hanging(small_bodies, host):
    """True if every body in *small_bodies* is short vs *host*."""
    hh = host.boundingRect().height()
    if hh < 1e-6:
        return False
    for b in small_bodies:
        if b.boundingRect().height() >= _HANGING_HEIGHT * hh:
            return False
    return True


def _groups_fuse_choice(bodies_a, bodies_b, cluster):
    """Nearest allowed join across two groups. (dist, kind, a, b) or None."""
    cands = []
    for a in bodies_a:
        for b in bodies_b:
            pair = _sol_geom._nearest_pair(a, b)
            if pair is None:
                continue
            cands.append((pair[2], a, b))
    cands.sort(key=lambda t: t[0])
    def sat_of(body, group):
        return any(
            _sol_cluster._is_stacked_satellite(body, h) for h in group if h is not body)

    best = None
    for dist, a, b in cands:
        if sat_of(a, bodies_a) or sat_of(b, bodies_b):
            continue
        others = [c for c in cluster if c is not a and c is not b]
        kind = _fuse_kind(a, b, others, cluster=cluster)
        if kind is None:
            continue
        if kind == 'hanging':
            hang = a if a.boundingRect().height() <= b.boundingRect().height() else b
            host = b if hang is a else a
            hang_group = bodies_a if hang in bodies_a else bodies_b
            if not _group_is_hanging(hang_group, host):
                continue
        pri = 0 if kind == 'satellite' else 1
        if (_sol_ties._is_compact_island(a, cluster)
                or _sol_ties._is_compact_island(b, cluster)):
            pri = 2
        if best is None or (pri, dist) < (best[0], best[1]):
            best = (pri, dist, kind, a, b)
    if best is None:
        return None
    return best[1], best[2], best[3], best[4]


def _agglomerate_islands(cluster, keep_fill, work, standoff, min_cut,
                         container, max_chunk=None, rules=None,
                         peel_frame=None, against=None):
    """Smallest island first: cut to another object until one island remains."""
    n = len(cluster)
    groups = [[i] for i in range(n)]
    out = QPainterPath()
    seen = QPainterPath()
    if against is not None:
        seen.addPath(against)
    sat_ids = set()
    fork_mouths = _sol_corridors._fork_branch_mouths(cluster)

    def area_of(g):
        return sum(max(_path_area(cluster[i]), 1e-6) for i in g)

    guard = 0
    while guard < n * n:
        live = [k for k, g in enumerate(groups) if g]
        if len(live) <= 1:
            break
        guard += 1
        live.sort(key=lambda k: (area_of(groups[k]), min(groups[k])))
        fused = False
        for gi in live:
            best = None
            ba = [cluster[i] for i in groups[gi]]
            for gj in live:
                if gj == gi:
                    continue
                bb = [cluster[i] for i in groups[gj]]
                found = _groups_fuse_choice(ba, bb, cluster)
                if found is None:
                    continue
                dist, kind, pa, pb = found
                pri = 0 if kind == 'satellite' else 1
                if (_sol_ties._is_compact_island(pa, cluster)
                        or _sol_ties._is_compact_island(pb, cluster)):
                    pri = 2
                if best is None or (pri, dist) < (best[0], best[1]):
                    best = (pri, dist, gj, kind, pa, pb)
            if best is None:
                continue
            _pri, _dist, gj, kind, pa, pb = best
            others = [c for c in cluster if c is not pa and c is not pb]
            segs = _apply_fuse(
                kind, pa, pb, keep_fill, work, standoff, min_cut, container,
                others=others, max_chunk=max_chunk, fork_mouths=fork_mouths,
                cluster=cluster, rules=rules, against=seen,
                peel_frame=peel_frame)
            if segs is None:
                continue
            for seg in segs:
                _sol_emit._add_seg(out, seg, 0.0, keep_path=keep_fill)
                _sol_emit._add_seg(seen, seg, 0.0, keep_path=keep_fill, report=False)
            if kind == 'satellite':
                for i in groups[gi]:
                    if any(_sol_cluster._is_stacked_satellite(cluster[i], h)
                           for h in [cluster[j] for j in groups[gj]]):
                        sat_ids.add(i)
                for j in groups[gj]:
                    if any(_sol_cluster._is_stacked_satellite(cluster[j], h)
                           for h in [cluster[i] for i in groups[gi]]):
                        sat_ids.add(j)
            groups[gi] = groups[gi] + groups[gj]
            groups[gj] = []
            fused = True
            break
        if not fused:
            break
    live_groups = [g for g in groups if g]
    return out, live_groups, sat_ids
