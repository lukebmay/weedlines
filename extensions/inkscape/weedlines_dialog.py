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
import multiprocessing
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
_SURROUND_MODE = 'Surround and Conquer'
_CUT_MODES = ('frame', 'grid', 'island-hop')
# Quarter-inch baseline, passed through as document user units.
_JOIN_GAP = 6.35


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


def _opening_mode(defaults):
    """Entry to select. Missing or blank opens on Surround and Conquer."""
    if 'mode' not in defaults or defaults.get('mode') is None:
        return _SURROUND_MODE
    text = str(defaults.get('mode')).strip()
    if not text:
        return _SURROUND_MODE
    folded = text.lower()
    if folded == _SURROUND_MODE.lower():
        return _SURROUND_MODE
    if folded in _CUT_MODES:
        return folded
    return 'frame'


def _surround_distance(bounds):
    """Five percent of the smaller side. Zero when the bounds are empty."""
    if bounds is None or not bounds.isValid():
        return 0.0
    side = min(float(bounds.width()), float(bounds.height()))
    if side <= 0.0:
        return 0.0
    return 0.05 * side


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


class _QueueLogHandler(logging.Handler):
    def __init__(self, queue):
        logging.Handler.__init__(self)
        self._queue = queue

    def emit(self, record):
        try:
            self._queue.append(self.format(record) + '\n')
        except Exception:
            pass


# Plain value the next ask passes to the spawn target. Unset does nothing.
_ASK_HOLD = None
# Plain text the child writes to stdout and stderr. Unset writes nothing.
_ASK_TRACE = None


def _burn_hold(hold):
    """Tight loop before a library call. Unset hold returns immediately.

    The switch interval keeps this loop from yielding the interpreter,
    so the same loop on a thread in this process cannot service the GUI.
    """
    if hold is None or hold is False:
        return
    try:
        limit = int(hold)
    except (TypeError, ValueError):
        return
    if limit <= 0:
        return
    interval = sys.getswitchinterval()
    sys.setswitchinterval(1.0e9)
    try:
        count = 0
        while count < limit:
            count += 1
    finally:
        sys.setswitchinterval(interval)


class _ConnLog(object):
    """Queue stand-in: each record is one log message."""

    def __init__(self, conn):
        self._conn = conn

    def append(self, text):
        self._conn.send(('log', text))


class _ConnStream(object):
    """File-like object that sends each line as a log message."""

    def __init__(self, conn):
        self._conn = conn
        self._buf = ''

    def write(self, data):
        if not data:
            return 0
        if not isinstance(data, str):
            data = data.decode('utf-8', 'replace')
        self._buf += data
        while '\n' in self._buf:
            line, self._buf = self._buf.split('\n', 1)
            self._conn.send(('log', line + '\n'))
        return len(data)

    def flush(self):
        if self._buf:
            self._conn.send(('log', self._buf))
            self._buf = ''

    def isatty(self):
        return False


def _plain_int(value):
    if callable(value):
        value = value()
    number = getattr(value, 'value', None)
    if number is not None and not callable(number):
        try:
            return int(number)
        except (TypeError, ValueError):
            pass
    return int(value)


def _path_elements(path):
    if path is None:
        return []
    elements = []
    count = path.elementCount()
    for index in range(count):
        element = path.elementAt(index)
        kind = element.type
        if callable(kind):
            kind = kind()
        x = element.x() if callable(element.x) else element.x
        y = element.y() if callable(element.y) else element.y
        elements.append((_plain_int(kind), float(x), float(y)))
    return elements


def _rule_code(path):
    from weedlib.qt import Qt
    if path is None:
        return 'odd'
    rule = path.fillRule()
    if callable(rule):
        rule = rule()
    if rule == Qt.WindingFill:
        return 'wind'
    return 'odd'


def _pack_path(path):
    if path is None:
        return ([], 'odd')
    return (_path_elements(path), _rule_code(path))


def _unpack_path(elements, rule):
    from weedlib.qt import QPainterPath, Qt
    path = QPainterPath()
    if not elements:
        return path
    move = _plain_int(QPainterPath.MoveToElement)
    line = _plain_int(QPainterPath.LineToElement)
    curve = _plain_int(QPainterPath.CurveToElement)
    data = _plain_int(QPainterPath.CurveToDataElement)
    index = 0
    count = len(elements)
    while index < count:
        kind, x, y = elements[index]
        if kind == move:
            path.moveTo(x, y)
            index += 1
        elif kind == line:
            path.lineTo(x, y)
            index += 1
        elif kind == curve:
            points = [(x, y)]
            nxt = index + 1
            while nxt < count and elements[nxt][0] == data:
                points.append((elements[nxt][1], elements[nxt][2]))
                nxt += 1
            if len(points) == 2:
                path.quadTo(
                    points[0][0], points[0][1], points[1][0], points[1][1])
            elif len(points) == 3:
                path.cubicTo(
                    points[0][0], points[0][1],
                    points[1][0], points[1][1],
                    points[2][0], points[2][1])
            else:
                raise ValueError('path element is not plain coordinates')
            index = nxt
        else:
            raise ValueError('path element is not plain coordinates')
    if rule == 'wind':
        path.setFillRule(Qt.WindingFill)
    else:
        path.setFillRule(Qt.OddEvenFill)
    return path


