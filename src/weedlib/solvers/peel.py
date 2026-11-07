# -*- coding: utf-8 -*-
"""The grow-clearance peel frame."""
from __future__ import division

import math

from .. import debug as _wdbg
from ..qt import QPainterPath, QPointF, QRectF

from .rules import (
    DEFAULT_FRAME_CLEARANCE,
    _FRAME_CLEARANCE_SOFT_MAX,
)
from . import bay as _sol_bay
from . import clip as _sol_clip
from . import clipper as _sol_clipper
from . import geom as _sol_geom
from . import stats as _sol_stats


def _peel_axis(path_a, path_b, core=None):
    """Along-corridor ĉ and across-alley n̂ for a keep–keep gap.

    *n̂* from *core.hx/hy* when given, else ``_dominant_gap_axis``.
    *ĉ* is unit and perpendicular (facing-end along order). Returns (c_hat, n_hat).
    """
    from . import gaps as _sol_gaps
    if core is not None and hasattr(core, 'hx'):
        nx, ny = float(core.hx), float(core.hy)
        ln = math.hypot(nx, ny)
        if ln < 1e-12:
            nx, ny = _sol_gaps._dominant_gap_axis(path_a, path_b)
        else:
            nx, ny = nx / ln, ny / ln
    else:
        nx, ny = _sol_gaps._dominant_gap_axis(path_a, path_b)
    # Facing-end order uses (-ny, nx) as the along axis.
    cx, cy = -ny, nx
    return (cx, cy), (nx, ny)


def _peel_dir_at(p, ctx):
    """Unit peel direction at *p* for a small context dict.

    ``ctx['kind']`` ∈ ``corridor`` | ``bay`` | ``frame_open`` | ``frame_letter``:

    - corridor: ±ĉ via ``c_hat`` and optional ``mouth`` (toward far end)
    - bay: mouth-mid → out (opposite ``_bay_waste_dir``), needs left/right/deep
      or precomputed ``out``
    - frame_open: keep → collar via ``collar_pt`` or ``n_hat``
    - frame_letter: along gap toward the frame-heavier open end
    """
    from . import frame_peninsulas as _sol_frame_peninsulas
    if ctx is None or p is None:
        return None
    kind = ctx.get('kind')
    if kind == 'corridor':
        c_hat = ctx.get('c_hat')
        if c_hat is None:
            return None
        cx, cy = float(c_hat[0]), float(c_hat[1])
        ln = math.hypot(cx, cy)
        if ln < 1e-12:
            return None
        cx, cy = cx / ln, cy / ln
        mouth = ctx.get('mouth')
        if mouth is None:
            return (cx, cy)
        s = (p.x() - mouth.x()) * cx + (p.y() - mouth.y()) * cy
        if s < 0.0:
            return (-cx, -cy)
        return (cx, cy)
    if kind == 'bay':
        out = ctx.get('out')
        if out is not None:
            return _sol_geom._unit_xy(float(out[0]), float(out[1]))
        left, right, deep = ctx.get('left'), ctx.get('right'), ctx.get('deep')
        if left is None or right is None or deep is None:
            return None
        wd = _sol_bay._bay_waste_dir(left, right, deep)
        if wd is None:
            return None
        # Peel out the mouth = opposite mouth→deep.
        return _sol_geom._unit_xy(-wd[0], -wd[1])
    if kind == 'frame_open':
        n_hat = ctx.get('n_hat')
        if n_hat is not None:
            return _sol_geom._unit_xy(float(n_hat[0]), float(n_hat[1]))
        collar_pt = ctx.get('collar_pt')
        if collar_pt is None:
            return None
        return _sol_geom._unit_xy(collar_pt.x() - p.x(), collar_pt.y() - p.y())
    if kind == 'frame_letter':
        path_a = ctx.get('path_a')
        path_b = ctx.get('path_b')
        if path_a is None or path_b is None:
            return None
        c_hat, _n_hat = _peel_axis(path_a, path_b, ctx.get('core'))
        top = _sol_frame_peninsulas._frame_open_is_top(
            path_a, path_b, ctx.get('work'),
            collar_rings=ctx.get('collar_rings'))
        # ĉ = (-ny, nx); for side-by-side n̂≈±X, ĉ≈±Y with +ĉ = up in Y-down?
        # Qt Y-down: +cy means downward. Frame-heavier top → peel toward top
        # (−Y), so flip when top is the open end and cy > 0.
        cx, cy = c_hat
        if top:
            if cy > 0.0 or (abs(cy) < 1e-12 and cx > 0.0):
                return (-cx, -cy)
            return (cx, cy)
        if cy < 0.0 or (abs(cy) < 1e-12 and cx < 0.0):
            return (-cx, -cy)
        return (cx, cy)
    return None


