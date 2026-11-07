# -*- coding: utf-8 -*-
"""Bay, peninsula, and pocket seals."""
from __future__ import division

import math

import pytest

from weedlib.qt import QPainterPath, QPointF, QRectF
from weedlib.solvers import (
    DEFAULT_CHANNEL_STANDOFF,
    DEFAULT_DELICATE_ANGLE_DEG,
    island_hop_weeds,
    even_odd_keep_fill,
    list_closed_subpaths,
    padded_work_rect,
)
from weedlib.solvers.bay import (
    _approx_bay_kappa,
    _bay_coast_length,
    _bay_has_undercut,
    _bay_kappa,
    _bay_mouth_width,
    _bay_should_seal,
    _deep_keep_peninsula_tips,
    _frontier_complexity,
    _frontier_run_metrics,
    _frontier_tip_count,
    _has_independent_waste_bays,
    _hull_bay_mouths,
    _mouth_between_keep_tips,
    _peninsula_is_deep,
    _peninsula_should_detach,
    _run_arc_length,
    _run_chord_length,
)
from weedlib.solvers.geom import (
    _included_angle_deg,
    _point_seg_dist,
)
from weedlib.solvers.pockets import (
    _bay_mouth_already_sealed,
    _body_pocket_seals,
    _closest_bay_mouth_corner,
)
from weedlib.solvers.rank import _created_peel_angles
from weedlib.solvers.rules import (
    _ALPHA_HARD,
    _ALPHA_MIN_PEEL,
)
import weedlib.solvers.emit as mod_emit
import weedlib.solvers.gaps as mod_gaps
import weedlib.solvers.rank as mod_rank
import weedlib.solvers.rules as mod_rules

pytest.importorskip('PyQt5', reason='Qt binding required for weedlib geometry')

from tests.weed_shapes import (
    requires_clipper,
    _rect_path,
    _star12_valleys,
    _alley_gap_seals,
    _letter_o,
    _residual_traps_for,
    _letter_t,
    _keep_bodies,
    _letter_k,
    _star12,
    _end_near_keep,
    _shallow_smooth_notch_body,
    _line_segments,
    _deep_smooth_bay_body,
    _poly_path,
    _letters_hi,
    _waste_flood,
    _letter_a,
)

@requires_clipper
def test_star_has_deep_keep_peninsulas_letters_do_not():
    """Star tips are deep keep peninsulas; boxy/smooth bodies are not."""
    star = _keep_bodies(_star12())
    assert len(star) == 1
    star_tips = _deep_keep_peninsula_tips(star[0], DEFAULT_DELICATE_ANGLE_DEG)
    assert len(star_tips) >= 5, "star12 should have many deep keep tips, got %s" % (
        len(star_tips),)
    for label, path in (
            ('A', _letter_a()), ('O', _letter_o()), ('HI', _letters_hi())):
        for body in _keep_bodies(path):
            n = len(_deep_keep_peninsula_tips(body, DEFAULT_DELICATE_ANGLE_DEG))
            assert n < 3, "%s sprouted %s deep keep peninsulas" % (label, n)


def test_h_bay_mouths_are_both_counters():
    """H has two U-bays; detector must emit both mouths."""
    keep = _letters_hi()
    closed = list_closed_subpaths(keep)
    h = max(closed, key=lambda p: p.boundingRect().width())
    mouths = _hull_bay_mouths(h, min_depth=4.0, min_width=4.0)
    assert len(mouths) >= 2, "H should have two bay mouths, got %s" % len(mouths)
    ys = sorted(0.5 * (a.y() + b.y()) for a, b, _d, _run in mouths)
    assert ys[0] < 24, "missing H top bay (ys=%s)" % ys
    assert ys[-1] > 66, "missing H bottom bay (ys=%s)" % ys


@requires_clipper
def test_h_lower_bay_is_sealed():
    """Cut across the H lower counter so it is not a live branch."""
    keep = _letters_hi()
    weed = island_hop_weeds(keep, padding=[10, 10, 10, 10], collar=4.0)
    keep_fill = even_odd_keep_fill(keep)
    hit = None
    for x0, y0, x1, y1 in _line_segments(weed):
        mx, my = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
        if keep_fill.contains(QPointF(mx, my)):
            continue
        if 16.5 <= mx <= 29.5 and 68.0 <= my <= 73.0:
            hit = (x0, y0, x1, y1)
            break
    assert hit is not None, "no seal on the H lower bay mouth"


@requires_clipper
def test_under_h_does_not_fork_into_bay_and_left():
    """Under the H: pocket and left wrap must not stay one piece."""
    keep = _letters_hi()
    pad = [10, 10, 10, 10]
    weed = island_hop_weeds(keep, padding=pad, collar=4.0)
    keep_fill = even_odd_keep_fill(keep)
    work = padded_work_rect(keep, pad)
    seed = QPointF(23, 74)
    seen, cell, _world = _waste_flood(keep_fill, weed, work, seed, step=1.5)
    pocket = cell(QPointF(23, 60))
    left = cell(QPointF(6, 45))
    assert pocket not in seen or left not in seen, (
        "under-H waste still forks into the H bay and the left corridor")


