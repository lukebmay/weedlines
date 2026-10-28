# -*- coding: utf-8 -*-
"""Window preview: subject, weed area, arrows, swap, and plugin colors."""
from __future__ import division

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

from weedlib.arrows import build_arrow_paths  # noqa: E402
from weedlib.figures import classify_figures, subject_weed_regions  # noqa: E402
from weedlib import padded_work_rect  # noqa: E402
from weedlines_dialog import run_weedlines_dialog  # noqa: E402

_SCALE = 8
_LIGHT = '#e6e6e6'
_DARK = '#cfcfcf'
_WEED = '#ff0000'
_SUBJECT = '#ffffff'
_ORANGE = '#e07020'
_BACKGROUND_FALLBACK = '#1e1e1e'

_FRAME = 'M 0,0 L 80,0 L 80,50 L 0,50 Z'
_LETTER_A = 'M 10,10 L 24,10 L 24,30 L 10,30 Z'
_LETTER_B = 'M 50,12 L 68,12 L 68,32 L 50,32 Z'
_BAND = (
    _FRAME
    + ' M 12,12 L 28,12 L 28,28 L 12,28 Z'
    + ' M 50,18 L 66,18 L 66,36 L 50,36 Z'
)
_LEFT = 'M 0,0 L 10,0 L 10,10 L 0,10 Z'
_RIGHT = 'M 20,0 L 30,0 L 30,10 L 20,10 Z'
_PANEL = 'M 0,0 L 50,0 L 50,50 L 0,50 Z'
_OPEN_TRI = 'M 0,0 L 10,0 L 10,10'
_BLOCK = 'M 8,-2 L 14,-2 L 14,4 L 8,4 Z'
_CROSS = (
    'M 100,100 L 110,100 L 110,110 L 100,110 Z '
    'M 105,105 L 115,105 L 115,115 L 105,115 Z'
)

_LETTERS = [
    {'id': 'frame', 'd': _FRAME, 'closed': [True], 'fill': 'none'},
    {'id': 'a', 'd': _LETTER_A, 'closed': [True], 'fill': '#112233'},
    {'id': 'b', 'd': _LETTER_B, 'closed': [True], 'fill': 'other'},
]
_BARE = [
    {'id': 'left', 'd': _LEFT, 'closed': [True], 'fill': 'none'},
    {'id': 'right', 'd': _RIGHT, 'closed': [True], 'fill': 'none'},
]
_HOLES = [{
    'id': 'band',
    'd': _BAND,
    'closed': [True, True, True],
    'fill': '#336699',
}]
_SOLID = [{
    'id': 'panel',
    'd': _PANEL,
    'closed': [True],
    'fill': '#112233',
}]
_OPEN = [{
    'id': 'gap',
    'd': 'M 5,6 L 15,6 L 15,20',
    'closed': [False],
    'fill': 'none',
}]
_DEFECTS = [
    {'id': 'gap', 'd': _OPEN_TRI, 'closed': [False], 'fill': 'none'},
    {'id': 'block', 'd': _BLOCK, 'closed': [True], 'fill': '#336699'},
    {'id': 'cross', 'd': _CROSS, 'closed': [True, True], 'fill': '#222222'},
]


def _button(dialog, name):
    widget = dialog.findChild(QtWidgets.QPushButton, name)
    assert widget is not None, name
    return widget


def _edit(dialog, name):
    widget = dialog.findChild(QtWidgets.QLineEdit, name)
    assert widget is not None, name
    return widget


def _view(dialog):
    widget = dialog.findChild(QtWidgets.QGraphicsView, 'preview')
    assert widget is not None
    return widget


def _run(records, drive):
    app = QtWidgets.QApplication.instance()
    if app is None:
        QtWidgets.QApplication([])

    def ready(dialog):
        timer = QtCore.QTimer(dialog)
        timer.setSingleShot(True)
        timer.timeout.connect(dialog.reject)
        timer.start(20000)
        drive(dialog)

    return run_weedlines_dialog(records, ready=ready, quit_app=False)


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


