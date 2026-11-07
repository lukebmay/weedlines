# -*- coding: utf-8 -*-
"""One body's bay seal."""
from __future__ import division

import math

from ..qt import QPainterPath, QPointF

from .rules import (
    DEFAULT_MIN_CUT,
    DEFAULT_PENINSULA_RATIO,
)
from . import agglomerate as _sol_agglomerate
from . import bay as _sol_bay
from . import emit as _sol_emit
from . import geom as _sol_geom
from . import rank as _sol_rank
from . import rules as _sol_rules


def _mouth_has_spanning_seal(seen, left, right, tol=3.0):
    """True if *seen* already bridges near the mouth ends (multi-pass guard)."""
    if seen is None or seen.isEmpty() or left is None or right is None:
        return False
    tt = float(tol)
    for seg in _sol_geom._iter_line_segs(seen):
        x0, y0, x1, y1 = seg
        d0l = math.hypot(x0 - left.x(), y0 - left.y())
        d0r = math.hypot(x0 - right.x(), y0 - right.y())
        d1l = math.hypot(x1 - left.x(), y1 - left.y())
        d1r = math.hypot(x1 - right.x(), y1 - right.y())
        if (d0l <= tt and d1r <= tt) or (d0r <= tt and d1l <= tt):
            return True
    return False


def _bay_mouth_already_sealed(seen, left, right, run=None, tol=None):
    """True if *seen* already dams this bay (lip–lip, chord cross, or side↔side)."""
    if seen is None or seen.isEmpty() or left is None or right is None:
        return False
    mouth_w = _sol_bay._bay_mouth_width(left, right)
    tt = max(3.0, 0.25 * mouth_w) if tol is None else float(tol)
    if _mouth_has_spanning_seal(seen, left, right, tol=tt):
        return True
    lx, ly = left.x(), left.y()
    rx, ry = right.x(), right.y()
    for seg in _sol_geom._iter_line_segs(seen):
        if _sol_geom._seg_proper_cross(seg[0], seg[1], seg[2], seg[3], lx, ly, rx, ry):
            return True
    coast = _sol_bay._bay_coast_pts(left, right, run)
    if len(coast) < 2:
        coast = [(lx, ly), (rx, ry)]
    arcs = [0.0]
    for i in range(len(coast) - 1):
        arcs.append(arcs[-1] + math.hypot(
            coast[i + 1][0] - coast[i][0], coast[i + 1][1] - coast[i][1]))
    mid = 0.5 * arcs[-1]
    left_band = [coast[i] for i in range(len(coast)) if arcs[i] <= mid + 1e-9]
    right_band = [coast[i] for i in range(len(coast)) if arcs[i] >= mid - 1e-9]
    band_tol = max(tt, 2.5)

    def near_band(px, py, band):
        if not band:
            return False
        for x, y in band:
            if math.hypot(px - x, py - y) <= band_tol:
                return True
        for i in range(len(band) - 1):
            if _sol_geom._point_seg_dist(
                    px, py, band[i][0], band[i][1],
                    band[i + 1][0], band[i + 1][1]) <= band_tol:
                return True
        return False

    for seg in _sol_geom._iter_line_segs(seen):
        x0, y0, x1, y1 = seg
        if ((near_band(x0, y0, left_band) and near_band(x1, y1, right_band))
                or (near_band(x0, y0, right_band)
                    and near_band(x1, y1, left_band))):
            return True
    return False


def _closest_bay_mouth_corner(body, left, right, run, min_turn=40,
                              coast_tol=2.5):
    """Convex keep corner on the bay coast nearest a mouth lip."""
    if body is None or left is None or right is None:
        return None
    run_pts = list(run or ())
    corners = _sol_geom._convex_corners(body, min_turn=min_turn)
    hits = []
    for c in corners:
        d_lip = min(
            math.hypot(c.x() - left.x(), c.y() - left.y()),
            math.hypot(c.x() - right.x(), c.y() - right.y()))
        if run_pts:
            d_run = min(
                math.hypot(c.x() - p.x(), c.y() - p.y()) for p in run_pts)
        else:
            d_run = d_lip
        if d_run > float(coast_tol) and d_lip > float(coast_tol):
            continue
        d_mouth = _sol_geom._point_seg_dist(
            c.x(), c.y(), left.x(), left.y(), right.x(), right.y())
        # Prefer a mouth lip; then shallow on the coast (not a deep bowl tip).
        hits.append((d_lip, d_mouth, c))
    if not hits:
        return None
    hits.sort(key=lambda t: (t[0], t[1]))
    return QPointF(hits[0][2])


