# -*- coding: utf-8 -*-
"""Surrounds: one smoothed outline around each subject cluster."""
from __future__ import division

from .bridge import _bridge_clears
from .build import build_surrounds
from .smooth import _straighten_colinear
from .union import (
    _chain_gap,
    _gap_overlap,
    _parallel_overlap,
    _ring_sits_inside,
    _straight_runs,
    _straight_side,
)

__all__ = [
    "build_surrounds",
    "_bridge_clears",
    "_chain_gap",
    "_gap_overlap",
    "_parallel_overlap",
    "_ring_sits_inside",
    "_straight_runs",
    "_straight_side",
    "_straighten_colinear",
]
