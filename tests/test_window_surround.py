# -*- coding: utf-8 -*-
"""Window surround: preview, distance, and approval. No Inkscape."""
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


def _named_spin(dialog, name):
    widget = dialog.findChild(QtWidgets.QDoubleSpinBox, name)
    assert widget is not None, name
    return widget


def _collar(dialog):
    spins = [
        spin for spin in dialog.findChildren(QtWidgets.QDoubleSpinBox)
        if spin.objectName() not in (
            'padding', 'spacing', 'surround-distance')
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

    def wrapped(subject, distance):
        paths = real(subject, distance)
        calls.append((subject, float(distance), paths))
        return paths

    monkeypatch.setattr(weedlib, 'build_surrounds', wrapped)
    return calls


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
    calls = _watch(monkeypatch)
    subject = _regions(_CLEAR, swap=False).subject
    view_rect = QtCore.QRectF(-4, -4, 40, 40)
    stroke = (17.0, 7.5)
    band = (17.0, 9.0)
    letter = (17.0, 20.0)

    def drive(dialog):
        assert calls
        assert _same_path(calls[0][0], subject)
        assert calls[0][1] == pytest.approx(_FIVE_PERCENT)
        spin = _distance_spin(dialog)
        label = _distance_label(dialog)
        change = _button(dialog, 'change-surround')
        assert label.text() == 'Surround distance'
        assert label.isVisible() and spin.isVisible() and change.isVisible()
        assert change.text() == 'Change surround'
        assert spin.value() == pytest.approx(_FIVE_PERCENT)
        assert spin.minimum() == 0.0
        assert spin.value() != pytest.approx(0.05 * 80.0)
        _assert_strokes(dialog, calls[-1][2], _WEED)
        view = _view(dialog)
        assert _at(view, view_rect, stroke[0], stroke[1]) == _WEED
        assert _at(view, view_rect, band[0], band[1]) in (_LIGHT, _DARK)
        assert _at(view, view_rect, letter[0], letter[1]) == '#112233'

        asked = len(calls)
        paths = calls[-1][2]
        _named_spin(dialog, 'padding').setValue(9.0)
        _named_spin(dialog, 'spacing').setValue(12.0)
        _collar(dialog).setValue(1.5)
        assert len(calls) == asked
        _assert_strokes(dialog, paths, _WEED)

        spin.setValue(6.0)
        assert len(calls) > asked
        assert calls[-1][1] == pytest.approx(6.0)
        assert spin.value() == pytest.approx(6.0)
        _assert_strokes(dialog, calls[-1][2], _WEED)
        assert not _same_path(calls[-1][2][0], paths[0])

        asked = len(calls)
        _set_mode(dialog, 'frame')
        assert len(calls) == asked
        assert label.isVisible() is False
        assert spin.isVisible() is False
        assert change.isVisible() is False
        assert _WEED not in _pen_colors(dialog)
        assert spin.value() == pytest.approx(6.0)

        _set_mode(dialog, _SURROUND)
        assert len(calls) > asked
        assert calls[-1][1] == pytest.approx(6.0)
        assert spin.value() == pytest.approx(6.0)
        assert label.isVisible() and spin.isVisible() and change.isVisible()
        _assert_strokes(dialog, calls[-1][2], _WEED)

        spin.setValue(-3.0)
        assert spin.value() == pytest.approx(0.0)
        assert calls[-1][1] == pytest.approx(0.0)
        assert calls[-1][1] >= 0.0

        swapped = _regions(_CLEAR, swap=True).subject
        asked = len(calls)
        _button(dialog, 'swap').click()
        assert len(calls) > asked
        assert _same_path(calls[-1][0], swapped)
        assert calls[-1][1] == pytest.approx(0.0)
        _assert_strokes(dialog, calls[-1][2], _WEED)
        dialog.reject()

    _run(
        _CLEAR,
        drive,
        width='1000mm',
        height='9mm',
        view_box='0 0 1000 9',
    )


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

    def wrapped(subject, distance):
        calls.append((subject, distance))
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
        assert label.isVisible() and spin.isVisible()
        start = _button(dialog, 'start')
        box = _mode_box(dialog)
        for index in range(box.count()):
            box.setCurrentIndex(index)
            assert start.isEnabled() is False
        _set_mode(dialog, _SURROUND)
        spin.setValue(3.0)
        _button(dialog, 'swap').click()
        _button(dialog, 'change-surround').click()
        start.click()
        assert start.isEnabled() is False
        assert _button(dialog, 'apply').isEnabled() is False
        assert calls == []
        assert cuts == []
        assert _WEED not in _pen_colors(dialog)
        dialog.reject()

    _run(_OPEN, drive)


def test_start_approves_the_showing_surrounds(monkeypatch, tmp_path):
    import weedlib
    import weedlines_job as JOB
    calls = _watch(monkeypatch)
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
        change = _button(dialog, 'change-surround')
        apply_btn = _button(dialog, 'apply')
        assert apply_btn.isEnabled() is False
        shown = calls[-1][2]
        asked = len(calls)
        _button(dialog, 'start').click()
        assert dialog.isVisible() is True
        assert cuts == []
        assert writes == []
        assert apply_btn.isEnabled() is False
        assert spin.isEnabled() is False
        assert change.isEnabled() is True
        assert len(calls) == asked
        _assert_strokes(dialog, shown, _WEED)
        apply_btn.click()
        assert dialog.isVisible() is True

        edit = dialog.findChild(QtWidgets.QLineEdit, 'weed-line-color')
        assert edit is not None
        edit.setText('#123456')
        edit.editingFinished.emit()
        assert spin.isEnabled() is False
        assert len(calls) == asked
        _assert_strokes(dialog, shown, '#123456')

        change.click()
        assert spin.isEnabled() is True
        assert len(calls) > asked
        assert calls[-1][1] == pytest.approx(spin.value())
        _assert_strokes(dialog, calls[-1][2], '#123456')

        spin.setValue(8.0)
        assert calls[-1][1] == pytest.approx(8.0)
        _assert_strokes(dialog, calls[-1][2], '#123456')
        assert cuts == []
        asked = len(calls)
        _button(dialog, 'start').click()
        assert spin.isEnabled() is False
        assert apply_btn.isEnabled() is False
        assert cuts == []
        assert len(calls) == asked

        swapped = _regions(_CLEAR, swap=True).subject
        asked = len(calls)
        _button(dialog, 'swap').click()
        assert spin.isEnabled() is True
        assert len(calls) > asked
        assert _same_path(calls[-1][0], swapped)
        assert cuts == []

        _button(dialog, 'start').click()
        assert spin.isEnabled() is False
        asked = len(calls)
        _set_mode(dialog, 'frame')
        assert spin.isEnabled() is True
        assert spin.isVisible() is False
        assert len(calls) == asked
        assert '#123456' not in _pen_colors(dialog)
        _set_mode(dialog, _SURROUND)
        assert spin.isEnabled() is True
        assert len(calls) > asked
        assert cuts == []
        assert writes == []
        assert apply_btn.isEnabled() is False
        dialog.reject()

    result = _run(_CLEAR, drive)
    assert result == (None, None, None)
    assert cuts == []
    assert writes == []
    assert list(tmp_path.iterdir()) == []
