# -*- coding: utf-8 -*-
"""The peel frame."""
from __future__ import division

import os

import pytest

from weedlib.qt import QPainterPath, QPointF, QRectF
from weedlib.solvers import (
    DEFAULT_CHANNEL_STANDOFF,
    island_hop_weeds,
    sample_points_on_path,
    even_odd_keep_fill,
    list_closed_subpaths,
    padded_work_rect,
)
from weedlib.solvers.cluster import _is_design_frame_node
from weedlib.solvers.peel import (
    _peel_axis,
    _peel_dir_at,
)
from weedlib.keep import _nest_closed_paths
import weedlib.solvers.channels as mod_channels
import weedlib.solvers.clipper as mod_clipper
import weedlib.solvers.geom as mod_geom

pytest.importorskip('PyQt5', reason='Qt binding required for weedlib geometry')

from tests.weed_shapes import _rect_path

def test_peel_axis_side_by_side_rects():
    """Two side-by-side rects: n̂ across the gap, ĉ along the alley."""
    a = _rect_path(0, 0, 20, 50)
    b = _rect_path(28, 0, 20, 50)
    c_hat, n_hat = _peel_axis(a, b)
    # Across ≈ ±X; along ≈ ±Y.
    assert abs(n_hat[0]) > 0.9 and abs(n_hat[1]) < 0.1
    assert abs(c_hat[1]) > 0.9 and abs(c_hat[0]) < 0.1
    assert abs(c_hat[0] * n_hat[0] + c_hat[1] * n_hat[1]) < 1e-9
    # Peel dir along corridor toward far end from a bottom mouth.
    mouth = QPointF(24.0, 50.0)
    p = QPointF(24.0, 25.0)
    d = _peel_dir_at(p, {'kind': 'corridor', 'c_hat': c_hat, 'mouth': mouth})
    assert d is not None
    # From bottom mouth toward mid → opposite +ĉ if ĉ points +Y.
    assert d[1] * c_hat[1] < 0.0 or abs(d[1]) > 0.9


def test_peel_frame_opens_at_full_clearance():
    """Keep→peel-frame radial still emits when clearance gap exceeds 12."""
    keep = _rect_path(0.0, 0.0, 80.0, 50.0)
    pad = [20.0, 20.0, 20.0, 20.0]
    weed = island_hop_weeds(
        keep, padding=pad, collar=4.0, frame_clearance=20.0)
    bodies = list_closed_subpaths(keep)
    delta = min(20.0, min(pad) - 2.0)
    rings = mod_clipper._cluster_offset_rings(bodies, delta)
    assert rings
    assert mod_channels._has_keep_to_collar_channel(
        weed, bodies, rings, DEFAULT_CHANNEL_STANDOFF), (
        "full-clearance peel frame missing corridor opening")


def test_peel_rail_stays_continuous_at_channel():
    """Auto peel rail stays continuous; keep→frame radial opens the collar."""
    keep = _rect_path(0.0, 0.0, 80.0, 50.0)
    pad = [20.0, 20.0, 20.0, 20.0]
    weed = island_hop_weeds(
        keep, padding=pad, collar=4.0, frame_clearance=20.0)
    bodies = list_closed_subpaths(keep)
    delta = min(20.0, min(pad) - 2.0)
    rings = mod_clipper._cluster_offset_rings(bodies, delta)
    lands = mod_channels._keep_to_collar_landings(
        weed, bodies, rings, DEFAULT_CHANNEL_STANDOFF)
    assert lands, "missing keep→frame channel landing"
    lx, ly = lands[0]
    rail_through = 0
    for seg in mod_geom._iter_line_segs(weed):
        mx = 0.5 * (seg[0] + seg[2])
        my = 0.5 * (seg[1] + seg[3])
        hit = mod_geom._nearest_on_rings(mx, my, rings)
        if hit is None or hit[2] > 2.0:
            continue
        # Long rail chords: landing can sit far from the midpoint.
        if mod_geom._point_seg_dist(lx, ly, *seg) < 1.5:
            rail_through += 1
    assert rail_through >= 1, (
        "peel rail discontinuous at channel landing (%s hits)" % rail_through)


def test_peel_frame_placed_in_open_water():
    """Open keep: peel rail sits outside keep, inside work, not on work edge."""
    keep = _rect_path(20.0, 20.0, 60.0, 40.0)
    pad = [12.0, 12.0, 12.0, 12.0]
    weed = island_hop_weeds(
        keep, padding=pad, collar=4.0, frame_clearance=20.0)
    work = padded_work_rect(keep, pad)
    keep_fill = even_odd_keep_fill(keep)
    on_work = 0
    outside_keep = 0
    for p in sample_points_on_path(weed, step=1.0):
        if keep_fill.contains(p):
            continue
        outside_keep += 1
        if (abs(p.x() - work.left()) < 0.6 or abs(p.x() - work.right()) < 0.6
                or abs(p.y() - work.top()) < 0.6
                or abs(p.y() - work.bottom()) < 0.6):
            on_work += 1
    assert outside_keep > 0
    assert on_work == 0, "peel frame sat on the padded work edge"


def test_design_frame_skips_outer_peel():
    """Hollow design frame must not get a second outer peel collar."""
    import io
    import logging
    from weedlib.solvers.cluster import _is_design_frame_node
    from weedlib.solvers import list_closed_subpaths
    from weedlib.keep import _nest_closed_paths

    keep = QPainterPath()
    keep.addRect(QRectF(0, 0, 200, 120))
    keep.addRect(QRectF(10, 10, 180, 100))
    keep.addRect(QRectF(40, 40, 30, 30))
    nodes = _nest_closed_paths(list_closed_subpaths(keep))
    roots = [n for n in nodes if n['depth'] == 0]
    assert roots and _is_design_frame_node(roots[0])

    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(logging.Formatter('%(message)s'))
    log = logging.getLogger('weedlib')
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)
    prev = os.environ.get('WEEDLINES_LOG')
    os.environ['WEEDLINES_LOG'] = '1'
    try:
        # reset debug configured so handler path works
        import weedlib.debug as d
        d._configured = False
        weed = island_hop_weeds(keep, padding=[4, 4, 4, 4], collar=4.0)
    finally:
        log.removeHandler(handler)
        if prev is None:
            os.environ.pop('WEEDLINES_LOG', None)
        else:
            os.environ['WEEDLINES_LOG'] = prev
        d._configured = False
    text = buf.getvalue()
    assert 'design_frame_outer' in text
    assert 'peel_frame.emit' not in text
    assert not weed.isEmpty()
