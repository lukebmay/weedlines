# -*- coding: utf-8 -*-
"""Window surround: preview, distance, and join gap. No Inkscape."""
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
    spins = [
        spin for spin in dialog.findChildren(QtWidgets.QDoubleSpinBox)
        if spin.objectName() not in (
            'padding', 'spacing', 'surround-distance', 'join-gap')
    ]
    assert len(spins) == 1
    return spins[0]


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


def _click_text(dialog, text):
    found = [
        button for button in dialog.findChildren(QtWidgets.QPushButton)
        if button.isVisible() and button.text() == text
    ]
    assert len(found) == 1, text
    found[0].click()


def _regions(records, swap):
    return subject_weed_regions(classify_figures(records).figures, swap=swap)


@pytest.mark.parametrize('defaults, expected', [
    (None, _SURROUND),
    ({}, _SURROUND),
    ({'mode': ''}, _SURROUND),
    ({'mode': '   '}, _SURROUND),
    ({'mode': 'Surround and Conquer'}, _SURROUND),
    ({'mode': 'sUrround AND conquer'}, _SURROUND),
    ({'mode': 'frame'}, 'frame'),
    ({'mode': 'grid'}, 'grid'),
    ({'mode': 'island-hop'}, 'island-hop'),
    ({'mode': 'region'}, 'frame'),
])
def test_window_opens_on_the_named_mode(defaults, expected):
    def drive(dialog):
        box = _mode_box(dialog)
        assert box.currentData() == expected
        if expected == _SURROUND:
            assert box.currentText() == _SURROUND
        dialog.reject()

    kwargs = {}
    if defaults is not None:
        kwargs['defaults'] = defaults
    _run(_CLEAR, drive, **kwargs)


