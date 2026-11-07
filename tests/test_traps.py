# -*- coding: utf-8 -*-
"""Residual waste traps."""
from __future__ import division

import pytest

from weedlib.qt import QPainterPath, QRectF

pytest.importorskip('PyQt5', reason='Qt binding required for weedlib geometry')

from tests.weed_shapes import (
    _quoted_blocks,
    _letter_o,
    _residual_traps_for,
    _wide_stem_pair,
    _star12,
    _side_by_side_rects,
    _shallow_smooth_notch_body,
    _deep_smooth_bay_body,
    _letters_hi,
)

def test_residual_traps_unsealed_deep_bay():
    """Empty weeds leave a detachable pocket on the collar peel."""
    keep = _deep_smooth_bay_body()
    traps = _residual_traps_for(keep, weed=QPainterPath())
    assert traps, "unsealed deep bay must be a residual trap"
    assert any(t.kind == 'pocket' for t in traps)


def test_residual_traps_unsealed_corridor():
    """An open long alley still wraps through the channel core."""
    keep = _side_by_side_rects(40.0, 40.0, gap=4.0)
    traps = _residual_traps_for(keep, weed=QPainterPath())
    assert any(t.kind == 'channel' for t in traps), traps


def test_residual_traps_unsealed_cluster_bay():
    """A wide non-corridor gutter still wraps under if no T4 mouth seal."""
    keep = _wide_stem_pair()
    traps = _residual_traps_for(keep, weed=QPainterPath())
    assert any(t.kind == 'cluster' for t in traps), traps


def test_residual_traps_shallow_notch_not_a_trap():
    """Shallow+smooth stays below the detach gate even with no weeds."""
    keep = _shallow_smooth_notch_body()
    traps = _residual_traps_for(keep, weed=QPainterPath())
    assert not traps, traps


def test_residual_traps_letter_o_zero():
    """O hole is keep-enclosed; outer waste is a simple collar gutter."""
    assert _residual_traps_for(_letter_o()) == []


def test_residual_traps_star12_zero():
    """Star valleys are keep-tip valleys, not residual traps."""
    assert _residual_traps_for(_star12(), padding=[12.0, 12.0, 12.0, 12.0]) == []


def test_residual_traps_hi_zero():
    """HI counters and the channel core are sealed after auto weeds."""
    assert _residual_traps_for(_letters_hi()) == []


def test_residual_traps_quoted_blocks_zero():
    """Quoted geometric blocks have no leftover detachable wrap."""
    assert _residual_traps_for(_quoted_blocks()) == []


def test_quoted_in_frame_no_residual_traps():
    """Quoted geometric blocks inside a hollow keep frame peel cleanly."""
    p = QPainterPath()
    p.addRect(QRectF(0, 0, 200, 90))
    p.addRect(QRectF(8, 8, 184, 74))
    p.addPath(_quoted_blocks())
    assert _residual_traps_for(p, padding=[12.0, 12.0, 12.0, 12.0]) == []
