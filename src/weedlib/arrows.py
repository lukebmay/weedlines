# -*- coding: utf-8 -*-
"""Correction arrows: one shaft and one head per defect target."""
from __future__ import division

import math

from .qt import QPainterPath, QRectF

# Fraction of the longer design side. The preview scales with the
# bounds, and the guide does not name a length.
_HEAD_OF_SPAN = 0.06
_HEAD_HALF_WIDTH = 0.35
# When the target is closer than the nominal head, keep a shaft.
_MAX_HEAD_OF_LENGTH = 0.55
_AT_ORIGIN = 1e-9

# Minimum y is the top. Inward is diagonal, into the design.
_KINDS = {
    'dangling': ('#FF00FF', 'top-left', (1.0, 1.0)),
    'overlap': ('#FF6A00', 'top-right', (-1.0, 1.0)),
    'self-overlap': ('#00E5FF', 'bottom-right', (-1.0, -1.0)),
}


class ArrowPath(object):
    """Open shaft, head triangle, and that kind's color."""

    def __init__(self, shaft, head, color):
        self.shaft = shaft
        self.head = head
        self.color = color


def build_arrow_paths(kind, targets, bounds):
    """Return one arrow per target for one defect kind.

    ``kind`` is dangling, overlap, or self-overlap. ``bounds`` is
    the design box in document units, minimum y at the top.
    """
    try:
        color, place, inward = _KINDS[kind]
    except KeyError:
        raise ValueError('unknown arrow kind: {!r}'.format(kind))
    if not isinstance(bounds, QRectF):
        raise TypeError(
            'bounds must be a QRectF, got: {}'.format(type(bounds).__name__))
    box = bounds.normalized()
    origin = _origin(place, box)
    head_len = _head_length(box)
    inward = _unit(inward)
    return [
        _one_arrow(origin, _xy(point), head_len, inward, color)
        for point in targets
    ]


def _origin(place, box):
    if place == 'top-left':
        return box.left(), box.top()
    if place == 'top-right':
        return box.right(), box.top()
    return box.right(), box.bottom()


def _head_length(box):
    span = max(box.width(), box.height())
    if span <= 0.0:
        span = 1.0
    return span * _HEAD_OF_SPAN


def _unit(vector):
    x, y = vector
    length = math.hypot(x, y)
    return (x / length, y / length)


def _xy(point):
    x = getattr(point, 'x', None)
    y = getattr(point, 'y', None)
    if x is not None and y is not None:
        if callable(x):
            x, y = x(), y()
        return float(x), float(y)
    x, y = point
    return float(x), float(y)


def _one_arrow(origin, target, head_len, inward, color):
    ox, oy = origin
    tx, ty = target
    length = math.hypot(tx - ox, ty - oy)
    if length <= _AT_ORIGIN:
        # Tip stays on the target. A shaft from the same point
        # would have no length, so the tail sits inside the bounds.
        mark = head_len / _MAX_HEAD_OF_LENGTH
        sx = tx + inward[0] * mark
        sy = ty + inward[1] * mark
        used = head_len
    else:
        sx, sy = ox, oy
        used = min(head_len, length * _MAX_HEAD_OF_LENGTH)
    shaft, head = _shaft_and_head(sx, sy, tx, ty, used)
    return ArrowPath(shaft, head, color)


def _shaft_and_head(sx, sy, tx, ty, head_len):
    length = math.hypot(tx - sx, ty - sy)
    ux = (tx - sx) / length
    uy = (ty - sy) / length
    half = head_len * _HEAD_HALF_WIDTH
    bx = tx - ux * head_len
    by = ty - uy * head_len
    px = -uy * half
    py = ux * half
    shaft = QPainterPath()
    shaft.moveTo(sx, sy)
    shaft.lineTo(bx, by)
    head = QPainterPath()
    head.moveTo(tx, ty)
    head.lineTo(bx + px, by + py)
    head.lineTo(bx - px, by - py)
    head.closeSubpath()
    return shaft, head
