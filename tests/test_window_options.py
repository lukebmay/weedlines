# -*- coding: utf-8 -*-
"""Option history on the weedlines window. No Inkscape."""
from __future__ import division

import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest

try:
    from weedlib.qt import QT_BINDING, load_widgets
    QtCore, QtGui, QtWidgets = load_widgets()
    if QT_BINDING == 'enaml':
        from enaml.qt.QtTest import QTest
    else:
        QTest = __import__(
            QT_BINDING + '.QtTest', fromlist=['QTest']).QTest
except Exception as exc:
    pytest.skip('Qt cannot load: %s' % exc, allow_module_level=True)

_EXT_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'extensions', 'inkscape'))
if _EXT_DIR not in sys.path:
    sys.path.insert(0, _EXT_DIR)

from weedlines_dialog import run_weedlines_dialog  # noqa: E402

_SURROUND = 'Surround and Conquer'
_SCALE = 8
_LIGHT = '#e6e6e6'
_DARK = '#cfcfcf'

_RECT = [{
    'id': 'panel',
    'd': 'M 0,0 L 40,0 L 40,30 L 0,30 Z',
    'closed': [True],
    'fill': '#112233',
}]


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


def _spin(dialog, name):
    widget = dialog.findChild(QtWidgets.QDoubleSpinBox, name)
    assert widget is not None, name
    return widget


def _edit(dialog, name):
    widget = dialog.findChild(QtWidgets.QLineEdit, name)
    assert widget is not None, name
    return widget


def _color_setting(dialog, name):
    widget = dialog.findChild(QtWidgets.QPushButton, name)
    assert widget is not None, name
    return widget


def _pick_color(dialog, name, color):
    button = _color_setting(dialog, name)

    def choose():
        opened = [
            picker for picker in dialog.findChildren(
                QtWidgets.QColorDialog, 'color-picker')
            if picker.isVisible()
        ]
        assert len(opened) == 1, name
        opened[0].setCurrentColor(QtGui.QColor(color))
        opened[0].accept()

    QtCore.QTimer.singleShot(0, choose)
    button.click()
    return button


def _label(dialog, name):
    widget = dialog.findChild(QtWidgets.QLabel, name)
    assert widget is not None, name
    return widget


def _output_label(dialog):
    found = [
        label for label in dialog.findChildren(QtWidgets.QLabel)
        if label.text() == 'Output layer'
    ]
    assert len(found) == 1
    return found[0]


def _assert_knobs(dialog, mode):
    cut = mode in ('frame', 'grid', 'island-hop')
    pairs = (
        (_label(dialog, 'padding-label'), _spin(dialog, 'padding'), cut),
        (_label(dialog, 'spacing-label'),
         _spin(dialog, 'spacing'), mode == 'grid'),
        (_label(dialog, 'collar-label'),
         _spin(dialog, 'collar'), mode == 'island-hop'),
        (_output_label(dialog), _edit(dialog, 'layer-name'), cut),
        (_label(dialog, 'surround-distance-label'),
         _spin(dialog, 'surround-distance'), mode == _SURROUND),
        (_label(dialog, 'join-gap-label'),
         _spin(dialog, 'join-gap'), mode == _SURROUND),
    )
    for label, field, show in pairs:
        assert label.isVisible() is show, (mode, label.text(), show)
        assert field.isVisible() is show, (mode, field.objectName(), show)


def _chord(widget, key, modifiers):
    widget.setFocus(QtCore.Qt.OtherFocusReason)
    QtWidgets.QApplication.instance().processEvents()
    QTest.keyClick(widget, key, modifiers)
    QtWidgets.QApplication.instance().processEvents()


def _undo_at(widget):
    _chord(widget, QtCore.Qt.Key_Z, QtCore.Qt.ControlModifier)


def _redo_at(widget):
    _chord(widget, QtCore.Qt.Key_Y, QtCore.Qt.ControlModifier)


def _redo_shift_at(widget):
    _chord(
        widget,
        QtCore.Qt.Key_Z,
        QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier)


