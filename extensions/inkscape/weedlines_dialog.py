# -*- coding: utf-8 -*-
"""Interactive Weedlines dialog for the Inkscape extension.

Start / Cancel, scrolling stdout+stderr log (keeps Inkscape from showing
the "additional data" popup), and a live graphics view of accepted cuts.
"""
from __future__ import division

import logging
import os
import sys
import threading
import time
from collections import deque


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


def run_weedlines_dialog(keep_path, defaults=None):
    """Show the weedlines UI. Returns ``(weed_path, layer_name)`` or ``(None, None)``.

    *keep_path* is design geometry (QPainterPath). *defaults* may include
    mode, padding, spacing, collar, layer_name.
    """
    from weedlib.qt import QPainterPath, load_widgets
    from weedlib.progress import WeedCancelled
    from weedlib import generate_weeds

    QtCore, QtGui, QtWidgets = load_widgets()
    defaults = dict(defaults or {})

    app = QtWidgets.QApplication.instance()
    owns_app = False
    if app is None:
        app = QtWidgets.QApplication([])
        owns_app = True

    dialog = QtWidgets.QDialog()
    dialog.setWindowTitle('Weedlines')
    dialog.resize(720, 640)
    dialog.setWindowModality(QtCore.Qt.ApplicationModal)

    root = QtWidgets.QVBoxLayout(dialog)

    form = QtWidgets.QFormLayout()
    mode_box = QtWidgets.QComboBox()
    mode_box.addItem('Frame (box)', 'frame')
    mode_box.addItem('Grid (clipped)', 'grid')
    mode_box.addItem('Island hop', 'island-hop')
    want_mode = str(defaults.get('mode', 'frame')).lower()
    for i in range(mode_box.count()):
        if mode_box.itemData(i) == want_mode:
            mode_box.setCurrentIndex(i)
            break
    pad_spin = QtWidgets.QDoubleSpinBox()
    pad_spin.setRange(0.0, 200.0)
    pad_spin.setDecimals(2)
    pad_spin.setValue(float(defaults.get('padding', 4.0)))
    space_spin = QtWidgets.QDoubleSpinBox()
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
    root.addLayout(form)

    btn_row = QtWidgets.QHBoxLayout()
    start_btn = QtWidgets.QPushButton('Start Algorithm')
    cancel_btn = QtWidgets.QPushButton('Cancel…')
    cancel_btn.hide()
    apply_btn = QtWidgets.QPushButton('Apply layer & Close')
    apply_btn.setEnabled(False)
    close_btn = QtWidgets.QPushButton('Close')
    btn_row.addWidget(start_btn)
    btn_row.addWidget(cancel_btn)
    btn_row.addStretch(1)
    btn_row.addWidget(apply_btn)
    btn_row.addWidget(close_btn)
    root.addLayout(btn_row)

    log_label = QtWidgets.QLabel('Algorithm output (stdout / stderr)')
    root.addWidget(log_label)
    log_view = QtWidgets.QPlainTextEdit()
    log_view.setReadOnly(True)
    log_view.setMaximumBlockCount(5000)
    log_view.setMinimumHeight(72)
    log_view.setSizePolicy(
        QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
    # User-expandable: put log in a splitter with the preview
    splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
    splitter.addWidget(log_view)

    scene = QtWidgets.QGraphicsScene()
    view = QtWidgets.QGraphicsView(scene)
    view.setRenderHints(
        QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform)
    view.setBackgroundBrush(QtGui.QBrush(QtGui.QColor('#1e1e1e')))
    view.setMinimumHeight(180)
    splitter.addWidget(view)
    splitter.setStretchFactor(0, 0)
    splitter.setStretchFactor(1, 1)
    splitter.setSizes([90, 400])
    root.addWidget(splitter, stretch=1)

    # Draw keep geometry (design) once
    keep_pen = QtGui.QPen(QtGui.QColor('#6a9fb5'))
    keep_pen.setWidthF(0.0)
    keep_pen.setCosmetic(True)
    weed_pen = QtGui.QPen(QtGui.QColor('#e07020'))
    weed_pen.setWidthF(0.0)
    weed_pen.setCosmetic(True)
    _add_path_to_scene(scene, keep_path, keep_pen, QtCore)
    view.fitInView(scene.itemsBoundingRect(), QtCore.Qt.KeepAspectRatio)

    state = {
        'busy': False,
        'cancel': threading.Event(),
        'result': None,
        'error': None,
        'log_q': deque(),
        'seg_q': deque(),
        'weed_items': [],
        'accepted': False,
        'thread': None,
    }

    def append_log(text):
        log_view.moveCursor(QtGui.QTextCursor.End)
        log_view.insertPlainText(text)
        log_view.moveCursor(QtGui.QTextCursor.End)

    def set_busy(busy):
        state['busy'] = busy
        start_btn.setVisible(not busy)
        start_btn.setEnabled(not busy)
        cancel_btn.setVisible(busy)
        cancel_btn.setEnabled(busy)
        cancel_btn.setText('Cancel…')
        mode_box.setEnabled(not busy)
        pad_spin.setEnabled(not busy)
        space_spin.setEnabled(not busy)
        collar_spin.setEnabled(not busy)
        layer_edit.setEnabled(not busy)
        apply_btn.setEnabled((not busy) and state['result'] is not None)

    def clear_weed_items():
        for item in state['weed_items']:
            scene.removeItem(item)
        state['weed_items'] = []

    def on_start():
        if state['busy']:
            return
        clear_weed_items()
        state['result'] = None
        state['error'] = None
        state['cancel'].clear()
        state['seg_q'].clear()
        apply_btn.setEnabled(False)
        log_view.clear()
        append_log('Starting %s…\n' % mode_box.currentData())
        set_busy(True)

        mode = mode_box.currentData()
        padding = float(pad_spin.value())
        spacing = float(space_spin.value())
        collar = float(collar_spin.value())
        keep = keep_path

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
            root_log = logging.getLogger()
            weed_log = logging.getLogger('weedlib')
            root_log.addHandler(handler)
            weed_log.addHandler(handler)
            prev_dbg = os.environ.get('WEEDLINES_LOG') or os.environ.get('INKCUT_WEED_DEBUG')
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
                root_log.removeHandler(handler)
                weed_log.removeHandler(handler)
                if not prev_dbg:
                    os.environ.pop('WEEDLINES_LOG', None)
                    os.environ.pop('INKCUT_WEED_DEBUG', None)

        thread = threading.Thread(target=work)
        thread.daemon = True
        state['thread'] = thread
        thread.start()

        last_fit = [0.0]

        def pump():
            while state['log_q']:
                append_log(state['log_q'].popleft())
            added = False
            # Drain a bounded batch so the UI stays responsive
            for _ in range(200):
                if not state['seg_q']:
                    break
                seg = state['seg_q'].popleft()
                try:
                    x0, y0, x1, y1 = seg
                except Exception:
                    continue
                item = scene.addLine(x0, y0, x1, y1, weed_pen)
                state['weed_items'].append(item)
                added = True
            if added and (time.time() - last_fit[0]) > 0.4:
                view.fitInView(
                    scene.itemsBoundingRect(), QtCore.Qt.KeepAspectRatio)
                last_fit[0] = time.time()

            if thread.is_alive() or state['seg_q'] or state['log_q']:
                QtCore.QTimer.singleShot(50, pump)
                return

            set_busy(False)
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
            append_log('Done. Review cuts, then Apply layer & Close.\n')
            view.fitInView(
                scene.itemsBoundingRect(), QtCore.Qt.KeepAspectRatio)
            apply_btn.setEnabled(True)

        QtCore.QTimer.singleShot(50, pump)

    def on_cancel():
        if not state['busy']:
            return
        state['cancel'].set()
        append_log('Cancel requested — stopping algorithm…\n')
        cancel_btn.setEnabled(False)
        cancel_btn.setText('Cancelling…')

    def on_apply():
        if state['result'] is None or state['busy']:
            return
        state['accepted'] = True
        dialog.accept()

    def on_close():
        if state['busy']:
            state['cancel'].set()
            thread = state.get('thread')
            if thread is not None and thread.is_alive():
                thread.join(2.0)
        dialog.reject()

    start_btn.clicked.connect(on_start)
    cancel_btn.clicked.connect(on_cancel)
    apply_btn.clicked.connect(on_apply)
    close_btn.clicked.connect(on_close)

    hint = QtWidgets.QLabel(
        'Builds a Weedlines layer only (no cutter travel planning). '
        'Send the design + this layer to your cutter app afterward. '
        'If the desktop asks to Force Quit Inkscape, choose Wait — this dialog '
        'is still running in the extension process.')
    hint.setWordWrap(True)
    root.addWidget(hint)

    result_code = dialog.exec_()
    layer_name = layer_edit.text().strip() or 'Weed lines'
    weed = state['result'] if state['accepted'] and result_code else None
    if owns_app:
        app.quit()
    if weed is None:
        return None, None
    return weed, layer_name


def _add_path_to_scene(scene, path, pen, QtCore):
    if path is None or path.isEmpty():
        return
    # QPainterPath can be added directly in Qt
    item = scene.addPath(path, pen)
    return item
