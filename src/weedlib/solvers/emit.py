# -*- coding: utf-8 -*-
"""Accepts or drops one segment."""
from __future__ import division

import math

from .. import debug as _wdbg
from ..qt import QPainterPath, QPointF
from ..keep import (
    list_closed_subpaths,
    _polyline_points,
    _unique_ring,
)

from .bay import _KAPPA_MIN
from .rules import (
    DEFAULT_ALPHA_MIN,
    DEFAULT_BODY_CLEARANCE,
    DEFAULT_MIN_CUT,
    _ALPHA_GRAZE,
)
from . import clip as _sol_clip
from . import gaps as _sol_gaps
from . import geom as _sol_geom
from . import rank as _sol_rank
from . import rules as _sol_rules


_D_HUG = 1.6
_PHI_HUG = 18.0
# Visual hug: mid-body near a keep edge (body-clearance scale) and φ small.
_D_HUG_CLOSE = DEFAULT_BODY_CLEARANCE
_A_SLIVER = 8.0
_H_SLIVER = 2.5
_A_GAIN_MIN = 12.0

# Piece-border inner path. None leaves a published segment unchanged.
_border_clip_shape = None


def _set_border_clip(shape):
    """Clip published segments to *shape*. None stops the clip."""
    global _border_clip_shape
    _border_clip_shape = shape


def _clip_published_pieces(seg):
    """Segments the host sees. Empty drops *seg*. No clip returns it.

    A rounded inner border is the path, not its bounding box.
    """
    shape = _border_clip_shape
    if seg is None:
        return ()
    if shape is None:
        return (seg,)
    if _sol_clip._path_has_curve(shape):
        parts = _sol_clip._clip_line_to_region(
            seg[0], seg[1], seg[2], seg[3], shape, False,
            samples=64, min_len=1e-9)
    else:
        clipped = _sol_clip._clip_seg_to_rect(
            seg[0], seg[1], seg[2], seg[3], shape.boundingRect())
        parts = () if clipped is None else (clipped,)
    kept = []
    for part in parts:
        if math.hypot(part[2] - part[0], part[3] - part[1]) >= 1e-9:
            kept.append(part)
    return kept


def _publish_path_segments(path):
    """Push each line segment to the live-preview geometry hook."""
    if path is None or path.isEmpty():
        return
    from .. import progress as _progress
    if _sol_clip._path_has_curve(path):
        # Curve handles sit outside a rounded corner.
        segments = _sol_clip._outline_segs(path)
    else:
        segments = _sol_geom._iter_line_segs(path)
    for seg in segments:
        for piece in _clip_published_pieces(seg):
            _progress.report_segment(piece)


# Candidate must lie along an existing weed (not merely both ends near it).
_SEG_REDUNDANT_DOT = 0.97  # ~14°


def _seg_redundant(path, seg, tol=1.5):
    """True if *seg* already overlaps a near-collinear weed segment."""
    if path is None or path.isEmpty() or seg is None:
        return False
    ax, ay, bx, by = seg
    dx, dy = bx - ax, by - ay
    ln = math.hypot(dx, dy)
    if ln < 1e-9:
        return False
    ux, uy = dx / ln, dy / ln
    for s in _sol_geom._iter_line_segs(path):
        sx0, sy0, sx1, sy1 = s
        sdx, sdy = sx1 - sx0, sy1 - sy0
        sln = math.hypot(sdx, sdy)
        if sln < 1e-9:
            continue
        if abs(ux * (sdx / sln) + uy * (sdy / sln)) < _SEG_REDUNDANT_DOT:
            continue
        if (_sol_geom._point_seg_dist(ax, ay, *s) > tol
                or _sol_geom._point_seg_dist(bx, by, *s) > tol):
            continue
        # Midpoint must also sit on the host (rejects near-miss diagonals).
        mx, my = 0.5 * (ax + bx), 0.5 * (ay + by)
        if _sol_geom._point_seg_dist(mx, my, *s) > tol:
            continue
        return True
    return False


def _keep_outline_edges(keep_path, max_edge=4.0):
    """Densified keep outline edges for endpoint anchoring checks."""
    edges = []
    if keep_path is None or keep_path.isEmpty():
        return edges
    for sp in list_closed_subpaths(keep_path):
        pts = _unique_ring(_polyline_points(sp, max_pts=512))
        if len(pts) < 2:
            continue
        ring = _sol_geom._densify_ring(pts, max_edge=max_edge)
        n = len(ring)
        for i in range(n):
            a, b = ring[i], ring[(i + 1) % n]
            edges.append((a.x(), a.y(), b.x(), b.y()))
    return edges