def _commit_text(edit, text):
    edit.setText(text)
    edit.editingFinished.emit()
    return edit


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
    raise AssertionError('ask did not finish')


def _pump_until(predicate, timeout=20):
    import time
    app = QtWidgets.QApplication.instance()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents(QtCore.QEventLoop.AllEvents, 30)
        if predicate():
            return
    raise AssertionError('timed out')


def _run(records, drive, **kwargs):
    app = QtWidgets.QApplication.instance()
    if app is None:
        QtWidgets.QApplication([])
    kwargs.setdefault('display_unit', 'mm')
    kwargs.setdefault('user_unit_scale', 1.0 / 25.4)

    def ready(dialog):
        timer = QtCore.QTimer(dialog)
        timer.setSingleShot(True)
        timer.timeout.connect(dialog.reject)
        timer.start(20000)
        drive(dialog)

    return run_weedlines_dialog(records, ready=ready, quit_app=False, **kwargs)


def _view(dialog):
    widget = dialog.findChild(QtWidgets.QGraphicsView, 'preview')
    assert widget is not None
    return widget


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


def _stroked_paths(dialog):
    found = []
    for item in _view(dialog).scene().items():
        reader = getattr(item, 'path', None)
        if not callable(reader):
            continue
        try:
            path = reader()
        except TypeError:
            continue
        if not hasattr(path, 'elementCount') or path.isEmpty():
            continue
        pen = item.pen()
        if pen.style() == QtCore.Qt.NoPen or pen.color().alpha() == 0:
            continue
        count = path.elementCount()
        start = path.elementAt(0)
        end = path.elementAt(count - 1)
        found.append((
            pen.color().name().lower(),
            count,
            round(start.x, 3),
            round(start.y, 3),
            round(end.x, 3),
            round(end.y, 3),
        ))
    return sorted(found)


def _cut_lines(dialog):
    found = []
    for item in _view(dialog).scene().items():
        reader = getattr(item, 'line', None)
        if not callable(reader) or callable(getattr(item, 'path', None)):
            continue
        line = reader()
        found.append((
            round(line.x1(), 3),
            round(line.y1(), 3),
            round(line.x2(), 3),
            round(line.y2(), 3),
        ))
    return sorted(found)


def test_undo_redo_committed_mode_length_layer_and_color():
    def drive(dialog):
        texts = {
            button.text()
            for button in dialog.findChildren(QtWidgets.QPushButton)
        }
        assert 'Undo' not in texts
        assert 'Redo' not in texts
        mode = _mode_box(dialog)
        assert mode.currentData() == _SURROUND
        _assert_knobs(dialog, _SURROUND)

        _set_mode(dialog, 'frame')
        assert mode.currentData() == 'frame'
        _assert_knobs(dialog, 'frame')
        _undo_at(mode)
        assert mode.currentData() == _SURROUND
        _assert_knobs(dialog, _SURROUND)
        _redo_at(mode)
        assert mode.currentData() == 'frame'
        _assert_knobs(dialog, 'frame')

        padding = _spin(dialog, 'padding')
        shown = padding.value()
        assert shown == pytest.approx(4.0 / 25.4, abs=1e-3)
        assert shown != pytest.approx(4.0)
        assert padding.suffix().strip() == 'in'
        padding.setValue(1.0)
        assert padding.value() == pytest.approx(1.0)
        _undo_at(padding)
        assert padding.value() == pytest.approx(shown, abs=1e-3)
        assert padding.value() != pytest.approx(4.0)
        assert mode.currentData() == 'frame'
        _redo_shift_at(padding)
        assert padding.value() == pytest.approx(1.0)
        assert padding.suffix().strip() == 'in'

        layer = _edit(dialog, 'layer-name')
        assert layer.text() == 'Weed lines'
        _commit_text(layer, 'Peel')
        assert layer.text() == 'Peel'
        _undo_at(mode)
        assert layer.text() == 'Weed lines'
        assert padding.value() == pytest.approx(1.0)
        _redo_at(mode)
        assert layer.text() == 'Peel'

        color = _color_setting(dialog, 'weed-line-color')
        assert color.property('color') == '#FF0000'
        _pick_color(dialog, 'weed-line-color', '#00ff00')
        assert color.property('color') == '#00FF00'
        assert color.text() == '#00FF00'
        _undo_at(mode)
        assert color.property('color') == '#FF0000'
        assert color.text() == '#FF0000'
        assert layer.text() == 'Peel'
        _redo_at(mode)
        assert color.property('color') == '#00FF00'
        assert mode.currentData() == 'frame'
        _assert_knobs(dialog, 'frame')

        _button(dialog, 'start').click()
        _pump_until(lambda: bool(dialog.solver_args))
        padding_arg, _spacing, _collar = dialog.solver_args[-1]
        assert padding_arg == pytest.approx([25.4, 25.4, 25.4, 25.4])
        assert padding_arg != pytest.approx([1.0, 1.0, 1.0, 1.0])
        assert padding_arg != pytest.approx([shown, shown, shown, shown])
        dialog.reject()

    _run(
        _RECT,
        drive,
        display_unit='in',
        user_unit_scale=1.0 / 25.4,
        defaults={'padding': 4.0},
    )