def _bay_coast_opposite(primary, left, right, run, deep=None, step=0.5):
    """Coast near the opposite mouth lip (slide target; not mid-bay / deep bowl)."""
    if primary is None or left is None or right is None:
        return []
    raw = [QPointF(x, y) for x, y in _sol_bay._bay_coast_pts(left, right, run)]
    if len(raw) < 2:
        return []
    dens = []
    ds = max(float(step), 0.25)
    for i in range(len(raw) - 1):
        a, b = raw[i], raw[i + 1]
        dens.append(QPointF(a))
        dx, dy = b.x() - a.x(), b.y() - a.y()
        edge = math.hypot(dx, dy)
        if edge < 1e-12:
            continue
        n = max(int(math.ceil(edge / ds)), 1)
        for k in range(1, n):
            t = k / float(n)
            dens.append(QPointF(a.x() + t * dx, a.y() + t * dy))
    dens.append(QPointF(raw[-1]))
    if len(dens) < 2:
        return []
    mouth_w = _sol_bay._bay_mouth_width(left, right)
    if deep is not None:
        bay_d = _sol_geom._point_seg_dist(
            deep.x(), deep.y(), left.x(), left.y(), right.x(), right.y())
    else:
        bay_d = mouth_w
    arc_limit = max(8.0, 0.55 * float(bay_d), 0.4 * float(mouth_w))
    d_l = math.hypot(primary.x() - left.x(), primary.y() - left.y())
    d_r = math.hypot(primary.x() - right.x(), primary.y() - right.y())
    # Walk from the far lip into the bay along the coast.
    if d_l <= d_r:
        start_i, step_i = len(dens) - 1, -1
    else:
        start_i, step_i = 0, 1
    out = [QPointF(dens[start_i])]
    traveled = 0.0
    i = start_i
    while True:
        ni = i + step_i
        if ni < 0 or ni >= len(dens):
            break
        traveled += math.hypot(
            dens[ni].x() - dens[i].x(), dens[ni].y() - dens[i].y())
        if traveled > arc_limit + 1e-9:
            break
        out.append(QPointF(dens[ni]))
        i = ni
    if step_i < 0:
        out.reverse()
    return out


def _created_peel_ok(p, w_hat, path, alpha_min, peel_frame=None):
    """True unless measurable created peel angles fall below *alpha_min*.

    Uses ``_created_peel_angles`` (D012), not ``_included_angle_deg``. At a
    >180° weed-side corner a mouth chord collinear with one keep edge is a
    legal 180° peel continuation (min created ≈ 90°), not a 0° graze.
    """
    angles = _sol_rank._created_peel_angles(p, w_hat, path)
    if angles is None and peel_frame is not None:
        angles = _sol_rank._created_peel_angles(p, w_hat, peel_frame)
    if angles is None:
        return True
    return min(angles) >= float(alpha_min) - 1e-9


def _bay_seal_ends_ok(primary, far, body, alpha_min, primary_locked):
    """Far coast/wall needs created α≥*alpha_min*; locked class-0 primary exempt."""
    if primary is None or far is None or body is None:
        return False
    dx = far.x() - primary.x()
    dy = far.y() - primary.y()
    ln = math.hypot(dx, dy)
    if ln < 1e-12:
        return False
    ux, uy = dx / ln, dy / ln
    if not _created_peel_ok(far, (-ux, -uy), body, alpha_min):
        return False
    if primary_locked:
        return True
    return _created_peel_ok(primary, (ux, uy), body, alpha_min)


def _iter_bay_far_ends(primary, opposite, body, alpha_min, primary_locked,
                       left=None, right=None):
    """Opposite-coast hits, shortest then mouth-near, that pass the α knob."""
    if primary is None or not opposite:
        return
    ranked = []
    for p in opposite:
        d = math.hypot(p.x() - primary.x(), p.y() - primary.y())
        if left is not None and right is not None:
            dm = _sol_geom._point_seg_dist(
                p.x(), p.y(), left.x(), left.y(), right.x(), right.y())
        else:
            dm = 0.0
        ranked.append((d, dm, p))
    ranked.sort(key=lambda t: (t[0], t[1]))
    for _d, _dm, p in ranked:
        # Coast trials run before a pocket segment is accepted.
        _sol_emit._progress_check(line=(
            primary.x(), primary.y(), p.x(), p.y()))
        if _bay_seal_ends_ok(primary, p, body, alpha_min, primary_locked):
            yield QPointF(p)


