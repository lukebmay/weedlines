# -*- coding: utf-8 -*-
"""Window timing: library asks run once, after the dialog is visible."""
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


_KIND_ORDER = (
    ('dangling', 'dangling ends'),
    ('overlap', 'figure overlaps'),
    ('self-overlap', 'self-overlaps'),
)
_SWATCH = '\u2588'


def _arrow_colors(records):
    import weedlib.arrows as arrow_mod
    import weedlib.figures as figures

    check = figures.classify_figures(records)
    regions = figures.subject_weed_regions(check.figures, swap=False)
    grouped = {}
    for defect in check.defects:
        grouped.setdefault(defect.kind, []).append(defect.target)
    colors = {}
    for kind, _word in _KIND_ORDER:
        targets = grouped.get(kind)
        if not targets:
            continue
        batch = arrow_mod.build_arrow_paths(kind, targets, regions.bounds)
        assert batch, kind
        colors[kind] = batch[0].color
    return colors


def _assert_return_swatches(line, colors, sentence):
    assert colors
    assert line.textFormat() == QtCore.Qt.RichText
    assert line.styleSheet() == ''
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
    present = [kind for kind, _word in _KIND_ORDER if kind in colors]
    swatches = []
    plain = []
    for ch, fmt in chars:
        colored = (
            fmt.hasProperty(QtGui.QTextFormat.ForegroundBrush)
            or fmt.hasProperty(QtGui.QTextFormat.BackgroundBrush))
        if ch == _SWATCH:
            assert fmt.hasProperty(QtGui.QTextFormat.ForegroundBrush)
            assert not fmt.hasProperty(QtGui.QTextFormat.BackgroundBrush)
            swatches.append(fmt.foreground().color().name().lower())
            continue
        assert not colored
        plain.append(ch)
    assert swatches == [colors[kind].lower() for kind in present]
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
        status = dialog.findChild(QtWidgets.QLabel, 'status')
        text = '' if status is None else status.text()
        busy = text.startswith('working') or text.startswith('paused')
        start = dialog.findChild(QtWidgets.QPushButton, 'start')
        if start is None or not start.isVisible():
            busy = True
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


def _pump_until(predicate, timeout=20):
    import time
    app = QtWidgets.QApplication.instance()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents(QtCore.QEventLoop.AllEvents, 30)
        if predicate():
            return
    raise AssertionError('timed out')


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
        assert list(dialog.worker_calls) == [
            'classify', 'subject', 'surrounds', 'piece_border']
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
    colors = _arrow_colors(_DEFECTS)
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
        assert line is not None
        _assert_return_swatches(line, colors, _ALL_KINDS)
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


def _button(dialog, name):
    widget = dialog.findChild(QtWidgets.QPushButton, name)
    assert widget is not None, name
    return widget


def _set_mode(dialog, mode):
    box = dialog.findChild(QtWidgets.QComboBox, 'mode')
    assert box is not None
    for index in range(box.count()):
        if box.itemData(index) == mode:
            box.setCurrentIndex(index)
            return
    raise AssertionError('missing mode %s' % mode)


def _status(dialog):
    label = dialog.findChild(QtWidgets.QLabel, 'status')
    assert label is not None
    return label


def _spinner(dialog):
    widget = dialog.findChild(QtWidgets.QProgressBar, 'spinner')
    assert widget is not None
    return widget


def _pen_names(dialog):
    view = dialog.findChild(QtWidgets.QGraphicsView, 'preview')
    assert view is not None
    names = set()
    for item in view.scene().items():
        pen = getattr(item, 'pen', None)
        if not callable(pen):
            continue
        color = pen().color()
        if color.alpha() == 0:
            continue
        path = item.path() if hasattr(item, 'path') else None
        if path is not None and path.elementCount() == 5:
            continue
        names.add(color.name().lower())
    return names


def _label_names(dialog):
    return sorted(
        label.objectName()
        for label in dialog.findChildren(QtWidgets.QLabel)
        if label.objectName())


def _visible_steps(dialog):
    shown = []
    for name in ('step-cut', 'step-surround', 'step-conquer'):
        widget = dialog.findChild(QtWidgets.QWidget, name)
        assert widget is not None, name
        if widget.isVisible():
            shown.append(name)
    return shown


def _run_busy_for(dialog):
    text = _status(dialog).text()
    if text.startswith('working') or text.startswith('paused'):
        return True
    return _button(dialog, 'pause').isVisible()