def test_uncommitted_color_undoes_inside_the_picker():
    rect = QtCore.QRectF(-2, -2, 44, 34)
    center = (20.0, 15.0)

    def drive(dialog):
        mode = _mode_box(dialog)
        _set_mode(dialog, 'frame')
        assert mode.currentData() == 'frame'
        view = _view(dialog)
        _button(dialog, 'swap').click()
        _wait_idle(dialog)
        before = _at(view, rect, center[0], center[1])
        color = _color_setting(dialog, 'checkerboard-light')
        assert color.property('color') == '#E6E6E6'

        def edit_picker():
            opened = [
                picker for picker in dialog.findChildren(
                    QtWidgets.QColorDialog, 'color-picker')
                if picker.isVisible()
            ]
            assert len(opened) == 1
            picker = opened[0]
            field = None
            for edit in picker.findChildren(QtWidgets.QLineEdit):
                if edit.text().startswith('#'):
                    field = edit
                    break
            assert field is not None
            field.setFocus(QtCore.Qt.OtherFocusReason)
            QtWidgets.QApplication.instance().processEvents()
            field.selectAll()
            QTest.keyClicks(field, '#010101')
            QtWidgets.QApplication.instance().processEvents()
            assert field.text().lower() == '#010101'
            assert color.property('color') == '#E6E6E6'
            assert _at(view, rect, center[0], center[1]) == before
            _undo_at(field)
            assert field.text().lower() == '#e6e6e6'
            assert color.property('color') == '#E6E6E6'
            assert mode.currentData() == 'frame'
            assert _at(view, rect, center[0], center[1]) == before
            picker.reject()

        QtCore.QTimer.singleShot(0, edit_picker)
        color.click()
        assert color.property('color') == '#E6E6E6'
        assert color.text() == '#E6E6E6'
        assert mode.currentData() == 'frame'
        assert _at(view, rect, center[0], center[1]) == before
        _undo_at(mode)
        assert mode.currentData() == _SURROUND
        assert color.property('color') == '#E6E6E6'
        dialog.reject()

    _run(_RECT, drive)


def test_each_color_setting_opens_a_picker():
    names = (
        'checkerboard-light',
        'checkerboard-dark',
        'weed-line-color',
        'default-subject-color',
    )
    chosen = {
        'checkerboard-light': '#010101',
        'checkerboard-dark': '#020202',
        'weed-line-color': '#030303',
        'default-subject-color': '#040404',
    }
    arrows = ('#FF00FF', '#FF6A00', '#00E5FF')

    def drive(dialog):
        colored = [
            widget for widget in dialog.findChildren(QtWidgets.QWidget)
            if isinstance(widget.property('color'), str)
        ]
        assert {widget.objectName() for widget in colored} == set(names)
        for widget in colored:
            assert widget.property('color') not in arrows
            assert widget.text() not in arrows
        kept = {
            name: _color_setting(dialog, name).property('color')
            for name in names
        }
        for name in names:
            button = _pick_color(dialog, name, chosen[name])
            assert button.property('color') == chosen[name].upper()
            assert button.text() == chosen[name].upper()
            for other in names:
                if other == name:
                    continue
                assert _color_setting(dialog, other).property('color') == kept[other]
            kept[name] = button.property('color')
        dialog.reject()

    _run(_RECT, drive)