def _point_near_edges(px, py, edges, tol):
    if not edges:
        return False
    for e in edges:
        if _sol_geom._point_seg_dist(px, py, *e) <= tol:
            return True
    return False


def _point_near_weed_segs(px, py, segs, skip=None, tol=1.5):
    for s in segs:
        if skip is not None and s == skip:
            continue
        if _sol_geom._point_seg_dist(px, py, *s) <= tol:
            return True
    return False


def _end_anchored(px, py, segs, keep_edges, skip=None, tol=1.5, work=None,
                  keep_path=None, weed_dir=None):
    """True if a weed endpoint meets keep, another weed, or the work frame.

    Mid-edge keep meet requires α unmeasurable or α ≥ ``_ALPHA_GRAZE``
    (side-on graze ≠ anchor). Corner / vertex hits are meets.
    """
    if _point_near_edges(px, py, keep_edges, tol):
        if keep_path is None or weed_dir is None:
            return True
        frame = _sol_geom._keep_frame_at(keep_path, QPointF(px, py))
        if frame is None or frame.vertex is not None:
            return True
        alpha = _sol_geom._included_angle_deg(QPointF(px, py), weed_dir, keep_path)
        if alpha is None or alpha >= _ALPHA_GRAZE:
            return True
        # Side-on graze: near mid-edge keep but α too small.
    if _point_near_weed_segs(px, py, segs, skip=skip, tol=tol):
        return True
    if work is not None and not work.isNull():
        # Work-rect edge counts (clipped channel/collar ends).
        if (abs(px - work.left()) <= tol or abs(px - work.right()) <= tol
                or abs(py - work.top()) <= tol
                or abs(py - work.bottom()) <= tol):
            return True
    return False


def _require_connected_ends(weed_path, keep_path, tol=1.5, work=None):
    """Drop weed segments with a free end (must meet keep or other weeds).

    Iterates until stable so a spur that only propped up another free
    end is removed too. Closed collars stay: each vertex meets neighbors.
    """
    if weed_path is None or weed_path.isEmpty():
        return QPainterPath()
    segs = list(_sol_geom._iter_line_segs(weed_path))
    if not segs:
        return QPainterPath()
    keep_edges = _keep_outline_edges(keep_path)
    changed = True
    while changed:
        changed = False
        kept = []
        for seg in segs:
            # The scan is the long part once a grid has many lines.
            _progress_check(line=seg)
            dx = seg[2] - seg[0]
            dy = seg[3] - seg[1]
            ln = math.hypot(dx, dy)
            if ln < 1e-12:
                changed = True
                continue
            ux, uy = dx / ln, dy / ln
            a_ok = _end_anchored(
                seg[0], seg[1], segs, keep_edges, skip=seg, tol=tol,
                work=work, keep_path=keep_path, weed_dir=(ux, uy))
            b_ok = _end_anchored(
                seg[2], seg[3], segs, keep_edges, skip=seg, tol=tol,
                work=work, keep_path=keep_path, weed_dir=(-ux, -uy))
            if a_ok and b_ok:
                kept.append(seg)
            else:
                changed = True
        segs = kept
    out = QPainterPath()
    for x0, y0, x1, y1 in segs:
        out.moveTo(x0, y0)
        out.lineTo(x1, y1)
    return out


