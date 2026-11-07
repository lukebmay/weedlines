# -*- coding: utf-8 -*-
"""Segment counts and sample audits."""
from __future__ import division

import math

from .. import debug as _wdbg
from ..qt import QPointF

from . import clip as _sol_clip
from . import geom as _sol_geom


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
    from . import emit as _sol_emit
    segs = list(_sol_geom._iter_line_segs(weed_path))
    crosses = []
    for i, a in enumerate(segs):
        for b in segs[i + 1:]:
            if _sol_geom._seg_proper_cross(a[0], a[1], a[2], a[3],
                                 b[0], b[1], b[2], b[3]):
                crosses.append((a, b))
    _wdbg.log('audit.cross_weed', count=len(crosses))
    for a, b in crosses[:12]:
        _wdbg.log('audit.cross_pair', a=a, b=b)
    clearance_hits = 0
    alpha_hits = 0
    for seg in segs:
        others = [s for s in segs if s != seg]
        if not _sol_emit._seg_body_clearance_ok(
                seg, keep_path, others, clearance=rules.body_clearance):
            clearance_hits += 1
            if clearance_hits <= 8:
                _wdbg.log('audit.body_clearance', seg=seg)
        if not _sol_emit._seg_alpha_ok(seg, keep_path, alpha_min=rules.alpha_min):
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
        if work_rect is not None and not _sol_clip._rect_contains_inclusive(
                work_rect, p.x(), p.y()):
            outside += 1
        if _sol_geom._in_keep_interior(keep_fill, p):
            in_keep += 1
    n = float(len(pts)) if pts else 1.0
    base['samples'] = len(pts)
    base['outside_work'] = outside
    base['in_keep'] = in_keep
    base['outside_work_frac'] = outside / n
    base['in_keep_frac'] = in_keep / n
    return base