def test_committed_color_undo_restores_the_preview():
    rect = QtCore.QRectF(-2, -2, 44, 34)
    center = (20.0, 15.0)

    def drive(dialog):
        view = _view(dialog)
        _button(dialog, 'swap').click()
        _wait_idle(dialog)
        before = _at(view, rect, center[0], center[1])
        assert before in (_LIGHT, _DARK)
        light = _pick_color(dialog, 'checkerboard-light', '#010101')
        dark = _pick_color(dialog, 'checkerboard-dark', '#020202')
        assert light.property('color') == '#010101'
        assert light.text() == '#010101'
        assert dark.property('color') == '#020202'
        assert dark.text() == '#020202'
        assert _color_setting(dialog, 'weed-line-color').property('color') == '#FF0000'
        assert _color_setting(
            dialog, 'default-subject-color').property('color') == '#FFFFFF'
        assert _at(view, rect, center[0], center[1]) in ('#010101', '#020202')
        _undo_at(light)
        _undo_at(light)
        assert light.property('color') == '#E6E6E6'
        assert light.text() == '#E6E6E6'
        assert dark.property('color') == '#CFCFCF'
        assert dark.text() == '#CFCFCF'
        assert _at(view, rect, center[0], center[1]) == before
        _redo_at(light)
        _redo_at(light)
        assert light.property('color') == '#010101'
        assert dark.property('color') == '#020202'
        assert _at(view, rect, center[0], center[1]) in ('#010101', '#020202')
        dialog.reject()

    _run(_RECT, drive)


def test_busy_run_does_not_take_a_color():
    names = (
        'checkerboard-light',
        'checkerboard-dark',
        'weed-line-color',
        'default-subject-color',
    )

    def drive(dialog):
        _set_mode(dialog, 'frame')
        colors = {name: _color_setting(dialog, name) for name in names}
        before = {
            name: button.property('color') for name, button in colors.items()
        }
        _button(dialog, 'start').click()
        for button in colors.values():
            assert button.isEnabled() is False
        seen = []

        def watch():
            opened = [
                picker for picker in dialog.findChildren(
                    QtWidgets.QColorDialog, 'color-picker')
                if picker.isVisible()
            ]
            seen.append(opened)

        for _name, button in colors.items():
            QtCore.QTimer.singleShot(0, watch)
            button.click()
        QtWidgets.QApplication.instance().processEvents()
        assert seen == [[], [], [], []]
        for name, button in colors.items():
            assert button.property('color') == before[name]
        dialog.reject()

    _run(_RECT, drive)


def test_undo_after_swap_does_not_swap_back():
    rect = QtCore.QRectF(-2, -2, 44, 34)
    center = (20.0, 15.0)

    def drive(dialog):
        mode = _mode_box(dialog)
        _set_mode(dialog, 'frame')
        view = _view(dialog)
        assert _at(view, rect, center[0], center[1]) == '#112233'
        swaps_before = len(dialog.worker_swaps)
        _button(dialog, 'swap').click()
        _wait_idle(dialog)
        assert dialog.worker_swaps[-1] is True
        assert len(dialog.worker_swaps) == swaps_before + 1
        assert _at(view, rect, center[0], center[1]) in (_LIGHT, _DARK)
        swaps = list(dialog.worker_swaps)
        calls = len(dialog.worker_calls)
        _undo_at(mode)
        _wait_idle(dialog)
        assert mode.currentData() == _SURROUND
        assert list(dialog.worker_swaps) == swaps
        assert len(dialog.worker_calls) == calls
        assert _at(view, rect, center[0], center[1]) in (_LIGHT, _DARK)
        dialog.reject()

    _run(_RECT, drive)