def _is_parallel_hug(seg, keep_path, min_cut):
    """True if *seg* hugs keep outline and should be dropped (C9 §4b).

    Five interior samples: mean outline distance and angle to nearest keep
    tangent. Reject when d < ``_D_HUG``, φ < ``_PHI_HUG``, and length >
    2·min_cut, unless a short two-body mouth (length ≤ 1.4·gap). Same-body
    outline traces (>80% samples within d_hug and φ < ``_PHI_HUG``) reject.
    A mid-body run that is close *and* parallel on ≥3 samples also rejects
    (long segs that only hug part-way used to survive on mean distance).
    """
    if seg is None or keep_path is None or keep_path.isEmpty():
        return False
    x0, y0, x1, y1 = seg
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy)
    if length < 1e-12:
        return False
    # Densify plus nearest-edge is the long part of a seal or hug pass.
    _progress_check(line=seg)
    # Bay mouth chord / corner→corner dam is not a hug (D012 exact emit).
    if (_sol_rank._near_waste_reflex_corner(keep_path, QPointF(x0, y0))
            and _sol_rank._near_waste_reflex_corner(keep_path, QPointF(x1, y1))):
        return False
    ux, uy = dx / length, dy / length
    rings = _sol_geom._path_to_rings(keep_path)
    if not rings:
        return False
    dens = [_sol_geom._densify_ring(list(r), max_edge=1.5) for r in rings]
    dists = []
    phis = []
    near_n = 0
    close_par = 0
    close_wide = 0
    d_close = max(_D_HUG, 2.5)
    n_samp = 9
    for i in range(1, n_samp + 1):
        t = i / float(n_samp + 1)
        px = x0 + t * dx
        py = y0 + t * dy
        hit = _sol_geom._nearest_on_rings(px, py, dens)
        if hit is None:
            continue
        d = hit[2]
        dists.append(d)
        if d < _D_HUG:
            near_n += 1
        frame = _sol_geom._keep_frame_at(keep_path, QPointF(px, py))
        if frame is None or frame.t0 is None:
            continue
        dot = abs(ux * frame.t0[0] + uy * frame.t0[1])
        phi = math.degrees(math.acos(max(0.0, min(1.0, dot))))
        phis.append(phi)
        if d < d_close and phi < _PHI_HUG:
            close_par += 1
        if d < _D_HUG_CLOSE and phi < _PHI_HUG:
            close_wide += 1
    if not dists:
        return False
    bodies = list_closed_subpaths(keep_path)
    span_pair = None
    for i, bi in enumerate(bodies):
        for bj in bodies[i + 1:]:
            if _sol_gaps._seg_spans_pair(seg, bi, bj, tol=2.5):
                span_pair = (bi, bj)
                break
        if span_pair is not None:
            break
    if span_pair is not None:
        pair = _sol_geom._nearest_pair(span_pair[0], span_pair[1])
        if pair is not None and length <= 1.4 * float(pair[2]):
            return False
    phi_par = (sum(phis) / float(len(phis))) if phis else None
    if (span_pair is None
            and near_n > 0.8 * len(dists)
            and phi_par is not None and phi_par < _PHI_HUG):
        # Same-body outline trace (not a across-bay mouth: those have large φ).
        return True
    if close_par >= 3:
        return True
    floor = float(min_cut) if float(min_cut) > 1e-9 else DEFAULT_MIN_CUT
    if length <= 2.0 * floor or phi_par is None:
        return False
    d_par = sum(dists) / float(len(dists))
    if d_par < _D_HUG and phi_par < _PHI_HUG:
        return True
    # Long rail that only hugs part-way. Uniform offset (peel frame) stays.
    if (length > 16.0 and min(dists) < _D_HUG_CLOSE
            and (max(dists) - min(dists)) > 2.5
            and phis and min(phis) < _PHI_HUG and close_wide >= 2):
        return True
    return False


def _drop_parallel_hugs(weed_path, keep_path, min_cut):
    """Remove parallel-hug segments from *weed_path*."""
    if weed_path is None or weed_path.isEmpty():
        return QPainterPath() if weed_path is None else weed_path
    out = QPainterPath()
    for seg in _sol_geom._iter_line_segs(weed_path):
        if _is_parallel_hug(seg, keep_path, min_cut):
            continue
        out.moveTo(seg[0], seg[1])
        out.lineTo(seg[2], seg[3])
    return out


def _span_pair_for_seg(seg, keep_path, tol=2.5):
    """Keep-body pair that *seg* bridges, or None (frame-open / non-pair)."""
    if seg is None or keep_path is None or keep_path.isEmpty():
        return None
    bodies = list_closed_subpaths(keep_path)
    for i, bi in enumerate(bodies):
        for bj in bodies[i + 1:]:
            if _sol_gaps._seg_spans_pair(seg, bi, bj, tol=tol):
                return (bi, bj)
    return None


def _nearest_pair_spanning_seal(seg, weed_path, path_a, path_b, tol=2.5):
    """Nearest existing *path_a*–*path_b* seal to *seg*, and midpoint distance."""
    if seg is None or weed_path is None or weed_path.isEmpty():
        return None, None
    mx, my = _sol_gaps._seal_midpoint(seg)
    best = None
    best_d = None
    for other in _sol_gaps._pair_spanning_segs(weed_path, path_a, path_b, tol=tol):
        if other == seg:
            continue
        ox, oy = _sol_gaps._seal_midpoint(other)
        d = math.hypot(ox - mx, oy - my)
        if d < 1e-9:
            continue
        if best_d is None or d < best_d:
            best_d = d
            best = other
    return best, best_d


