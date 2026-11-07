# -*- coding: utf-8 -*-
"""Classify path records into figures and figure-check defects."""
from __future__ import division

from .types import Defect, Figure, FigureCheck, SubjectWeed
from .borders import _border_pieces, _piece_hits, _self_overlap_defects
from .overlap import (
    _linked_mark_groups,
    _marks_share_region,
    _meets_region,
    _one_point_per_region,
    _sample_sets_meet,
)
from .check import _painted_parts, classify_figures, subject_weed_regions

__all__ = [
    "classify_figures",
    "subject_weed_regions",
    "Figure",
    "Defect",
    "FigureCheck",
    "SubjectWeed",
    "_painted_parts",
]
