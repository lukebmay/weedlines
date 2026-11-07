# -*- coding: utf-8 -*-
"""Residual open waste, and it emits no cuts."""
from __future__ import division

import math
from collections import namedtuple

from ..qt import QPainterPath, QPointF
from ..keep import (
    even_odd_keep_fill,
    list_closed_subpaths,
    padded_work_rect,
    _nest_closed_paths,
    _path_centroid,
)

from .rules import (
    DEFAULT_CHANNEL_STANDOFF,
    DEFAULT_CLEARANCE,
    DEFAULT_COLLAR,
    DEFAULT_DELICATE_ANGLE_DEG,
    DEFAULT_MIN_CUT,
    DEFAULT_PENINSULA_RATIO,
)
from .ties import _MIN_COMPACT_TIES
from . import agglomerate as _sol_agglomerate
from . import bay as _sol_bay
from . import clipper as _sol_clipper
from . import cluster as _sol_cluster
from . import cluster_bays as _sol_cluster_bays
from . import corridors as _sol_corridors
from . import gaps as _sol_gaps
from . import geom as _sol_geom
from . import ties as _sol_ties


ResidualWasteTrap = namedtuple(
    'ResidualWasteTrap',
    ('kind', 'x', 'y', 'depth', 'mouth', 'rho', 'tip_count'))


def _waste_grid(work, step):
    sx = work.left()
    sy = work.top()
    nx = int(math.floor(work.width() / float(step))) + 1
    ny = int(math.floor(work.height() / float(step))) + 1

    def cell(p):
        return (int(round((p.x() - sx) / step)),
                int(round((p.y() - sy) / step)))

    def world(ix, iy):
        return QPointF(sx + (ix + 0.5) * step, sy + (iy + 0.5) * step)

    return nx, ny, cell, world


def _weed_blocks_point(px, py, segs, tol):
    for x0, y0, x1, y1 in segs:
        if _sol_geom._point_seg_dist(px, py, x0, y0, x1, y1) < tol:
            return True
    return False


def _mouth_covered_by_weeds(pa, pb, segs, tol):
    """True when a weed already sits on the neck (seal present)."""
    x0, y0, x1, y1 = pa.x(), pa.y(), pb.x(), pb.y()
    for t in (0.25, 0.5, 0.75):
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * t
        if _weed_blocks_point(x, y, segs, tol):
            return True
    return False


def _flood_collar_peel(keep_fill, weed_path, work, collar_rings, step):
    """Waste cells reachable from collar-adjacent land (weeds + keep = walls)."""
    segs = list(_sol_geom._iter_line_segs(weed_path))
    wall = 0.65 * step
    seed_r = 2.0 * step
    nx, ny, cell, world = _waste_grid(work, step)

    def blocked(p):
        if not work.contains(p):
            return True
        if (keep_fill is not None and not keep_fill.isEmpty()
                and keep_fill.contains(p)):
            return True
        return _weed_blocks_point(p.x(), p.y(), segs, wall)

    stack = []
    if collar_rings:
        for iy in range(ny):
            for ix in range(nx):
                p = world(ix, iy)
                if blocked(p):
                    continue
                hit = _sol_geom._nearest_on_rings(p.x(), p.y(), collar_rings)
                if hit is None or hit[2] > seed_r:
                    continue
                stack.append((ix, iy))

    seen = set()
    while stack:
        ix, iy = stack.pop()
        if (ix, iy) in seen:
            continue
        if ix < 0 or iy < 0 or ix >= nx or iy >= ny:
            continue
        p = world(ix, iy)
        if blocked(p):
            continue
        seen.add((ix, iy))
        stack.extend((
            (ix + 1, iy), (ix - 1, iy), (ix, iy + 1), (ix, iy - 1)))
    return seen, cell, blocked, segs


def _probe_in_peel(px, py, peel, cell, blocked):
    """True when this exact waste point is in the collar peel (no neighbor hop)."""
    p = QPointF(px, py)
    if blocked(p):
        return False
    return cell(p) in peel


