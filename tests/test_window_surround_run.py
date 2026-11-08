# -*- coding: utf-8 -*-
"""Window surround run: hold, pause, Clear All, and the log. No Inkscape."""
from __future__ import division

import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest

try:
    from weedlib.qt import QPainterPath, load_widgets
    QtCore, QtGui, QtWidgets = load_widgets()
except Exception as exc:
    pytest.skip('Qt cannot load: %s' % exc, allow_module_level=True)

_EXT_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'extensions', 'inkscape'))
if _EXT_DIR not in sys.path:
    sys.path.insert(0, _EXT_DIR)

from weedlib.figures import classify_figures, subject_weed_regions  # noqa: E402
from weedlines_dialog import run_weedlines_dialog  # noqa: E402
from weedlines_svg import _INCHES_PER_UNIT  # noqa: E402

_SURROUND = 'Surround and Conquer'
_LIGHT = '#e6e6e6'
_DARK = '#cfcfcf'
_WEED = '#ff0000'
_SCALE = 8

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
_FIVE_PERCENT = 2.5


def _button(dialog, name):
    widget = dialog.findChild(QtWidgets.QPushButton, name)
    assert widget is not None, name
    return widget


def _mode_box(dialog):
    widget = dialog.findChild(QtWidgets.QComboBox, 'mode')
    assert widget is not None
    return widget


def _set_mode(dialog, mode):
    box = _mode_box(dialog)
    for index in range(box.count()):
        if box.itemData(index) == mode:
            box.setCurrentIndex(index)
            return box
    raise AssertionError('missing mode %s' % mode)


def _distance_label(dialog):
    found = [
        label for label in dialog.findChildren(QtWidgets.QLabel)
        if label.text() == 'Surround distance'
    ]
    assert len(found) == 1
    return found[0]


def _distance_spin(dialog):
    widget = dialog.findChild(QtWidgets.QDoubleSpinBox, 'surround-distance')
    assert widget is not None
    return widget


def _join_label(dialog):
    found = [
        label for label in dialog.findChildren(QtWidgets.QLabel)
        if label.text() == 'Join gap'
    ]
    assert len(found) == 1
    return found[0]


def _join_spin(dialog):
    return _named_spin(dialog, 'join-gap')


def _display_box(dialog):
    widget = dialog.findChild(QtWidgets.QComboBox, 'display-unit')
    assert widget is not None
    return widget


def _set_display_unit(dialog, unit):
    box = _display_box(dialog)
    index = box.findData(unit)
    assert index >= 0, unit
    box.setCurrentIndex(index)
    return box


def _length_label(dialog, name):
    widget = dialog.findChild(QtWidgets.QLabel, name)
    assert widget is not None, name
    return widget


def _named_spin(dialog, name):
    widget = dialog.findChild(QtWidgets.QDoubleSpinBox, name)
    assert widget is not None, name
    return widget


def _collar(dialog):
    return _named_spin(dialog, 'collar')


def _line_edit(dialog, name):
    widget = dialog.findChild(QtWidgets.QLineEdit, name)
    assert widget is not None, name
    return widget


def _label_text(dialog, text):
    found = [
        label for label in dialog.findChildren(QtWidgets.QLabel)
        if label.text() == text
    ]
    assert len(found) == 1, text
    return found[0]


_COLOR_NAMES = (
    'checkerboard-light',
    'checkerboard-dark',
    'weed-line-color',
    'default-subject-color',
)


def _assert_mode_knobs(dialog, mode):
    cut = mode in ('frame', 'grid', 'island-hop')
    pairs = (
        (_length_label(dialog, 'padding-label'),
         _named_spin(dialog, 'padding'), cut),
        (_length_label(dialog, 'spacing-label'),
         _named_spin(dialog, 'spacing'), mode == 'grid'),
        (_length_label(dialog, 'collar-label'),
         _named_spin(dialog, 'collar'), mode == 'island-hop'),
        (_label_text(dialog, 'Output layer'),
         _line_edit(dialog, 'layer-name'), cut),
        (_distance_label(dialog), _distance_spin(dialog), mode == _SURROUND),
        (_join_label(dialog), _join_spin(dialog), mode == _SURROUND),
    )
    for label, field, show in pairs:
        assert label.isVisible() is show, (mode, label.text())
        assert field.isVisible() is show, (mode, field.objectName())
    assert _mode_box(dialog).isVisible() is True
    assert _button(dialog, 'swap').isVisible() is True
    for name in _COLOR_NAMES:
        assert _line_edit(dialog, name).isVisible() is True, name


