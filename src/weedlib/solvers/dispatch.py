# -*- coding: utf-8 -*-
"""generate_weeds switches mode, and frame stays here."""
from __future__ import division

from ..qt import QPainterPath
from ..keep import (
    _normalize_padding,
    _padded_rect,
)

from .rules import (
    DEFAULT_GRID_SPACING,
    DEFAULT_WEED_MODE,
    WEED_MODES,
)
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
    from .. import progress as _progress
    _progress.report(mode)
    mode = (mode or DEFAULT_WEED_MODE).strip().lower()
    if mode == 'auto':
        mode = 'island-hop'
    mode = mode if mode in WEED_MODES else DEFAULT_WEED_MODE
    padding = _normalize_padding(padding)
    spacing = max(float(spacing or DEFAULT_GRID_SPACING), 1e-6)
    rules = _sol_rules._cut_rules(body_clearance, alpha_min, frame_clearance)

    if mode == 'frame':
        return frame_weeds(keep_path, padding)
    if mode == 'grid':
        return _sol_grid.grid_weeds(
            keep_path, padding, spacing, rules=rules)
    if mode == 'region':
        return _sol_grid.grid_weeds(
            keep_path, padding, spacing, rules=rules)
    return _sol_island.island_hop_weeds(
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
