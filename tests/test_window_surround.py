# -*- coding: utf-8 -*-
"""Window surround: mode, preview, distance, and start. No Inkscape."""
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


def _color_setting(dialog, name):
    widget = dialog.findChild(QtWidgets.QPushButton, name)
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
        assert _color_setting(dialog, name).isVisible() is True, name


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

def test_mode_knobs_follow_the_mode():
    def drive(dialog):
        _assert_mode_knobs(dialog, _SURROUND)
        distance = _distance_spin(dialog)
        join = _join_spin(dialog)
        pad = _named_spin(dialog, 'padding')
        space = _named_spin(dialog, 'spacing')
        collar = _named_spin(dialog, 'collar')
        layer = _line_edit(dialog, 'layer-name')
        distance.setValue(7.0)
        join.setValue(3.0)

        _set_mode(dialog, 'frame')
        _assert_mode_knobs(dialog, 'frame')
        assert distance.value() == pytest.approx(7.0)
        assert join.value() == pytest.approx(3.0)
        pad.setValue(9.0)
        layer.setText('Peel')

        _set_mode(dialog, 'grid')
        _assert_mode_knobs(dialog, 'grid')
        assert pad.value() == pytest.approx(9.0)
        assert layer.text() == 'Peel'
        space.setValue(12.0)

        _set_mode(dialog, 'island-hop')
        _assert_mode_knobs(dialog, 'island-hop')
        assert pad.value() == pytest.approx(9.0)
        assert layer.text() == 'Peel'
        assert space.value() == pytest.approx(12.0)
        collar.setValue(1.5)

        _set_mode(dialog, _SURROUND)
        _assert_mode_knobs(dialog, _SURROUND)
        assert distance.value() == pytest.approx(7.0)
        assert join.value() == pytest.approx(3.0)
        assert pad.value() == pytest.approx(9.0)
        assert space.value() == pytest.approx(12.0)
        assert collar.value() == pytest.approx(1.5)
        assert layer.text() == 'Peel'

        _set_mode(dialog, 'frame')
        _assert_mode_knobs(dialog, 'frame')
        assert pad.value() == pytest.approx(9.0)
        assert layer.text() == 'Peel'
        assert space.value() == pytest.approx(12.0)
        assert collar.value() == pytest.approx(1.5)

        _set_mode(dialog, 'grid')
        _assert_mode_knobs(dialog, 'grid')
        assert space.value() == pytest.approx(12.0)
        assert pad.value() == pytest.approx(9.0)
        assert layer.text() == 'Peel'

        _set_mode(dialog, 'island-hop')
        _assert_mode_knobs(dialog, 'island-hop')
        assert collar.value() == pytest.approx(1.5)
        assert layer.text() == 'Peel'
        assert pad.value() == pytest.approx(9.0)

        _set_mode(dialog, _SURROUND)
        _assert_mode_knobs(dialog, _SURROUND)
        assert distance.value() == pytest.approx(7.0)
        assert join.value() == pytest.approx(3.0)
        dialog.reject()

    _run(_CLEAR, drive)

    def drive_grid(dialog):
        assert _mode_box(dialog).currentData() == 'grid'
        _assert_mode_knobs(dialog, 'grid')
        dialog.reject()

    _run(_CLEAR, drive_grid, defaults={'mode': 'grid'})

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
        _assert_no_retired(dialog)
        assert label.text() == 'Surround distance'
        assert join_label.text() == 'Join gap'
        assert label.isVisible() and spin.isVisible()
        assert join_label.isVisible() and join.isVisible()
        assert _visible_step_labels(dialog) == ['Surround', 'Conquer']
        conquer = _button(dialog, 'conquer-start')
        assert conquer.text() == 'Start'
        assert conquer.isEnabled() is False
        assert _status(dialog).text() == 'ready'
        assert _spinner(dialog).isVisible() is False
        assert _button(dialog, 'start').text() == 'Start'
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
            assert _visible_step_labels(dialog) == [{
                'frame': 'Frame',
                'grid': 'Grid',
                'island-hop': 'Island hop',
            }[mode]]
            assert _button(dialog, 'conquer-start').isVisible() is False
            assert spin.value() == pytest.approx(_FIVE_PERCENT)
            assert join.value() == pytest.approx(6.35)
        _set_mode(dialog, _SURROUND)
        assert calls == []
        assert label.isVisible() and join_label.isVisible()
        assert _visible_step_labels(dialog) == ['Surround', 'Conquer']

        _named_spin(dialog, 'padding').setValue(9.0)
        _named_spin(dialog, 'spacing').setValue(12.0)
        _collar(dialog).setValue(1.5)
        assert calls == []

        _button(dialog, 'start').click()
        _wait_idle(dialog)
        assert len(dialog.surround_args) == 1
        assert dialog.surround_args[0][0] == pytest.approx(_FIVE_PERCENT)
        assert dialog.surround_args[0][1] == pytest.approx(6.35)
        assert dialog.worker_calls.count('surrounds') == 1
        assert _button(dialog, 'start').text() == 'Restart'
        assert _status(dialog).text() == 'done'
        assert _spinner(dialog).isVisible() is False
        assert _visible_step_labels(dialog) == ['Surround', 'Conquer']
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
        widened = real(
            subject, 6.0, 6.35, inner_distance=dialog.lengths['inner'])
        # Past the inner rectangle the clip removes the surround.
        assert widened == []
        assert _WEED not in _pen_colors(dialog)

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
        assert _visible_step_labels(dialog) == ['Frame']
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
        assert label.isVisible() and spin.isVisible()
        assert join_label.isVisible() and join.isVisible()
        assert _visible_step_labels(dialog) == ['Surround', 'Conquer']
        _assert_strokes(dialog, real(swapped, 0.0, 0.0), _WEED)

        asked = len(dialog.surround_args)
        _button(dialog, 'clear-all').click()
        assert _button(dialog, 'start').text() == 'Start'
        assert _status(dialog).text() == 'ready'
        assert _spinner(dialog).isVisible() is False
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
        _assert_strokes(dialog, real(
            swapped, 4.0, 2.0, inner_distance=dialog.lengths['inner']), _WEED)
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
        _assert_no_retired(dialog)
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
        assert _button(dialog, 'start').text() == 'Restart'
        assert _status(dialog).text() == 'done'
        assert _spinner(dialog).isVisible() is False
        assert 'solver' not in dialog.worker_calls
        shown = real(subject, spin.value(), join.value())
        _assert_strokes(dialog, shown, _WEED)
        apply_btn.click()
        assert dialog.isVisible() is True

        edit = _color_setting(dialog, 'weed-line-color')

        def choose():
            opened = [
                picker for picker in dialog.findChildren(
                    QtWidgets.QColorDialog, 'color-picker')
                if picker.isVisible()
            ]
            assert len(opened) == 1
            opened[0].setCurrentColor(QtGui.QColor('#123456'))
            opened[0].accept()

        QtCore.QTimer.singleShot(0, choose)
        edit.click()
        assert calls == []
        assert len(dialog.surround_args) == 1
        assert spin.isEnabled() is True
        assert join.isEnabled() is True
        _assert_strokes(dialog, shown, '#123456')

        kept_distance = spin.value()
        kept_join = join.value()
        _button(dialog, 'clear-all').click()
        assert _button(dialog, 'start').text() == 'Start'
        assert _status(dialog).text() == 'ready'
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
