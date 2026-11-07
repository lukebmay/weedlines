# -*- coding: utf-8 -*-
"""Frame-to-letter bay seals."""
from __future__ import division

import math

from ..qt import QPainterPath

from .rules import DEFAULT_PENINSULA_RATIO
from . import bay as _sol_bay
from . import geom as _sol_geom
from . import ties as _sol_ties


def _frame_chain_bodies(cluster):
    """X-ordered keep bodies with stacked satellites folded into their host.

    Frame-peninsula necks run between consecutive *visible* islands along
    the cluster (stem+dot counts as one, hanging marks stay as links).
    Compact water specks are sealed separately (square ties), not as chain
    links that spawn long parallel rails.
    """
    from . import cluster as _sol_cluster
    bodies = _sol_cluster._x_sorted_bodies(cluster)
    skip = set()
    for b in bodies:
        if _sol_ties._is_compact_island(b, cluster):
            skip.add(id(b))
            continue
        for other in bodies:
            if other is b or id(other) in skip:
                continue
            if _sol_cluster._is_stacked_satellite(b, other):
                skip.add(id(b))
                break
    return [b for b in bodies if id(b) not in skip]


def _frame_open_is_top(path_a, path_b, work, collar_rings=None):
    """Which open end of a side-by-side gap faces more outer-frame waste."""
    # Hanging marks sit in the frame-open wrap; seal at their outer end.
    from . import cluster as _sol_cluster
    if _sol_cluster._is_hanging(path_a, path_b):
        ha, hb = path_a, path_b
        if ha.boundingRect().height() > hb.boundingRect().height():
            ha, hb = hb, ha
        return ha.boundingRect().center().y() < hb.boundingRect().center().y()
    ra, rb = path_a.boundingRect(), path_b.boundingRect()
    top = min(ra.top(), rb.top())
    bot = max(ra.bottom(), rb.bottom())
    if collar_rings:
        # Thicker keep→collar; if both ends are real strips, prefer bottom.
        mx = 0.5 * (ra.center().x() + rb.center().x())
        near_top = _sol_geom._nearest_on_rings(mx, top, collar_rings)
        near_bot = _sol_geom._nearest_on_rings(mx, bot, collar_rings)
        if near_top is not None and near_bot is not None:
            dt, db = float(near_top[2]), float(near_bot[2])
            thick, thin = (dt, db) if dt >= db else (db, dt)
            if thin + 1e-9 >= max(8.0, 0.45 * thick):
                return False
            return dt > db + 1e-9
    if work is None or work.isNull():
        return False
    room_top = top - work.top()
    room_bot = work.bottom() - bot
    return room_top > room_bot + 1e-9


def _frame_mouth_pair(path_a, path_b, top):
    """Keep-to-keep pair at the frame-open end of a gap."""
    from . import cluster_bays as _sol_cluster_bays, gaps as _sol_gaps
    pair = _sol_cluster_bays._gutter_pair(path_a, path_b, top)
    if pair is not None:
        return pair
    mouths = _sol_gaps._gap_mouths(path_a, path_b)
    if not mouths:
        return _sol_geom._nearest_pair(path_a, path_b)
    if top:
        return min(mouths, key=lambda m: _sol_cluster_bays._gap_mouth_mid_y(m))
    return max(mouths, key=lambda m: _sol_cluster_bays._gap_mouth_mid_y(m))


def _frame_peninsula_should_seal(path_a, path_b, mouth, top, ratio):
    """Frame→letter opening is a bay (D007): seal by κ / depth gates."""
    from . import cluster_bays as _sol_cluster_bays
    if mouth is None:
        return False
    pa, pb, width = mouth[0], mouth[1], float(mouth[2])
    if width < 1.5:
        return False
    ra, rb = path_a.boundingRect(), path_b.boundingRect()
    mid_y = 0.5 * (pa.y() + pb.y())
    if top:
        depth = max(ra.bottom(), rb.bottom()) - mid_y
    else:
        depth = mid_y - min(ra.top(), rb.top())
    depth = max(depth, 0.0)
    run = _sol_cluster_bays._facing_frontier_pts(path_a, path_b)
    return _sol_bay._peninsula_should_detach(depth, width, run, ratio=ratio)


