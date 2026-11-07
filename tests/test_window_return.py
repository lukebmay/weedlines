# -*- coding: utf-8 -*-
"""Window return: the line and actions under the preview."""
from __future__ import division

import json
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

from weedlines_dialog import run_weedlines_dialog  # noqa: E402

_PROBLEM = (
    'Correct the marked problems in Inkscape before weed lines will run.')
_ALL_KINDS = (
    _PROBLEM + ' dangling ends, figure overlaps, and self-overlaps.')
_DANGLING_ONLY = _PROBLEM + ' dangling ends.'
_TWO_KINDS = _PROBLEM + ' dangling ends and self-overlaps.'
_IMPORT = (
    'Run Extensions → Weedlines → Import last result to place the arrows.')
_PLAIN = 'Return to Inkscape'
_ARROW = 'Return to Inkscape with correction arrows'
_INK_LABEL = '{http://www.inkscape.org/namespaces/inkscape}label'
_LABELS = {
    'dangling': 'Dangling ends',
    'overlap': 'Figure overlaps',
    'self-overlap': 'Self-overlaps',
}
_KIND_ORDER = (
    ('dangling', 'dangling ends'),
    ('overlap', 'figure overlaps'),
    ('self-overlap', 'self-overlaps'),
)
_SWATCH = '\u2588'

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
_OPEN = [{
    'id': 'gap',
    'd': 'M 5,6 L 15,6 L 15,20',
    'closed': [False],
    'fill': 'none',
}]
_TWO = [
    _OPEN[0],
    {'id': 'cross', 'd': _CROSS, 'closed': [True, True], 'fill': '#222222'},
]
_CLEAR = [{
    'id': 'panel',
    'd': 'M 0,0 L 50,0 L 50,50 L 0,50 Z',
    'closed': [True],
    'fill': '#112233',
}]


def _button(dialog, name):
    widget = dialog.findChild(QtWidgets.QPushButton, name)
    assert widget is not None, name
    return widget


def _buttons(dialog, text):
    return [
        button
        for button in dialog.findChildren(QtWidgets.QPushButton)
        if button.text() == text
    ]


def _one(dialog, text):
    found = _buttons(dialog, text)
    assert len(found) == 1, text
    return found[0]


def _line(dialog):
    widget = dialog.findChild(QtWidgets.QLabel, 'return-line')
    assert widget is not None
    return widget


def _line_chars(line):
    doc = QtGui.QTextDocument()
    doc.setHtml(line.text())
    chars = []
    block = doc.begin()
    while block.isValid():
        it = block.begin()
        while not it.atEnd():
            frag = it.fragment()
            text = frag.text()
            if text:
                fmt = frag.charFormat()
                for ch in text:
                    chars.append((ch, fmt))
            it += 1
        block = block.next()
    return chars


def _has_ink(fmt):
    return (
        fmt.hasProperty(QtGui.QTextFormat.ForegroundBrush)
        or fmt.hasProperty(QtGui.QTextFormat.BackgroundBrush))


def _label_ink(dialog, line):
    for label in dialog.findChildren(QtWidgets.QLabel):
        if label is line or label.styleSheet():
            continue
        if not label.text():
            continue
        return label.palette().color(QtGui.QPalette.WindowText).name()
    raise AssertionError('no label color to compare')


