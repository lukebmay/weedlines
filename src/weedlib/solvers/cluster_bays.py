# -*- coding: utf-8 -*-
"""Multi-body bays and hanging gutters."""
from __future__ import division

import math

from ..qt import QPainterPath
from ..keep import (
    _polyline_points,
    _signed_area,
    _unique_ring,
)

from .rules import DEFAULT_PENINSULA_RATIO
from . import bay as _sol_bay
from . import frame_peninsulas as _sol_frame_peninsulas
from . import geom as _sol_geom
from . import peel as _sol_peel
from . import ties as _sol_ties


def _gutter_pair(hanging, major, top):
    """Outline pair near the outer ends, preferring the true gutter."""
    pairs = _sol_geom._outline_pairs(hanging, major)
    if not pairs:
        return None
    hr = hanging.boundingRect()
    mr = major.boundingRect()
    band = max(0.45 * max(hr.height(), mr.height()), 4.0)
    if top:
        y_ref = min(hr.top(), mr.top())
    else:
        y_ref = max(hr.bottom(), mr.bottom())
    best = None
    best_score = None
    for pa, pb, d in pairs:
        my = 0.5 * (pa.y() + pb.y())
        off = abs(my - y_ref)
        if off > band:
            continue
        score = d + 2.0 * off
        if best_score is None or score < best_score:
            best_score = score
            best = (pa, pb, d)
    return best if best is not None else pairs[0]


# Hanging marks in a wide major gap: leftover wrap at the hanging's end.
_WIDE_GAP_VS_HEIGHT = 0.8
_WIDE_GAP_MIN = 18.0


def _leftover_hanging_gutters(cluster, keep_fill, work, standoff, min_cut,
                              container, against=None, rules=None,
                              peel_frame=None):
    """If a wide alley still wraps past hanging marks, add the missing gutters."""
    from . import agglomerate as _sol_agglomerate, emit as _sol_emit, gaps as _sol_gaps
    out = QPainterPath()
    seen = QPainterPath()
    if against is not None:
        seen.addPath(against)
    bodies = [b for b in cluster if b is not None and not b.isEmpty()]
    if len(bodies) < 3:
        return out
    max_h = max(b.boundingRect().height() for b in bodies)
    if max_h < 1e-6:
        return out
    majors = [b for b in bodies if b.boundingRect().height() >= 0.5 * max_h]
    hangs = [b for b in bodies if b.boundingRect().height() < 0.5 * max_h]
    if len(majors) < 2 or not hangs:
        return out
    majors = sorted(majors, key=lambda b: b.boundingRect().center().x())
    wide = max(_WIDE_GAP_VS_HEIGHT * max_h, _WIDE_GAP_MIN)
    for left, right in zip(majors, majors[1:]):
        lr, rr = left.boundingRect(), right.boundingRect()
        gap = max(0.0, rr.left() - lr.right(), lr.left() - rr.right())
        if gap < wide - 1e-9:
            continue
        l_edge, r_edge = lr.right(), rr.left()
        if l_edge > r_edge:
            l_edge, r_edge = r_edge, l_edge
        mid_y = 0.5 * (lr.center().y() + rr.center().y())
        in_gap = []
        for hang in hangs:
            hb = hang.boundingRect()
            if not (l_edge < hb.center().x() < r_edge):
                continue
            if hb.center().y() >= mid_y:
                continue
            in_gap.append(hang)
        if not in_gap:
            continue
        for major in (left, right):
            def _hang_dist(h, m=major):
                pair = _sol_geom._nearest_pair(h, m)
                return pair[2] if pair else 1e9
            hang = min(in_gap, key=_hang_dist)
            # Already fused during agglomerate / bay — no second gutter.
            if _sol_gaps._pair_join_already_effective(seen, hang, major, bodies):
                continue
            pair = _gutter_pair(hang, major, True)
            if pair is None:
                continue
            seg = _sol_agglomerate._fuse_bridge(
                pair[0], pair[1], standoff, keep_fill, work,
                min_cut, container)
            if seg is None:
                continue
            if rules is not None:
                if not _sol_emit._seg_emit_ok(
                        seg, keep_fill, seen, rules, peel_frame=peel_frame):
                    if not _sol_emit._seg_forced_ok(
                            seg, keep_fill, seen, rules,
                            peel_frame=peel_frame):
                        continue
            if _sol_emit._seg_redundant(seen, seg) or _sol_geom._seg_crosses_path(seen, seg):
                continue
            _sol_emit._add_seg(out, seg, 0.0, keep_path=keep_fill)
            _sol_emit._add_seg(seen, seg, 0.0, keep_path=keep_fill, report=False)
    return out