def _frame_mouth_on_corridor_core(path_a, path_b, mouth, tol=4.0):
    """True if *mouth* sits on an existing channel-core / facing end seal site."""
    from . import cluster_bays as _sol_cluster_bays, gaps as _sol_gaps
    if mouth is None:
        return False
    mx = _sol_cluster_bays._gap_mouth_mid_x(mouth)
    my = _sol_cluster_bays._gap_mouth_mid_y(mouth)
    for pa, pb, _d in _sol_gaps._gap_mouths(path_a, path_b):
        cx = 0.5 * (pa.x() + pb.x())
        cy = 0.5 * (pa.y() + pb.y())
        if math.hypot(mx - cx, my - cy) <= tol:
            return True
    return False


def _seal_frame_peninsulas(cluster, keep_fill, work, standoff, min_cut,
                           container, against=None, peninsula_ratio=None,
                           collar_rings=None, rules=None, peel_frame=None):
    """Neck-seal frame→letter bays (water from the collar frame into gaps).

    D007: frame openings are multi-body bays (κ / undercut / depth), not
    corridor mouths. Consecutive keep bodies (left→right, satellites
    folded into host) get one seal at the frame-heavier open end when the
    bay should seal. Hanging marks are chain links.

    Do not re-cut a gap the corridor / agglomerate pass already necks: a
    corridor with any spanning seal owns the alley; any pair with a seal
    already near the intended mouth is done.
    """
    from . import agglomerate as _sol_agglomerate, corridors as _sol_corridors, emit as _sol_emit, gaps as _sol_gaps
    out = QPainterPath()
    seen = QPainterPath()
    if against is not None:
        seen.addPath(against)
    ratio = (DEFAULT_PENINSULA_RATIO if peninsula_ratio is None
             else float(peninsula_ratio))
    bodies = _frame_chain_bodies(cluster)
    n = len(bodies)
    if n < 2:
        return out
    for i in range(n - 1):
        a, b = bodies[i], bodies[i + 1]
        if _sol_agglomerate._bodies_touch(a, b):
            continue
        # Compact/tick bodies folded out of the chain still sit in the gap;
        # skip unless those ticks already have ≥2 ties (major neck still ok).
        gap_others = [c for c in cluster if c is not a and c is not b]
        through_tied = False
        if _sol_gaps._gap_blocked(a, b, gap_others):
            walls = []
            if container is not None and not container.isEmpty():
                walls.append(container)
            if peel_frame is not None and not peel_frame.isEmpty():
                walls.append(peel_frame)
            if not _sol_gaps._gap_blocked_only_by_tied_compacts(
                    a, b, gap_others, cluster, seen, walls=walls):
                continue
            through_tied = True
        # Seal the frame-heavier open end (thicker keep→collar waste strip).
        top = _frame_open_is_top(a, b, work, collar_rings)
        mouth = _frame_mouth_pair(a, b, top)
        if mouth is None:
            continue
        if not _frame_peninsula_should_seal(a, b, mouth, top, ratio):
            continue
        # Corridor already sealed (mid or ends) blocks the alley — the
        # open frame waste peels with the collar without another neck.
        if _sol_corridors._is_corridor_pair(a, b) and _sol_gaps._pair_has_spanning_seal(seen, a, b):
            continue
        # Corridor core mouth sites, or any existing pair seal near this
        # open end, already provide the neck.
        if _sol_corridors._is_corridor_pair(a, b) and _frame_mouth_on_corridor_core(
                a, b, mouth):
            continue
        if _sol_gaps._mouth_near_spanning_seals(seen, a, b, mouth, cluster=cluster):
            continue
        pa, pb = mouth[0], mouth[1]
        if through_tied:
            # Open-end chord only — ranked mouth_seal climbs into ticks.
            seg = _sol_agglomerate._fuse_bridge(
                pa, pb, 0.0, keep_fill, work, min_cut, container)
        else:
            ax, ay = _sol_gaps._dominant_gap_axis(a, b)
            hit_t = max(32.0, 2.0 * float(mouth[2]))
            seg = _sol_gaps._mouth_seal(
                a, b, pa, pb, ax, ay, hit_t, standoff, keep_fill, work,
                min_cut, container, rules=rules, against=seen,
                peel_frame=peel_frame, near_mouth=True)
        if seg is None or not _sol_gaps._seg_spans_pair(seg, a, b):
            continue
        if _sol_emit._seg_redundant(seen, seg) or _sol_geom._seg_crosses_path(seen, seg):
            continue
        _sol_emit._add_seg(out, seg, 0.0, keep_path=keep_fill)
        _sol_emit._add_seg(seen, seg, 0.0, keep_path=keep_fill, report=False)
    return out