def _assert_swatches(dialog, records, sentence):
    """Each present kind has its arrow color before the name.

    The names stay in the label color. The sentence without the
    swatches is the same line as before.
    """
    line = _line(dialog)
    colors = {}
    for kind, batch in _expected_arrow_batches(records):
        assert batch, kind
        colors[kind] = batch[0].color
        for arrow in batch:
            assert arrow.color == batch[0].color
    assert colors
    assert line.textFormat() == QtCore.Qt.RichText
    assert line.styleSheet() == ''
    assert (
        line.palette().color(QtGui.QPalette.WindowText).name()
        == _label_ink(dialog, line))
    present = [kind for kind, _word in _KIND_ORDER if kind in colors]
    chars = _line_chars(line)
    swatches = []
    plain = []
    for ch, fmt in chars:
        if ch == _SWATCH:
            assert fmt.hasProperty(QtGui.QTextFormat.ForegroundBrush)
            assert not fmt.hasProperty(QtGui.QTextFormat.BackgroundBrush)
            swatches.append(fmt.foreground().color().name().lower())
            continue
        assert not _has_ink(fmt), ch
        plain.append(ch)
    assert swatches == [colors[kind].lower() for kind in present]
    if 'self-overlap' in colors:
        assert colors['self-overlap'].upper() == '#00E5FF'
        assert swatches[present.index('self-overlap')] == '#00e5ff'
        assert '#00E5FF' in line.text()
    assert ' '.join(''.join(plain).split()) == sentence
    full = ''.join(ch for ch, _fmt in chars)
    cursor = 0
    for kind in present:
        word = dict(_KIND_ORDER)[kind]
        at = full.find(word, cursor)
        assert at >= 2, word
        assert full[at - 1] == ' '
        assert full[at - 2] == _SWATCH
        cursor = at + len(word)
    for _kind, word in _KIND_ORDER:
        if word in sentence:
            assert word in full
        else:
            assert word not in line.text()
            assert word not in full


def _view(dialog):
    widget = dialog.findChild(QtWidgets.QGraphicsView, 'preview')
    assert widget is not None
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


def _rect(dialog, widget):
    origin = widget.mapTo(dialog, QtCore.QPoint(0, 0))
    return QtCore.QRect(origin, widget.size())


def _below(upper, lower):
    assert lower.top() >= upper.top() + upper.height(), (upper, lower)


def _in_dialog(dialog, widget):
    assert widget.isWindow() is False
    assert widget.window() is dialog
    parent = widget
    while parent is not None:
        assert not isinstance(parent, QtWidgets.QMessageBox)
        parent = parent.parentWidget()


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


def _forbid_message_box(monkeypatch):
    opened = []

    def _opened(*_args, **_kwargs):
        opened.append('open')
        raise AssertionError('message box opened')

    for name in ('information', 'warning', 'critical', 'question', 'about'):
        monkeypatch.setattr(QtWidgets.QMessageBox, name, _opened)
    monkeypatch.setattr(
        QtWidgets.QMessageBox, 'exec_', _opened, raising=False)
    monkeypatch.setattr(
        QtWidgets.QMessageBox, 'exec', _opened, raising=False)
    return opened


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
    raise AssertionError('missing preview path')


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


def _group_paths(group):
    shafts = []
    heads = []
    for el in list(group):
        tag = el.tag
        local = tag.rsplit('}', 1)[-1] if isinstance(tag, str) else ''
        if local != 'path':
            continue
        path_id = el.get('id') or ''
        if '-shaft-' in path_id:
            shafts.append(el.get('d') or '')
        elif '-head-' in path_id:
            heads.append(el.get('d') or '')
    return shafts, heads


def test_defect_line_and_actions_sit_under_the_preview():
    def drive(dialog):
        view = _view(dialog)
        line = _line(dialog)
        plain = _one(dialog, _PLAIN)
        arrows = _one(dialog, _ARROW)
        _assert_swatches(dialog, _DEFECTS, _ALL_KINDS)
        assert plain.text() == _PLAIN
        assert arrows.text() == _ARROW
        assert view.height() > 0
        assert line.height() > 0
        assert plain.isVisible() and arrows.isVisible()
        for widget in (line, plain, arrows):
            _in_dialog(dialog, widget)
        preview_rect = _rect(dialog, view)
        line_rect = _rect(dialog, line)
        _below(preview_rect, line_rect)
        _below(line_rect, _rect(dialog, plain))
        _below(line_rect, _rect(dialog, arrows))
        assert not preview_rect.intersects(line_rect)
        start = _button(dialog, 'start')
        box = _mode_box(dialog)
        for index in range(box.count()):
            box.setCurrentIndex(index)
            assert start.isEnabled() is False
        start.click()
        assert _button(dialog, 'apply').isEnabled() is False
        dialog.reject()

    _run(_DEFECTS, drive)