def _sliver_triangle_metrics(seg, other):
    """Area, altitude, κ for the triangle of *seg* + nearest point on *other*."""
    x0, y0, x1, y1 = seg
    mx, my = _sol_gaps._seal_midpoint(seg)
    ox0, oy0, ox1, oy1 = other
    dx, dy = ox1 - ox0, oy1 - oy0
    ln2 = dx * dx + dy * dy
    if ln2 < 1e-18:
        ax, ay = ox0, oy0
    else:
        t = max(0.0, min(1.0, ((mx - ox0) * dx + (my - oy0) * dy) / ln2))
        ax, ay = ox0 + t * dx, oy0 + t * dy
    area = 0.5 * abs((x1 - x0) * (ay - y0) - (ax - x0) * (y1 - y0))
    base = math.hypot(x1 - x0, y1 - y0)
    altitude = _sol_geom._point_seg_dist(ax, ay, x0, y0, x1, y1)
    coast = math.hypot(ax - x0, ay - y0) + math.hypot(ax - x1, ay - y1)
    kappa = (coast / base) if base > 1e-9 else 0.0
    return area, altitude, kappa


def _pair_near_seal_tol(path_a, path_b, seg):
    """Same-site radius used to tell optional extras from far required mouths."""
    from . import corridors as _sol_corridors
    facing = _sol_corridors._corridor_facing(path_a, path_b)
    if facing is not None:
        width = float(facing[3])
        overlap = float(facing[0])
        return max(6.0, 1.25 * max(width, 1e-6), 0.45 * overlap)
    if seg is not None:
        gap = math.hypot(seg[2] - seg[0], seg[3] - seg[1])
        return max(6.0, 1.25 * max(gap, 1e-6))
    return 6.0


def _is_sliver_seal(seg, weed_path, keep_path):
    """True if *seg* only closes a tiny waste triangle (C9 §4d).

    Requires an existing spanning seal on the same keep pair. Drops when the
    closed face has A < ``_A_SLIVER``, h < ``_H_SLIVER``, and κ < 2 (would
    not pass ``_bay_should_seal``).
    """
    if seg is None or weed_path is None or keep_path is None:
        return False
    if weed_path.isEmpty() or keep_path.isEmpty():
        return False
    pair = _span_pair_for_seg(seg, keep_path)
    if pair is None:
        return False
    other, _dist = _nearest_pair_spanning_seal(seg, weed_path, pair[0], pair[1])
    if other is None:
        return False
    area, altitude, kappa = _sliver_triangle_metrics(seg, other)
    if area >= _A_SLIVER or altitude >= _H_SLIVER:
        return False
    if kappa + 1e-9 >= _KAPPA_MIN:
        return False
    return True


def _is_needless_optional_seal(seg, weed_path, keep_path):
    """True if an optional same-site seal adds no peel gain (C9 §4e).

    Only when the pair already has a *nearby* spanning seal (not a far
    still-open D007 mouth). Frame-open (no span pair) never drops. Cheap
    ΔA = closed triangle area; Δn = 0 when same-site already sealed.
    """
    if seg is None or weed_path is None or keep_path is None:
        return False
    if weed_path.isEmpty() or keep_path.isEmpty():
        return False
    pair = _span_pair_for_seg(seg, keep_path)
    if pair is None:
        return False
    other, dist = _nearest_pair_spanning_seal(seg, weed_path, pair[0], pair[1])
    if other is None or dist is None:
        return False
    if dist > _pair_near_seal_tol(pair[0], pair[1], seg):
        return False
    sx, sy = seg[2] - seg[0], seg[3] - seg[1]
    ox, oy = other[2] - other[0], other[3] - other[1]
    sl = math.hypot(sx, sy)
    ol = math.hypot(ox, oy)
    if sl > 1e-9 and ol > 1e-9:
        if abs((sx * ox + sy * oy) / (sl * ol)) < math.cos(
                math.radians(25.0)):
            return False
    area, _altitude, _kappa = _sliver_triangle_metrics(seg, other)
    return area < _A_GAIN_MIN