def _view(dialog):
    widget = dialog.findChild(QtWidgets.QGraphicsView, 'preview')
    assert widget is not None
    return widget


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


def _path_items(scene):
    items = []
    for item in scene.items():
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


def _take_path(items, expected):
    for index, item in enumerate(items):
        if _same_path(item.path(), expected):
            return items.pop(index)
    raise AssertionError('missing surround path with %s elements' % (
        expected.elementCount(),))


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


def _checker_z(items):
    found = []
    for item in items:
        if _pen_hex(item) is not None or _brush_hex(item) is not None:
            continue
        path = item.path()
        if path.isEmpty():
            continue
        found.append(item.zValue())
    assert found, 'checkerboard missing'
    return min(found)


def _assert_strokes(dialog, paths, color):
    assert paths
    items = _path_items(_view(dialog).scene())
    floor = _checker_z(items)
    for path in paths:
        item = _take_path(items, path)
        assert _pen_hex(item) == color.lower()
        assert _brush_hex(item) is None
        assert item.zValue() > floor
    for item in items:
        if _is_border(item.path(), dialog):
            continue
        assert _pen_hex(item) != color.lower()


def _render(view, rect):
    width = round(rect.width() * _SCALE)
    height = round(rect.height() * _SCALE)
    image = QtGui.QImage(
        width, height, QtGui.QImage.Format_ARGB32_Premultiplied)
    image.fill(view.backgroundBrush().color())
    painter = QtGui.QPainter(image)
    painter.setRenderHint(QtGui.QPainter.Antialiasing, False)
    view.scene().render(
        painter,
        QtCore.QRectF(0, 0, width, height),
        QtCore.QRectF(rect))
    painter.end()
    return image


def _at(view, rect, x, y):
    image = _render(view, rect)
    px = round((x - rect.x()) * _SCALE)
    py = round((y - rect.y()) * _SCALE)
    assert 0 <= px < image.width(), (x, y, px)
    assert 0 <= py < image.height(), (x, y, py)
    return image.pixelColor(px, py).name().lower()


def _watch(monkeypatch):
    import weedlib
    real = weedlib.build_surrounds
    calls = []

    def wrapped(subject, distance, join_gap=0.0):
        paths = real(subject, distance, join_gap)
        calls.append((
            subject, float(distance), float(join_gap), paths))
        return paths

    monkeypatch.setattr(weedlib, 'build_surrounds', wrapped)
    return calls, real


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


def _run_busy(dialog):
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


def _wait_idle(dialog, timeout=20):
    import time
    app = QtWidgets.QApplication.instance()
    deadline = time.monotonic() + timeout
    quiet = 0
    while time.monotonic() < deadline:
        app.processEvents(QtCore.QEventLoop.AllEvents, 30)
        if _run_busy(dialog):
            quiet = 0
            continue
        quiet += 1
        if quiet >= 2:
            return
    raise AssertionError('surround ask did not finish')


def _pump_until(predicate, timeout=20):
    import time
    app = QtWidgets.QApplication.instance()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents(QtCore.QEventLoop.AllEvents, 30)
        if predicate():
            return
    raise AssertionError('timed out')


def _status(dialog):
    label = dialog.findChild(QtWidgets.QLabel, 'status')
    assert label is not None
    return label


def _spinner(dialog):
    widget = dialog.findChild(QtWidgets.QProgressBar, 'spinner')
    assert widget is not None
    return widget


def _visible_step_labels(dialog):
    shown = []
    for name in ('step-cut-label', 'step-surround-label', 'step-conquer-label'):
        label = dialog.findChild(QtWidgets.QLabel, name)
        assert label is not None, name
        if label.isVisible():
            shown.append(label.text())
    return shown