def test_line_names_only_the_kinds_present():
    def drive_one(dialog):
        _assert_swatches(dialog, _OPEN, _DANGLING_ONLY)
        assert 'figure overlaps' not in _line(dialog).text()
        assert 'self-overlaps' not in _line(dialog).text()
        dialog.reject()

    def drive_two(dialog):
        _assert_swatches(dialog, _TWO, _TWO_KINDS)
        assert 'figure overlaps' not in _line(dialog).text()
        dialog.reject()

    _run(_OPEN, drive_one)
    _run(_TWO, drive_two)


def test_clear_check_has_an_empty_line_and_start_works():
    # The solver imports generate_weeds in the spawned child. The parent
    # sees that run as the frame keep and Apply.
    holder = {'error': None, 'modes': None, 'solver_calls': 0}

    def drive(dialog):
        view = _view(dialog)
        line = _line(dialog)
        assert line.text() == ''
        assert _buttons(dialog, _ARROW) == []
        assert view.height() > 0
        _in_dialog(dialog, line)
        _below(_rect(dialog, view), _rect(dialog, line))
        start = _button(dialog, 'start')
        box = _mode_box(dialog)
        for index in range(box.count()):
            box.setCurrentIndex(index)
            assert start.isEnabled() is True
        _set_mode(dialog, 'frame')
        apply_btn = _button(dialog, 'apply')
        start.click()
        ticks = {'n': 0}

        def poll():
            ticks['n'] += 1
            modes = [mode for mode, _path in dialog.solver_keeps]
            if apply_btn.isEnabled() and modes:
                holder['modes'] = list(modes)
                holder['solver_calls'] = dialog.worker_calls.count('solver')
                dialog.reject()
                return
            if ticks['n'] > 100:
                holder['error'] = 'start did not run'
                dialog.reject()
                return
            QtCore.QTimer.singleShot(50, poll)

        QtCore.QTimer.singleShot(50, poll)

    _run(_CLEAR, drive)
    assert holder['error'] is None, holder['error']
    assert holder['modes'] == ['frame']
    assert holder['solver_calls'] == 1


def test_plain_return_writes_nothing_and_closes(tmp_path, monkeypatch):
    import weedlines_job as JOB
    _forbid_message_box(monkeypatch)
    monkeypatch.setattr(JOB, 'cache_dir', lambda: str(tmp_path))

    def fail_write(*_args, **_kwargs):
        raise AssertionError('result written')

    monkeypatch.setattr(JOB, 'write_correction_result', fail_write)
    monkeypatch.setattr(JOB, 'write_result', fail_write)

    def drive(dialog):
        _one(dialog, _PLAIN).click()
        assert dialog.isVisible() is False

    result = _run(_DEFECTS, drive)
    assert result == (None, None, None)
    assert list(tmp_path.iterdir()) == []


def _expected_arrow_batches(records):
    import weedlib.arrows as arrow_mod
    from weedlib.figures import classify_figures, subject_weed_regions

    check = classify_figures(records)
    regions = subject_weed_regions(check.figures, swap=False)
    grouped = {}
    for defect in check.defects:
        grouped.setdefault(defect.kind, []).append(defect.target)
    batches = []
    for kind in ('dangling', 'overlap', 'self-overlap'):
        targets = grouped.get(kind)
        if not targets:
            continue
        batches.append((
            kind, arrow_mod.build_arrow_paths(kind, targets, regions.bounds)))
    return batches


