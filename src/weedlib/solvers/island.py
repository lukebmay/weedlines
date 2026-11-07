# -*- coding: utf-8 -*-
"""Island-hop's pass order, with the phase blocks and hole splits."""
from __future__ import division

import math

from .. import debug as _wdbg
from ..qt import QPainterPath, QRectF
from ..keep import (
    even_odd_keep_fill,
    list_closed_subpaths,
    _nest_closed_paths,
    _normalize_padding,
    _padded_rect,
    _path_centroid,
)

from .rules import (
    DEFAULT_CHANNEL_STANDOFF,
    DEFAULT_CLEARANCE,
    DEFAULT_COLLAR,
    DEFAULT_DELICATE_ANGLE_DEG,
    DEFAULT_GRID_SPACING,
    DEFAULT_MAX_CHUNK,
    DEFAULT_MAX_SPOKES,
    DEFAULT_MIN_CUT,
    DEFAULT_PENINSULA_RATIO,
)
from . import agglomerate as _sol_agglomerate
from . import bay as _sol_bay
from . import channels as _sol_channels
from . import clip as _sol_clip
from . import cluster as _sol_cluster
from . import cluster_bays as _sol_cluster_bays
from . import corridors as _sol_corridors
from . import emit as _sol_emit
from . import frame_peninsulas as _sol_frame_peninsulas
from . import geom as _sol_geom
from . import peel as _sol_peel
from . import pockets as _sol_pockets
from . import rules as _sol_rules
from . import stats as _sol_stats
from . import ties as _sol_ties


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
    rules = _sol_rules._cut_rules(body_clearance, alpha_min, frame_clearance)
    _ = spacing, bridge_width

    work = _padded_rect(keep_path.boundingRect(), padding)
    out = QPainterPath()

    closed = list_closed_subpaths(keep_path)
    if not closed:
        return _sol_clip._clip_path_to_rect(out, work)

    nodes = _nest_closed_paths(closed)
    keep_fill = even_odd_keep_fill(keep_path)
    if keep_fill.isEmpty():
        keep_fill = QPainterPath(keep_path)

    keep_bodies = [n['path'] for n in nodes if n['depth'] % 2 == 0]
    holes = [n for n in nodes if n['depth'] % 2 == 1]
    if not keep_bodies:
        return _sol_clip._clip_path_to_rect(out, work)

    frame_ring = _sol_geom._rect_as_ring(work)
    standoff = max(clearance, DEFAULT_CHANNEL_STANDOFF)
    groups = _sol_cluster._enclosure_groups(nodes, collar_margin)
    _wdbg.log(
        'island_hop.start', bodies=len(keep_bodies), holes=len(holes),
        clusters=len(groups), collar=collar_margin,
        body_clearance=rules.body_clearance, alpha_min=rules.alpha_min,
        frame_clearance=rules.frame_clearance, work=_wdbg.bbox_fmt(work))

    # One outer peel + one free working set (chords isolate; no per-box rails).
    # Design frames (hollow keep that already bounds interior) are not peeled
    # again — their hole coast is the wall for contained clusters (D013).
    design_frame_ids = _sol_cluster._design_frame_path_ids(nodes)
    free_bodies = []
    contained_groups = []
    for cluster, container in groups:
        if container is not None and not container.isEmpty():
            contained_groups.append((cluster, container))
            continue
        for body in cluster:
            if body is not None and not body.isEmpty():
                free_bodies.append(body)
    peel_bodies = [
        b for b in free_bodies if id(b) not in design_frame_ids
    ]
    shared_frame = QPainterPath()
    shared_rings = []
    if peel_bodies:
        shared_frame, shared_rings = _sol_peel._peel_frame_for_cluster(
            peel_bodies, keep_fill, work, None, rules.frame_clearance)
        if not shared_frame.isEmpty():
            # Rails: no-cross / redundant only — body-clearance is for seals;
            # standoff is frame_clearance (may be < body_clearance).
            _sol_emit._add_path_segs(out, shared_frame, min_cut)
    elif free_bodies and design_frame_ids:
        _wdbg.log(
            'peel_frame.skip', reason='design_frame_outer',
            n_frames=len(design_frame_ids), free=len(free_bodies))
    work_groups = []
    # Free bodies that are only design frames need no planner pass — their
    # hole coasts already bound contained clusters. Still plan any free
    # (unframed) keep that is not itself a hollow design frame.
    free_plan = [b for b in free_bodies if id(b) not in design_frame_ids]
    if free_plan:
        work_groups.append((free_plan, None))
    elif free_bodies and not contained_groups:
        # Hollow frame alone (no interior keep yet): still visit once with
        # no peel so hole splits can run later from the holes loop.
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
            wall_rings = _sol_peel._opening_wall_rings(used_rings, container)
            spoke_bodies = False
            body_tips = []
            for body in cluster:
                tips = _sol_bay._deep_keep_peninsula_tips(body, delicate_angle)
                body_tips.append(tips)
            outer_bodies = _outside_in_bodies(cluster, work, container)
            tip_map = dict((id(b), t) for b, t in zip(cluster, body_tips))
            with _wdbg.phase('body_pockets'):
                for body in outer_bodies:
                    out.addPath(_sol_pockets._body_pocket_seals(
                        body, keep_fill, work, standoff, min_cut,
                        container=container,
                        keep_tips=tip_map.get(id(body)) or (),
                        peninsula_ratio=peninsula_ratio, against=out,
                        rules=rules, peel_frame=frame_path))
            if len(cluster) >= 2:
                with _wdbg.phase('frame_peninsulas'):
                    out.addPath(_sol_frame_peninsulas._seal_frame_peninsulas(
                        cluster, keep_fill, work, standoff, min_cut, container,
                        against=out, peninsula_ratio=peninsula_ratio,
                        collar_rings=wall_rings, rules=rules,
                        peel_frame=frame_path))
                with _wdbg.phase('compact_ties'):
                    out.addPath(_sol_ties._seal_compact_islands(
                        cluster, keep_fill, work, standoff, min_cut, container,
                        against=out, rules=rules, peel_frame=frame_path))
                with _wdbg.phase('agglomerate'):
                    fuse_path, _groups, _sat_ids = _sol_agglomerate._agglomerate_islands(
                        cluster, keep_fill, work, standoff, min_cut, container,
                        max_chunk=max_chunk, rules=rules,
                        peel_frame=frame_path, against=out)
                    out.addPath(fuse_path)
            for body in cluster:
                tips = tip_map.get(id(body)) or ()
                if (tips and not _sol_bay._has_independent_waste_bays(
                        body, tips, standoff, min_cut,
                        peninsula_ratio=peninsula_ratio)):
                    out.addPath(_sol_channels._tip_spokes(
                        tips, used_rings, frame_ring, keep_fill, work,
                        clearance=standoff, min_cut=min_cut,
                        max_spokes=max_spokes, against=out))
                    spoke_bodies = True
            # Residual multi-body water re-analysis (D007).
            for _pass in range(3):
                before = _sol_stats.weed_path_stats(out)['segments']
                with _wdbg.phase('residual[%d]' % _pass, segs_before=before):
                    for body in outer_bodies:
                        out.addPath(_sol_pockets._body_pocket_seals(
                            body, keep_fill, work, standoff, min_cut,
                            container=container,
                            keep_tips=tip_map.get(id(body)) or (),
                            peninsula_ratio=peninsula_ratio, against=out,
                            rules=rules, peel_frame=frame_path))
                    if len(cluster) >= 2:
                        out.addPath(_sol_cluster_bays._cluster_bay_seals(
                            cluster, keep_fill, work, standoff, min_cut,
                            container, against=out,
                            peninsula_ratio=peninsula_ratio,
                            rules=rules, peel_frame=frame_path,
                            collar_rings=wall_rings))
                        out.addPath(_sol_ties._seal_compact_islands(
                            cluster, keep_fill, work, standoff, min_cut,
                            container, against=out, rules=rules,
                            peel_frame=frame_path))
                        out.addPath(_sol_corridors._seal_divergent_corridors(
                            cluster, keep_fill, work, standoff, min_cut,
                            container, against=out, max_chunk=max_chunk,
                            rules=rules, peel_frame=frame_path))
                        out.addPath(_sol_cluster_bays._leftover_hanging_gutters(
                            cluster, keep_fill, work, standoff, min_cut,
                            container, against=out, rules=rules,
                            peel_frame=frame_path))
                        if wall_rings and not _sol_channels._has_keep_to_collar_channel(
                                out, cluster, wall_rings, standoff):
                            outline = _sol_cluster._cluster_keep_outline(cluster)
                            if outline is not None:
                                ch = _sol_channels._shortest_outer_channel(
                                    outline, wall_rings, keep_fill, work,
                                    min_cut, clearance=standoff,
                                    container=container)
                                if ch is not None and _sol_emit._seg_forced_ok(
                                        ch, keep_path, out, rules,
                                        peel_frame=frame_path):
                                    _sol_emit._add_seg(out, ch, min_cut)
                        out.addPath(_sol_frame_peninsulas._seal_frame_peninsulas(
                            cluster, keep_fill, work, standoff, min_cut,
                            container, against=out,
                            peninsula_ratio=peninsula_ratio,
                            collar_rings=wall_rings, rules=rules,
                            peel_frame=frame_path))
                if _sol_stats.weed_path_stats(out)['segments'] <= before:
                    break
            if (len(cluster) < 2 and wall_rings
                    and not _sol_channels._has_keep_to_collar_channel(
                        out, cluster, wall_rings, standoff)):
                ch = _sol_channels._shortest_outer_channel(
                    cluster[0], wall_rings, keep_fill, work, min_cut,
                    clearance=standoff, container=container)
                if ch is not None and _sol_emit._seg_forced_ok(
                        ch, keep_path, out, rules, peel_frame=frame_path):
                    _sol_emit._add_seg(out, ch, min_cut)

    for node in holes:
        if node['children']:
            continue
        hole = QPainterPath(node['path'])
        if hole.isEmpty():
            continue
        splits = _hole_internal_splits(
            hole, keep_fill, max_chunk, min_cut)
        out.addPath(splits)
        # Accepted splits. A later pass may drop or shorten them.
        _sol_emit._publish_path_segments(splits)

    # Drop hugs / slivers / needless optionals, then require connected ends.
    # Hugs vs keep fill (land outline), not raw design subpaths.
    out = _sol_emit._drop_parallel_hugs(out, keep_fill, min_cut)
    out = _sol_emit._drop_slivers_and_needless(out, keep_path)
    anchor_tol = max(1.5, standoff + 0.25)
    out = _sol_emit._require_connected_ends(
        out, keep_path, tol=anchor_tol, work=work)
    out = _sol_clip._clip_path_to_rect(out, work)
    if _wdbg.enabled():
        _sol_stats._audit_firm_rules(out, keep_path, rules)
        stats = _sol_stats.weed_path_stats(out)
        _wdbg.log('island_hop.done', segs=stats['segments'], length=stats['length'])
    return out