def test_clear_design_strokes_surrounds_and_follows_distance(monkeypatch):
    import weedlib
    calls, real = _watch(monkeypatch)
    cuts = []

    def refuse(*_args, **_kwargs):
        cuts.append('cut')
        raise AssertionError('generate_weeds ran')

    monkeypatch.setattr(weedlib, 'generate_weeds', refuse)
    subject = _regions(_CLEAR, swap=False).subject
    view_rect = QtCore.QRectF(-4, -4, 40, 40)
    stroke = (17.0, 7.5)
    band = (17.0, 9.0)
    letter = (17.0, 20.0)

    def drive(dialog):
        assert calls == []
        assert dialog.surround_args == []
        spin = _distance_spin(dialog)
        join = _join_spin(dialog)
        label = _distance_label(dialog)
        join_label = _join_label(dialog)
        change = _button(dialog, 'change-surround')
        assert label.text() == 'Surround distance'
        assert join_label.text() == 'Join gap'
        assert label.isVisible() and spin.isVisible() and change.isVisible()
        assert join_label.isVisible() and join.isVisible()
        assert change.text() == 'Change surround'
        assert spin.value() == pytest.approx(_FIVE_PERCENT)
        assert spin.minimum() == 0.0
        assert spin.value() != pytest.approx(0.05 * 80.0)
        assert join.value() == pytest.approx(6.35)
        assert join.minimum() == 0.0
        assert _WEED not in _pen_colors(dialog)

        spin.setValue(6.0)
        join.setValue(3.0)
        assert calls == []
        assert _WEED not in _pen_colors(dialog)
        spin.setValue(_FIVE_PERCENT)
        join.setValue(6.35)
        _button(dialog, 'swap').click()
        _button(dialog, 'swap').click()
        assert calls == []
        assert _WEED not in _pen_colors(dialog)

        for mode in ('frame', 'grid', 'island-hop'):
            _set_mode(dialog, mode)
            assert calls == []
            assert label.isVisible() is False
            assert spin.isVisible() is False
            assert join_label.isVisible() is False
            assert join.isVisible() is False
            assert change.isVisible() is False
            assert spin.value() == pytest.approx(_FIVE_PERCENT)
            assert join.value() == pytest.approx(6.35)
        _set_mode(dialog, _SURROUND)
        assert calls == []
        assert label.isVisible() and join_label.isVisible() and change.isVisible()

        _named_spin(dialog, 'padding').setValue(9.0)
        _named_spin(dialog, 'spacing').setValue(12.0)
        _collar(dialog).setValue(1.5)
        assert calls == []

        _button(dialog, 'start').click()
        _wait_idle(dialog)
        assert calls == []
        assert len(dialog.surround_args) == 1
        assert dialog.surround_args[0][0] == pytest.approx(_FIVE_PERCENT)
        assert dialog.surround_args[0][1] == pytest.approx(6.35)
        assert dialog.worker_calls.count('surrounds') == 1
        paths = real(subject, _FIVE_PERCENT, 6.35)
        assert spin.isEnabled() is True
        assert join.isEnabled() is True
        assert _button(dialog, 'apply').isEnabled() is False
        _assert_strokes(dialog, paths, _WEED)
        view = _view(dialog)
        assert _at(view, view_rect, stroke[0], stroke[1]) == _WEED
        assert _at(view, view_rect, band[0], band[1]) in (_LIGHT, _DARK)
        assert _at(view, view_rect, letter[0], letter[1]) == '#112233'

        asked = len(dialog.surround_args)
        _named_spin(dialog, 'padding').setValue(8.0)
        _named_spin(dialog, 'spacing').setValue(11.0)
        _collar(dialog).setValue(2.0)
        assert calls == []
        assert len(dialog.surround_args) == asked
        _assert_strokes(dialog, paths, _WEED)

        spin.setValue(6.0)
        _wait_idle(dialog)
        assert calls == []
        assert len(dialog.surround_args) == asked + 1
        assert dialog.surround_args[-1][0] == pytest.approx(6.0)
        assert dialog.surround_args[-1][1] == pytest.approx(6.35)
        assert spin.value() == pytest.approx(6.0)
        widened = real(subject, 6.0, 6.35)
        _assert_strokes(dialog, widened, _WEED)
        assert not _same_path(widened[0], paths[0])

        asked = len(dialog.surround_args)
        join.setValue(9.0)
        _wait_idle(dialog)
        assert calls == []
        assert len(dialog.surround_args) == asked + 1
        assert dialog.surround_args[-1][0] == pytest.approx(6.0)
        assert dialog.surround_args[-1][1] == pytest.approx(9.0)

        join.setValue(-1.0)
        _wait_idle(dialog)
        assert join.value() == pytest.approx(0.0)
        assert dialog.surround_args[-1][1] == pytest.approx(0.0)
        assert dialog.surround_args[-1][1] >= 0.0

        spin.setValue(-3.0)
        _wait_idle(dialog)
        assert spin.value() == pytest.approx(0.0)
        assert dialog.surround_args[-1][0] == pytest.approx(0.0)
        assert dialog.surround_args[-1][0] >= 0.0

        swapped = _regions(_CLEAR, swap=True).subject
        asked = len(dialog.surround_args)
        _button(dialog, 'swap').click()
        _wait_idle(dialog)
        assert calls == []
        assert len(dialog.surround_args) == asked + 1
        assert dialog.surround_args[-1][0] == pytest.approx(0.0)
        assert dialog.surround_args[-1][1] == pytest.approx(0.0)
        _assert_strokes(dialog, real(swapped, 0.0, 0.0), _WEED)

        asked = len(dialog.surround_args)
        _set_mode(dialog, 'frame')
        assert calls == []
        assert len(dialog.surround_args) == asked
        assert label.isVisible() is False
        assert spin.isVisible() is False
        assert join_label.isVisible() is False
        assert join.isVisible() is False
        assert change.isVisible() is False
        assert _WEED not in _pen_colors(dialog)
        assert spin.value() == pytest.approx(0.0)
        assert join.value() == pytest.approx(0.0)

        _set_mode(dialog, _SURROUND)
        _wait_idle(dialog)
        assert calls == []
        assert len(dialog.surround_args) == asked + 1
        assert dialog.surround_args[-1][0] == pytest.approx(0.0)
        assert dialog.surround_args[-1][1] == pytest.approx(0.0)
        assert spin.value() == pytest.approx(0.0)
        assert join.value() == pytest.approx(0.0)
        assert label.isVisible() and spin.isVisible() and change.isVisible()
        assert join_label.isVisible() and join.isVisible()
        _assert_strokes(dialog, real(swapped, 0.0, 0.0), _WEED)

        asked = len(dialog.surround_args)
        change.click()
        assert calls == []
        assert len(dialog.surround_args) == asked
        assert spin.value() == pytest.approx(0.0)
        assert join.value() == pytest.approx(0.0)
        assert spin.isEnabled() is True
        assert join.isEnabled() is True
        assert _WEED not in _pen_colors(dialog)

        spin.setValue(4.0)
        join.setValue(2.0)
        assert calls == []
        assert len(dialog.surround_args) == asked
        assert spin.value() == pytest.approx(4.0)
        assert join.value() == pytest.approx(2.0)
        _set_mode(dialog, 'grid')
        _set_mode(dialog, _SURROUND)
        assert calls == []
        assert len(dialog.surround_args) == asked
        assert spin.value() == pytest.approx(4.0)
        assert join.value() == pytest.approx(2.0)

        _button(dialog, 'start').click()
        _wait_idle(dialog)
        assert calls == []
        assert len(dialog.surround_args) == asked + 1
        assert dialog.surround_args[-1][0] == pytest.approx(4.0)
        assert dialog.surround_args[-1][1] == pytest.approx(2.0)
        _assert_strokes(dialog, real(swapped, 4.0, 2.0), _WEED)
        assert _button(dialog, 'apply').isEnabled() is False
        assert cuts == []
        dialog.reject()

    _run(
        _CLEAR,
        drive,
        width='1000mm',
        height='9mm',
        view_box='0 0 1000 9',
    )
    assert cuts == []


