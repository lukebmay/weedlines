# -*- coding: utf-8 -*-
"""Interactive Weedlines dialog for the Inkscape extension.

Start / Pause / Resume / Cancel, scrolling stdout+stderr log (keeps
Inkscape from showing the "additional data" popup), and a live preview
of the subject, the weed area, and accepted cuts. Pause is cooperative
so you can inspect the preview mid-run, then resume.
"""
from __future__ import division

import logging
import math
import os
import sys
import threading
import time
from collections import deque

# Scene units. Short enough that a padding ring shows both tiles.
_CHECKER_TILE = 8.0
_ARROW_KINDS = ('dangling', 'overlap', 'self-overlap')
_KIND_WORDS = (
    ('dangling', 'dangling ends'),
    ('overlap', 'figure overlaps'),
    ('self-overlap', 'self-overlaps'),
)
_PROBLEM_SENTENCE = (
    'Correct the marked problems in Inkscape before weed lines will run.')
_IMPORT_SENTENCE = (
    'Run Extensions → Weedlines → Import last result to place the arrows.')


def _defect_line(defects):
    """Name each defect kind that is present. Empty when the check is clear."""
    present = set()
    for defect in defects or ():
        present.add(defect.kind)
    names = [word for kind, word in _KIND_WORDS if kind in present]
    if not names:
        return ''
    if len(names) == 1:
        named = names[0]
    elif len(names) == 2:
        named = '%s and %s' % (names[0], names[1])
    else:
        named = '%s, %s, and %s' % (names[0], names[1], names[2])
    return '%s %s.' % (_PROBLEM_SENTENCE, named)


def _hex_color(text):
    if not isinstance(text, str):
        return None
    token = text.strip()
    if len(token) != 7 or token[0] != '#':
        return None
    body = token[1:]
    for ch in body:
        if ch not in '0123456789abcdefABCDEF':
            return None
    return '#' + body.upper()


def _tint_edit(edit, color):
    luma = (
        int(color[1:3], 16) * 0.3
        + int(color[3:5], 16) * 0.59
        + int(color[5:7], 16) * 0.11)
    ink = '#000000' if luma > 140 else '#ffffff'
    edit.setStyleSheet('background-color: %s; color: %s;' % (color, ink))


def _line_pen(QtGui, QtCore, color):
    pen = QtGui.QPen(QtGui.QColor(color))
    pen.setWidthF(0.0)
    pen.setCosmetic(True)
    return pen


def _with_work_region(weed_area, work, QPainterPath, Qt):
    """Weed area, plus the solver work rect once cuts exist."""
    path = QPainterPath()
    if weed_area is not None and not weed_area.isEmpty():
        path = QPainterPath(weed_area)
    if work is not None and work.isValid():
        rect = QPainterPath()
        rect.addRect(work)
        path = rect if path.isEmpty() else path.united(rect)
    path.setFillRule(Qt.OddEvenFill)
    return path


def _checker_type(QtWidgets, QtGui, QtCore):
    class _CheckerItem(QtWidgets.QGraphicsPathItem):
        def __init__(self, path, light, dark, tile):
            QtWidgets.QGraphicsPathItem.__init__(self, path)
            self._light = QtGui.QColor(light)
            self._dark = QtGui.QColor(dark)
            self._tile = float(tile)
            self.setPen(QtGui.QPen(QtCore.Qt.NoPen))

        def paint(self, painter, _option, _widget=None):
            painter.save()
            painter.setPen(QtCore.Qt.NoPen)
            painter.setClipPath(self.path(), QtCore.Qt.IntersectClip)
            bounds = self.path().boundingRect()
            tile = self._tile
            x0 = math.floor(bounds.left() / tile) * tile
            y0 = math.floor(bounds.top() / tile) * tile
            y = y0
            row = 0
            while y < bounds.bottom() - 1e-9:
                x = x0
                col = 0
                while x < bounds.right() - 1e-9:
                    if (col + row) % 2 == 0:
                        painter.setBrush(QtGui.QBrush(self._light))
                    else:
                        painter.setBrush(QtGui.QBrush(self._dark))
                    painter.drawRect(QtCore.QRectF(x, y, tile, tile))
                    x += tile
                    col += 1
                y += tile
                row += 1
            painter.restore()

    return _CheckerItem