def _outside_in_bodies(cluster, work, container=None):
    """Bodies closer to the outer waste wall first."""
    bodies = [b for b in cluster if b is not None and not b.isEmpty()]
    if len(bodies) <= 1:
        return bodies
    wall = container if container is not None else None

    def key(body):
        c = _path_centroid(body)
        if wall is not None and not wall.isEmpty():
            rings = _sol_geom._path_to_rings(wall)
            hit = _sol_geom._nearest_on_rings(c.x(), c.y(), rings) if rings else None
            if hit is not None:
                return (hit[2], c.x(), c.y())
        if work is not None and not work.isNull():
            d = min(
                c.x() - work.left(), work.right() - c.x(),
                c.y() - work.top(), work.bottom() - c.y())
            return (d, c.x(), c.y())
        return (0.0, c.x(), c.y())

    return sorted(bodies, key=key)


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
            segs = _sol_clip._clip_line_to_region(
                x, br.top(), x, br.bottom(), hole_path, invert_keep=False,
                samples=64, min_len=min_cut)
            for s in segs:
                inner = _sol_clip._clip_line_to_region(
                    s[0], s[1], s[2], s[3], keep_fill, invert_keep=True,
                    samples=48, min_len=min_cut)
                _sol_geom._add_line_segs(out, inner)
    else:
        n = max(int(math.ceil(br.height() / max_chunk)) - 1, 1)
        n = min(n, 8)
        for i in range(1, n + 1):
            y = br.top() + br.height() * i / float(n + 1)
            segs = _sol_clip._clip_line_to_region(
                br.left(), y, br.right(), y, hole_path, invert_keep=False,
                samples=64, min_len=min_cut)
            for s in segs:
                inner = _sol_clip._clip_line_to_region(
                    s[0], s[1], s[2], s[3], keep_fill, invert_keep=True,
                    samples=48, min_len=min_cut)
                _sol_geom._add_line_segs(out, inner)
    return out