def _pen_colors(dialog):
    found = []
    for item in _path_items(_view(dialog).scene()):
        color = _pen_hex(item)
        if color is not None:
            found.append(color)
    return found


def test_defect_paints_no_surround_and_disables_start(monkeypatch):
    import weedlib
    calls = []
    cuts = []

    def wrapped(subject, distance, join_gap=0.0):
        calls.append((subject, distance, join_gap))
        raise AssertionError('build_surrounds while a defect exists')

    def fake(*_args, **_kwargs):
        cuts.append('cut')
        out = QPainterPath()
        out.addRect(0, 0, 1, 1)
        return out

    monkeypatch.setattr(weedlib, 'build_surrounds', wrapped)
    monkeypatch.setattr(weedlib, 'generate_weeds', fake)

    def drive(dialog):
        assert calls == []
        assert _WEED not in _pen_colors(dialog)
        label = _distance_label(dialog)
        spin = _distance_spin(dialog)
        join_label = _join_label(dialog)
        join = _join_spin(dialog)
        assert label.isVisible() and spin.isVisible()
        assert join_label.isVisible() and join.isVisible()
        assert join_label.text() == 'Join gap'
        assert join.value() == pytest.approx(6.35)
        assert join.minimum() == 0.0
        start = _button(dialog, 'start')
        box = _mode_box(dialog)
        for index in range(box.count()):
            box.setCurrentIndex(index)
            assert start.isEnabled() is False
            surround = box.currentData() == _SURROUND
            assert label.isVisible() is surround
            assert spin.isVisible() is surround
            assert join_label.isVisible() is surround
            assert join.isVisible() is surround
        _set_mode(dialog, _SURROUND)
        spin.setValue(3.0)
        join.setValue(1.25)
        join.setValue(-4.0)
        assert spin.value() == pytest.approx(3.0)
        assert join.value() == pytest.approx(0.0)
        _button(dialog, 'swap').click()
        _button(dialog, 'change-surround').click()
        start.click()
        assert start.isEnabled() is False
        assert _button(dialog, 'apply').isEnabled() is False
        assert calls == []
        assert dialog.surround_args == []
        assert 'surrounds' not in dialog.worker_calls
        assert cuts == []
        assert _WEED not in _pen_colors(dialog)
        dialog.reject()

    _run(_OPEN, drive)