def _available_work_delta(cluster, work):
    """Room from cluster bbox to work edge, minus 2 so the rail is inside."""
    if work is None or work.isNull():
        return 0.0
    acc = None
    for b in cluster:
        if b is None or b.isEmpty():
            continue
        br = b.boundingRect()
        acc = QRectF(br) if acc is None else acc.united(br)
    if acc is None or acc.isEmpty():
        return 0.0
    room = min(
        acc.left() - work.left(),
        acc.top() - work.top(),
        work.right() - acc.right(),
        work.bottom() - acc.bottom())
    return max(0.0, room - 2.0)


def _drop_segs_near_path(path, other, tol):
    """Drop segments whose midpoint sits on *other* (design already a wall)."""
    if path is None or path.isEmpty() or other is None or other.isEmpty():
        return path if path is not None else QPainterPath()
    rings = _sol_geom._path_to_rings(other)
    if not rings:
        return path
    out = QPainterPath()
    tt = float(tol)
    for seg in _sol_geom._iter_line_segs(path):
        mx = 0.5 * (seg[0] + seg[2])
        my = 0.5 * (seg[1] + seg[3])
        hit = _sol_geom._nearest_on_rings(mx, my, rings)
        if hit is not None and hit[2] <= tt:
            continue
        out.moveTo(seg[0], seg[1])
        out.lineTo(seg[2], seg[3])
    return out


def _frame_clearance_want(frame_clearance, room):
    """Standoff inside soft band ~20–30 when knob is default-ish and room allows.

    Explicit below-default clearances (tests / tight packs) stay exact.
    """
    lo = max(float(frame_clearance), 0.0)
    if lo + 1e-9 >= float(DEFAULT_FRAME_CLEARANCE):
        hi = max(lo, float(_FRAME_CLEARANCE_SOFT_MAX))
    else:
        hi = lo
    avail = max(0.0, float(room) - 2.0)
    if avail >= hi - 1e-9:
        return hi
    if avail > lo:
        return min(avail, hi)
    return lo


def _peel_frame_for_cluster(cluster, keep_fill, work, container, frame_clearance):
    """Grow-clearance peel frame (full or partial). (path, rings).

    Empty when *container* bounds the face (D013 — no second collar).
    """
    empty = (QPainterPath(), [])
    if not cluster or frame_clearance <= 1e-9:
        _wdbg.log('peel_frame.skip', reason='no_cluster_or_clearance')
        return empty
    if container is not None and not container.isEmpty():
        _wdbg.log('peel_frame.skip', reason='design_container_D013')
        return empty
    room = _available_work_delta(cluster, work) + 2.0
    if room < 0.6:
        _wdbg.log('peel_frame.skip', reason='no_room', room=room)
        return empty
    want = _frame_clearance_want(frame_clearance, room)
    delta = min(want, room - 2.0)
    if delta < 0.75:
        delta = max(0.6, room - 0.35)
    rings = _sol_clipper._cluster_offset_rings(cluster, delta)
    raw = _sol_geom._rings_to_path(rings)
    clipped = _sol_clip._clip_path_to_waste(raw, keep_fill, None)
    clipped = _sol_clip._clip_path_to_rect(clipped, work)
    segs = _sol_stats.weed_path_stats(clipped)['segments']
    _wdbg.log(
        'peel_frame.emit', n_bodies=len(cluster), delta=delta, room=room,
        rings=len(rings), segs=segs)
    return clipped, rings


def _opening_wall_rings(used_rings, container):
    """Target rings for keep→wall corridor: peel frame, else container coast."""
    if used_rings:
        return used_rings
    if container is not None and not container.isEmpty():
        return _sol_geom._path_to_rings(container)
    return []


def _corners_near(path, origin, r_hunt, other=None):
    """Convex corners within *r_hunt* of *origin* (optional nearer-than-*other*)."""
    if path is None or origin is None:
        return []
    rr = float(r_hunt)
    out = []
    for c in _sol_geom._convex_corners(path, min_turn=40):
        d0 = math.hypot(c.x() - origin.x(), c.y() - origin.y())
        if d0 > rr:
            continue
        if other is not None:
            d1 = math.hypot(c.x() - other.x(), c.y() - other.y())
            if d0 > d1 + 1.0:
                continue
        out.append(QPointF(c))
    return out


def _keep_tangent_for_peel(frame, peel_hat):
    """Incident keep tangent most aligned with *peel_hat*."""
    if frame is None or peel_hat is None:
        return None
    px, py = float(peel_hat[0]), float(peel_hat[1])
    t0 = frame.t0
    if frame.vertex is None:
        return t0
    t1 = frame.t1
    d0 = abs(t0[0] * px + t0[1] * py)
    d1 = abs(t1[0] * px + t1[1] * py)
    return t0 if d0 >= d1 else t1


def _dist_to_points(p, pts, default=None):
    """Nearest distance to *pts*; *default* when empty (else inf)."""
    if p is None or not pts:
        return float('inf') if default is None else float(default)
    px, py = p.x(), p.y()
    return min(math.hypot(c.x() - px, c.y() - py) for c in pts)