def _slide_bay_far_end(primary, opposite, body, alpha_min, primary_locked,
                       left=None, right=None):
    """First α-legal opposite-coast hit (shortest / mouth-near)."""
    for p in _iter_bay_far_ends(
            primary, opposite, body, alpha_min, primary_locked,
            left=left, right=right):
        return p
    return None


def _coast_walk_candidates(end, run, r_hunt, step=0.5, min_inset=0.0):
    """Points from *end* along *run* toward the far mouth, up to *r_hunt*."""
    if end is None:
        return []
    out = []
    seen = set()

    def add(p):
        key = (round(p.x(), 3), round(p.y(), 3))
        if key in seen:
            return
        seen.add(key)
        out.append(QPointF(p))

    if float(min_inset) <= 1e-12:
        add(end)
    if not run or len(run) < 1:
        return out
    pts = list(run)
    d_first = math.hypot(pts[0].x() - end.x(), pts[0].y() - end.y())
    d_last = math.hypot(pts[-1].x() - end.x(), pts[-1].y() - end.y())
    if d_last < d_first:
        pts = list(reversed(pts))
    # Bridge mouth end → first run sample, then along the run.
    chain = [QPointF(end)] + [QPointF(p) for p in pts]
    traveled = 0.0
    lim = float(r_hunt)
    skip = float(min_inset)
    ds = max(float(step), 0.25)
    prev = chain[0]
    for p in chain[1:]:
        dx = p.x() - prev.x()
        dy = p.y() - prev.y()
        edge = math.hypot(dx, dy)
        if edge < 1e-12:
            continue
        n = max(int(math.ceil(edge / ds)), 1)
        for k in range(1, n + 1):
            t = k / float(n)
            q = QPointF(prev.x() + t * dx, prev.y() + t * dy)
            traveled += edge / float(n)
            if traveled > lim + 1e-9:
                return out
            if traveled + 1e-9 >= skip:
                add(q)
        prev = p
    return out


