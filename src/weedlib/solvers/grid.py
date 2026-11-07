# -*- coding: utf-8 -*-
"""Hatch plus the closed work rectangle."""
from __future__ import division

import math

from ..qt import QPainterPath
from ..keep import (
    even_odd_keep_fill,
    list_closed_subpaths,
    _nest_closed_paths,
    _normalize_padding,
    _padded_rect,
)

from .rules import DEFAULT_GRID_SPACING
from . import clip as _sol_clip
from . import emit as _sol_emit
from . import geom as _sol_geom
from . import rules as _sol_rules


# Grid clip sample gap: snap ends to keep / ortho crossing within this.
_GRID_END_SNAP = 3.5
# Grid hatch only needs nick clearance — island-hop's 5 mm body floor
# drops too many lines in letter counters / tight alleys.
_GRID_BODY_CLEARANCE = 0.75


def grid_weeds(keep_path, padding=None, spacing=DEFAULT_GRID_SPACING,
               rules=None, body_clearance=None, alpha_min=None):
    """Axis-aligned grid over design waste, plus a peel surround rectangle.

    Hatch covers waste (frame interiors, letter counters, gaps between
    islands) and never the vinyl keep itself. When the design already has
    hollow counters / a frame, hatch stays inside the design bbox — outer
    padding is one peel sheet. Solid designs still hatch the padded work
    annulus. A closed rectangle at the work edge always bounds the outer
    scrap so those cuts can be pulled up.

    Grid uses a softer body-clearance floor than island-hop (nick
    protection only); parallel-hug rejection is skipped so coast-parallel
    hatch in waste is kept.
    """
    padding = _normalize_padding(padding)
    spacing = max(float(spacing), 1e-6)
    if rules is None:
        bc = (body_clearance if body_clearance is not None
              else _GRID_BODY_CLEARANCE)
        rules = _sol_rules._cut_rules(bc, alpha_min, None)
    keep_bbox = keep_path.boundingRect()
    work = _padded_rect(keep_bbox, padding)
    keep_fill = even_odd_keep_fill(keep_path)
    closed = list_closed_subpaths(keep_path)
    nodes = _nest_closed_paths(closed)
    has_interior_waste = any(n.get('depth', 0) % 2 == 1 for n in nodes)
    # Framed / hollow keep: grid the counter waste. Solid keep: grid padding.
    hatch_rect = keep_bbox if has_interior_waste else work
    weed = _grid_in_region(
        hatch_rect, keep_fill, spacing, invert_keep=True,
        keep_path=keep_path, rules=rules, grid_mode=True)
    # Accepted hatch. A later pass may drop or shorten it.
    _sol_emit._publish_path_segments(weed)
    surround = QPainterPath()
    surround.addRect(work)
    _sol_emit._add_path_segs(weed, surround, min_cut=1e-6)
    weed = _sol_emit._require_connected_ends(weed, keep_path, tol=2.5, work=work)
    weed = _sol_clip._clip_path_to_rect(weed, work)
    return weed


def _axis_keep_snap(px, py, horizontal, keep_edges, max_snap):
    """Nearest keep outline hit along the grid axis within *max_snap*."""
    best = None
    best_d = None
    for ax, ay, bx, by in keep_edges:
        dx, dy = bx - ax, by - ay
        if horizontal:
            if abs(dy) < 1e-15:
                if abs(ay - py) > 0.15:
                    continue
                lo, hi = (ax, bx) if ax <= bx else (bx, ax)
                qx = max(lo, min(hi, px))
                d = abs(qx - px)
                if 1e-12 < d <= max_snap and (best_d is None or d < best_d):
                    best_d = d
                    best = (qx, py)
                continue
            t = (py - ay) / dy
            if t < -1e-9 or t > 1.0 + 1e-9:
                continue
            t = max(0.0, min(1.0, t))
            qx = ax + t * dx
            if abs((ay + t * dy) - py) > 0.15:
                continue
            d = abs(qx - px)
            if 1e-12 < d <= max_snap and (best_d is None or d < best_d):
                best_d = d
                best = (qx, py)
        else:
            if abs(dx) < 1e-15:
                if abs(ax - px) > 0.15:
                    continue
                lo, hi = (ay, by) if ay <= by else (by, ay)
                qy = max(lo, min(hi, py))
                d = abs(qy - py)
                if 1e-12 < d <= max_snap and (best_d is None or d < best_d):
                    best_d = d
                    best = (px, qy)
                continue
            t = (px - ax) / dx
            if t < -1e-9 or t > 1.0 + 1e-9:
                continue
            t = max(0.0, min(1.0, t))
            qy = ay + t * dy
            if abs((ax + t * dx) - px) > 0.15:
                continue
            d = abs(qy - py)
            if 1e-12 < d <= max_snap and (best_d is None or d < best_d):
                best_d = d
                best = (px, qy)
    return best