@requires_clipper
def test_deep_waste_peninsula_seals_h_not_t():
    """H counters are deep (sealed); a t open side is shallow (not sealed)."""
    h = max(list_closed_subpaths(_letters_hi()),
            key=lambda p: p.boundingRect().width())
    h_mouths = _hull_bay_mouths(h, min_depth=4.0, min_width=4.0)
    h_deep = []
    for left, right, deep, _run in h_mouths:
        mouth_w = math.hypot(right.x() - left.x(), right.y() - left.y())
        depth = _point_seg_dist(
            deep.x(), deep.y(), left.x(), left.y(), right.x(), right.y())
        if _peninsula_is_deep(depth, mouth_w):
            h_deep.append((left, right, deep))
    assert len(h_deep) >= 2, "H bays should be deep, got %s" % len(h_deep)

    t = _letter_t()
    t_mouths = _hull_bay_mouths(t, min_depth=4.0, min_width=4.0)
    t_deep = []
    for left, right, deep, _run in t_mouths:
        mouth_w = math.hypot(right.x() - left.x(), right.y() - left.y())
        depth = _point_seg_dist(
            deep.x(), deep.y(), left.x(), left.y(), right.x(), right.y())
        if _peninsula_is_deep(depth, mouth_w):
            t_deep.append((left, right, deep))
    assert not t_deep, "t open side should be shallow, got %s deep" % len(t_deep)

    weed = island_hop_weeds(t, padding=[10, 10, 10, 10], collar=4.0)
    keep_fill = even_odd_keep_fill(t)
    # Inside the left dent (between stem and hull), not the outer collar.
    left_notch = QRectF(35.5, 32.0, 4.0, 28.0)
    seals = []
    for x0, y0, x1, y1 in _line_segments(weed):
        mx, my = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
        if keep_fill.contains(QPointF(mx, my)):
            continue
        if left_notch.contains(QPointF(mx, my)) and math.hypot(x1 - x0, y1 - y0) > 3.0:
            seals.append((x0, y0, x1, y1))
    assert not seals, "t left opening was sealed: %s" % seals


def test_font_like_h_counter_is_deep():
    """A U wider than it is deep (font H) is still a trap."""
    u = _rect_path(0, 0, 8, 15).united(_rect_path(21, 0, 8, 15))
    u = u.united(_rect_path(0, 11, 29, 4))
    mouths = _hull_bay_mouths(u, min_depth=4.0, min_width=4.0)
    deep = []
    for left, right, tip, _run in mouths:
        mouth_w = math.hypot(right.x() - left.x(), right.y() - left.y())
        depth = _point_seg_dist(
            tip.x(), tip.y(), left.x(), left.y(), right.x(), right.y())
        if _peninsula_is_deep(depth, mouth_w):
            deep.append((left, right, tip))
    assert deep, "font-like U (11 deep / 13 wide) should be deep"
    weed = island_hop_weeds(u, padding=[8, 8, 8, 8], collar=4.0)
    keep_fill = even_odd_keep_fill(u)
    hit = None
    for x0, y0, x1, y1 in _line_segments(weed):
        mx, my = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
        if keep_fill.contains(QPointF(mx, my)):
            continue
        if 8.0 <= mx <= 21.0 and -0.2 <= my <= 5.0:
            hit = (x0, y0, x1, y1)
            break
    assert hit is not None, "font-like U mouth was not sealed"


def test_star_valley_mouth_is_not_sealed():
    """Waste between two keep tips is a valley, not a peninsula seal."""
    keep = _star12()
    body = _keep_bodies(keep)[0]
    tips = _deep_keep_peninsula_tips(body, DEFAULT_DELICATE_ANGLE_DEG)
    assert len(tips) >= 5
    mouths = _hull_bay_mouths(body, min_depth=4.0, min_width=4.0)
    valley = 0
    for left, right, _deep, _run in mouths:
        if _mouth_between_keep_tips(left, right, tips, tol=3.0):
            valley += 1
    assert valley >= 5, "star valleys should sit between keep tips, got %s" % valley
    weed = island_hop_weeds(keep, padding=[12, 12, 12, 12], collar=4.0)
    valleys = _star12_valleys()
    for x0, y0, x1, y1 in _line_segments(weed):
        mx, my = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
        for v in valleys:
            if math.hypot(mx - v.x(), my - v.y()) < 8.0:
                raise AssertionError(
                    "star valley sealed at (%s, %s)" % (mx, my))


def test_k_has_independent_bays_so_no_tip_spokes():
    """A K is not a star: seal the openings, channel to the collar."""
    k = _letter_k()
    tips = _deep_keep_peninsula_tips(k, DEFAULT_DELICATE_ANGLE_DEG)
    assert len(tips) >= 2
    assert _has_independent_waste_bays(
        k, tips, DEFAULT_CHANNEL_STANDOFF, 1.0)
    neighbor = _rect_path(42, 0, 6, 40)
    keep = QPainterPath()
    keep.addPath(k)
    keep.addPath(neighbor)
    weed = island_hop_weeds(keep, padding=[10, 10, 10, 10], collar=4.0)
    keep_fill = even_odd_keep_fill(keep)
    diagonals = []
    for x0, y0, x1, y1 in _line_segments(weed):
        mx, my = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
        if keep_fill.contains(QPointF(mx, my)):
            continue
        ln = math.hypot(x1 - x0, y1 - y0)
        if ln < 4.0:
            continue
        near_tip = any(
            math.hypot(x0 - t['pt'].x(), y0 - t['pt'].y()) < 4.0
            or math.hypot(x1 - t['pt'].x(), y1 - t['pt'].y()) < 4.0
            for t in tips)
        if not near_tip:
            continue
        ang = abs(math.degrees(math.atan2(y1 - y0, x1 - x0)))
        ang = min(ang % 180.0, 180.0 - (ang % 180.0))
        from_axis = min(ang, abs(90.0 - ang))
        if from_axis > 20.0:
            diagonals.append((from_axis, (x0, y0, x1, y1)))
    assert not diagonals, "K still has tip spokes: %s" % diagonals