def test_cut_shows_one_step_and_a_phase_does_not_add_one():
    def drive(dialog):
        color = dialog.findChild(QtWidgets.QLineEdit, 'weed-line-color')
        assert color is not None
        color.setText('#123456')
        color.editingFinished.emit()
        assert color.property('color') == '#123456'
        _set_mode(dialog, 'frame')
        assert _visible_steps(dialog) == ['step-cut']
        assert _button(dialog, 'conquer-start').isVisible() is False
        labels = _label_names(dialog)
        start = _button(dialog, 'start')
        assert start.text() == 'Start'
        start.click()
        assert _status(dialog).text().startswith('working')
        assert _spinner(dialog).isVisible() is True
        assert start.text() == 'Restart'
        assert start.isEnabled() is False
        assert _visible_steps(dialog) == ['step-cut']
        _wait_idle(dialog)
        assert _status(dialog).text() == 'done'
        assert _spinner(dialog).isVisible() is False
        assert start.text() == 'Restart'
        assert start.isEnabled() is True
        assert dialog.last_phase == 'frame'
        assert _visible_steps(dialog) == ['step-cut']
        assert _label_names(dialog) == labels
        assert '#123456' in _pen_names(dialog)
        assert dialog.worker_calls.count('solver') == 1
        start.click()
        assert '#123456' not in _pen_names(dialog)
        assert _status(dialog).text().startswith('working')
        assert _spinner(dialog).isVisible() is True
        assert start.isEnabled() is False
        _wait_idle(dialog)
        assert dialog.worker_calls.count('solver') == 2
        assert '#123456' in _pen_names(dialog)
        assert _status(dialog).text() == 'done'
        assert _button(dialog, 'apply').isEnabled() is True
        _button(dialog, 'clear-all').click()
        assert '#123456' not in _pen_names(dialog)
        assert _status(dialog).text() == 'ready'
        assert _spinner(dialog).isVisible() is False
        assert start.text() == 'Start'
        assert start.isEnabled() is True
        assert _button(dialog, 'apply').isEnabled() is False
        mode = dialog.findChild(QtWidgets.QComboBox, 'mode')
        assert mode.currentData() == 'frame'
        assert color.property('color') == '#123456'
        dialog.reject()

    _run(_CLEAR, drive)


def test_pause_hides_the_spinner_and_resume_keeps_the_run(monkeypatch):
    import weedlines_dialog as dialog_mod

    paused = []
    real_spawn = dialog_mod._spawn_ask

    def wrapped(request, hold, pausing, cancelled):
        proc, conn = real_spawn(request, hold, pausing, cancelled)
        if request.get('kind') != 'solver':
            return proc, conn
        dialog = _visible_dialog()
        assert dialog is not None
        timer = QtCore.QTimer(dialog)
        timer.setSingleShot(True)

        def mark():
            if dialog.isVisible() and proc.is_alive():
                _button(dialog, 'pause').click()
                paused.append(proc.is_alive())

        timer.timeout.connect(mark)
        timer.start(0)
        timers = getattr(dialog, '_hold_timers', None)
        if timers is None:
            timers = []
            dialog._hold_timers = timers
        timers.append(timer)
        return proc, conn

    monkeypatch.setattr(dialog_mod, '_spawn_ask', wrapped)
    old_hold = dialog_mod._ASK_HOLD
    dialog_mod._ASK_HOLD = 8000000

    def drive(dialog):
        try:
            _set_mode(dialog, 'grid')
            view = dialog.findChild(QtWidgets.QGraphicsView, 'preview')
            assert view is not None
            _button(dialog, 'start').click()
            _pump_until(lambda: bool(paused), timeout=10)
            assert paused == [True]
            _pump_until(lambda: dialog.worker_calls.count('solver') >= 1)
            assert _status(dialog).text().startswith('paused')
            assert _spinner(dialog).isVisible() is False
            assert _WEED not in _pen_names(dialog)
            kept = len(view.scene().items())
            app = QtWidgets.QApplication.instance()
            for _ in range(4):
                app.processEvents(QtCore.QEventLoop.AllEvents, 50)
            assert len(view.scene().items()) == kept
            assert dialog.worker_calls.count('solver') == 1
            assert _run_busy_for(dialog) is True
            _button(dialog, 'pause').click()
            _wait_idle(dialog)
            assert dialog.worker_calls.count('solver') == 1
            assert _WEED in _pen_names(dialog)
            assert _status(dialog).text() == 'done'
            assert _spinner(dialog).isVisible() is False
            dialog.reject()
        finally:
            if dialog.isVisible() and _run_busy_for(dialog):
                _button(dialog, 'clear-all').click()
                _wait_idle(dialog)
            if dialog.isVisible():
                dialog.reject()

    try:
        _run(_CLEAR, drive)
    finally:
        dialog_mod._ASK_HOLD = old_hold