def _point_xy(point):
    x = getattr(point, 'x', None)
    y = getattr(point, 'y', None)
    if x is not None and y is not None:
        if callable(x):
            x, y = x(), y()
        return float(x), float(y)
    x, y = point
    return float(x), float(y)


def _box_tuple(rect):
    return (
        float(rect.x()), float(rect.y()),
        float(rect.width()), float(rect.height()))


def _empty_inbox():
    return {
        'figures': [],
        'defects': [],
        'subject': None,
        'weed': None,
        'bounds': None,
        'fills': [],
        'arrows': [],
        'surrounds': [],
        'result': None,
        'error': None,
        'cancelled': False,
    }


def _send_call(conn, name, swap=None):
    if swap is None:
        conn.send(('call', name))
    else:
        conn.send(('call', name, bool(swap)))


def _arm_solver_log(conn):
    """Same ``WEEDLINES_LOG`` setup the solver used in-process.

    A deliberate ``0`` or ``2`` is left alone. Unset becomes ``1``.
    The weedlib handler sends lines on the channel. Stdout and stderr
    are already that channel.
    """
    handler = _QueueLogHandler(_ConnLog(conn))
    handler.setFormatter(logging.Formatter(
        '%(levelname)s %(name)s: %(message)s'))
    weed_log = logging.getLogger('weedlib')
    removed = []
    for existing in list(weed_log.handlers):
        if isinstance(existing, logging.StreamHandler) and existing is not handler:
            weed_log.removeHandler(existing)
            removed.append(existing)
    weed_log.addHandler(handler)
    weed_log.setLevel(logging.DEBUG)
    weed_log.propagate = False
    prev = os.environ.get('WEEDLINES_LOG') or os.environ.get('INKCUT_WEED_DEBUG')
    if not prev:
        os.environ['WEEDLINES_LOG'] = '1'
    return weed_log, handler, removed, prev


def _disarm_solver_log(weed_log, handler, removed, prev):
    weed_log.removeHandler(handler)
    for existing in removed:
        weed_log.addHandler(existing)
    if not prev:
        os.environ.pop('WEEDLINES_LOG', None)
        os.environ.pop('INKCUT_WEED_DEBUG', None)


def _ask_solver(request, conn, pausing, cancelled):
    """One frame, grid, or island-hop run. Plain messages back. No window."""
    from weedlib import generate_weeds
    from weedlib import progress as weed_progress
    from weedlib.progress import WeedCancelled

    mode = request.get('mode') or 'frame'
    try:
        padding = [float(value) for value in (request.get('padding') or ())]
    except (TypeError, ValueError):
        padding = []
    try:
        spacing = float(request.get('spacing', 0.0))
    except (TypeError, ValueError):
        spacing = 0.0
    try:
        collar = float(request.get('collar', 0.0))
    except (TypeError, ValueError):
        collar = 0.0
    keep = _unpack_path(
        request.get('elements') or [], request.get('rule') or 'odd')
    elements, rule = _pack_path(keep)
    conn.send(('keep', str(mode), elements, rule))
    conn.send(('call', 'solver'))

    def on_phase(name):
        conn.send(('log', '[phase] %s\n' % name))

    def on_seg(seg):
        if cancelled.is_set():
            raise WeedCancelled('weed generation cancelled')
        try:
            x0, y0, x1, y1 = seg
        except (TypeError, ValueError):
            return
        conn.send(('segment', (float(x0), float(y0), float(x1), float(y1))))

    def on_focus(outline, line):
        conn.send(('focus', outline, line))

    weed_log, handler, removed, prev = _arm_solver_log(conn)
    weed_progress.install(
        progress=on_phase,
        cancel=lambda: cancelled.is_set(),
        pause=lambda: pausing.is_set(),
        geometry=on_seg,
        focus=on_focus,
    )
    try:
        path = generate_weeds(
            keep,
            mode=mode,
            padding=padding,
            spacing=spacing,
            collar=collar,
        )
        if cancelled.is_set():
            raise WeedCancelled('weed generation cancelled')
        if path is None:
            conn.send(('result', [], 'odd'))
        else:
            packed, packed_rule = _pack_path(path)
            conn.send(('result', packed, packed_rule))
    except WeedCancelled:
        conn.send(('log', 'Cancelled.\n'))
        raise
    except Exception as exc:
        conn.send(('log', 'Error: %s\n' % exc))
        raise
    finally:
        weed_progress.clear()
        _disarm_solver_log(weed_log, handler, removed, prev)


def _ask_classify(request, conn):
    from weedlib.figures import classify_figures
    _send_call(conn, 'classify')
    check = classify_figures(request.get('records') or [])
    for figure in check.figures:
        elements, rule = _pack_path(figure.path)
        conn.send(('figure', figure.id, figure.fill, elements, rule))
    for defect in check.defects:
        x, y = _point_xy(defect.target)
        conn.send(('defect', defect.kind, x, y))


def _ask_surround(request, conn):
    """One surround ask. Plain paths back. No window and no solver."""
    from weedlib import build_surrounds
    try:
        distance = float(request.get('distance', 0.0))
    except (TypeError, ValueError):
        distance = 0.0
    try:
        join_gap = float(request.get('join_gap', 0.0))
    except (TypeError, ValueError):
        join_gap = 0.0
    if distance < 0.0:
        distance = 0.0
    if join_gap < 0.0:
        join_gap = 0.0
    conn.send(('call', 'surrounds', distance, join_gap))
    subject = _unpack_path(
        request.get('elements') or [], request.get('rule') or 'odd')
    for path in build_surrounds(subject, distance, join_gap):
        elements, rule = _pack_path(path)
        conn.send(('surround', elements, rule))


