# -*- coding: utf-8 -*-
"""Figure, defect, figure-check, and subject-weed records."""
from __future__ import division

from dataclasses import dataclass

from ..qt import QPainterPath, QPointF, QRectF


@dataclass
class Figure:
    """One path element after twin outlines are collapsed."""

    id: str
    path: QPainterPath
    fill: object


@dataclass
class Defect:
    """One figure-check defect. ``target`` is the arrow point."""

    kind: str
    target: QPointF


@dataclass
class FigureCheck:
    """Figures from the records, and the defects on those figures."""

    figures: list
    defects: list


@dataclass
class SubjectWeed:
    """Subject path, weed-area path, and the design bounds around both."""

    subject: QPainterPath
    weed_area: QPainterPath
    bounds: QRectF