def _body_pocket_seals(body, keep_fill, work, standoff, min_cut, container,
                       keep_tips=None, peninsula_ratio=None, against=None,
                       alpha_min=None, rules=None, peel_frame=None):
    """One peel-wall dam per body bay: mouth-nearest corner → opposite coast."""
    out = QPainterPath()
    seen = QPainterPath()
    if against is not None:
        seen.addPath(against)
    min_width = 2.0 * float(standoff) + float(min_cut)
    min_depth = _sol_bay._bay_min_depth(standoff)
    ratio = (DEFAULT_PENINSULA_RATIO if peninsula_ratio is None
             else float(peninsula_ratio))
    tips = keep_tips or ()
    use_rules = rules if rules is not None else _sol_rules._cut_rules()
    a_min = (float(alpha_min) if alpha_min is not None
             else use_rules.alpha_min)
    for left, right, deep, run in _sol_bay._hull_bay_mouths(body, min_depth, min_width):
        # One bay mouth. The body is the one object.
        _sol_emit._progress_check(
            outline=_sol_geom._one_outline(body),
            line=(left.x(), left.y(), right.x(), right.y()))
        ln = math.hypot(right.x() - left.x(), right.y() - left.y())
        depth = _sol_geom._point_seg_dist(
            deep.x(), deep.y(), left.x(), left.y(), right.x(), right.y())
        if not _sol_bay._bay_should_seal(
                left, right, deep, run, depth=depth, mouth_w=ln, ratio=ratio):
            continue
        if _sol_bay._mouth_between_keep_tips(left, right, tips, tol=2.0):
            continue
        seal_tol = max(3.0, 0.25 * ln)
        if _bay_mouth_already_sealed(
                seen, left, right, run=run, tol=seal_tol):
            continue

        primary = _closest_bay_mouth_corner(body, left, right, run)
        candidates = []
        if primary is not None:
            candidates.append((primary, True))
            for ip in _coast_walk_candidates(
                    primary, run, r_hunt=max(8.0, 0.45 * ln),
                    step=3.0, min_inset=2.0)[:3]:
                candidates.append((ip, False))
        else:
            candidates.extend(((QPointF(left), False), (QPointF(right), False)))

        legal = []
        forced = []
        others = _sol_emit._other_weed_segs(seen)
        for anchor, locked in candidates:
            opposite = _bay_coast_opposite(
                anchor, left, right, run, deep=deep)
            for far in _iter_bay_far_ends(
                    anchor, opposite, body, a_min, locked,
                    left=left, right=right):
                if math.hypot(
                        far.x() - anchor.x(), far.y() - anchor.y()) < min_cut:
                    continue
                trial = _sol_agglomerate._fuse_bridge(
                    anchor, far, standoff, keep_fill, work, min_cut, container)
                if trial is None:
                    continue
                if _sol_emit._seg_redundant(seen, trial) or _sol_geom._seg_crosses_path(seen, trial):
                    continue
                qa = QPointF(trial[0], trial[1])
                qb = QPointF(trial[2], trial[3])
                d_a = math.hypot(qa.x() - anchor.x(), qa.y() - anchor.y())
                d_b = math.hypot(qb.x() - anchor.x(), qb.y() - anchor.y())
                if d_a <= d_b:
                    pri_e, far_e = qa, qb
                else:
                    pri_e, far_e = qb, qa
                if not _bay_seal_ends_ok(pri_e, far_e, body, a_min, locked):
                    if not locked:
                        continue
                    dx = far_e.x() - pri_e.x()
                    dy = far_e.y() - pri_e.y()
                    ln_e = math.hypot(dx, dy)
                    if ln_e < 1e-12:
                        continue
                    if not _created_peel_ok(
                            far_e, (-dx / ln_e, -dy / ln_e), body, a_min):
                        continue
                locked_ends = (
                    _sol_rank._near_waste_reflex_corner(body, QPointF(trial[0], trial[1])),
                    _sol_rank._near_waste_reflex_corner(body, QPointF(trial[2], trial[3])),
                )
                emit_keep = keep_fill if keep_fill is not None else body
                if _sol_emit._seg_emit_ok(
                        trial, emit_keep, seen, use_rules, peel_frame=peel_frame,
                        locked_ends=locked_ends, other_segs=others):
                    legal.append(trial)
                elif _sol_emit._seg_forced_ok(
                        trial, emit_keep, seen, use_rules, peel_frame=peel_frame,
                        locked_ends=locked_ends, other_segs=others):
                    forced.append(trial)
        def _mouth_rank_ok(s):
            # Class-0↔class-0 may *be* the mouth chord; inset only for edge–edge.
            if _sol_rank._seg_both_class0(s, body, peel_frame, body):
                return True
            # Keep exact mouth-corner anchors even when the chord skims the mouth.
            if primary is not None and (
                    math.hypot(s[0] - primary.x(), s[1] - primary.y()) <= 1.25
                    or math.hypot(s[2] - primary.x(), s[3] - primary.y()) <= 1.25):
                return True
            mx = 0.5 * (s[0] + s[2])
            my = 0.5 * (s[1] + s[3])
            return _sol_geom._point_seg_dist(
                mx, my, left.x(), left.y(), right.x(), right.y()) >= 2.0

        def _end_near(s, p, tol=1.25):
            if p is None:
                return False
            return (
                math.hypot(s[0] - p.x(), s[1] - p.y()) <= tol
                or math.hypot(s[2] - p.x(), s[3] - p.y()) <= tol)

        def _is_true_mouth_chord(s, tol=2.0):
            d0l = math.hypot(s[0] - left.x(), s[1] - left.y())
            d0r = math.hypot(s[0] - right.x(), s[1] - right.y())
            d1l = math.hypot(s[2] - left.x(), s[3] - left.y())
            d1r = math.hypot(s[2] - right.x(), s[3] - right.y())
            return (
                (d0l <= tol and d1r <= tol) or (d0r <= tol and d1l <= tol))

        def _survives_hug(s):
            return not _sol_emit._is_parallel_hug(s, body, DEFAULT_MIN_CUT)

        def _pick_pocket(cands):
            if not cands:
                return None
            pool = [s for s in cands if _mouth_rank_ok(s)]
            use = pool if pool else list(cands)
            chords = [s for s in use if _is_true_mouth_chord(s)]
            if chords:
                durable = [s for s in chords if _survives_hug(s)]
                return _sol_rank._pick_ranked_seg(
                    durable if durable else chords, body, body, peel_frame)
            if primary is not None:
                at_corner = [s for s in use if _end_near(s, primary)]
                if at_corner:
                    durable = [s for s in at_corner if _survives_hug(s)]
                    if durable:
                        return _sol_rank._pick_quality_seg(
                            durable, body, body, peel_frame, prefer=a_min)
            durable = [s for s in use if _survives_hug(s)]
            return _sol_rank._pick_quality_seg(
                durable if durable else use, body, body, peel_frame)

        seg = _pick_pocket(legal)
        if seg is None:
            short_f = [s for s in forced
                       if math.hypot(s[2] - s[0], s[3] - s[1]) <= 24.0]
            seg = _pick_pocket(short_f)
        if seg is None:
            continue
        _sol_emit._add_seg(out, seg, 0.0)
        _sol_emit._add_seg(seen, seg, 0.0, report=False)
    return out
