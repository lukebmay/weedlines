# -*- coding: utf-8 -*-
"""Pyclipper offset and collar rings."""
from __future__ import division

from ..qt import QPainterPath, QPointF, QRectF
from ..keep import (
    list_closed_subpaths,
    _nest_closed_paths,
    _polyline_points,
    _unique_ring,
)

try:
    import pyclipper
except ImportError:
    pyclipper = None

from . import geom as _sol_geom


_CLIPPER_SCALE = 1000.0


def _require_pyclipper():
    if pyclipper is None:
        raise RuntimeError(
            "island-hop collar requires pyclipper; install with: "
            "pip install pyclipper")
    return pyclipper


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
        ccw = _sol_geom._ensure_ccw(ring)
        if len(ccw) < 3:
            continue
        pc.AddPath(
            _ring_to_clipper(ccw, scale),
            clip.JT_ROUND,
            clip.ET_CLOSEDPOLYGON)
    raw = pc.Execute(float(delta) * scale)
    rings_out = [_clipper_to_ring(r, scale) for r in raw if len(r) >= 3]
    return [_sol_geom._simplify_ring(r, 0.45, max_pts=max_pts) for r in rings_out]


def _ellipse_collar_rings(keep_bodies, delta):
    acc = None
    for body in keep_bodies:
        br = body.boundingRect()
        acc = QRectF(br) if acc is None else acc.united(br)
    if acc is None or acc.isEmpty():
        return []
    p = QPainterPath()
    p.addEllipse(acc.adjusted(-delta, -delta, delta, delta))
    return _sol_geom._path_to_rings(p)


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
    ring = _sol_geom._rect_as_ring(acc)
    try:
        offset = _offset_rings([ring], float(delta), max_pts=16)
        if offset:
            return offset
    except RuntimeError:
        raise
    except Exception:
        pass
    pad = float(delta)
    return [_sol_geom._rect_as_ring(acc.adjusted(-pad, -pad, pad, pad))]


def _prefer_hull_collar(keep_bodies, delicate_angle):
    """Simple enclosure (hull) around a cluster; not a per-letter halo."""
    _ = keep_bodies, delicate_angle
    return True


def _isolation_collar_rings(keep_bodies, delta, prefer_hull=False):
    """Offset of outer keep only (never hole contours)."""
    rings = []
    for body in keep_bodies:
        rings.extend(_sol_geom._path_to_rings(body))
    if not rings:
        return []
    source = rings
    max_pts = 32 if prefer_hull else 72
    if prefer_hull:
        pts = [p for ring in rings for p in ring]
        hull = _sol_geom._convex_hull(pts)
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
    hull = _sol_geom._convex_hull(pts)
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


def _cluster_offset_rings(cluster, delta, max_pts=48):
    """Simple hull (or AABB) grow — not a per-nook offset maze."""
    _ = max_pts
    pts = []
    for b in cluster:
        if b is None or b.isEmpty():
            continue
        pts.extend(_unique_ring(_polyline_points(b, max_pts=48)))
    hull = _sol_geom._convex_hull(pts) if pts else []
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


def _enclosure_collar_rings(keep_path, collar_margin):
    """Isolation collar rings per enclosure group (same as enclosure_weeds)."""
    from . import cluster as _sol_cluster
    closed = list_closed_subpaths(keep_path)
    if not closed:
        return []
    nodes = _nest_closed_paths(closed)
    rings = []
    for cluster, _container in _sol_cluster._enclosure_groups(nodes, collar_margin):
        if len(cluster) >= 2:
            rings.extend(_aabb_collar_rings(cluster, collar_margin))
        else:
            rings.extend(_isolation_collar_rings(
                cluster, collar_margin, prefer_hull=True))
    return rings