def _kappa_borderline_bay_body():
    """U with κ ≈ 2.0 and depth 0.5×mouth: default depth gate off, ratio 0.15 on."""
    # Mouth 20, depth 10 → L_coast=40, κ=2; deep iff ratio < 0.5.
    return _poly_path((
        (0, 0), (10, 0), (10, 10), (30, 10), (30, 0), (40, 0),
        (40, 24), (0, 24),
    ))


def test_peninsula_ratio_seals_borderline_bay():
    """Lowering peninsula_ratio seals a κ≥2 bay the default depth gate skips."""
    keep = _kappa_borderline_bay_body()
    mouths = _hull_bay_mouths(keep, min_depth=1.0, min_width=4.0)
    assert mouths
    left, right, deep, run = mouths[0]
    mw = _bay_mouth_width(left, right)
    depth = _point_seg_dist(
        deep.x(), deep.y(), left.x(), left.y(), right.x(), right.y())
    assert abs(_bay_kappa(left, right, run, mouth_w=mw) - 2.0) < 0.15
    assert not _peninsula_is_deep(depth, mw, ratio=0.75)
    assert _peninsula_is_deep(depth, mw, ratio=0.15)

    def mouth_seals(weed):
        keep_fill = even_odd_keep_fill(keep)
        return _keep_to_keep_in_box(weed, keep_fill, 9.0, -0.5, 31.0, 3.0)

    default = island_hop_weeds(keep, padding=[10, 10, 10, 10], collar=4.0)
    shallow = island_hop_weeds(
        keep, padding=[10, 10, 10, 10], collar=4.0, peninsula_ratio=0.15)
    assert not mouth_seals(default), "default ratio sealed borderline bay"
    assert mouth_seals(shallow), "ratio 0.15 did not seal borderline bay"


def _square_wave_run(teeth=3, width=2.0, height=4.0):
    """Open serrated polyline: square teeth point +y (into waste)."""
    pts = []
    x = 0.0
    for _ in range(teeth):
        pts.append((x, 0.0))
        pts.append((x, height))
        x += width
        pts.append((x, height))
        pts.append((x, 0.0))
        x += width
    return pts


def _pointed_comb_run(teeth=3, width=2.0, height=4.0):
    """Open zig-zag comb: sharp tips point +y (turn ≫ delicate angle)."""
    pts = [(0.0, 0.0)]
    x = 0.0
    half = 0.5 * width
    for _ in range(teeth):
        pts.append((x + half, height))
        x += width
        pts.append((x, 0.0))
    return pts


def test_frontier_smooth_run_low_rho():
    """Straight and gentle-arc frontier runs stay near ρ ≈ 1."""
    straight = [(0.0, 0.0), (10.0, 0.0), (20.0, 0.0), (30.0, 0.0)]
    assert _frontier_complexity(straight) < 1.15
    assert abs(_run_arc_length(straight) - 30.0) < 1e-9
    assert abs(_run_chord_length(straight) - 30.0) < 1e-9

    # Shallow circular arc (~30°): ρ stays near 1.
    r = 40.0
    arc = []
    for i in range(9):
        t = math.radians(i * 30.0 / 8.0)
        arc.append((r * math.sin(t), r * (1.0 - math.cos(t))))
    assert _frontier_complexity(arc) < 1.15


def test_frontier_serrated_run_high_rho():
    """Square-wave frontier is clearly more complex than a smooth run."""
    serrated = _square_wave_run(teeth=3, width=2.0, height=4.0)
    rho = _frontier_complexity(serrated)
    assert rho > 2.0, "expected serrated ρ > 2, got %s" % rho
    smooth = [(0.0, 0.0), (_run_chord_length(serrated), 0.0)]
    assert rho > _frontier_complexity(smooth) * 1.5


def test_frontier_three_tooth_comb_tip_count():
    """Three keep teeth into waste (+y) yield tip_count ≥ 3."""
    comb = _pointed_comb_run(teeth=3, width=2.0, height=4.0)
    # Waste above the run; tips are the +y tooth peaks.
    n = _frontier_tip_count(comb, waste_dir=(0.0, 1.0))
    assert n >= 3, "expected ≥3 tips on 3-tooth comb, got %s" % n
    m = _frontier_run_metrics(comb, waste_dir=(0.0, 1.0))
    assert m.tip_count == n
    assert m.rho > 1.5


def test_frontier_empty_or_tiny_safe_defaults():
    """Empty/tiny runs: ρ=1, tip_count=0, no exceptions."""
    assert _frontier_complexity([]) == 1.0
    assert _frontier_complexity([(0.0, 0.0)]) == 1.0
    assert _frontier_complexity([(1.0, 1.0), (1.0, 1.0)]) == 1.0
    assert _run_arc_length([]) == 0.0
    assert _run_chord_length([(0.0, 0.0)]) == 0.0
    assert _frontier_tip_count([]) == 0
    assert _frontier_tip_count([(0.0, 0.0), (1.0, 0.0)]) == 0
    m = _frontier_run_metrics([])
    assert m.rho == 1.0 and m.tip_count == 0
    assert m.length == 0.0 and m.chord == 0.0


