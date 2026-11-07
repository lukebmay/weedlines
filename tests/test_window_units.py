# -*- coding: utf-8 -*-
"""Window surround units: display unit, join gap, and padding. No Inkscape."""
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