def test_start_paints_without_a_solver_or_a_result(monkeypatch, tmp_path):
    import weedlib
    import weedlines_job as JOB
    calls, real = _watch(monkeypatch)
    cuts = []
    writes = []

    def fake(*_args, **_kwargs):
        cuts.append('cut')
        out = QPainterPath()
        out.addRect(0, 0, 1, 1)
        return out

    def fail_write(*_args, **_kwargs):
        writes.append('write')
        raise AssertionError('result written')

    monkeypatch.setattr(weedlib, 'generate_weeds', fake)
    monkeypatch.setattr(JOB, 'write_result', fail_write)
    monkeypatch.setattr(JOB, 'write_correction_result', fail_write)
    monkeypatch.setattr(JOB, 'cache_dir', lambda: str(tmp_path))

    def drive(dialog):
        spin = _distance_spin(dialog)
        join = _join_spin(dialog)
        change = _button(dialog, 'change-surround')
        apply_btn = _button(dialog, 'apply')
        assert calls == []
        assert dialog.surround_args == []
        assert apply_btn.isEnabled() is False
        subject = _regions(_CLEAR, swap=False).subject
        _button(dialog, 'start').click()
        _wait_idle(dialog)
        assert dialog.isVisible() is True
        assert calls == []
        assert len(dialog.surround_args) == 1
        assert dialog.worker_calls.count('surrounds') == 1
        assert dialog.surround_args[0][0] == pytest.approx(spin.value())
        assert dialog.surround_args[0][1] == pytest.approx(join.value())
        assert dialog.surround_args[0][1] == pytest.approx(6.35)
        assert cuts == []
        assert writes == []
        assert apply_btn.isEnabled() is False
        assert spin.isEnabled() is True
        assert join.isEnabled() is True
        assert change.isEnabled() is True
        shown = real(subject, spin.value(), join.value())
        _assert_strokes(dialog, shown, _WEED)
        apply_btn.click()
        assert dialog.isVisible() is True

        edit = dialog.findChild(QtWidgets.QLineEdit, 'weed-line-color')
        assert edit is not None
        edit.setText('#123456')
        edit.editingFinished.emit()
        assert calls == []
        assert len(dialog.surround_args) == 1
        assert spin.isEnabled() is True
        assert join.isEnabled() is True
        _assert_strokes(dialog, shown, '#123456')

        kept_distance = spin.value()
        kept_join = join.value()
        change.click()
        assert calls == []
        assert len(dialog.surround_args) == 1
        assert spin.value() == pytest.approx(kept_distance)
        assert join.value() == pytest.approx(kept_join)
        assert spin.isEnabled() is True
        assert '#123456' not in _pen_colors(dialog)
        assert cuts == []
        assert writes == []
        assert apply_btn.isEnabled() is False
        dialog.reject()

    result = _run(_CLEAR, drive)
    assert result == (None, None, None)
    assert cuts == []
    assert writes == []
    assert list(tmp_path.iterdir()) == []


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
        fresh = real(_regions(_CLEAR, swap=True).subject, 6.0, 1.25)
        stale = real(_regions(_CLEAR, swap=False).subject, _FIVE_PERCENT, 6.35)
        _assert_strokes(dialog, fresh, _WEED)
        assert not _same_path(fresh[0], stale[0])
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

    def _cancel(dialog):
        found = [
            button for button in dialog.findChildren(QtWidgets.QPushButton)
            if button.isVisible() and button.text().startswith('Cancel')
        ]
        assert len(found) == 1
        found[0].click()

    def drive(dialog):
        _button(dialog, 'start').click()
        _pump_until(
            lambda: any(
                button.isVisible() and button.text().startswith('Cancel')
                for button in dialog.findChildren(QtWidgets.QPushButton)),
            timeout=5)
        _cancel(dialog)
        _wait_idle(dialog)
        assert killed == []
        assert _WEED not in _pen_colors(dialog)
        assert dialog.isVisible() is True
        assert _button(dialog, 'start').isEnabled() is True
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


