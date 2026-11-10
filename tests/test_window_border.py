# -*- coding: utf-8 -*-
"""Window piece border: paint, lengths, swap, and the form. No Inkscape."""
from __future__ import division

import importlib
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest

try:
    from weedlib.qt import load_widgets
    QtCore, QtGui, QtWidgets = load_widgets()
except Exception as exc:
    pytest.skip('Qt cannot load: %s' % exc, allow_module_level=True)

_EXT_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'extensions', 'inkscape'))
if _EXT_DIR not in sys.path:
    sys.path.insert(0, _EXT_DIR)

border_mod = importlib.import_module('weedlib.piece_border')
from weedlib.figures import classify_figures, subject_weed_regions  # noqa: E402
from weedlines_dialog import run_weedlines_dialog  # noqa: E402

_WEED = '#ff0000'
_MM = 1.0 / 25.4

_SQUARE = [{
    'id': 'box',
    'd': 'M 0,0 L 40,0 L 40,30 L 0,30 Z',
    'closed': [True],
    'fill': 'none',
}]
_FRAME = 'M 0,0 L 80,0 L 80,50 L 0,50 Z'
_LETTER = 'M 10,10 L 24,10 L 24,30 L 10,30 Z'
_CLEAR = [
    {'id': 'frame', 'd': _FRAME, 'closed': [True], 'fill': 'none'},
    {'id': 'letter', 'd': _LETTER, 'closed': [True], 'fill': '#112233'},
]
_OPEN = [{
    'id': 'gap',
    'd': 'M 5,6 L 15,6 L 15,20',
    'closed': [False],
    'fill': 'none',
}]
_SPINS = ('collar', 'join-gap', 'padding', 'spacing', 'surround-distance')


def _button(dialog, name):
    widget = dialog.findChild(QtWidgets.QPushButton, name)
    assert widget is not None, name
    return widget


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


def _busy(dialog):
    start = dialog.findChild(QtWidgets.QPushButton, 'start')
    if start is None or not start.isVisible():
        return True
    for button in dialog.findChildren(QtWidgets.QPushButton):
        if not button.isVisible():
            continue
        if button.text() in ('Pause', 'Resume', 'Cancelling…'):
            return True
        if button.text().startswith('Cancel'):
            return True
    return False


def _pump_until(predicate, timeout=20):
    import time
    app = QtWidgets.QApplication.instance()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents(QtCore.QEventLoop.AllEvents, 30)
        if predicate():
            return
    raise AssertionError('timed out')


def _wait_settled(dialog, borders):
    _pump_until(
        lambda: len(dialog.border_args) >= borders and not _busy(dialog))


def _subject(records, swap):
    return subject_weed_regions(
        classify_figures(records).figures, swap=swap).subject


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


def _assert_border(dialog, paths, color):
    assert len(paths) == 2
    items = _path_items(dialog)
    for path in paths:
        matched = [item for item in items if _same_path(item.path(), path)]
        assert len(matched) == 1
        assert _pen_hex(matched[0]) == color
        assert _brush_hex(matched[0]) is None
        assert matched[0].zValue() == 20


def _watch(monkeypatch):
    import weedlib
    parent = []
    real = border_mod.piece_border

    def wrapped(*args, **kwargs):
        parent.append(args)
        return real(*args, **kwargs)

    monkeypatch.setattr(border_mod, 'piece_border', wrapped)
    monkeypatch.setattr(weedlib, 'piece_border', wrapped)
    return parent, real


def test_clear_design_paints_both_rectangles_without_start(monkeypatch):
    parent, real = _watch(monkeypatch)
    subject = _subject(_SQUARE, False)

    def drive(dialog):
        assert _button(dialog, 'start').text() == 'Start'
        _wait_settled(dialog, 1)
        assert parent == []
        assert dialog.worker_calls.count('piece_border') == 1
        assert _button(dialog, 'start').text() == 'Start'
        pair = real(subject, dialog.lengths['inner'], dialog.lengths['border'])
        _assert_border(dialog, pair, _WEED)
        asked = len(dialog.border_args)
        calls = len(dialog.worker_calls)
        edit = dialog.findChild(QtWidgets.QPushButton, 'weed-line-color')
        assert edit is not None

        def choose():
            opened = [
                picker for picker in dialog.findChildren(
                    QtWidgets.QColorDialog, 'color-picker')
                if picker.isVisible()
            ]
            assert len(opened) == 1
            opened[0].setCurrentColor(QtGui.QColor('#0000ff'))
            opened[0].accept()

        QtCore.QTimer.singleShot(0, choose)
        edit.click()
        assert edit.property('color') == '#0000FF'
        assert len(dialog.border_args) == asked
        assert len(dialog.worker_calls) == calls
        _assert_border(dialog, pair, '#0000ff')
        dialog.reject()

    _run(_SQUARE, drive)
    assert parent == []