def _assert_no_retired(dialog):
    assert dialog.findChild(QtWidgets.QPushButton, 'change-surround') is None
    for button in dialog.findChildren(QtWidgets.QPushButton):
        assert not button.text().startswith('Cancel'), button.text()
        assert button.text() != 'Change surround'
    hint = dialog.findChild(QtWidgets.QLabel, 'hint')
    assert hint is not None
    assert 'Cancel' not in hint.text()


def _click_text(dialog, text):
    found = [
        button for button in dialog.findChildren(QtWidgets.QPushButton)
        if button.isVisible() and button.text() == text
    ]
    assert len(found) == 1, text
    found[0].click()


def _regions(records, swap):
    return subject_weed_regions(classify_figures(records).figures, swap=swap)

def _border_paths(dialog):
    import importlib
    piece_border = importlib.import_module('weedlib.piece_border').piece_border
    inner = float(dialog.lengths['inner'])
    width = float(dialog.lengths['border'])
    found = []
    for swap in (False, True):
        subject = _regions(_CLEAR, swap=swap).subject
        found.extend(piece_border(subject, inner, width))
    return found


def _is_border(path, dialog):
    if path.elementCount() != 5:
        return False
    for border in _border_paths(dialog):
        if _same_path(path, border):
            return True
    return False


def _pen_colors(dialog):
    found = []
    for item in _path_items(_view(dialog).scene()):
        if _is_border(item.path(), dialog):
            continue
        color = _pen_hex(item)
        if color is not None:
            found.append(color)
    return found

def _keep_timer(dialog, timer):
    timers = getattr(dialog, '_hold_timers', None)
    if timers is None:
        timers = []
        dialog._hold_timers = timers
    timers.append(timer)

def test_surround_hold_drops_a_newer_distance_join_and_swap(monkeypatch):
    """A GUI timer fires before the surround is painted. The older result is dropped."""
    import weedlib
    import weedlines_dialog as dialog_mod

    fired = []
    painted_early = []
    cuts = []
    real = weedlib.build_surrounds

    def parent_saw(*_args, **_kwargs):
        raise AssertionError('parent saw build_surrounds')

    def refuse(*_args, **_kwargs):
        cuts.append('cut')
        raise AssertionError('generate_weeds ran')

    monkeypatch.setattr(weedlib, 'build_surrounds', parent_saw)
    monkeypatch.setattr(weedlib, 'generate_weeds', refuse)
    real_spawn = dialog_mod._spawn_ask

    def wrapped_spawn(request, hold, pausing, cancelled):
        proc, conn = real_spawn(request, hold, pausing, cancelled)
        if request.get('kind') != 'surround':
            return proc, conn
        assert hold
        assert proc._start_method == 'spawn'
        dialog = _visible_dialog()
        assert dialog is not None and dialog.isVisible()
        if getattr(dialog, '_hold_armed', False):
            return proc, conn
        dialog._hold_armed = True
        timer = QtCore.QTimer(dialog)
        timer.setSingleShot(True)

        def mark():
            alive = dialog.isVisible() and proc.is_alive()
            fired.append(bool(alive))
            painted_early.append(_WEED in _pen_colors(dialog))
            if not alive:
                return
            _distance_spin(dialog).setValue(6.0)
            _join_spin(dialog).setValue(1.25)
            _button(dialog, 'swap').click()

        timer.timeout.connect(mark)
        timer.start(0)
        _keep_timer(dialog, timer)
        return proc, conn

    monkeypatch.setattr(dialog_mod, '_spawn_ask', wrapped_spawn)
    old_hold = dialog_mod._ASK_HOLD
    dialog_mod._ASK_HOLD = 8000000

    def drive(dialog):
        apply_btn = _button(dialog, 'apply')
        assert apply_btn.isEnabled() is False
        _button(dialog, 'start').click()
        _pump_until(lambda: bool(fired), timeout=10)
        assert fired == [True]
        assert painted_early == [False]
        assert dialog.isVisible() is True
        assert apply_btn.isEnabled() is False
        assert cuts == []
        _wait_idle(dialog, timeout=30)
        assert dialog.isVisible() is True
        assert apply_btn.isEnabled() is False
        assert cuts == []
        assert len(dialog.surround_args) == 2
        assert dialog.surround_args[0][0] == pytest.approx(_FIVE_PERCENT)
        assert dialog.surround_args[0][1] == pytest.approx(6.35)
        assert dialog.surround_args[-1][0] == pytest.approx(6.0)
        assert dialog.surround_args[-1][1] == pytest.approx(1.25)
        inner = dialog.lengths['inner']
        fresh = real(
            _regions(_CLEAR, swap=True).subject, 6.0, 1.25,
            inner_distance=inner)
        stale = real(
            _regions(_CLEAR, swap=False).subject, _FIVE_PERCENT, 6.35,
            inner_distance=inner)
        # The newer distance is outside the inner rectangle, so the
        # clip removes it. The older surround must not stay up.
        assert fresh == []
        assert stale
        assert _WEED not in _pen_colors(dialog)
        assert dialog.worker_swaps[-1] is True
        assert 'surrounds' in dialog.worker_calls
        dialog.reject()

    try:
        _run(_CLEAR, drive)
    finally:
        dialog_mod._ASK_HOLD = old_hold
    assert cuts == []