def test_surround_forwards_focus_and_does_not_paint_it():
    def drive(dialog):
        dialog.focus_mark = None
        _button(dialog, 'start').click()
        _wait_idle(dialog)
        mark = dialog.focus_mark
        assert isinstance(mark, tuple) and len(mark) == 2
        outline, line = mark
        assert isinstance(outline, tuple) and outline
        assert all(
            isinstance(point, tuple) and len(point) == 2 for point in outline)
        assert line is None or (isinstance(line, tuple) and len(line) == 2)
        for item in _path_items(_view(dialog).scene()):
            assert _pen_hex(item) not in ('#7a5cff', '#15803d')
            assert _brush_hex(item) not in ('#7a5cff', '#15803d')
        dialog.reject()

    _run(_CLEAR, drive)


_LENGTH_LABELS = (
    ('surround-distance-label', 'Surround distance'),
    ('join-gap-label', 'Join gap'),
    ('padding-label', 'Padding'),
    ('spacing-label', 'Grid spacing'),
    ('collar-label', 'Collar (island-hop)'),
)


def _assert_length_labels(dialog):
    for name, text in _LENGTH_LABELS:
        label = _length_label(dialog, name)
        assert label.text() == text


def test_display_unit_converts_lengths_without_clamping():
    def drive(dialog):
        box = _display_box(dialog)
        assert box.currentData() == 'mm'
        assert box.findData('%') < 0
        assert box.findData('em') < 0
        assert box.findText('%') < 0
        assert box.findText('em') < 0
        _assert_length_labels(dialog)
        join = _join_spin(dialog)
        pad = _named_spin(dialog, 'padding')
        space = _named_spin(dialog, 'spacing')
        assert join.suffix().strip() == 'mm'
        assert pad.suffix().strip() == 'mm'
        assert join.value() == pytest.approx(6.35)
        assert pad.value() == pytest.approx(4.0)
        assert space.value() == pytest.approx(25.0)

        pad.setValue(200.0)
        _set_display_unit(dialog, 'px')
        shown_pad = 200.0 * 96.0 / 25.4
        assert pad.value() == pytest.approx(shown_pad, abs=1e-3)
        assert pad.value() > 200.0
        _assert_length_labels(dialog)
        assert pad.suffix().strip() == 'px'

        _set_display_unit(dialog, 'in')
        assert space.value() == pytest.approx(25.0 / 25.4, abs=1e-3)
        assert space.value() < 1.0
        assert join.value() == pytest.approx(0.25)
        assert pad.value() == pytest.approx(200.0 / 25.4, abs=1e-3)
        assert join.suffix().strip() == 'in'
        assert pad.suffix().strip() == 'in'
        _assert_length_labels(dialog)

        _button(dialog, 'start').click()
        _wait_idle(dialog)
        assert len(dialog.surround_args) == 1
        distance, join_gap = dialog.surround_args[0]
        assert distance == pytest.approx(_FIVE_PERCENT)
        assert join_gap == pytest.approx(6.35)
        assert _distance_spin(dialog).value() == pytest.approx(
            _FIVE_PERCENT / 25.4, abs=1e-3)
        assert join.value() == pytest.approx(0.25)
        dialog.reject()

    _run(_CLEAR, drive)


def test_no_scale_join_gap_is_a_quarter_inch_in_px():
    def drive(dialog):
        box = _display_box(dialog)
        assert box.currentData() == 'px'
        join = _join_spin(dialog)
        assert join.value() == pytest.approx(24.0)
        assert join.value() != pytest.approx(6.35)
        _button(dialog, 'start').click()
        _wait_idle(dialog)
        assert len(dialog.surround_args) == 1
        distance, join_gap = dialog.surround_args[0]
        assert distance == pytest.approx(_FIVE_PERCENT)
        assert join_gap == pytest.approx(24.0)
        assert join_gap != pytest.approx(6.35)
        dialog.reject()

    _run(_CLEAR, drive, display_unit=None, user_unit_scale=None)