def test_held_border_ask_paints_only_after_it_returns(monkeypatch):
    import weedlines_dialog as dialog_mod
    parent, real = _watch(monkeypatch)
    subject = _subject(_SQUARE, False)
    seen = []
    real_spawn = dialog_mod._spawn_ask

    def wrapped_spawn(request, hold, pausing, cancelled):
        proc, conn = real_spawn(request, hold, pausing, cancelled)
        if request.get('kind') != 'border':
            return proc, conn
        dialog = QtWidgets.QApplication.instance().activeWindow()
        if dialog is None or dialog.windowTitle() != 'Weedlines':
            found = [
                widget for widget in QtWidgets.QApplication.instance().topLevelWidgets()
                if widget.isVisible() and widget.windowTitle() == 'Weedlines'
            ]
            dialog = found[0]
        timer = QtCore.QTimer(dialog)
        timer.setSingleShot(True)

        def mark():
            pair = real(subject, dialog.lengths['inner'], dialog.lengths['border'])
            painted = []
            for path in pair:
                painted.append(any(
                    _same_path(item.path(), path) for item in _path_items(dialog)))
            seen.append((
                dialog.isVisible() is True,
                proc.is_alive(),
                painted,
            ))

        timer.timeout.connect(mark)
        timer.start(0)
        timers = getattr(dialog, '_hold_timers', None)
        if timers is None:
            timers = []
            dialog._hold_timers = timers
        timers.append(timer)
        return proc, conn

    monkeypatch.setattr(dialog_mod, '_spawn_ask', wrapped_spawn)
    old = dialog_mod._ASK_HOLD
    dialog_mod._ASK_HOLD = 8000000

    def drive(dialog):
        try:
            _pump_until(lambda: bool(seen))
            visible, alive, painted = seen[0]
            assert visible is True
            assert alive is True
            assert painted == [False, False]
            _wait_settled(dialog, 1)
            pair = real(subject, dialog.lengths['inner'], dialog.lengths['border'])
            _assert_border(dialog, pair, _WEED)
            assert parent == []
            assert 'piece_border' in dialog.worker_calls
            dialog.reject()
        finally:
            if dialog.isVisible():
                dialog.reject()

    try:
        _run(_SQUARE, drive)
    finally:
        dialog_mod._ASK_HOLD = old
    assert parent == []


def test_lengths_are_an_eighth_inch_under_the_document_scale(monkeypatch):
    parent, _real = _watch(monkeypatch)

    def drive(dialog):
        _wait_settled(dialog, 1)
        inner, width = dialog.border_args[0]
        assert inner == pytest.approx(12)
        assert width == pytest.approx(12)
        assert inner != pytest.approx(6.35)
        assert width != pytest.approx(6.35)
        box = dialog.findChild(QtWidgets.QComboBox, 'mode')
        for index in range(box.count()):
            if box.itemData(index) == 'frame':
                box.setCurrentIndex(index)
                break
        _button(dialog, 'start').click()
        _pump_until(lambda: bool(dialog.solver_border))
        sent_inner, sent_width = dialog.solver_border[-1]
        assert sent_inner == pytest.approx(12)
        assert sent_width == pytest.approx(12)
        assert sent_inner != pytest.approx(6.35)
        padding, _spacing, _collar = dialog.solver_args[-1]
        assert len(padding) == 4
        dialog.reject()

    _run(_SQUARE, drive)
    assert parent == []

    def drive_mm(dialog):
        _wait_settled(dialog, 1)
        inner, width = dialog.border_args[0]
        assert inner == pytest.approx(3.175)
        assert width == pytest.approx(3.175)
        assert inner != pytest.approx(6.35)
        assert width != pytest.approx(6.35)
        assert inner != pytest.approx(12)
        dialog.reject()

    _run(_SQUARE, drive_mm, user_unit_scale=_MM)
    assert parent == []


def test_defect_paints_no_border_and_does_not_ask(monkeypatch):
    parent, _real = _watch(monkeypatch)

    def drive(dialog):
        _pump_until(lambda: not _busy(dialog))
        assert 'piece_border' not in dialog.worker_calls
        assert dialog.border_args == []
        for item in _path_items(dialog):
            assert _pen_hex(item) != _WEED
        dialog.reject()

    _run(_OPEN, drive)
    assert parent == []


