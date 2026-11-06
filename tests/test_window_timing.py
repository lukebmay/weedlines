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
    # A one-millimeter document, unless the test names another scale.
    kwargs.setdefault('display_unit', 'mm')
    kwargs.setdefault('user_unit_scale', 1.0 / 25.4)

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


def _library_arrows(records):
    import weedlib.arrows as arrow_mod
    import weedlib.figures as figures

    check = figures.classify_figures(records)
    regions = figures.subject_weed_regions(check.figures, swap=False)
    grouped = {}
    for defect in check.defects:
        grouped.setdefault(defect.kind, []).append(defect.target)
    arrows = []
    for kind in ('dangling', 'overlap', 'self-overlap'):
        targets = grouped.get(kind)
        if not targets:
            continue
        arrows.extend(arrow_mod.build_arrow_paths(
            kind, targets, regions.bounds))
    return arrows


def _watch(monkeypatch):
    import weedlib
    import weedlib.arrows as arrow_mod
    import weedlib.figures as figures

    parent = []
    surrounds = []

    real_classify = figures.classify_figures
    real_subject = figures.subject_weed_regions
    real_arrows = arrow_mod.build_arrow_paths
    real_surrounds = weedlib.build_surrounds

    def classify_wrap(records):
        parent.append('classify')
        return real_classify(records)

    def subject_wrap(figures, swap):
        parent.append(('subject', swap))
        return real_subject(figures, swap)

    def arrows_wrap(kind, targets, bounds):
        parent.append('arrows')
        return real_arrows(kind, targets, bounds)

    def surrounds_wrap(subject, distance, join_gap=0.0):
        dialog = _visible_dialog()
        assert dialog is not None
        parent.append('surrounds')
        paths = real_surrounds(subject, distance, join_gap)
        surrounds.append((float(distance), float(join_gap), paths, dialog))
        return paths

    def refuse_solver(*_args, **_kwargs):
        raise AssertionError('solver ran')

    monkeypatch.setattr(figures, 'classify_figures', classify_wrap)
    monkeypatch.setattr(figures, 'subject_weed_regions', subject_wrap)
    monkeypatch.setattr(arrow_mod, 'build_arrow_paths', arrows_wrap)
    monkeypatch.setattr(weedlib, 'build_surrounds', surrounds_wrap)
    monkeypatch.setattr(weedlib, 'generate_weeds', refuse_solver)
    return parent, surrounds, real_surrounds, real_classify, real_subject


def _wait_idle(dialog, timeout=20):
    import time
    app = QtWidgets.QApplication.instance()
    deadline = time.monotonic() + timeout
    quiet = 0
    while time.monotonic() < deadline:
        app.processEvents(QtCore.QEventLoop.AllEvents, 30)
        start = dialog.findChild(QtWidgets.QPushButton, 'start')
        busy = start is None or not start.isVisible()
        if not busy:
            for button in dialog.findChildren(QtWidgets.QPushButton):
                if not button.isVisible():
                    continue
                if button.text() in ('Pause', 'Resume', 'Cancelling…'):
                    busy = True
                elif button.text().startswith('Cancel'):
                    busy = True
        if busy:
            quiet = 0
            continue
        quiet += 1
        if quiet >= 2:
            return
    raise AssertionError('surround ask did not finish')


def test_clear_surround_waits_until_start(monkeypatch):
    parent, surrounds, real_surrounds, real_classify, real_subject = _watch(
        monkeypatch)

    def drive(dialog):
        assert dialog.isVisible() is True
        # The parent patch does not see the child. The worker does.
        assert parent == []
        assert list(dialog.worker_calls) == ['classify', 'subject']
        assert list(dialog.worker_swaps) == [False]
        assert surrounds == []
        for item in _path_items(dialog):
            assert _pen_hex(item) != _WEED
        spin = dialog.findChild(
            QtWidgets.QDoubleSpinBox, 'surround-distance')
        join = dialog.findChild(QtWidgets.QDoubleSpinBox, 'join-gap')
        assert spin is not None and join is not None
        assert spin.value() == pytest.approx(2.5)
        assert join.value() == pytest.approx(6.35)
        start = dialog.findChild(QtWidgets.QPushButton, 'start')
        assert start is not None and start.isEnabled() is True
        line = dialog.findChild(QtWidgets.QLabel, 'return-line')
        assert line is not None and line.text() == ''
        correction = [
            button for button in dialog.findChildren(QtWidgets.QPushButton)
            if button.text() == _ARROW
        ]
        assert correction == []
        start.click()
        _wait_idle(dialog)
        assert list(dialog.worker_calls) == ['classify', 'subject', 'surrounds']
        assert parent == []
        assert surrounds == []
        assert dialog.isVisible() is True
        assert len(dialog.surround_args) == 1
        distance, join_gap = dialog.surround_args[0]
        assert distance == pytest.approx(spin.value())
        assert join_gap == pytest.approx(join.value())
        assert distance == pytest.approx(2.5)
        assert join_gap == pytest.approx(6.35)
        regions = real_subject(real_classify(_CLEAR).figures, False)
        paths = real_surrounds(regions.subject, distance, join_gap)
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
        assert spin.isEnabled() is True
        assert join.isEnabled() is True
        dialog.reject()

    _run(_CLEAR, drive)


