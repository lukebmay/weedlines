# -*- coding: utf-8 -*-
"""Figure check plus correction arrows for each kind that has a target."""
from __future__ import division

from dataclasses import dataclass

from .arrows import arrow_origin, build_arrow_paths
from .figures import classify_figures, subject_weed_regions

# Label text for a kind that has a target. An empty kind is omitted.
_LABELS = (
    ('dangling', 'Dangling ends'),
    ('overlap', 'Figure overlaps'),
    ('self-overlap', 'Self-overlaps'),
)


@dataclass
class CorrectionLabel:
    """One label at a kind origin, in that kind's arrow color."""

    text: str
    color: str
    point: object


@dataclass
class CorrectionMarks:
    """The check, the design bounds, the arrows, and one label per kind."""

    check: object
    bounds: object
    arrows: dict
    labels: list


def build_correction_marks(records):
    """Classify the records once and build arrows for present kinds.

    Design bounds come from the figures. Swap is not an argument.
    """
    check = classify_figures(records)
    bounds = subject_weed_regions(check.figures, False).bounds
    grouped = {}
    for defect in check.defects:
        grouped.setdefault(defect.kind, []).append(defect.target)
    arrows = {}
    labels = []
    for kind, text in _LABELS:
        targets = grouped.get(kind)
        if not targets:
            continue
        paths = build_arrow_paths(kind, targets, bounds)
        arrows[kind] = paths
        labels.append(CorrectionLabel(
            text=text,
            color=paths[0].color,
            point=arrow_origin(kind, bounds),
        ))
    return CorrectionMarks(
        check=check,
        bounds=bounds,
        arrows=arrows,
        labels=labels,
    )