def test_swap_and_stored_lengths_ask_again(monkeypatch):
    parent, real = _watch(monkeypatch)

    def drive(dialog):
        _wait_settled(dialog, 1)
        assert len(dialog.border_args) == 1
        _button(dialog, 'swap').click()
        _wait_settled(dialog, 2)
        swapped = _subject(_CLEAR, True)
        pair = real(swapped, dialog.lengths['inner'], dialog.lengths['border'])
        _assert_border(dialog, pair, _WEED)
        assert parent == []

        _button(dialog, 'start').click()
        _pump_until(
            lambda: dialog.worker_calls.count('surrounds') >= 1 and not _busy(dialog))
        borders = len(dialog.border_args)
        surrounds = len(dialog.surround_args)
        dialog.lengths['inner'] = dialog.lengths['inner'] + 1.0
        dialog.change_piece_length('inner')
        _pump_until(
            lambda: (
                len(dialog.border_args) >= borders + 1
                and len(dialog.surround_args) >= surrounds + 1
                and not _busy(dialog)))
        assert len(dialog.border_args) == borders + 1
        assert len(dialog.surround_args) == surrounds + 1
        assert dialog.surround_inner[-1] == pytest.approx(dialog.lengths['inner'])
        assert dialog.border_args[-1][0] == pytest.approx(dialog.lengths['inner'])

        borders = len(dialog.border_args)
        surrounds = len(dialog.surround_args)
        dialog.lengths['border'] = dialog.lengths['border'] + 1.0
        dialog.change_piece_length()
        _wait_settled(dialog, borders + 1)
        assert len(dialog.border_args) == borders + 1
        assert len(dialog.surround_args) == surrounds
        assert dialog.border_args[-1][1] == pytest.approx(dialog.lengths['border'])
        assert parent == []
        dialog.reject()

    _run(_CLEAR, drive)
    assert parent == []


def _set_mode(dialog, mode):
    box = dialog.findChild(QtWidgets.QComboBox, 'mode')
    assert box is not None
    for index in range(box.count()):
        if box.itemData(index) == mode:
            box.setCurrentIndex(index)
            return
    raise AssertionError('missing mode %s' % mode)


def _shown_dialog():
    app = QtWidgets.QApplication.instance()
    found = [
        widget for widget in app.topLevelWidgets()
        if widget.isVisible() and widget.windowTitle() == 'Weedlines'
    ]
    assert found
    return found[0]


def _hold_border(monkeypatch, mark):
    """Hold one border ask and run mark while that child is alive."""
    import weedlines_dialog as dialog_mod
    real_spawn = dialog_mod._spawn_ask
    armed = []

    def wrapped_spawn(request, hold, pausing, cancelled):
        proc, conn = real_spawn(request, hold, pausing, cancelled)
        if request.get('kind') != 'border' or armed:
            return proc, conn
        dialog = _shown_dialog()
        if not mark_ready(dialog):
            return proc, conn
        armed.append(True)
        timer = QtCore.QTimer(dialog)
        timer.setSingleShot(True)

        def fire():
            if dialog.isVisible() and proc.is_alive() and dialog.ask_name == 'border':
                mark(dialog)

        timer.timeout.connect(fire)
        timer.start(0)
        timers = getattr(dialog, '_hold_timers', None)
        if timers is None:
            timers = []
            dialog._hold_timers = timers
        timers.append(timer)
        return proc, conn

    def mark_ready(dialog):
        return True

    wrapped_spawn.mark_ready = None

    def use(dialog_ready):
        nonlocal mark_ready
        mark_ready = dialog_ready

    monkeypatch.setattr(dialog_mod, '_spawn_ask', wrapped_spawn)
    old = dialog_mod._ASK_HOLD
    dialog_mod._ASK_HOLD = 8000000
    return dialog_mod, old, use


