# -*- coding: utf-8 -*-
"""Path helpers used by weed solvers (no job/UI deps)."""
from __future__ import division

from .qt import QPointF, QPainterPath


def split_painter_path(path):
    """Split a QPainterPath into subpaths."""
    if not isinstance(path, QPainterPath):
        raise TypeError("path must be a QPainterPath, got: {}".format(path))

    MoveToElement = QPainterPath.MoveToElement
    LineToElement = QPainterPath.LineToElement
    CurveToElement = QPainterPath.CurveToElement
    CurveToDataElement = QPainterPath.CurveToDataElement

    subpaths = []
    params = []
    p = None

    def finish_curve(path_obj, curve_params):
        if len(curve_params) == 2:
            path_obj.quadTo(*curve_params)
        elif len(curve_params) == 3:
            path_obj.cubicTo(*curve_params)
        else:
            raise ValueError("Invalid curve parameters: {}".format(curve_params))

    for i in range(path.elementCount()):
        e = path.elementAt(i)

        if params and e.type != CurveToDataElement:
            finish_curve(p, params)
            params = []

        if e.type == MoveToElement:
            p = QPainterPath()
            p.moveTo(e.x, e.y)
            subpaths.append(p)
        elif e.type == LineToElement:
            p.lineTo(e.x, e.y)
        elif e.type == CurveToElement:
            params = [QPointF(e.x, e.y)]
        elif e.type == CurveToDataElement:
            params.append(QPointF(e.x, e.y))

    if params:
        finish_curve(p, params)
    return subpaths


def join_painter_paths(paths):
    """Join a list of QPainterPath into a single path."""
    result = QPainterPath()
    for path in paths:
        result.addPath(path)
    return result
