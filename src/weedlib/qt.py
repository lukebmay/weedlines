# -*- coding: utf-8 -*-
"""Qt binding shim for weed geometry (enaml, PyQt, or PySide)."""
from __future__ import division


def _load():
    try:
        from enaml.qt.QtCore import QPointF, QRectF, Qt
        from enaml.qt.QtGui import QPainterPath, QTransform
        return QPointF, QRectF, Qt, QPainterPath, QTransform, 'enaml'
    except ImportError:
        pass
    for pkg in ('PyQt5', 'PySide2', 'PyQt6', 'PySide6'):
        try:
            core = __import__(pkg + '.QtCore', fromlist=['QPointF', 'QRectF', 'Qt'])
            gui = __import__(pkg + '.QtGui', fromlist=['QPainterPath', 'QTransform'])
            return (
                core.QPointF, core.QRectF, core.Qt,
                gui.QPainterPath, gui.QTransform, pkg,
            )
        except ImportError:
            continue
    raise ImportError(
        'weedlib requires Qt: PyQt5/6, PySide2/6, or enaml.qt'
    )


QPointF, QRectF, Qt, QPainterPath, QTransform, QT_BINDING = _load()


def load_widgets():
    """Return ``(QtCore, QtGui, QtWidgets)`` modules for the active binding."""
    if QT_BINDING == 'enaml':
        from enaml.qt import QtCore, QtGui, QtWidgets
        return QtCore, QtGui, QtWidgets
    core = __import__(QT_BINDING + '.QtCore', fromlist=['Qt'])
    gui = __import__(QT_BINDING + '.QtGui', fromlist=['QPainter'])
    widgets = __import__(QT_BINDING + '.QtWidgets', fromlist=['QApplication'])
    return core, gui, widgets


__all__ = [
    'QPointF', 'QRectF', 'Qt', 'QPainterPath', 'QTransform',
    'QT_BINDING', 'load_widgets',
]
