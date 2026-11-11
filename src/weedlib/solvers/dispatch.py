# -*- coding: utf-8 -*-
"""generate_weeds switches mode, and frame stays here."""
from __future__ import division

from ..qt import QPainterPath
from ..keep import (
    _normalize_padding,
    _padded_rect,
)
from ..piece_border import piece_border

from .rules import (
    DEFAULT_GRID_SPACING,
    DEFAULT_WEED_MODE,
    WEED_MODES,
)
from . import clip as _sol_clip
from . import emit as _sol_emit
from . import grid as _sol_grid
from . import island as _sol_island
from . import rules as _sol_rules


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
                   frame_clearance=None,
                   inner_distance=None,
                   border_width=None,
                   corner_radius=None):
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
    inner_distance, border_width
        Piece-border lengths in user units. Omit either and today's
        path is unchanged. When both are set, mode lines stay inside
        the inner border, then that pair is emitted, inner then outer.
    corner_radius
        Rounds that border when both lengths are set. Omitted stays
        square. The radius is user units the caller already converted.
    """
    if keep_path is None or keep_path.isEmpty():
        return QPainterPath()
    from .. import progress as _progress
    _progress.report(mode)
    mode = (mode or DEFAULT_WEED_MODE).strip().lower()
    if mode == 'auto':
        mode = 'island-hop'
    mode = mode if mode in WEED_MODES else DEFAULT_WEED_MODE
    padding = _normalize_padding(padding)
    spacing = max(float(spacing or DEFAULT_GRID_SPACING), 1e-6)
    rules = _sol_rules._cut_rules(body_clearance, alpha_min, frame_clearance)
    borders = None
    inner_shape = None
    if inner_distance is not None and border_width is not None:
        if corner_radius is None:
            pair = piece_border(keep_path, inner_distance, border_width)
        else:
            pair = piece_border(
                keep_path, inner_distance, border_width, corner_radius)
        if len(pair) == 2:
            borders = pair
            inner_shape = pair[0]
    # None leaves a published segment unchanged.
    _sol_emit._set_border_clip(inner_shape)
    try:
        if mode == 'frame':
            weed = frame_weeds(keep_path, padding)
        elif mode == 'grid':
            weed = _sol_grid.grid_weeds(
                keep_path, padding, spacing, rules=rules)
        elif mode == 'region':
            weed = _sol_grid.grid_weeds(
                keep_path, padding, spacing, rules=rules)
        else:
            weed = _sol_island.island_hop_weeds(
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
    finally:
        _sol_emit._set_border_clip(None)
    if borders is None:
        return weed
    inner, outer = borders
    weed = _sol_clip._clip_path_to_border(weed, inner_shape)
    # The pair is not clipped. Nothing sits between the two rectangles.
    weed.addPath(inner)
    weed.addPath(outer)
    _sol_emit._publish_path_segments(inner)
    _sol_emit._publish_path_segments(outer)
    return weed


def frame_weeds(keep_path, padding=None):
    """Padded rectangle around keep bbox (legacy weedline)."""
    padding = _normalize_padding(padding)
    # Before the rectangle is accepted. Frame has no long search.
    _sol_emit._progress_check()
    rect = _padded_rect(keep_path.boundingRect(), padding)
    out = QPainterPath()
    out.addRect(rect)
    _sol_emit._publish_path_segments(out)
    return out


def region_weeds(keep_path, padding=None, spacing=DEFAULT_GRID_SPACING):
    """Alias of grid (kept for saved jobs)."""
    return _sol_grid.grid_weeds(keep_path, padding, spacing)


def auto_weeds(*args, **kwargs):
    """Deprecated alias of :func:`island_hop_weeds`."""
    return _sol_island.island_hop_weeds(*args, **kwargs)
