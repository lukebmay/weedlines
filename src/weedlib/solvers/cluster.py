# -*- coding: utf-8 -*-
"""Nearby keep bodies and a design frame."""
from __future__ import division

import math

from .. import debug as _wdbg
from ..qt import QPainterPath
from ..keep import (
    _interior_point,
    _path_area,
    _polyline_points,
    _unique_ring,
)

from . import corridors as _sol_corridors
from . import gaps as _sol_gaps
from . import geom as _sol_geom


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


def _split_interior_groups(bodies, collar):
    """Peel keep that sits inside a surrounding design separately."""
    if len(bodies) < 3:
        return [list(bodies)]
    pts = []
    for b in bodies:
        pts.extend(_unique_ring(_polyline_points(b, max_pts=48)))
    hull = _sol_geom._convex_hull(pts)
    if len(hull) < 3:
        return [list(bodies)]
    margin = max(float(collar), 2.0)
    interior, border = [], []
    for b in bodies:
        probe = _interior_point(b)
        if _sol_geom._point_in_convex(probe, hull, margin=margin):
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


def _is_design_frame_node(node):
    """True if *node* is a hollow keep frame (design already framed).

    Matches D013 / hard-rules: do not invent another outer collar when the
    design already provides a frame. Detected when the keep body has a
    direct hole that either contains nested keep, or is a large hollow
    (hole area > 35% of the outer path area).
    """
    if node is None or node.get('depth', 0) % 2 != 0:
        return False
    body = node.get('path')
    if body is None or body.isEmpty():
        return False
    body_area = abs(_path_area(body))
    if body_area < 1e-6:
        return False
    hole_area = 0.0
    has_inner_keep = False
    for child in node.get('children') or ():
        if child.get('depth') != node['depth'] + 1:
            continue
        hole_area += abs(_path_area(child.get('path')))
        for gc in child.get('children') or ():
            if gc.get('depth', 0) % 2 == 0:
                gp = gc.get('path')
                if gp is not None and not gp.isEmpty():
                    has_inner_keep = True
                    break
        if has_inner_keep:
            break
    if has_inner_keep:
        return True
    return hole_area > 0.35 * body_area


def _design_frame_path_ids(nodes):
    """``id(path)`` set for keep bodies that are design frames."""
    return set(
        id(n['path']) for n in nodes
        if _is_design_frame_node(n) and n.get('path') is not None
    )


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
    ux, uy = _sol_gaps._dominant_gap_axis(path_a, path_b)
    if abs(ux) >= abs(uy):
        return ra.width(), rb.width()
    return ra.height(), rb.height()


def _is_stacked_satellite(speck, host):
    """True if *speck* is a small stacked island on *host* (dot on a stem)."""
    if speck is None or host is None or speck.isEmpty() or host.isEmpty():
        return False
    if _path_area(speck) >= 0.5 * _path_area(host):
        return False
    facing = _sol_corridors._corridor_facing(speck, host)
    if facing is None:
        return False
    overlap, size_a, size_b, gap = facing
    if overlap < _SATELLITE_MIN_OVERLAP * min(size_a, size_b):
        return False
    hr = host.boundingRect()
    host_tall = hr.height() >= hr.width()
    ux, uy = _sol_gaps._dominant_gap_axis(speck, host)
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
    if _sol_corridors._is_corridor_pair(path_a, path_b):
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
        pair = _sol_geom._nearest_pair(body, other)
        if pair is None:
            continue
        if best is None or pair[2] < best[0]:
            best = (pair[2], other)
    return None if best is None else best[1]


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


def _x_sorted_bodies(cluster):
    """Bodies left→right; taller first at the same x (stem before its dot)."""
    bodies = [b for b in cluster if b is not None and not b.isEmpty()]
    bodies.sort(key=lambda b: (
        b.boundingRect().center().x(),
        -b.boundingRect().height(),
        b.boundingRect().center().y()))
    return bodies
