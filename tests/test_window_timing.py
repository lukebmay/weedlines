# -*- coding: utf-8 -*-
"""Window timing: library asks run once, after the dialog is visible."""
from __future__ import division

import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest

try:
    from weedlib.qt import load_widgets
    QtCore, _QtGui, QtWidgets = load_widgets()
except Exception as exc:
    pytest.skip('Qt cannot load: %s' % exc, allow_module_level=True)

_EXT_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'extensions', 'inkscape'))
if _EXT_DIR not in sys.path:
    sys.path.insert(0, _EXT_DIR)

from weedlines_dialog import run_weedlines_dialog  # noqa: E402

_PROBLEM = (
    'Correct the marked problems in Inkscape before weed lines will run.')
_ALL_KINDS = (
    _PROBLEM + ' dangling ends, figure overlaps, and self-overlaps.')
_ARROW = 'Return to Inkscape with correction arrows'
_WEED = '#ff0000'

_CLEAR = [{
    'id': 'panel',
    'd': 'M 0,0 L 50,0 L 50,50 L 0,50 Z',
    'closed': [True],
    'fill': '#112233',
}]
_OPEN_TRI = 'M 0,0 L 10,0 L 10,10'
_BLOCK = 'M 8,-2 L 14,-2 L 14,4 L 8,4 Z'
_CROSS = (
    'M 100,100 L 110,100 L 110,110 L 100,110 Z '
    'M 105,105 L 115,105 L 115,115 L 105,115 Z'
)
_DEFECTS = [
    {'id': 'gap', 'd': _OPEN_TRI, 'closed': [False], 'fill': 'none'},
    {'id': 'block', 'd': _BLOCK, 'closed': [True], 'fill': '#336699'},
    {'id': 'cross', 'd': _CROSS, 'closed': [True, True], 'fill': '#222222'},
]


def _visible_dialog():
    app = QtWidgets.QApplication.instance()
    if app is None:
        return None
    found = [
        widget for widget in app.topLevelWidgets()
        if widget.isVisible() and widget.windowTitle() == 'Weedlines'
    ]
    if len(found) != 1:
        return None
    return found[0]


def _run(records, drive, **kwargs):
    app = QtWidgets.QApplication.instance()
    if app is None:
        QtWidgets.QApplication([])

    def ready(dialog):
        timer = QtCore.QTimer(dialog)
        timer.setSingleShot(True)
        timer.timeout.connect(dialog.reject)
        timer.start(20000)
        drive(dialog)

    return run_weedlines_dialog(records, ready=ready, quit_app=False, **kwargs)


def _same_path(got, expected):
    if got.elementCount() != expected.elementCount():
        return False
    for index in range(expected.elementCount()):
        left = got.elementAt(index)
        right = expected.elementAt(index)
        if left.type != right.type:
            return False
        if left.x != pytest.approx(right.x) or left.y != pytest.approx(right.y):
            return False
    return True


def _path_items(dialog):
    view = dialog.findChild(QtWidgets.QGraphicsView, 'preview')
    assert view is not None
    items = []
    for item in view.scene().items():
        reader = getattr(item, 'path', None)
        if not callable(reader):
            continue
        try:
            path = reader()
        except TypeError:
            continue
        if hasattr(path, 'elementCount'):
            items.append(item)
    return items


def _pen_hex(item):
    pen = item.pen()
    if pen.style() == QtCore.Qt.NoPen:
        return None
    return pen.color().name().lower()


def _brush_hex(item):
    brush = item.brush()
    if brush.style() == QtCore.Qt.NoBrush:
        return None
    return brush.color().name().lower()