def _ask_subject(request, conn):
    from weedlib.arrows import build_arrow_paths
    from weedlib.figures import Figure, _painted_parts, subject_weed_regions
    from weedlib.paths import split_painter_path
    _send_call(conn, 'subject', bool(request.get('swap')))
    figures = []
    for item in request.get('figures') or []:
        figures.append(Figure(
            id=item.get('id'),
            path=_unpack_path(item.get('elements') or [], item.get('rule') or 0),
            fill=item.get('fill'),
        ))
    regions = subject_weed_regions(figures, bool(request.get('swap')))
    elements, rule = _pack_path(regions.subject)
    conn.send(('path', 'subject', elements, rule))
    elements, rule = _pack_path(regions.weed_area)
    conn.send(('path', 'weed', elements, rule))
    conn.send(('bounds',) + _box_tuple(regions.bounds))
    subject = regions.subject
    for figure in figures:
        interior = _painted_parts(split_painter_path(figure.path))
        if subject is None:
            part = interior
        else:
            part = interior.intersected(subject)
        elements, rule = _pack_path(part)
        conn.send(('fill', figure.fill, elements, rule))
    grouped = {}
    for defect in request.get('defects') or []:
        grouped.setdefault(defect.get('kind'), []).append(
            (defect.get('x'), defect.get('y')))
    for kind in _ARROW_KINDS:
        targets = grouped.get(kind)
        if not targets:
            continue
        _send_call(conn, 'arrows')
        batch = build_arrow_paths(kind, targets, regions.bounds)
        for arrow in batch:
            shaft, shaft_rule = _pack_path(arrow.shaft)
            head, head_rule = _pack_path(arrow.head)
            conn.send((
                'arrow', kind, arrow.color,
                shaft, shaft_rule, head, head_rule))


def _run_geometry_ask(request, conn, pausing, cancelled):
    from weedlib.progress import WeedCancelled
    from weedlib import progress as weed_progress

    def on_focus(outline, line):
        conn.send(('focus', outline, line))

    weed_progress.install(
        pause=lambda: pausing.is_set(),
        cancel=lambda: cancelled.is_set(),
        focus=on_focus,
    )
    try:
        trace = request.get('trace')
        if trace:
            sys.stdout.write('%s\n' % trace)
            sys.stderr.write('%s\n' % trace)
        kind = request.get('kind')
        if kind == 'classify':
            _ask_classify(request, conn)
        elif kind == 'subject':
            _ask_subject(request, conn)
        elif kind == 'surround':
            _ask_surround(request, conn)
        elif kind == 'solver':
            _ask_solver(request, conn, pausing, cancelled)
        else:
            conn.send(('error', 'unknown ask'))
    except WeedCancelled:
        conn.send(('cancelled',))
    except Exception as exc:
        conn.send(('error', '%s' % exc))
    finally:
        weed_progress.clear()


def _geometry_worker(request, hold, conn, pausing, cancelled):
    """Spawn target. One ask, as messages. No window.

    The window already has a QApplication, so the parent starts this
    with spawn, not fork. A nested function cannot be the target.
    """
    old_out, old_err = sys.stdout, sys.stderr
    stream = _ConnStream(conn)
    sys.stdout = stream
    sys.stderr = stream
    try:
        # The hold is the CPU loop. Its stderr line is part of this log.
        if request.get('kind') == 'solver':
            try:
                hold_n = int(hold)
            except (TypeError, ValueError):
                hold_n = 0
            if hold_n > 0:
                sys.stderr.write('hold\n')
                sys.stderr.flush()
        _burn_hold(hold)
        _run_geometry_ask(request, conn, pausing, cancelled)
    finally:
        try:
            stream.flush()
        except Exception:
            pass
        sys.stdout = old_out
        sys.stderr = old_err
        try:
            conn.send(('done',))
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


def _spawn_ask(request, hold, pausing, cancelled):
    """Start one ask in its own interpreter. Returns ``(process, conn)``."""
    ctx = multiprocessing.get_context('spawn')
    parent_conn, child_conn = ctx.Pipe(duplex=False)
    proc = ctx.Process(
        target=_geometry_worker,
        args=(request, hold, child_conn, pausing, cancelled),
        daemon=True,
    )
    proc.start()
    child_conn.close()
    return proc, parent_conn


