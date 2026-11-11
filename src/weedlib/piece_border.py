# -*- coding: utf-8 -*-
"""The two piece-border rectangles around the subject."""
from __future__ import division

from .qt import QPainterPath


def piece_border(subject, inner_distance, border_width, corner_radius=None):
    """Return the inner rectangle, then the outer one.

    ``subject`` is the subject path in document user units. The
    lengths are user units the caller already converted. This
    function does not read a scale. The inner rectangle is the
    subject's axis-aligned bounds, expanded by ``inner_distance``
    on every side. The outer rectangle is that rectangle expanded
    by ``border_width``. An empty subject returns an empty tuple.

    ``corner_radius`` rounds every corner of both rectangles by
    the same radius. Omitted, ``None``, zero, or below stays
    square. The radius used is at most half the shorter side of
    the inner rectangle, so the corner arcs do not cross.
    """
    if not isinstance(subject, QPainterPath):
        raise TypeError(
            'subject must be a QPainterPath, got: {}'.format(
                type(subject).__name__))
    inner_distance = float(inner_distance)
    border_width = float(border_width)
    if subject.isEmpty():
        return ()
    inner = subject.boundingRect().adjusted(
        -inner_distance, -inner_distance,
        inner_distance, inner_distance)
    outer = inner.adjusted(
        -border_width, -border_width, border_width, border_width)
    radius = _limited_radius(inner, corner_radius)
    if radius == 0.0:
        return (_rectangle(inner), _rectangle(outer))
    return (_rounded(inner, radius), _rounded(outer, radius))


def _limited_radius(rect, corner_radius):
    """Cap at half the shorter side. Zero and below stay square."""
    if corner_radius is None:
        return 0.0
    radius = float(corner_radius)
    if not radius > 0.0:
        return 0.0
    shorter = min(abs(rect.width()), abs(rect.height()))
    limit = shorter * 0.5
    if radius > limit:
        return limit
    return radius


def _rectangle(rect):
    path = QPainterPath()
    path.addRect(rect)
    return path


def _rounded(rect, radius):
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    return path