def test_undo_does_not_remove_a_surround():
    def drive(dialog):
        mode = _mode_box(dialog)
        _set_mode(dialog, 'frame')
        _set_mode(dialog, _SURROUND)
        _button(dialog, 'start').click()
        _wait_idle(dialog)
        assert dialog.surround_args
        asked = len(dialog.surround_args)
        strokes = _stroked_paths(dialog)
        assert strokes
        assert _button(dialog, 'apply').isEnabled() is False
        _undo_at(mode)
        _wait_idle(dialog)
        assert mode.currentData() == 'frame'
        _assert_knobs(dialog, 'frame')
        assert len(dialog.surround_args) == asked
        assert _stroked_paths(dialog) == strokes
        assert _button(dialog, 'apply').isEnabled() is False
        _redo_at(mode)
        assert mode.currentData() == _SURROUND
        _assert_knobs(dialog, _SURROUND)
        assert len(dialog.surround_args) == asked
        assert _stroked_paths(dialog) == strokes

        color = _pick_color(dialog, 'weed-line-color', '#0000ff')
        assert color.property('color') == '#0000FF'
        assert len(dialog.surround_args) == asked
        _undo_at(mode)
        _wait_idle(dialog)
        assert color.property('color') == '#FF0000'
        assert mode.currentData() == _SURROUND
        assert len(dialog.surround_args) == asked
        assert _stroked_paths(dialog) == strokes
        assert _button(dialog, 'apply').isEnabled() is False
        dialog.reject()

    _run(_RECT, drive)


def test_undo_does_not_remove_a_cut():
    def drive(dialog):
        _set_mode(dialog, 'frame')
        _button(dialog, 'start').click()
        apply_btn = _button(dialog, 'apply')
        _pump_until(lambda: apply_btn.isEnabled())
        cuts = _cut_lines(dialog)
        assert cuts
        asked = len(dialog.solver_args)
        log = dialog.findChild(QtWidgets.QPlainTextEdit)
        assert log is not None
        before = log.toPlainText()
        assert before
        color = _pick_color(dialog, 'weed-line-color', '#0000ff')
        assert color.property('color') == '#0000FF'
        _undo_at(_mode_box(dialog))
        _wait_idle(dialog)
        assert color.property('color') == '#FF0000'
        assert _cut_lines(dialog) == cuts
        assert len(dialog.solver_args) == asked
        assert apply_btn.isEnabled() is True
        assert log.toPlainText().startswith(before)
        dialog.reject()

    _run(_RECT, drive)


_INK_LABEL = '{http://www.inkscape.org/namespaces/inkscape}label'
_JOB = [
    _RECT[0],
    {
        'id': 'weedlines-correction-arrow',
        'd': 'M 7,7 L 8,9',
        'closed': [False],
        'fill': 'none',
    },
]
_FRAME = {'mode': 'frame'}


def _include_box(dialog):
    widget = dialog.findChild(QtWidgets.QCheckBox, 'include-original')
    assert widget is not None
    return widget


def _paths(group):
    found = []
    for el in list(group):
        tag = el.tag
        if isinstance(tag, str) and tag.rsplit('}', 1)[-1] == 'path':
            found.append(el)
    return found


def _apply_choice(dialog, include):
    _pump_until(lambda: dialog.worker_calls.count('piece_border') >= 1)
    _wait_idle(dialog)
    assert 'classify' in dialog.worker_calls
    box = _include_box(dialog)
    assert box.isChecked() is False
    if include:
        box.setChecked(True)
    start = _button(dialog, 'start')
    assert start.isEnabled() is True
    start.click()
    apply_btn = _button(dialog, 'apply')
    _pump_until(lambda: apply_btn.isEnabled())
    _wait_idle(dialog)
    import importlib
    import weedlib
    piece_mod = importlib.import_module('weedlib.piece_border')
    seen = {'n': 0}
    real = piece_mod.piece_border

    def boom(*args, **kwargs):
        seen['n'] += 1
        return real(*args, **kwargs)

    piece_mod.piece_border = boom
    weedlib.piece_border = boom
    try:
        apply_btn.click()
    finally:
        piece_mod.piece_border = real
        weedlib.piece_border = real
    return seen