def _gap_mouth_mid_y(mouth):
    pa, pb = mouth[0], mouth[1]
    return 0.5 * (pa.y() + pb.y())


def _gap_mouth_mid_x(mouth):
    pa, pb = mouth[0], mouth[1]
    return 0.5 * (pa.x() + pb.x())


def _cluster_gap_width(path_a, path_b, mouths):
    """Keep-to-keep width of a non-corridor gap."""
    from . import corridors as _sol_corridors
    facing = _sol_corridors._corridor_facing(path_a, path_b)
    if facing is not None and facing[3] > 1e-6:
        return facing[3]
    if not mouths:
        return 0.0
    return sum(float(m[2]) for m in mouths) / float(len(mouths))


def _cluster_gap_depth(path_a, path_b, mouths):
    """How far waste runs along the gap (mouth span, else facing overlap)."""
    from . import corridors as _sol_corridors
    if len(mouths) >= 2:
        m0x = _gap_mouth_mid_x(mouths[0])
        m0y = _gap_mouth_mid_y(mouths[0])
        m1x = _gap_mouth_mid_x(mouths[-1])
        m1y = _gap_mouth_mid_y(mouths[-1])
        span = math.hypot(m1x - m0x, m1y - m0y)
        if span > 1e-6:
            return span
    facing = _sol_corridors._corridor_facing(path_a, path_b)
    if facing is None:
        return 0.0
    return float(facing[0])


def _facing_frontier_pts(path_a, path_b):
    """One keep wall of the facing band, ordered along the alley."""
    from . import gaps as _sol_gaps
    pairs = _sol_geom._outline_pairs(path_a, path_b)
    if not pairs:
        return []
    dmin = pairs[0][2]
    slack = max(2.0, 0.25 * dmin)
    facing = [(pa, pb, d) for pa, pb, d in pairs if d <= dmin + slack]
    if not facing:
        return []
    ux, uy = _sol_gaps._dominant_gap_axis(path_a, path_b)
    tx, ty = -uy, ux

    def along(pa, pb):
        mx = 0.5 * (pa.x() + pb.x())
        my = 0.5 * (pa.y() + pb.y())
        return mx * tx + my * ty

    facing.sort(key=lambda t: along(t[0], t[1]))
    return [(pa.x(), pa.y()) for pa, _pb, _d in facing]


def _hanging_pocket_mouth(path_a, path_b, cluster, mouths):
    """Inner-end mouth of a hanging mark vs its nearest taller host."""
    from . import cluster as _sol_cluster
    if not mouths or not _sol_cluster._is_hanging(path_a, path_b):
        return None
    short, tall = path_a, path_b
    if short.boundingRect().height() > tall.boundingRect().height():
        short, tall = tall, short
    if _sol_cluster._hanging_host(short, cluster) is not tall:
        return None
    gutter_top = (short.boundingRect().center().y()
                  < tall.boundingRect().center().y())
    y_ref = (short.boundingRect().bottom() if gutter_top
             else short.boundingRect().top())
    return min(mouths, key=lambda m: abs(_gap_mouth_mid_y(m) - y_ref))


def _snap_hanging_mouth_to_corner(mouth, path_a, path_b):
    """Move the short-mark end of *mouth* to the nearest outline corner.

    Gap mouths often sit mid-edge along the short mark's base, so a seal
    runs nearly parallel to that base (extremely shallow angle). A corner
    join peels cleanly and matches the agglomerate gutter style.
    """
    from . import cluster as _sol_cluster
    if mouth is None:
        return None
    pa, pb, dist = mouth[0], mouth[1], float(mouth[2])
    if not _sol_cluster._is_hanging(path_a, path_b):
        return mouth
    short, tall = path_a, path_b
    if short.boundingRect().height() > tall.boundingRect().height():
        short, tall = tall, short
    # Which endpoint sits on the short mark.
    if _sol_geom._point_near_path(pa.x(), pa.y(), short, tol=2.5):
        ps, pt = pa, pb
    elif _sol_geom._point_near_path(pb.x(), pb.y(), short, tol=2.5):
        ps, pt = pb, pa
    else:
        return mouth
    pts = _unique_ring(_polyline_points(short, max_pts=64))
    if len(pts) < 3:
        return mouth
    # Prefer convex corners (turn ≥ 40°) near the pocket end.
    best = None
    best_score = None
    n = len(pts)
    ccw = _signed_area(pts) > 0
    for i in range(n):
        p0, p1, p2 = pts[(i - 1) % n], pts[i], pts[(i + 1) % n]
        cross = ((p1.x() - p0.x()) * (p2.y() - p1.y())
                 - (p1.y() - p0.y()) * (p2.x() - p1.x()))
        is_convex = (cross > 0) == ccw
        turn = _sol_geom._angle_turn_deg(p0, p1, p2)
        if not is_convex or turn < 40.0:
            continue
        d_end = math.hypot(p1.x() - ps.x(), p1.y() - ps.y())
        d_tall = math.hypot(p1.x() - pt.x(), p1.y() - pt.y())
        score = d_end + 0.25 * d_tall
        if best_score is None or score < best_score:
            best_score = score
            best = p1
    if best is None:
        return mouth
    # Keep short→tall order matching the original mouth ends.
    if ps is pa:
        return (best, pt, math.hypot(best.x() - pt.x(), best.y() - pt.y()))
    return (pt, best, math.hypot(best.x() - pt.x(), best.y() - pt.y()))