def test_arrow_return_writes_the_preview_paths_and_stays_open(
        tmp_path, monkeypatch):
    import weedlib.arrows as arrow_mod
    import weedlines_job as JOB
    import weedlines_svg as SVG
    from weedlib.svg_paths import qpainterpath_to_svg_d

    expected = _expected_arrow_batches(_DEFECTS)
    assert expected
    opened = _forbid_message_box(monkeypatch)
    monkeypatch.setattr(JOB, 'cache_dir', lambda: str(tmp_path))
    built = []
    real_build = arrow_mod.build_arrow_paths

    def wrapped(kind, targets, bounds):
        batch = real_build(kind, targets, bounds)
        built.append((kind, batch))
        return batch

    # A parent patch does not see the child. The preview is the proof.
    monkeypatch.setattr(arrow_mod, 'build_arrow_paths', wrapped)
    written = {}
    real_write = JOB.write_correction_result

    def wrapped_write(arrows, doc_attrs=None, meta=None, labels=None):
        written['arrows'] = arrows
        written['doc'] = doc_attrs
        written['labels'] = labels
        return real_write(
            arrows, doc_attrs=doc_attrs, meta=meta, labels=labels)

    monkeypatch.setattr(JOB, 'write_correction_result', wrapped_write)
    holder = {}

    def drive(dialog):
        assert built == []
        calls = list(dialog.worker_calls)
        items = _path_items(_view(dialog).scene())
        for _kind, batch in expected:
            for arrow in batch:
                shaft = _take_path(items, arrow.shaft)
                head = _take_path(items, arrow.head)
                assert _pen_hex(shaft) == arrow.color.lower()
                assert _brush_hex(head) == arrow.color.lower()
        _one(dialog, _ARROW).click()
        assert built == []
        assert list(dialog.worker_calls) == calls
        assert dialog.isVisible() is True
        assert _line(dialog).text() == _IMPORT
        start = _button(dialog, 'start')
        box = _mode_box(dialog)
        for index in range(box.count()):
            box.setCurrentIndex(index)
            assert start.isEnabled() is False
        boxes = [
            widget
            for widget in QtWidgets.QApplication.topLevelWidgets()
            if isinstance(widget, QtWidgets.QMessageBox)
        ]
        assert boxes == []
        assert opened == []
        for kind, batch in expected:
            written_batch = written['arrows'][kind]
            assert len(written_batch) == len(batch)
            for got, arrow in zip(written_batch, batch):
                assert _same_path(got.shaft, arrow.shaft)
                assert _same_path(got.head, arrow.head)
                assert got.color.lower() == arrow.color.lower()
        svg_path = tmp_path / 'last_result.svg'
        holder['svg'] = svg_path.read_text(encoding='utf-8')
        _one(dialog, _PLAIN).click()
        assert dialog.isVisible() is False

    result = _run(
        _DEFECTS,
        drive,
        width='100',
        height='80',
        view_box='0 0 100 80',
    )
    assert result == (None, None, None)
    assert written['doc'] == {
        'width': '100',
        'height': '80',
        'viewBox': '0 0 100 80',
    }
    json_path = tmp_path / 'last_result.json'
    svg_path = tmp_path / 'last_result.svg'
    assert svg_path.read_text(encoding='utf-8') == holder['svg']
    with json_path.open(encoding='utf-8') as fh:
        payload = json.load(fh)
    assert payload.get('result') == 'correction'
    assert 'keep_d' not in payload
    assert payload.get('doc_attrs') == written['doc']
    groups = SVG.load_correction_svg_groups(str(svg_path))
    assert [group.get(_INK_LABEL) for group in groups] == [
        _LABELS[kind] for kind, _batch in expected
    ]
    from weedlib.ready import build_correction_marks
    marks = build_correction_marks(_DEFECTS)
    by_text = {label.text: label for label in marks.labels}
    assert [got['text'] for got in written['labels']] == [
        label.text for label in marks.labels
    ]
    for got, label in zip(written['labels'], marks.labels):
        assert got['text'] == label.text
        assert got['color'] == label.color
        assert got['point'][0] == pytest.approx(label.point[0])
        assert got['point'][1] == pytest.approx(label.point[1])
    for (kind, batch), group in zip(expected, groups):
        shafts, heads = _group_paths(group)
        assert shafts == [
            qpainterpath_to_svg_d(arrow.shaft, close_subpaths=False)
            for arrow in batch
        ]
        assert heads == [
            qpainterpath_to_svg_d(arrow.head, close_subpaths=False)
            for arrow in batch
        ]
        texts = [
            el for el in list(group)
            if isinstance(el.tag, str) and el.tag.rsplit('}', 1)[-1] == 'text'
        ]
        assert len(texts) == 1
        label = by_text[group.get(_INK_LABEL)]
        assert texts[0].text == label.text
        assert float(texts[0].get('x')) == pytest.approx(label.point[0])
        assert float(texts[0].get('y')) == pytest.approx(label.point[1])
        assert label.color.lower() in (texts[0].get('style') or '').lower()
        assert texts[0].text == _LABELS[kind]