def test_clear_all_discards_the_surround_and_does_not_kill(monkeypatch):
    import weedlines_dialog as dialog_mod

    killed = []
    real_spawn = dialog_mod._spawn_ask

    def wrapped_spawn(request, hold, pausing, cancelled):
        proc, conn = real_spawn(request, hold, pausing, cancelled)
        if request.get('kind') != 'surround':
            return proc, conn

        def deny(*_args, **_kwargs):
            killed.append('kill')
            raise AssertionError('child killed')

        proc.terminate = deny
        proc.kill = deny
        return proc, conn

    monkeypatch.setattr(dialog_mod, '_spawn_ask', wrapped_spawn)
    old_hold = dialog_mod._ASK_HOLD
    dialog_mod._ASK_HOLD = 8000000

    def drive(dialog):
        color = dialog.findChild(QtWidgets.QLineEdit, 'weed-line-color')
        assert color is not None
        _button(dialog, 'start').click()
        _pump_until(
            lambda: _status(dialog).text().startswith('working'),
            timeout=5)
        assert _spinner(dialog).isVisible() is True
        assert _button(dialog, 'start').text() == 'Restart'
        assert _button(dialog, 'start').isEnabled() is False
        _button(dialog, 'clear-all').click()
        _wait_idle(dialog)
        assert killed == []
        assert _WEED not in _pen_colors(dialog)
        assert dialog.isVisible() is True
        assert _button(dialog, 'start').text() == 'Start'
        assert _button(dialog, 'start').isEnabled() is True
        assert _status(dialog).text() == 'ready'
        assert _spinner(dialog).isVisible() is False
        assert _mode_box(dialog).currentData() == _SURROUND
        assert color.property('color') == '#FF0000'
        assert _button(dialog, 'apply').isEnabled() is False
        asked = len(dialog.surround_args)
        _distance_spin(dialog).setValue(4.0)
        _wait_idle(dialog)
        assert len(dialog.surround_args) == asked
        assert _WEED not in _pen_colors(dialog)
        dialog.reject()

    try:
        _run(_CLEAR, drive)
    finally:
        dialog_mod._ASK_HOLD = old_hold