def _hanging_has_underarm_wrap(short, host, cluster, clear=8.0):
    """True if open waste continues past the short mark away from *host*.

    A hanging mark beside a close neighbor (apostrophe–s, quote pairs)
    only needs the outer gutter fuse. A mark floating in a wide major gap
    (comma between stems) needs an inner pocket so waste cannot wrap under
    the arm. Any neighboring body counts as a blocker (including other
    hanging marks), not only tall majors.
    """
    if short is None or host is None or short.isEmpty() or host.isEmpty():
        return False
    sr = short.boundingRect()
    if sr.center().x() >= host.boundingRect().center().x():
        edge = sr.right()
        for b in cluster:
            if b is short or b is host or b is None or b.isEmpty():
                continue
            br = b.boundingRect()
            if br.left() >= edge - 1e-6 and br.left() - edge < clear:
                return False
        return True
    edge = sr.left()
    for b in cluster:
        if b is short or b is host or b is None or b.isEmpty():
            continue
        br = b.boundingRect()
        if br.right() <= edge + 1e-6 and edge - br.right() < clear:
            return False
    return True


def _open_side_bay_mouth(mouths):
    """One open-side mouth; larger Y is the wrap-under side in Qt."""
    if not mouths:
        return None
    return max(mouths, key=lambda m: (_gap_mouth_mid_y(m), _gap_mouth_mid_x(m)))