def _is_duplicate_rail(seg, weed_path):
    """True if a long *seg* runs parallel and close to an existing weed."""
    if seg is None or weed_path is None or weed_path.isEmpty():
        return False
    x0, y0, x1, y1 = seg
    ln = math.hypot(x1 - x0, y1 - y0)
    if ln < 16.0:
        return False
    ux, uy = (x1 - x0) / ln, (y1 - y0) / ln
    mx, my = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
    cos_lim = math.cos(math.radians(_PHI_HUG))
    for o in _sol_geom._iter_line_segs(weed_path):
        if o == seg:
            continue
        ox0, oy0, ox1, oy1 = o
        oln = math.hypot(ox1 - ox0, oy1 - oy0)
        if oln < 8.0:
            continue
        oux, ouy = (ox1 - ox0) / oln, (oy1 - oy0) / oln
        if abs(ux * oux + uy * ouy) < cos_lim:
            continue
        if _sol_geom._point_seg_dist(mx, my, *o) < 6.0:
            return True
    return False


def _drop_slivers_and_needless(weed_path, keep_path):
    """Remove sliver / needless-optional / duplicate-rail seals."""
    if weed_path is None or weed_path.isEmpty():
        return QPainterPath() if weed_path is None else weed_path
    if keep_path is None or keep_path.isEmpty():
        return weed_path
    out = QPainterPath()
    for seg in _sol_geom._iter_line_segs(weed_path):
        if (_is_sliver_seal(seg, out, keep_path)
                or _is_needless_optional_seal(seg, out, keep_path)
                or _is_duplicate_rail(seg, out)):
            continue
        out.moveTo(seg[0], seg[1])
        out.lineTo(seg[2], seg[3])
    return out


def _progress_check(line=None, outline=None):
    """Pause or cancel. At most one outline and one trial line."""
    from .. import progress as _progress
    _progress.check(outline=outline, line=line)


def _add_seg(out, seg, min_cut, keep_path=None, rules=None, report=True):
    if seg is None:
        return
    x0, y0, x1, y1 = seg
    if math.hypot(x1 - x0, y1 - y0) < min_cut:
        _wdbg.log('emit.reject', reason='short', seg=seg)
        return
    if keep_path is not None and rules is not None:
        reason = _seg_emit_fail_reason(seg, keep_path, out, rules)
        if reason is not None:
            _wdbg.log('emit.reject', reason=reason, seg=seg)
            return
    if keep_path is not None and _is_parallel_hug(seg, keep_path, min_cut):
        _wdbg.log('emit.reject', reason='parallel_hug', seg=seg)
        return
    if keep_path is not None and (
            _is_sliver_seal(seg, out, keep_path)
            or _is_needless_optional_seal(seg, out, keep_path)
            or _is_duplicate_rail(seg, out)):
        _wdbg.log('emit.reject', reason='sliver_or_needless', seg=seg)
        return
    if _seg_redundant(out, (x0, y0, x1, y1)):
        _wdbg.log('emit.reject', reason='redundant', seg=seg)
        return
    if _sol_geom._seg_crosses_path(out, (x0, y0, x1, y1)):
        _wdbg.log('emit.reject', reason='cross_weed', seg=seg)
        return
    from .. import progress as _progress
    _progress.check_cancel()
    out.moveTo(x0, y0)
    out.lineTo(x1, y1)
    _wdbg.log('emit.accept', seg=seg)
    # The seen copy is the same seal, not a second cut.
    # Piece-border clip, when one is set. The stored seal stays whole.
    if report:
        for published in _clip_published_pieces(seg):
            _progress.report_segment(published)


def _add_path_segs(out, path, min_cut, keep_path=None, rules=None):
    """Emit *path* line segments through ``_add_seg`` (no ungated addPath)."""
    if path is None or path.isEmpty():
        return
    for seg in _sol_geom._iter_line_segs(path):
        _add_seg(out, seg, min_cut, keep_path=keep_path, rules=rules)


def _passes_alpha_hard(pa, pb, path_a, path_b, alpha_hard=None):
    """True unless measurable created α falls below the emit floor (D012)."""
    hard = DEFAULT_ALPHA_MIN if alpha_hard is None else float(alpha_hard)
    amin = _sol_rank._alpha_min_at_anchors(pa, pb, path_a, path_b)
    if amin is None:
        return True
    return amin >= hard - 1e-9


