# -*- coding: utf-8 -*-
"""Checkerboard, subject, arrows, surrounds, and accepted segments."""
from __future__ import division

import math
import time

from .form import _hex_color, _surround_distance
from .geometry_ask import _unpack_path
from .return_line import _ARROW_KINDS

# Scene units. Short enough that a padding ring shows both tiles.
_CHECKER_TILE = 8.0


def _line_pen(QtGui, QtCore, color):
    pen = QtGui.QPen(QtGui.QColor(color))
    pen.setWidthF(0.0)
    pen.setCosmetic(True)
    return pen


def _with_work_region(weed_area, work, QPainterPath, Qt):
    """Weed area, plus the solver work rect once cuts exist."""
    path = QPainterPath()
    if weed_area is not None and not weed_area.isEmpty():
        path = QPainterPath(weed_area)
    if work is not None and work.isValid():
        rect = QPainterPath()
        rect.addRect(work)
        path = rect if path.isEmpty() else path.united(rect)
    path.setFillRule(Qt.OddEvenFill)
    return path


def _checker_type(QtWidgets, QtGui, QtCore):
    class _CheckerItem(QtWidgets.QGraphicsPathItem):
        def __init__(self, path, light, dark, tile):
            QtWidgets.QGraphicsPathItem.__init__(self, path)
            self._light = QtGui.QColor(light)
            self._dark = QtGui.QColor(dark)
            self._tile = float(tile)
            self.setPen(QtGui.QPen(QtCore.Qt.NoPen))

        def paint(self, painter, _option, _widget=None):
            painter.save()
            painter.setPen(QtCore.Qt.NoPen)
            painter.setClipPath(self.path(), QtCore.Qt.IntersectClip)
            bounds = self.path().boundingRect()
            tile = self._tile
            x0 = math.floor(bounds.left() / tile) * tile
            y0 = math.floor(bounds.top() / tile) * tile
            y = y0
            row = 0
            while y < bounds.bottom() - 1e-9:
                x = x0
                col = 0
                while x < bounds.right() - 1e-9:
                    if (col + row) % 2 == 0:
                        painter.setBrush(QtGui.QBrush(self._light))
                    else:
                        painter.setBrush(QtGui.QBrush(self._dark))
                    painter.drawRect(QtCore.QRectF(x, y, tile, tile))
                    x += tile
                    col += 1
                y += tile
                row += 1
            painter.restore()

    return _CheckerItem


class _Regions(object):
    def __init__(self, subject, weed_area, bounds):
        self.subject = subject
        self.weed_area = weed_area
        self.bounds = bounds