def _cluster_bay_seals(cluster, keep_fill, work, standoff, min_cut,
                       container, against=None, peninsula_ratio=None,
                       rules=None, peel_frame=None, collar_rings=None):
    """Seal multi-body waste bays that no single-body hull mouth sees.

    Skip gaps agglomerate / corridor already joined (including satellite
    host already sealed to the neighbor). Hanging marks use a gutter
    corner join, not a mouth that runs parallel to the short mark's base.
    """
    from . import agglomerate as _sol_agglomerate, cluster as _sol_cluster, corridors as _sol_corridors, emit as _sol_emit, gaps as _sol_gaps
    out = QPainterPath()
    seen = QPainterPath()
    if against is not None:
        seen.addPath(against)
    ratio = (DEFAULT_PENINSULA_RATIO if peninsula_ratio is None
             else float(peninsula_ratio))
    wall_rings = _sol_peel._opening_wall_rings(collar_rings, container)
    bodies = [b for b in cluster if b is not None and not b.isEmpty()]
    n = len(bodies)
    if n < 2:
        return out
    for i in range(n):
        for j in range(i + 1, n):
            a, b = bodies[i], bodies[j]
            if _sol_agglomerate._bodies_touch(a, b):
                continue
            if _sol_cluster._is_stacked_satellite(a, b) or _sol_cluster._is_stacked_satellite(b, a):
                continue
            others = [bodies[k] for k in range(n) if k != i and k != j]
            walls = []
            if container is not None and not container.isEmpty():
                walls.append(container)
            if peel_frame is not None and not peel_frame.isEmpty():
                walls.append(peel_frame)
            blocked = _sol_gaps._gap_blocked(a, b, others)
            through_tied = False
            if blocked:
                # Well-tied compact ticks in the AABB must not forever
                # block a major↔major frame-heavier / bottom neck.
                if (_sol_ties._is_compact_island(a, bodies)
                        or _sol_ties._is_compact_island(b, bodies)):
                    continue
                if not _sol_gaps._gap_blocked_only_by_tied_compacts(
                        a, b, others, bodies, seen, walls=walls):
                    continue
                through_tied = True
            # Corridors normally belong to agglomerate; when only tied
            # ticks blocked the gap, still emit one open-end neck here.
            if _sol_corridors._is_corridor_pair(a, b) and not through_tied:
                continue
            # Speck→neighbor when the host alley is already sealed.
            if _sol_gaps._satellite_neighbor_already_sealed(seen, a, b, bodies):
                continue
            mouths = _sol_gaps._gap_mouths(a, b)
            if not mouths:
                continue
            width = _cluster_gap_width(a, b, mouths)
            depth = _cluster_gap_depth(a, b, mouths)
            run = _facing_frontier_pts(a, b)
            if not _sol_bay._peninsula_should_detach(depth, width, run, ratio=ratio):
                continue
            if _sol_cluster._is_hanging(a, b):
                short, tall = a, b
                if short.boundingRect().height() > tall.boundingRect().height():
                    short, tall = tall, short
                # Dot stacked on a stem that already joins the neighbor
                # *near the speck* (same band). A distant host seal does not
                # cover a far pocket.
                if _sol_gaps._satellite_neighbor_already_sealed(seen, a, b, bodies):
                    continue
                mouth = _hanging_pocket_mouth(a, b, bodies, mouths)
                mouth = _snap_hanging_mouth_to_corner(mouth, a, b)
                # Tight close neighbor already fused: skip *shallow* base
                # slides (apostrophe–s ~3 mm gap). Wider hanging gaps still
                # get a pocket even when the cut is nearly horizontal.
                reject_shallow = (
                    _sol_gaps._pair_has_spanning_seal(seen, a, b)
                    and not _hanging_has_underarm_wrap(short, tall, bodies)
                    and width <= 5.0)
            else:
                reject_shallow = False
                if through_tied:
                    # Prefer the frame-heavier open end (usually bottom).
                    top = _sol_frame_peninsulas._frame_open_is_top(a, b, work, wall_rings)
                    mouth = _sol_frame_peninsulas._frame_mouth_pair(a, b, top)
                else:
                    mouth = _open_side_bay_mouth(mouths)
            if mouth is None:
                continue
            # Do not stack on an existing pair join at the same site.
            if _sol_gaps._mouth_near_spanning_seals(seen, a, b, mouth):
                continue
            if _sol_ties._is_compact_island(a, bodies) or _sol_ties._is_compact_island(b, bodies):
                continue
            pa, pb, _dist = mouth
            if through_tied:
                # Open-end chord only — ranked mouth_seal climbs into ticks.
                seg = _sol_agglomerate._fuse_bridge(
                    pa, pb, 0.0, keep_fill, work, min_cut, container)
            else:
                ax, ay = _sol_gaps._dominant_gap_axis(a, b)
                hit_t = max(32.0, 2.0 * max(m[2] for m in mouths))
                seg = _sol_gaps._mouth_seal(
                    a, b, pa, pb, ax, ay, hit_t, standoff, keep_fill,
                    work, min_cut, container, rules=rules, against=seen,
                    peel_frame=peel_frame)
            if seg is None or not _sol_gaps._seg_spans_pair(seg, a, b):
                continue
            if reject_shallow and _seg_parallel_to_short_base(seg, a, b):
                continue
            if _sol_emit._seg_redundant(seen, seg) or _sol_geom._seg_crosses_path(seen, seg):
                continue
            _sol_emit._add_seg(out, seg, 0.0, keep_path=keep_fill)
            _sol_emit._add_seg(seen, seg, 0.0, keep_path=keep_fill, report=False)
    return out


def _seg_parallel_to_short_base(seg, path_a, path_b, deg=18.0):
    """True if *seg* skims along the short mark's top/bottom base.

    Hanging marks are usually upright: a cut that is nearly horizontal at
    the mark's bottom creates the shallow apostrophe→s angle. Reject those
    when an outer gutter already joins the pair.
    """
    from . import cluster as _sol_cluster
    if seg is None or not _sol_cluster._is_hanging(path_a, path_b):
        return False
    short, tall = path_a, path_b
    if short.boundingRect().height() > tall.boundingRect().height():
        short, tall = tall, short
    sx = seg[2] - seg[0]
    sy = seg[3] - seg[1]
    sl = math.hypot(sx, sy)
    if sl < 1e-9:
        return False
    # Upright short mark: base is horizontal → shallow if |sy/sl| is small.
    return abs(sy) / sl <= math.sin(math.radians(deg))