def _at(image, rect, x, y):
    px = round((x - rect.x()) * _SCALE)
    py = round((y - rect.y()) * _SCALE)
    assert 0 <= px < image.width(), (x, y, px)
    assert 0 <= py < image.height(), (x, y, py)
    return image.pixelColor(px, py).name().lower()


def _background(view):
    return view.backgroundBrush().color().name().lower()


def _sample(view, rect, points):
    image = _render(view, rect)
    return {point: _at(image, rect, point[0], point[1]) for point in points}


def _set_color(dialog, name, color):
    edit = _edit(dialog, name)
    edit.setText(color)
    edit.editingFinished.emit()
    return edit


def _regions(records, swap=False):
    return subject_weed_regions(classify_figures(records).figures, swap)


def _stroke_colors(view):
    found = []
    for item in view.scene().items():
        pen = getattr(item, 'pen', None)
        if not callable(pen):
            continue
        paint = pen()
        if paint.style() == QtCore.Qt.NoPen or paint.color().alpha() == 0:
            continue
        found.append(paint.color().name().lower())
    return found


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


def _take_path(items, expected):
    for index, item in enumerate(items):
        if _same_path(item.path(), expected):
            return items.pop(index)
    raise AssertionError('missing preview path with %s elements' % (
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


def _expected_arrows(records):
    check = classify_figures(records)
    regions = subject_weed_regions(check.figures, swap=False)
    grouped = {}
    for defect in check.defects:
        grouped.setdefault(defect.kind, []).append(defect.target)
    arrows = []
    for kind in ('dangling', 'overlap', 'self-overlap'):
        targets = grouped.get(kind)
        if not targets:
            continue
        arrows.extend(build_arrow_paths(kind, targets, regions.bounds))
    assert {arrow.color.lower() for arrow in arrows} == {
        '#ff00ff', '#ff6a00', '#00e5ff',
    }
    return arrows


def _wait_for_cuts(dialog, sample):
    apply_btn = _button(dialog, 'apply')
    holder = {'error': None}
    ticks = {'n': 0}

    def poll():
        ticks['n'] += 1
        try:
            if apply_btn.isEnabled():
                holder.update(sample())
                dialog.reject()
                return
            if ticks['n'] > 300:
                log = dialog.findChild(QtWidgets.QPlainTextEdit)
                text = log.toPlainText() if log is not None else ''
                holder['error'] = 'timeout\n' + text
                dialog.reject()
                return
        except Exception as exc:
            holder['error'] = str(exc)
            dialog.reject()
            return
        QtCore.QTimer.singleShot(50, poll)

    QtCore.QTimer.singleShot(50, poll)
    return holder


def test_subject_weed_and_background_colors():
    letters = QtCore.QRectF(-10, -10, 100, 80)
    solid = (17.0, 20.0)
    gradient = (59.0, 22.0)
    weed = ((4.0, 4.0), (12.0, 4.0), (44.0, 25.0), (74.0, 20.0))
    outside = ((-6.0, 25.0), (40.0, 60.0))

    def drive_letters(dialog):
        view = _view(dialog)
        seen = _sample(view, letters, (solid, gradient) + weed + outside)
        assert seen[solid] == '#112233'
        assert seen[gradient] == _SUBJECT
        assert {seen[point] for point in weed} == {_LIGHT, _DARK}
        background = _background(view)
        assert background == _BACKGROUND_FALLBACK
        for point in outside:
            assert seen[point] == background
        dialog.reject()

    _run(_LETTERS, drive_letters)

    bare = QtCore.QRectF(-8, -8, 46, 32)
    bare_subject = ((5.0, 5.0), (25.0, 5.0))
    bare_weed = ((12.0, 5.0), (18.0, 5.0))
    bare_out = ((-3.0, 5.0), (15.0, 16.0))

    def drive_bare(dialog):
        view = _view(dialog)
        seen = _sample(view, bare, bare_subject + bare_weed + bare_out)
        for point in bare_subject:
            assert seen[point] == _SUBJECT
        assert {seen[point] for point in bare_weed} == {_LIGHT, _DARK}
        background = _background(view)
        for point in bare_out:
            assert seen[point] == background
        dialog.reject()

    _run(_BARE, drive_bare)

    holes = QtCore.QRectF(-10, -10, 100, 80)
    band = (4.0, 25.0)
    hole_points = ((14.0, 20.0), (22.0, 20.0), (58.0, 26.0))
    hole_out = ((84.0, 25.0),)

    def drive_holes(dialog):
        view = _view(dialog)
        seen = _sample(view, holes, (band,) + hole_points + hole_out)
        assert seen[band] == '#336699'
        assert {seen[point] for point in hole_points[:2]} == {_LIGHT, _DARK}
        assert seen[hole_points[2]] in (_LIGHT, _DARK)
        background = _background(view)
        assert seen[hole_out[0]] == background
        dialog.reject()

    _run(_HOLES, drive_holes)


def test_weed_lines_use_the_weed_line_color_on_the_work_region():
    regions = _regions(_SOLID)
    work = padded_work_rect(regions.subject, [4.0, 4.0, 4.0, 4.0])
    bounds = regions.bounds
    mid_y = (bounds.top() + bounds.bottom()) / 2.0
    pad_x = (work.left() + bounds.left()) / 2.0
    line = (work.left(), mid_y)
    outside = (work.left() - 2.0, mid_y)
    subject = (25.0, 25.0)
    rect = QtCore.QRectF(
        work.left() - 8.0, work.top() - 8.0, work.width() + 16.0,
        work.height() + 16.0)
    pad_points = [
        (pad_x, y) for y in range(int(bounds.top()) + 1, int(bounds.bottom()))
    ]

    def drive(dialog):
        view = _view(dialog)
        before = _sample(view, rect, (subject, (pad_x, mid_y), outside))
        background = _background(view)
        assert before[subject] == '#112233'
        assert before[(pad_x, mid_y)] == background
        assert before[outside] == background
        assert _ORANGE not in _stroke_colors(view)
        pad = dialog.findChild(QtWidgets.QDoubleSpinBox, 'padding')
        assert pad is not None
        pad.setValue(4.0)
        assert _button(dialog, 'start').isEnabled()
        _button(dialog, 'start').click()

        def sample():
            image = _render(view, rect)
            colors = {_at(image, rect, x, y) for x, y in pad_points}
            return {
                'subject': _at(image, rect, subject[0], subject[1]),
                'pad': colors,
                'line': _at(image, rect, line[0], line[1]),
                'outside': _at(image, rect, outside[0], outside[1]),
                'strokes': _stroke_colors(view),
                'background': _background(view),
            }

        dialog._cuts = _wait_for_cuts(dialog, sample)

    holder = {}

    def wrapped(dialog):
        drive(dialog)
        holder['cuts'] = dialog._cuts

    _run(_SOLID, wrapped)
    cuts = holder['cuts']
    assert cuts['error'] is None, cuts['error']
    assert cuts['subject'] == '#112233'
    assert cuts['pad'] == {_LIGHT, _DARK}
    assert cuts['line'] == _WEED
    assert cuts['outside'] == cuts['background']
    assert _ORANGE not in cuts['strokes']
    assert _WEED in cuts['strokes']


def test_solid_self_overlap_paints_the_crossing_lens():
    rect = QtCore.QRectF(98, 98, 20, 20)
    arm = (102.0, 102.0)
    lens = (107.5, 107.5)

    def drive(dialog):
        seen = _sample(_view(dialog), rect, (arm, lens))
        assert seen[arm] == '#222222'
        assert seen[lens] == '#222222'
        dialog.reject()

    _run(_DEFECTS, drive)


def test_preview_arrows_are_the_library_paths():
    expected = _expected_arrows(_DEFECTS)
    assert expected

    def drive(dialog):
        items = _path_items(_view(dialog).scene())
        for arrow in expected:
            shaft = _take_path(items, arrow.shaft)
            head = _take_path(items, arrow.head)
            assert _pen_hex(shaft) == arrow.color.lower()
            assert _brush_hex(shaft) is None
            assert _brush_hex(head) == arrow.color.lower()
            assert _pen_hex(head) is None
        colors = {arrow.color.lower() for arrow in expected}
        for item in items:
            assert _pen_hex(item) not in colors
            assert _brush_hex(item) not in colors
        dialog.reject()

    _run(_DEFECTS, drive)


def test_swap_and_color_controls_change_paint_only():
    rect = QtCore.QRectF(-10, -10, 110, 80)
    solid = (17.0, 20.0)
    gradient = (59.0, 22.0)
    weed = (44.0, 25.0)
    outside = (90.0, 25.0)
    checker = ('#010101', '#020202')
    regions = _regions(_LETTERS)
    work = padded_work_rect(regions.subject, [4.0, 4.0, 4.0, 4.0])
    line = (work.left(), (work.top() + work.bottom()) / 2.0)

    def drive(dialog):
        assert _button(dialog, 'swap').text() == 'Swap subject and weed area'
        assert _edit(dialog, 'checkerboard-light').text().lower() == _LIGHT
        assert _edit(dialog, 'checkerboard-dark').text().lower() == _DARK
        assert _edit(dialog, 'weed-line-color').text().lower() == _WEED
        assert _edit(dialog, 'default-subject-color').text().lower() == _SUBJECT
        view = _view(dialog)
        background = _background(view)

        def at(point):
            return _sample(view, rect, (point,))[point]

        assert at(solid) == '#112233'
        assert at(gradient) == _SUBJECT
        assert at(weed) in (_LIGHT, _DARK)
        assert at(outside) == background
        start = _button(dialog, 'start')
        assert start.isEnabled()

        _button(dialog, 'swap').click()
        assert at(solid) in (_LIGHT, _DARK)
        assert at(weed) == _SUBJECT
        assert at(outside) == background
        assert start.isEnabled()

        _button(dialog, 'swap').click()
        assert at(solid) == '#112233'
        assert at(gradient) == _SUBJECT
        assert at(weed) in (_LIGHT, _DARK)
        assert start.isEnabled()

        _set_color(dialog, 'checkerboard-light', checker[0])
        _set_color(dialog, 'checkerboard-dark', checker[1])
        assert at(weed) in checker
        assert at(solid) == '#112233'
        assert at(gradient) == _SUBJECT
        assert at(outside) == background
        assert start.isEnabled()

        _set_color(dialog, 'default-subject-color', '#030405')
        assert at(gradient) == '#030405'
        assert at(solid) == '#112233'
        assert at(weed) in checker
        assert start.isEnabled()

        assert at(solid) == '#112233'
        assert start.isEnabled()
        pad = dialog.findChild(QtWidgets.QDoubleSpinBox, 'padding')
        assert pad is not None
        pad.setValue(4.0)
        start.click()

        def sample():
            image = _render(view, rect)
            assert _at(image, rect, line[0], line[1]) == _WEED
            _set_color(dialog, 'weed-line-color', '#050607')
            image = _render(view, rect)
            return {
                'line': _at(image, rect, line[0], line[1]),
                'solid': _at(image, rect, solid[0], solid[1]),
                'weed': _at(image, rect, weed[0], weed[1]),
            }

        dialog._cuts = _wait_for_cuts(dialog, sample)

    holder = {}

    def wrapped(dialog):
        drive(dialog)
        holder['cuts'] = dialog._cuts

    _run(_LETTERS, wrapped)
    cuts = holder['cuts']
    assert cuts['error'] is None, cuts['error']
    assert cuts['line'] == '#050607'
    assert cuts['solid'] == '#112233'
    assert cuts['weed'] in checker


def test_start_stays_disabled_when_the_check_reports_a_defect():
    def drive(dialog):
        start = _button(dialog, 'start')
        assert start.isEnabled() is False
        _set_color(dialog, 'checkerboard-light', '#010101')
        _set_color(dialog, 'checkerboard-dark', '#020202')
        _set_color(dialog, 'weed-line-color', '#050607')
        _set_color(dialog, 'default-subject-color', '#030405')
        _button(dialog, 'swap').click()
        _button(dialog, 'swap').click()
        box = dialog.findChild(QtWidgets.QComboBox, 'mode')
        assert box is not None
        box.setCurrentIndex(1)
        box.setCurrentIndex(2)
        assert start.isEnabled() is False
        start.click()
        assert _button(dialog, 'apply').isEnabled() is False
        dialog.reject()

    _run(_OPEN, drive)