def _deep_smooth_c_bay_body():
    """Rect 40×40 with a right C-notch: mouth 16, depth 16."""
    return _poly_path((
        (0, 0), (40, 0), (40, 12), (24, 12), (24, 28), (40, 28),
        (40, 40), (0, 40),
    ))


def _shallow_jagged_bay_body():
    """Shallow bay (depth < 0.75×mouth) with long coast so κ ≥ 3 (D007)."""
    # Mouth 20 at y=0; 10 teeth of depth 6 → L_coast ≫ mouth, still not deep.
    pts = [(0, 0), (10, 0), (10, 1.0)]
    x = 10.0
    for _ in range(10):
        pts.append((x + 1.0, 6.0))
        x += 2.0
        pts.append((x, 1.0))
    pts.extend(((30, 0), (50, 0), (50, 28), (0, 28)))
    return _poly_path(pts)


def _undercut_bay_body():
    """Mouth 10, wider interior 20 (undercut), moderate depth (κ in [2, 3))."""
    # Bottle bay: neck 10 wide, chamber 20 wide, depth ~12.
    return _poly_path((
        (0, 0), (15, 0), (15, 4), (10, 4), (10, 16), (30, 16), (30, 4),
        (25, 4), (25, 0), (40, 0), (40, 28), (0, 28),
    ))


def _keep_to_keep_in_box(weed, keep_fill, x0, y0, x1, y1, min_len=6.0):
    """Waste segments in *box* whose both ends meet keep."""
    hits = []
    for sx, sy, ex, ey in _line_segments(weed):
        mx, my = 0.5 * (sx + ex), 0.5 * (sy + ey)
        if keep_fill.contains(QPointF(mx, my)):
            continue
        if not (x0 <= mx <= x1 and y0 <= my <= y1):
            continue
        if math.hypot(ex - sx, ey - sy) < min_len:
            continue
        if _end_near_keep(sx, sy, keep_fill) and _end_near_keep(ex, ey, keep_fill):
            hits.append((sx, sy, ex, ey))
    return hits


def test_bay_kappa_and_undercut_helpers():
    """Pure D007 helpers: κ, coast length, undercut probe."""
    deep = _deep_smooth_bay_body()
    mouths = _hull_bay_mouths(deep, min_depth=1.0, min_width=4.0)
    assert len(mouths) >= 1
    left, right, deep_pt, run = mouths[0]
    mw = _bay_mouth_width(left, right)
    assert abs(mw - 16.0) < 0.5
    assert abs(_bay_coast_length(left, right, run) - 48.0) < 1.0
    assert abs(_bay_kappa(left, right, run) - 3.0) < 0.1
    assert _bay_should_seal(left, right, deep_pt, run)

    shallow = _shallow_smooth_notch_body()
    mouths = _hull_bay_mouths(shallow, min_depth=1.0, min_width=4.0)
    left, right, deep_pt, run = mouths[0]
    assert _bay_kappa(left, right, run) < 2.0
    assert not _bay_should_seal(left, right, deep_pt, run)

    # Approx: deep U → κ = 2·d/w + 1 ≥ 3; shallow notch stays below min.
    assert _approx_bay_kappa(10.0, 10.0) >= 3.0
    assert _approx_bay_kappa(2.0, 10.0) < 2.0
    assert _peninsula_should_detach(10.0, 10.0, [(0, 0), (10, 0)])
    assert not _peninsula_should_detach(2.0, 10.0, [(0, 0), (10, 0)])

    under = _undercut_bay_body()
    mouths = _hull_bay_mouths(under, min_depth=1.0, min_width=4.0)
    assert mouths, "undercut bay missing"
    sealed = False
    undercut = False
    for left, right, deep_pt, run in mouths:
        mw = _bay_mouth_width(left, right)
        depth = _point_seg_dist(
            deep_pt.x(), deep_pt.y(), left.x(), left.y(), right.x(), right.y())
        k = _bay_kappa(left, right, run, mouth_w=mw)
        if _bay_has_undercut(left, right, deep_pt, run):
            undercut = True
        if _bay_should_seal(left, right, deep_pt, run, depth=depth, mouth_w=mw):
            sealed = True
        # Prefer the neck mouth (~10), not a wider hull edge.
        if mw < 14.0 and 2.0 <= k < 3.0:
            assert _bay_has_undercut(left, right, deep_pt, run), (
                "bottle interior should undercut mouth=%s κ=%s" % (mw, k))
    assert undercut or sealed, "undercut bay should undercut or seal"


def test_peninsula_should_detach_or_gates():
    """D007: detach via κ/depth approx (ρ/tips alone no longer seal)."""
    smooth = [(0.0, 0.0), (10.0, 0.0), (20.0, 0.0)]
    assert _peninsula_should_detach(10.0, 10.0, smooth)
    assert not _peninsula_should_detach(2.0, 10.0, smooth)
    comb = _pointed_comb_run(teeth=3, width=2.0, height=4.0)
    # Short shallow comb: κ_approx = 2*2/10+1 = 1.4 < 2 → not a bay.
    assert not _peninsula_should_detach(2.0, 10.0, comb, waste_dir=(0.0, 1.0))