def test_pause_holds_the_surround_until_resume(monkeypatch):
    import weedlines_dialog as dialog_mod

    paused = []
    real_spawn = dialog_mod._spawn_ask

    def wrapped_spawn(request, hold, pausing, cancelled):
        proc, conn = real_spawn(request, hold, pausing, cancelled)
        if request.get('kind') != 'surround':
            return proc, conn
        dialog = _visible_dialog()
        assert dialog is not None
        timer = QtCore.QTimer(dialog)
        timer.setSingleShot(True)

        def mark():
            if dialog.isVisible() and proc.is_alive():
                _click_text(dialog, 'Pause')
                paused.append(proc.is_alive())

        timer.timeout.connect(mark)
        timer.start(0)
        _keep_timer(dialog, timer)
        return proc, conn

    monkeypatch.setattr(dialog_mod, '_spawn_ask', wrapped_spawn)
    old_hold = dialog_mod._ASK_HOLD
    dialog_mod._ASK_HOLD = 8000000

    def drive(dialog):
        try:
            _button(dialog, 'start').click()
            _pump_until(lambda: bool(paused), timeout=10)
            assert paused == [True]
            assert _status(dialog).text().startswith('paused')
            assert _spinner(dialog).isVisible() is False
            assert _button(dialog, 'start').text() == 'Restart'
            assert _button(dialog, 'start').isEnabled() is False
            assert dialog.isVisible() is True
            _pump_until(
                lambda: dialog.worker_calls.count('surrounds') >= 1,
                timeout=10)
            assert _WEED not in _pen_colors(dialog)
            app = QtWidgets.QApplication.instance()
            for _ in range(4):
                app.processEvents(QtCore.QEventLoop.AllEvents, 50)
            assert _WEED not in _pen_colors(dialog)
            assert _run_busy(dialog) is True
            assert dialog.isVisible() is True
            _click_text(dialog, 'Resume')
            _wait_idle(dialog)
            assert _WEED in _pen_colors(dialog)
            assert _button(dialog, 'apply').isEnabled() is False
            assert _status(dialog).text() == 'done'
            assert _spinner(dialog).isVisible() is False
            assert _button(dialog, 'start').text() == 'Restart'
            assert dialog.isVisible() is True
        finally:
            if dialog.isVisible() and _run_busy(dialog):
                resume = [
                    button for button in dialog.findChildren(
                        QtWidgets.QPushButton)
                    if button.isVisible() and button.text() == 'Resume'
                ]
                if resume:
                    resume[0].click()
                _wait_idle(dialog)
            if dialog.isVisible():
                dialog.reject()

    try:
        _run(_CLEAR, drive)
    finally:
        dialog_mod._ASK_HOLD = old_hold

def test_surround_stdio_reaches_the_algorithm_log():
    import weedlines_dialog as dialog_mod

    old_trace = dialog_mod._ASK_TRACE

    def drive(dialog):
        dialog_mod._ASK_TRACE = 'surround-stdio-marker'
        _button(dialog, 'start').click()
        _wait_idle(dialog)
        log = dialog.findChild(QtWidgets.QPlainTextEdit)
        assert log is not None
        assert log.toPlainText().count('surround-stdio-marker') >= 2
        dialog.reject()

    try:
        _run(_CLEAR, drive)
    finally:
        dialog_mod._ASK_TRACE = old_trace

def test_conquer_start_does_not_cut_and_restart_repeats(monkeypatch):
    import weedlib
    calls, real = _watch(monkeypatch)
    cuts = []

    def refuse(*_args, **_kwargs):
        cuts.append('cut')
        raise AssertionError('generate_weeds ran')

    monkeypatch.setattr(weedlib, 'generate_weeds', refuse)

    def drive(dialog):
        _assert_no_retired(dialog)
        assert _visible_step_labels(dialog) == ['Surround', 'Conquer']
        mark = dialog.findChild(QtWidgets.QLabel, 'step-conquer-mark')
        assert mark is not None and mark.text() == 'left' and mark.isVisible()
        conquer = _button(dialog, 'conquer-start')
        assert conquer.isEnabled() is False
        asked = list(dialog.worker_calls)
        conquer.click()
        assert list(dialog.worker_calls) == asked
        assert dialog.solver_keeps == []
        assert cuts == []
        assert calls == []

        _button(dialog, 'start').click()
        _wait_idle(dialog)
        assert cuts == []
        assert calls == []
        assert 'solver' not in dialog.worker_calls
        assert _button(dialog, 'start').text() == 'Restart'
        assert _status(dialog).text() == 'done'
        assert _spinner(dialog).isVisible() is False
        assert _visible_step_labels(dialog) == ['Surround', 'Conquer']
        paths = real(
            _regions(_CLEAR, swap=False).subject,
            _distance_spin(dialog).value(),
            _join_spin(dialog).value())
        _assert_strokes(dialog, paths, _WEED)
        asked_n = len(dialog.surround_args)
        _button(dialog, 'start').click()
        _wait_idle(dialog)
        assert len(dialog.surround_args) == asked_n + 1
        assert cuts == []
        assert calls == []
        assert 'solver' not in dialog.worker_calls
        assert _status(dialog).text() == 'done'
        assert _button(dialog, 'start').text() == 'Restart'
        _assert_strokes(dialog, paths, _WEED)
        dialog.reject()

    _run(_CLEAR, drive)
    assert cuts == []
