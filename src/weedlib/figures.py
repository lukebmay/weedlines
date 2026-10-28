# -*- coding: utf-8 -*-
"""Classify path records into figures and dangling-end defects."""
from __future__ import division

from dataclasses import dataclass

from .paths import join_painter_paths, split_painter_path
from .qt import QPainterPath, QPointF
from .solvers import _dedupe_closed_subpaths, _subpath_is_closed
from .svg_paths import svg_d_to_qpainterpath

# Same start/end coincidence _subpath_is_closed uses.
_SAME_POINT_TOL = 1e-4
_CORRECTION_PREFIX = "weedlines-correction"


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


def classify_figures(records):
    """One figure per path record, plus a dangling end at each free endpoint.

    ``d`` is parsed by the SVG path helper. A closed flag does not add a
    closepath. Twins use the keep-fill near-duplicate collapse. An id
    starting with ``weedlines-correction`` is not a figure.
    """
    figures = []
    defects = []
    kept_closed = []
    for record in records or []:
        element_id = _element_id(record)
        if element_id.startswith(_CORRECTION_PREFIX):
            continue
        # Path data decides. Do not closeSubpath from the record's closed flags.
        path = _path_from_record(record)
        subpaths = split_painter_path(path)
        kept = _without_twins(subpaths, kept_closed)
        if not kept:
            continue
        figures.append(Figure(
            id=element_id,
            path=_figure_path(path, subpaths, kept),
            fill=_lookup(record, "fill"),
        ))
        defects.extend(_dangling_defects(kept))
    return FigureCheck(figures=figures, defects=defects)


def _element_id(record):
    value = _lookup(record, "id", "")
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _path_from_record(record):
    path = _lookup(record, "path")
    if isinstance(path, QPainterPath):
        return QPainterPath(path)
    d = _lookup(record, "d")
    if isinstance(d, str):
        return svg_d_to_qpainterpath(d)
    raise ValueError("figure record has no path data")


def _lookup(record, name, default=None):
    if isinstance(record, dict):
        return record.get(name, default)
    return getattr(record, name, default)


def _without_twins(subpaths, kept_closed):
    kept = []
    for subpath in subpaths:
        if _subpath_is_closed(subpath):
            if not _is_new_outline(subpath, kept_closed):
                continue
            kept_closed.append(subpath)
        kept.append(subpath)
    return kept


def _is_new_outline(subpath, kept_closed):
    """False when the keep-fill twin collapse drops *subpath*."""
    unique = _dedupe_closed_subpaths(kept_closed + [subpath])
    return any(item is subpath for item in unique)


def _figure_path(path, subpaths, kept):
    if len(kept) == len(subpaths):
        return QPainterPath(path)
    return join_painter_paths(kept)


def _dangling_defects(subpaths):
    endpoints = []
    for subpath in subpaths:
        if _subpath_is_closed(subpath):
            continue
        endpoints.extend(_endpoints(subpath))
    defects = []
    for index, point in enumerate(endpoints):
        if _meets_other(point, endpoints, index):
            continue
        defects.append(Defect(kind="dangling", target=point))
    return defects


def _endpoints(subpath):
    count = subpath.elementCount()
    if count <= 0:
        return []
    start = _point_at(subpath, 0)
    if count == 1:
        return [start]
    return [start, _point_at(subpath, count - 1)]


def _point_at(subpath, index):
    element = subpath.elementAt(index)
    return QPointF(element.x, element.y)


def _meets_other(point, endpoints, index):
    for other_index, other in enumerate(endpoints):
        if other_index == index:
            continue
        if _same_point(point, other):
            return True
    return False


def _same_point(a, b):
    return (
        abs(a.x() - b.x()) <= _SAME_POINT_TOL
        and abs(a.y() - b.y()) <= _SAME_POINT_TOL
    )