class _Preview(object):

    def _fit(self):
        rect = self.scene.itemsBoundingRect()
        if rect.isNull():
            return
        self.view.fitInView(rect, self.QtCore.Qt.KeepAspectRatio)

    def _fill(self, path, color, z_value):
        if path is None or path.isEmpty():
            return
        pen = self.QtGui.QPen(self.QtCore.Qt.NoPen)
        item = self.scene.addPath(path, pen, self.QtGui.QBrush(self.QtGui.QColor(color)))
        item.setZValue(z_value)
        self.state['preview_items'].append(item)

    def refresh_preview(self):
        for item in self.state['preview_items']:
            self.scene.removeItem(item)
        self.state['preview_items'] = []
        regions = self._ensure_regions()
        if regions is None:
            return
        light = self.light_edit.property('color')
        dark = self.dark_edit.property('color')
        weed_color = self.weed_edit.property('color')
        subject_color = self.subject_edit.property('color')
        # The work rect covers the subject. Subject paint sits above it.
        weed_path = _with_work_region(
            regions.weed_area, self.state['work'], self.QPainterPath, self.QtCore.Qt)
        if not weed_path.isEmpty():
            checker = self.CheckerItem(weed_path, light, dark, _CHECKER_TILE)
            checker.setZValue(0)
            self.scene.addItem(checker)
            self.state['preview_items'].append(checker)
        subject = regions.subject
        if subject is not None and not subject.isEmpty():
            painted = self.QPainterPath(subject)
            painted.setFillRule(self.QtCore.Qt.OddEvenFill)
            self._fill(painted, subject_color, 10)
        for fill, part in self.state.get('fill_parts') or []:
            solid = _hex_color(fill)
            if solid is None or part is None or part.isEmpty():
                continue
            self._fill(part, solid, 11)
        arrow_paths = {}
        for kind in _ARROW_KINDS:
            batch = list((self.state.get('arrow_paths') or {}).get(kind) or [])
            if not batch:
                continue
            arrow_paths[kind] = batch
            for arrow in batch:
                shaft = self.scene.addPath(
                    arrow.shaft,
                    _line_pen(self.QtGui, self.QtCore, arrow.color),
                    self.QtGui.QBrush(self.QtCore.Qt.NoBrush))
                shaft.setZValue(30)
                self.state['preview_items'].append(shaft)
                head = self.scene.addPath(
                    arrow.head,
                    self.QtGui.QPen(self.QtCore.Qt.NoPen),
                    self.QtGui.QBrush(self.QtGui.QColor(arrow.color)))
                head.setZValue(30)
                self.state['preview_items'].append(head)
        self.state['arrows'] = arrow_paths
        if not self.blocked and self.state['surround_started'] and self._in_surround():
            surround_pen = _line_pen(self.QtGui, self.QtCore, weed_color)
            bare = self.QtGui.QBrush(self.QtCore.Qt.NoBrush)
            for path in self.state['surround_paths']:
                if path is None or path.isEmpty():
                    continue
                item = self.scene.addPath(path, surround_pen, bare)
                item.setZValue(20)
                self.state['preview_items'].append(item)
        weed_pen = _line_pen(self.QtGui, self.QtCore, weed_color)
        for item in self.state['weed_items']:
            item.setPen(weed_pen)
            item.setZValue(20)
        self._fit()

    def clear_weed_items(self):
        for item in self.state['weed_items']:
            self.scene.removeItem(item)
        self.state['weed_items'] = []

    def _paint_solver_segments(self):
        """Line items for accepted segments. This thread owns the scene."""
        if self.state.get('aborting') or self.state['cancel'].is_set():
            self.state['seg_q'].clear()
            return
        if self.state.get('ask') != 'solver' or not self.state['seg_q']:
            return
        if self.state['work'] is None and self.state['solved_keep'] is not None:
            self.state['work'] = self.padded_work_rect(
                self.state['solved_keep'], self.state['solved_pad'])
            self.refresh_preview()
        weed_pen = _line_pen(self.QtGui, self.QtCore, self.weed_edit.property('color'))
        added = False
        for _ in range(200):
            if not self.state['seg_q']:
                break
            seg = self.state['seg_q'].popleft()
            try:
                x0, y0, x1, y1 = seg
            except (TypeError, ValueError):
                continue
            item = self.scene.addLine(x0, y0, x1, y1, weed_pen)
            item.setZValue(20)
            self.state['weed_items'].append(item)
            added = True
        if added and (time.time() - self.state.get('last_fit', 0.0)) > 0.4:
            rect = self.scene.itemsBoundingRect()
            if not rect.isNull():
                self.view.fitInView(rect, self.QtCore.Qt.KeepAspectRatio)
            self.state['last_fit'] = time.time()

    def _ensure_regions(self):
        # Applied by the subject ask. A color change does not ask again.
        return self.state.get('regions')

    def _store_subject(self, inbox):
        packed = inbox.get('subject') or ([], 0)
        subject = _unpack_path(packed[0], packed[1])
        packed = inbox.get('weed') or ([], 0)
        weed = _unpack_path(packed[0], packed[1])
        x, y, width, height = inbox['bounds']
        bounds = self.QtCore.QRectF(x, y, width, height)
        self.state['regions'] = _Regions(subject, weed, bounds)
        self.state['regions_swap'] = self.state['swapped']
        self.state['fill_parts'] = [
            (fill, _unpack_path(elements, rule))
            for fill, elements, rule in inbox['fills']
        ]
        arrow_paths = {}
        for kind, color, shaft, shaft_rule, head, head_rule in inbox['arrows']:
            arrow = self.ArrowPath(
                _unpack_path(shaft, shaft_rule),
                _unpack_path(head, head_rule),
                color)
            arrow_paths.setdefault(kind, []).append(arrow)
        self.state['arrow_paths'] = arrow_paths
        self._show_return_line()
        if self.state.get('opening'):
            # Setting the spin is not a surround ask.
            initial_distance = _surround_distance(bounds)
            hi = self.state['limits']['distance'][1]
            self.state['limits']['distance'] = (0.0, max(hi, initial_distance))
            self.state['lengths']['distance'] = initial_distance
            self._show_lengths()