def _step_into_bay(left, right, deep, step):
    """A waste probe from the valley toward the mouth."""
    mx = 0.5 * (left.x() + right.x())
    my = 0.5 * (left.y() + right.y())
    dx, dy = mx - deep.x(), my - deep.y()
    ln = math.hypot(dx, dy)
    if ln < 1e-9:
        return mx, my
    t = min(max(step, 0.35 * ln), 0.55 * ln)
    return deep.x() + dx / ln * t, deep.y() + dy / ln * t


def _make_residual_trap(kind, x, y, depth, mouth, pts, waste_dir=None):
    m = _sol_bay._frontier_run_metrics(pts, waste_dir=waste_dir)
    return ResidualWasteTrap(
        kind, float(x), float(y), float(depth), float(mouth),
        m.rho, m.tip_count)


def residual_waste_traps(keep_path,
                         weed_path,
                         work=None,
                         padding=None,
                         step=1.5,
                         collar=None,
                         clearance=None,
                         min_cut=None,
                         peninsula_ratio=None,
                         delicate_angle_deg=None):
    """Residual D007 waste traps still open after *weed_path*.

    Land = keep, water = waste (D007). Weeds are walls. Seeds are waste
    cells next to the isolation collar. A trap is a pocket, cluster bay,
    or channel core that still meets ``_bay_should_seal`` /
    ``_peninsula_should_detach`` and remains reachable from those seeds.
    Keep-enclosed holes and keep-tip valleys are not traps.

    Returns a list of ``ResidualWasteTrap``.
    """
    if keep_path is None or keep_path.isEmpty():
        return []
    if work is None:
        pad = padding if padding is not None else [10.0, 10.0, 10.0, 10.0]
        work = padded_work_rect(keep_path, pad)
    if work is None or work.isEmpty():
        return []
    step = max(float(step), 0.5)
    collar_margin = float(collar if collar is not None else DEFAULT_COLLAR)
    clearance = float(clearance if clearance is not None else DEFAULT_CLEARANCE)
    collar_margin = max(collar_margin, clearance, 1e-6)
    min_cut = float(min_cut if min_cut is not None else DEFAULT_MIN_CUT)
    standoff = max(clearance, DEFAULT_CHANNEL_STANDOFF)
    ratio = (DEFAULT_PENINSULA_RATIO if peninsula_ratio is None
             else float(peninsula_ratio))
    delicate = float(
        delicate_angle_deg if delicate_angle_deg is not None
        else DEFAULT_DELICATE_ANGLE_DEG)
    keep_fill = even_odd_keep_fill(keep_path)
    if keep_fill.isEmpty():
        keep_fill = QPainterPath(keep_path)
    weed_path = weed_path if weed_path is not None else QPainterPath()
    rings = _sol_clipper._enclosure_collar_rings(keep_path, collar_margin)
    peel, cell, blocked, segs = _flood_collar_peel(
        keep_fill, weed_path, work, rings, step)
    wall = 0.65 * step
    closed = list_closed_subpaths(keep_path)
    if not closed:
        return []
    nodes = _nest_closed_paths(closed)
    traps = []
    seen_at = set()

    def add_trap(trap):
        key = (trap.kind, round(trap.x, 1), round(trap.y, 1))
        if key in seen_at:
            return
        seen_at.add(key)
        traps.append(trap)

    min_width = 2.0 * standoff + min_cut
    min_depth = _sol_bay._bay_min_depth(standoff)
    for cluster, _container in _sol_cluster._enclosure_groups(nodes, collar_margin):
        bodies = [b for b in cluster if b is not None and not b.isEmpty()]
        for body in bodies:
            tips = _sol_bay._deep_keep_peninsula_tips(body, delicate)
            for left, right, deep, run in _sol_bay._hull_bay_mouths(
                    body, min_depth, min_width):
                mouth_w = math.hypot(
                    right.x() - left.x(), right.y() - left.y())
                depth = _sol_geom._point_seg_dist(
                    deep.x(), deep.y(), left.x(), left.y(),
                    right.x(), right.y())
                waste_dir = _sol_bay._bay_waste_dir(left, right, deep)
                if not _sol_bay._bay_should_seal(
                        left, right, deep, run, depth=depth,
                        mouth_w=mouth_w, ratio=ratio):
                    continue
                if _sol_bay._mouth_between_keep_tips(left, right, tips, tol=2.0):
                    continue
                px, py = _step_into_bay(left, right, deep, step)
                if not _probe_in_peel(px, py, peel, cell, blocked):
                    continue
                add_trap(_make_residual_trap(
                    'pocket', px, py, depth, mouth_w, run,
                    waste_dir=waste_dir))
        n = len(bodies)
        for i in range(n):
            for j in range(i + 1, n):
                a, b = bodies[i], bodies[j]
                if _sol_agglomerate._bodies_touch(a, b):
                    continue
                if (_sol_cluster._is_stacked_satellite(a, b)
                        or _sol_cluster._is_stacked_satellite(b, a)):
                    continue
                if ((_sol_ties._is_compact_island(a, bodies)
                        or _sol_ties._is_compact_island(b, bodies))):
                    speck = a if _sol_ties._is_compact_island(a, bodies) else b
                    tied_tgts = [x for x in bodies if x is not speck]
                    # One tie is not enough — waste can still fork around.
                    if _sol_ties._compact_tie_count(
                            weed_path, speck, tied_tgts) >= _MIN_COMPACT_TIES:
                        continue
                others = [bodies[k] for k in range(n) if k != i and k != j]
                if _sol_gaps._gap_blocked(a, b, others):
                    # Majors may still need a residual trap when only
                    # well-tied ticks occupy the AABB (seal pass handles it).
                    if not (_sol_gaps._gap_blocked_only_by_tied_compacts(
                            a, b, others, bodies, weed_path)
                            and not _sol_ties._is_compact_island(a, bodies)
                            and not _sol_ties._is_compact_island(b, bodies)):
                        continue
                if _sol_corridors._is_corridor_pair(a, b):
                    core = _sol_corridors._channel_core(a, b)
                    if core is None:
                        continue
                    mx = 0.25 * (
                        core.pa0.x() + core.pb0.x()
                        + core.pa1.x() + core.pb1.x())
                    my = 0.25 * (
                        core.pa0.y() + core.pb0.y()
                        + core.pa1.y() + core.pb1.y())
                    if not _probe_in_peel(mx, my, peel, cell, blocked):
                        continue
                    run = _sol_cluster_bays._facing_frontier_pts(a, b)
                    if not _sol_bay._peninsula_should_detach(
                            core.length, core.width, run, ratio=ratio):
                        continue
                    add_trap(_make_residual_trap(
                        'channel', mx, my, core.length, core.width, run))
                    continue
                mouths = _sol_gaps._gap_mouths(a, b)
                if not mouths:
                    continue
                width = _sol_cluster_bays._cluster_gap_width(a, b, mouths)
                depth = _sol_cluster_bays._cluster_gap_depth(a, b, mouths)
                run = _sol_cluster_bays._facing_frontier_pts(a, b)
                if not _sol_bay._peninsula_should_detach(
                        depth, width, run, ratio=ratio):
                    continue
                if _sol_cluster._is_hanging(a, b):
                    mouth = _sol_cluster_bays._hanging_pocket_mouth(a, b, bodies, mouths)
                else:
                    mouth = _sol_cluster_bays._open_side_bay_mouth(mouths)
                if mouth is None:
                    continue
                pa, pb, _dist = mouth
                if _mouth_covered_by_weeds(pa, pb, segs, max(wall, 1.5)):
                    continue
                mx = 0.5 * (pa.x() + pb.x())
                my = 0.5 * (pa.y() + pb.y())
                if len(mouths) >= 2:
                    other = mouths[0] if mouth is mouths[-1] else mouths[-1]
                    ix = _sol_cluster_bays._gap_mouth_mid_x(other) - mx
                    iy = _sol_cluster_bays._gap_mouth_mid_y(other) - my
                else:
                    ca, cb = _path_centroid(a), _path_centroid(b)
                    ix = 0.5 * (ca.x() + cb.x()) - mx
                    iy = 0.5 * (ca.y() + cb.y()) - my
                ln = math.hypot(ix, iy)
                if ln > 1e-9:
                    px = mx + ix / ln * step
                    py = my + iy / ln * step
                else:
                    px, py = mx, my
                if not _probe_in_peel(px, py, peel, cell, blocked):
                    continue
                add_trap(_make_residual_trap(
                    'cluster', px, py, depth, width, run))
    return traps
