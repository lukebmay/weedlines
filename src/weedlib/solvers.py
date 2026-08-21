# -*- coding: utf-8 -*-
"""Weed-line strategies: frame, grid, island-hop (collar + channels).

Closed design subpaths form keep (stays on liner) by nesting: each keep
island is the body minus its direct holes; sibling islands are *united*
so overlapping design stays keep (keep+keep ≠ waste). A letter O is a
keep ring; the hole is waste and is never released through the ring.
Open strokes never form keep interiors.

Canonical map (D007): **land** = keep (design), **water** = waste
(weedable vinyl), **coast** = keep↔waste frontier. A **bay** is water
into land (mouth); a **peninsula** is land into water (isthmus).
Bay seal uses coastline closure κ = L_coast/L_mouth (classify ≥ 2,
seal if undercut or κ ≥ 3 or depth gate). Corridor = thin channel core
of water between two keep walls; stop side openings when depth > width.
Peel frame (D012) is placed first (full or partial). Frame→letter
gaps are bays. After seals that wall waste, re-analyze residual pieces.
"""
from __future__ import division

import math
from collections import namedtuple

from . import debug as _wdbg
from .qt import QPointF, QRectF, Qt, QPainterPath, QTransform
from .paths import split_painter_path

try:
    import pyclipper
except ImportError:
    pyclipper = None


WEED_MODES = ('frame', 'grid', 'region', 'island-hop', 'auto')  # auto=alias
DEFAULT_WEED_MODE = 'frame'
DEFAULT_GRID_SPACING = 25.0

# Auto peel defaults (device units; mm-scale when job units are mm)
DEFAULT_MAX_CHUNK = 60.0
DEFAULT_BRIDGE_WIDTH = 4.0
DEFAULT_CLEARANCE = 0.5
DEFAULT_MIN_CUT = 2.0
# Above 90° so box corners are not convex "tips"
DEFAULT_DELICATE_ANGLE_DEG = 95.0
DEFAULT_COLLAR = 4.0
DEFAULT_MAX_SPOKES = 24
# D012 hard floors (all modes).
DEFAULT_BODY_CLEARANCE = 5.0
DEFAULT_ALPHA_MIN = 30.0
DEFAULT_FRAME_CLEARANCE = 20.0
# Soft planner band for grow-and-frame standoff (knob stays one number).
_FRAME_CLEARANCE_SOFT_MAX = 30.0
# Channels stop this far from keep so a slight vinyl slip does not nick it.
DEFAULT_CHANNEL_STANDOFF = 1.0
# Legacy bay depth gate (D001); C8 prefers κ/undercut (D007).
DEFAULT_PENINSULA_RATIO = 0.75
# Ray / flare search probe into waste (not an emit endpoint inset).
_SEARCH_PROBE = 0.08
# Legacy C9 α; emit floor is DEFAULT_ALPHA_MIN (D012).
_ALPHA_HARD = 18.0
_ALPHA_GRAZE = 10.0  # connected-ends only
# Alias of DEFAULT_ALPHA_MIN (bay peel-wall / emit floor).
_ALPHA_MIN_PEEL = DEFAULT_ALPHA_MIN
# Endpoint class order for ranking (lower is better).
_EP_CORNER = 0
_EP_FRAME = 1
_EP_EDGE = 2
CutRules = namedtuple(
    'CutRules', 'body_clearance alpha_min frame_clearance')
_D_HUG = 1.6
_PHI_HUG = 18.0
# Visual hug: mid-body near a keep edge (body-clearance scale) and φ small.
_D_HUG_CLOSE = DEFAULT_BODY_CLEARANCE
_A_SLIVER = 8.0
_H_SLIVER = 2.5
_A_GAIN_MIN = 12.0
# Prefer this created-min after a harder coast search; below is α≈40 junk.
_CREATED_PREFER = 55.0
# Mouth joins: drop mediocre created-min when a square-ish cand exists.
_CREATED_MOUTH_PREFER = 70.0
# Grid clip sample gap: snap ends to keep / ortho crossing within this.
_GRID_END_SNAP = 2.0
_CLIPPER_SCALE = 1000.0

# padding indices match job.models.Padding
_LEFT, _TOP, _RIGHT, _BOTTOM = 0, 1, 2, 3


def _cut_rules(body_clearance=None, alpha_min=None, frame_clearance=None):
    """Resolve D012 knobs (defaults 5 / 30° / 20)."""
    return CutRules(
        max(float(body_clearance if body_clearance is not None
                  else DEFAULT_BODY_CLEARANCE), 0.0),
        max(float(alpha_min if alpha_min is not None
                  else DEFAULT_ALPHA_MIN), 0.0),
        max(float(frame_clearance if frame_clearance is not None
                  else DEFAULT_FRAME_CLEARANCE), 0.0),
    )


def generate_weeds(keep_path,
                   mode=DEFAULT_WEED_MODE,
                   padding=None,
                   spacing=DEFAULT_GRID_SPACING,
                   max_chunk=None,
                   bridge_width=None,
                   clearance=None,
                   min_cut=None,
                   delicate_angle_deg=None,
                   collar=None,
                   max_spokes=None,
                   peninsula_ratio=None,
                   body_clearance=None,
                   alpha_min=None,
                   frame_clearance=None):
    """Build a weed QPainterPath for keep geometry.

    Parameters
    ----------
    keep_path : QPainterPath
        Design cuts (blade-down geometry) to protect / nest against.
    mode : str
        ``frame`` | ``grid`` | ``island-hop``. ``region`` aliases ``grid``;
        ``auto`` is a deprecated alias of ``island-hop``.
    padding : sequence of 4 floats, optional
        Left, top, right, bottom pad around keep bbox.
    spacing : float
        Grid pitch (device units).
    max_chunk, bridge_width, clearance, min_cut, delicate_angle_deg,
    collar, max_spokes, peninsula_ratio
        Island-hop physical knobs (ignored by other modes).
    body_clearance, alpha_min, frame_clearance
        D012 floors (island-hop + grid). ``frame`` mode is a closed box.
    """
    if keep_path is None or keep_path.isEmpty():
        return QPainterPath()
    from . import progress as _progress
    _progress.report(mode)
    mode = (mode or DEFAULT_WEED_MODE).strip().lower()
    if mode == 'auto':
        mode = 'island-hop'
    mode = mode if mode in WEED_MODES else DEFAULT_WEED_MODE
    padding = _normalize_padding(padding)
    spacing = max(float(spacing or DEFAULT_GRID_SPACING), 1e-6)
    rules = _cut_rules(body_clearance, alpha_min, frame_clearance)

    if mode == 'frame':
        return frame_weeds(keep_path, padding)
    if mode == 'grid':
        return grid_weeds(
            keep_path, padding, spacing, rules=rules)
    if mode == 'region':
        return grid_weeds(
            keep_path, padding, spacing, rules=rules)
    return island_hop_weeds(
        keep_path,
        padding=padding,
        spacing=spacing,
        max_chunk=max_chunk,
        bridge_width=bridge_width,
        clearance=clearance,
        min_cut=min_cut,
        delicate_angle_deg=delicate_angle_deg,
        collar=collar,
        max_spokes=max_spokes,
        peninsula_ratio=peninsula_ratio,
        body_clearance=rules.body_clearance,
        alpha_min=rules.alpha_min,
        frame_clearance=rules.frame_clearance,
    )


def frame_weeds(keep_path, padding=None):
    """Padded rectangle around keep bbox (legacy weedline)."""
    padding = _normalize_padding(padding)
    rect = _padded_rect(keep_path.boundingRect(), padding)
    out = QPainterPath()
    out.addRect(rect)
    return out


def grid_weeds(keep_path, padding=None, spacing=DEFAULT_GRID_SPACING,
               rules=None, body_clearance=None, alpha_min=None):
    """Axis-aligned grid over padded bbox; omit parts inside even-odd keep."""
    padding = _normalize_padding(padding)
    spacing = max(float(spacing), 1e-6)
    if rules is None:
        rules = _cut_rules(body_clearance, alpha_min, None)
    work = _padded_rect(keep_path.boundingRect(), padding)
    keep_fill = even_odd_keep_fill(keep_path)
    weed = _grid_in_region(
        work, keep_fill, spacing, invert_keep=True,
        keep_path=keep_path, rules=rules)
    weed = _require_connected_ends(weed, keep_path, tol=1.5, work=work)
    return _clip_path_to_rect(weed, work)


def region_weeds(keep_path, padding=None, spacing=DEFAULT_GRID_SPACING):
    """Alias of grid (kept for saved jobs)."""
    return grid_weeds(keep_path, padding, spacing)


def island_hop_weeds(keep_path,
               padding=None,
               spacing=DEFAULT_GRID_SPACING,
               max_chunk=None,
               bridge_width=None,
               clearance=None,
               min_cut=None,
               delicate_angle_deg=None,
               collar=None,
               max_spokes=None,
               peninsula_ratio=None,
               body_clearance=None,
               alpha_min=None,
               frame_clearance=None):
    """Shop peel: peel-frame first, then ranked seals (D012)."""
    return enclosure_weeds(
        keep_path,
        padding=padding,
        spacing=spacing,
        max_chunk=max_chunk,
        bridge_width=bridge_width,
        clearance=clearance,
        min_cut=min_cut,
        delicate_angle_deg=delicate_angle_deg,
        collar=collar,
        max_spokes=max_spokes,
        peninsula_ratio=peninsula_ratio,
        body_clearance=body_clearance,
        alpha_min=alpha_min,
        frame_clearance=frame_clearance,
    )


def auto_weeds(*args, **kwargs):
    """Deprecated alias of :func:`island_hop_weeds`."""
    return island_hop_weeds(*args, **kwargs)



def enclosure_weeds(keep_path,
                    padding=None,
                    spacing=DEFAULT_GRID_SPACING,
                    max_chunk=None,
                    bridge_width=None,
                    clearance=None,
                    min_cut=None,
                    delicate_angle_deg=None,
                    collar=None,
                    max_spokes=None,
                    peninsula_ratio=None,
                    body_clearance=None,
                    alpha_min=None,
                    frame_clearance=None):
    """Simple enclosure + sparse channels per waste face.

    Keep = design (D007 land; nested rings + united siblings), waste =
    peel water. Dispatch is geometric only: island/hole, frame,
    bay/peninsula, corridor, nest.
    Nearby islands share one enclosure. Peel frame first (full/partial).
    Islands merge smallest-first: each cut joins the smallest island to
    another object until one island remains. Waste bays are sealed by
    κ/undercut (per-body, then multi-body mouths no single hull sees).
    Channel cores next; side openings stop when depth > local width;
    T-junction branch necks if two corridors share a body end. Keep-tip
    spokes only if a body has no independent bays. Frame→letter openings
    are bays on the consecutive keep chain. After each seal batch,
    re-analyze residual multi-body waste. A corridor with another island
    in the gap is not sealed across. A keep ring is never cut through.
    Every open weed segment must meet keep or another weed at both ends.
    Keep-to-keep seals must span two distinct bodies.
    """
    padding = _normalize_padding(padding)
    max_chunk = float(max_chunk if max_chunk is not None else DEFAULT_MAX_CHUNK)
    max_chunk = max(max_chunk, 1e-6)
    clearance = float(clearance if clearance is not None else DEFAULT_CLEARANCE)
    min_cut = float(min_cut if min_cut is not None else DEFAULT_MIN_CUT)
    delicate_angle = float(
        delicate_angle_deg if delicate_angle_deg is not None
        else DEFAULT_DELICATE_ANGLE_DEG)
    collar_margin = float(collar if collar is not None else DEFAULT_COLLAR)
    # Clearance is a minimum isolation distance.
    collar_margin = max(collar_margin, clearance, 1e-6)
    pad_room = min(padding) if padding else 0.0
    if pad_room >= 1.0:
        collar_margin = min(collar_margin, pad_room)
    max_spokes = int(max_spokes if max_spokes is not None else DEFAULT_MAX_SPOKES)
    max_spokes = max(max_spokes, 0)
    peninsula_ratio = float(
        peninsula_ratio if peninsula_ratio is not None
        else DEFAULT_PENINSULA_RATIO)
    peninsula_ratio = max(peninsula_ratio, 1e-6)
    rules = _cut_rules(body_clearance, alpha_min, frame_clearance)
    _ = spacing, bridge_width

    work = _padded_rect(keep_path.boundingRect(), padding)
    out = QPainterPath()

    closed = list_closed_subpaths(keep_path)
    if not closed:
        return _clip_path_to_rect(out, work)

    nodes = _nest_closed_paths(closed)
    keep_fill = even_odd_keep_fill(keep_path)
    if keep_fill.isEmpty():
        keep_fill = QPainterPath(keep_path)

    keep_bodies = [n['path'] for n in nodes if n['depth'] % 2 == 0]
    holes = [n for n in nodes if n['depth'] % 2 == 1]
    if not keep_bodies:
        return _clip_path_to_rect(out, work)

    frame_ring = _rect_as_ring(work)
    standoff = max(clearance, DEFAULT_CHANNEL_STANDOFF)
    groups = _enclosure_groups(nodes, collar_margin)
    _wdbg.log(
        'island_hop.start', bodies=len(keep_bodies), holes=len(holes),
        clusters=len(groups), collar=collar_margin,
        body_clearance=rules.body_clearance, alpha_min=rules.alpha_min,
        frame_clearance=rules.frame_clearance, work=_wdbg.bbox_fmt(work))

    # One outer peel + one free working set (chords isolate; no per-box rails).
    free_bodies = []
    contained_groups = []
    for cluster, container in groups:
        if container is not None and not container.isEmpty():
            contained_groups.append((cluster, container))
            continue
        for body in cluster:
            if body is not None and not body.isEmpty():
                free_bodies.append(body)
    shared_frame = QPainterPath()
    shared_rings = []
    if free_bodies:
        shared_frame, shared_rings = _peel_frame_for_cluster(
            free_bodies, keep_fill, work, None, rules.frame_clearance)
        if not shared_frame.isEmpty():
            # Rails: no-cross / redundant only — body-clearance is for seals;
            # standoff is frame_clearance (may be < body_clearance).
            _add_path_segs(out, shared_frame, min_cut)
    work_groups = []
    if free_bodies:
        work_groups.append((free_bodies, None))
    work_groups.extend(contained_groups)

    for gi, (cluster, container) in enumerate(work_groups):
        cbbox = None
        for body in cluster:
            br = body.boundingRect()
            cbbox = QRectF(br) if cbbox is None else cbbox.united(br)
        with _wdbg.phase(
                'cluster[%d]' % gi, n_bodies=len(cluster),
                container=container is not None and not container.isEmpty(),
                bbox=_wdbg.bbox_fmt(cbbox)):
            if container is not None and not container.isEmpty():
                # D013: design container is the wall — no second collar.
                frame_path, used_rings = QPainterPath(), []
                _wdbg.log('peel_frame.skip', reason='design_container_D013')
            else:
                frame_path, used_rings = shared_frame, shared_rings
                if frame_path.isEmpty() and not shared_rings:
                    _wdbg.log('peel_frame.skip', reason='shared_empty')
            # Peel-frame rings, else design-container coast (D013).
            wall_rings = _opening_wall_rings(used_rings, container)
            spoke_bodies = False
            body_tips = []
            for body in cluster:
                tips = _deep_keep_peninsula_tips(body, delicate_angle)
                body_tips.append(tips)
            outer_bodies = _outside_in_bodies(cluster, work, container)
            tip_map = dict((id(b), t) for b, t in zip(cluster, body_tips))
            with _wdbg.phase('body_pockets'):
                for body in outer_bodies:
                    out.addPath(_body_pocket_seals(
                        body, keep_fill, work, standoff, min_cut,
                        container=container,
                        keep_tips=tip_map.get(id(body)) or (),
                        peninsula_ratio=peninsula_ratio, against=out,
                        rules=rules, peel_frame=frame_path))
            if len(cluster) >= 2:
                with _wdbg.phase('frame_peninsulas'):
                    out.addPath(_seal_frame_peninsulas(
                        cluster, keep_fill, work, standoff, min_cut, container,
                        against=out, peninsula_ratio=peninsula_ratio,
                        collar_rings=wall_rings, rules=rules,
                        peel_frame=frame_path))
                with _wdbg.phase('compact_ties'):
                    out.addPath(_seal_compact_islands(
                        cluster, keep_fill, work, standoff, min_cut, container,
                        against=out, rules=rules, peel_frame=frame_path))
                with _wdbg.phase('agglomerate'):
                    fuse_path, _groups, _sat_ids = _agglomerate_islands(
                        cluster, keep_fill, work, standoff, min_cut, container,
                        max_chunk=max_chunk, rules=rules,
                        peel_frame=frame_path, against=out)
                    out.addPath(fuse_path)
            for body in cluster:
                tips = tip_map.get(id(body)) or ()
                if (tips and not _has_independent_waste_bays(
                        body, tips, standoff, min_cut,
                        peninsula_ratio=peninsula_ratio)):
                    out.addPath(_tip_spokes(
                        tips, used_rings, frame_ring, keep_fill, work,
                        clearance=standoff, min_cut=min_cut,
                        max_spokes=max_spokes, against=out))
                    spoke_bodies = True
            # Residual multi-body water re-analysis (D007).
            for _pass in range(3):
                before = weed_path_stats(out)['segments']
                with _wdbg.phase('residual[%d]' % _pass, segs_before=before):
                    for body in outer_bodies:
                        out.addPath(_body_pocket_seals(
                            body, keep_fill, work, standoff, min_cut,
                            container=container,
                            keep_tips=tip_map.get(id(body)) or (),
                            peninsula_ratio=peninsula_ratio, against=out,
                            rules=rules, peel_frame=frame_path))
                    if len(cluster) >= 2:
                        out.addPath(_cluster_bay_seals(
                            cluster, keep_fill, work, standoff, min_cut,
                            container, against=out,
                            peninsula_ratio=peninsula_ratio,
                            rules=rules, peel_frame=frame_path,
                            collar_rings=wall_rings))
                        out.addPath(_seal_compact_islands(
                            cluster, keep_fill, work, standoff, min_cut,
                            container, against=out, rules=rules,
                            peel_frame=frame_path))
                        out.addPath(_seal_divergent_corridors(
                            cluster, keep_fill, work, standoff, min_cut,
                            container, against=out, max_chunk=max_chunk,
                            rules=rules, peel_frame=frame_path))
                        out.addPath(_leftover_hanging_gutters(
                            cluster, keep_fill, work, standoff, min_cut,
                            container, against=out, rules=rules,
                            peel_frame=frame_path))
                        if wall_rings and not _has_keep_to_collar_channel(
                                out, cluster, wall_rings, standoff):
                            outline = _cluster_keep_outline(cluster)
                            if outline is not None:
                                ch = _shortest_outer_channel(
                                    outline, wall_rings, keep_fill, work,
                                    min_cut, clearance=standoff,
                                    container=container)
                                if ch is not None and _seg_forced_ok(
                                        ch, keep_path, out, rules,
                                        peel_frame=frame_path):
                                    _add_seg(out, ch, min_cut)
                        out.addPath(_seal_frame_peninsulas(
                            cluster, keep_fill, work, standoff, min_cut,
                            container, against=out,
                            peninsula_ratio=peninsula_ratio,
                            collar_rings=wall_rings, rules=rules,
                            peel_frame=frame_path))
                if weed_path_stats(out)['segments'] <= before:
                    break
            if (len(cluster) < 2 and wall_rings
                    and not _has_keep_to_collar_channel(
                        out, cluster, wall_rings, standoff)):
                ch = _shortest_outer_channel(
                    cluster[0], wall_rings, keep_fill, work, min_cut,
                    clearance=standoff, container=container)
                if ch is not None and _seg_forced_ok(
                        ch, keep_path, out, rules, peel_frame=frame_path):
                    _add_seg(out, ch, min_cut)

    for node in holes:
        if node['children']:
            continue
        hole = QPainterPath(node['path'])
        if hole.isEmpty():
            continue
        out.addPath(_hole_internal_splits(
            hole, keep_fill, max_chunk, min_cut))

    # Drop hugs / slivers / needless optionals, then require connected ends.
    # Hugs vs keep fill (land outline), not raw design subpaths.
    out = _drop_parallel_hugs(out, keep_fill, min_cut)
    out = _drop_slivers_and_needless(out, keep_path)
    anchor_tol = max(1.5, standoff + 0.25)
    out = _require_connected_ends(
        out, keep_path, tol=anchor_tol, work=work)
    out = _clip_path_to_rect(out, work)
    if _wdbg.enabled():
        _audit_firm_rules(out, keep_path, rules)
        stats = weed_path_stats(out)
        _wdbg.log('island_hop.done', segs=stats['segments'], length=stats['length'])
    return out


def even_odd_keep_fill(path):
    """Design keep fill: rings keep holes, sibling keep islands *union*.

    Nested holes (letter O counter, frame interior) stay waste. Overlapping
    design islands stay keep — keep∩keep is still design vinyl, never
    weedable. (Plain even-odd XOR would punch an overlap into waste.)

    Historical name kept for callers; nesting is containment-based, not a
    global even-odd of every subpath.
    """
    return design_keep_fill(path)


def design_keep_fill(path):
    """Union of keep islands (each island = body minus its direct holes)."""
    fill = QPainterPath()
    closed = list_closed_subpaths(path)
    if not closed:
        return fill
    nodes = _nest_closed_paths(closed)
    for node in nodes:
        if node['depth'] % 2 != 0:
            continue
        solid = QPainterPath(node['path'])
        for child in node['children']:
            # Direct hole in this keep body (odd relative nesting).
            if child['depth'] == node['depth'] + 1:
                try:
                    solid = solid.subtracted(child['path'])
                except Exception:
                    # Older Qt: fall back to even-odd of body+hole only.
                    hole_fill = QPainterPath()
                    hole_fill.setFillRule(Qt.OddEvenFill)
                    hole_fill.addPath(node['path'])
                    hole_fill.addPath(child['path'])
                    solid = hole_fill
        if solid.isEmpty():
            continue
        fill = solid if fill.isEmpty() else fill.united(solid)
    if fill.isEmpty():
        # Degenerate: single open strokes / empty nest — last resort.
        fill.setFillRule(Qt.OddEvenFill)
        for sp in closed:
            fill.addPath(sp)
    return fill


# Older name; same design keep fill (not a solid disk of every outline).
closed_fill_union = even_odd_keep_fill


def list_closed_subpaths(path, tol=1e-4):
    """Return closed subpaths of *path* (start≈end, enough elements)."""
    result = []
    for sp in split_painter_path(path):
        if _subpath_is_closed(sp, tol=tol):
            result.append(sp)
    return result


def padded_work_rect(keep_path, padding=None):
    """Padded work rectangle around keep bbox."""
    return _padded_rect(keep_path.boundingRect(), _normalize_padding(padding))


def _normalize_padding(padding):
    if not padding:
        return [0.0, 0.0, 0.0, 0.0]
    pad = list(padding)
    while len(pad) < 4:
        pad.append(0.0)
    return [float(pad[i]) for i in range(4)]


def _padded_rect(bbox, padding):
    x = bbox.x() - padding[_LEFT]
    y = bbox.y() - padding[_TOP]
    w = bbox.width() + padding[_LEFT] + padding[_RIGHT]
    h = bbox.height() + padding[_TOP] + padding[_BOTTOM]
    return QRectF(x, y, w, h)


def _subpath_is_closed(sp, tol=1e-4):
    n = sp.elementCount()
    if n < 3:
        return False
    e0 = sp.elementAt(0)
    eN = sp.elementAt(n - 1)
    return (abs(e0.x - eN.x) <= tol and abs(e0.y - eN.y) <= tol)