def test_clear_all_from_pause_drops_the_cut(monkeypatch):
    import weedlines_dialog as dialog_mod

    killed = []
    real_spawn = dialog_mod._spawn_ask

    def wrapped(request, hold, pausing, cancelled):
        proc, conn = real_spawn(request, hold, pausing, cancelled)
        if request.get('kind') != 'solver':
            return proc, conn

        def deny(*_args, **_kwargs):
            killed.append('kill')
            raise AssertionError('child killed')

        proc.terminate = deny
        proc.kill = deny
        dialog = _visible_dialog()
        timer = QtCore.QTimer(dialog)
        timer.setSingleShot(True)

        def mark():
            if dialog.isVisible() and proc.is_alive():
                _button(dialog, 'pause').click()

        timer.timeout.connect(mark)
        timer.start(0)
        timers = getattr(dialog, '_hold_timers', None)
        if timers is None:
            timers = []
            dialog._hold_timers = timers
        timers.append(timer)
        return proc, conn

    monkeypatch.setattr(dialog_mod, '_spawn_ask', wrapped)
    old_hold = dialog_mod._ASK_HOLD
    dialog_mod._ASK_HOLD = 8000000

    def drive(dialog):
        color = dialog.findChild(QtWidgets.QLineEdit, 'weed-line-color')
        try:
            _set_mode(dialog, 'frame')
            _button(dialog, 'start').click()
            _pump_until(
                lambda: _status(dialog).text().startswith('paused'),
                timeout=10)
            _pump_until(lambda: dialog.worker_calls.count('solver') >= 1)
            assert _spinner(dialog).isVisible() is False
            _button(dialog, 'clear-all').click()
            _wait_idle(dialog)
            assert killed == []
            assert _WEED not in _pen_names(dialog)
            assert _status(dialog).text() == 'ready'
            assert _spinner(dialog).isVisible() is False
            assert _button(dialog, 'start').text() == 'Start'
            assert _button(dialog, 'apply').isEnabled() is False
            mode = dialog.findChild(QtWidgets.QComboBox, 'mode')
            assert mode.currentData() == 'frame'
            assert color.property('color') == '#FF0000'
            dialog.reject()
        finally:
            if dialog.isVisible() and _run_busy_for(dialog):
                _button(dialog, 'clear-all').click()
                _wait_idle(dialog)
            if dialog.isVisible():
                dialog.reject()

    try:
        _run(_CLEAR, drive)
    finally:
        dialog_mod._ASK_HOLD = old_hold
    assert killed == []


def test_close_during_a_cut_returns_nothing(monkeypatch):
    import weedlines_dialog as dialog_mod

    killed = []
    real_spawn = dialog_mod._spawn_ask

    def wrapped(request, hold, pausing, cancelled):
        proc, conn = real_spawn(request, hold, pausing, cancelled)
        if request.get('kind') != 'solver':
            return proc, conn

        def deny(*_args, **_kwargs):
            killed.append('kill')
            raise AssertionError('child killed')

        proc.terminate = deny
        proc.kill = deny
        return proc, conn

    monkeypatch.setattr(dialog_mod, '_spawn_ask', wrapped)
    old_hold = dialog_mod._ASK_HOLD
    dialog_mod._ASK_HOLD = 8000000

    def drive(dialog):
        _set_mode(dialog, 'island-hop')
        assert _visible_steps(dialog) == ['step-cut']
        _button(dialog, 'start').click()
        assert _status(dialog).text().startswith('working')
        assert _spinner(dialog).isVisible() is True
        _button(dialog, 'close').click()
        assert dialog.isVisible() is True

    try:
        result = _run(_CLEAR, drive)
    finally:
        dialog_mod._ASK_HOLD = old_hold
    assert result == (None, None, None)
    assert killed == []