def _trim_seg_ends(seg, clearance):
    """Interior of *seg* after dropping first/last *clearance*. None if none."""
    if seg is None:
        return None
    x0, y0, x1, y1 = seg
    dx, dy = x1 - x0, y1 - y0
    ln = math.hypot(dx, dy)
    c = float(clearance)
    if ln <= 2.0 * c + 1e-9 or c <= 1e-12:
        return None
    ux, uy = dx / ln, dy / ln
    return (x0 + ux * c, y0 + uy * c, x1 - ux * c, y1 - uy * c)


def _seg_body_clearance_ok(seg, keep_path, other_segs=None, clearance=None):
    """True if mid-segment stays ≥ *clearance* from keep coasts and weeds.

    A keep-to-keep dam whose ends sit on the *same* outline ring is allowed
    to run near that ring (intra-body bay water). Other rings still count.
    """
    c = DEFAULT_BODY_CLEARANCE if clearance is None else float(clearance)
    if c <= 1e-12 or seg is None:
        return True
    mid = _trim_seg_ends(seg, c)
    if mid is None:
        return True
    mx0, my0, mx1, my1 = mid
    dx, dy = mx1 - mx0, my1 - my0
    ln = math.hypot(dx, dy)
    if ln < 1e-12:
        return True
    # Sample walk against the keep rings. One trial line.
    _progress_check(line=seg)
    n = max(int(math.ceil(ln)), 3)
    end_a = (seg[0], seg[1])
    end_b = (seg[2], seg[3])
    land = float(c) + 0.75
    keep_rings = []
    if keep_path is not None and not keep_path.isEmpty():
        keep_rings = _sol_geom._path_to_rings(keep_path)
        if not keep_rings:
            pts = _unique_ring(_polyline_points(keep_path, max_pts=256))
            if len(pts) >= 3:
                keep_rings = [pts]
    skip_ring = None
    if len(keep_rings) >= 1:
        end_idx = []
        for ex, ey in (end_a, end_b):
            best = None
            for i, ring in enumerate(keep_rings):
                hit = _sol_geom._nearest_on_rings(ex, ey, [ring])
                if hit is None:
                    continue
                if best is None or hit[2] < best[0]:
                    best = (hit[2], i)
            end_idx.append(best[1] if best is not None and best[0] <= 1.5 else None)
        if end_idx[0] is not None and end_idx[0] == end_idx[1]:
            skip_ring = end_idx[0]
    others = []
    if other_segs:
        for o in other_segs:
            if o is None or o == seg:
                continue
            if _sol_geom._seg_proper_cross(seg[0], seg[1], seg[2], seg[3],
                                 o[0], o[1], o[2], o[3]):
                continue
            if (_sol_geom._point_seg_dist(seg[0], seg[1], *o) <= 1.2
                    or _sol_geom._point_seg_dist(seg[2], seg[3], *o) <= 1.2
                    or _sol_geom._point_seg_dist(o[0], o[1], *seg) <= 1.2
                    or _sol_geom._point_seg_dist(o[2], o[3], *seg) <= 1.2):
                continue
            others.append(o)
    ux, uy = dx / ln, dy / ln
    for i in range(n + 1):
        t = i / float(n)
        px = mx0 + t * dx
        py = my0 + t * dy
        if keep_rings:
            check = [r for i, r in enumerate(keep_rings) if i != skip_ring]
            if check:
                hit = _sol_geom._nearest_on_rings(px, py, check)
                if hit is not None and hit[2] < c - 1e-9:
                    if (math.hypot(hit[0] - end_a[0], hit[1] - end_a[1]) > land
                            and math.hypot(hit[0] - end_b[0],
                                           hit[1] - end_b[1]) > land):
                        return False
            if skip_ring is not None:
                # Same-ring exemption is for across-bay dams, not a mid-body
                # that runs parallel outside along that ring.
                hit_s = _sol_geom._nearest_on_rings(px, py, [keep_rings[skip_ring]])
                if (hit_s is not None and hit_s[2] < c - 1e-9
                        and math.hypot(hit_s[0] - end_a[0],
                                       hit_s[1] - end_a[1]) > land
                        and math.hypot(hit_s[0] - end_b[0],
                                       hit_s[1] - end_b[1]) > land):
                    frame = _sol_geom._keep_frame_at(keep_path, QPointF(px, py))
                    if frame is not None and frame.t0 is not None:
                        dot = abs(ux * frame.t0[0] + uy * frame.t0[1])
                        phi = math.degrees(
                            math.acos(max(0.0, min(1.0, dot))))
                        if phi < _PHI_HUG:
                            return False
        for o in others:
            if _sol_geom._point_seg_dist(px, py, *o) < c - 1e-9:
                return False
    return True


