# -*- coding: utf-8 -*-
"""Keep fill, twins, and samples."""
from __future__ import division

import math
import os

import pytest

from weedlib.qt import QPainterPath, QPointF, QRectF
from weedlib import solvers as weeds_mod
from weedlib.solvers import (
    island_hop_weeds,
    weed_path_stats,
    closed_fill_union,
    even_odd_keep_fill,
    list_closed_subpaths,
)
from weedlib.keep import _polyline_points
import weedlib.solvers.geom as mod_geom

pytest.importorskip('PyQt5', reason='Qt binding required for weedlib geometry')

from tests.weed_shapes import (
    requires_clipper,
    _rect_path,
    _circle_path,
    _inkscape_fill_stroke_twin,
    _letter_o,
    _framed_hi,
)

def test_solid_keep_leaves_only_is_gone():
    assert not hasattr(weeds_mod, '_solid_keep_from_nodes')


def test_text_star_dispatch_helpers_are_gone():
    assert not hasattr(weeds_mod, '_height_classes')
    assert not hasattr(weeds_mod, '_is_spiky_island')
    assert not hasattr(weeds_mod, '_major_keep_bodies')


def test_even_odd_letter_o_keep_is_ring():
    keep = _letter_o()
    fill = even_odd_keep_fill(keep)
    assert fill.contains(QPointF(50, 25))  # ring
    assert not fill.contains(QPointF(50, 50))  # hole is waste
    assert not fill.contains(QPointF(4, 4))  # exterior
    # Alias still names the same design keep fill (not a solid disk).
    assert closed_fill_union is even_odd_keep_fill
    assert not even_odd_keep_fill(keep).contains(QPointF(50, 50))


def test_overlapping_design_stays_keep():
    """Two design islands that overlap: intersection is keep, not waste."""
    keep = QPainterPath()
    keep.addPath(_rect_path(0, 0, 20, 20))
    keep.addPath(_rect_path(10, 10, 20, 20))
    fill = even_odd_keep_fill(keep)
    assert fill.contains(QPointF(5, 5))
    assert fill.contains(QPointF(25, 25))
    # Pure even-odd would XOR the overlap into waste.
    assert fill.contains(QPointF(15, 15)), (
        "design+design overlap must stay keep (not weedable)")


def test_polyline_samples_curves_not_control_points():
    keep = _circle_path(50, 50, 40)
    pts = _polyline_points(keep)
    assert len(pts) >= 8
    for p in pts:
        r = math.hypot(p.x() - 50.0, p.y() - 50.0)
        assert abs(r - 40.0) < 1.5, "Bezier control treated as vertex (r=%s)" % r


def test_outline_samples_stay_on_path():
    """BBox corners of a circle are not outline samples (cuts to nowhere)."""
    keep = _circle_path(50, 50, 30)
    br = keep.boundingRect()
    samples = mod_geom._outline_samples(keep, max_pts=128)
    assert samples, "expected outline samples"
    corner = QPointF(br.left(), br.top())
    # True outline is 30*sqrt(2)-30 ≈ 12.4 mm inside that corner.
    for p in samples:
        d = math.hypot(p.x() - corner.x(), p.y() - corner.y())
        assert d > 2.0, "bbox corner leaked into outline samples: %s" % (
            (p.x(), p.y()),)


def test_keep_fill_svg_d_uses_evenodd_holes():
    """Preview keep-fill polygons need evenodd (same-winding outer+hole)."""
    from weedlib.svg_paths import keep_fill_to_svg_d
    keep = QPainterPath()
    keep.addRect(QRectF(0.0, 0.0, 200.0, 100.0))
    keep.addRect(QRectF(8.0, 8.0, 184.0, 84.0))
    fill = even_odd_keep_fill(keep)
    assert not fill.contains(QPointF(100.0, 50.0))
    d = keep_fill_to_svg_d(fill)
    assert d.count('Z') >= 2
    assert 'M ' in d


@requires_clipper
def test_fill_stroke_twins_deduped_for_framed_keep():
    """Fill+stroke duplicate outers must not solid-fill the frame counter."""
    keep = _inkscape_fill_stroke_twin(_framed_hi())
    # Without dedupe there would be 8 closed outlines; keep one of each.
    assert len(list_closed_subpaths(keep)) == 4
    fill = even_odd_keep_fill(keep)
    assert fill.contains(QPointF(3, 3))  # frame band
    assert not fill.contains(QPointF(60, 50))  # counter waste
    assert fill.contains(QPointF(40, 50))  # H keep


@requires_clipper
def test_fill_stroke_twins_island_hop_no_outer_peel():
    """Duplicate framed keep still skips outer peel and emits interior seals."""
    import io
    import logging

    keep = _inkscape_fill_stroke_twin(_framed_hi())
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(logging.Formatter('%(message)s'))
    log = logging.getLogger('weedlib')
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)
    prev = os.environ.get('WEEDLINES_LOG')
    os.environ['WEEDLINES_LOG'] = '1'
    try:
        import weedlib.debug as d
        d._configured = False
        weed = island_hop_weeds(keep, padding=[12, 12, 12, 12], collar=4.0)
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
    assert weed_path_stats(weed)['segments'] > 0