def _axis_cross_snap(px, py, horizontal, crosses, max_snap):
    """Snap to nearest orthogonal grid coordinate within *max_snap*."""
    best = None
    best_d = None
    for c in crosses:
        if horizontal:
            d = abs(c - px)
            if 1e-12 < d <= max_snap and (best_d is None or d < best_d):
                best_d = d
                best = (c, py)
        else:
            d = abs(c - py)
            if 1e-12 < d <= max_snap and (best_d is None or d < best_d):
                best_d = d
                best = (px, c)
    return best


def _on_work_edge(px, py, work, tol=1e-6):
    if work is None or work.isNull():
        return False
    return (abs(px - work.left()) <= tol or abs(px - work.right()) <= tol
            or abs(py - work.top()) <= tol
            or abs(py - work.bottom()) <= tol)


def _snap_grid_end(px, py, horizontal, keep_edges, crosses, work,
                   max_snap=_GRID_END_SNAP):
    if _on_work_edge(px, py, work):
        return px, py
    if _sol_emit._point_near_edges(px, py, keep_edges, tol=0.15):
        return px, py
    hit = _axis_keep_snap(px, py, horizontal, keep_edges, max_snap)
    if hit is not None:
        return hit
    hit = _axis_cross_snap(px, py, horizontal, crosses, max_snap)
    if hit is not None:
        return hit
    return px, py


def _snap_grid_seg(seg, horizontal, keep_edges, crosses, work,
                   max_snap=_GRID_END_SNAP):
    x0, y0, x1, y1 = seg
    ax, ay = _snap_grid_end(
        x0, y0, horizontal, keep_edges, crosses, work, max_snap)
    bx, by = _snap_grid_end(
        x1, y1, horizontal, keep_edges, crosses, work, max_snap)
    if math.hypot(bx - ax, by - ay) < 1e-9:
        return None
    return (ax, ay, bx, by)


def _grid_in_region(rect, region_path, spacing, invert_keep,
                   keep_path=None, rules=None, grid_mode=False):
    """Vertical + horizontal lines over rect, clipped by region test."""
    out = QPainterPath()
    if rect.width() <= 0 or rect.height() <= 0:
        return out
    spacing = max(float(spacing), 1e-6)
    x0, y0 = rect.left(), rect.top()
    x1, y1 = rect.right(), rect.bottom()

    xs = []
    ys = []
    v_segs = []
    h_segs = []

    x = x0
    while x <= x1 + 1e-9:
        xs.append(x)
        # One trial hatch line, before any segment of it is accepted.
        _sol_emit._progress_check(line=(x, y0, x, y1))
        v_segs.extend(_sol_clip._clip_line_to_region(
            x, y0, x, y1, region_path, invert_keep=invert_keep))
        x += spacing

    y = y0
    while y <= y1 + 1e-9:
        ys.append(y)
        _sol_emit._progress_check(line=(x0, y, x1, y))
        h_segs.extend(_sol_clip._clip_line_to_region(
            x0, y, x1, y, region_path, invert_keep=invert_keep))
        y += spacing

    if invert_keep and region_path is not None and not region_path.isEmpty():
        keep_edges = _sol_emit._keep_outline_edges(region_path)
        snapped = []
        for seg in v_segs:
            s = _snap_grid_seg(seg, False, keep_edges, ys, rect)
            if s is not None:
                snapped.append(s)
        for seg in h_segs:
            s = _snap_grid_seg(seg, True, keep_edges, xs, rect)
            if s is not None:
                snapped.append(s)
        segs = snapped
    else:
        segs = list(v_segs) + list(h_segs)
    if rules is not None and keep_path is not None:
        kept = []
        for seg in segs:
            if grid_mode:
                # Soft gate: nick clearance + α only (no parallel-hug).
                if not _sol_emit._seg_body_clearance_ok(
                        seg, keep_path, kept, clearance=rules.body_clearance):
                    continue
                if not _sol_emit._seg_alpha_ok(
                        seg, keep_path, alpha_min=rules.alpha_min):
                    continue
                kept.append(seg)
            elif _sol_emit._seg_emit_ok(seg, keep_path, None, rules, other_segs=kept):
                kept.append(seg)
        segs = kept
    _sol_geom._add_line_segs(out, segs)
    return out