def run_weedlines_dialog(records, defaults=None, platform_lines=None,
                         quit_app=True, width=None, height=None,
                         view_box=None, display_unit=None,
                         user_unit_scale=None, ready=None):
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
    *height*, and *view_box* are the document size. *display_unit*
    is the unit the document names. An unset unit is px.
    *user_unit_scale* is how many inches one user unit is. *defaults*
    may include mode, padding, spacing, collar, layer_name. Missing or
    blank mode opens on Surround and Conquer. Start in that mode
    asks for the surround and paints it. It does not run a solver.
    Until that start, the window does not ask for a surround.

    *platform_lines* is an optional deque fed by ``NativeStdioCapture``
    (Qt/OS stderr). Those lines are shown in the log and never reach Inkscape.

    *quit_app*: when this call created the QApplication, quit it on return
    (default). Detached host passes False so it can show a follow-up box.

    *ready*, when given, is called with the dialog once the window is
    shown. The figure check, the subject and weed area, and any arrow
    paths finish after the window is visible and before that call.
    The surround is not asked until Start Algorithm. That ask uses
    the same spawn target. This thread builds the paths and paints
    them. It does not run the surround or a solver on this thread.
    """
    from weedlib import padded_work_rect
    from weedlib.arrows import ArrowPath
    from weedlib.qt import QPainterPath, load_widgets
    from weedlines_job import write_correction_result

    QtCore, QtGui, QtWidgets = load_widgets()
    defaults = dict(defaults or {})
    # Filled once the window is visible, before ready.
    check = None
    blocked = True

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
    dialog.display_unit = display_unit or 'px'
    if user_unit_scale is None:
        dialog.user_unit_scale = 1.0 / 96.0
    else:
        dialog.user_unit_scale = float(user_unit_scale)
    dialog.resize(720, 640)
    # WindowModal: don't freeze every Qt window in a multi-app session;
    # when hosted inside Inkscape's process this still blocks that app.
    dialog.setWindowModality(QtCore.Qt.WindowModal)

    root = QtWidgets.QVBoxLayout(dialog)

    form = QtWidgets.QFormLayout()
    mode_box = QtWidgets.QComboBox()
    mode_box.setObjectName('mode')
    mode_box.addItem(_SURROUND_MODE, _SURROUND_MODE)
    mode_box.addItem('Frame (box)', 'frame')
    mode_box.addItem('Grid (clipped)', 'grid')
    mode_box.addItem('Island hop', 'island-hop')
    want_mode = _opening_mode(defaults)
    for i in range(mode_box.count()):
        if mode_box.itemData(i) == want_mode:
            mode_box.setCurrentIndex(i)
            break
    distance_label = QtWidgets.QLabel('Surround distance')
    distance_spin = QtWidgets.QDoubleSpinBox()
    distance_spin.setObjectName('surround-distance')
    distance_spin.setDecimals(4)
    distance_spin.setSingleStep(0.1)
    distance_spin.setRange(0.0, 1000000.0)
    distance_spin.setValue(0.0)
    distance_spin.setEnabled(False)
    join_label = QtWidgets.QLabel('Join gap (mm)')
    join_spin = QtWidgets.QDoubleSpinBox()
    join_spin.setObjectName('join-gap')
    join_spin.setDecimals(4)
    join_spin.setSingleStep(0.1)
    join_spin.setRange(0.0, 1000000.0)
    join_spin.setValue(_JOIN_GAP)
    join_spin.setEnabled(False)
    change_btn = QtWidgets.QPushButton('Change surround')
    change_btn.setObjectName('change-surround')
    change_btn.setEnabled(False)
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
    form.addRow(distance_label, distance_spin)
    form.addRow(join_label, join_spin)
    form.addRow(change_btn)
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
    swap_btn.setEnabled(False)
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
    start_btn.setEnabled(False)
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
    return_line.setText('')
    return_btn = QtWidgets.QPushButton('Return to Inkscape')
    return_btn.setObjectName('return-inkscape')
    return_row = QtWidgets.QHBoxLayout()
    return_row.addWidget(return_btn)
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
        'surround_started': False,
        'surround_paths': [],
        'surround_args': [],
        'surround_inflight': None,
        'regions_swap': None,
        'asked': False,
        'calls': [],
        'swaps': [],
        'focus': None,
        'fill_parts': [],
        'arrow_paths': {},
        'plain_figures': [],
        'plain_defects': [],
        'ask': None,
        'ask_seq': 0,
        'ask_token': None,
        'closed_token': None,
        'opening': True,
        'drop': False,
        'proc': None,
        'conn': None,
        'mp_pause': None,
        'mp_cancel': None,
        'inbox': None,
        'solver_keeps': [],
        'last_fit': 0.0,
        'close_when_done': False,
    }
    dialog.worker_calls = state['calls']
    dialog.worker_swaps = state['swaps']
    dialog.surround_args = state['surround_args']
    dialog.solver_keeps = state['solver_keeps']
    dialog.focus_mark = None
    dialog.focus_named = None
    dialog.ask_name = None
    CheckerItem = _checker_type(QtWidgets, QtGui, QtCore)

    def _set_ask(kind):
        state['ask'] = kind
        dialog.ask_name = kind

    def _solver_running():
        return state.get('ask') == 'solver'

    def _form_locked():
        # Distance, join, swap, and mode stay live during a surround
        # ask so a newer one can wait. The solver still locks the form.
        if state.get('opening') or _solver_running():
            return True
        return state['busy'] and state.get('ask') != 'surround'

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
        locked = _form_locked()
        mode_box.setEnabled(not locked)
        pad_spin.setEnabled(not busy)
        space_spin.setEnabled(not busy)
        collar_spin.setEnabled(not busy)
        layer_edit.setEnabled(not busy)
        swap_btn.setEnabled(not locked)
        light_edit.setEnabled(not busy)
        dark_edit.setEnabled(not busy)
        weed_edit.setEnabled(not busy)
        subject_edit.setEnabled(not busy)
        apply_btn.setEnabled((not busy) and state['result'] is not None)
        _arm_surround_controls()

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

    class _Defect(object):
        def __init__(self, kind, target):
            self.kind = kind
            self.target = target

    class _Check(object):
        def __init__(self, defects):
            self.defects = defects
            self.figures = []

    class _Regions(object):
        def __init__(self, subject, weed_area, bounds):
            self.subject = subject
            self.weed_area = weed_area
            self.bounds = bounds

    def _ensure_regions():
        # Applied by the subject ask. A color change does not ask again.
        return state.get('regions')

    def refresh_preview():
        for item in state['preview_items']:
            scene.removeItem(item)
        state['preview_items'] = []
        regions = _ensure_regions()
        if regions is None:
            return
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
        for fill, part in state.get('fill_parts') or []:
            solid = _hex_color(fill)
            if solid is None or part is None or part.isEmpty():
                continue
            _fill(part, solid, 11)
        arrow_paths = {}
        for kind in _ARROW_KINDS:
            batch = list((state.get('arrow_paths') or {}).get(kind) or [])
            if not batch:
                continue
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
        if not blocked and state['surround_started'] and _in_surround():
            surround_pen = _line_pen(QtGui, QtCore, weed_color)
            bare = QtGui.QBrush(QtCore.Qt.NoBrush)
            for path in state['surround_paths']:
                if path is None or path.isEmpty():
                    continue
                item = scene.addPath(path, surround_pen, bare)
                item.setZValue(20)
                state['preview_items'].append(item)
        weed_pen = _line_pen(QtGui, QtCore, weed_color)
        for item in state['weed_items']:
            item.setPen(weed_pen)
            item.setZValue(20)
        _fit()

    def clear_weed_items():
        for item in state['weed_items']:
            scene.removeItem(item)
        state['weed_items'] = []

    def _in_surround():
        return mode_box.currentData() == _SURROUND_MODE

    def _show_surround_controls():
        show = _in_surround()
        distance_label.setVisible(show)
        distance_spin.setVisible(show)
        join_label.setVisible(show)
        join_spin.setVisible(show)
        change_btn.setVisible(show)

    def _arm_surround_controls():
        live = not _form_locked()
        distance_spin.setEnabled(live)
        join_spin.setEnabled(live)
        change_btn.setEnabled(live)

    def _surround_due():
        return (
            state['surround_started'] and not blocked and _in_surround()
            and not state.get('drop') and not state['cancel'].is_set())

    def _surround_stale():
        """True when a newer distance, join, or swap is already waiting."""
        asked = state.get('surround_inflight')
        if not asked:
            return False
        distance, join_gap, swap = asked
        if bool(state['swapped']) != bool(swap):
            return True
        if abs(float(distance_spin.value()) - float(distance)) > 1e-9:
            return True
        if abs(float(join_spin.value()) - float(join_gap)) > 1e-9:
            return True
        return False

    def _ask_surrounds():
        # Callers set surround_started. The child builds. This thread paints.
        if not _surround_due():
            return False
        regions = _ensure_regions()
        if regions is None or regions.subject is None:
            return False
        if state.get('ask'):
            return False
        distance = float(distance_spin.value())
        join_gap = float(join_spin.value())
        if distance < 0.0:
            distance = 0.0
        if join_gap < 0.0:
            join_gap = 0.0
        elements, rule = _pack_path(regions.subject)
        state['surround_inflight'] = (
            distance, join_gap, bool(state['swapped']))
        return _begin_ask({
            'kind': 'surround',
            'elements': elements,
            'rule': rule,
            'distance': distance,
            'join_gap': join_gap,
        })

    def on_start():
        if state['busy'] or blocked or state.get('ask'):
            return
        if _in_surround():
            # Start asks for the surround. It does not run a solver.
            state['cancel'].clear()
            state['pause'].clear()
            state['surround_started'] = True
            state['surround_paths'] = []
            _ask_surrounds()
            refresh_preview()
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
        state['last_fit'] = 0.0
        state['close_when_done'] = False
        elements, rule = _pack_path(keep)
        if not _begin_ask({
            'kind': 'solver',
            'mode': mode,
            'padding': [padding, padding, padding, padding],
            'spacing': spacing,
            'collar': collar,
            'elements': elements,
            'rule': rule,
        }):
            set_controls(False)
            append_log('Error: solver did not start\n')

    def _sync_worker_flags():
        mp_pause = state.get('mp_pause')
        if mp_pause is not None:
            if state['pause'].is_set():
                mp_pause.set()
            else:
                mp_pause.clear()
        if state['cancel'].is_set():
            mp_cancel = state.get('mp_cancel')
            if mp_cancel is not None:
                mp_cancel.set()

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
        _sync_worker_flags()

    def on_cancel():
        if not state['busy'] and not state.get('ask'):
            return
        # Wake a paused worker so it can see cancel. Do not kill it.
        state['pause'].clear()
        state['cancel'].set()
        _sync_worker_flags()
        append_log('Cancel requested — stopping algorithm…\n')
        if state.get('ask') == 'surround':
            # Clear All returns this step to the wait. The child is not killed.
            state['surround_started'] = False
            state['surround_paths'] = []
            refresh_preview()
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
        # Drop a late result. Do not join or kill the child. A solver
        # keeps pumping until the next progress check ends the run.
        state['drop'] = True
        state['pause'].clear()
        state['cancel'].set()
        _sync_worker_flags()
        proc = state.get('proc')
        if (state.get('ask') == 'solver' and proc is not None
                and proc.is_alive()):
            state['close_when_done'] = True
            append_log('Cancel requested — stopping algorithm…\n')
            set_controls(True, paused=False)
            return
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
        if state.get('opening') or _solver_running():
            return
        if state['busy'] and state.get('ask') != 'surround':
            return
        state['swapped'] = not state['swapped']
        if state.get('ask') == 'surround':
            # The swap flag is already toggled. The arrival starts
            # the subject ask. This thread does not wait on the child.
            return
        if not _begin_ask(_subject_request()):
            state['swapped'] = not state['swapped']
            return
        app_loop = QtWidgets.QApplication.instance()
        while state.get('ask') == 'subject' and dialog.isVisible():
            app_loop.processEvents(QtCore.QEventLoop.AllEvents, 50)

    def _on_mode(_index=None):
        if _solver_running() or state.get('ask') not in (None, 'surround'):
            return
        had_surrounds = bool(state['surround_paths'])
        _show_surround_controls()
        _arm_surround_controls()
        if state['surround_started'] and not blocked and _in_surround():
            if state.get('ask'):
                return
            _ask_surrounds()
            return
        state['surround_paths'] = []
        # Cut-mode changes do not rebuild arrows or the checkerboard.
        if had_surrounds:
            refresh_preview()

    def _on_surround_length(value=None):
        if isinstance(value, str):
            return
        if (blocked or state.get('opening') or _solver_running()
                or not state['surround_started'] or not _in_surround()):
            return
        if state.get('ask'):
            # The spin already holds the newer length. Do not paint
            # the in-flight result when it arrives.
            return
        _ask_surrounds()

    def _on_change_surround():
        if _solver_running() or not _in_surround():
            return
        if state.get('ask') not in (None, 'surround'):
            return
        state['surround_started'] = False
        state['surround_paths'] = []
        _arm_surround_controls()
        refresh_preview()

    start_btn.clicked.connect(on_start)
    pause_btn.clicked.connect(on_pause_toggle)
    cancel_btn.clicked.connect(on_cancel)
    apply_btn.clicked.connect(on_apply)
    close_btn.clicked.connect(on_close)
    return_btn.clicked.connect(on_return)
    swap_btn.clicked.connect(_on_swap)
    mode_box.currentIndexChanged.connect(_on_mode)
    distance_spin.valueChanged.connect(_on_surround_length)
    join_spin.valueChanged.connect(_on_surround_length)
    change_btn.clicked.connect(_on_change_surround)
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

    _show_surround_controls()

    def _conn_pending(conn):
        try:
            return conn.poll()
        except (EOFError, OSError):
            return False

    def _take_message(msg):
        kind = msg[0]
        inbox = state.get('inbox')
        if kind == 'log':
            append_log(msg[1])
        elif kind == 'focus':
            mark = (msg[1], msg[2])
            state['focus'] = mark
            dialog.focus_mark = mark
            outline, line = mark
            if outline or line:
                dialog.focus_named = mark
        elif kind == 'segment':
            state['seg_q'].append(msg[1])
        elif kind == 'keep':
            path = _unpack_path(msg[2], msg[3])
            state['solver_keeps'].append((msg[1], path))
        elif kind == 'result':
            inbox['result'] = (msg[1], msg[2])
        elif kind == 'call':
            state['calls'].append(msg[1])
            if msg[1] == 'subject' and len(msg) > 2:
                state['swaps'].append(bool(msg[2]))
            elif msg[1] == 'surrounds' and len(msg) >= 4:
                state['surround_args'].append((float(msg[2]), float(msg[3])))
        elif kind == 'figure':
            inbox['figures'].append(msg[1:])
        elif kind == 'defect':
            inbox['defects'].append(msg[1:])
        elif kind == 'path':
            inbox[msg[1]] = (msg[2], msg[3])
        elif kind == 'bounds':
            inbox['bounds'] = msg[1:]
        elif kind == 'fill':
            inbox['fills'].append((msg[1], msg[2], msg[3]))
        elif kind == 'arrow':
            inbox['arrows'].append(msg[1:])
        elif kind == 'surround':
            inbox['surrounds'].append((msg[1], msg[2]))
        elif kind == 'cancelled':
            inbox['cancelled'] = True
        elif kind == 'error':
            inbox['error'] = msg[1]
        elif kind == 'done':
            state['ask_done'] = True

    def _reap_proc(proc):
        if proc is None:
            return
        if not proc.is_alive():
            proc.join(0)
            close = getattr(proc, 'close', None)
            if close is not None:
                close()
            return

        def once():
            if proc.is_alive():
                QtCore.QTimer.singleShot(50, once)
                return
            proc.join(0)
            close = getattr(proc, 'close', None)
            if close is not None:
                close()

        QtCore.QTimer.singleShot(0, once)

    def _subject_request():
        return {
            'kind': 'subject',
            'swap': bool(state['swapped']),
            'figures': state['plain_figures'],
            'defects': state['plain_defects'],
        }

    def _begin_ask(request):
        if state.get('ask'):
            return False
        request = dict(request)
        if _ASK_TRACE:
            request['trace'] = _ASK_TRACE
        token = state['ask_seq'] + 1
        state['ask_seq'] = token
        state['ask_token'] = token
        state['pump_token'] = token
        _set_ask(request['kind'])
        state['ask_done'] = False
        state['inbox'] = _empty_inbox()
        ctx = multiprocessing.get_context('spawn')
        pausing = ctx.Event()
        cancelled = ctx.Event()
        if state['pause'].is_set():
            pausing.set()
        if state['cancel'].is_set():
            cancelled.set()
        try:
            proc, conn = _spawn_ask(request, _ASK_HOLD, pausing, cancelled)
        except Exception:
            _set_ask(None)
            state['ask_token'] = None
            raise
        state['proc'] = proc
        state['conn'] = conn
        state['mp_pause'] = pausing
        state['mp_cancel'] = cancelled
        set_controls(True, paused=state['pause'].is_set())
        QtCore.QTimer.singleShot(0, _pump_ask)
        return True

    def _store_classify(inbox):
        nonlocal check, blocked
        plain_figures = []
        for fig_id, fill, elements, rule in inbox['figures']:
            plain_figures.append({
                'id': fig_id,
                'fill': fill,
                'elements': elements,
                'rule': rule,
            })
        defects = []
        plain_defects = []
        for kind_name, x, y in inbox['defects']:
            defects.append(_Defect(kind_name, QtCore.QPointF(x, y)))
            plain_defects.append({'kind': kind_name, 'x': x, 'y': y})
        check = _Check(defects)
        state['plain_figures'] = plain_figures
        state['plain_defects'] = plain_defects
        blocked = bool(defects)
        return_line.setText(_defect_line(defects))
        if blocked and not state.get('arrows_button'):
            arrows_btn = QtWidgets.QPushButton(
                'Return to Inkscape with correction arrows')
            arrows_btn.setObjectName('return-arrows')
            return_row.insertWidget(1, arrows_btn)
            arrows_btn.clicked.connect(on_return_arrows)
            # setParent from the layout hides a widget added after show.
            arrows_btn.show()
            state['arrows_button'] = arrows_btn

    def _store_subject(inbox):
        packed = inbox.get('subject') or ([], 0)
        subject = _unpack_path(packed[0], packed[1])
        packed = inbox.get('weed') or ([], 0)
        weed = _unpack_path(packed[0], packed[1])
        x, y, width, height = inbox['bounds']
        bounds = QtCore.QRectF(x, y, width, height)
        state['regions'] = _Regions(subject, weed, bounds)
        state['regions_swap'] = state['swapped']
        state['fill_parts'] = [
            (fill, _unpack_path(elements, rule))
            for fill, elements, rule in inbox['fills']
        ]
        arrow_paths = {}
        for kind, color, shaft, shaft_rule, head, head_rule in inbox['arrows']:
            arrow = ArrowPath(
                _unpack_path(shaft, shaft_rule),
                _unpack_path(head, head_rule),
                color)
            arrow_paths.setdefault(kind, []).append(arrow)
        state['arrow_paths'] = arrow_paths
        if state.get('opening'):
            # Setting the spin is not a surround ask.
            initial_distance = _surround_distance(bounds)
            distance_spin.blockSignals(True)
            distance_spin.setRange(0.0, max(1000000.0, initial_distance))
            distance_spin.setValue(initial_distance)
            distance_spin.blockSignals(False)

    def _fail_ask(exc):
        _set_ask(None)
        state['opening'] = False
        state['ready_error'] = exc
        dialog.reject()

    def _follow_surround():
        """Start the newer ask, if one was waiting. Do not paint the old one."""
        if state.get('ask') or state.get('drop'):
            return
        if state['swapped'] != state.get('regions_swap'):
            _begin_ask(_subject_request())
            return
        if _surround_due() and _surround_stale():
            _ask_surrounds()
            return
        state['surround_inflight'] = None

    def _after_classify(inbox):
        if state.get('drop'):
            state['opening'] = False
            return
        if inbox.get('error'):
            raise RuntimeError(inbox['error'])
        if inbox.get('cancelled'):
            append_log('Cancelled.\n')
            state['opening'] = False
            set_controls(False)
            return
        _store_classify(inbox)
        if not _begin_ask(_subject_request()):
            raise RuntimeError('subject ask did not start')

    def _after_subject(inbox):
        if state.get('drop'):
            _set_ask(None)
            state['opening'] = False
            return
        if inbox.get('error'):
            if not state.get('opening'):
                state['swapped'] = not state['swapped']
                append_log('Error: %s\n' % inbox['error'])
                _set_ask(None)
                set_controls(False)
                return
            raise RuntimeError(inbox['error'])
        if inbox.get('cancelled'):
            append_log('Cancelled.\n')
            if not state.get('opening'):
                state['swapped'] = not state['swapped']
            _set_ask(None)
            state['opening'] = False
            set_controls(False)
            return
        _store_subject(inbox)
        due = _surround_due()
        if due:
            state['surround_paths'] = []
        was_opening = bool(state.get('opening'))
        if was_opening:
            # Unlock the form after the first paint. _form_locked
            # still sees opening until this flag drops.
            state['opening'] = False
        refresh_preview()
        set_controls(False)
        _set_ask(None)
        if was_opening:
            root.invalidate()
            root.activate()
            _fit()
            if ready is not None:
                ready(dialog)
            return
        if due:
            _ask_surrounds()

    def _after_surround(inbox):
        if state.get('drop'):
            _set_ask(None)
            return
        abort = bool(inbox.get('cancelled')) or state['cancel'].is_set()
        if abort:
            append_log('Cancelled.\n')
            state['surround_paths'] = []
            state['surround_started'] = False
            state['surround_inflight'] = None
            state['cancel'].clear()
            state['pause'].clear()
            refresh_preview()
            _set_ask(None)
            set_controls(False)
            _follow_surround()
            return
        if inbox.get('error'):
            append_log('Error: %s\n' % inbox['error'])
            _set_ask(None)
            set_controls(False)
            _follow_surround()
            return
        # A newer distance, join, or swap is waiting. Do not paint this one.
        if not _surround_due() or _surround_stale():
            _set_ask(None)
            set_controls(False)
            _follow_surround()
            return
        paths = []
        for elements, rule in inbox.get('surrounds') or []:
            paths.append(_unpack_path(elements, rule))
        state['surround_paths'] = paths
        refresh_preview()
        _set_ask(None)
        set_controls(False)
        _follow_surround()

    def _paint_solver_segments():
        """Line items for accepted segments. This thread owns the scene."""
        if state.get('ask') != 'solver' or not state['seg_q']:
            return
        if state['work'] is None and state['solved_keep'] is not None:
            state['work'] = padded_work_rect(
                state['solved_keep'], state['solved_pad'])
            refresh_preview()
        weed_pen = _line_pen(QtGui, QtCore, weed_edit.property('color'))
        added = False
        for _ in range(200):
            if not state['seg_q']:
                break
            seg = state['seg_q'].popleft()
            try:
                x0, y0, x1, y1 = seg
            except (TypeError, ValueError):
                continue
            item = scene.addLine(x0, y0, x1, y1, weed_pen)
            item.setZValue(20)
            state['weed_items'].append(item)
            added = True
        if added and (time.time() - state.get('last_fit', 0.0)) > 0.4:
            rect = scene.itemsBoundingRect()
            if not rect.isNull():
                view.fitInView(rect, QtCore.Qt.KeepAspectRatio)
            state['last_fit'] = time.time()

    def _after_solver(inbox):
        if state.get('close_when_done'):
            state['result'] = None
            state['accepted'] = False
            _set_ask(None)
            set_controls(False)
            dialog.reject()
            return
        if inbox.get('cancelled'):
            append_log('Algorithm cancelled.\n')
            state['result'] = None
            _set_ask(None)
            set_controls(False)
            return
        if inbox.get('error'):
            append_log('Algorithm failed: %s\n' % inbox['error'])
            state['result'] = None
            _set_ask(None)
            set_controls(False)
            return
        packed = inbox.get('result')
        if packed:
            state['result'] = _unpack_path(packed[0], packed[1])
        else:
            state['result'] = QPainterPath()
        _set_ask(None)
        set_controls(False)
        if state['result'] is None or state['result'].isEmpty():
            append_log('No weed cuts produced.\n')
            apply_btn.setEnabled(False)
            return
        append_log('Done. Review cuts, then Apply.\n')
        rect = scene.itemsBoundingRect()
        if not rect.isNull():
            view.fitInView(rect, QtCore.Qt.KeepAspectRatio)
        apply_btn.setEnabled(True)

    def _finish_ask(token):
        if state.get('ask_token') != token:
            return
        if state.get('closed_token') == token:
            return
        state['closed_token'] = token
        kind = state.get('ask')
        inbox = state.get('inbox') or _empty_inbox()
        proc = state.get('proc')
        conn = state.get('conn')
        state['ask_token'] = None
        state['proc'] = None
        state['conn'] = None
        state['mp_pause'] = None
        state['mp_cancel'] = None
        _reap_proc(proc)
        if conn is not None:
            try:
                conn.close()
            except OSError:
                pass
        if not state.get('ask_done') and not inbox.get('error'):
            if not inbox.get('cancelled'):
                if kind == 'solver':
                    inbox['error'] = 'solver stopped'
                else:
                    inbox['error'] = 'figure check stopped'
        try:
            if kind == 'classify':
                _set_ask(None)
                _after_classify(inbox)
            elif kind == 'subject':
                _after_subject(inbox)
            elif kind == 'surround':
                _after_surround(inbox)
            elif kind == 'solver':
                _after_solver(inbox)
        except Exception as exc:
            _fail_ask(exc)

    def _pump_ask():
        token = state.get('pump_token')
        if token is None or state.get('ask_token') != token:
            return
        drain_platform_lines()
        conn = state.get('conn')
        if conn is not None:
            while _conn_pending(conn):
                try:
                    msg = conn.recv()
                except EOFError:
                    inbox = state.get('inbox')
                    if inbox is not None and not inbox.get('error'):
                        if state.get('ask') == 'solver':
                            inbox['error'] = 'solver stopped'
                        else:
                            inbox['error'] = 'figure check stopped'
                    state['ask_done'] = True
                    break
                _take_message(msg)
                if msg[0] == 'done':
                    break
        if state.get('ask_token') != token:
            return
        if state.get('ask') == 'solver':
            _paint_solver_segments()
        if state.get('ask') == 'solver' and state['seg_q']:
            QtCore.QTimer.singleShot(15, _pump_ask)
            return
        proc = state.get('proc')
        alive = proc is not None and proc.is_alive()
        if state.get('ask_done') or not alive:
            _finish_ask(token)
            return
        QtCore.QTimer.singleShot(15, _pump_ask)

    def _shown():
        # exec_ has shown the dialog. The ask returns here; ready is later.
        if state['asked']:
            return
        state['asked'] = True
        state['opening'] = True
        try:
            _begin_ask({
                'kind': 'classify',
                'records': list(records or []),
            })
        except Exception as exc:
            state['ready_error'] = exc
            dialog.reject()

    def _mark_closed():
        state['drop'] = True

    dialog.rejected.connect(_mark_closed)

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