def _write_choice(tmp_path, monkeypatch, chosen):
    import weedlines_job as JOB
    from weedlib.svg_paths import weed_path_to_open_d_list
    monkeypatch.setattr(JOB, 'cache_dir', lambda: str(tmp_path))
    weed, layer_name, color = chosen
    JOB.write_result(
        layer_name,
        weed_path_to_open_d_list(weed),
        weed_line_color=color,
        border_d_list=chosen.border_d_list,
        records=chosen.records,
    )
    return os.path.join(str(tmp_path), 'last_result.svg')


def _result_group(svg_path):
    import weedlines_svg as SVG
    group = SVG.load_result_svg_groups(svg_path)
    assert group is not None
    return group


def test_include_original_design_joins_the_option_history():
    def drive(dialog):
        for mode in (_SURROUND, 'frame', 'grid', 'island-hop'):
            _set_mode(dialog, mode)
            box = _include_box(dialog)
            label = _label(dialog, 'include-original-label')
            assert label.text() == 'Include original design'
            assert label.isVisible() is True
            assert box.isVisible() is True
            assert box.isChecked() is False
        box = _include_box(dialog)
        box.setChecked(True)
        assert box.isChecked() is True
        _undo_at(box)
        assert box.isChecked() is False
        _redo_at(box)
        assert box.isChecked() is True
        assert _mode_box(dialog).currentData() == 'island-hop'
        dialog.reject()

    _run(_JOB, drive)


def test_default_apply_omits_original_design(tmp_path, monkeypatch):
    seen = {}

    def drive(dialog):
        seen['rebuild'] = _apply_choice(dialog, False)

    chosen = _run(_JOB, drive, defaults=dict(_FRAME))
    assert seen['rebuild']['n'] == 0
    assert chosen.records is None
    assert chosen.border_d_list
    svg_path = _write_choice(tmp_path, monkeypatch, chosen)
    group = _result_group(svg_path)
    assert [el.get(_INK_LABEL) for el in list(group)] == [
        'Border', 'Weed lines',
    ]
    from weedlib.svg_paths import weed_path_to_open_d_list
    cuts = _paths(list(group)[1])
    assert [el.get('d') for el in cuts] == weed_path_to_open_d_list(chosen[0])
    assert [el.get('d') for el in _paths(list(group)[0])] == [
        d for d in chosen.border_d_list if d
    ]
    with open(svg_path, encoding='utf-8') as fh:
        text = fh.read()
    assert 'Original design' not in text
    assert 'weedlines-correction' not in text
    assert text.count('inkscape:groupmode="layer"') == 1


def test_include_original_design_copies_the_records(tmp_path, monkeypatch):
    def drive(dialog):
        _apply_choice(dialog, True)

    chosen = _run(_JOB, drive, defaults=dict(_FRAME))
    assert chosen.records == _JOB
    svg_path = _write_choice(tmp_path, monkeypatch, chosen)
    group = _result_group(svg_path)
    assert [el.get(_INK_LABEL) for el in list(group)] == [
        'Border', 'Weed lines', 'Original design',
    ]
    paths = _paths(list(group)[-1])
    assert [el.get('id') for el in paths] == ['panel']
    assert [el.get('d') for el in paths] == [_RECT[0]['d']]
    with open(svg_path, encoding='utf-8') as fh:
        text = fh.read()
    assert 'weedlines-correction' not in text
    assert 'M 7,7 L 8,9' not in text
    from weedlib.svg_paths import weed_path_to_open_d_list
    cuts = _paths(list(group)[1])
    assert [el.get('d') for el in cuts] == weed_path_to_open_d_list(chosen[0])


