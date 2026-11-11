# -*- coding: utf-8 -*-
"""Proposals for defects the figure check already reported."""
from __future__ import division

from dataclasses import dataclass

from .figures.borders import _same_point
from .figures.types import Defect
from .keep import _subpath_is_closed
from .paths import join_painter_paths, split_painter_path
from .qt import QPainterPath, QPointF


@dataclass
class Proposal:
    """One defect and its replacement path, or none when it is kept."""

    defect: Defect
    path: object


def propose(check):
    """Proposals for *check*, in that check's defect order.

    *check* is the figure check the caller already ran. A dangling
    end is joined by a line between the two open ends of its subpath.
    Each self-overlap stays, with no path. The check does not separate
    a smooth stack, a corner stack, and a larger overlap. A separate
    overlap is omitted.
    """
    proposals = []
    figures = list(check.figures)
    for defect in check.defects:
        if defect.kind == "dangling":
            proposals.append(Proposal(defect, _join_open_ends(figures, defect.target)))
        elif defect.kind == "self-overlap":
            proposals.append(Proposal(defect, None))
    return proposals


def _join_open_ends(figures, target):
    for figure in figures:
        subpaths = split_painter_path(figure.path)
        for index, subpath in enumerate(subpaths):
            if _subpath_is_closed(subpath):
                continue
            if not _has_end(subpath, target):
                continue
            # The check leaves this subpath open. The line is the join.
            closed = QPainterPath(subpath)
            closed.closeSubpath()
            parts = list(subpaths)
            parts[index] = closed
            return join_painter_paths(parts)
    return None


def _has_end(subpath, target):
    count = subpath.elementCount()
    if count < 2:
        return False
    start = subpath.elementAt(0)
    end = subpath.elementAt(count - 1)
    return (
        _same_point(QPointF(start.x, start.y), target)
        or _same_point(QPointF(end.x, end.y), target)
    )