def test_restart_during_border_asks_the_surround_again(monkeypatch):
    import weedlib
    parent, _real = _watch(monkeypatch)
    clicked = []

    def mark(dialog):
        clicked.append(dialog.ask_name == 'border')
        _button(dialog, 'start').click()

    def ready(dialog):
        return dialog.worker_calls.count('surrounds') >= 1

    dialog_mod, old, use = _hold_border(monkeypatch, mark)
    use(ready)

    def drive(dialog):
        try:
            _wait_settled(dialog, 1)
            _button(dialog, 'start').click()
            _pump_until(
                lambda: dialog.worker_calls.count('surrounds') >= 1
                and not _busy(dialog))
            surrounds = dialog.worker_calls.count('surrounds')
            dialog.lengths['border'] = dialog.lengths['border'] + 1.0
            dialog.change_piece_length('border')
            _pump_until(lambda: bool(clicked))
            assert clicked == [True]
            _pump_until(
                lambda: dialog.worker_calls.count('surrounds') >= surrounds + 1
                and not _busy(dialog))
            assert dialog.worker_calls.count('surrounds') == surrounds + 1
            assert dialog.worker_calls[-1] == 'surrounds'
            subject = _subject(_CLEAR, False)
            distance, join_gap = dialog.surround_args[-1]
            paths = weedlib.build_surrounds(
                subject, distance, join_gap,
                inner_distance=dialog.lengths['inner'])
            assert paths
            items = _path_items(dialog)
            for path in paths:
                matched = [
                    item for item in items if _same_path(item.path(), path)]
                assert len(matched) == 1
                assert _pen_hex(matched[0]) == _WEED
                assert _brush_hex(matched[0]) is None
            assert parent == []
            dialog.reject()
        finally:
            if dialog.isVisible():
                dialog.reject()

    try:
        _run(_CLEAR, drive)
    finally:
        dialog_mod._ASK_HOLD = old
    assert parent == []


def test_queued_solver_uses_the_later_subject_and_lengths(monkeypatch):
    parent, _real = _watch(monkeypatch)

    def mark(dialog):
        _set_mode(dialog, 'frame')
        _button(dialog, 'start').click()
        dialog.lengths['padding'] = 7.0
        dialog.lengths['spacing'] = 9.0
        dialog.lengths['collar'] = 1.5
        dialog.lengths['inner'] = 13.0
        dialog.lengths['border'] = 13.0
        _button(dialog, 'swap').click()

    dialog_mod, old, _use = _hold_border(monkeypatch, mark)

    def drive(dialog):
        try:
            _pump_until(
                lambda: bool(dialog.solver_border) and not _busy(dialog))
            padding, spacing, collar = dialog.solver_args[-1]
            assert padding == pytest.approx([7.0, 7.0, 7.0, 7.0])
            assert spacing == pytest.approx(9.0)
            assert collar == pytest.approx(1.5)
            sent_inner, sent_width = dialog.solver_border[-1]
            assert sent_inner == pytest.approx(13.0)
            assert sent_width == pytest.approx(13.0)
            assert dialog.solver_keeps[-1][0] == 'frame'
            box = dialog.solver_keeps[-1][1].boundingRect()
            assert box.width() == pytest.approx(80.0)
            assert box.height() == pytest.approx(50.0)
            assert parent == []
            dialog.reject()
        finally:
            if dialog.isVisible():
                dialog.reject()

    try:
        _run(_CLEAR, drive)
    finally:
        dialog_mod._ASK_HOLD = old
    assert parent == []


def test_queued_solver_drops_when_the_mode_leaves(monkeypatch):
    parent, _real = _watch(monkeypatch)

    def mark(dialog):
        _set_mode(dialog, 'frame')
        _button(dialog, 'start').click()
        _set_mode(dialog, 'grid')

    dialog_mod, old, _use = _hold_border(monkeypatch, mark)

    def drive(dialog):
        try:
            _pump_until(
                lambda: dialog.worker_calls.count('piece_border') >= 1
                and not _busy(dialog))
            assert 'solver' not in dialog.worker_calls
            assert dialog.solver_args == []
            _set_mode(dialog, 'frame')
            assert _button(dialog, 'start').text() == 'Start'
            assert parent == []
            dialog.reject()
        finally:
            if dialog.isVisible():
                dialog.reject()

    try:
        _run(_CLEAR, drive)
    finally:
        dialog_mod._ASK_HOLD = old
    assert parent == []


def test_form_has_no_new_length_option(monkeypatch):
    _watch(monkeypatch)

    def drive(dialog):
        spins = sorted(
            spin.objectName()
            for spin in dialog.findChildren(QtWidgets.QDoubleSpinBox))
        assert tuple(spins) == _SPINS
        for label in dialog.findChildren(QtWidgets.QLabel):
            text = label.text().lower()
            assert 'border' not in text
            assert 'inner' not in text
            assert 'eighth' not in text
        box = dialog.findChild(QtWidgets.QComboBox, 'mode')
        modes = [box.itemData(index) for index in range(box.count())]
        assert 'island-hop' in modes
        assert 'Surround and Conquer' in modes
        dialog.reject()

    _run(_SQUARE, drive)