def test_defect_asks_once_after_the_window_is_visible(monkeypatch):
    expected = _library_arrows(_DEFECTS)
    assert len(expected) >= 3
    parent, surrounds, _real_surrounds, _real_classify, _real_subject = _watch(
        monkeypatch)

    def drive(dialog):
        assert dialog.isVisible() is True
        assert parent == []
        assert list(dialog.worker_calls) == [
            'classify', 'subject', 'arrows', 'arrows', 'arrows']
        assert list(dialog.worker_swaps) == [False]
        assert surrounds == []
        items = _path_items(dialog)
        for arrow in expected:
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
        asked = list(dialog.worker_calls)
        start.click()
        assert list(dialog.worker_calls) == asked
        assert parent == []
        assert start.isEnabled() is False
        dialog.reject()

    _run(_DEFECTS, drive)


def test_hold_on_a_thread_blocks_the_gui_timer():
    """The spawn target's loop does not let this process paint."""
    import time
    import threading
    from weedlines_dialog import _burn_hold

    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    fired = []
    timer = QtCore.QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(lambda: fired.append(True))
    # The worker stays out of the loop until this thread is inside
    # processEvents. One call can still return before that loop starts.
    ready = threading.Event()

    def run():
        ready.wait()
        _burn_hold(20000000)

    worker = threading.Thread(target=run)
    worker.start()
    blocked = 0.0
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        del fired[:]
        timer.start(0)
        ready.set()
        started = time.monotonic()
        app.processEvents()
        elapsed = time.monotonic() - started
        if elapsed > blocked:
            blocked = elapsed
        if fired and elapsed > 0.05:
            break
        if not worker.is_alive():
            break
    worker.join(timeout=5)
    assert worker.is_alive() is False
    assert fired == [True]
    assert blocked > 0.05


def test_figure_check_hold_lets_the_gui_timer_fire(monkeypatch):
    import inspect
    import weedlines_dialog as dialog_mod

    fired = []
    real_spawn = dialog_mod._spawn_ask

    def wrapped(request, hold, pausing, cancelled):
        assert hold == dialog_mod._ASK_HOLD
        assert hold
        proc, conn = real_spawn(request, hold, pausing, cancelled)
        assert proc._start_method == 'spawn'
        dialog = _visible_dialog()
        assert dialog is not None and dialog.isVisible() is True
        timer = QtCore.QTimer(dialog)
        timer.setSingleShot(True)

        def mark():
            fired.append(dialog.isVisible() is True and proc.is_alive())

        timer.timeout.connect(mark)
        timer.start(0)
        timers = getattr(dialog, '_hold_timers', None)
        if timers is None:
            timers = []
            dialog._hold_timers = timers
        timers.append(timer)
        return proc, conn

    monkeypatch.setattr(dialog_mod, '_spawn_ask', wrapped)
    old = dialog_mod._ASK_HOLD
    dialog_mod._ASK_HOLD = 8000000

    def drive(dialog):
        assert all(frame.function != '_shown' for frame in inspect.stack())
        assert fired
        assert all(fired)
        assert dialog.isVisible() is True
        dialog.reject()

    try:
        _run(_CLEAR, drive)
    finally:
        dialog_mod._ASK_HOLD = old


def test_child_stdio_reaches_the_algorithm_log():
    import weedlines_dialog as dialog_mod

    old = dialog_mod._ASK_TRACE
    dialog_mod._ASK_TRACE = 'ask-stdio-marker'

    def drive(dialog):
        log = dialog.findChild(QtWidgets.QPlainTextEdit)
        assert log is not None
        text = log.toPlainText()
        assert text.count('ask-stdio-marker') >= 2
        dialog.reject()

    try:
        _run(_CLEAR, drive)
    finally:
        dialog_mod._ASK_TRACE = old


def test_focus_is_forwarded_and_not_painted():
    def drive(dialog):
        mark = dialog.focus_mark
        assert isinstance(mark, tuple) and len(mark) == 2
        outline, line = mark
        assert isinstance(outline, tuple) and outline
        assert all(
            isinstance(point, tuple) and len(point) == 2 for point in outline)
        assert line is None or (
            isinstance(line, tuple) and len(line) == 2)
        for item in _path_items(dialog):
            pen = _pen_hex(item)
            brush = _brush_hex(item)
            assert pen not in ('#7a5cff', '#15803d')
            assert brush not in ('#7a5cff', '#15803d')
        dialog.reject()

    _run(_CLEAR, drive)