def _seg_alpha_ok(seg, keep_path, alpha_min=None, peel_frame=None,
                  locked_ends=None):
    """True unless a landing creates a peel angle below the floor."""
    amin = DEFAULT_ALPHA_MIN if alpha_min is None else float(alpha_min)
    ends = _sol_rank._seg_end_dirs(seg)
    if ends is None:
        return False
    locked = locked_ends or ()
    for i, (p, w_hat) in enumerate(ends):
        if i < len(locked) and locked[i]:
            continue
        angles = None
        if keep_path is not None and _sol_geom._point_near_path(
                p.x(), p.y(), keep_path, tol=2.5):
            angles = _sol_rank._created_peel_angles(p, w_hat, keep_path)
        if angles is None and peel_frame is not None and _sol_geom._point_near_path(
                p.x(), p.y(), peel_frame, tol=2.5):
            angles = _sol_rank._created_peel_angles(p, w_hat, peel_frame)
        if angles is not None and min(angles) < amin - 1e-9:
            return False
    return True


def _other_weed_segs(against, skip=None):
    if against is None or against.isEmpty():
        return []
    out = []
    for s in _sol_geom._iter_line_segs(against):
        if skip is not None and s == skip:
            continue
        out.append(s)
    return out


def _seg_emit_fail_reason(seg, keep_path, against, rules, peel_frame=None,
                          locked_ends=None, other_segs=None, clearance=None):
    """None if D012 emit OK; else a short firm-rule tag.

    Crosses are checked by callers (``_add_seg`` / square-tie pick) so
    T-junctions onto existing weeds stay allowed here.
    """
    if seg is None:
        return 'null'
    if rules is None:
        rules = _sol_rules._cut_rules()
    c = rules.body_clearance if clearance is None else float(clearance)
    others = other_segs
    if others is None:
        others = _other_weed_segs(against, skip=seg)
    if not _seg_body_clearance_ok(seg, keep_path, others, clearance=c):
        return 'body_clearance'
    # Corner-locked bay seals may skim the bowl; hug would block exact emit.
    if keep_path is not None and _is_parallel_hug(seg, keep_path, DEFAULT_MIN_CUT):
        if not (locked_ends and any(locked_ends)):
            return 'parallel_hug'
    if not _seg_alpha_ok(
            seg, keep_path, alpha_min=rules.alpha_min, peel_frame=peel_frame,
            locked_ends=locked_ends):
        return 'alpha_min'
    return None


def _seg_emit_ok(seg, keep_path, against, rules, peel_frame=None,
                 locked_ends=None, other_segs=None, clearance=None):
    """Strict D012 emit gate: body clearance + α_min + mid-body hug."""
    return _seg_emit_fail_reason(
        seg, keep_path, against, rules, peel_frame=peel_frame,
        locked_ends=locked_ends, other_segs=other_segs,
        clearance=clearance) is None


def _seg_forced_ok(seg, keep_path, against, rules, peel_frame=None,
                   locked_ends=None, other_segs=None):
    """Forced-seal: never α < floor; tiny body-clearance backoff only."""
    if _seg_emit_ok(
            seg, keep_path, against, rules, peel_frame=peel_frame,
            locked_ends=locked_ends, other_segs=other_segs):
        return True
    if not _seg_alpha_ok(
            seg, keep_path, alpha_min=rules.alpha_min,
            peel_frame=peel_frame, locked_ends=locked_ends):
        return False
    if keep_path is not None and _is_parallel_hug(seg, keep_path, DEFAULT_MIN_CUT):
        if not (locked_ends and any(locked_ends)):
            return False
    c0 = float(rules.body_clearance)
    ln = math.hypot(seg[2] - seg[0], seg[3] - seg[1])
    if ln > 4.0 * max(c0, 1.0):
        return False
    others = other_segs
    if others is None:
        others = _other_weed_segs(against, skip=seg)
    for frac in (0.7, 0.5):
        if _seg_body_clearance_ok(
                seg, keep_path, others, clearance=c0 * frac):
            return True
    return False