def test_deep_smooth_bay_is_sealed():
    """A U with κ ≥ 3 (or deep) gets a keep-to-keep mouth seal."""
    keep = _deep_smooth_bay_body()
    weed = island_hop_weeds(keep, padding=[10, 10, 10, 10], collar=4.0)
    keep_fill = even_odd_keep_fill(keep)
    seals = _keep_to_keep_in_box(weed, keep_fill, 11.0, -0.5, 29.0, 4.0)
    assert seals, "deep smooth bay mouth was not sealed"


def test_shallow_smooth_notch_is_not_sealed():
    """A shallow rectangular notch (κ < 2) must stay open."""
    keep = _shallow_smooth_notch_body()
    weed = island_hop_weeds(keep, padding=[10, 10, 10, 10], collar=4.0)
    keep_fill = even_odd_keep_fill(keep)
    seals = _keep_to_keep_in_box(weed, keep_fill, 7.0, -0.5, 33.0, 5.0)
    assert not seals, "shallow smooth notch was sealed: %s" % seals


def test_shallow_jagged_bay_is_sealed():
    """A shallow bay with κ ≥ 3 (long coast) still seals at the neck."""
    keep = _shallow_jagged_bay_body()
    mouths = _hull_bay_mouths(keep, min_depth=1.0, min_width=4.0)
    assert mouths, "jagged bay was not a hull-bay candidate"
    jagged = False
    for left, right, deep, run in mouths:
        mouth_w = math.hypot(right.x() - left.x(), right.y() - left.y())
        depth = _point_seg_dist(
            deep.x(), deep.y(), left.x(), left.y(), right.x(), right.y())
        assert depth < 0.75 * mouth_w, "fixture is deep, not a κ case"
        assert _bay_kappa(left, right, run, mouth_w=mouth_w) >= 3.0, (
            "fixture needs κ ≥ 3")
        if _bay_should_seal(
                left, right, deep, run, depth=depth, mouth_w=mouth_w):
            jagged = True
    assert jagged, "expected κ ≥ 3 seal on the jagged bay"
    weed = island_hop_weeds(keep, padding=[10, 10, 10, 10], collar=4.0)
    keep_fill = even_odd_keep_fill(keep)
    seals = _keep_to_keep_in_box(weed, keep_fill, 9.0, -0.5, 31.0, 2.5)
    assert seals, "shallow jagged bay was not sealed"


def test_peninsula_detach_uses_neck():
    """Detach is the mouth; both ends meet keep (no floating spur)."""
    keep = _shallow_jagged_bay_body()
    weed = island_hop_weeds(keep, padding=[10, 10, 10, 10], collar=4.0)
    keep_fill = even_odd_keep_fill(keep)
    seals = _keep_to_keep_in_box(weed, keep_fill, 9.0, -0.5, 31.0, 2.5)
    assert seals, "expected a neck seal"
    for x0, y0, x1, y1 in seals:
        assert abs(y1 - y0) < 3.0, "neck seal is not across the mouth: %s" % (
            (x0, y0, x1, y1),)
        assert max(x0, x1) - min(x0, x1) > 12.0, (
            "neck seal does not span the mouth: %s" % ((x0, y0, x1, y1),))
        assert _end_near_keep(x0, y0, keep_fill)
        assert _end_near_keep(x1, y1, keep_fill)
    # Nothing floating among the teeth (y deeper than the neck).
    for x0, y0, x1, y1 in _line_segments(weed):
        mx, my = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
        if keep_fill.contains(QPointF(mx, my)):
            continue
        if not (10.0 <= mx <= 30.0 and 2.4 <= my <= 7.0):
            continue
        raise AssertionError(
            "floating or in-bay spur at %s" % ((x0, y0, x1, y1),))


def _hanging_mark_cluster():
    """Stem + short hanging mark + neighbor (wide inter-stem gap)."""
    p = QPainterPath()
    p.addPath(_rect_path(0, 20, 10, 50))
    p.addPath(_rect_path(14, 20, 4, 12))
    p.addPath(_rect_path(42, 20, 10, 50))
    return p


def test_hanging_mark_pocket_sealed_not_through_cut():
    """Hanging mark pocket/neck is sealed; no through-cut under the arm."""
    keep = _hanging_mark_cluster()
    weed = island_hop_weeds(keep, padding=[10, 10, 10, 10], collar=4.0)
    keep_fill = even_odd_keep_fill(keep)
    # Neck: host (x=10) to mark (x=14) near the mark's inner end (y≈32).
    pocket = _alley_gap_seals(weed, keep_fill, 9.0, 19.0, 30.0, 36.0, min_len=2.0)
    assert pocket, "hanging-mark pocket/neck was not sealed"
    under_arm = []
    for x0, y0, x1, y1 in _line_segments(weed):
        my = 0.5 * (y0 + y1)
        if keep_fill.contains(QPointF(0.5 * (x0 + x1), my)):
            continue
        if not (28.0 <= my <= 36.0):
            continue
        if math.hypot(x1 - x0, y1 - y0) < 16.0:
            continue
        xs = (x0, x1)
        if min(xs) <= 12.0 and max(xs) >= 40.0:
            under_arm.append((x0, y0, x1, y1))
    assert not under_arm, "through-cut under the hanging arm: %s" % under_arm
    cleaned = mod_emit._require_connected_ends(weed, keep, tol=1.5)
    assert _alley_gap_seals(cleaned, keep_fill, 9.0, 19.0, 30.0, 36.0, min_len=2.0)