def test_centimeter_scale_join_gap_is_not_the_millimeter_count():
    scale = 1.0 / 2.54
    expected = 0.25 / scale

    def drive(dialog):
        assert _display_box(dialog).currentData() == 'cm'
        join = _join_spin(dialog)
        assert join.value() == pytest.approx(expected)
        assert join.value() != pytest.approx(6.35)
        _button(dialog, 'start').click()
        _wait_idle(dialog)
        distance, join_gap = dialog.surround_args[0]
        assert distance == pytest.approx(_FIVE_PERCENT)
        assert join_gap == pytest.approx(expected)
        assert join_gap != pytest.approx(6.35)
        dialog.reject()

    _run(_CLEAR, drive, display_unit='cm', user_unit_scale=scale)


def test_padding_converts_on_screen_and_stays_for_the_solver():
    def drive(dialog):
        pad = _named_spin(dialog, 'padding')
        space = _named_spin(dialog, 'spacing')
        collar = _collar(dialog)
        assert pad.value() == pytest.approx(4.0 / 25.4, abs=1e-3)
        assert pad.value() != pytest.approx(4.0)
        assert space.value() == pytest.approx(25.0 / 25.4, abs=1e-3)
        assert space.value() != pytest.approx(25.0)
        assert collar.value() == pytest.approx(4.0 / 25.4, abs=1e-3)
        assert collar.value() != pytest.approx(4.0)
        assert pad.suffix().strip() == 'in'
        _set_mode(dialog, 'frame')
        assert _button(dialog, 'start').isEnabled() is True
        _button(dialog, 'start').click()
        _pump_until(lambda: bool(dialog.solver_args))
        padding, spacing, collar_arg = dialog.solver_args[-1]
        assert padding == pytest.approx([4.0, 4.0, 4.0, 4.0])
        assert spacing == pytest.approx(25.0)
        assert collar_arg == pytest.approx(4.0)
        dialog.reject()

    _run(
        _CLEAR,
        drive,
        display_unit='in',
        user_unit_scale=1.0 / 25.4,
        defaults={'padding': 4.0},
    )


_LINEAR_UNITS = ('px', 'in', 'ft', 'mm', 'cm', 'm', 'pt', 'pc')


@pytest.mark.parametrize('unit', ('yd', 'q', 'km'))
def test_dropdown_rejects_yd_q_and_km(unit):
    def drive(dialog):
        box = _display_box(dialog)
        assert dialog.display_unit == unit
        assert box.currentData() == 'px'
        choices = [box.itemData(index) for index in range(box.count())]
        labels = [box.itemText(index) for index in range(box.count())]
        assert unit not in choices
        assert unit not in labels
        assert 'yd' not in choices and 'q' not in choices
        assert 'km' not in choices
        assert tuple(choices) == _LINEAR_UNITS
        assert unit in _INCHES_PER_UNIT
        assert _join_spin(dialog).value() == pytest.approx(24.0)
        dialog.reject()

    _run(
        _CLEAR,
        drive,
        display_unit=unit,
        user_unit_scale=1.0 / 25.4,
    )


@pytest.mark.parametrize('unit', ('%', 'em'))
def test_dropdown_rejects_percent_and_em(unit):
    def drive(dialog):
        box = _display_box(dialog)
        assert box.currentData() == 'px'
        assert box.findData(unit) < 0
        assert box.findData('%') < 0
        assert box.findData('em') < 0
        assert _join_spin(dialog).value() == pytest.approx(24.0)
        dialog.reject()

    _run(
        _CLEAR,
        drive,
        display_unit=unit,
        user_unit_scale=1.0 / 25.4,
    )