def test_host_passes_the_included_groups(tmp_path, monkeypatch):
    import json
    import weedlines_host
    import weedlines_dialog
    import weedlines_job as JOB
    from weedlib.qt import QPainterPath
    monkeypatch.setattr(JOB, 'cache_dir', lambda: str(tmp_path))
    path = QPainterPath()
    path.moveTo(0, 0)
    path.lineTo(12, 0)

    class _Chosen(tuple):
        def __new__(cls):
            result = tuple.__new__(cls, (path, 'Weed lines', '#ABCDEF'))
            result.border_d_list = ['M 1,1 L 4,1']
            result.records = list(_JOB)
            return result

    monkeypatch.setattr(
        weedlines_dialog, 'run_weedlines_dialog', lambda *_a, **_k: _Chosen())

    def information(*_args, **_kwargs):
        return None

    monkeypatch.setattr(QtWidgets.QMessageBox, 'information', information)
    job_path = os.path.join(str(tmp_path), 'job.json')
    with open(job_path, 'w', encoding='utf-8') as fh:
        json.dump({
            'keep_d': 'M 0,0 L 8,0',
            'records': list(_JOB),
            'defaults': dict(_FRAME),
            'doc_attrs': {'width': '20', 'height': '20', 'viewBox': '0 0 20 20'},
        }, fh)
    assert weedlines_host.main([job_path]) == 0
    group = _result_group(os.path.join(str(tmp_path), 'last_result.svg'))
    assert [el.get(_INK_LABEL) for el in list(group)] == [
        'Border', 'Weed lines', 'Original design',
    ]
    assert [el.get('d') for el in _paths(list(group)[0])] == ['M 1,1 L 4,1']
    assert [el.get('id') for el in _paths(list(group)[-1])] == ['panel']
    assert [el.get('d') for el in _paths(list(group)[-1])] == [_RECT[0]['d']]


def test_inline_path_writes_the_same_groups():
    inkex_dir = '/usr/share/inkscape/extensions'
    if (os.path.isdir(os.path.join(inkex_dir, 'inkex'))
            and inkex_dir not in sys.path):
        sys.path.insert(0, inkex_dir)
    inkex = pytest.importorskip('inkex')
    from inkex import PathElement
    import weedlines
    svg = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape">\n'
        '  <g id="layer1" inkscape:groupmode="layer" '
        'inkscape:label="Layer 1">\n'
        '    <path id="person-path" d="M 2,3 L 4,5"/>\n'
        '  </g>\n'
        '</svg>\n'
    )
    root = inkex.load_svg(svg.encode('utf-8')).getroot()
    weedlines._add_weed_layer_from_d(
        root, inkex, PathElement, ['M 0,0 L 12,0'], 'Weed lines', '#123456',
        border_d_list=['M 1,1 L 4,1'], records=list(_JOB))
    assert root.getElementById('person-path').get('d') == 'M 2,3 L 4,5'
    assert len(list(root.getElementById('person-path').getparent())) == 1
    group = root.getElementById('weedlines')
    assert [el.get(_INK_LABEL) for el in group] == [
        'Border', 'Weed lines', 'Original design',
    ]
    assert root.getElementById('weedlines-border-0000').get('d') == (
        'M 1,1 L 4,1')
    cut = root.getElementById('weed-cut-0000')
    assert cut.getparent().get('id') == 'weedlines-cuts'
    assert cut.get('d') == 'M 0,0 L 12,0'
    assert root.getElementById('panel').get('d') == _RECT[0]['d']
    assert root.getElementById('weedlines-correction-arrow') is None
    bare = inkex.load_svg(svg.encode('utf-8')).getroot()
    weedlines._add_weed_layer_from_d(
        bare, inkex, PathElement, ['M 0,0 L 12,0'], 'Weed lines')
    assert [el.get(_INK_LABEL) for el in bare.getElementById('weedlines')] == [
        'Border', 'Weed lines',
    ]