def _stem_comma_stem_t():
    """i-stem, comma, i-stem, t — frame-attached peninsulas under the baseline."""
    p = QPainterPath()
    p.addPath(_rect_path(10, 10, 6, 36))   # first stem
    p.addPath(_rect_path(22, 34, 6, 14))   # hanging comma-like mark
    p.addPath(_rect_path(40, 10, 6, 36))   # second stem
    p.addPath(_rect_path(52, 8, 6, 38))    # t stem
    p.addPath(_rect_path(52, 8, 14, 6))    # t bar
    return p


def test_frame_peninsula_chain_seals_bottom_wrap():
    """Consecutive stems + hanging mark: bottom necks detach frame peninsulas."""
    keep = _stem_comma_stem_t()
    weed = island_hop_weeds(keep, padding=[10, 10, 10, 10], collar=4.0)
    keep_fill = even_odd_keep_fill(keep)
    # Comma (x~22-28) → second stem (x~40-46) near bottoms (y~40-48).
    comma_i = _alley_gap_seals(
        weed, keep_fill, 20.0, 48.0, 38.0, 50.0, min_len=4.0)
    assert comma_i, "missing comma→stem frame-peninsula seal: %s" % (
        _line_segments(weed),)
    # Second stem → t near bottoms.
    i_t = _alley_gap_seals(
        weed, keep_fill, 44.0, 58.0, 38.0, 50.0, min_len=3.0)
    assert i_t, "missing stem→t frame-peninsula seal"
    assert _residual_traps_for(keep, weed=weed) == []


def _tangent_bay_with_bar():
    """Undercut bowl whose hull mouth chord is tangent (α→0) + nearby bar."""
    # Mouth on y=0 is collinear with the top flanges → α=0 at the lips.
    body = _poly_path((
        (0, 0), (22, 0),
        (22, 8), (12, 20), (12, 40), (48, 40), (48, 20), (38, 8), (38, 0),
        (60, 0), (60, 52), (0, 52),
    ))
    keep = QPainterPath()
    keep.addPath(body)
    keep.addPath(_rect_path(24, -14, 12, 10))
    return keep


def _rect_pocket_body():
    """Rect keep with a deep top U: mouth 16, depth 16 — clear bay corners."""
    return _deep_smooth_bay_body()


def test_bay_corner_to_opposite_coast_one_seal():
    """Constructed U-bay: one dam from a run corner toward the opposite coast."""
    body = _rect_pocket_body()
    mouths = _hull_bay_mouths(body, min_depth=1.0, min_width=4.0)
    assert mouths, "fixture needs a hull bay"
    left, right, deep, run = mouths[0]
    assert _bay_should_seal(left, right, deep, run)
    primary = _closest_bay_mouth_corner(body, left, right, run)
    assert primary is not None
    # >180° weed-side corner near the mouth (lip or bay-facing), not an outer tip.
    d_mouth = _point_seg_dist(
        primary.x(), primary.y(), left.x(), left.y(), right.x(), right.y())
    assert d_mouth <= 2.5, "primary should sit at the mouth, d=%s" % d_mouth

    keep_fill = even_odd_keep_fill(body)
    work = padded_work_rect(body, [8.0, 8.0, 8.0, 8.0])
    pockets = _body_pocket_seals(
        body, keep_fill, work, DEFAULT_CHANNEL_STANDOFF, 2.0, None)
    segs = _line_segments(pockets)
    assert len(segs) == 1, "exactly one dam per mouth, got %s" % segs
    x0, y0, x1, y1 = segs[0]
    # Must cross toward the opposite shore (not graze one wall).
    mid_x = 0.5 * (x0 + x1)
    assert left.x() + 2.0 < mid_x < right.x() - 2.0, (
        "dam should span the bay, got %s" % segs[0])
    # Created peel angles (D012) — not graze-α vs a collinear flange edge.
    ln = math.hypot(x1 - x0, y1 - y0) or 1.0
    ends = (
        (QPointF(x0, y0), (x1 - x0) / ln, (y1 - y0) / ln),
        (QPointF(x1, y1), (x0 - x1) / ln, (y0 - y1) / ln),
    )
    far_ok = False
    for p, wx, wy in ends:
        angles = _created_peel_angles(p, (wx, wy), body)
        if angles is not None and min(angles) >= _ALPHA_MIN_PEEL - 1e-6:
            far_ok = True
    assert far_ok, "coast/wall end should meet α_min=%s" % _ALPHA_MIN_PEEL