def _polyline_points(path, max_pts=256):
    """Flattened outline vertices (curves sampled; Bezier controls omitted)."""
    pts = []
    polys = _subpath_polygons(path)
    if not polys:
        return pts
    for p in polys[0]:
        pt = QPointF(p)
        if pts and abs(pts[-1].x() - pt.x()) < 1e-12 and abs(
                pts[-1].y() - pt.y()) < 1e-12:
            continue
        pts.append(pt)
    if len(pts) <= max_pts:
        return pts
    step = max(len(pts) // max_pts, 1)
    return pts[::step]


def _subpath_polygons(path):
    if path is None or path.isEmpty():
        return []
    try:
        polys = path.toSubpathPolygons()
    except TypeError:
        polys = path.toSubpathPolygons(QTransform())
    return list(polys)


def _unique_ring(pts, tol=1e-6):
    """Drop a closing duplicate so the ring can be indexed modulo n."""
    if len(pts) >= 2 and math.hypot(
            pts[0].x() - pts[-1].x(), pts[0].y() - pts[-1].y()) <= tol:
        return pts[:-1]
    return pts


def _signed_area(pts):
    ring = _unique_ring(pts)
    n = len(ring)
    if n < 3:
        return 0.0
    acc = 0.0
    for i in range(n):
        j = (i + 1) % n
        acc += ring[i].x() * ring[j].y() - ring[j].x() * ring[i].y()
    return acc * 0.5


def _shoelace_area(pts):
    return abs(_signed_area(pts))


def _polygon_centroid(pts):
    ring = _unique_ring(pts)
    n = len(ring)
    if n < 1:
        return QPointF(0.0, 0.0)
    if n < 3:
        sx = sum(p.x() for p in ring) / float(n)
        sy = sum(p.y() for p in ring) / float(n)
        return QPointF(sx, sy)
    acc = 0.0
    cx = cy = 0.0
    for i in range(n):
        j = (i + 1) % n
        cross = ring[i].x() * ring[j].y() - ring[j].x() * ring[i].y()
        acc += cross
        cx += (ring[i].x() + ring[j].x()) * cross
        cy += (ring[i].y() + ring[j].y()) * cross
    if abs(acc) < 1e-18:
        sx = sum(p.x() for p in ring) / float(n)
        sy = sum(p.y() for p in ring) / float(n)
        return QPointF(sx, sy)
    return QPointF(cx / (3.0 * acc), cy / (3.0 * acc))


def _path_area(path):
    """Polygon area (not bbox)."""
    pts = _unique_ring(_polyline_points(path))
    area = _shoelace_area(pts)
    if area > 1e-12:
        return area
    r = path.boundingRect()
    return abs(r.width() * r.height())


def _path_centroid(path):
    pts = _polyline_points(path)
    if len(pts) >= 3:
        return _polygon_centroid(pts)
    r = path.boundingRect()
    return QPointF(r.center())


def _interior_point(path):
    """A point inside the filled path — not bbox-center (may lie outside)."""
    pts = _unique_ring(_polyline_points(path))
    if len(pts) >= 3:
        c = _polygon_centroid(pts)
        if path.contains(c):
            return c
        n = len(pts)
        for i in range(n):
            a, b = pts[i], pts[(i + 1) % n]
            mx = 0.5 * (a.x() + b.x())
            my = 0.5 * (a.y() + b.y())
            ex, ey = b.x() - a.x(), b.y() - a.y()
            nx, ny = -ey, ex
            ln = math.hypot(nx, ny) or 1.0
            nx, ny = nx / ln, ny / ln
            for sign in (1.0, -1.0):
                probe = QPointF(mx + sign * nx * 0.75, my + sign * ny * 0.75)
                if path.contains(probe):
                    return probe
    br = path.boundingRect()
    for i in range(1, 8):
        for j in range(1, 8):
            p = QPointF(
                br.left() + br.width() * i / 8.0,
                br.top() + br.height() * j / 8.0)
            if path.contains(p):
                return p
    return QPointF(br.center())


def _nest_closed_paths(closed_paths):
    """Parent/children by interior-point containment + smaller polygon area."""
    nodes = []
    for p in closed_paths:
        nodes.append({
            'path': p,
            'area': _path_area(p),
            'inside': _interior_point(p),
            'parent': None,
            'children': [],
            'depth': 0,
        })
    for i, child in enumerate(nodes):
        best = None
        best_area = None
        probe = child['inside']
        for j, parent in enumerate(nodes):
            if i == j:
                continue
            if parent['area'] <= child['area']:
                continue
            if not parent['path'].contains(probe):
                continue
            if best is None or parent['area'] < best_area:
                best = parent
                best_area = parent['area']
        if best is not None:
            child['parent'] = best
            best['children'].append(child)
    for node in nodes:
        depth = 0
        p = node['parent']
        while p is not None:
            depth += 1
            p = p['parent']
        node['depth'] = depth
    return nodes


def _rect_contains_inclusive(rect, x, y, eps=1e-6):
    return (
        rect.left() - eps <= x <= rect.right() + eps
        and rect.top() - eps <= y <= rect.bottom() + eps)


def _clip_seg_to_rect(x0, y0, x1, y1, rect):
    """Liang-Barsky clip of a segment to *rect*. None if fully outside."""
    dx = x1 - x0
    dy = y1 - y0
    t0, t1 = 0.0, 1.0
    edges = (
        (-dx, x0 - rect.left()),
        (dx, rect.right() - x0),
        (-dy, y0 - rect.top()),
        (dy, rect.bottom() - y0),
    )
    for p, q in edges:
        if abs(p) < 1e-15:
            if q < 0.0:
                return None
            continue
        t = q / p
        if p < 0.0:
            if t > t1:
                return None
            if t > t0:
                t0 = t
        else:
            if t < t0:
                return None
            if t < t1:
                t1 = t
    return (x0 + t0 * dx, y0 + t0 * dy, x0 + t1 * dx, y0 + t1 * dy)


def _clip_path_to_rect(path, rect):
    """Clip every line segment of *path* to *rect* (curves become end lines)."""
    out = QPainterPath()
    if path is None or path.isEmpty() or rect is None or rect.isEmpty():
        return out
    x0 = y0 = None
    for i in range(path.elementCount()):
        e = path.elementAt(i)
        if e.isMoveTo():
            x0, y0 = e.x, e.y
            continue
        x1, y1 = e.x, e.y
        if x0 is not None:
            seg = _clip_seg_to_rect(x0, y0, x1, y1, rect)
            if seg is not None:
                if math.hypot(seg[2] - seg[0], seg[3] - seg[1]) >= 1e-9:
                    out.moveTo(seg[0], seg[1])
                    out.lineTo(seg[2], seg[3])
        x0, y0 = x1, y1
    return out


def _point_allowed(x, y, region_path, invert_keep):
    """If invert_keep, region is keep-fill (allow outside). Else allow inside."""
    if region_path is None or region_path.isEmpty():
        return True
    inside = region_path.contains(QPointF(x, y))
    return (not inside) if invert_keep else inside


def _refine_allowed_end(xa, ya, xb, yb, region_path, invert_keep, steps=24):
    """Last allowed point on segment a→b (*a* allowed, *b* forbidden)."""
    ax, ay, fx, fy = xa, ya, xb, yb
    for _ in range(steps):
        mx = 0.5 * (ax + fx)
        my = 0.5 * (ay + fy)
        if _point_allowed(mx, my, region_path, invert_keep):
            ax, ay = mx, my
        else:
            fx, fy = mx, my
    return ax, ay


def _clip_line_to_region(x0, y0, x1, y1, region_path, invert_keep,
                        samples=64, min_len=0.5):
    """Return list of (x0,y0,x1,y1) segments allowed by region test."""
    n = max(int(samples), 8)
    flags = []
    pts = []
    for i in range(n + 1):
        t = i / float(n)
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * t
        pts.append((x, y))
        flags.append(_point_allowed(x, y, region_path, invert_keep))

    def _run_seg(i0, i1, refine_start, refine_end_to):
        xa, ya = pts[i0]
        xb, yb = pts[i1]
        if refine_start and i0 > 0:
            xa, ya = _refine_allowed_end(
                xa, ya, pts[i0 - 1][0], pts[i0 - 1][1],
                region_path, invert_keep)
        if refine_end_to is not None:
            xb, yb = _refine_allowed_end(
                xb, yb, refine_end_to[0], refine_end_to[1],
                region_path, invert_keep)
        if math.hypot(xb - xa, yb - ya) >= min_len:
            return (xa, ya, xb, yb)
        return None

    segs = []
    run = None
    for i, ok in enumerate(flags):
        if ok:
            if run is None:
                run = i
        else:
            if run is not None and i - 1 >= run:
                seg = _run_seg(
                    run, i - 1, refine_start=True, refine_end_to=pts[i])
                if seg is not None:
                    segs.append(seg)
            run = None
    if run is not None and n >= run:
        seg = _run_seg(run, n, refine_start=True, refine_end_to=None)
        if seg is not None:
            segs.append(seg)
    return segs


def _add_line_segs(out, segs):
    for x0, y0, x1, y1 in segs:
        out.moveTo(x0, y0)
        out.lineTo(x1, y1)


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
    if _point_near_edges(px, py, keep_edges, tol=0.15):
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
                   keep_path=None, rules=None):
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
        v_segs.extend(_clip_line_to_region(
            x, y0, x, y1, region_path, invert_keep=invert_keep))
        x += spacing

    y = y0
    while y <= y1 + 1e-9:
        ys.append(y)
        h_segs.extend(_clip_line_to_region(
            x0, y, x1, y, region_path, invert_keep=invert_keep))
        y += spacing

    if invert_keep and region_path is not None and not region_path.isEmpty():
        keep_edges = _keep_outline_edges(region_path)
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
            if _seg_emit_ok(seg, keep_path, None, rules, other_segs=kept):
                kept.append(seg)
        segs = kept
    _add_line_segs(out, segs)
    return out


def _require_pyclipper():
    if pyclipper is None:
        raise RuntimeError(
            "island-hop collar requires pyclipper; install with: "
            "pip install pyclipper")
    return pyclipper


def _path_to_rings(path):
    """Closed rings as lists of QPointF (no closing duplicate)."""
    rings = []
    for poly in _subpath_polygons(path):
        pts = [QPointF(p) for p in poly]
        ring = _unique_ring(pts)
        if len(ring) >= 3:
            rings.append(ring)
    return rings


def _rings_to_path(rings):
    out = QPainterPath()
    for ring in rings:
        if len(ring) < 3:
            continue
        out.moveTo(ring[0])
        for p in ring[1:]:
            out.lineTo(p)
        out.closeSubpath()
    return out


def _ensure_ccw(ring):
    if _signed_area(ring) < 0:
        return list(reversed(ring))
    return list(ring)


def _rect_as_ring(rect):
    return [
        QPointF(rect.left(), rect.top()),
        QPointF(rect.right(), rect.top()),
        QPointF(rect.right(), rect.bottom()),
        QPointF(rect.left(), rect.bottom()),
    ]


def _ring_to_clipper(ring, scale):
    return [
        (int(round(p.x() * scale)), int(round(p.y() * scale)))
        for p in ring
    ]


def _clipper_to_ring(cpath, scale):
    return [QPointF(x / scale, y / scale) for x, y in cpath]


def _offset_rings(rings, delta, max_pts=72):
    """True outward offset (round joins). Empty if nothing to emit."""
    clip = _require_pyclipper()
    scale = _CLIPPER_SCALE
    if not rings or abs(delta) < 1e-12:
        return [list(r) for r in rings]
    pc = clip.PyclipperOffset()
    pc.ArcTolerance = max(scale * 0.35, 2.0)
    for ring in rings:
        ccw = _ensure_ccw(ring)
        if len(ccw) < 3:
            continue
        pc.AddPath(
            _ring_to_clipper(ccw, scale),
            clip.JT_ROUND,
            clip.ET_CLOSEDPOLYGON)
    raw = pc.Execute(float(delta) * scale)
    rings_out = [_clipper_to_ring(r, scale) for r in raw if len(r) >= 3]
    return [_simplify_ring(r, 0.45, max_pts=max_pts) for r in rings_out]


def _rdp(pts, epsilon):
    if len(pts) < 3:
        return list(pts)
    ax, ay = pts[0].x(), pts[0].y()
    bx, by = pts[-1].x(), pts[-1].y()
    dx, dy = bx - ax, by - ay
    ln = math.hypot(dx, dy)
    max_d = -1.0
    idx = 0
    for i in range(1, len(pts) - 1):
        if ln < 1e-15:
            d = math.hypot(pts[i].x() - ax, pts[i].y() - ay)
        else:
            d = abs((pts[i].x() - ax) * dy - (pts[i].y() - ay) * dx) / ln
        if d > max_d:
            max_d = d
            idx = i
    if max_d > epsilon:
        left = _rdp(pts[:idx + 1], epsilon)
        right = _rdp(pts[idx:], epsilon)
        return left[:-1] + right
    return [pts[0], pts[-1]]


def _simplify_ring(ring, epsilon, max_pts=36):
    if len(ring) <= 4:
        return ring
    pts = list(ring) + [ring[0]]
    simple = _rdp(pts, epsilon)
    if simple and math.hypot(
            simple[0].x() - simple[-1].x(),
            simple[0].y() - simple[-1].y()) <= 1e-9:
        simple = simple[:-1]
    if len(simple) < 3:
        return ring
    if len(simple) > max_pts:
        n = len(simple)
        simple = [
            simple[int(i * n / float(max_pts)) % n]
            for i in range(max_pts)
        ]
    return simple


def _convex_hull(points):
    pts = sorted(set((p.x(), p.y()) for p in points))
    if len(pts) <= 2:
        return [QPointF(x, y) for x, y in pts]

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    ring = lower[:-1] + upper[:-1]
    return [QPointF(x, y) for x, y in ring]


def _ellipse_collar_rings(keep_bodies, delta):
    acc = None
    for body in keep_bodies:
        br = body.boundingRect()
        acc = QRectF(br) if acc is None else acc.united(br)
    if acc is None or acc.isEmpty():
        return []
    p = QPainterPath()
    p.addEllipse(acc.adjusted(-delta, -delta, delta, delta))
    return _path_to_rings(p)


def _bbox_gap(a, b):
    """Separation between two path bboxes (0 if they overlap)."""
    ra, rb = a.boundingRect(), b.boundingRect()
    ox = max(0.0, ra.left() - rb.right(), rb.left() - ra.right())
    oy = max(0.0, ra.top() - rb.bottom(), rb.top() - ra.bottom())
    y_overlap = ra.top() < rb.bottom() and rb.top() < ra.bottom()
    x_overlap = ra.left() < rb.right() and rb.left() < ra.right()
    if x_overlap and y_overlap:
        return 0.0
    if y_overlap:
        return ox
    if x_overlap:
        return oy
    return math.hypot(ox, oy)