def _watch(monkeypatch):
    import weedlib
    import weedlib.arrows as arrow_mod
    import weedlib.figures as figures

    events = []
    swaps = []
    surrounds = []
    arrows = []

    def see(name):
        dialog = _visible_dialog()
        assert dialog is not None, name
        events.append((name, dialog))

    real_classify = figures.classify_figures
    real_subject = figures.subject_weed_regions
    real_arrows = arrow_mod.build_arrow_paths
    real_surrounds = weedlib.build_surrounds

    def classify_wrap(records):
        see('classify')
        return real_classify(records)

    def subject_wrap(figures, swap):
        see('subject')
        swaps.append(swap)
        return real_subject(figures, swap)

    def arrows_wrap(kind, targets, bounds):
        see('arrows')
        batch = real_arrows(kind, targets, bounds)
        arrows.append(batch)
        return batch

    def surrounds_wrap(subject, distance):
        see('surrounds')
        paths = real_surrounds(subject, distance)
        surrounds.append((float(distance), paths))
        return paths

    def refuse_solver(*_args, **_kwargs):
        raise AssertionError('solver ran')

    monkeypatch.setattr(figures, 'classify_figures', classify_wrap)
    monkeypatch.setattr(figures, 'subject_weed_regions', subject_wrap)
    monkeypatch.setattr(arrow_mod, 'build_arrow_paths', arrows_wrap)
    monkeypatch.setattr(weedlib, 'build_surrounds', surrounds_wrap)
    monkeypatch.setattr(weedlib, 'generate_weeds', refuse_solver)
    return events, swaps, surrounds, arrows


def _names(events):
    return [name for name, _dialog in events]


def _assert_same_dialog(events, dialog):
    assert events
    for _name, seen in events:
        assert seen is dialog


def test_clear_surround_asks_once_after_the_window_is_visible(monkeypatch):
    events, swaps, surrounds, arrows = _watch(monkeypatch)

    def drive(dialog):
        assert dialog.isVisible() is True
        assert _names(events) == ['classify', 'subject', 'surrounds']
        _assert_same_dialog(events, dialog)
        assert swaps == [False]
        assert arrows == []
        assert len(surrounds) == 1
        distance, paths = surrounds[0]
        spin = dialog.findChild(
            QtWidgets.QDoubleSpinBox, 'surround-distance')
        assert spin is not None
        assert distance == pytest.approx(spin.value())
        assert distance == pytest.approx(2.5)
        assert paths
        items = _path_items(dialog)
        for path in paths:
            matched = [
                item for item in items
                if _same_path(item.path(), path)
            ]
            assert len(matched) == 1
            assert _pen_hex(matched[0]) == _WEED
            assert _brush_hex(matched[0]) is None
        start = dialog.findChild(QtWidgets.QPushButton, 'start')
        assert start is not None and start.isEnabled() is True
        asked = list(events)
        start.click()
        assert events == asked
        assert dialog.isVisible() is True
        assert spin.isEnabled() is False
        line = dialog.findChild(QtWidgets.QLabel, 'return-line')
        assert line is not None and line.text() == ''
        correction = [
            button for button in dialog.findChildren(QtWidgets.QPushButton)
            if button.text() == _ARROW
        ]
        assert correction == []
        dialog.reject()

    _run(_CLEAR, drive)


def test_defect_asks_once_after_the_window_is_visible(monkeypatch):
    events, swaps, surrounds, arrows = _watch(monkeypatch)

    def drive(dialog):
        assert dialog.isVisible() is True
        assert _names(events) == [
            'classify', 'subject', 'arrows', 'arrows', 'arrows']
        _assert_same_dialog(events, dialog)
        assert swaps == [False]
        assert surrounds == []
        assert len(arrows) == 3
        items = _path_items(dialog)
        for batch in arrows:
            assert batch
            for arrow in batch:
                shafts = [
                    item for item in items
                    if _same_path(item.path(), arrow.shaft)
                ]
                heads = [
                    item for item in items
                    if _same_path(item.path(), arrow.head)
                ]
                assert len(shafts) == 1
                assert len(heads) == 1
                assert _pen_hex(shafts[0]) == arrow.color.lower()
                assert _brush_hex(heads[0]) == arrow.color.lower()
        line = dialog.findChild(QtWidgets.QLabel, 'return-line')
        assert line is not None and line.text() == _ALL_KINDS
        correction = dialog.findChild(QtWidgets.QPushButton, 'return-arrows')
        assert correction is not None
        assert correction.text() == _ARROW
        assert correction.isVisible() is True
        start = dialog.findChild(QtWidgets.QPushButton, 'start')
        assert start is not None and start.isEnabled() is False
        asked = list(events)
        start.click()
        assert events == asked
        assert start.isEnabled() is False
        dialog.reject()

    _run(_DEFECTS, drive)