def test_bay_mouth_corners_preferred_over_inset_lip():
    """U/C bay: convex-keep mouth corners seal the mouth, not a mid-lip inset."""
    for body in (_deep_smooth_bay_body(), _deep_smooth_c_bay_body()):
        mouths = _hull_bay_mouths(body, min_depth=1.0, min_width=4.0)
        assert mouths, "fixture needs a hull bay"
        left, right, deep, run = mouths[0]
        assert _bay_should_seal(left, right, deep, run)
        keep_fill = even_odd_keep_fill(body)
        work = padded_work_rect(body, [8.0, 8.0, 8.0, 8.0])
        pockets = _body_pocket_seals(
            body, keep_fill, work, DEFAULT_CHANNEL_STANDOFF, 2.0, None)
        segs = _line_segments(pockets)
        assert len(segs) == 1, "exactly one dam per mouth, got %s" % segs
        x0, y0, x1, y1 = segs[0]
        lips = ((left.x(), left.y()), (right.x(), right.y()))

        def _near(a, b, tol=2.5):
            return math.hypot(a[0] - b[0], a[1] - b[1]) <= tol

        ends = ((x0, y0), (x1, y1))
        cornered = (
            (_near(ends[0], lips[0]) and _near(ends[1], lips[1]))
            or (_near(ends[0], lips[1]) and _near(ends[1], lips[0])))
        assert cornered, (
            "expected mouth-corner chord, got %s vs lips %s" % (segs[0], lips))
        mx, my = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
        d_mid = _point_seg_dist(
            mx, my, left.x(), left.y(), right.x(), right.y())
        assert d_mid < 2.0, (
            "seal should sit on the mouth, not ≥2 mm inset: %s d=%s" % (
                segs[0], d_mid))


def test_uneven_tops_mouth_seal_stays_corner_corner():
    """t-bar (y=28) ↔ taller quote (y=26): diagonal corners, not y=26.5 mid-edge.

    Axis-hit slides + loose corner tol used to rank a horizontal mid-edge
    (false class-0 within 1.5 of a vertex) over the real corner pair.
    """
    tbar = _rect_path(88.0, 28.0, 16.0, 8.0)
    quote = _rect_path(120.0, 26.0, 4.0, 16.0)
    keep = QPainterPath()
    keep.addPath(tbar)
    keep.addPath(quote)
    keep_fill = even_odd_keep_fill(keep)
    work = padded_work_rect(keep, [8.0, 8.0, 8.0, 8.0])
    seg = mod_gaps._mouth_seal(
        tbar, quote, QPointF(104.0, 28.0), QPointF(120.0, 26.0),
        1.0, 0.0, 32.0, DEFAULT_CHANNEL_STANDOFF, keep_fill, work, 2.0, None)
    assert seg is not None
    ends = ((seg[0], seg[1]), (seg[2], seg[3]))
    corners = {(104.0, 28.0), (120.0, 26.0)}

    def _near(a, b, tol=1e-6):
        return math.hypot(a[0] - b[0], a[1] - b[1]) <= tol

    assert (
        (_near(ends[0], (104.0, 28.0)) and _near(ends[1], (120.0, 26.0)))
        or (_near(ends[0], (120.0, 26.0)) and _near(ends[1], (104.0, 28.0)))
    ), "expected corner–corner, got %s" % (seg,)
    # Mid-edge impostor must not win class-0.
    assert not mod_rank._near_waste_reflex_corner(
        tbar, QPointF(104.0, 26.5))
    assert mod_rank._endpoint_class(
        QPointF(104.0, 26.5), tbar, path_b=quote) == mod_rules._EP_EDGE


def test_bay_collinear_flange_mouth_is_true_corner_chord():
    """H-like U: mouth chord collinear with flanges still lands on both corners.

    ``_included_angle_deg`` reports α=0 on that chord (edge continuation);
    created peel angles are (90°, 180°) — legal under D012. Regression for
    sliding ~1 unit down the opposite stem.
    """
    body = _deep_smooth_bay_body()
    mouths = _hull_bay_mouths(body, min_depth=1.0, min_width=4.0)
    assert mouths, "fixture needs a hull bay"
    left, right, deep, run = mouths[0]
    assert _bay_should_seal(left, right, deep, run)
    keep_fill = even_odd_keep_fill(body)
    work = padded_work_rect(body, [8.0, 8.0, 8.0, 8.0])
    pockets = _body_pocket_seals(
        body, keep_fill, work, DEFAULT_CHANNEL_STANDOFF, 2.0, None)
    segs = _line_segments(pockets)
    assert len(segs) == 1, "exactly one dam, got %s" % segs
    x0, y0, x1, y1 = segs[0]
    lips = ((left.x(), left.y()), (right.x(), right.y()))
    # Exact corner–corner (no fuse pullback).
    tol = 1e-6

    def _near(a, b):
        return math.hypot(a[0] - b[0], a[1] - b[1]) <= tol

    ends = ((x0, y0), (x1, y1))
    cornered = (
        (_near(ends[0], lips[0]) and _near(ends[1], lips[1]))
        or (_near(ends[0], lips[1]) and _near(ends[1], lips[0])))
    assert cornered, (
        "expected exact corner–corner, got %s vs lips %s" % (
            segs[0], lips))
    d_mid = _point_seg_dist(
        0.5 * (x0 + x1), 0.5 * (y0 + y1),
        left.x(), left.y(), right.x(), right.y())
    assert d_mid < 1e-6, (
        "chord must lie on the mouth line, not inset: %s d=%s" % (
            segs[0], d_mid))


def test_bay_mouth_already_sealed_blocks_second_pass():
    """Multi-pass guard: an existing side↔side dam skips another seal."""
    body = _rect_pocket_body()
    mouths = _hull_bay_mouths(body, min_depth=1.0, min_width=4.0)
    left, right, deep, run = mouths[0]
    keep_fill = even_odd_keep_fill(body)
    work = padded_work_rect(body, [8.0, 8.0, 8.0, 8.0])
    first = _body_pocket_seals(
        body, keep_fill, work, DEFAULT_CHANNEL_STANDOFF, 2.0, None)
    assert _line_segments(first), "expected an initial dam"
    assert _bay_mouth_already_sealed(first, left, right, run=run)
    second = _body_pocket_seals(
        body, keep_fill, work, DEFAULT_CHANNEL_STANDOFF, 2.0, None,
        against=first)
    assert _line_segments(second) == [], "must not fan a second dam"