class _StreamToQueue(object):
    """File-like object that appends written text to a thread-safe deque."""

    def __init__(self, queue, mirror=None):
        self._queue = queue
        self._mirror = mirror
        self._buf = ''

    def write(self, data):
        if not data:
            return 0
        if self._mirror is not None:
            try:
                self._mirror.write(data)
            except Exception:
                pass
        self._buf += data
        while '\n' in self._buf:
            line, self._buf = self._buf.split('\n', 1)
            self._queue.append(line + '\n')
        return len(data)

    def flush(self):
        if self._buf:
            self._queue.append(self._buf)
            self._buf = ''
        if self._mirror is not None:
            try:
                self._mirror.flush()
            except Exception:
                pass

    def isatty(self):
        return False


class _QueueLogHandler(logging.Handler):
    def __init__(self, queue):
        logging.Handler.__init__(self)
        self._queue = queue

    def emit(self, record):
        try:
            self._queue.append(self.format(record) + '\n')
        except Exception:
            pass


def run_weedlines_dialog(records, defaults=None, platform_lines=None,
                         quit_app=True, width=None, height=None,
                         view_box=None, ready=None):
    """Show the weedlines UI. Returns ``(weed_path, layer_name, color)``.

    ``color`` is the weed-line color when Apply accepts, and None when
    the window does not. *records* are the job's per-path records, not
    a union. Start runs only when the figure check reports no defect.
    The solver keep path is the subject region. Swap exchanges that
    subject with the weed area. The preview paints the subject, the
    weed area, and the library's correction arrows. Plugin settings
    change those preview colors only. When the check reports a defect,
    the return line and its actions sit under the preview. Return to
    Inkscape closes without writing. The correction action writes
    those same arrow paths and leaves the window open. *width*,
    *height*, and *view_box* are the document size. *defaults* may
    include mode, padding, spacing, collar, layer_name.

    *platform_lines* is an optional deque fed by ``NativeStdioCapture``
    (Qt/OS stderr). Those lines are shown in the log and never reach Inkscape.

    *quit_app*: when this call created the QApplication, quit it on return
    (default). Detached host passes False so it can show a follow-up box.

    *ready*, when given, is called with the dialog once the window is shown.
    """
    from weedlib import generate_weeds, padded_work_rect
    from weedlib.arrows import build_arrow_paths
    from weedlib.figures import (
        _painted_parts, classify_figures, subject_weed_regions)
    from weedlib.paths import split_painter_path
    from weedlib.progress import WeedCancelled
    from weedlib.qt import QPainterPath, load_widgets
    from weedlines_job import write_correction_result

    QtCore, QtGui, QtWidgets = load_widgets()
    defaults = dict(defaults or {})
    check = classify_figures(records)
    blocked = bool(check.defects)

    app = QtWidgets.QApplication.instance()
    owns_app = False
    if app is None:
        app = QtWidgets.QApplication([])
        owns_app = True

    dialog = QtWidgets.QDialog()
    dialog.setWindowTitle('Weedlines')
    dialog.doc_width = width
    dialog.doc_height = height
    dialog.doc_viewbox = view_box
    dialog.resize(720, 640)
    # WindowModal: don't freeze every Qt window in a multi-app session;
    # when hosted inside Inkscape's process this still blocks that app.
    dialog.setWindowModality(QtCore.Qt.WindowModal)

    root = QtWidgets.QVBoxLayout(dialog)

    form = QtWidgets.QFormLayout()
    mode_box = QtWidgets.QComboBox()
    mode_box.setObjectName('mode')
    mode_box.addItem('Frame (box)', 'frame')
    mode_box.addItem('Grid (clipped)', 'grid')
    mode_box.addItem('Island hop', 'island-hop')
    want_mode = str(defaults.get('mode', 'frame')).lower()
    for i in range(mode_box.count()):
        if mode_box.itemData(i) == want_mode:
            mode_box.setCurrentIndex(i)
            break
    pad_spin = QtWidgets.QDoubleSpinBox()
    pad_spin.setObjectName('padding')
    pad_spin.setRange(0.0, 200.0)
    pad_spin.setDecimals(2)
    pad_spin.setValue(float(defaults.get('padding', 4.0)))
    space_spin = QtWidgets.QDoubleSpinBox()
    space_spin.setObjectName('spacing')
    space_spin.setRange(1.0, 200.0)
    space_spin.setDecimals(2)
    space_spin.setValue(float(defaults.get('spacing', 25.0)))
    collar_spin = QtWidgets.QDoubleSpinBox()
    collar_spin.setRange(0.0, 50.0)
    collar_spin.setDecimals(2)
    collar_spin.setValue(float(defaults.get('collar', 4.0)))
    layer_edit = QtWidgets.QLineEdit(str(defaults.get('layer_name', 'Weed lines')))
    form.addRow('Mode', mode_box)
    form.addRow('Padding (mm)', pad_spin)
    form.addRow('Grid spacing (mm)', space_spin)
    form.addRow('Collar (mm, island-hop)', collar_spin)
    form.addRow('Output layer', layer_edit)

    def _color_edit(name, initial):
        edit = QtWidgets.QLineEdit(initial)
        edit.setObjectName(name)
        edit.setMaxLength(7)
        edit.setProperty('color', initial)
        _tint_edit(edit, initial)
        return edit

    swap_btn = QtWidgets.QPushButton('Swap subject and weed area')
    swap_btn.setObjectName('swap')
    form.addRow(swap_btn)
    light_edit = _color_edit('checkerboard-light', '#E6E6E6')
    dark_edit = _color_edit('checkerboard-dark', '#CFCFCF')
    weed_edit = _color_edit('weed-line-color', '#FF0000')
    subject_edit = _color_edit('default-subject-color', '#FFFFFF')
    form.addRow('Checkerboard light', light_edit)
    form.addRow('Checkerboard dark', dark_edit)
    form.addRow('Weed line color', weed_edit)
    form.addRow('Default subject color', subject_edit)
    root.addLayout(form)

    btn_row = QtWidgets.QHBoxLayout()
    start_btn = QtWidgets.QPushButton('Start Algorithm')
    start_btn.setObjectName('start')
    pause_btn = QtWidgets.QPushButton('Pause')
    pause_btn.hide()
    cancel_btn = QtWidgets.QPushButton('Cancel…')
    cancel_btn.hide()
    apply_btn = QtWidgets.QPushButton('Apply')
    apply_btn.setObjectName('apply')
    apply_btn.setEnabled(False)
    close_btn = QtWidgets.QPushButton('Close')
    btn_row.addWidget(start_btn)
    btn_row.addWidget(pause_btn)
    btn_row.addWidget(cancel_btn)
    btn_row.addStretch(1)
    btn_row.addWidget(apply_btn)
    btn_row.addWidget(close_btn)
    root.addLayout(btn_row)

    status_label = QtWidgets.QLabel('')
    status_label.setStyleSheet('color: #c0c0c0;')
    root.addWidget(status_label)

    log_label = QtWidgets.QLabel('Algorithm output (stdout / stderr)')
    root.addWidget(log_label)
    log_view = QtWidgets.QPlainTextEdit()
    log_view.setReadOnly(True)
    log_view.setMaximumBlockCount(5000)
    log_view.setMinimumHeight(72)
    log_view.setSizePolicy(
        QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
    splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
    splitter.addWidget(log_view)

    scene = QtWidgets.QGraphicsScene()
    scene.setBackgroundBrush(QtGui.QBrush(QtCore.Qt.NoBrush))
    view = QtWidgets.QGraphicsView(scene)
    view.setObjectName('preview')
    view.setRenderHints(
        QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform)
    view.setBackgroundBrush(QtGui.QBrush(QtGui.QColor('#1e1e1e')))
    view.setMinimumHeight(180)
    splitter.addWidget(view)
    splitter.setStretchFactor(0, 0)
    splitter.setStretchFactor(1, 1)
    splitter.setSizes([90, 400])
    root.addWidget(splitter, stretch=1)

    return_line = QtWidgets.QLabel()
    return_line.setObjectName('return-line')
    return_line.setWordWrap(True)
    return_line.setTextFormat(QtCore.Qt.PlainText)
    return_line.setText(_defect_line(check.defects))
    return_btn = QtWidgets.QPushButton('Return to Inkscape')
    return_btn.setObjectName('return-inkscape')
    arrows_btn = None
    if blocked:
        arrows_btn = QtWidgets.QPushButton(
            'Return to Inkscape with correction arrows')
        arrows_btn.setObjectName('return-arrows')
    return_row = QtWidgets.QHBoxLayout()
    return_row.addWidget(return_btn)
    if arrows_btn is not None:
        return_row.addWidget(arrows_btn)
    return_row.addStretch(1)
    root.addWidget(return_line)
    root.addLayout(return_row)

    state = {
        'busy': False,
        'paused': False,
        'cancel': threading.Event(),
        'pause': threading.Event(),  # set => paused (worker blocks)
        'result': None,
        'error': None,
        'log_q': deque(),
        'seg_q': deque(),
        'weed_items': [],
        'preview_items': [],
        'arrows': {},
        'swapped': False,
        'regions': None,
        'work': None,
        'solved_keep': None,
        'solved_pad': None,
        'accepted': False,
        'thread': None,
    }
    CheckerItem = _checker_type(QtWidgets, QtGui, QtCore)

    def append_log(text):
        log_view.moveCursor(QtGui.QTextCursor.End)
        log_view.insertPlainText(text)
        log_view.moveCursor(QtGui.QTextCursor.End)

    def drain_platform_lines():
        """Pull Qt/OS stderr captures into the dialog log (not Inkscape)."""
        if platform_lines is None:
            return
        while platform_lines:
            try:
                line = platform_lines.popleft()
            except IndexError:
                break
            append_log('[platform] %s\n' % line)

    # QApplication often emits the Wayland warning during construction above.
    drain_platform_lines()

    def set_controls(busy, paused=False):
        state['busy'] = busy
        state['paused'] = bool(paused) if busy else False
        start_btn.setVisible(not busy)
        start_btn.setEnabled((not busy) and not blocked)
        pause_btn.setVisible(busy)
        pause_btn.setEnabled(busy and not state['cancel'].is_set())
        if busy and state['paused']:
            pause_btn.setText('Resume')
            status_label.setText('Paused — inspect preview, then Resume or Cancel.')
        elif busy:
            pause_btn.setText('Pause')
            status_label.setText('Running…')
        else:
            pause_btn.setText('Pause')
            status_label.setText('')
        cancel_btn.setVisible(busy)
        cancel_btn.setEnabled(busy and not state['cancel'].is_set())
        if state['cancel'].is_set() and busy:
            cancel_btn.setText('Cancelling…')
            cancel_btn.setEnabled(False)
            pause_btn.setEnabled(False)
        else:
            cancel_btn.setText('Cancel…')
        mode_box.setEnabled(not busy)
        pad_spin.setEnabled(not busy)
        space_spin.setEnabled(not busy)
        collar_spin.setEnabled(not busy)
        layer_edit.setEnabled(not busy)
        swap_btn.setEnabled(not busy)
        light_edit.setEnabled(not busy)
        dark_edit.setEnabled(not busy)
        weed_edit.setEnabled(not busy)
        subject_edit.setEnabled(not busy)
        apply_btn.setEnabled((not busy) and state['result'] is not None)

    def _fit():
        rect = scene.itemsBoundingRect()
        if rect.isNull():
            return
        view.fitInView(rect, QtCore.Qt.KeepAspectRatio)

    def _fill(path, color, z_value):
        if path is None or path.isEmpty():
            return
        pen = QtGui.QPen(QtCore.Qt.NoPen)
        item = scene.addPath(path, pen, QtGui.QBrush(QtGui.QColor(color)))
        item.setZValue(z_value)
        state['preview_items'].append(item)

    def refresh_preview():
        for item in state['preview_items']:
            scene.removeItem(item)
        state['preview_items'] = []
        regions = subject_weed_regions(
            check.figures, swap=state['swapped'])
        state['regions'] = regions
        light = light_edit.property('color')
        dark = dark_edit.property('color')
        weed_color = weed_edit.property('color')
        subject_color = subject_edit.property('color')
        # The work rect covers the subject. Subject paint sits above it.
        weed_path = _with_work_region(
            regions.weed_area, state['work'], QPainterPath, QtCore.Qt)
        if not weed_path.isEmpty():
            checker = CheckerItem(weed_path, light, dark, _CHECKER_TILE)
            checker.setZValue(0)
            scene.addItem(checker)
            state['preview_items'].append(checker)
        subject = regions.subject
        if subject is not None and not subject.isEmpty():
            painted = QPainterPath(subject)
            painted.setFillRule(QtCore.Qt.OddEvenFill)
            _fill(painted, subject_color, 10)
        for figure in check.figures:
            solid = _hex_color(figure.fill)
            if solid is None or subject is None:
                continue
            # Painted interior. Odd-even of the whole path drops a crossing lens.
            interior = _painted_parts(split_painter_path(figure.path))
            part = interior.intersected(subject)
            if part.isEmpty():
                continue
            _fill(part, solid, 11)
        grouped = {}
        for defect in check.defects:
            grouped.setdefault(defect.kind, []).append(defect.target)
        arrow_paths = {}
        for kind in _ARROW_KINDS:
            targets = grouped.get(kind)
            if not targets:
                continue
            batch = build_arrow_paths(kind, targets, regions.bounds)
            arrow_paths[kind] = batch
            for arrow in batch:
                shaft = scene.addPath(
                    arrow.shaft,
                    _line_pen(QtGui, QtCore, arrow.color),
                    QtGui.QBrush(QtCore.Qt.NoBrush))
                shaft.setZValue(30)
                state['preview_items'].append(shaft)
                head = scene.addPath(
                    arrow.head,
                    QtGui.QPen(QtCore.Qt.NoPen),
                    QtGui.QBrush(QtGui.QColor(arrow.color)))
                head.setZValue(30)
                state['preview_items'].append(head)
        state['arrows'] = arrow_paths
        weed_pen = _line_pen(QtGui, QtCore, weed_color)
        for item in state['weed_items']:
            item.setPen(weed_pen)
            item.setZValue(20)
        _fit()

    def clear_weed_items():
        for item in state['weed_items']:
            scene.removeItem(item)
        state['weed_items'] = []

    def on_start():
        if state['busy'] or blocked:
            return
        clear_weed_items()
        state['work'] = None
        state['result'] = None
        state['error'] = None
        state['cancel'].clear()
        state['pause'].clear()
        state['seg_q'].clear()
        apply_btn.setEnabled(False)
        log_view.clear()
        append_log('Starting %s…\n' % mode_box.currentData())
        set_controls(True, paused=False)
        refresh_preview()

        mode = mode_box.currentData()
        padding = float(pad_spin.value())
        spacing = float(space_spin.value())
        collar = float(collar_spin.value())
        keep = QPainterPath(state['regions'].subject)
        state['solved_keep'] = keep
        state['solved_pad'] = [padding, padding, padding, padding]

        def work():
            from weedlib import progress as weed_progress
            log_q = state['log_q']
            seg_q = state['seg_q']
            old_out, old_err = sys.stdout, sys.stderr
            sys.stdout = _StreamToQueue(log_q)
            sys.stderr = _StreamToQueue(log_q)
            handler = _QueueLogHandler(log_q)
            handler.setFormatter(logging.Formatter(
                '%(levelname)s %(name)s: %(message)s'))
            weed_log = logging.getLogger('weedlib')
            # Avoid double lines: debug.py also installs a StreamHandler to
            # stderr, and we redirect stderr into the same queue.
            removed_handlers = []
            for h in list(weed_log.handlers):
                if isinstance(h, logging.StreamHandler) and h is not handler:
                    weed_log.removeHandler(h)
                    removed_handlers.append(h)
            weed_log.addHandler(handler)
            weed_log.setLevel(logging.DEBUG)
            weed_log.propagate = False
            prev_dbg = os.environ.get('WEEDLINES_LOG') or os.environ.get(
                'INKCUT_WEED_DEBUG')
            if not prev_dbg:
                os.environ['WEEDLINES_LOG'] = '1'

            def on_phase(name):
                log_q.append('[phase] %s\n' % name)

            def on_seg(seg):
                if state['cancel'].is_set():
                    raise WeedCancelled('weed generation cancelled')
                seg_q.append(seg)

            weed_progress.install(
                progress=on_phase,
                cancel=lambda: state['cancel'].is_set(),
                pause=lambda: state['pause'].is_set(),
                geometry=on_seg,
            )
            try:
                path = generate_weeds(
                    keep,
                    mode=mode,
                    padding=[padding] * 4,
                    spacing=spacing,
                    collar=collar,
                )
                if state['cancel'].is_set():
                    raise WeedCancelled('weed generation cancelled')
                state['result'] = path if path is not None else QPainterPath()
            except WeedCancelled as exc:
                state['error'] = exc
                state['result'] = None
                log_q.append('Cancelled.\n')
            except Exception as exc:
                state['error'] = exc
                state['result'] = None
                log_q.append('Error: %s\n' % exc)
            finally:
                weed_progress.clear()
                sys.stdout = old_out
                sys.stderr = old_err
                weed_log.removeHandler(handler)
                for h in removed_handlers:
                    weed_log.addHandler(h)
                if not prev_dbg:
                    os.environ.pop('WEEDLINES_LOG', None)
                    os.environ.pop('INKCUT_WEED_DEBUG', None)

        thread = threading.Thread(target=work)
        thread.daemon = True
        state['thread'] = thread
        thread.start()

        last_fit = [0.0]

        def pump():
            drain_platform_lines()
            while state['log_q']:
                append_log(state['log_q'].popleft())
            added = False
            if (state['seg_q'] and state['work'] is None
                    and state['solved_keep'] is not None):
                state['work'] = padded_work_rect(
                    state['solved_keep'], state['solved_pad'])
                refresh_preview()
            weed_pen = _line_pen(QtGui, QtCore, weed_edit.property('color'))
            for _ in range(200):
                if not state['seg_q']:
                    break
                seg = state['seg_q'].popleft()
                try:
                    x0, y0, x1, y1 = seg
                except Exception:
                    continue
                item = scene.addLine(x0, y0, x1, y1, weed_pen)
                item.setZValue(20)
                state['weed_items'].append(item)
                added = True
            if added and (time.time() - last_fit[0]) > 0.4:
                view.fitInView(
                    scene.itemsBoundingRect(), QtCore.Qt.KeepAspectRatio)
                last_fit[0] = time.time()

            if thread.is_alive() or state['seg_q'] or state['log_q']:
                QtCore.QTimer.singleShot(50, pump)
                return
            drain_platform_lines()

            set_controls(False)
            if state['error'] is not None:
                if isinstance(state['error'], WeedCancelled):
                    append_log('Algorithm cancelled.\n')
                else:
                    append_log('Algorithm failed: %s\n' % state['error'])
                apply_btn.setEnabled(False)
                return
            if state['result'] is None or state['result'].isEmpty():
                append_log('No weed cuts produced.\n')
                apply_btn.setEnabled(False)
                return
            append_log('Done. Review cuts, then Apply.\n')
            view.fitInView(
                scene.itemsBoundingRect(), QtCore.Qt.KeepAspectRatio)
            apply_btn.setEnabled(True)

        QtCore.QTimer.singleShot(50, pump)

    def on_pause_toggle():
        if not state['busy'] or state['cancel'].is_set():
            return
        if state['pause'].is_set():
            state['pause'].clear()
            append_log('Resumed.\n')
            set_controls(True, paused=False)
        else:
            state['pause'].set()
            append_log('Paused — worker waiting; inspect preview.\n')
            set_controls(True, paused=True)

    def on_cancel():
        if not state['busy']:
            return
        # Wake a paused worker so it can see cancel
        state['pause'].clear()
        state['cancel'].set()
        append_log('Cancel requested — stopping algorithm…\n')
        set_controls(True, paused=False)
        cancel_btn.setEnabled(False)
        cancel_btn.setText('Cancelling…')
        pause_btn.setEnabled(False)

    def on_apply():
        if state['result'] is None or state['busy']:
            return
        state['accepted'] = True
        dialog.accept()

    def on_close():
        if state['busy']:
            state['pause'].clear()
            state['cancel'].set()
            thread = state.get('thread')
            if thread is not None and thread.is_alive():
                thread.join(2.0)
        dialog.reject()

    def on_return():
        on_close()

    def _doc_attrs():
        doc_attrs = {}
        if dialog.doc_width:
            doc_attrs['width'] = dialog.doc_width
        if dialog.doc_height:
            doc_attrs['height'] = dialog.doc_height
        if dialog.doc_viewbox:
            doc_attrs['viewBox'] = dialog.doc_viewbox
        return doc_attrs

    def on_return_arrows():
        if not blocked or state['busy']:
            return
        arrows = state.get('arrows') or {}
        if not arrows:
            return
        write_correction_result(arrows, doc_attrs=_doc_attrs())
        return_line.setText(_IMPORT_SENTENCE)

    def _commit_color(edit):
        if state['busy']:
            edit.blockSignals(True)
            edit.setText(edit.property('color'))
            edit.blockSignals(False)
            return
        color = _hex_color(edit.text())
        if color is None or color == edit.property('color'):
            edit.blockSignals(True)
            edit.setText(edit.property('color'))
            edit.blockSignals(False)
            return
        edit.blockSignals(True)
        edit.setText(color)
        edit.setProperty('color', color)
        edit.blockSignals(False)
        _tint_edit(edit, color)
        refresh_preview()

    def _on_swap():
        if state['busy']:
            return
        state['swapped'] = not state['swapped']
        refresh_preview()

    start_btn.clicked.connect(on_start)
    pause_btn.clicked.connect(on_pause_toggle)
    cancel_btn.clicked.connect(on_cancel)
    apply_btn.clicked.connect(on_apply)
    close_btn.clicked.connect(on_close)
    return_btn.clicked.connect(on_return)
    if arrows_btn is not None:
        arrows_btn.clicked.connect(on_return_arrows)
    swap_btn.clicked.connect(_on_swap)
    for _edit in (light_edit, dark_edit, weed_edit, subject_edit):
        _edit.editingFinished.connect(
            lambda edit=_edit: _commit_color(edit))

    hint = QtWidgets.QLabel(
        'Builds weed cuts only (no cutter travel planning). '
        'Pause freezes the algorithm so you can inspect the live preview, '
        'then Resume or Cancel. '
        'After Apply, use Extensions → Weedlines → Import last result '
        'in Inkscape — that brings back the design and cuts together at '
        'the original size and position.')
    hint.setWordWrap(True)
    root.addWidget(hint)

    refresh_preview()
    set_controls(False)

    def _shown():
        _fit()
        if ready is None:
            return
        try:
            ready(dialog)
        except Exception as exc:
            state['ready_error'] = exc
            dialog.reject()

    QtCore.QTimer.singleShot(0, _shown)

    result_code = dialog.exec_()
    layer_name = layer_edit.text().strip() or 'Weed lines'
    weed = state['result'] if state['accepted'] and result_code else None
    if owns_app and quit_app:
        app.quit()
    ready_error = state.pop('ready_error', None)
    if ready_error is not None:
        raise ready_error
    if weed is None:
        return None, None, None
    return weed, layer_name, weed_edit.property('color')
