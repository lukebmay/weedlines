# -*- coding: utf-8 -*-
"""The two piece-border rectangles around the subject."""
from __future__ import division

from .qt import QPainterPath


def piece_border(subject, inner_distance, border_width):
    """Return the inner rectangle, then the outer one.

    ``subject`` is the subject path in document user units. The
    two lengths are user units the caller already converted.
    This function does not read a scale. The inner rectangle is
    the subject's axis-aligned bounds, expanded by
    ``inner_distance`` on every side. The outer rectangle is
    that rectangle expanded by ``border_width``. An empty
    subject returns an empty tuple.
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
    return (_rectangle(inner), _rectangle(outer))


def _rectangle(rect):
    path = QPainterPath()
    path.addRect(rect)
    return path
