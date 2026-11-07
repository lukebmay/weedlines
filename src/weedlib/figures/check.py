# -*- coding: utf-8 -*-
"""Classify figures, collapse twins, and name dangling ends and subject area."""
from __future__ import division

from .. import keep, progress
from ..paths import join_painter_paths, split_painter_path
from ..qt import QPainterPath, QPointF, QRectF, Qt
from ..svg_paths import svg_d_to_qpainterpath

from .types import Defect, Figure, FigureCheck, SubjectWeed
from .borders import _border_pieces, _borders_cross, _pieces_outline, _same_point
from .interior import _area_of, _has_area, _outside_fill
from .overlap import _overlap_defects

_CORRECTION_PREFIX = "weedlines-correction"


def classify_figures(records):
    """One figure per path record, and every figure-check defect.

    ``d`` is parsed by the SVG path helper. A closed flag does not add a
    closepath. Twins use the keep-fill near-duplicate collapse. An id
    starting with ``weedlines-correction`` is not a figure.

    Dangling ends, separate-figure overlaps, and self-overlaps are all
    reported. Overlap uses the painted interior. A self-overlap uses the
    real border, not the segment an open subpath is painted as if closed by.
    """
    figures = []
    defects = []
    kept_closed = []
    kept_parts = []
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
        kept_parts.append(kept)
    for subpaths in kept_parts:
        # Looked up on the package each call. A test replaces it.
        from . import _self_overlap_defects
        defects.extend(_self_overlap_defects(subpaths))
    painted = [_painted_parts(subpaths) for subpaths in kept_parts]
    count = len(painted)
    for index in range(count):
        for other in range(index + 1, count):
            defects.extend(_overlap_defects(
                painted[index], painted[other],
                kept_parts[index], kept_parts[other],
            ))
    return FigureCheck(figures=figures, defects=defects)


def subject_weed_regions(figures, swap):
    """Subject, weed area, and design bounds for classified figures.

    ``figures`` is the list from ``classify_figures``. A fill is paint
    when it is a color or ``other``; ``none`` is not. Painted interiors
    start as subject. When no figure has paint, every interior does.
    Weed area is the design bounds minus that subject. ``swap``
    exchanges the two inside those bounds and does not move the bounds.
    """
    figures = list(figures or [])
    any_paint = any(_is_paint(figure.fill) for figure in figures)
    subject = _union_interiors(figures, any_paint)
    bounds = _design_bounds(figures)
    weed_area = _bounds_minus(bounds, subject)
    if swap:
        subject, weed_area = weed_area, subject
    return SubjectWeed(subject=subject, weed_area=weed_area, bounds=bounds)


def _is_paint(fill):
    # Job fill is none, a #rrggbb color, or other (a gradient).
    if not isinstance(fill, str):
        return False
    token = " ".join(fill.split()).lower()
    return token not in ("", "none", "transparent")


def _union_interiors(figures, require_paint):
    acc = QPainterPath()
    for figure in figures:
        if require_paint and not _is_paint(figure.fill):
            continue
        # Painted interior, including an open subpath. Not solver keep.
        interior = _painted_parts(split_painter_path(figure.path))
        if not _has_area(interior):
            continue
        acc = interior if acc.isEmpty() else acc.united(interior)
    acc.setFillRule(Qt.OddEvenFill)
    return acc


def _design_bounds(figures):
    box = QRectF()
    for figure in figures:
        rect = figure.path.boundingRect()
        # A null seed is the origin, not a figure. Do not union with it.
        box = rect if box.isNull() else box.united(rect)
    return box.normalized()


def _bounds_minus(bounds, subject):
    if not bounds.isValid():
        return QPainterPath()
    rect = QPainterPath()
    rect.addRect(bounds)
    rect.setFillRule(Qt.OddEvenFill)
    if not _has_area(subject):
        return rect
    weed_area = rect.subtracted(subject)
    weed_area.setFillRule(Qt.OddEvenFill)
    return weed_area


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


def _focus_outline(path):
    """One subpath as plain points, or None. Not a cut."""
    if path is None:
        return None
    return _pieces_outline(_border_pieces(path))


def _without_twins(subpaths, kept_closed):
    kept = []
    for subpath in subpaths:
        # The twin walk repeats the whole list. One check per subpath.
        progress.check(outline=_focus_outline(subpath))
        if keep._subpath_is_closed(subpath):
            if not _is_new_outline(subpath, kept_closed):
                continue
            kept_closed.append(subpath)
        kept.append(subpath)
    return kept


def _is_new_outline(subpath, kept_closed):
    """False when the keep-fill twin collapse drops *subpath*."""
    unique = keep._dedupe_closed_subpaths(kept_closed + [subpath])
    return any(item is subpath for item in unique)


def _figure_path(path, subpaths, kept):
    if len(kept) == len(subpaths):
        return QPainterPath(path)
    return join_painter_paths(kept)


def _dangling_defects(subpaths):
    endpoints = []
    for subpath in subpaths:
        if keep._subpath_is_closed(subpath):
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


def _painted_parts(subpaths):
    """Union of painted subpaths, minus a counter that does not cross.

    Global odd-even would drop the lens where two subpaths cross. That lens
    is not a counter. A counter is contained, and its real border does not
    cross the border around it.
    """
    fills = [_fill_subpath(subpath) for subpath in subpaths]
    count = len(fills)
    if count == 0:
        return QPainterPath()
    if count == 1:
        return fills[0]
    areas = [_area_of(fill) for fill in fills]
    parent = [None] * count
    for index in range(count):
        best = None
        best_area = None
        for other in range(count):
            if index == other or areas[other] <= areas[index]:
                continue
            if _outside_fill(fills[index], fills[other]):
                continue
            if _borders_cross(subpaths[index], subpaths[other]):
                continue
            if best is None or areas[other] < best_area:
                best = other
                best_area = areas[other]
        parent[index] = best
    acc = QPainterPath()
    for index, fill in enumerate(fills):
        if _nest_depth(parent, index) % 2 != 0:
            continue
        solid = QPainterPath(fill)
        for child, owner in enumerate(parent):
            if owner == index:
                solid = solid.subtracted(fills[child])
        if not _has_area(solid):
            continue
        acc = solid if acc.isEmpty() else acc.united(solid)
    return acc


def _fill_subpath(subpath):
    """Painted interior of one subpath. The close is fill-only."""
    filled = QPainterPath(subpath)
    if not keep._subpath_is_closed(subpath):
        filled.closeSubpath()
    filled.setFillRule(Qt.OddEvenFill)
    return filled


def _nest_depth(parent, index):
    seen = 0
    node = parent[index]
    while node is not None and seen <= len(parent):
        seen += 1
        node = parent[node]
    return seen