def _word_cluster_gap(keep_bodies, collar):
    """How close two islands must be to share one enclosure."""
    heights = [b.boundingRect().height() for b in keep_bodies if not b.isEmpty()]
    heights.sort()
    mid_h = heights[len(heights) // 2] if heights else 0.0
    return max(4.0 * float(collar), 0.55 * mid_h, 1.0)


def _cluster_keep_bodies(keep_bodies, gap):
    """Union-find: nearby islands share one enclosure."""
    n = len(keep_bodies)
    if n <= 1:
        return [list(keep_bodies)]
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(n):
        for j in range(i + 1, n):
            if _bbox_gap(keep_bodies[i], keep_bodies[j]) <= gap:
                a, b = find(i), find(j)
                if a != b:
                    parent[b] = a
    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(keep_bodies[i])
    return list(groups.values())


def _aabb_collar_rings(keep_bodies, delta):
    """One enclosure around a multi-island cluster."""
    acc = None
    for body in keep_bodies:
        if body is None or body.isEmpty():
            continue
        br = body.boundingRect()
        acc = QRectF(br) if acc is None else acc.united(br)
    if acc is None or acc.isEmpty():
        return []
    ring = _rect_as_ring(acc)
    try:
        offset = _offset_rings([ring], float(delta), max_pts=16)
        if offset:
            return offset
    except RuntimeError:
        raise
    except Exception:
        pass
    pad = float(delta)
    return [_rect_as_ring(acc.adjusted(-pad, -pad, pad, pad))]


def _point_in_convex(pt, hull, margin=0.0):
    """True if *pt* is inside convex *hull* by at least *margin*."""
    n = len(hull)
    if n < 3:
        return False
    ring = _ensure_ccw(hull)
    for i in range(n):
        a, b = ring[i], ring[(i + 1) % n]
        ex, ey = b.x() - a.x(), b.y() - a.y()
        ln = math.hypot(ex, ey) or 1.0
        # inward normal for CCW
        nx, ny = -ey / ln, ex / ln
        dist = (pt.x() - a.x()) * nx + (pt.y() - a.y()) * ny
        if dist < margin:
            return False
    return True


def _split_interior_groups(bodies, collar):
    """Peel keep that sits inside a surrounding design separately."""
    if len(bodies) < 3:
        return [list(bodies)]
    pts = []
    for b in bodies:
        pts.extend(_unique_ring(_polyline_points(b, max_pts=48)))
    hull = _convex_hull(pts)
    if len(hull) < 3:
        return [list(bodies)]
    margin = max(float(collar), 2.0)
    interior, border = [], []
    for b in bodies:
        probe = _interior_point(b)
        if _point_in_convex(probe, hull, margin=margin):
            interior.append(b)
        else:
            border.append(b)
    if not interior or not border:
        return [list(bodies)]
    # Few tiny hull-vertex specks are not a surrounding ornament ring.
    interior_peak = max(_path_area(b) for b in interior)
    border_peak = max(_path_area(b) for b in border)
    if border_peak < 0.5 * interior_peak and len(border) <= 5:
        return [list(bodies)]
    # Similar-scale interior and border are a word, not an ornament ring.
    if (interior_peak > 0.35 * border_peak
            and border_peak > 0.35 * interior_peak):
        return [list(bodies)]
    out = [border]
    out.extend(_split_interior_groups(interior, collar))
    return out


def _enclosure_groups(nodes, collar):
    """(cluster, container_or_None) per waste face.

    Siblings only — a frame is not clustered with islands in its hole.
    Among siblings, hull-interior islands split off a surrounding ring.
    """
    by_parent = {}
    for n in nodes:
        if n['depth'] % 2 != 0:
            continue
        key = id(n['parent']) if n['parent'] is not None else None
        by_parent.setdefault(key, []).append(n)
    groups = []
    for knodes in by_parent.values():
        bodies = [n['path'] for n in knodes]
        container = None
        parent = knodes[0]['parent']
        if parent is not None:
            container = parent['path']
        gap = _word_cluster_gap(bodies, collar)
        clustered = _cluster_keep_bodies(bodies, gap)
        if _wdbg.enabled():
            _wdbg.log(
                'cluster.gap', sibling_bodies=len(bodies),
                gap=gap, collar=collar,
                raw_clusters=len(clustered),
                container=container is not None and not container.isEmpty())
            for ci, cl in enumerate(clustered):
                parts = []
                for b in cl:
                    br = b.boundingRect()
                    parts.append('x=%.0f y=%.0f w=%.0f h=%.0f' % (
                        br.x(), br.y(), br.width(), br.height()))
                _wdbg.log(
                    'cluster.raw', idx=ci, n=len(cl), bodies=parts)
        for cluster in clustered:
            for sub in _split_interior_groups(cluster, collar):
                if _wdbg.enabled() and len(sub) != len(cluster):
                    _wdbg.log(
                        'cluster.split_interior',
                        parent_n=len(cluster), child_n=len(sub))
                groups.append((sub, container))
    return groups


def _clip_path_to_waste(path, keep_fill, container=None):
    """Keep only segments in waste, and inside *container* when set."""
    out = QPainterPath()
    if path is None or path.isEmpty():
        return out
    x0 = y0 = None
    for i in range(path.elementCount()):
        e = path.elementAt(i)
        if e.isMoveTo():
            x0, y0 = e.x, e.y
            continue
        x1, y1 = e.x, e.y
        if x0 is not None:
            segs = [(x0, y0, x1, y1)]
            if keep_fill is not None and not keep_fill.isEmpty():
                nxt = []
                for s in segs:
                    nxt.extend(_clip_line_to_region(
                        s[0], s[1], s[2], s[3], keep_fill, invert_keep=True,
                        samples=32, min_len=0.4))
                segs = nxt
            if container is not None and not container.isEmpty():
                nxt = []
                for s in segs:
                    nxt.extend(_clip_line_to_region(
                        s[0], s[1], s[2], s[3], container, invert_keep=False,
                        samples=32, min_len=0.4))
                segs = nxt
            _add_line_segs(out, segs)
        x0, y0 = x1, y1
    return out


def _prefer_hull_collar(keep_bodies, delicate_angle):
    """Simple enclosure (hull) around a cluster; not a per-letter halo."""
    _ = keep_bodies, delicate_angle
    return True


def _isolation_collar_rings(keep_bodies, delta, prefer_hull=False):
    """Offset of outer keep only (never hole contours)."""
    rings = []
    for body in keep_bodies:
        rings.extend(_path_to_rings(body))
    if not rings:
        return []
    source = rings
    max_pts = 32 if prefer_hull else 72
    if prefer_hull:
        pts = [p for ring in rings for p in ring]
        hull = _convex_hull(pts)
        if len(hull) >= 3:
            source = [hull]
    try:
        offset = _offset_rings(source, delta, max_pts=max_pts)
        if offset:
            return offset
    except RuntimeError:
        raise
    except Exception:
        offset = []
    if source is not rings:
        try:
            offset = _offset_rings(rings, delta, max_pts=72)
            if offset:
                return offset
        except RuntimeError:
            raise
        except Exception:
            pass
    pts = [p for ring in rings for p in ring]
    hull = _convex_hull(pts)
    if len(hull) >= 3:
        try:
            offset = _offset_rings([hull], delta, max_pts=32)
            if offset:
                return offset
        except RuntimeError:
            raise
        except Exception:
            pass
    return _ellipse_collar_rings(keep_bodies, delta)


def _angle_turn_deg(p0, p1, p2):
    """Exterior turn angle at p1 in degrees (0 = straight, 180 = reverse)."""
    v1x, v1y = p0.x() - p1.x(), p0.y() - p1.y()
    v2x, v2y = p2.x() - p1.x(), p2.y() - p1.y()
    n1 = math.hypot(v1x, v1y)
    n2 = math.hypot(v2x, v2y)
    if n1 < 1e-12 or n2 < 1e-12:
        return 0.0
    v1x, v1y = v1x / n1, v1y / n1
    v2x, v2y = v2x / n2, v2y / n2
    dot = max(-1.0, min(1.0, v1x * v2x + v1y * v2y))
    interior = math.degrees(math.acos(dot))
    return 180.0 - interior


def _orient_outward(px, py, nx, ny, keep_path):
    """Flip (nx, ny) so it points out of keep at (px, py)."""
    ln = math.hypot(nx, ny) or 1.0
    nx, ny = nx / ln, ny / ln
    probe = 2.0
    a = QPointF(px + nx * probe, py + ny * probe)
    b = QPointF(px - nx * probe, py - ny * probe)
    a_in = keep_path.contains(a)
    b_in = keep_path.contains(b)
    if a_in and not b_in:
        return -nx, -ny
    if b_in and not a_in:
        return nx, ny
    c = _path_centroid(keep_path)
    if nx * (c.x() - px) + ny * (c.y() - py) > 0:
        return -nx, -ny
    return nx, ny


def _outward_normal_at_corner(p0, p1, p2, keep_path):
    """Unit direction from corner into waste (away from keep interior)."""
    v1x, v1y = p0.x() - p1.x(), p0.y() - p1.y()
    v2x, v2y = p2.x() - p1.x(), p2.y() - p1.y()
    n1 = math.hypot(v1x, v1y) or 1.0
    n2 = math.hypot(v2x, v2y) or 1.0
    v1x, v1y = v1x / n1, v1y / n1
    v2x, v2y = v2x / n2, v2y / n2
    bx, by = v1x + v2x, v1y + v2y
    bn = math.hypot(bx, by)
    if bn < 1e-9:
        bx, by = -v1y, v1x
        bn = 1.0
    return _orient_outward(p1.x(), p1.y(), bx / bn, by / bn, keep_path)


def _iter_line_segs(path):
    if path is None or path.isEmpty():
        return
    x0 = y0 = None
    for i in range(path.elementCount()):
        e = path.elementAt(i)
        if e.isMoveTo():
            x0, y0 = e.x, e.y
            continue
        x1, y1 = e.x, e.y
        if x0 is not None:
            yield (x0, y0, x1, y1)
        x0, y0 = x1, y1


def _seg_proper_cross(ax, ay, bx, by, cx, cy, dx, dy, eps=1e-4):
    """True if interiors of ab and cd cross (T-junctions are not a cross)."""
    den = (bx - ax) * (dy - cy) - (by - ay) * (dx - cx)
    if abs(den) < 1e-18:
        return False
    t = ((cx - ax) * (dy - cy) - (cy - ay) * (dx - cx)) / den
    u = ((cx - ax) * (by - ay) - (cy - ay) * (bx - ax)) / den
    return eps < t < 1.0 - eps and eps < u < 1.0 - eps


def _seg_crosses_path(path, seg):
    x0, y0, x1, y1 = seg
    for s in _iter_line_segs(path):
        if _seg_proper_cross(x0, y0, x1, y1, s[0], s[1], s[2], s[3]):
            return True
    return False


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
    for s in _iter_line_segs(path):
        sx0, sy0, sx1, sy1 = s
        sdx, sdy = sx1 - sx0, sy1 - sy0
        sln = math.hypot(sdx, sdy)
        if sln < 1e-9:
            continue
        if abs(ux * (sdx / sln) + uy * (sdy / sln)) < _SEG_REDUNDANT_DOT:
            continue
        if (_point_seg_dist(ax, ay, *s) > tol
                or _point_seg_dist(bx, by, *s) > tol):
            continue
        # Midpoint must also sit on the host (rejects near-miss diagonals).
        mx, my = 0.5 * (ax + bx), 0.5 * (ay + by)
        if _point_seg_dist(mx, my, *s) > tol:
            continue
        return True
    return False


def _pair_spanning_segs(path, path_a, path_b, tol=2.5):
    """Weed segments in *path* that already bridge *path_a* to *path_b*."""
    out = []
    if path is None or path.isEmpty() or path_a is None or path_b is None:
        return out
    for seg in _iter_line_segs(path):
        if _seg_spans_pair(seg, path_a, path_b, tol=tol):
            out.append(seg)
    return out


def _pair_has_spanning_seal(path, path_a, path_b, tol=2.5):
    """True if *path* already has a keep-to-keep seal across this pair."""
    return bool(_pair_spanning_segs(path, path_a, path_b, tol=tol))


def _pair_related_spanning_segs(path, path_a, path_b, cluster=None, tol=2.5):
    """Seals across *path_a*–*path_b*, or either body to the other's satellite.

    A bang-dot pocket on K covers the same alley as a K–! frame neck; treat
    it as an existing join when deciding whether another seal is needed.
    """
    segs = list(_pair_spanning_segs(path, path_a, path_b, tol=tol))
    if not cluster:
        return segs
    seen = set(segs)
    for body, other in ((path_a, path_b), (path_b, path_a)):
        for sat in cluster:
            if sat is body or sat is other or sat is None or sat.isEmpty():
                continue
            if not _is_stacked_satellite(sat, other):
                continue
            for seg in _pair_spanning_segs(path, body, sat, tol=tol):
                if seg not in seen:
                    seen.add(seg)
                    segs.append(seg)
    return segs


def _seal_midpoint(seg):
    return (0.5 * (seg[0] + seg[2]), 0.5 * (seg[1] + seg[3]))


def _mouth_near_spanning_seals(path, path_a, path_b, mouth, tol=None,
                               cluster=None):
    """True if an existing pair-spanning seal sits near *mouth*.

    Default *tol* scales with gap width and facing length so a mid-frame
    seal is dropped when a bay/corridor seal already necks the same alley
    (K–! mid cut next to a bottom bay), while a far open-end mouth on a
    tall stem pair (top fuse, bottom wrap) still seals.
    """
    if mouth is None:
        return False
    mx = _gap_mouth_mid_x(mouth)
    my = _gap_mouth_mid_y(mouth)
    if tol is None:
        facing = _corridor_facing(path_a, path_b)
        if facing is not None:
            width = float(facing[3])
            overlap = float(facing[0])
        else:
            width = float(mouth[2])
            overlap = 0.0
        tol = max(6.0, 1.25 * max(width, 1e-6), 0.45 * overlap)
    for seg in _pair_related_spanning_segs(
            path, path_a, path_b, cluster=cluster):
        sx, sy = _seal_midpoint(seg)
        if math.hypot(sx - mx, sy - my) <= tol:
            return True
    return False


def _pair_join_already_effective(path, path_a, path_b, cluster, tol=2.5):
    """True if a second *same-site* seal across this gap would be redundant.

    Direct keep-to-keep on the pair counts (leftover gutters). Stacked
    satellite whose host is already sealed to the neighbor also counts
    (speck→neighbor is a duplicate of the host alley). Callers that seal a
    *specific mouth* (cluster bay / frame open end) should not use this to
    block a far open-side mouth — use ``_mouth_near_spanning_seals`` so a
    top fuse can still get a bottom wrap seal.
    """
    if _pair_has_spanning_seal(path, path_a, path_b, tol=tol):
        return True
    if not cluster:
        return False
    for body, other in ((path_a, path_b), (path_b, path_a)):
        for host in cluster:
            if host is body or host is other or host is None or host.isEmpty():
                continue
            if not _is_stacked_satellite(body, host):
                continue
            if _pair_has_spanning_seal(path, host, other, tol=tol):
                return True
    return False


def _satellite_neighbor_already_sealed(path, path_a, path_b, cluster, tol=2.5):
    """True if a stacked speck's host is already sealed to the neighbor nearby.

    Only treat the host alley seal as covering the speck when that seal sits
    within the speck's band along the alley (plus a small margin). A top
    host→neighbor fuse must not suppress a bottom bang-dot pocket.
    """
    if not cluster:
        return False
    for body, other in ((path_a, path_b), (path_b, path_a)):
        for host in cluster:
            if host is body or host is other or host is None or host.isEmpty():
                continue
            if not _is_stacked_satellite(body, host):
                continue
            segs = _pair_spanning_segs(path, host, other, tol=tol)
            if not segs:
                continue
            br = body.boundingRect()
            # Alley axis from host→other; project speck and seals.
            ax, ay = _dominant_gap_axis(host, other)
            tx, ty = -ay, ax
            lo = min(br.left() * tx + br.top() * ty,
                     br.left() * tx + br.bottom() * ty,
                     br.right() * tx + br.top() * ty,
                     br.right() * tx + br.bottom() * ty)
            hi = max(br.left() * tx + br.top() * ty,
                     br.left() * tx + br.bottom() * ty,
                     br.right() * tx + br.top() * ty,
                     br.right() * tx + br.bottom() * ty)
            margin = max(4.0, 0.5 * (hi - lo))
            for seg in segs:
                sx, sy = _seal_midpoint(seg)
                t = sx * tx + sy * ty
                if lo - margin <= t <= hi + margin:
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
        ring = _densify_ring(pts, max_edge=max_edge)
        n = len(ring)
        for i in range(n):
            a, b = ring[i], ring[(i + 1) % n]
            edges.append((a.x(), a.y(), b.x(), b.y()))
    return edges


def _point_near_edges(px, py, edges, tol):
    if not edges:
        return False
    for e in edges:
        if _point_seg_dist(px, py, *e) <= tol:
            return True
    return False


def _point_near_weed_segs(px, py, segs, skip=None, tol=1.5):
    for s in segs:
        if skip is not None and s == skip:
            continue
        if _point_seg_dist(px, py, *s) <= tol:
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
        frame = _keep_frame_at(keep_path, QPointF(px, py))
        if frame is None or frame.vertex is not None:
            return True
        alpha = _included_angle_deg(QPointF(px, py), weed_dir, keep_path)
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
    segs = list(_iter_line_segs(weed_path))
    if not segs:
        return QPainterPath()
    keep_edges = _keep_outline_edges(keep_path)
    changed = True
    while changed:
        changed = False
        kept = []
        for seg in segs:
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
    # Bay mouth chord / corner→corner dam is not a hug (D012 exact emit).
    if (_near_waste_reflex_corner(keep_path, QPointF(x0, y0))
            and _near_waste_reflex_corner(keep_path, QPointF(x1, y1))):
        return False
    ux, uy = dx / length, dy / length
    rings = _path_to_rings(keep_path)
    if not rings:
        return False
    dens = [_densify_ring(list(r), max_edge=1.5) for r in rings]
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
        hit = _nearest_on_rings(px, py, dens)
        if hit is None:
            continue
        d = hit[2]
        dists.append(d)
        if d < _D_HUG:
            near_n += 1
        frame = _keep_frame_at(keep_path, QPointF(px, py))
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
            if _seg_spans_pair(seg, bi, bj, tol=2.5):
                span_pair = (bi, bj)
                break
        if span_pair is not None:
            break
    if span_pair is not None:
        pair = _nearest_pair(span_pair[0], span_pair[1])
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
    for seg in _iter_line_segs(weed_path):
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
            if _seg_spans_pair(seg, bi, bj, tol=tol):
                return (bi, bj)
    return None


def _nearest_pair_spanning_seal(seg, weed_path, path_a, path_b, tol=2.5):
    """Nearest existing *path_a*–*path_b* seal to *seg*, and midpoint distance."""
    if seg is None or weed_path is None or weed_path.isEmpty():
        return None, None
    mx, my = _seal_midpoint(seg)
    best = None
    best_d = None
    for other in _pair_spanning_segs(weed_path, path_a, path_b, tol=tol):
        if other == seg:
            continue
        ox, oy = _seal_midpoint(other)
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
    mx, my = _seal_midpoint(seg)
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
    altitude = _point_seg_dist(ax, ay, x0, y0, x1, y1)
    coast = math.hypot(ax - x0, ay - y0) + math.hypot(ax - x1, ay - y1)
    kappa = (coast / base) if base > 1e-9 else 0.0
    return area, altitude, kappa


def _pair_near_seal_tol(path_a, path_b, seg):
    """Same-site radius used to tell optional extras from far required mouths."""
    facing = _corridor_facing(path_a, path_b)
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
    for o in _iter_line_segs(weed_path):
        if o == seg:
            continue
        ox0, oy0, ox1, oy1 = o
        oln = math.hypot(ox1 - ox0, oy1 - oy0)
        if oln < 8.0:
            continue
        oux, ouy = (ox1 - ox0) / oln, (oy1 - oy0) / oln
        if abs(ux * oux + uy * ouy) < cos_lim:
            continue
        if _point_seg_dist(mx, my, *o) < 6.0:
            return True
    return False


def _drop_slivers_and_needless(weed_path, keep_path):
    """Remove sliver / needless-optional / duplicate-rail seals."""
    if weed_path is None or weed_path.isEmpty():
        return QPainterPath() if weed_path is None else weed_path
    if keep_path is None or keep_path.isEmpty():
        return weed_path
    out = QPainterPath()
    for seg in _iter_line_segs(weed_path):
        if (_is_sliver_seal(seg, out, keep_path)
                or _is_needless_optional_seal(seg, out, keep_path)
                or _is_duplicate_rail(seg, out)):
            continue
        out.moveTo(seg[0], seg[1])
        out.lineTo(seg[2], seg[3])
    return out


def _add_seg(out, seg, min_cut, keep_path=None, rules=None):
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
    if _seg_crosses_path(out, (x0, y0, x1, y1)):
        _wdbg.log('emit.reject', reason='cross_weed', seg=seg)
        return
    from . import progress as _progress
    _progress.check_cancel()
    out.moveTo(x0, y0)
    out.lineTo(x1, y1)
    _wdbg.log('emit.accept', seg=seg)
    _progress.report_segment(seg)


def _add_path_segs(out, path, min_cut, keep_path=None, rules=None):
    """Emit *path* line segments through ``_add_seg`` (no ungated addPath)."""
    if path is None or path.isEmpty():
        return
    for seg in _iter_line_segs(path):
        _add_seg(out, seg, min_cut, keep_path=keep_path, rules=rules)


def _convex_tips(outline, angle_deg):
    """Convex outline vertices whose exterior turn is at least *angle_deg*."""
    pts = _unique_ring(_polyline_points(outline))
    n = len(pts)
    if n < 3:
        return []
    ccw = _signed_area(pts) > 0
    tips = []
    for i in range(n):
        p0, p1, p2 = pts[(i - 1) % n], pts[i], pts[(i + 1) % n]
        ix, iy = p1.x() - p0.x(), p1.y() - p0.y()
        ox, oy = p2.x() - p1.x(), p2.y() - p1.y()
        cross = ix * oy - iy * ox
        is_convex = (cross > 0) == ccw
        if not is_convex:
            continue
        turn = _angle_turn_deg(p0, p1, p2)
        if turn < angle_deg:
            continue
        dx, dy = _outward_normal_at_corner(p0, p1, p2, outline)
        tips.append({
            'pt': p1, 'turn': turn, 'dx': dx, 'dy': dy,
            'p0': p0, 'p2': p2,
        })
    return tips


def _ray_hit_segment(ox, oy, dx, dy, ax, ay, bx, by, min_t=1e-9):
    """t along unit ray o+t d, or None if the segment is missed."""
    ex, ey = bx - ax, by - ay
    det = dx * ey - dy * ex
    if abs(det) < 1e-18:
        return None
    rx, ry = ax - ox, ay - oy
    t = (rx * ey - ry * ex) / det
    u = (rx * dy - ry * dx) / det
    if t >= min_t and 0.0 <= u <= 1.0:
        return t
    return None


def _ray_intersect_rings(ox, oy, dx, dy, rings, max_t=1e7):
    """First hit of a ray with any ring edge. (x, y, t) or None."""
    ln = math.hypot(dx, dy)
    if ln < 1e-15 or not rings:
        return None
    ux, uy = dx / ln, dy / ln
    best_t = None
    for ring in rings:
        n = len(ring)
        if n < 2:
            continue
        for i in range(n):
            a, b = ring[i], ring[(i + 1) % n]
            t = _ray_hit_segment(
                ox, oy, ux, uy, a.x(), a.y(), b.x(), b.y())
            if t is None or t > max_t:
                continue
            if best_t is None or t < best_t:
                best_t = t
    if best_t is None:
        return None
    return (ox + ux * best_t, oy + uy * best_t, best_t)


def _nearest_pair(path_a, path_b):
    """Closest sample points on two outlines. (pa, pb, dist) or None."""
    pairs = _outline_pairs(path_a, path_b)
    return pairs[0] if pairs else None


def _densify_ring(pts, max_edge=8.0):
    """Add vertices so no ring edge is longer than *max_edge*."""
    n = len(pts)
    if n < 2:
        return list(pts)
    out = []
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        out.append(a)
        dx, dy = b.x() - a.x(), b.y() - a.y()
        ln = math.hypot(dx, dy)
        if ln <= max_edge:
            continue
        steps = int(math.ceil(ln / max_edge))
        for k in range(1, steps):
            t = k / float(steps)
            out.append(QPointF(a.x() + dx * t, a.y() + dy * t))
    return out


def _outline_samples(path, max_pts=96):
    """Outline vertices and densified edges (on-path only).

    Bounding-box corners are *not* added: on curved glyphs they sit in
    empty waste and turn fuse bridges into cuts to nowhere. Multi-subpath
    bodies (host united with stacked satellites) contribute every ring.
    """
    if path is None or path.isEmpty():
        return []
    rings = _path_to_rings(path)
    if not rings:
        pts = list(_unique_ring(_polyline_points(path, max_pts=512)))
        rings = [pts] if pts else []
    pts = []
    for ring in rings:
        dens = _densify_ring(list(ring), max_edge=8.0)
        pts.extend(dens)
    if not pts:
        return []
    if len(pts) > max_pts:
        step = max(int(math.ceil(len(pts) / float(max_pts))), 1)
        pts = pts[::step]
    return pts


def _outline_pairs(path_a, path_b):
    """All sample pairs (pa, pb, dist), nearest first."""
    pts_a = _outline_samples(path_a)
    pts_b = _outline_samples(path_b)
    if not pts_a or not pts_b:
        return []
    pairs = []
    for pa in pts_a:
        for pb in pts_b:
            d = math.hypot(pb.x() - pa.x(), pb.y() - pa.y())
            pairs.append((pa, pb, d))
    pairs.sort(key=lambda t: t[2])
    return pairs


def _pullback_for_gap(ln, standoff, min_cut):
    """Standoff and leftover-cut floor that still fit *ln*."""
    standoff = float(standoff)
    min_cut = float(min_cut)
    if ln >= 2.0 * standoff + min_cut:
        return standoff, min_cut
    remain = max(0.8, min(min_cut, 0.5 * ln))
    if ln < remain + 0.3:
        return None, None
    pull = min(standoff, 0.5 * (ln - remain))
    leftover = ln - 2.0 * pull
    return pull, min(min_cut, leftover)


def _bridge_seg(pa, pb, standoff, keep_fill, work, min_cut, container):
    """Segment between two keep outlines, both ends pulled back."""
    dx, dy = pb.x() - pa.x(), pb.y() - pa.y()
    ln = math.hypot(dx, dy)
    if ln < 1e-9:
        return None
    pull, floor = _pullback_for_gap(ln, standoff, min_cut)
    if pull is None:
        return None
    ux, uy = dx / ln, dy / ln
    while pull >= 0.0:
        x0 = pa.x() + ux * pull
        y0 = pa.y() + uy * pull
        x1 = pb.x() - ux * pull
        y1 = pb.y() - uy * pull
        leftover = math.hypot(x1 - x0, y1 - y0)
        use_floor = min(floor, leftover)
        seg = _waste_seg_or_none(
            x0, y0, x1, y1, keep_fill, work, use_floor, container=container)
        if seg is not None:
            return seg
        if pull < 0.25:
            break
        pull *= 0.5
    return None


def _dominant_gap_axis(path_a, path_b):
    """Unit axis across the waste between two islands (side-by-side → ±X)."""
    ra, rb = path_a.boundingRect(), path_b.boundingRect()
    dx = rb.center().x() - ra.center().x()
    dy = rb.center().y() - ra.center().y()
    x_ov = min(ra.right(), rb.right()) - max(ra.left(), rb.left())
    y_ov = min(ra.bottom(), rb.bottom()) - max(ra.top(), rb.top())
    if y_ov >= x_ov:
        return (1.0 if dx >= 0 else -1.0), 0.0
    return 0.0, (1.0 if dy >= 0 else -1.0)


# Local keep frame at a point (C9 G0).
KeepFrameAt = namedtuple(
    'KeepFrameAt',
    ('t0', 't1', 'n_hat', 'vertex', 'turn_deg'))


def _unit_xy(dx, dy):
    ln = math.hypot(dx, dy)
    if ln < 1e-12:
        return None
    return (dx / ln, dy / ln)


def _keep_frame_at(path, p, edge_max=1.5):
    """Tangents and outward normal of *path* nearest *p*.

    Densifies each ring with max_edge=*edge_max*. Mid-edge: *t0* along the
    original edge, *t1* = -*t0*, *vertex* is None. Vertex with turn ≥ 25°:
    *t0*/*t1* along both *original* incident edges (not densified chords).
    Returns KeepFrameAt(t0, t1, n_hat, vertex, turn_deg) or None.
    """
    if path is None or path.isEmpty() or p is None:
        return None
    rings = _path_to_rings(path)
    if not rings:
        pts = _unique_ring(_polyline_points(path, max_pts=512))
        if len(pts) >= 3:
            rings = [pts]
    if not rings:
        return None
    px, py = p.x(), p.y()
    vtx_tol = max(0.35, 0.5 * float(edge_max))
    best = None  # (dist, qx, qy, orig_ring)
    for orig in rings:
        dens = _densify_ring(list(orig), max_edge=float(edge_max))
        hit = _nearest_on_rings(px, py, [dens])
        if hit is None:
            continue
        qx, qy, d = hit
        if best is None or d < best[0]:
            best = (d, qx, qy, orig)
    if best is None:
        return None
    _d, qx, qy, orig = best
    n = len(orig)
    # Prefer a sharp original vertex when the hit sits on it.
    best_vtx = None
    best_vtx_d = None
    for i in range(n):
        v = orig[i]
        vd = math.hypot(qx - v.x(), qy - v.y())
        if vd > vtx_tol:
            continue
        p0, p1, p2 = orig[(i - 1) % n], v, orig[(i + 1) % n]
        turn = _angle_turn_deg(p0, p1, p2)
        if turn < 25.0:
            continue
        if best_vtx_d is None or vd < best_vtx_d:
            best_vtx_d = vd
            best_vtx = (i, p0, p1, p2, turn)
    if best_vtx is not None:
        _i, p0, p1, p2, turn = best_vtx
        t0 = _unit_xy(p0.x() - p1.x(), p0.y() - p1.y())
        t1 = _unit_xy(p2.x() - p1.x(), p2.y() - p1.y())
        if t0 is None or t1 is None:
            return None
        nx, ny = _outward_normal_at_corner(p0, p1, p2, path)
        return KeepFrameAt(t0, t1, (nx, ny), QPointF(p1), turn)
    # Mid-edge: nearest *original* edge (not a densified chord).
    best_e = None
    best_ed = None
    for i in range(n):
        a, b = orig[i], orig[(i + 1) % n]
        ed = _point_seg_dist(qx, qy, a.x(), a.y(), b.x(), b.y())
        if best_ed is None or ed < best_ed:
            best_ed = ed
            best_e = (a, b)
    if best_e is None:
        return None
    a, b = best_e
    t0 = _unit_xy(b.x() - a.x(), b.y() - a.y())
    if t0 is None:
        return None
    t1 = (-t0[0], -t0[1])
    nx, ny = _orient_outward(qx, qy, -t0[1], t0[0], path)
    return KeepFrameAt(t0, t1, (nx, ny), None, 0.0)


def _included_angle_deg(p, w_hat, path):
    """Included angle α between weed direction *w_hat* and keep at *p*.

    *w_hat* is unit, away from keep into waste. Mid-edge:
    α = acos(clip(|ŵ·t̂|, 0, 1)) — 0° tangent, 90° square. Vertex: min of
    that vs both incident edges (thin-wedge risk). Returns degrees or None.
    """
    if w_hat is None or path is None or p is None:
        return None
    wx, wy = float(w_hat[0]), float(w_hat[1])
    wn = math.hypot(wx, wy)
    if wn < 1e-12:
        return None
    wx, wy = wx / wn, wy / wn
    frame = _keep_frame_at(path, p)
    if frame is None:
        return None

    def alpha_vs(t):
        dot = abs(wx * t[0] + wy * t[1])
        return math.degrees(math.acos(max(0.0, min(1.0, dot))))

    if frame.vertex is None:
        return alpha_vs(frame.t0)
    return min(alpha_vs(frame.t0), alpha_vs(frame.t1))


def _convex_corners(path, min_turn=40):
    """Convex outline vertices with exterior turn ≥ *min_turn* degrees."""
    if path is None or path.isEmpty():
        return []
    rings = _path_to_rings(path)
    if not rings:
        pts = _unique_ring(_polyline_points(path, max_pts=256))
        rings = [pts] if len(pts) >= 3 else []
    out = []
    for ring in rings:
        n = len(ring)
        if n < 3:
            continue
        ccw = _signed_area(ring) > 0
        for i in range(n):
            p0, p1, p2 = ring[(i - 1) % n], ring[i], ring[(i + 1) % n]
            cross = ((p1.x() - p0.x()) * (p2.y() - p1.y())
                     - (p1.y() - p0.y()) * (p2.x() - p1.x()))
            is_convex = (cross > 0) == ccw
            turn = _angle_turn_deg(p0, p1, p2)
            if is_convex and turn >= float(min_turn):
                out.append(QPointF(p1))
    return out


def _peel_axis(path_a, path_b, core=None):
    """Along-corridor ĉ and across-alley n̂ for a keep–keep gap.

    *n̂* from *core.hx/hy* when given, else ``_dominant_gap_axis``.
    *ĉ* is unit and perpendicular (facing-end along order). Returns (c_hat, n_hat).
    """
    if core is not None and hasattr(core, 'hx'):
        nx, ny = float(core.hx), float(core.hy)
        ln = math.hypot(nx, ny)
        if ln < 1e-12:
            nx, ny = _dominant_gap_axis(path_a, path_b)
        else:
            nx, ny = nx / ln, ny / ln
    else:
        nx, ny = _dominant_gap_axis(path_a, path_b)
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
            return _unit_xy(float(out[0]), float(out[1]))
        left, right, deep = ctx.get('left'), ctx.get('right'), ctx.get('deep')
        if left is None or right is None or deep is None:
            return None
        wd = _bay_waste_dir(left, right, deep)
        if wd is None:
            return None
        # Peel out the mouth = opposite mouth→deep.
        return _unit_xy(-wd[0], -wd[1])
    if kind == 'frame_open':
        n_hat = ctx.get('n_hat')
        if n_hat is not None:
            return _unit_xy(float(n_hat[0]), float(n_hat[1]))
        collar_pt = ctx.get('collar_pt')
        if collar_pt is None:
            return None
        return _unit_xy(collar_pt.x() - p.x(), collar_pt.y() - p.y())
    if kind == 'frame_letter':
        path_a = ctx.get('path_a')
        path_b = ctx.get('path_b')
        if path_a is None or path_b is None:
            return None
        c_hat, _n_hat = _peel_axis(path_a, path_b, ctx.get('core'))
        top = _frame_open_is_top(
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


def _vertex_weed_degree(p, weed_path, r=1.2):
    """Count weed segment endpoints within *r* of *p*."""
    if p is None or weed_path is None or weed_path.isEmpty():
        return 0
    px, py = p.x(), p.y()
    rr = float(r)
    count = 0
    for x0, y0, x1, y1 in _iter_line_segs(weed_path):
        if math.hypot(x0 - px, y0 - py) <= rr:
            count += 1
        if math.hypot(x1 - px, y1 - py) <= rr:
            count += 1
    return count


def _hunt_radius(gap_w, overlap_l=0.0):
    """Corner / coast hunt radius: max(8, 1.2w, 0.35L)."""
    return max(8.0, 1.2 * float(gap_w), 0.35 * float(overlap_l))


def _alpha_min_at_anchors(pa, pb, path_a, path_b):
    """Min created peel angle at anchors *pa*/*pb*, or None if unmeasurable."""
    if pa is None or pb is None or path_a is None or path_b is None:
        return None
    dx = pb.x() - pa.x()
    dy = pb.y() - pa.y()
    ln = math.hypot(dx, dy)
    if ln < 1e-12:
        return None
    ux, uy = dx / ln, dy / ln
    a0 = _created_peel_angles(pa, (ux, uy), path_a)
    a1 = _created_peel_angles(pb, (-ux, -uy), path_b)
    if a0 is None or a1 is None:
        return None
    return min(min(a0), min(a1))


def _passes_alpha_hard(pa, pb, path_a, path_b, alpha_hard=None):
    """True unless measurable created α falls below the emit floor (D012)."""
    hard = DEFAULT_ALPHA_MIN if alpha_hard is None else float(alpha_hard)
    amin = _alpha_min_at_anchors(pa, pb, path_a, path_b)
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
    n = max(int(math.ceil(ln)), 3)
    end_a = (seg[0], seg[1])
    end_b = (seg[2], seg[3])
    land = float(c) + 0.75
    keep_rings = []
    if keep_path is not None and not keep_path.isEmpty():
        keep_rings = _path_to_rings(keep_path)
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
                hit = _nearest_on_rings(ex, ey, [ring])
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
            if _seg_proper_cross(seg[0], seg[1], seg[2], seg[3],
                                 o[0], o[1], o[2], o[3]):
                continue
            if (_point_seg_dist(seg[0], seg[1], *o) <= 1.2
                    or _point_seg_dist(seg[2], seg[3], *o) <= 1.2
                    or _point_seg_dist(o[0], o[1], *seg) <= 1.2
                    or _point_seg_dist(o[2], o[3], *seg) <= 1.2):
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
                hit = _nearest_on_rings(px, py, check)
                if hit is not None and hit[2] < c - 1e-9:
                    if (math.hypot(hit[0] - end_a[0], hit[1] - end_a[1]) > land
                            and math.hypot(hit[0] - end_b[0],
                                           hit[1] - end_b[1]) > land):
                        return False
            if skip_ring is not None:
                # Same-ring exemption is for across-bay dams, not a mid-body
                # that runs parallel outside along that ring.
                hit_s = _nearest_on_rings(px, py, [keep_rings[skip_ring]])
                if (hit_s is not None and hit_s[2] < c - 1e-9
                        and math.hypot(hit_s[0] - end_a[0],
                                       hit_s[1] - end_a[1]) > land
                        and math.hypot(hit_s[0] - end_b[0],
                                       hit_s[1] - end_b[1]) > land):
                    frame = _keep_frame_at(keep_path, QPointF(px, py))
                    if frame is not None and frame.t0 is not None:
                        dot = abs(ux * frame.t0[0] + uy * frame.t0[1])
                        phi = math.degrees(
                            math.acos(max(0.0, min(1.0, dot))))
                        if phi < _PHI_HUG:
                            return False
        for o in others:
            if _point_seg_dist(px, py, *o) < c - 1e-9:
                return False
    return True


# Endpoint must sit on the vertex — not 0.5–1.5 mm down the edge (mouth-seal
# slides used to steal class-0 that way and beat true corner–corner ranks).
_CORNER_HIT_TOL = 0.35


def _near_waste_reflex_corner(path, p, tol=None, min_turn=40):
    """True if *p* sits on a >180° weed-side (convex keep) corner."""
    if path is None or p is None:
        return False
    tt = _CORNER_HIT_TOL if tol is None else float(tol)
    for c in _convex_corners(path, min_turn=min_turn):
        if math.hypot(c.x() - p.x(), c.y() - p.y()) <= tt:
            return True
    return False


def _measure_alpha_at(p, w_hat, path):
    """Included α at *p*; snap to the true corner vertex when near one."""
    if p is None or path is None or w_hat is None:
        return None
    frame = _keep_frame_at(path, p)
    if frame is not None and frame.vertex is not None:
        return _included_angle_deg(frame.vertex, w_hat, path)
    return _included_angle_deg(p, w_hat, path)


def _created_peel_angles(p, w_hat, path):
    """Water-side peel angles the cut creates at *p*, or None.

    Mid-edge: (α, 180−α) with included α in 0–90 (0 = graze). Vertex: the
    two 0–180° angles from ŵ to the incident keep tangents. A wall
    continuation is ~180° vs that edge, not 0°.
    """
    if p is None or path is None or w_hat is None:
        return None
    frame = _keep_frame_at(path, p)
    if frame is None or frame.t0 is None:
        return None
    wx, wy = float(w_hat[0]), float(w_hat[1])
    wn = math.hypot(wx, wy)
    if wn < 1e-12:
        return None
    wx, wy = wx / wn, wy / wn

    def ang180(t):
        if t is None:
            return None
        dot = max(-1.0, min(1.0, wx * t[0] + wy * t[1]))
        return math.degrees(math.acos(dot))

    if frame.vertex is None:
        a = ang180(frame.t0)
        if a is None:
            return None
        inc = min(a, 180.0 - a)
        return (inc, 180.0 - inc)
    a0 = ang180(frame.t0)
    a1 = ang180(frame.t1)
    if a0 is None or a1 is None:
        return None
    return (a0, a1)


def _seg_end_dirs(seg):
    x0, y0, x1, y1 = seg
    dx, dy = x1 - x0, y1 - y0
    ln = math.hypot(dx, dy)
    if ln < 1e-12:
        return None
    ux, uy = dx / ln, dy / ln
    return (
        (QPointF(x0, y0), (ux, uy)),
        (QPointF(x1, y1), (-ux, -uy)),
    )


def _seg_alpha_ok(seg, keep_path, alpha_min=None, peel_frame=None,
                  locked_ends=None):
    """True unless a landing creates a peel angle below the floor."""
    amin = DEFAULT_ALPHA_MIN if alpha_min is None else float(alpha_min)
    ends = _seg_end_dirs(seg)
    if ends is None:
        return False
    locked = locked_ends or ()
    for i, (p, w_hat) in enumerate(ends):
        if i < len(locked) and locked[i]:
            continue
        angles = None
        if keep_path is not None and _point_near_path(
                p.x(), p.y(), keep_path, tol=2.5):
            angles = _created_peel_angles(p, w_hat, keep_path)
        if angles is None and peel_frame is not None and _point_near_path(
                p.x(), p.y(), peel_frame, tol=2.5):
            angles = _created_peel_angles(p, w_hat, peel_frame)
        if angles is not None and min(angles) < amin - 1e-9:
            return False
    return True


def _other_weed_segs(against, skip=None):
    if against is None or against.isEmpty():
        return []
    out = []
    for s in _iter_line_segs(against):
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
        rules = _cut_rules()
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


def _endpoint_class(p, keep_path, peel_frame=None, path_b=None):
    """0 = >180° weed-side corner, 1 = peel-frame, 2 = design edge."""
    if _near_waste_reflex_corner(keep_path, p):
        return _EP_CORNER
    if path_b is not None and _near_waste_reflex_corner(path_b, p):
        return _EP_CORNER
    # On design coast: not a frame landing even if a rail nicks the same point.
    if _point_near_path(p.x(), p.y(), keep_path, tol=2.0):
        return _EP_EDGE
    if path_b is not None and _point_near_path(p.x(), p.y(), path_b, tol=2.0):
        return _EP_EDGE
    if peel_frame is not None and not peel_frame.isEmpty():
        if _point_near_path(p.x(), p.y(), peel_frame, tol=2.0):
            return _EP_FRAME
    return _EP_EDGE


def _seg_both_class0(seg, keep_path, peel_frame=None, path_b=None):
    """True if both ends are >180° weed-side (convex keep) corners."""
    ends = _seg_end_dirs(seg)
    if ends is None:
        return False
    (p0, _w0), (p1, _w1) = ends
    pb = path_b if path_b is not None else keep_path
    return (
        _endpoint_class(p0, keep_path, peel_frame, path_b=pb) == _EP_CORNER
        and _endpoint_class(p1, keep_path, peel_frame, path_b=pb) == _EP_CORNER)


def _created_angle_error(p, w_hat, keep_path, peel_frame=None):
    """Distance of the worst created peel angle from 180°. Unknown → 90.

    Included α is small on a graze and ~90° on a square landing. E is
    180 − min(created) so shallow grazes lose to nearer-180° / square.
    """
    angles = _created_peel_angles(p, w_hat, keep_path)
    if angles is None and peel_frame is not None:
        angles = _created_peel_angles(p, w_hat, peel_frame)
    if angles is None:
        return 90.0
    return 180.0 - min(angles)


def _seg_min_created(seg, keep_path, peel_frame=None):
    """Smallest created peel angle at either landing, or None."""
    ends = _seg_end_dirs(seg)
    if ends is None:
        return None
    worst = None
    for p, w_hat in ends:
        angles = _created_peel_angles(p, w_hat, keep_path)
        if angles is None and peel_frame is not None:
            angles = _created_peel_angles(p, w_hat, peel_frame)
        if angles is None:
            continue
        m = min(angles)
        if worst is None or m < worst:
            worst = m
    return worst


def _pick_quality_seg(cands, keep_path, path_b=None, peel_frame=None,
                      prefer=None):
    """Ranked pick; prefer created-min ≥ *prefer* when any candidate has it."""
    if not cands:
        return None
    floor = _CREATED_PREFER if prefer is None else float(prefer)
    good = []
    for seg in cands:
        if seg is None:
            continue
        mc = _seg_min_created(seg, keep_path, peel_frame)
        if mc is not None and mc + 1e-9 >= floor:
            good.append(seg)
    pool = good if good else list(cands)
    return _pick_ranked_seg(pool, keep_path, path_b, peel_frame)


def _peel_rank_cost(seg, keep_path, path_b=None, peel_frame=None):
    """cost ≈ E√L; E is sum of |created peel − 180°| at both ends."""
    ends = _seg_end_dirs(seg)
    if ends is None:
        return float('inf')
    (p0, w0), (p1, w1) = ends
    pb = path_b if path_b is not None else keep_path
    e0 = _created_angle_error(p0, w0, keep_path, peel_frame)
    e1 = _created_angle_error(p1, w1, pb, peel_frame)
    x0, y0, x1, y1 = seg
    ln = math.hypot(x1 - x0, y1 - y0)
    return (e0 + e1) * math.sqrt(max(ln, 1e-9))


def _corner_miss_penalty(seg, keep_path, path_b=None):
    """Sum of distances from ends to nearest convex corners (tie-break)."""
    ends = _seg_end_dirs(seg)
    if ends is None:
        return 0.0
    paths = [keep_path]
    if path_b is not None and path_b is not keep_path:
        paths.append(path_b)
    total = 0.0
    for p, _w in ends:
        best = None
        for path in paths:
            if path is None or path.isEmpty():
                continue
            for c in _convex_corners(path, min_turn=40):
                d = math.hypot(c.x() - p.x(), c.y() - p.y())
                if best is None or d < best:
                    best = d
        total += 0.0 if best is None else best
    return total


def _peel_rank_key(seg, keep_path, path_b=None, peel_frame=None):
    """(class pair, cost, corner miss) — lower is better."""
    ends = _seg_end_dirs(seg)
    if ends is None:
        return ((_EP_EDGE, _EP_EDGE), float('inf'), float('inf'))
    (p0, _w0), (p1, _w1) = ends
    pb = path_b if path_b is not None else keep_path
    c0 = _endpoint_class(p0, keep_path, peel_frame, path_b=pb)
    c1 = _endpoint_class(p1, keep_path, peel_frame, path_b=pb)
    klass = (min(c0, c1), max(c0, c1))
    return (
        klass,
        _peel_rank_cost(seg, keep_path, pb, peel_frame),
        _corner_miss_penalty(seg, keep_path, pb),
    )


def _pick_ranked_seg(cands, keep_path, path_b=None, peel_frame=None,
                     prefer=None):
    """Lowest D012 rank among *cands*; *prefer* is a same-class created-min."""
    scored = []
    for seg in cands:
        if seg is None:
            continue
        klass, cost, miss = _peel_rank_key(seg, keep_path, path_b, peel_frame)
        mc = _seg_min_created(seg, keep_path, peel_frame)
        scored.append((klass, cost, miss, mc, seg))
    if not scored:
        return None
    best_klass = min(s[0] for s in scored)
    same = [s for s in scored if s[0] == best_klass]
    if prefer is not None:
        floor = float(prefer)
        good = [s for s in same if s[3] is not None and s[3] + 1e-9 >= floor]
        if good:
            same = good
    winner = min(same, key=lambda s: (s[1], s[2]))
    if _wdbg.enabled():
        # Corner vs edge preference is a hard ranking rule; log the pool.
        corner_pool = [
            s for s in scored if s[0][0] == _EP_CORNER or s[0][1] == _EP_CORNER]
        top = sorted(scored, key=lambda s: (s[0], s[1], s[2]))[:5]
        _wdbg.log(
            'rank.pick', n=len(scored),
            winner_class=(_wdbg.ep_name(winner[0][0]),
                          _wdbg.ep_name(winner[0][1])),
            winner_cost=winner[1], winner_miss=winner[2],
            winner_created=winner[3], winner=winner[4],
            corner_cands=len(corner_pool),
            top=[
                '%s/%s c=%.1f m=%.2f %s' % (
                    _wdbg.ep_name(s[0][0]), _wdbg.ep_name(s[0][1]),
                    s[1], s[2], _wdbg.seg_fmt(s[4]))
                for s in top])
        if (winner[0][0] != _EP_CORNER and winner[0][1] != _EP_CORNER
                and corner_pool):
            best_corner = min(corner_pool, key=lambda s: (s[0], s[1], s[2]))
            _wdbg.log(
                'rank.corner_available_but_lost',
                winner_class=(_wdbg.ep_name(winner[0][0]),
                              _wdbg.ep_name(winner[0][1])),
                corner_class=(_wdbg.ep_name(best_corner[0][0]),
                              _wdbg.ep_name(best_corner[0][1])),
                corner_cost=best_corner[1], corner=best_corner[4],
                winner=winner[4])
    return winner[4]


def _outside_in_bodies(cluster, work, container=None):
    """Bodies closer to the outer waste wall first."""
    bodies = [b for b in cluster if b is not None and not b.isEmpty()]
    if len(bodies) <= 1:
        return bodies
    wall = container if container is not None else None

    def key(body):
        c = _path_centroid(body)
        if wall is not None and not wall.isEmpty():
            rings = _path_to_rings(wall)
            hit = _nearest_on_rings(c.x(), c.y(), rings) if rings else None
            if hit is not None:
                return (hit[2], c.x(), c.y())
        if work is not None and not work.isNull():
            d = min(
                c.x() - work.left(), work.right() - c.x(),
                c.y() - work.top(), work.bottom() - c.y())
            return (d, c.x(), c.y())
        return (0.0, c.x(), c.y())

    return sorted(bodies, key=key)


def _cluster_offset_rings(cluster, delta, max_pts=48):
    """Simple hull (or AABB) grow — not a per-nook offset maze."""
    _ = max_pts
    pts = []
    for b in cluster:
        if b is None or b.isEmpty():
            continue
        pts.extend(_unique_ring(_polyline_points(b, max_pts=48)))
    hull = _convex_hull(pts) if pts else []
    if len(hull) >= 3:
        try:
            off = _offset_rings([hull], float(delta), max_pts=16)
            if off:
                return off
        except RuntimeError:
            raise
        except Exception:
            pass
    return _aabb_collar_rings(cluster, delta)


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
    rings = _path_to_rings(other)
    if not rings:
        return path
    out = QPainterPath()
    tt = float(tol)
    for seg in _iter_line_segs(path):
        mx = 0.5 * (seg[0] + seg[2])
        my = 0.5 * (seg[1] + seg[3])
        hit = _nearest_on_rings(mx, my, rings)
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
    rings = _cluster_offset_rings(cluster, delta)
    raw = _rings_to_path(rings)
    clipped = _clip_path_to_waste(raw, keep_fill, None)
    clipped = _clip_path_to_rect(clipped, work)
    segs = weed_path_stats(clipped)['segments']
    _wdbg.log(
        'peel_frame.emit', n_bodies=len(cluster), delta=delta, room=room,
        rings=len(rings), segs=segs)
    return clipped, rings


def _opening_wall_rings(used_rings, container):
    """Target rings for keep→wall corridor: peel frame, else container coast."""
    if used_rings:
        return used_rings
    if container is not None and not container.isEmpty():
        return _path_to_rings(container)
    return []


def _corners_near(path, origin, r_hunt, other=None):
    """Convex corners within *r_hunt* of *origin* (optional nearer-than-*other*)."""
    if path is None or origin is None:
        return []
    rr = float(r_hunt)
    out = []
    for c in _convex_corners(path, min_turn=40):
        d0 = math.hypot(c.x() - origin.x(), c.y() - origin.y())
        if d0 > rr:
            continue
        if other is not None:
            d1 = math.hypot(c.x() - other.x(), c.y() - other.y())
            if d0 > d1 + 1.0:
                continue
        out.append(QPointF(c))
    return out


# C9 G2: edge-lift + peel ranking (α_hard still wins).
_ALPHA_SOFT = 35.0
_PEEL_ALIGN_E = 25.0
_PEEL_ALIGN_C = 35.0
_CUT_PERP_E = 65.0
_R_SNAP = 1.5
_C_CORNER_MISS = 0.4
_E_SOFT_HUGE = 8.0


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


def _facing_along_range(path_a, path_b, c_hat):
    """(lo, hi) of facing AABB overlap projected onto ĉ."""
    if path_a is None or path_b is None or c_hat is None:
        return None
    ra, rb = path_a.boundingRect(), path_b.boundingRect()
    cx, cy = float(c_hat[0]), float(c_hat[1])
    if abs(cy) >= abs(cx):
        y0 = max(ra.top(), rb.top())
        y1 = min(ra.bottom(), rb.bottom())
        if y1 < y0:
            return None
        a0, a1 = y0 * cy, y1 * cy
    else:
        x0 = max(ra.left(), rb.left())
        x1 = min(ra.right(), rb.right())
        if x1 < x0:
            return None
        a0, a1 = x0 * cx, x1 * cx
    return (min(a0, a1), max(a0, a1))


def _alley_facing_corners(path, other, c_hat, along_lo, along_hi, r_hunt,
                          mouth=None):
    """Convex corners on the alley face within overlap ± R_hunt (mouth-local)."""
    if path is None or other is None or c_hat is None:
        return []
    cx, cy = float(c_hat[0]), float(c_hat[1])
    lo = float(along_lo) - float(r_hunt)
    hi = float(along_hi) + float(r_hunt)
    pc = path.boundingRect().center()
    oc = other.boundingRect().center()
    dx, dy = oc.x() - pc.x(), oc.y() - pc.y()
    mouth_along = None
    if mouth is not None:
        mouth_along = mouth.x() * cx + mouth.y() * cy
    out = []
    for c in _convex_corners(path, min_turn=40):
        along = c.x() * cx + c.y() * cy
        if along < lo or along > hi:
            continue
        if (c.x() - pc.x()) * dx + (c.y() - pc.y()) * dy <= 0.0:
            continue
        if mouth_along is not None:
            if abs(along - mouth_along) > float(r_hunt) + 1e-9:
                if math.hypot(c.x() - mouth.x(), c.y() - mouth.y()) > float(
                        r_hunt):
                    continue
        out.append(QPointF(c))
    return out


def _body_along_extent(path, c_hat):
    """(lo, hi) of *path* AABB projected onto ĉ."""
    if path is None or path.isEmpty() or c_hat is None:
        return None
    r = path.boundingRect()
    cx, cy = float(c_hat[0]), float(c_hat[1])
    corners = (
        (r.left(), r.top()), (r.right(), r.top()),
        (r.left(), r.bottom()), (r.right(), r.bottom()))
    vals = [x * cx + y * cy for x, y in corners]
    return (min(vals), max(vals))


def _core_along_span(core, c_hat):
    """(lo, hi) of thin-core mouths on ĉ, or None."""
    if core is None or c_hat is None:
        return None
    cx, cy = float(c_hat[0]), float(c_hat[1])
    pts = (core.pa0, core.pb0, core.pa1, core.pb1)
    vals = [p.x() * cx + p.y() * cy for p in pts]
    return (min(vals), max(vals))


def _edge_lift_E(p, w_hat, path, peel_hat, d_corner, r_snap=None,
                 body_len=None):
    """True when a mid-edge seal dams peel along a peel-aligned keep edge."""
    rs = _R_SNAP if r_snap is None else float(r_snap)
    if p is None or w_hat is None or peel_hat is None or path is None:
        return False
    if float(d_corner) <= rs:
        return False
    # Near a body end along ĉ — not mid-stick.
    if body_len is not None and float(body_len) > 1e-6:
        if float(d_corner) <= 0.2 * float(body_len):
            return False
    frame = _keep_frame_at(path, p)
    t = _keep_tangent_for_peel(frame, peel_hat)
    if t is None:
        return False
    px, py = float(peel_hat[0]), float(peel_hat[1])
    pl = math.hypot(px, py)
    if pl < 1e-12:
        return False
    px, py = px / pl, py / pl
    if abs(t[0] * px + t[1] * py) < math.cos(math.radians(_PEEL_ALIGN_E)):
        return False
    wx, wy = float(w_hat[0]), float(w_hat[1])
    wn = math.hypot(wx, wy)
    if wn < 1e-12:
        return False
    wx, wy = wx / wn, wy / wn
    if abs(wx * px + wy * py) > math.cos(math.radians(_CUT_PERP_E)):
        return False
    return True


def _c_alpha(amin):
    if amin is None:
        return 0.0
    return (max(0.0, _ALPHA_SOFT - float(amin)) / _ALPHA_SOFT) ** 2


def _c_peel(p, w_hat, path, peel_hat, d_corner, gap_w):
    """Soft peel cost; 0 when keep edge is not peel-aligned."""
    if p is None or w_hat is None or peel_hat is None or path is None:
        return 0.0
    frame = _keep_frame_at(path, p)
    t = _keep_tangent_for_peel(frame, peel_hat)
    if t is None:
        return 0.0
    px, py = float(peel_hat[0]), float(peel_hat[1])
    pl = math.hypot(px, py)
    if pl < 1e-12:
        return 0.0
    px, py = px / pl, py / pl
    if abs(t[0] * px + t[1] * py) < math.cos(math.radians(_PEEL_ALIGN_C)):
        return 0.0
    wx, wy = float(w_hat[0]), float(w_hat[1])
    wn = math.hypot(wx, wy)
    if wn < 1e-12:
        return 0.0
    wx, wy = wx / wn, wy / wn
    dot = max(-1.0, min(1.0, px * wx + py * wy))
    psi = math.degrees(math.acos(dot))
    return (psi / 90.0) ** 2 * (
        1.0 + float(d_corner) / max(float(gap_w), 1.0))


def _c_corner(d_corner, r_snap=None):
    rs = _R_SNAP if r_snap is None else float(r_snap)
    return 0.0 if float(d_corner) <= rs else _C_CORNER_MISS


def _ray_hit_path(p, ux, uy, path, max_t):
    """Nearest ring hit from *p* along ±(ux,uy), or None."""
    rings = _path_to_rings(path)
    if not rings or p is None:
        return None
    best = None
    best_t = None
    for sgn in (1.0, -1.0):
        hit = _ray_intersect_rings(
            p.x(), p.y(), sgn * ux, sgn * uy, rings, max_t=max_t)
        if hit is None:
            continue
        t = float(hit[2]) if len(hit) > 2 else math.hypot(
            hit[0] - p.x(), hit[1] - p.y())
        if t < 1e-6:
            continue
        if best_t is None or t < best_t:
            best_t = t
            best = QPointF(hit[0], hit[1])
    return best


def _peel_straight_J(pa, pb, path_a, path_b, peel_hat, gap_w, corners_a,
                     corners_b, has_legal_corner, mouth_mid=None,
                     d_cap=None, body_len_a=None, body_len_b=None):
    """Peel J for an α-legal straight; None if E-hard rejected."""
    if pa is None or pb is None or peel_hat is None:
        return None
    dx = pb.x() - pa.x()
    dy = pb.y() - pa.y()
    ln = math.hypot(dx, dy)
    if ln < 1e-12:
        return None
    w_a = (dx / ln, dy / ln)
    w_b = (-dx / ln, -dy / ln)
    # Cap when a body has no hunt corners (smooth O) so J stays finite.
    cap = max(float(gap_w), 8.0) if d_cap is None else float(d_cap)
    if corners_a:
        d_a = min(_dist_to_points(pa, corners_a, default=cap), cap * 4.0)
    else:
        d_a = cap
    if corners_b:
        d_b = min(_dist_to_points(pb, corners_b, default=cap), cap * 4.0)
    else:
        d_b = cap
    e_a = _edge_lift_E(
        pa, w_a, path_a, peel_hat, d_a, body_len=body_len_a)
    e_b = _edge_lift_E(
        pb, w_b, path_b, peel_hat, d_b, body_len=body_len_b)
    # Hard E only when that body has a lift target (outside-core corner).
    if (e_a and corners_a and has_legal_corner) or (
            e_b and corners_b and has_legal_corner):
        return None
    amin = _alpha_min_at_anchors(pa, pb, path_a, path_b)
    cp = max(
        _c_peel(pa, w_a, path_a, peel_hat, d_a, gap_w),
        _c_peel(pb, w_b, path_b, peel_hat, d_b, gap_w))
    cc_a = _c_corner(d_a) if corners_a else 0.0
    cc_b = _c_corner(d_b) if corners_b else 0.0
    cc = max(cc_a, cc_b) if (corners_a or corners_b) else 0.0
    j = 3.0 * _c_alpha(amin) + 1.5 * cp + cc
    j += 0.4 * ln / max(float(gap_w), 1.0)
    if ((e_a and corners_a) or (e_b and corners_b)) and not has_legal_corner:
        j += _E_SOFT_HUGE
    if mouth_mid is not None:
        mx = 0.5 * (pa.x() + pb.x()) - mouth_mid.x()
        my = 0.5 * (pa.y() + pb.y()) - mouth_mid.y()
        j += 0.15 * math.hypot(mx, my)
    return j


def _mouth_has_spanning_seal(seen, left, right, tol=3.0):
    """True if *seen* already bridges near the mouth ends (multi-pass guard)."""
    if seen is None or seen.isEmpty() or left is None or right is None:
        return False
    tt = float(tol)
    for seg in _iter_line_segs(seen):
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
    mouth_w = _bay_mouth_width(left, right)
    tt = max(3.0, 0.25 * mouth_w) if tol is None else float(tol)
    if _mouth_has_spanning_seal(seen, left, right, tol=tt):
        return True
    lx, ly = left.x(), left.y()
    rx, ry = right.x(), right.y()
    for seg in _iter_line_segs(seen):
        if _seg_proper_cross(seg[0], seg[1], seg[2], seg[3], lx, ly, rx, ry):
            return True
    coast = _bay_coast_pts(left, right, run)
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
            if _point_seg_dist(
                    px, py, band[i][0], band[i][1],
                    band[i + 1][0], band[i + 1][1]) <= band_tol:
                return True
        return False

    for seg in _iter_line_segs(seen):
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
    corners = _convex_corners(body, min_turn=min_turn)
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
        d_mouth = _point_seg_dist(
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
    raw = [QPointF(x, y) for x, y in _bay_coast_pts(left, right, run)]
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
    mouth_w = _bay_mouth_width(left, right)
    if deep is not None:
        bay_d = _point_seg_dist(
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
    angles = _created_peel_angles(p, w_hat, path)
    if angles is None and peel_frame is not None:
        angles = _created_peel_angles(p, w_hat, peel_frame)
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
            dm = _point_seg_dist(
                p.x(), p.y(), left.x(), left.y(), right.x(), right.y())
        else:
            dm = 0.0
        ranked.append((d, dm, p))
    ranked.sort(key=lambda t: (t[0], t[1]))
    for _d, _dm, p in ranked:
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


def _facing_end_mouths(path_a, path_b):
    """First/last near outline pairs along the facing band (AABB fallback)."""
    pairs = _outline_pairs(path_a, path_b)
    if not pairs:
        return []
    dmin = pairs[0][2]
    slack = max(2.0, 0.25 * dmin)
    facing = [(pa, pb, d) for pa, pb, d in pairs if d <= dmin + slack]
    if not facing:
        return []
    ux, uy = _dominant_gap_axis(path_a, path_b)
    tx, ty = -uy, ux

    def along(pa, pb):
        mx = 0.5 * (pa.x() + pb.x())
        my = 0.5 * (pa.y() + pb.y())
        return mx * tx + my * ty

    facing.sort(key=lambda t: along(t[0], t[1]))
    first, last = facing[0], facing[-1]
    span = abs(along(last[0], last[1]) - along(first[0], first[1]))
    if span < max(3.0, 0.5 * dmin):
        return [first]
    return [first, last]


def _stacked_satellites_of(host, cluster):
    """Bodies in *cluster* that are stacked satellites of *host*."""
    if host is None or not cluster:
        return []
    out = []
    for b in cluster:
        if b is host or b is None or b.isEmpty():
            continue
        if _is_stacked_satellite(b, host):
            out.append(b)
    return out


def _stacked_host_of(speck, cluster):
    """Host body that *speck* stacks on, or None."""
    if speck is None or speck.isEmpty() or not cluster:
        return None
    best = None
    for b in cluster:
        if b is speck or b is None or b.isEmpty():
            continue
        if not _is_stacked_satellite(speck, b):
            continue
        area = abs(_path_area(b))
        if best is None or area > best[0]:
            best = (area, b)
    return None if best is None else best[1]


def _with_stacked_satellites(body, cluster):
    """*body* united with its stacked satellites (dot+stem as one island)."""
    if body is None or body.isEmpty():
        return body
    sats = _stacked_satellites_of(body, cluster)
    if not sats:
        return body
    acc = QPainterPath(body)
    for sat in sats:
        acc = acc.united(sat)
    return acc if not acc.isEmpty() else body


def _gap_mouths(path_a, path_b, cluster=None):
    """Keep-point pairs at each end of the channel core (else facing ends).

    When *cluster* is given, each side is expanded with stacked satellites
    so an i-dot above a stem extends the alley mouth to the dot (H→dot
    rather than H→top-of-stem only).
    """
    a_use = _with_stacked_satellites(path_a, cluster) if cluster else path_a
    b_use = _with_stacked_satellites(path_b, cluster) if cluster else path_b
    # Prefer facing ends on the expanded outlines when satellites grew the
    # island beyond the thin core (core would still stop at the stem top).
    expanded = (a_use is not path_a) or (b_use is not path_b)
    if expanded:
        faces = _facing_end_mouths(a_use, b_use)
        if faces:
            return faces
    core = _channel_core(a_use, b_use)
    if core is None and expanded:
        core = _channel_core(path_a, path_b)
    if core is not None:
        d0 = math.hypot(
            core.pa0.x() - core.pb0.x(), core.pa0.y() - core.pb0.y())
        d1 = math.hypot(
            core.pa1.x() - core.pb1.x(), core.pa1.y() - core.pb1.y())
        return [(core.pa0, core.pb0, d0), (core.pa1, core.pb1, d1)]
    return _facing_end_mouths(a_use, b_use)


def _axis_hit_pair(pa, pb, ux, uy, path_a, path_b, max_t=32.0):
    """Rebuild pa–pb along the gap axis so the seal meets keep square-on."""
    rings_a = _path_to_rings(path_a)
    rings_b = _path_to_rings(path_b)
    if not rings_a or not rings_b:
        return pa, pb
    best = None
    best_ln = None

    def consider(qa, qb):
        nonlocal best, best_ln
        ln = math.hypot(qb.x() - qa.x(), qb.y() - qa.y())
        if ln < 1e-6 or ln > max_t:
            return
        if best_ln is None or ln < best_ln:
            best_ln = ln
            best = (qa, qb)

    for sgn in (1.0, -1.0):
        hit = _ray_intersect_rings(
            pa.x(), pa.y(), sgn * ux, sgn * uy, rings_b, max_t=max_t)
        if hit is not None:
            consider(QPointF(pa.x(), pa.y()), QPointF(hit[0], hit[1]))
    for sgn in (1.0, -1.0):
        hit = _ray_intersect_rings(
            pb.x(), pb.y(), sgn * ux, sgn * uy, rings_a, max_t=max_t)
        if hit is not None:
            consider(QPointF(hit[0], hit[1]), QPointF(pb.x(), pb.y()))
    return best if best is not None else (pa, pb)


# Waste pockets: font-H ~0.85, t-open ~0.24. Keep tips stay a true spike.
_WASTE_PENINSULA_MIN_RATIO = DEFAULT_PENINSULA_RATIO
_KEEP_PENINSULA_MIN_RATIO = 1.0
# Legacy frontier metrics (ρ / tips); bay seal uses D007 κ (below).
_FRONTIER_RHO_MAX = 1.6
_FRONTIER_TIP_MIN = 3
# Hull-bay discovery floor. Old 4 mm / 3×standoff hid shallow jagged bays.
_BAY_DISCOVERY_MIN_DEPTH = 1.0
# D007 coastline closure: classify if κ ≥ min; seal if undercut or κ ≥ cut.
_KAPPA_MIN = 2.0
_KAPPA_CUT = 3.0

FrontierRunMetrics = namedtuple(
    'FrontierRunMetrics', ('rho', 'length', 'chord', 'tip_count'))


def _pt_xy(p):
    """(x, y) from a QPointF-like or (x, y) pair."""
    if hasattr(p, 'x'):
        return float(p.x()), float(p.y())
    return float(p[0]), float(p[1])


def _run_arc_length(pts):
    """Sum of segment lengths along a densified frontier run."""
    if not pts or len(pts) < 2:
        return 0.0
    total = 0.0
    for i in range(len(pts) - 1):
        x0, y0 = _pt_xy(pts[i])
        x1, y1 = _pt_xy(pts[i + 1])
        total += math.hypot(x1 - x0, y1 - y0)
    return total


def _run_chord_length(pts):
    """Straight-line distance first→last sample of a frontier run."""
    if not pts or len(pts) < 2:
        return 0.0
    x0, y0 = _pt_xy(pts[0])
    x1, y1 = _pt_xy(pts[-1])
    return math.hypot(x1 - x0, y1 - y0)


def _frontier_complexity(pts, eps=1e-9):
    """Frontier complexity ρ = L / max(C, ε). Empty/tiny → 1.0."""
    if not pts or len(pts) < 2:
        return 1.0
    length = _run_arc_length(pts)
    chord = _run_chord_length(pts)
    if length < eps and chord < eps:
        return 1.0
    return length / max(chord, eps)


def _frontier_tip_count(pts, angle_deg=None, waste_dir=None, eps=1e-12):
    """Count sharp tips on an open run whose exterior bisector faces waste.

    *waste_dir* is a preferred waste direction (default: left normal of the
    first→last chord). Tips reuse the turn threshold used for convex keep
    tips (DEFAULT_DELICATE_ANGLE_DEG).
    """
    if angle_deg is None:
        angle_deg = DEFAULT_DELICATE_ANGLE_DEG
    if not pts or len(pts) < 3:
        return 0
    if waste_dir is None:
        x0, y0 = _pt_xy(pts[0])
        x1, y1 = _pt_xy(pts[-1])
        cx, cy = x1 - x0, y1 - y0
        cl = math.hypot(cx, cy)
        if cl < eps:
            return 0
        # Left normal of chord (waste side of a L→R keep-below run).
        waste_dir = (-cy / cl, cx / cl)
    else:
        wx, wy = float(waste_dir[0]), float(waste_dir[1])
        wl = math.hypot(wx, wy)
        if wl < eps:
            return 0
        waste_dir = (wx / wl, wy / wl)
    wx, wy = waste_dir
    count = 0
    for i in range(1, len(pts) - 1):
        p0 = QPointF(*_pt_xy(pts[i - 1]))
        p1 = QPointF(*_pt_xy(pts[i]))
        p2 = QPointF(*_pt_xy(pts[i + 1]))
        turn = _angle_turn_deg(p0, p1, p2)
        if turn < angle_deg:
            continue
        v1x, v1y = p0.x() - p1.x(), p0.y() - p1.y()
        v2x, v2y = p2.x() - p1.x(), p2.y() - p1.y()
        n1 = math.hypot(v1x, v1y)
        n2 = math.hypot(v2x, v2y)
        if n1 < eps or n2 < eps:
            continue
        v1x, v1y = v1x / n1, v1y / n1
        v2x, v2y = v2x / n2, v2y / n2
        bx, by = v1x + v2x, v1y + v2y
        bn = math.hypot(bx, by)
        if bn < eps:
            # Straight reverse: exterior ≈ either side normal.
            bx, by = -v1y, v1x
            bn = 1.0
        # Exterior bisector points out of the wedge (into waste for a tip).
        ex, ey = -bx / bn, -by / bn
        if ex * wx + ey * wy <= 0.0:
            continue
        count += 1
    return count


def _frontier_run_metrics(pts, angle_deg=None, waste_dir=None, eps=1e-9):
    """ρ, L, chord, tip_count for a densified frontier run."""
    length = _run_arc_length(pts)
    chord = _run_chord_length(pts)
    rho = _frontier_complexity(pts, eps=eps)
    tips = _frontier_tip_count(
        pts, angle_deg=angle_deg, waste_dir=waste_dir, eps=eps)
    return FrontierRunMetrics(rho, length, chord, tips)


def _peninsula_is_deep(depth, mouth_w, ratio=_WASTE_PENINSULA_MIN_RATIO, eps=1e-6):
    """Deep when depth exceeds *ratio* of the mouth."""
    return float(depth) > float(ratio) * float(mouth_w) + eps


def _bay_coast_pts(left, right, run):
    """Mouth-left → coast samples → mouth-right as (x, y) pairs."""
    pts = []

    def add(p):
        if p is None:
            return
        xy = _pt_xy(p)
        if pts:
            px, py = pts[-1]
            if abs(xy[0] - px) < 1e-12 and abs(xy[1] - py) < 1e-12:
                return
        pts.append(xy)

    add(left)
    if run:
        for p in run:
            add(p)
    add(right)
    return pts


def _bay_coast_length(left, right, run):
    """L_coast along the keep↔waste frontier between mouth ends."""
    return _run_arc_length(_bay_coast_pts(left, right, run))


def _bay_mouth_width(left, right):
    """L_mouth = distance between mouth endpoints."""
    lx, ly = _pt_xy(left)
    rx, ry = _pt_xy(right)
    return math.hypot(rx - lx, ry - ly)


def _bay_kappa(left, right, run, mouth_w=None, eps=1e-9):
    """Closure κ = L_coast / L_mouth (D007)."""
    if mouth_w is None:
        mouth_w = _bay_mouth_width(left, right)
    mouth_w = float(mouth_w)
    if mouth_w < eps:
        return 0.0
    return _bay_coast_length(left, right, run) / mouth_w


def _approx_bay_kappa(depth, mouth_w, frontier_pts=None, eps=1e-9):
    """κ when only depth/mouth (and optional one-wall frontier) are known.

    Models an open multi-body bay as a U: two walls of *depth* plus a far
    chord ≈ mouth → κ = 2·depth/mouth + 1. A denser facing frontier may
    raise κ further.
    """
    mw = max(float(mouth_w), eps)
    kappa = 2.0 * float(depth) / mw + 1.0
    if frontier_pts and len(frontier_pts) >= 2:
        kappa = max(kappa, _run_arc_length(frontier_pts) / mw)
    return kappa


def _line_line_s(ox, oy, tx, ty, ax, ay, bx, by, eps=1e-12):
    """Parameter s for o+s·t̂ intersecting segment ab, or None."""
    dx, dy = bx - ax, by - ay
    den = tx * dy - ty * dx
    if abs(den) < eps:
        return None
    sx, sy = ax - ox, ay - oy
    s = (sx * dy - sy * dx) / den
    u = (sx * ty - sy * tx) / den
    if u < -eps or u > 1.0 + eps:
        return None
    return s


def _bay_has_undercut(left, right, deep, run, n_samples=12, eps=1e-6):
    """True if some water chord parallel to the mouth is longer than the mouth."""
    mouth_w = _bay_mouth_width(left, right)
    if mouth_w < eps:
        return False
    lx, ly = _pt_xy(left)
    rx, ry = _pt_xy(right)
    tx, ty = (rx - lx) / mouth_w, (ry - ly) / mouth_w
    mx, my = 0.5 * (lx + rx), 0.5 * (ly + ry)
    dpx, dpy = _pt_xy(deep)
    nx, ny = dpx - mx, dpy - my
    depth = math.hypot(nx, ny)
    if depth < eps:
        return False
    nx, ny = nx / depth, ny / depth
    coast = _bay_coast_pts(left, right, run)
    if len(coast) < 2:
        return False
    n_samples = max(int(n_samples), 3)
    for i in range(1, n_samples):
        t = depth * (i / float(n_samples))
        ox, oy = mx + nx * t, my + ny * t
        hits = []
        for j in range(len(coast) - 1):
            ax, ay = coast[j]
            bx, by = coast[j + 1]
            s = _line_line_s(ox, oy, tx, ty, ax, ay, bx, by)
            if s is not None:
                hits.append(s)
        if len(hits) < 2:
            continue
        hits.sort()
        span = hits[-1] - hits[0]
        if span > mouth_w + eps:
            return True
    return False


def _bay_should_seal(left, right, deep, run, depth=None, mouth_w=None,
                     ratio=_WASTE_PENINSULA_MIN_RATIO,
                     kappa_min=_KAPPA_MIN, kappa_cut=_KAPPA_CUT, eps=1e-9):
    """Seal a body bay mouth (D007): κ ≥ min and (undercut or κ ≥ cut or deep)."""
    if left is None or right is None:
        return False
    if mouth_w is None:
        mouth_w = _bay_mouth_width(left, right)
    mouth_w = float(mouth_w)
    if mouth_w < eps:
        return False
    if depth is None and deep is not None:
        depth = _point_seg_dist(
            _pt_xy(deep)[0], _pt_xy(deep)[1],
            _pt_xy(left)[0], _pt_xy(left)[1],
            _pt_xy(right)[0], _pt_xy(right)[1])
    depth = float(depth or 0.0)
    kappa = _bay_kappa(left, right, run, mouth_w=mouth_w, eps=eps)
    if kappa + eps < float(kappa_min):
        return False
    if kappa + eps >= float(kappa_cut):
        return True
    if deep is not None and _bay_has_undercut(left, right, deep, run):
        return True
    if _peninsula_is_deep(depth, mouth_w, ratio=ratio):
        return True
    return False


def _peninsula_should_detach(depth, mouth_w, frontier_pts,
                             ratio=_WASTE_PENINSULA_MIN_RATIO,
                             rho_max=_FRONTIER_RHO_MAX,
                             tip_min=_FRONTIER_TIP_MIN,
                             waste_dir=None,
                             left=None, right=None, deep=None,
                             kappa_min=_KAPPA_MIN, kappa_cut=_KAPPA_CUT):
    """Seal waste bay when D007 κ/undercut/depth gates fire.

    Full mouth geometry (*left*, *right*, *deep*, *frontier_pts* as coast)
    uses true κ. Callers with only depth/mouth use the U approx. *rho_max*
    / *tip_min* are accepted for API compat but no longer seal by themselves.
    """
    _ = rho_max, tip_min, waste_dir
    if left is not None and right is not None:
        return _bay_should_seal(
            left, right, deep, frontier_pts, depth=depth, mouth_w=mouth_w,
            ratio=ratio, kappa_min=kappa_min, kappa_cut=kappa_cut)
    kappa = _approx_bay_kappa(depth, mouth_w, frontier_pts)
    if kappa + 1e-9 < float(kappa_min):
        return False
    if kappa + 1e-9 >= float(kappa_cut):
        return True
    return _peninsula_is_deep(depth, mouth_w, ratio=ratio)


def _bay_waste_dir(left, right, deep):
    """Vector from the mouth midpoint toward the bay (into waste / water)."""
    wx = deep.x() - 0.5 * (left.x() + right.x())
    wy = deep.y() - 0.5 * (left.y() + right.y())
    if wx * wx + wy * wy <= 1e-18:
        return None
    return (wx, wy)


def _bay_min_depth(standoff):
    """Discovery floor so shallow complex bays are still candidates."""
    return max(_BAY_DISCOVERY_MIN_DEPTH, float(standoff))


def _vertex_is_concave(pts, i, ccw):
    n = len(pts)
    p0, p1, p2 = pts[(i - 1) % n], pts[i], pts[(i + 1) % n]
    ix, iy = p1.x() - p0.x(), p1.y() - p0.y()
    ox, oy = p2.x() - p1.x(), p2.y() - p1.y()
    cross = ix * oy - iy * ox
    if abs(cross) < 1e-12:
        return False
    is_convex = (cross > 0) == ccw
    return not is_convex


def _keep_peninsula_mouth(pts, i, ccw):
    """Base of a keep tip: first reflex vertex each side, else neighbors."""
    n = len(pts)
    left = right = None
    for k in range(1, n - 1):
        j = (i - k) % n
        if _vertex_is_concave(pts, j, ccw):
            left = pts[j]
            break
    for k in range(1, n - 1):
        j = (i + k) % n
        if _vertex_is_concave(pts, j, ccw):
            right = pts[j]
            break
    if left is None or right is None:
        left = pts[(i - 1) % n]
        right = pts[(i + 1) % n]
    return left, right


def _mouth_has_body_beyond(pa, pb, tip, outline):
    """True if keep continues past the mouth (a neck, not the whole body)."""
    mx = 0.5 * (pa.x() + pb.x())
    my = 0.5 * (pa.y() + pb.y())
    dx, dy = mx - tip.x(), my - tip.y()
    ln = math.hypot(dx, dy)
    if ln < 1e-9:
        return False
    ux, uy = dx / ln, dy / ln
    mouth_w = math.hypot(pb.x() - pa.x(), pb.y() - pa.y())
    step = max(0.75, 0.15 * mouth_w)
    return outline.contains(QPointF(mx + ux * step, my + uy * step))


def _deep_keep_peninsula_tips(outline, angle_deg):
    """Convex tips whose protrusion is deeper than the neck is wide."""
    tips = _convex_tips(outline, angle_deg)
    if not tips:
        return []
    pts = _unique_ring(_polyline_points(outline))
    if len(pts) < 3:
        return []
    ccw = _signed_area(pts) > 0
    out = []
    for tip in tips:
        i = _nearest_pt_index(pts, tip['pt'])
        pa, pb = _keep_peninsula_mouth(pts, i, ccw)
        mouth_w = math.hypot(pb.x() - pa.x(), pb.y() - pa.y())
        depth = _point_seg_dist(
            tip['pt'].x(), tip['pt'].y(), pa.x(), pa.y(), pb.x(), pb.y())
        if not _peninsula_is_deep(
                depth, mouth_w, ratio=_KEEP_PENINSULA_MIN_RATIO):
            continue
        if not _mouth_has_body_beyond(pa, pb, tip['pt'], outline):
            continue
        out.append(tip)
    return out


# Corridor: facing overlap is a large fraction of *both* islands.
_CORRIDOR_MIN_OVERLAP = 0.5
# Gap must be small vs that facing length.
_CORRIDOR_MAX_GAP = 0.6
# End-seal span ≤ k×width → one mid seal. 2.0 keeps HI dual-mouth (L/W≈2.25).
_CORRIDOR_SHORT_K = 2.0

ChannelCore = namedtuple(
    'ChannelCore',
    ('width', 'length', 'along0', 'along1',
     'pa0', 'pb0', 'pa1', 'pb1',
     'stations', 'thin', 'hx', 'hy'))


def _corridor_facing(path_a, path_b):
    """(overlap, size_a, size_b, gap) along the facing axis, or None."""
    if path_a is None or path_b is None or path_a.isEmpty() or path_b.isEmpty():
        return None
    ra, rb = path_a.boundingRect(), path_b.boundingRect()
    ux, uy = _dominant_gap_axis(path_a, path_b)
    if abs(ux) >= abs(uy):
        overlap = min(ra.bottom(), rb.bottom()) - max(ra.top(), rb.top())
        size_a, size_b = ra.height(), rb.height()
        gap = max(0.0, ra.left() - rb.right(), rb.left() - ra.right())
    else:
        overlap = min(ra.right(), rb.right()) - max(ra.left(), rb.left())
        size_a, size_b = ra.width(), rb.width()
        gap = max(0.0, ra.top() - rb.bottom(), rb.top() - ra.bottom())
    if overlap <= 0.0 or size_a < 1e-6 or size_b < 1e-6:
        return None
    return overlap, size_a, size_b, gap


def _alley_width_profile(path_a, path_b, step=None):
    """(stations, hx, hy) along the facing overlap, or None."""
    facing = _corridor_facing(path_a, path_b)
    if facing is None:
        return None
    overlap, _size_a, _size_b, gap = facing
    if step is None:
        step = max(1.5, min(2.5, float(overlap) / 16.0))
    ax, ay = _dominant_gap_axis(path_a, path_b)
    ra, rb = path_a.boundingRect(), path_b.boundingRect()
    rings_a = _path_to_rings(path_a)
    rings_b = _path_to_rings(path_b)
    if not rings_a or not rings_b:
        return None
    if abs(ax) >= abs(ay):
        t0 = max(ra.top(), rb.top())
        t1 = min(ra.bottom(), rb.bottom())
        if ra.center().x() <= rb.center().x():
            gx = 0.5 * (ra.right() + rb.left())
            left_rings, right_rings = rings_a, rings_b
        else:
            gx = 0.5 * (rb.right() + ra.left())
            left_rings, right_rings = rings_b, rings_a
        hx, hy = 1.0, 0.0

        def origin(t):
            return gx, t
    else:
        t0 = max(ra.left(), rb.left())
        t1 = min(ra.right(), rb.right())
        if ra.center().y() <= rb.center().y():
            gy = 0.5 * (ra.bottom() + rb.top())
            left_rings, right_rings = rings_a, rings_b
        else:
            gy = 0.5 * (rb.bottom() + ra.top())
            left_rings, right_rings = rings_b, rings_a
        hx, hy = 0.0, 1.0

        def origin(t):
            return t, gy
    if t1 - t0 < 1e-6:
        return None
    max_t = max(32.0, 2.0 * (float(gap) + 16.0))
    n = max(int(math.ceil((t1 - t0) / float(step))), 2)
    stations = []
    for i in range(n + 1):
        t = t0 + (t1 - t0) * i / float(n)
        ox, oy = origin(t)
        hit_l = _ray_intersect_rings(ox, oy, -hx, -hy, left_rings, max_t)
        hit_r = _ray_intersect_rings(ox, oy, hx, hy, right_rings, max_t)
        if hit_l is None or hit_r is None:
            continue
        width = math.hypot(hit_r[0] - hit_l[0], hit_r[1] - hit_l[1])
        stations.append((
            t, width,
            QPointF(hit_l[0], hit_l[1]),
            QPointF(hit_r[0], hit_r[1])))
    if len(stations) < 2:
        return None
    return stations, hx, hy


def _channel_core(path_a, path_b):
    """Thin through-channel between two keep walls, or None."""
    prof = _alley_width_profile(path_a, path_b)
    if prof is None:
        return None
    stations, hx, hy = prof
    wmin = min(s[1] for s in stations)
    slack = max(2.0, 0.25 * wmin)
    thin = [s[1] <= wmin + slack + 1e-9 for s in stations]
    if not any(thin):
        return None
    i0 = next(i for i, flag in enumerate(thin) if flag)
    i1 = (len(thin) - 1
          - next(i for i, flag in enumerate(reversed(thin)) if flag))
    s0, s1 = stations[i0], stations[i1]
    length = abs(s1[0] - s0[0])
    if length < max(3.0, 0.5 * max(wmin, 1e-6)):
        return None
    return ChannelCore(
        wmin, length, s0[0], s1[0], s0[2], s0[3], s1[2], s1[3],
        stations, thin, hx, hy)


def _channel_side_opening_seals(path_a, path_b, core, keep_fill, work,
                                standoff, min_cut, container,
                                peninsula_ratio=None):
    """Side-seal corridor openings when flare depth > local core width (D007)."""
    out = []
    _ = peninsula_ratio
    if core is None or not core.stations or not core.thin:
        return out
    stations = core.stations
    thin = core.thin
    hx, hy = core.hx, core.hy
    first = next((i for i, flag in enumerate(thin) if flag), None)
    if first is None:
        return out
    last = (len(thin) - 1
            - next(i for i, flag in enumerate(reversed(thin)) if flag))

    def across(p):
        return p.x() * hx + p.y() * hy

    thin_left = []
    thin_right = []
    for i, flag in enumerate(thin):
        if not flag:
            continue
        thin_left.append(across(stations[i][2]))
        thin_right.append(across(stations[i][3]))
    if not thin_left:
        return out
    thin_left.sort()
    thin_right.sort()
    ntl = len(thin_left)
    base_l = (thin_left[ntl // 2] if ntl % 2
              else 0.5 * (thin_left[ntl // 2 - 1] + thin_left[ntl // 2]))
    ntr = len(thin_right)
    base_r = (thin_right[ntr // 2] if ntr % 2
              else 0.5 * (thin_right[ntr // 2 - 1] + thin_right[ntr // 2]))
    local_w = max(float(core.width), 1e-6)

    i = first
    while i <= last:
        if thin[i]:
            i += 1
            continue
        j = i
        while j <= last and not thin[j]:
            j += 1
        # End flare: core mouth already necks the channel; skip end bands.
        if i <= first or j - 1 >= last:
            i = j
            continue
        flare = stations[i:j]
        if not flare:
            i = j
            continue
        # Opening depth into the side = max width gain over the thin core.
        extra = max(s[1] for s in flare) - core.width
        span = abs(stations[j - 1][0] - stations[i][0])
        if extra < 1.0 or span < 2.0:
            i = j
            continue
        # D007 corridor stop: seal when opening depth > local corridor width.
        if extra <= local_w + 1e-9:
            i = j
            continue
        n_f = float(len(flare))
        flare_l = sum(across(s[2]) for s in flare) / n_f
        flare_r = sum(across(s[3]) for s in flare) / n_f
        left_rec = base_l - flare_l
        right_rec = flare_r - base_r
        if right_rec >= left_rec and right_rec >= 1.0:
            receding = 3
        elif left_rec > right_rec and left_rec >= 1.0:
            receding = 2
        else:
            i = j
            continue
        base = base_r if receding == 3 else base_l
        a0, a1 = stations[i][0], stations[j - 1][0]
        pull = (hx, hy) if receding == 3 else (-hx, -hy)
        if abs(hx) >= abs(hy):
            mid = QPointF(base + pull[0] * _SEARCH_PROBE, 0.5 * (a0 + a1))
            lx, ly = 0.0, 1.0
        else:
            mid = QPointF(0.5 * (a0 + a1), base + pull[1] * _SEARCH_PROBE)
            lx, ly = 1.0, 0.0
        rings = _path_to_rings(path_a) + _path_to_rings(path_b)
        max_t = span + 8.0
        hit0 = _ray_intersect_rings(mid.x(), mid.y(), -lx, -ly, rings, max_t)
        hit1 = _ray_intersect_rings(mid.x(), mid.y(), lx, ly, rings, max_t)
        if hit0 is None or hit1 is None:
            i = j
            continue
        pa, pb = QPointF(hit0[0], hit0[1]), QPointF(hit1[0], hit1[1])
        seg = _fuse_bridge(
            pa, pb, standoff, keep_fill, work, min_cut, container)
        if seg is not None:
            out.append(seg)
        i = j
    return out


def _is_corridor_pair(path_a, path_b):
    """Thin channel core between two keep walls; satellites are not corridors."""
    if _is_stacked_satellite(path_a, path_b) or _is_stacked_satellite(
            path_b, path_a):
        return False
    facing = _corridor_facing(path_a, path_b)
    if facing is None:
        return False
    overlap, size_a, size_b, gap = facing
    if (overlap < _CORRIDOR_MIN_OVERLAP * size_a
            or overlap < _CORRIDOR_MIN_OVERLAP * size_b):
        return False
    if gap > _CORRIDOR_MAX_GAP * overlap:
        return False
    if _channel_core(path_a, path_b) is not None:
        return True
    return len(_facing_end_mouths(path_a, path_b)) >= 2


def _gap_aabb(path_a, path_b):
    """AABB of the waste corridor between two islands, or None."""
    if path_a is None or path_b is None:
        return None
    ra, rb = path_a.boundingRect(), path_b.boundingRect()
    ux, uy = _dominant_gap_axis(path_a, path_b)
    if abs(ux) >= abs(uy):
        x0 = min(ra.right(), rb.right())
        x1 = max(ra.left(), rb.left())
        if x1 - x0 < 0.5:
            return None
        y0 = max(ra.top(), rb.top()) - 4.0
        y1 = min(ra.bottom(), rb.bottom()) + 4.0
        return QRectF(x0, min(y0, y1), x1 - x0, abs(y1 - y0))
    y0 = min(ra.bottom(), rb.bottom())
    y1 = max(ra.top(), rb.top())
    if y1 - y0 < 0.5:
        return None
    x0 = max(ra.left(), rb.left()) - 4.0
    x1 = min(ra.right(), rb.right()) + 4.0
    return QRectF(min(x0, x1), y0, abs(x1 - x0), y1 - y0)


def _gap_blockers(path_a, path_b, others):
    """Islands that occupy a meaningful fraction of the a–b gap AABB."""
    out = []
    gap = _gap_aabb(path_a, path_b)
    if gap is None or not others:
        return out
    for o in others:
        if o is None or o.isEmpty():
            continue
        ro = o.boundingRect()
        inter = gap.intersected(ro)
        if inter.isEmpty():
            continue
        ia = inter.width() * inter.height()
        oa = max(ro.width() * ro.height(), 1e-6)
        if ia >= 0.2 * oa:
            out.append(o)
    return out


def _gap_blocked(path_a, path_b, others):
    """True if another island sits in the waste between *path_a* and *path_b*."""
    return bool(_gap_blockers(path_a, path_b, others))


def _gap_blocked_only_by_tied_compacts(path_a, path_b, others, cluster,
                                       weed_path, walls=None):
    """True when gap blockers are only compact islands with ≥2 ties.

    Major↔major bottom necks may still seal through such ticks.
    """
    blockers = _gap_blockers(path_a, path_b, others)
    if not blockers:
        return False
    wall_tgts = [w for w in (walls or ()) if w is not None and not w.isEmpty()]
    for o in blockers:
        if not _is_compact_island(o, cluster):
            return False
        tgts = [b for b in cluster
                if b is not None and not b.isEmpty() and b is not o]
        tgts.extend(wall_tgts)
        if _compact_tie_count(weed_path, o, tgts) < _MIN_COMPACT_TIES:
            return False
    return True


def _mouth_body_end(mouth, body, band):
    """Which AABB end of *body* a mouth sits on, or None."""
    if body is None or body.isEmpty() or not mouth:
        return None
    br = body.boundingRect()
    pa, pb = mouth[0], mouth[1]
    mx = 0.5 * (pa.x() + pb.x())
    my = 0.5 * (pa.y() + pb.y())
    if br.height() >= br.width():
        dt = abs(my - br.top())
        db = abs(my - br.bottom())
        if dt <= db and dt <= band:
            return 'top'
        if db <= band:
            return 'bottom'
        return None
    dl = abs(mx - br.left())
    dr = abs(mx - br.right())
    if dl <= dr and dl <= band:
        return 'left'
    if dr <= band:
        return 'right'
    return None


def _fork_branch_mouths(cluster):
    """Corridor mouths that share a body end with another corridor (T)."""
    bodies = [b for b in cluster if b is not None and not b.isEmpty()]
    n = len(bodies)
    if n < 3:
        return []
    entries = []
    for i in range(n):
        for j in range(i + 1, n):
            a, b = bodies[i], bodies[j]
            if _is_stacked_satellite(a, b) or _is_stacked_satellite(b, a):
                continue
            others = [bodies[k] for k in range(n) if k != i and k != j]
            if _gap_blocked(a, b, others):
                continue
            if not _is_corridor_pair(a, b):
                continue
            mouths = _gap_mouths(a, b)
            if len(mouths) < 2:
                continue
            entries.append((a, b, mouths))
    if len(entries) < 2:
        return []
    at = {}
    for a, b, mouths in entries:
        facing = _corridor_facing(a, b)
        width = facing[3] if facing is not None else 0.0
        band = max(3.0, 0.5 * max(width, 1e-6))
        for mouth in mouths:
            for body in (a, b):
                end = _mouth_body_end(mouth, body, band)
                if end is None:
                    continue
                at.setdefault((id(body), end), []).append((a, b, mouth))
    seen = set()
    out = []
    for items in at.values():
        pair_ids = set()
        for a, b, _m in items:
            ia, ib = id(a), id(b)
            pair_ids.add((ia, ib) if ia <= ib else (ib, ia))
        if len(pair_ids) < 2:
            continue
        for a, b, mouth in items:
            ia, ib = id(a), id(b)
            pid = (ia, ib) if ia <= ib else (ib, ia)
            key = (
                pid,
                round(0.5 * (mouth[0].x() + mouth[1].x()), 3),
                round(0.5 * (mouth[0].y() + mouth[1].y()), 3),
            )
            if key in seen:
                continue
            seen.add(key)
            out.append((a, b, mouth[0], mouth[1], mouth[2]))
    return out


def _pair_fork_mouth_indices(path_a, path_b, mouths, fork_mouths):
    """Indices into *mouths* that are T-junction branch necks."""
    if not fork_mouths or not mouths:
        return set()
    ia, ib = id(path_a), id(path_b)
    want = (ia, ib) if ia <= ib else (ib, ia)
    hit = set()
    for fa, fb, pa, pb, _d in fork_mouths:
        fa_id, fb_id = id(fa), id(fb)
        key = (fa_id, fb_id) if fa_id <= fb_id else (fb_id, fa_id)
        if key != want:
            continue
        fmx = 0.5 * (pa.x() + pb.x())
        fmy = 0.5 * (pa.y() + pb.y())
        for i, (qa, qb, _dist) in enumerate(mouths):
            mx = 0.5 * (qa.x() + qb.x())
            my = 0.5 * (qa.y() + qb.y())
            if math.hypot(mx - fmx, my - fmy) <= 4.0:
                hit.add(i)
    return hit


def _fuse_bridge(pa, pb, standoff, keep_fill, work, min_cut, container):
    """Keep-to-keep join at the chosen anchors (exact endpoints)."""
    _ = standoff
    return _bridge_seg(pa, pb, 0.0, keep_fill, work, min_cut, container)


def _point_near_path(px, py, path, tol=2.5):
    """True if (px, py) lies within *tol* of *path*'s outline.

    Closed rings are preferred; open polylines (peel frames) fall back to
    iterated line segments so frame landings still count.
    """
    if path is None or path.isEmpty():
        return False
    br = path.boundingRect().adjusted(-tol, -tol, tol, tol)
    if not br.contains(QPointF(px, py)):
        return False
    rings = _path_to_rings(path)
    if rings:
        for ring in rings:
            n = len(ring)
            if n < 2:
                continue
            for i in range(n):
                a, b = ring[i], ring[(i + 1) % n]
                if _point_seg_dist(px, py, a.x(), a.y(), b.x(), b.y()) <= tol:
                    return True
        return False
    for x0, y0, x1, y1 in _iter_line_segs(path):
        if _point_seg_dist(px, py, x0, y0, x1, y1) <= tol:
            return True
    return False


def _seg_spans_pair(seg, path_a, path_b, tol=2.5):
    """True when one endpoint meets *path_a* and the other meets *path_b*."""
    if seg is None or path_a is None or path_b is None:
        return False
    x0, y0, x1, y1 = seg
    a0 = _point_near_path(x0, y0, path_a, tol)
    b0 = _point_near_path(x0, y0, path_b, tol)
    a1 = _point_near_path(x1, y1, path_a, tol)
    b1 = _point_near_path(x1, y1, path_b, tol)
    return (a0 and b1) or (b0 and a1)


def _mouth_seal(path_a, path_b, pa, pb, ax, ay, hit_t, standoff, keep_fill,
                work, min_cut, container, rules=None, against=None,
                peel_frame=None, near_mouth=False):
    """Keep-to-keep alley seal: D012 floors + class / E√L rank."""
    tx, ty = -ay, ax
    c_hat = (tx, ty)
    gap_w = math.hypot(pb.x() - pa.x(), pb.y() - pa.y())
    facing = _corridor_facing(path_a, path_b)
    overlap_l = float(facing[0]) if facing is not None else 0.0
    r_hunt = _hunt_radius(gap_w, overlap_l)
    along_span = _facing_along_range(path_a, path_b, c_hat)
    if along_span is None:
        along_lo = along_hi = 0.5 * (
            (pa.x() + pb.x()) * tx + (pa.y() + pb.y()) * ty)
    else:
        along_lo, along_hi = along_span
    mouth_mid = QPointF(0.5 * (pa.x() + pb.x()), 0.5 * (pa.y() + pb.y()))
    peel_hat = _peel_dir_at(
        mouth_mid, {'kind': 'corridor', 'c_hat': c_hat, 'mouth': mouth_mid})
    if peel_hat is None:
        peel_hat = c_hat

    core = _channel_core(path_a, path_b)
    core_span = _core_along_span(core, c_hat)
    ext_a = _body_along_extent(path_a, c_hat)
    ext_b = _body_along_extent(path_b, c_hat)
    len_a = (ext_a[1] - ext_a[0]) if ext_a else None
    len_b = (ext_b[1] - ext_b[0]) if ext_b else None

    mouth_along = mouth_mid.x() * tx + mouth_mid.y() * ty

    def is_lift_corner(c):
        """Outside thin core, and mouth still at/inside that core end."""
        if core_span is None:
            return True
        clo, chi = core_span
        along = c.x() * tx + c.y() * ty
        if along < clo - 0.35:
            return mouth_along >= clo - 1.0
        if along > chi + 0.35:
            return mouth_along <= chi + 1.0
        return False

    raw_a = _alley_facing_corners(
        path_a, path_b, c_hat, along_lo, along_hi, r_hunt, mouth=mouth_mid)
    raw_b = _alley_facing_corners(
        path_b, path_a, c_hat, along_lo, along_hi, r_hunt, mouth=mouth_mid)
    for c in _corners_near(path_a, pa, r_hunt, other=pb):
        if all(math.hypot(c.x() - q.x(), c.y() - q.y()) > 0.35
               for q in raw_a):
            raw_a.append(QPointF(c))
    for c in _corners_near(path_b, pb, r_hunt, other=pa):
        if all(math.hypot(c.x() - q.x(), c.y() - q.y()) > 0.35
               for q in raw_b):
            raw_b.append(QPointF(c))
    # Peel lift targets: alley corners beyond the thin core (O–K widen).
    lift_a = [c for c in raw_a if is_lift_corner(c)]
    lift_b = [c for c in raw_b if is_lift_corner(c)]

    pairs = []
    seen_pair = set()

    along_cap = max(0.5 * gap_w, 2.0)
    short_mouth = overlap_l <= 2.5 * max(gap_w, 1e-6)
    if near_mouth:
        short_mouth = True
        along_cap = max(0.6 * gap_w, 3.0)

    def add_pair(ha, hb):
        if ha is None or hb is None:
            return
        dx, dy = hb.x() - ha.x(), hb.y() - ha.y()
        if math.hypot(dx, dy) < max(float(min_cut), 1e-6):
            return
        if abs(dx * ax + dy * ay) < 0.35 * max(gap_w, 1.0):
            return
        if short_mouth:
            mid_along = (
                0.5 * (ha.x() + hb.x()) * tx + 0.5 * (ha.y() + hb.y()) * ty)
            if abs(mid_along - mouth_along) > along_cap + 1e-9:
                return
        key = (round(ha.x(), 3), round(ha.y(), 3),
               round(hb.x(), 3), round(hb.y(), 3))
        if key in seen_pair:
            return
        seen_pair.add(key)
        pairs.append((QPointF(ha), QPointF(hb)))

    def add_corner_pairs(corners_a, corners_b, slide_hits):
        for ca in corners_a:
            hit_b = _ray_hit_path(ca, ax, ay, path_b, hit_t)
            if hit_b is not None:
                add_pair(ca, hit_b)
            for cb in corners_b:
                add_pair(ca, cb)
            for _ha, hb in slide_hits:
                add_pair(ca, hb)
        for cb in corners_b:
            hit_a = _ray_hit_path(cb, ax, ay, path_a, hit_t)
            if hit_a is not None:
                add_pair(hit_a, cb)
            for ha, _hb in slide_hits:
                add_pair(ha, cb)

    # Keep the caller mouth anchors (often true corners / diagonal).
    # Axis-hit slides alone can replace them with mid-edge "square" chords.
    add_pair(pa, pb)
    slide_hits = []
    for step in (0.0, 1.5, 3.0, -1.5, -3.0):
        qa = QPointF(pa.x() + tx * step, pa.y() + ty * step)
        qb = QPointF(pb.x() + tx * step, pb.y() + ty * step)
        ha, hb = _axis_hit_pair(
            qa, qb, ax, ay, path_a, path_b, max_t=hit_t)
        add_pair(ha, hb)
        slide_hits.append((ha, hb))

    # Lift only when the primary mouth landing is an edge-lift mid-stick.
    use_lift_a, use_lift_b = [], []
    if slide_hits:
        ha0, hb0 = slide_hits[0]
        dx0, dy0 = hb0.x() - ha0.x(), hb0.y() - ha0.y()
        ln0 = math.hypot(dx0, dy0)
        if ln0 > 1e-12:
            w_a0 = (dx0 / ln0, dy0 / ln0)
            w_b0 = (-dx0 / ln0, -dy0 / ln0)
            d_a0 = _dist_to_points(ha0, lift_a, default=max(gap_w, 8.0))
            d_b0 = _dist_to_points(hb0, lift_b, default=max(gap_w, 8.0))
            if lift_a and _edge_lift_E(
                    ha0, w_a0, path_a, peel_hat, d_a0, body_len=len_a):
                use_lift_a = lift_a
            if lift_b and _edge_lift_E(
                    hb0, w_b0, path_b, peel_hat, d_b0, body_len=len_b):
                use_lift_b = lift_b
    add_corner_pairs(use_lift_a, use_lift_b, slide_hits)
    add_corner_pairs(raw_a, raw_b, slide_hits)
    lift_a, lift_b = use_lift_a, use_lift_b
    def evaluate_pairs():
        legal = []
        forced = []
        use_rules = rules if rules is not None else _cut_rules()
        emit_keep = keep_fill if keep_fill is not None else path_a
        others = _other_weed_segs(against)
        for ha, hb in pairs:
            seg = _fuse_bridge(
                ha, hb, standoff, keep_fill, work, min_cut, container)
            if seg is None or not _seg_spans_pair(seg, path_a, path_b):
                continue
            if _seg_emit_ok(
                    seg, emit_keep, against, use_rules,
                    peel_frame=peel_frame, other_segs=others):
                legal.append(seg)
            elif _seg_forced_ok(
                    seg, emit_keep, against, use_rules,
                    peel_frame=peel_frame, other_segs=others):
                forced.append(seg)
        return legal, forced

    legal, forced = evaluate_pairs()
    if not legal and not forced:
        add_corner_pairs(raw_a, raw_b, slide_hits)
        legal, forced = evaluate_pairs()
    emit_keep = keep_fill if keep_fill is not None else path_a
    picked = _pick_ranked_seg(
        legal, emit_keep, path_b, peel_frame, prefer=_CREATED_MOUTH_PREFER)
    if picked is not None:
        return picked
    short_f = []
    for seg in forced:
        ln = math.hypot(seg[2] - seg[0], seg[3] - seg[1])
        if ln <= 24.0:
            short_f.append(seg)
    return _pick_ranked_seg(
        short_f, emit_keep, path_b, peel_frame, prefer=_CREATED_MOUTH_PREFER)


def _corridor_chunk_seals(path_a, path_b, mouths, max_chunk, ax, ay, hit_t,
                          standoff, keep_fill, work, min_cut, container,
                          rules=None, against=None, peel_frame=None):
    """Extra seals between the two mouths when the alley is longer than *max_chunk*."""
    if max_chunk is None or len(mouths) != 2:
        return []
    (pa0, pb0, _), (pa1, pb1, _) = mouths
    mx0 = 0.5 * (pa0.x() + pb0.x())
    my0 = 0.5 * (pa0.y() + pb0.y())
    mx1 = 0.5 * (pa1.x() + pb1.x())
    my1 = 0.5 * (pa1.y() + pb1.y())
    span = math.hypot(mx1 - mx0, my1 - my0)
    if span <= float(max_chunk) + 1e-6:
        return []
    n = max(int(math.ceil(span / float(max_chunk))), 2)
    extra = []
    for i in range(1, n):
        t = i / float(n)
        pa = QPointF(pa0.x() + t * (pa1.x() - pa0.x()),
                     pa0.y() + t * (pa1.y() - pa0.y()))
        pb = QPointF(pb0.x() + t * (pb1.x() - pb0.x()),
                     pb0.y() + t * (pb1.y() - pb0.y()))
        ha, hb = _axis_hit_pair(
            pa, pb, ax, ay, path_a, path_b, max_t=hit_t)
        seg = None
        if ha is not None and hb is not None:
            seg = _fuse_bridge(
                ha, hb, standoff, keep_fill, work, min_cut, container)
        if seg is None:
            seg = _mouth_seal(
                path_a, path_b, pa, pb, ax, ay, hit_t, standoff, keep_fill,
                work, min_cut, container, rules=rules, against=against,
                peel_frame=peel_frame)
        if seg is not None:
            extra.append(seg)
    return extra


def _order_mouth_to_paths(pa, pb, path_a, path_b):
    """Return (end_on_a, end_on_b); core mouths are geometric L/R, not arg order."""
    if pa is None or pb is None:
        return pa, pb
    a_on_a = _point_near_path(pa.x(), pa.y(), path_a)
    b_on_b = _point_near_path(pb.x(), pb.y(), path_b)
    if a_on_a and b_on_b:
        return pa, pb
    a_on_b = _point_near_path(pa.x(), pa.y(), path_b)
    b_on_a = _point_near_path(pb.x(), pb.y(), path_a)
    if a_on_b and b_on_a:
        return pb, pa
    return pa, pb


def _seal_corridor_pair(path_a, path_b, keep_fill, work, standoff, min_cut,
                        container, max_chunk=None, fork_mouths=None,
                        cluster=None, rules=None, against=None,
                        peel_frame=None):
    """Seal the channel core: short → one mid; else core ends (+ max_chunk).

    Fork mouths (T-junction branches) keep their necks; no mid collapse.
    Seals that collapse onto a single body are dropped (no cuts to nowhere).
    *cluster* expands each side with stacked satellites so mouths reach a
    host's dots (H→i-dot, not only H→stem top).
    """
    out = []
    expand_sats = bool(cluster)
    # Framed word: once stacked specks are host+wall tied, seal host mouths
    # only (stem↔H) — do not re-open via the speck coast (H↔i-dot).
    if (expand_sats and container is not None and not container.isEmpty()
            and against is not None and not against.isEmpty()):
        sats = (_stacked_satellites_of(path_a, cluster)
                + _stacked_satellites_of(path_b, cluster))
        if sats:
            done = True
            for sat in sats:
                if not _is_compact_island(sat, cluster):
                    done = False
                    break
                host = _stacked_host_of(sat, cluster)
                tgts = [container]
                if host is not None:
                    tgts.append(host)
                if peel_frame is not None and not peel_frame.isEmpty():
                    tgts.append(peel_frame)
                if len(_compact_tie_segs(against, sat, tgts)) < _MIN_COMPACT_TIES:
                    done = False
                    break
            if done:
                expand_sats = False
    use_cluster = cluster if expand_sats else None
    a_use = (_with_stacked_satellites(path_a, cluster)
             if use_cluster else path_a)
    b_use = (_with_stacked_satellites(path_b, cluster)
             if use_cluster else path_b)
    mouths = _gap_mouths(path_a, path_b, cluster=use_cluster)
    if not mouths:
        return out
    ax, ay = _dominant_gap_axis(a_use, b_use)
    span = max(m[2] for m in mouths)
    hit_t = max(32.0, 2.0 * span)

    def mouth_done(pa, pb, dist):
        if against is None or against.isEmpty():
            return False
        mouth = (pa, pb, dist)
        if _mouth_near_spanning_seals(
                against, path_a, path_b, mouth, cluster=cluster):
            return True
        # Satellite already sealed to the neighbor — skip duplicate H↔i-dot.
        if cluster:
            for body, other in ((path_a, path_b), (path_b, path_a)):
                for sat in _stacked_satellites_of(body, cluster):
                    on_sat = (
                        _point_near_path(pa.x(), pa.y(), sat, tol=2.5)
                        or _point_near_path(pb.x(), pb.y(), sat, tol=2.5))
                    if not on_sat:
                        continue
                    if _pair_has_spanning_seal(against, sat, other):
                        return True
        return False

    def accept_pair(seg):
        """Across-alley mouth: must meet both keep walls (host or sat)."""
        if seg is None:
            return
        if not _seg_spans_pair(seg, a_use, b_use):
            return
        out.append(seg)

    def accept_any(seg):
        """Side-pocket necks may both land on one wall."""
        if seg is not None:
            out.append(seg)

    aligned = []
    for pa, pb, dist in mouths:
        pa, pb = _order_mouth_to_paths(pa, pb, a_use, b_use)
        qa, qb = _axis_hit_pair(
            pa, pb, ax, ay, a_use, b_use, max_t=hit_t)
        aligned.append((qa, qb, dist))
    mouths = aligned
    raw_mouths = list(mouths)
    fork_mis = _pair_fork_mouth_indices(
        path_a, path_b, mouths, fork_mouths)
    if len(mouths) == 2:
        (pa0, pb0, d0), (pa1, pb1, d1) = mouths
        m0x = 0.5 * (pa0.x() + pb0.x())
        m0y = 0.5 * (pa0.y() + pb0.y())
        m1x = 0.5 * (pa1.x() + pb1.x())
        m1y = 0.5 * (pa1.y() + pb1.y())
        dx, dy = m1x - m0x, m1y - m0y
        ln = math.hypot(dx, dy)
        # Width = facing gap; fall back to mean keep-to-keep mouth length.
        facing = _corridor_facing(a_use, b_use)
        if facing is None:
            facing = _corridor_facing(path_a, path_b)
        width = facing[3] if facing is not None else 0.0
        if width < 1e-6:
            la = math.hypot(pa0.x() - pb0.x(), pa0.y() - pb0.y())
            lb = math.hypot(pa1.x() - pb1.x(), pa1.y() - pb1.y())
            width = 0.5 * (la + lb)
            if width < 1e-6:
                width = 0.5 * (float(d0) + float(d1))
        short = width > 1e-6 and ln <= _CORRIDOR_SHORT_K * width
        if short and not fork_mis:
            t = 0.5
            pa = QPointF(pa0.x() + t * (pa1.x() - pa0.x()),
                         pa0.y() + t * (pa1.y() - pa0.y()))
            pb = QPointF(pb0.x() + t * (pb1.x() - pb0.x()),
                         pb0.y() + t * (pb1.y() - pb0.y()))
            mid_dist = 0.5 * (float(d0) + float(d1))
            if not mouth_done(pa, pb, mid_dist):
                accept_pair(_mouth_seal(
                    a_use, b_use, pa, pb, ax, ay, hit_t, standoff, keep_fill,
                    work, min_cut, container, rules=rules, against=against,
                    peel_frame=peel_frame))
            for seg in _channel_side_opening_seals(
                    path_a, path_b, _channel_core(path_a, path_b), keep_fill,
                    work, standoff, min_cut, container):
                accept_any(seg)
            return out
        if short and fork_mis:
            keep_idx = sorted(i for i in fork_mis if 0 <= i < len(mouths))
            if keep_idx:
                mouths = [mouths[i] for i in keep_idx]
                raw_mouths = list(mouths)
                for pa, pb, dist in mouths:
                    if mouth_done(pa, pb, dist):
                        continue
                    accept_pair(_mouth_seal(
                        a_use, b_use, pa, pb, ax, ay, hit_t, standoff,
                        keep_fill, work, min_cut, container, rules=rules,
                        against=against, peel_frame=peel_frame))
                for seg in _channel_side_opening_seals(
                        path_a, path_b, _channel_core(path_a, path_b),
                        keep_fill, work, standoff, min_cut, container):
                    accept_any(seg)
                return out
    for pa, pb, dist in mouths:
        if mouth_done(pa, pb, dist):
            continue
        accept_pair(_mouth_seal(
            a_use, b_use, pa, pb, ax, ay, hit_t, standoff, keep_fill,
            work, min_cut, container, rules=rules, against=against,
            peel_frame=peel_frame))
    for seg in _corridor_chunk_seals(
            a_use, b_use, raw_mouths, max_chunk, ax, ay, hit_t, standoff,
            keep_fill, work, min_cut, container, rules=rules,
            against=against, peel_frame=peel_frame):
        accept_pair(seg)
    core = _channel_core(path_a, path_b)
    for seg in _channel_side_opening_seals(
            path_a, path_b, core, keep_fill, work, standoff, min_cut,
            container):
        accept_any(seg)
    return out


def _bodies_touch(path_a, path_b, tol=1.0):
    """True if two keep outlines already meet (no weed cut needed)."""
    pair = _nearest_pair(path_a, path_b)
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
        if not _gap_blocked(path_a, path_b, [o]):
            continue
        ys.append(o.boundingRect().center().y())
    if not ys:
        return True
    return (sum(ys) / float(len(ys))) < mid_y


def _fuse_kind(path_a, path_b, others, cluster=None):
    """How two islands join, or None if this pair should be skipped."""
    if _bodies_touch(path_a, path_b):
        return 'touch'
    if _is_stacked_satellite(path_a, path_b) or _is_stacked_satellite(
            path_b, path_a):
        return 'satellite'
    a_use = _with_stacked_satellites(path_a, cluster) if cluster else path_a
    b_use = _with_stacked_satellites(path_b, cluster) if cluster else path_b
    block_others = []
    for o in others or []:
        if o is None or o is path_a or o is path_b:
            continue
        if o is a_use or o is b_use:
            continue
        if _is_stacked_satellite(o, path_a) or _is_stacked_satellite(
                o, path_b):
            continue
        block_others.append(o)
    if a_use is not path_a or b_use is not path_b:
        if _bodies_touch(a_use, b_use):
            return 'touch'
    if _gap_blocked(a_use, b_use, block_others):
        if _is_hanging(a_use, b_use):
            return None
        # Hanging/compact blockers are chain links — do not around-fuse
        # a long bypass over them (quote alley → O stub class).
        if _gap_blockers_are_ticks(a_use, b_use, block_others, clus=cluster):
            return None
        return 'around'
    if _is_corridor_pair(a_use, b_use):
        return 'corridor'
    if _is_hanging(a_use, b_use):
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
        if not _gap_blocked(path_a, path_b, [o]):
            continue
        saw = True
        if _is_compact_island(o, cluster):
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
    compact_a = _is_compact_island(path_a, clus)
    compact_b = _is_compact_island(path_b, clus)
    if compact_a or compact_b:
        # Square ties own speck geometry; always merge the group here.
        return []
    a_use = _with_stacked_satellites(path_a, clus)
    b_use = _with_stacked_satellites(path_b, clus)
    if kind == 'corridor':
        return _seal_corridor_pair(
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
            if _is_stacked_satellite(o, path_a) or _is_stacked_satellite(
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
        mouths = _gap_mouths(path_a, path_b, cluster=clus)
        if mouths:
            if top:
                pair = min(mouths, key=lambda m: 0.5 * (m[0].y() + m[1].y()))
            else:
                pair = max(mouths, key=lambda m: 0.5 * (m[0].y() + m[1].y()))
        if pair is None:
            pair = _gutter_pair(a_use, b_use, top)
    if pair is None:
        pair = _nearest_pair(a_use, b_use)
    if pair is None:
        return None
    ax, ay = _dominant_gap_axis(a_use, b_use)
    span = float(pair[2]) if len(pair) > 2 else math.hypot(
        pair[1].x() - pair[0].x(), pair[1].y() - pair[0].y())
    hit_t = max(32.0, 2.0 * span)
    pa, pb = _order_mouth_to_paths(pair[0], pair[1], a_use, b_use)
    qa, qb = _axis_hit_pair(pa, pb, ax, ay, a_use, b_use, max_t=hit_t)
    seg = _mouth_seal(
        a_use, b_use, qa, qb, ax, ay, hit_t, standoff, keep_fill,
        work, min_cut, container, rules=rules, against=against,
        peel_frame=peel_frame, near_mouth=True)
    if seg is not None:
        return [seg]
    seg = _fuse_bridge(
        pa, pb, standoff, keep_fill, work, min_cut, container)
    if seg is None or not _seg_spans_pair(seg, a_use, b_use):
        return None
    if rules is not None:
        emit_keep = keep_fill if keep_fill is not None else a_use
        if not _seg_emit_ok(
                seg, emit_keep, against, rules, peel_frame=peel_frame):
            if not _seg_forced_ok(
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
            pair = _nearest_pair(a, b)
            if pair is None:
                continue
            cands.append((pair[2], a, b))
    cands.sort(key=lambda t: t[0])
    def sat_of(body, group):
        return any(
            _is_stacked_satellite(body, h) for h in group if h is not body)

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
        if (_is_compact_island(a, cluster)
                or _is_compact_island(b, cluster)):
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
    fork_mouths = _fork_branch_mouths(cluster)

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
                if (_is_compact_island(pa, cluster)
                        or _is_compact_island(pb, cluster)):
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
                _add_seg(out, seg, 0.0, keep_path=keep_fill)
                _add_seg(seen, seg, 0.0, keep_path=keep_fill)
            if kind == 'satellite':
                for i in groups[gi]:
                    if any(_is_stacked_satellite(cluster[i], h)
                           for h in [cluster[j] for j in groups[gj]]):
                        sat_ids.add(i)
                for j in groups[gj]:
                    if any(_is_stacked_satellite(cluster[j], h)
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


# Speck stacked on a host: span along the gap vs the host.
_SATELLITE_SPAN = 0.45
# Gap may be up to this times the speck's own stack-axis size.
_SATELLITE_MAX_GAP = 1.25
_SATELLITE_MIN_OVERLAP = 0.5
# Hanging mark vs its host (apostrophe, comma, quote vs a letter).
_HANGING_HEIGHT = 0.55


def _gap_axis_spans(path_a, path_b):
    """Each island's size along the gap axis (stack direction)."""
    ra, rb = path_a.boundingRect(), path_b.boundingRect()
    ux, uy = _dominant_gap_axis(path_a, path_b)
    if abs(ux) >= abs(uy):
        return ra.width(), rb.width()
    return ra.height(), rb.height()


def _is_stacked_satellite(speck, host):
    """True if *speck* is a small stacked island on *host* (dot on a stem)."""
    if speck is None or host is None or speck.isEmpty() or host.isEmpty():
        return False
    if _path_area(speck) >= 0.5 * _path_area(host):
        return False
    facing = _corridor_facing(speck, host)
    if facing is None:
        return False
    overlap, size_a, size_b, gap = facing
    if overlap < _SATELLITE_MIN_OVERLAP * min(size_a, size_b):
        return False
    hr = host.boundingRect()
    host_tall = hr.height() >= hr.width()
    ux, uy = _dominant_gap_axis(speck, host)
    gap_vertical = abs(uy) > abs(ux)
    if host_tall != gap_vertical:
        return False
    span_s, span_h = _gap_axis_spans(speck, host)
    if span_s > _SATELLITE_SPAN * span_h or span_s < 1e-6:
        return False
    return gap <= _SATELLITE_MAX_GAP * span_s


def _is_hanging(path_a, path_b):
    """True if one island is a short mark beside a taller neighbor."""
    if path_a is None or path_b is None or path_a.isEmpty() or path_b.isEmpty():
        return False
    if _is_stacked_satellite(path_a, path_b) or _is_stacked_satellite(
            path_b, path_a):
        return False
    if _is_corridor_pair(path_a, path_b):
        return False
    ha = path_a.boundingRect().height()
    hb = path_b.boundingRect().height()
    if min(ha, hb) < 1e-6:
        return False
    return min(ha, hb) < _HANGING_HEIGHT * max(ha, hb)


def _hanging_host(body, cluster):
    """Nearest taller neighbor that forms a hanging pair, or None."""
    if body is None or body.isEmpty():
        return None
    bh = body.boundingRect().height()
    best = None
    for other in cluster:
        if other is body or other is None or other.isEmpty():
            continue
        if other.boundingRect().height() <= bh:
            continue
        if not _is_hanging(body, other):
            continue
        pair = _nearest_pair(body, other)
        if pair is None:
            continue
        if best is None or pair[2] < best[0]:
            best = (pair[2], other)
    return None if best is None else best[1]


def _gutter_pair(hanging, major, top):
    """Outline pair near the outer ends, preferring the true gutter."""
    pairs = _outline_pairs(hanging, major)
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


def _seal_divergent_corridors(cluster, keep_fill, work, standoff, min_cut,
                              container, against=None, max_chunk=None,
                              rules=None, peel_frame=None):
    """Seal leftover wrap alleys (both mouths) after islands are one piece."""
    out = QPainterPath()
    seen = QPainterPath()
    if against is not None:
        seen.addPath(against)
    n = len(cluster)
    fork_mouths = _fork_branch_mouths(cluster)
    for i in range(n):
        for j in range(i + 1, n):
            others = [cluster[k] for k in range(n) if k != i and k != j]
            if _gap_blocked(cluster[i], cluster[j], others):
                continue
            if _is_hanging(cluster[i], cluster[j]):
                continue
            if _is_stacked_satellite(cluster[i], cluster[j]) or (
                    _is_stacked_satellite(cluster[j], cluster[i])):
                continue
            if not _is_corridor_pair(cluster[i], cluster[j]):
                continue
            for seg in _seal_corridor_pair(
                    cluster[i], cluster[j], keep_fill, work, standoff,
                    min_cut, container, max_chunk=max_chunk,
                    fork_mouths=fork_mouths, cluster=cluster,
                    rules=rules, against=seen, peel_frame=peel_frame):
                if _seg_redundant(seen, seg) or _seg_crosses_path(seen, seg):
                    continue
                _add_seg(out, seg, 0.0, keep_path=keep_fill)
                _add_seg(seen, seg, 0.0, keep_path=keep_fill)
    return out


def _cluster_keep_outline(cluster):
    """Union outline of keep bodies (for one outer frame-opening channel)."""
    acc = QPainterPath()
    for b in cluster:
        if b is None or b.isEmpty():
            continue
        if acc.isEmpty():
            acc = QPainterPath(b)
        else:
            acc = acc.united(b)
    return None if acc.isEmpty() else acc


def _keep_to_collar_landings(weed_path, cluster, collar_rings, standoff,
                             tol=None, ring_tol=2.0):
    """Wall-ring (x, y) ends of keep→wall radials (not peel-rail edges)."""
    if weed_path is None or weed_path.isEmpty() or not collar_rings:
        return []
    tol = float(standoff + 1.5 if tol is None else tol)
    keep_edges = []
    for b in cluster:
        if b is None or b.isEmpty():
            continue
        keep_edges.extend(_keep_outline_edges(b))
    if not keep_edges:
        return []
    out = []
    for x0, y0, x1, y1 in _iter_line_segs(weed_path):
        # Rail edges sit on the ring at mid; radials cross waste.
        mx, my = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
        mid = _nearest_on_rings(mx, my, collar_rings)
        if mid is not None and mid[2] <= ring_tol:
            continue
        a_keep = _point_near_edges(x0, y0, keep_edges, tol)
        b_keep = _point_near_edges(x1, y1, keep_edges, tol)
        a_col = _nearest_on_rings(x0, y0, collar_rings)
        b_col = _nearest_on_rings(x1, y1, collar_rings)
        a_on = a_col is not None and a_col[2] <= tol
        b_on = b_col is not None and b_col[2] <= tol
        if a_keep and b_on and not b_keep:
            out.append((x1, y1))
        elif b_keep and a_on and not a_keep:
            out.append((x0, y0))
    return out


def _has_keep_to_collar_channel(weed_path, cluster, collar_rings, standoff,
                                tol=None):
    """True if some open weed already runs from keep to the wall rings."""
    if weed_path is None or weed_path.isEmpty() or not collar_rings:
        return False
    tol = float(standoff + 1.5 if tol is None else tol)
    keep_edges = []
    for b in cluster:
        if b is None or b.isEmpty():
            continue
        keep_edges.extend(_keep_outline_edges(b))
    if not keep_edges:
        return False
    for x0, y0, x1, y1 in _iter_line_segs(weed_path):
        a_keep = _point_near_edges(x0, y0, keep_edges, tol)
        b_keep = _point_near_edges(x1, y1, keep_edges, tol)
        a_col = _nearest_on_rings(x0, y0, collar_rings)
        b_col = _nearest_on_rings(x1, y1, collar_rings)
        a_on = a_col is not None and a_col[2] <= tol
        b_on = b_col is not None and b_col[2] <= tol
        if (a_keep and b_on) or (b_keep and a_on):
            return True
    return False


def _x_sorted_bodies(cluster):
    """Bodies left→right; taller first at the same x (stem before its dot)."""
    bodies = [b for b in cluster if b is not None and not b.isEmpty()]
    bodies.sort(key=lambda b: (
        b.boundingRect().center().x(),
        -b.boundingRect().height(),
        b.boundingRect().center().y()))
    return bodies


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


def _rotate_hat(ux, uy, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return (c * ux - s * uy, s * ux + c * uy)


def _closest_on_line_segs(px, py, path):
    """Closest point on any line segment of *path*, or None."""
    if path is None or path.isEmpty():
        return None
    best = None
    for x0, y0, x1, y1 in _iter_line_segs(path):
        vx, vy = x1 - x0, y1 - y0
        ln2 = vx * vx + vy * vy
        if ln2 < 1e-12:
            qx, qy = x0, y0
        else:
            t = ((px - x0) * vx + (py - y0) * vy) / ln2
            t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
            qx, qy = x0 + t * vx, y0 + t * vy
        d = math.hypot(px - qx, py - qy)
        if best is None or d < best[0]:
            best = (d, qx, qy)
    if best is None:
        return None
    return (best[1], best[2], best[0])


def _square_tie_cands(island, targets, keep_fill, work, min_cut, container):
    """Short near-normal seals from a compact island to nearby coasts."""
    if island is None or island.isEmpty() or not targets:
        return []
    samples = _outline_samples(island, max_pts=10)
    corners = _convex_corners(island)
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
        seg = _fuse_bridge(
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
        pair = _nearest_pair(island, tgt)
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
            hit = _closest_on_line_segs(c.x(), c.y(), tgt)
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
        frame = _keep_frame_at(island, p)
        if frame is None or frame.n_hat is None:
            continue
        nx, ny = frame.n_hat
        for deg in (0.0, 25.0, -25.0):
            ux, uy = _rotate_hat(nx, ny, deg)
            for tgt in near_tgts:
                hit = _ray_hit_path(p, ux, uy, tgt, max_t=24.0)
                if hit is not None:
                    add(p, hit)
        # Peel frames are open polylines — `_ray_hit_path` needs closed
        # rings — so also project onto line segs along the outward normal.
        for tgt in near_tgts:
            if _path_to_rings(tgt):
                continue
            hit = _closest_on_line_segs(p.x(), p.y(), tgt)
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
    out = []
    if weed_path is None or weed_path.isEmpty() or speck is None:
        return out
    seen = set()
    for tgt in targets:
        if tgt is None or tgt.isEmpty() or tgt is speck:
            continue
        for seg in _pair_spanning_segs(weed_path, speck, tgt):
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
    a_on = _point_near_path(seg[0], seg[1], speck, tol=2.5)
    b_on = _point_near_path(seg[2], seg[3], speck, tol=2.5)
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
    if not cands:
        return None
    use_rules = rules if rules is not None else _cut_rules()
    others = _other_weed_segs(against)
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
        if against is not None and _seg_crosses_path(against, seg):
            rejected.append(('cross_weed', seg))
            continue
        if _seg_emit_ok(
                seg, keep_fill, against, use_rules, peel_frame=peel_frame,
                other_segs=others):
            legal.append(seg)
        elif _seg_forced_ok(
                seg, keep_fill, against, use_rules, peel_frame=peel_frame,
                other_segs=others):
            forced.append(seg)
        else:
            rejected.append((
                _seg_emit_fail_reason(
                    seg, keep_fill, against, use_rules,
                    peel_frame=peel_frame, other_segs=others) or 'forced_fail',
                seg))

    def _prefer_host(pool):
        if not pool:
            return None
        if not hosts:
            return _pick_quality_seg(pool, keep_fill, peel_frame=peel_frame)
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
                if (_point_near_path(seg[0], seg[1], h, tol=2.5)
                        or _point_near_path(seg[2], seg[3], h, tol=2.5)):
                    best = max(best, abs(_path_area(h)))
            return best

        near.sort(key=lambda s: (
            -host_hit(s),
            _peel_rank_key(s, keep_fill, peel_frame=peel_frame)))
        return near[0] if near else _pick_quality_seg(
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
        _point_near_path(seg[0], seg[1], target, tol=tol)
        or _point_near_path(seg[2], seg[3], target, tol=tol))


def _path_near_seg(path, seg, tol=2.0):
    """True if any outline sample of *path* lies within *tol* of *seg*."""
    if path is None or path.isEmpty() or seg is None:
        return False
    br = path.boundingRect().adjusted(-tol, -tol, tol, tol)
    x0, y0, x1, y1 = seg
    if (max(x0, x1) < br.left() or min(x0, x1) > br.right()
            or max(y0, y1) < br.top() or min(y0, y1) > br.bottom()):
        return False
    for p in _outline_samples(path, max_pts=12):
        if _point_seg_dist(p.x(), p.y(), *seg) <= tol:
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
    for seg in _iter_line_segs(weed_path):
        if not _path_near_seg(speck, seg, tol=tol):
            continue
        a_hit = [t for t in live
                 if _point_near_path(seg[0], seg[1], t, tol=ep_tol)]
        if not a_hit:
            continue
        b_hit = [t for t in live
                 if _point_near_path(seg[2], seg[3], t, tol=ep_tol)]
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
            pair = _nearest_pair(speck, other)
            if pair is not None and pair[2] <= 12.0:
                targets.append(other)
        if not targets:
            continue
        host = _stacked_host_of(speck, cluster)
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
                        pair = _nearest_pair(speck, other)
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
            before_n = weed_path_stats(seen)['segments']
            _add_seg(seen, picked, 0.0, keep_path=keep_fill)
            if weed_path_stats(seen)['segments'] <= before_n:
                break
            _add_seg(out, picked, 0.0, keep_path=keep_fill)
    return out


def _frame_chain_bodies(cluster):
    """X-ordered keep bodies with stacked satellites folded into their host.

    Frame-peninsula necks run between consecutive *visible* islands along
    the cluster (stem+dot counts as one, hanging marks stay as links).
    Compact water specks are sealed separately (square ties), not as chain
    links that spawn long parallel rails.
    """
    bodies = _x_sorted_bodies(cluster)
    skip = set()
    for b in bodies:
        if _is_compact_island(b, cluster):
            skip.add(id(b))
            continue
        for other in bodies:
            if other is b or id(other) in skip:
                continue
            if _is_stacked_satellite(b, other):
                skip.add(id(b))
                break
    return [b for b in bodies if id(b) not in skip]


def _frame_open_is_top(path_a, path_b, work, collar_rings=None):
    """Which open end of a side-by-side gap faces more outer-frame waste."""
    # Hanging marks sit in the frame-open wrap; seal at their outer end.
    if _is_hanging(path_a, path_b):
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
        near_top = _nearest_on_rings(mx, top, collar_rings)
        near_bot = _nearest_on_rings(mx, bot, collar_rings)
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
    pair = _gutter_pair(path_a, path_b, top)
    if pair is not None:
        return pair
    mouths = _gap_mouths(path_a, path_b)
    if not mouths:
        return _nearest_pair(path_a, path_b)
    if top:
        return min(mouths, key=lambda m: _gap_mouth_mid_y(m))
    return max(mouths, key=lambda m: _gap_mouth_mid_y(m))


def _frame_peninsula_should_seal(path_a, path_b, mouth, top, ratio):
    """Frame→letter opening is a bay (D007): seal by κ / depth gates."""
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
    run = _facing_frontier_pts(path_a, path_b)
    return _peninsula_should_detach(depth, width, run, ratio=ratio)


def _frame_mouth_on_corridor_core(path_a, path_b, mouth, tol=4.0):
    """True if *mouth* sits on an existing channel-core / facing end seal site."""
    if mouth is None:
        return False
    mx = _gap_mouth_mid_x(mouth)
    my = _gap_mouth_mid_y(mouth)
    for pa, pb, _d in _gap_mouths(path_a, path_b):
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
        if _bodies_touch(a, b):
            continue
        # Compact/tick bodies folded out of the chain still sit in the gap;
        # skip unless those ticks already have ≥2 ties (major neck still ok).
        gap_others = [c for c in cluster if c is not a and c is not b]
        through_tied = False
        if _gap_blocked(a, b, gap_others):
            walls = []
            if container is not None and not container.isEmpty():
                walls.append(container)
            if peel_frame is not None and not peel_frame.isEmpty():
                walls.append(peel_frame)
            if not _gap_blocked_only_by_tied_compacts(
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
        if _is_corridor_pair(a, b) and _pair_has_spanning_seal(seen, a, b):
            continue
        # Corridor core mouth sites, or any existing pair seal near this
        # open end, already provide the neck.
        if _is_corridor_pair(a, b) and _frame_mouth_on_corridor_core(
                a, b, mouth):
            continue
        if _mouth_near_spanning_seals(seen, a, b, mouth, cluster=cluster):
            continue
        pa, pb = mouth[0], mouth[1]
        if through_tied:
            # Open-end chord only — ranked mouth_seal climbs into ticks.
            seg = _fuse_bridge(
                pa, pb, 0.0, keep_fill, work, min_cut, container)
        else:
            ax, ay = _dominant_gap_axis(a, b)
            hit_t = max(32.0, 2.0 * float(mouth[2]))
            seg = _mouth_seal(
                a, b, pa, pb, ax, ay, hit_t, standoff, keep_fill, work,
                min_cut, container, rules=rules, against=seen,
                peel_frame=peel_frame, near_mouth=True)
        if seg is None or not _seg_spans_pair(seg, a, b):
            continue
        if _seg_redundant(seen, seg) or _seg_crosses_path(seen, seg):
            continue
        _add_seg(out, seg, 0.0, keep_path=keep_fill)
        _add_seg(seen, seg, 0.0, keep_path=keep_fill)
    return out


# Hanging marks in a wide major gap: leftover wrap at the hanging's end.
_WIDE_GAP_VS_HEIGHT = 0.8
_WIDE_GAP_MIN = 18.0


def _leftover_hanging_gutters(cluster, keep_fill, work, standoff, min_cut,
                              container, against=None, rules=None,
                              peel_frame=None):
    """If a wide alley still wraps past hanging marks, add the missing gutters."""
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
                pair = _nearest_pair(h, m)
                return pair[2] if pair else 1e9
            hang = min(in_gap, key=_hang_dist)
            # Already fused during agglomerate / bay — no second gutter.
            if _pair_join_already_effective(seen, hang, major, bodies):
                continue
            pair = _gutter_pair(hang, major, True)
            if pair is None:
                continue
            seg = _fuse_bridge(
                pair[0], pair[1], standoff, keep_fill, work,
                min_cut, container)
            if seg is None:
                continue
            if rules is not None:
                if not _seg_emit_ok(
                        seg, keep_fill, seen, rules, peel_frame=peel_frame):
                    if not _seg_forced_ok(
                            seg, keep_fill, seen, rules,
                            peel_frame=peel_frame):
                        continue
            if _seg_redundant(seen, seg) or _seg_crosses_path(seen, seg):
                continue
            _add_seg(out, seg, 0.0, keep_path=keep_fill)
            _add_seg(seen, seg, 0.0, keep_path=keep_fill)
    return out


def _gap_mouth_mid_y(mouth):
    pa, pb = mouth[0], mouth[1]
    return 0.5 * (pa.y() + pb.y())


def _gap_mouth_mid_x(mouth):
    pa, pb = mouth[0], mouth[1]
    return 0.5 * (pa.x() + pb.x())


def _cluster_gap_width(path_a, path_b, mouths):
    """Keep-to-keep width of a non-corridor gap."""
    facing = _corridor_facing(path_a, path_b)
    if facing is not None and facing[3] > 1e-6:
        return facing[3]
    if not mouths:
        return 0.0
    return sum(float(m[2]) for m in mouths) / float(len(mouths))


def _cluster_gap_depth(path_a, path_b, mouths):
    """How far waste runs along the gap (mouth span, else facing overlap)."""
    if len(mouths) >= 2:
        m0x = _gap_mouth_mid_x(mouths[0])
        m0y = _gap_mouth_mid_y(mouths[0])
        m1x = _gap_mouth_mid_x(mouths[-1])
        m1y = _gap_mouth_mid_y(mouths[-1])
        span = math.hypot(m1x - m0x, m1y - m0y)
        if span > 1e-6:
            return span
    facing = _corridor_facing(path_a, path_b)
    if facing is None:
        return 0.0
    return float(facing[0])


def _facing_frontier_pts(path_a, path_b):
    """One keep wall of the facing band, ordered along the alley."""
    pairs = _outline_pairs(path_a, path_b)
    if not pairs:
        return []
    dmin = pairs[0][2]
    slack = max(2.0, 0.25 * dmin)
    facing = [(pa, pb, d) for pa, pb, d in pairs if d <= dmin + slack]
    if not facing:
        return []
    ux, uy = _dominant_gap_axis(path_a, path_b)
    tx, ty = -uy, ux

    def along(pa, pb):
        mx = 0.5 * (pa.x() + pb.x())
        my = 0.5 * (pa.y() + pb.y())
        return mx * tx + my * ty

    facing.sort(key=lambda t: along(t[0], t[1]))
    return [(pa.x(), pa.y()) for pa, _pb, _d in facing]


def _hanging_pocket_mouth(path_a, path_b, cluster, mouths):
    """Inner-end mouth of a hanging mark vs its nearest taller host."""
    if not mouths or not _is_hanging(path_a, path_b):
        return None
    short, tall = path_a, path_b
    if short.boundingRect().height() > tall.boundingRect().height():
        short, tall = tall, short
    if _hanging_host(short, cluster) is not tall:
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
    if mouth is None:
        return None
    pa, pb, dist = mouth[0], mouth[1], float(mouth[2])
    if not _is_hanging(path_a, path_b):
        return mouth
    short, tall = path_a, path_b
    if short.boundingRect().height() > tall.boundingRect().height():
        short, tall = tall, short
    # Which endpoint sits on the short mark.
    if _point_near_path(pa.x(), pa.y(), short, tol=2.5):
        ps, pt = pa, pb
    elif _point_near_path(pb.x(), pb.y(), short, tol=2.5):
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
        turn = _angle_turn_deg(p0, p1, p2)
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
    out = QPainterPath()
    seen = QPainterPath()
    if against is not None:
        seen.addPath(against)
    ratio = (DEFAULT_PENINSULA_RATIO if peninsula_ratio is None
             else float(peninsula_ratio))
    wall_rings = _opening_wall_rings(collar_rings, container)
    bodies = [b for b in cluster if b is not None and not b.isEmpty()]
    n = len(bodies)
    if n < 2:
        return out
    for i in range(n):
        for j in range(i + 1, n):
            a, b = bodies[i], bodies[j]
            if _bodies_touch(a, b):
                continue
            if _is_stacked_satellite(a, b) or _is_stacked_satellite(b, a):
                continue
            others = [bodies[k] for k in range(n) if k != i and k != j]
            walls = []
            if container is not None and not container.isEmpty():
                walls.append(container)
            if peel_frame is not None and not peel_frame.isEmpty():
                walls.append(peel_frame)
            blocked = _gap_blocked(a, b, others)
            through_tied = False
            if blocked:
                # Well-tied compact ticks in the AABB must not forever
                # block a major↔major frame-heavier / bottom neck.
                if (_is_compact_island(a, bodies)
                        or _is_compact_island(b, bodies)):
                    continue
                if not _gap_blocked_only_by_tied_compacts(
                        a, b, others, bodies, seen, walls=walls):
                    continue
                through_tied = True
            # Corridors normally belong to agglomerate; when only tied
            # ticks blocked the gap, still emit one open-end neck here.
            if _is_corridor_pair(a, b) and not through_tied:
                continue
            # Speck→neighbor when the host alley is already sealed.
            if _satellite_neighbor_already_sealed(seen, a, b, bodies):
                continue
            mouths = _gap_mouths(a, b)
            if not mouths:
                continue
            width = _cluster_gap_width(a, b, mouths)
            depth = _cluster_gap_depth(a, b, mouths)
            run = _facing_frontier_pts(a, b)
            if not _peninsula_should_detach(depth, width, run, ratio=ratio):
                continue
            if _is_hanging(a, b):
                short, tall = a, b
                if short.boundingRect().height() > tall.boundingRect().height():
                    short, tall = tall, short
                # Dot stacked on a stem that already joins the neighbor
                # *near the speck* (same band). A distant host seal does not
                # cover a far pocket.
                if _satellite_neighbor_already_sealed(seen, a, b, bodies):
                    continue
                mouth = _hanging_pocket_mouth(a, b, bodies, mouths)
                mouth = _snap_hanging_mouth_to_corner(mouth, a, b)
                # Tight close neighbor already fused: skip *shallow* base
                # slides (apostrophe–s ~3 mm gap). Wider hanging gaps still
                # get a pocket even when the cut is nearly horizontal.
                reject_shallow = (
                    _pair_has_spanning_seal(seen, a, b)
                    and not _hanging_has_underarm_wrap(short, tall, bodies)
                    and width <= 5.0)
            else:
                reject_shallow = False
                if through_tied:
                    # Prefer the frame-heavier open end (usually bottom).
                    top = _frame_open_is_top(a, b, work, wall_rings)
                    mouth = _frame_mouth_pair(a, b, top)
                else:
                    mouth = _open_side_bay_mouth(mouths)
            if mouth is None:
                continue
            # Do not stack on an existing pair join at the same site.
            if _mouth_near_spanning_seals(seen, a, b, mouth):
                continue
            if _is_compact_island(a, bodies) or _is_compact_island(b, bodies):
                continue
            pa, pb, _dist = mouth
            if through_tied:
                # Open-end chord only — ranked mouth_seal climbs into ticks.
                seg = _fuse_bridge(
                    pa, pb, 0.0, keep_fill, work, min_cut, container)
            else:
                ax, ay = _dominant_gap_axis(a, b)
                hit_t = max(32.0, 2.0 * max(m[2] for m in mouths))
                seg = _mouth_seal(
                    a, b, pa, pb, ax, ay, hit_t, standoff, keep_fill,
                    work, min_cut, container, rules=rules, against=seen,
                    peel_frame=peel_frame)
            if seg is None or not _seg_spans_pair(seg, a, b):
                continue
            if reject_shallow and _seg_parallel_to_short_base(seg, a, b):
                continue
            if _seg_redundant(seen, seg) or _seg_crosses_path(seen, seg):
                continue
            _add_seg(out, seg, 0.0, keep_path=keep_fill)
            _add_seg(seen, seg, 0.0, keep_path=keep_fill)
    return out


def _seg_parallel_to_short_base(seg, path_a, path_b, deg=18.0):
    """True if *seg* skims along the short mark's top/bottom base.

    Hanging marks are usually upright: a cut that is nearly horizontal at
    the mark's bottom creates the shallow apostrophe→s angle. Reject those
    when an outer gutter already joins the pair.
    """
    if seg is None or not _is_hanging(path_a, path_b):
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


def _point_seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    ln2 = dx * dx + dy * dy
    if ln2 < 1e-18:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / ln2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _nearest_pt_index(pts, q):
    best_i = 0
    best_d = None
    for i, p in enumerate(pts):
        d = math.hypot(p.x() - q.x(), p.y() - q.y())
        if best_d is None or d < best_d:
            best_d = d
            best_i = i
    return best_i


def _bay_chain(pts, i0, i1, hull_idx):
    """Outline walk from i0 to i1 that does not pass other hull vertices."""
    n = len(pts)
    if n < 2 or i0 == i1:
        return None
    others = set(hull_idx) - {i0, i1}

    def walk(step):
        chain = [pts[i0]]
        i = i0
        for _ in range(n):
            i = (i + step) % n
            if i in others:
                return None
            chain.append(pts[i])
            if i == i1:
                return chain
        return None

    a, b = walk(1), walk(-1)
    if a and b:
        return a if len(a) <= len(b) else b
    return a or b


def _hull_bay_mouths(body, min_depth, min_width):
    """Mouths of concave bays: hull edges the outline dents away from."""
    pts = _unique_ring(_polyline_points(body, max_pts=256))
    pts = _densify_ring(pts, max_edge=8.0)
    if len(pts) < 4:
        return []
    hull = _convex_hull(pts)
    if len(hull) < 3:
        return []
    hull_idx = [_nearest_pt_index(pts, h) for h in hull]
    if len(set(hull_idx)) < 3:
        return []
    mouths = []
    n_h = len(hull)
    on_tol = 0.6
    for k in range(n_h):
        i0, i1 = hull_idx[k], hull_idx[(k + 1) % n_h]
        ha, hb = pts[i0], pts[i1]
        chain = _bay_chain(pts, i0, i1, hull_idx)
        if chain is None or len(chain) < 3:
            continue
        mouth_w = math.hypot(hb.x() - ha.x(), hb.y() - ha.y())
        if mouth_w < min_width:
            continue
        depths = [
            _point_seg_dist(p.x(), p.y(), ha.x(), ha.y(), hb.x(), hb.y())
            for p in chain
        ]
        max_d = max(depths)
        if max_d < min_depth:
            continue
        on_edge = [
            _point_seg_dist(p.x(), p.y(), ha.x(), ha.y(), hb.x(), hb.y())
            <= on_tol
            for p in chain
        ]
        i = 0
        n_c = len(chain)
        while i < n_c:
            if on_edge[i]:
                i += 1
                continue
            left = chain[i - 1] if i > 0 else chain[0]
            j = i
            while j < n_c and not on_edge[j]:
                j += 1
            right = chain[j] if j < n_c else chain[-1]
            run_d = max(depths[i:j]) if j > i else 0.0
            span = math.hypot(right.x() - left.x(), right.y() - left.y())
            if run_d >= min_depth and span >= min_width:
                deep = chain[i + depths[i:j].index(run_d)]
                # Off-edge walk only: mouth endpoints would inflate ρ on a U.
                mouths.append((left, right, deep, chain[i:j]))
            i = j
    return mouths


def _has_independent_waste_bays(body, tips, standoff, min_cut,
                                peninsula_ratio=None):
    """Bays that seal under D007 and are not valleys between keep tips."""
    min_width = 2.0 * float(standoff) + float(min_cut)
    min_depth = _bay_min_depth(standoff)
    ratio = (DEFAULT_PENINSULA_RATIO if peninsula_ratio is None
             else float(peninsula_ratio))
    for left, right, deep, run in _hull_bay_mouths(body, min_depth, min_width):
        mouth_w = math.hypot(right.x() - left.x(), right.y() - left.y())
        depth = _point_seg_dist(
            deep.x(), deep.y(), left.x(), left.y(), right.x(), right.y())
        if not _bay_should_seal(
                left, right, deep, run, depth=depth, mouth_w=mouth_w,
                ratio=ratio):
            continue
        # Fixed tol: large mouths must not treat nearby coast teeth as valley tips.
        if _mouth_between_keep_tips(left, right, tips, tol=2.0):
            continue
        return True
    return False


def _mouth_between_keep_tips(pa, pb, tips, tol=2.0):
    """True when both mouth ends sit on keep-peninsula tips (a star valley)."""
    if not tips:
        return False

    def near(p):
        for tip in tips:
            q = tip['pt'] if isinstance(tip, dict) else tip
            if math.hypot(p.x() - q.x(), p.y() - q.y()) <= tol:
                return True
        return False

    return near(pa) and near(pb)


def _body_pocket_seals(body, keep_fill, work, standoff, min_cut, container,
                       keep_tips=None, peninsula_ratio=None, against=None,
                       alpha_min=None, rules=None, peel_frame=None):
    """One peel-wall dam per body bay: mouth-nearest corner → opposite coast."""
    out = QPainterPath()
    seen = QPainterPath()
    if against is not None:
        seen.addPath(against)
    min_width = 2.0 * float(standoff) + float(min_cut)
    min_depth = _bay_min_depth(standoff)
    ratio = (DEFAULT_PENINSULA_RATIO if peninsula_ratio is None
             else float(peninsula_ratio))
    tips = keep_tips or ()
    use_rules = rules if rules is not None else _cut_rules()
    a_min = (float(alpha_min) if alpha_min is not None
             else use_rules.alpha_min)
    for left, right, deep, run in _hull_bay_mouths(body, min_depth, min_width):
        ln = math.hypot(right.x() - left.x(), right.y() - left.y())
        depth = _point_seg_dist(
            deep.x(), deep.y(), left.x(), left.y(), right.x(), right.y())
        if not _bay_should_seal(
                left, right, deep, run, depth=depth, mouth_w=ln, ratio=ratio):
            continue
        if _mouth_between_keep_tips(left, right, tips, tol=2.0):
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
        others = _other_weed_segs(seen)
        for anchor, locked in candidates:
            opposite = _bay_coast_opposite(
                anchor, left, right, run, deep=deep)
            for far in _iter_bay_far_ends(
                    anchor, opposite, body, a_min, locked,
                    left=left, right=right):
                if math.hypot(
                        far.x() - anchor.x(), far.y() - anchor.y()) < min_cut:
                    continue
                trial = _fuse_bridge(
                    anchor, far, standoff, keep_fill, work, min_cut, container)
                if trial is None:
                    continue
                if _seg_redundant(seen, trial) or _seg_crosses_path(seen, trial):
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
                    _near_waste_reflex_corner(body, QPointF(trial[0], trial[1])),
                    _near_waste_reflex_corner(body, QPointF(trial[2], trial[3])),
                )
                emit_keep = keep_fill if keep_fill is not None else body
                if _seg_emit_ok(
                        trial, emit_keep, seen, use_rules, peel_frame=peel_frame,
                        locked_ends=locked_ends, other_segs=others):
                    legal.append(trial)
                elif _seg_forced_ok(
                        trial, emit_keep, seen, use_rules, peel_frame=peel_frame,
                        locked_ends=locked_ends, other_segs=others):
                    forced.append(trial)
        def _mouth_rank_ok(s):
            # Class-0↔class-0 may *be* the mouth chord; inset only for edge–edge.
            if _seg_both_class0(s, body, peel_frame, body):
                return True
            # Keep exact mouth-corner anchors even when the chord skims the mouth.
            if primary is not None and (
                    math.hypot(s[0] - primary.x(), s[1] - primary.y()) <= 1.25
                    or math.hypot(s[2] - primary.x(), s[3] - primary.y()) <= 1.25):
                return True
            mx = 0.5 * (s[0] + s[2])
            my = 0.5 * (s[1] + s[3])
            return _point_seg_dist(
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
            return not _is_parallel_hug(s, body, DEFAULT_MIN_CUT)

        def _pick_pocket(cands):
            if not cands:
                return None
            pool = [s for s in cands if _mouth_rank_ok(s)]
            use = pool if pool else list(cands)
            chords = [s for s in use if _is_true_mouth_chord(s)]
            if chords:
                durable = [s for s in chords if _survives_hug(s)]
                return _pick_ranked_seg(
                    durable if durable else chords, body, body, peel_frame)
            if primary is not None:
                at_corner = [s for s in use if _end_near(s, primary)]
                if at_corner:
                    durable = [s for s in at_corner if _survives_hug(s)]
                    if durable:
                        return _pick_quality_seg(
                            durable, body, body, peel_frame, prefer=a_min)
            durable = [s for s in use if _survives_hug(s)]
            return _pick_quality_seg(
                durable if durable else use, body, body, peel_frame)

        seg = _pick_pocket(legal)
        if seg is None:
            short_f = [s for s in forced
                       if math.hypot(s[2] - s[0], s[3] - s[1]) <= 24.0]
            seg = _pick_pocket(short_f)
        if seg is None:
            continue
        _add_seg(out, seg, 0.0)
        _add_seg(seen, seg, 0.0)
    return out


def _in_keep_interior(keep_fill, p, coast_tol=0.05):
    """True if *p* is clearly inside keep (not on/near the coast)."""
    if keep_fill is None or keep_fill.isEmpty() or p is None:
        return False
    if not keep_fill.contains(p):
        return False
    # contains() is unreliable on the outline; exact corner landings sit there.
    return not _point_near_path(p.x(), p.y(), keep_fill, tol=coast_tol)


def _waste_seg_or_none(x0, y0, x1, y1, keep_fill, work, min_cut,
                       container=None):
    capped = _clip_seg_to_rect(x0, y0, x1, y1, work)
    if capped is None:
        return None
    if math.hypot(capped[2] - capped[0], capped[3] - capped[1]) < min_cut:
        return None
    n = 12
    for i in range(1, n):
        t = i / float(n)
        x = capped[0] + (capped[2] - capped[0]) * t
        y = capped[1] + (capped[3] - capped[1]) * t
        p = QPointF(x, y)
        if _in_keep_interior(keep_fill, p):
            return None
        if container is not None and not container.contains(p):
            return None
    return capped


def _tip_spokes(tips, collar_rings, frame_ring, keep_fill, work,
                clearance, min_cut, max_spokes, against=None):
    """One spoke per convex tip: tip → nearest of collar or frame."""
    out = QPainterPath()
    ranked = sorted(tips, key=lambda t: -t['turn'])
    used = []
    targets = list(collar_rings or [])
    extra = [frame_ring] if frame_ring else []
    for tip in ranked:
        if len(used) >= max_spokes:
            break
        p1 = tip['pt']
        if any(math.hypot(p1.x() - u.x(), p1.y() - u.y()) < min_cut * 3
               for u in used):
            continue
        dx, dy = tip['dx'], tip['dy']
        standoff = max(float(clearance), min_cut * 0.25)
        sx = p1.x() + dx * standoff
        sy = p1.y() + dy * standoff
        hit_c = _ray_intersect_rings(sx, sy, dx, dy, targets)
        hit_f = _ray_intersect_rings(sx, sy, dx, dy, extra)
        hit = None
        if hit_c is not None and hit_f is not None:
            hit = hit_c if hit_c[2] <= hit_f[2] else hit_f
        else:
            hit = hit_c if hit_c is not None else hit_f
        if hit is None:
            continue
        seg = _waste_seg_or_none(sx, sy, hit[0], hit[1], keep_fill, work, min_cut)
        if seg is None:
            continue
        if against is not None and _seg_crosses_path(against, seg):
            continue
        _add_seg(out, seg, min_cut)
        used.append(p1)
    return out


def _nearest_on_rings(px, py, rings):
    """Closest point on any ring edge. (x, y, dist) or None."""
    best = None
    best_d = None
    for ring in rings:
        n = len(ring)
        if n < 2:
            continue
        for i in range(n):
            a, b = ring[i], ring[(i + 1) % n]
            ax, ay, bx, by = a.x(), a.y(), b.x(), b.y()
            dx, dy = bx - ax, by - ay
            ln2 = dx * dx + dy * dy
            if ln2 < 1e-18:
                qx, qy = ax, ay
            else:
                t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / ln2))
                qx, qy = ax + t * dx, ay + t * dy
            d = math.hypot(qx - px, qy - py)
            if best_d is None or d < best_d:
                best_d = d
                best = (qx, qy, d)
    return best


def _shortest_outer_channel(outline, collar_rings, keep_fill, work, min_cut,
                            clearance=0.0, container=None):
    """Shortest waste cut from keep to wall rings (peel frame or container).

    Keep end is the outline point. Channel standoff is only a ray-search
    probe — not a permanent gap at keep. *collar_rings* may be a grown peel
    rail or the design-container coast (D013).
    """
    pts = _unique_ring(_polyline_points(outline, max_pts=64))
    n = len(pts)
    if n < 3 or not collar_rings:
        return None
    standoff = max(float(clearance), DEFAULT_CHANNEL_STANDOFF, 0.15)
    # Allow keep→collar length up to the real peel-frame gap (D013).
    max_ln = max(12.0, 8.0 * standoff)
    for p in pts:
        near = _nearest_on_rings(p.x(), p.y(), collar_rings)
        if near is not None and near[2] > 1e-9:
            max_ln = max(max_ln, near[2] * 1.2 + float(min_cut))
    best = None
    best_len = None

    def consider(ox, oy, dx, dy):
        """*ox,oy* on the keep outline; ray along unit *(dx,dy)* to collar."""
        nonlocal best, best_len
        probe = QPointF(ox + dx * _SEARCH_PROBE, oy + dy * _SEARCH_PROBE)
        if keep_fill is not None and keep_fill.contains(probe):
            return
        if container is not None and not container.contains(probe):
            return
        px = ox + dx * standoff
        py = oy + dy * standoff
        hit = _ray_intersect_rings(px, py, dx, dy, collar_rings)
        if hit is None:
            hit = _ray_intersect_rings(
                probe.x(), probe.y(), dx, dy, collar_rings)
        if hit is None:
            return
        seg = _waste_seg_or_none(
            ox, oy, hit[0], hit[1], keep_fill, work, 0.0,
            container=container)
        if seg is None:
            return
        ln = math.hypot(seg[2] - seg[0], seg[3] - seg[1])
        if ln < min_cut or ln > max_ln:
            return
        if best_len is None or ln < best_len - 1e-9:
            best_len = ln
            best = seg

    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        ex, ey = b.x() - a.x(), b.y() - a.y()
        eln = math.hypot(ex, ey)
        if eln < 1e-9:
            continue
        mx = 0.5 * (a.x() + b.x())
        my = 0.5 * (a.y() + b.y())
        dx, dy = _orient_outward(mx, my, -ey, ex, outline)
        consider(mx, my, dx, dy)

    if best is not None:
        return best
    for p in pts:
        near = _nearest_on_rings(p.x(), p.y(), collar_rings)
        if near is None or near[2] < 1e-9:
            continue
        dx, dy = (near[0] - p.x()) / near[2], (near[1] - p.y()) / near[2]
        consider(p.x(), p.y(), dx, dy)
    return best


def _hole_internal_splits(hole_path, keep_fill, max_chunk, min_cut):
    """Axis-aligned splits that stay inside a huge hole (never through keep)."""
    out = QPainterPath()
    if hole_path is None or hole_path.isEmpty():
        return out
    br = hole_path.boundingRect()
    if max(br.width(), br.height()) <= max_chunk:
        return out
    if br.width() >= br.height():
        n = max(int(math.ceil(br.width() / max_chunk)) - 1, 1)
        n = min(n, 8)
        for i in range(1, n + 1):
            x = br.left() + br.width() * i / float(n + 1)
            segs = _clip_line_to_region(
                x, br.top(), x, br.bottom(), hole_path, invert_keep=False,
                samples=64, min_len=min_cut)
            for s in segs:
                inner = _clip_line_to_region(
                    s[0], s[1], s[2], s[3], keep_fill, invert_keep=True,
                    samples=48, min_len=min_cut)
                _add_line_segs(out, inner)
    else:
        n = max(int(math.ceil(br.height() / max_chunk)) - 1, 1)
        n = min(n, 8)
        for i in range(1, n + 1):
            y = br.top() + br.height() * i / float(n + 1)
            segs = _clip_line_to_region(
                br.left(), y, br.right(), y, hole_path, invert_keep=False,
                samples=64, min_len=min_cut)
            for s in segs:
                inner = _clip_line_to_region(
                    s[0], s[1], s[2], s[3], keep_fill, invert_keep=True,
                    samples=48, min_len=min_cut)
                _add_line_segs(out, inner)
    return out


def weed_path_stats(path):
    """Debug/metrics: segment count and total length."""
    segs = 0
    length = 0.0
    x0 = y0 = None
    for i in range(path.elementCount() if path is not None else 0):
        e = path.elementAt(i)
        if e.isMoveTo():
            x0, y0 = e.x, e.y
            continue
        if x0 is not None:
            length += math.hypot(e.x - x0, e.y - y0)
            segs += 1
        x0, y0 = e.x, e.y
    return {'segments': segs, 'length': length}


def _audit_firm_rules(weed_path, keep_path, rules):
    """Post-hoc firm-rule scan (logging only; does not mutate)."""
    segs = list(_iter_line_segs(weed_path))
    crosses = []
    for i, a in enumerate(segs):
        for b in segs[i + 1:]:
            if _seg_proper_cross(a[0], a[1], a[2], a[3],
                                 b[0], b[1], b[2], b[3]):
                crosses.append((a, b))
    _wdbg.log('audit.cross_weed', count=len(crosses))
    for a, b in crosses[:12]:
        _wdbg.log('audit.cross_pair', a=a, b=b)
    clearance_hits = 0
    alpha_hits = 0
    for seg in segs:
        others = [s for s in segs if s != seg]
        if not _seg_body_clearance_ok(
                seg, keep_path, others, clearance=rules.body_clearance):
            clearance_hits += 1
            if clearance_hits <= 8:
                _wdbg.log('audit.body_clearance', seg=seg)
        if not _seg_alpha_ok(seg, keep_path, alpha_min=rules.alpha_min):
            alpha_hits += 1
            if alpha_hits <= 8:
                _wdbg.log('audit.alpha_min', seg=seg)
    _wdbg.log(
        'audit.summary', segs=len(segs), cross=len(crosses),
        body_clearance=clearance_hits, alpha_min=alpha_hits)


def sample_points_on_path(path, step=2.0):
    """Approximate samples along line segments of *path*."""
    pts = []
    if path is None or path.isEmpty():
        return pts
    x0 = y0 = None
    for i in range(path.elementCount()):
        e = path.elementAt(i)
        if e.isMoveTo():
            x0, y0 = e.x, e.y
            continue
        x1, y1 = e.x, e.y
        if x0 is None:
            x0, y0 = x1, y1
            continue
        dx, dy = x1 - x0, y1 - y0
        length = math.hypot(dx, dy)
        n = max(int(length / step), 1)
        for k in range(n + 1):
            t = k / float(n)
            pts.append(QPointF(x0 + dx * t, y0 + dy * t))
        x0, y0 = x1, y1
    return pts


def weed_sample_stats(path, keep_fill=None, work_rect=None, step=1.0):
    """Stats plus sample counts outside the work rect / inside keep interior.

    Exact coast landings (chosen corners/edges) are not counted as in-keep.
    """
    base = weed_path_stats(path)
    pts = sample_points_on_path(path, step=step)
    outside = 0
    in_keep = 0
    for p in pts:
        if work_rect is not None and not _rect_contains_inclusive(
                work_rect, p.x(), p.y()):
            outside += 1
        if _in_keep_interior(keep_fill, p):
            in_keep += 1
    n = float(len(pts)) if pts else 1.0
    base['samples'] = len(pts)
    base['outside_work'] = outside
    base['in_keep'] = in_keep
    base['outside_work_frac'] = outside / n
    base['in_keep_frac'] = in_keep / n
    return base


ResidualWasteTrap = namedtuple(
    'ResidualWasteTrap',
    ('kind', 'x', 'y', 'depth', 'mouth', 'rho', 'tip_count'))


def _enclosure_collar_rings(keep_path, collar_margin):
    """Isolation collar rings per enclosure group (same as enclosure_weeds)."""
    closed = list_closed_subpaths(keep_path)
    if not closed:
        return []
    nodes = _nest_closed_paths(closed)
    rings = []
    for cluster, _container in _enclosure_groups(nodes, collar_margin):
        if len(cluster) >= 2:
            rings.extend(_aabb_collar_rings(cluster, collar_margin))
        else:
            rings.extend(_isolation_collar_rings(
                cluster, collar_margin, prefer_hull=True))
    return rings


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
        if _point_seg_dist(px, py, x0, y0, x1, y1) < tol:
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
    segs = list(_iter_line_segs(weed_path))
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
                hit = _nearest_on_rings(p.x(), p.y(), collar_rings)
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
    m = _frontier_run_metrics(pts, waste_dir=waste_dir)
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
    rings = _enclosure_collar_rings(keep_path, collar_margin)
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
    min_depth = _bay_min_depth(standoff)
    for cluster, _container in _enclosure_groups(nodes, collar_margin):
        bodies = [b for b in cluster if b is not None and not b.isEmpty()]
        for body in bodies:
            tips = _deep_keep_peninsula_tips(body, delicate)
            for left, right, deep, run in _hull_bay_mouths(
                    body, min_depth, min_width):
                mouth_w = math.hypot(
                    right.x() - left.x(), right.y() - left.y())
                depth = _point_seg_dist(
                    deep.x(), deep.y(), left.x(), left.y(),
                    right.x(), right.y())
                waste_dir = _bay_waste_dir(left, right, deep)
                if not _bay_should_seal(
                        left, right, deep, run, depth=depth,
                        mouth_w=mouth_w, ratio=ratio):
                    continue
                if _mouth_between_keep_tips(left, right, tips, tol=2.0):
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
                if _bodies_touch(a, b):
                    continue
                if (_is_stacked_satellite(a, b)
                        or _is_stacked_satellite(b, a)):
                    continue
                if ((_is_compact_island(a, bodies)
                        or _is_compact_island(b, bodies))):
                    speck = a if _is_compact_island(a, bodies) else b
                    tied_tgts = [x for x in bodies if x is not speck]
                    # One tie is not enough — waste can still fork around.
                    if _compact_tie_count(
                            weed_path, speck, tied_tgts) >= _MIN_COMPACT_TIES:
                        continue
                others = [bodies[k] for k in range(n) if k != i and k != j]
                if _gap_blocked(a, b, others):
                    # Majors may still need a residual trap when only
                    # well-tied ticks occupy the AABB (seal pass handles it).
                    if not (_gap_blocked_only_by_tied_compacts(
                            a, b, others, bodies, weed_path)
                            and not _is_compact_island(a, bodies)
                            and not _is_compact_island(b, bodies)):
                        continue
                if _is_corridor_pair(a, b):
                    core = _channel_core(a, b)
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
                    run = _facing_frontier_pts(a, b)
                    if not _peninsula_should_detach(
                            core.length, core.width, run, ratio=ratio):
                        continue
                    add_trap(_make_residual_trap(
                        'channel', mx, my, core.length, core.width, run))
                    continue
                mouths = _gap_mouths(a, b)
                if not mouths:
                    continue
                width = _cluster_gap_width(a, b, mouths)
                depth = _cluster_gap_depth(a, b, mouths)
                run = _facing_frontier_pts(a, b)
                if not _peninsula_should_detach(
                        depth, width, run, ratio=ratio):
                    continue
                if _is_hanging(a, b):
                    mouth = _hanging_pocket_mouth(a, b, bodies, mouths)
                else:
                    mouth = _open_side_bay_mouth(mouths)
                if mouth is None:
                    continue
                pa, pb, _dist = mouth
                if _mouth_covered_by_weeds(pa, pb, segs, max(wall, 1.5)):
                    continue
                mx = 0.5 * (pa.x() + pb.x())
                my = 0.5 * (pa.y() + pb.y())
                if len(mouths) >= 2:
                    other = mouths[0] if mouth is mouths[-1] else mouths[-1]
                    ix = _gap_mouth_mid_x(other) - mx
                    iy = _gap_mouth_mid_y(other) - my
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