def test_tangent_bay_seal_has_hard_alpha():
    """Tangent hull mouth reroutes via corner→coast (far end α ≥ peel min)."""
    keep = _tangent_bay_with_bar()
    bodies = list_closed_subpaths(keep)
    body = max(bodies, key=lambda p: p.boundingRect().height()
               * p.boundingRect().width())
    mouths = _hull_bay_mouths(body, min_depth=1.0, min_width=4.0)
    assert mouths, "fixture needs a hull bay mouth"
    left, right, deep, run = mouths[0]
    mw = math.hypot(right.x() - left.x(), right.y() - left.y()) or 1.0
    a_mouth = min(
        _included_angle_deg(
            left,
            ((right.x() - left.x()) / mw, (right.y() - left.y()) / mw),
            body) or 0.0,
        _included_angle_deg(
            right,
            ((left.x() - right.x()) / mw, (left.y() - right.y()) / mw),
            body) or 0.0,
    )
    assert a_mouth < _ALPHA_HARD, (
        "fixture mouth should be near-tangent, got α=%s" % a_mouth)

    pad = [12.0, 12.0, 12.0, 12.0]
    keep_fill = even_odd_keep_fill(keep)
    work = padded_work_rect(keep, pad)
    pockets = _body_pocket_seals(
        body, keep_fill, work, DEFAULT_CHANNEL_STANDOFF, 2.0, None)
    segs = _line_segments(pockets)
    assert segs, "expected a pocket seal on the tangent bay"
    assert len(segs) == 1, "one dam only, got %s" % segs
    x0, y0, x1, y1 = segs[0]
    ln = math.hypot(x1 - x0, y1 - y0) or 1.0
    a0 = _included_angle_deg(
        QPointF(x0, y0), ((x1 - x0) / ln, (y1 - y0) / ln), body)
    a1 = _included_angle_deg(
        QPointF(x1, y1), ((x0 - x1) / ln, (y0 - y1) / ln), body)
    assert a0 is not None and a1 is not None
    # At least one end (coast/wall) meets peel α; corner primary may be tiny.
    assert max(a0, a1) >= _ALPHA_MIN_PEEL - 1e-6, (
        "far-end α below peel min: %s α=(%s,%s)" % (
            (x0, y0, x1, y1), a0, a1))
    assert min(a0, a1) >= 0.0

    weed = island_hop_weeds(keep, padding=pad, collar=4.0)
    assert _residual_traps_for(keep, weed=weed, padding=pad) == []


def test_horizontal_pocket_mouth_emits_chord():
    """When a bay mouth is horizontal, the seal is the lip–lip chord."""
    body = _deep_smooth_bay_body()
    keep_fill = even_odd_keep_fill(body)
    work = padded_work_rect(body, [8.0, 8.0, 8.0, 8.0])
    pockets = _body_pocket_seals(
        body, keep_fill, work, DEFAULT_CHANNEL_STANDOFF, 2.0, None)
    segs = _line_segments(pockets)
    assert len(segs) == 1, segs
    x0, y0, x1, y1 = segs[0]
    assert abs(y0 - y1) < 0.5, "mouth chord should be horizontal: %s" % (segs[0],)
    mouths = _hull_bay_mouths(body, min_depth=1.0, min_width=4.0)
    left, right, _d, _r = mouths[0]
    ends = ((x0, y0), (x1, y1))
    lips = ((left.x(), left.y()), (right.x(), right.y()))

    def near(a, b, tol=1.5):
        return math.hypot(a[0] - b[0], a[1] - b[1]) <= tol

    assert (
        (near(ends[0], lips[0]) and near(ends[1], lips[1]))
        or (near(ends[0], lips[1]) and near(ends[1], lips[0]))
    ), "expected lip–lip chord, got %s vs %s" % (segs[0], lips)


def test_bay_seal_anchors_at_mouth_corner_vertex():
    """Primary mouth corner is an exact emit end (not a mid-edge walk-in)."""
    body = _deep_smooth_c_bay_body()
    mouths = _hull_bay_mouths(body, min_depth=1.0, min_width=4.0)
    assert mouths
    left, right, deep, run = mouths[0]
    primary = _closest_bay_mouth_corner(body, left, right, run)
    assert primary is not None
    keep_fill = even_odd_keep_fill(body)
    work = padded_work_rect(body, [8.0, 8.0, 8.0, 8.0])
    pockets = _body_pocket_seals(
        body, keep_fill, work, DEFAULT_CHANNEL_STANDOFF, 2.0, None)
    segs = _line_segments(pockets)
    assert segs, "expected a bay seal"
    hit = False
    for x0, y0, x1, y1 in segs:
        if (math.hypot(x0 - primary.x(), y0 - primary.y()) <= 1.25
                or math.hypot(x1 - primary.x(), y1 - primary.y()) <= 1.25):
            hit = True
    assert hit, "seal must anchor at corner %s, got %s" % (
        (primary.x(), primary.y()), segs)
