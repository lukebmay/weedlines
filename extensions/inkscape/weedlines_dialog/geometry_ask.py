# -*- coding: utf-8 -*-
"""Spawn one ask and install progress, cancel, pause, focus, and the solver log in the child."""
from __future__ import division

import logging
import multiprocessing
import os
import sys

from .return_line import _ARROW_KINDS

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


def _send_call(conn, name, swap=None):
    if swap is None:
        conn.send(('call', name))
    else:
        conn.send(('call', name, bool(swap)))


def _optional_length(request, key):
    if request.get(key) is None:
        return None
    try:
        return float(request.get(key))
    except (TypeError, ValueError):
        return None


def _radius_moved(asked, current):
    if asked is None or current is None:
        return asked is not current
    return abs(float(asked) - float(current)) > 1e-9


def _with_corner_radius(request, radius):
    # Only a stored radius goes on the call. Omitted stays square.
    if radius is not None:
        request['corner_radius'] = radius
    return request


def _radius_kwargs(radius):
    if radius is None:
        return {}
    return {'corner_radius': radius}


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
    inner_distance = _optional_length(request, 'inner_distance')
    border_width = _optional_length(request, 'border_width')
    corner_radius = _optional_length(request, 'corner_radius')
    keep = _unpack_path(
        request.get('elements') or [], request.get('rule') or 'odd')
    elements, rule = _pack_path(keep)
    conn.send(('keep', str(mode), elements, rule))
    call = (
        'call', 'solver',
        [float(value) for value in padding],
        float(spacing),
        float(collar),
    )
    if inner_distance is not None and border_width is not None:
        call = call + (inner_distance, border_width)
    conn.send(call)

    def on_phase(name):
        conn.send(('phase', str(name)))
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
            inner_distance=inner_distance,
            border_width=border_width,
            **_radius_kwargs(corner_radius),
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
    from weedlib.ready import build_correction_marks
    _send_call(conn, 'classify')
    records = request.get('records') or []
    marks = build_correction_marks(records)
    check = marks.check
    for figure in check.figures:
        elements, rule = _pack_path(figure.path)
        conn.send(('figure', figure.id, figure.fill, elements, rule))
    for defect in check.defects:
        x, y = _point_xy(defect.target)
        conn.send(('defect', defect.kind, x, y))
    for label in marks.labels:
        x, y = _point_xy(label.point)
        conn.send(('mark', label.text, label.color, x, y))


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
    inner_distance = _optional_length(request, 'inner_distance')
    corner_radius = _optional_length(request, 'corner_radius')
    if inner_distance is None:
        conn.send(('call', 'surrounds', distance, join_gap))
    else:
        conn.send(('call', 'surrounds', distance, join_gap, inner_distance))
    subject = _unpack_path(
        request.get('elements') or [], request.get('rule') or 'odd')
    if inner_distance is None:
        surrounds = build_surrounds(
            subject, distance, join_gap, **_radius_kwargs(corner_radius))
    else:
        surrounds = build_surrounds(
            subject, distance, join_gap, inner_distance=inner_distance,
            **_radius_kwargs(corner_radius))
    for path in surrounds:
        elements, rule = _pack_path(path)
        conn.send(('surround', elements, rule))


def _ask_piece_border(request, conn):
    """One border ask. The library builds the rectangles. No window."""
    from weedlib.piece_border import piece_border
    inner_distance = _optional_length(request, 'inner_distance')
    border_width = _optional_length(request, 'border_width')
    corner_radius = _optional_length(request, 'corner_radius')
    if inner_distance is None:
        inner_distance = 0.0
    if border_width is None:
        border_width = 0.0
    conn.send(('call', 'piece_border', inner_distance, border_width))
    subject = _unpack_path(
        request.get('elements') or [], request.get('rule') or 'odd')
    for path in piece_border(
            subject, inner_distance, border_width,
            **_radius_kwargs(corner_radius)):
        elements, rule = _pack_path(path)
        conn.send(('border', elements, rule))


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
        elif kind == 'border':
            _ask_piece_border(request, conn)
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


class _Ask(object):

    def _set_ask(self, kind):
        self.state['ask'] = kind
        self.dialog.ask_name = kind

    def _surround_due(self):
        return (
            self.state['surround_started'] and not self.blocked and self._in_surround()
            and not self.state.get('drop') and not self.state['cancel'].is_set())

    def _surround_stale(self):
        """True when a newer distance, join, inner distance, radius, or swap is waiting."""
        asked = self.state.get('surround_inflight')
        if not asked:
            return False
        distance, join_gap, swap, inner = asked[:4]
        asked_radius = asked[4] if len(asked) > 4 else None
        if bool(self.state['swapped']) != bool(swap):
            return True
        if abs(self.state['lengths']['distance'] - float(distance)) > 1e-9:
            return True
        if abs(self.state['lengths']['join'] - float(join_gap)) > 1e-9:
            return True
        if abs(self.state['lengths']['inner'] - float(inner)) > 1e-9:
            return True
        radius = _optional_length(self.state['lengths'], 'corner_radius')
        if _radius_moved(asked_radius, radius):
            return True
        return False

    def _ask_surrounds(self):
        # Callers set surround_started. The child builds. This thread paints.
        if not self._surround_due():
            return False
        regions = self._ensure_regions()
        if regions is None or regions.subject is None:
            return False
        if self.state.get('ask'):
            return False
        distance = self.state['lengths']['distance']
        join_gap = self.state['lengths']['join']
        inner = float(self.state['lengths']['inner'])
        if distance < 0.0:
            distance = 0.0
        if join_gap < 0.0:
            join_gap = 0.0
        elements, rule = _pack_path(regions.subject)
        radius = _optional_length(self.state['lengths'], 'corner_radius')
        self.state['surround_inflight'] = (
            distance, join_gap, bool(self.state['swapped']), inner, radius)
        return self._begin_ask(_with_corner_radius({
            'kind': 'surround',
            'elements': elements,
            'rule': rule,
            'distance': distance,
            'join_gap': join_gap,
            'inner_distance': inner,
        }, radius))

    def _begin_ask(self, request):
        # Looked up on the package each call. A test replaces it.
        import weedlines_dialog as _dialog
        from .inbox import _empty_inbox
        if self.state.get('ask'):
            return False
        request = dict(request)
        if _dialog._ASK_TRACE:
            request['trace'] = _dialog._ASK_TRACE
        token = self.state['ask_seq'] + 1
        self.state['ask_seq'] = token
        self.state['ask_token'] = token
        self.state['pump_token'] = token
        self._set_ask(request['kind'])
        self.state['ask_done'] = False
        self.state['inbox'] = _empty_inbox()
        ctx = multiprocessing.get_context('spawn')
        pausing = ctx.Event()
        cancelled = ctx.Event()
        if self.state['pause'].is_set():
            pausing.set()
        if self.state['cancel'].is_set():
            cancelled.set()
        try:
            proc, conn = _dialog._spawn_ask(request, _dialog._ASK_HOLD, pausing, cancelled)
        except Exception:
            self._set_ask(None)
            self.state['ask_token'] = None
            raise
        self.state['proc'] = proc
        self.state['conn'] = conn
        self.state['mp_pause'] = pausing
        self.state['mp_cancel'] = cancelled
        self.set_controls(True, paused=self.state['pause'].is_set())
        self.QtCore.QTimer.singleShot(0, self._pump_ask)
        return True

    def _subject_request(self):
        return {
            'kind': 'subject',
            'swap': bool(self.state['swapped']),
            'figures': self.state['plain_figures'],
            'defects': self.state['plain_defects'],
        }

    def _border_due(self):
        return not self.blocked and not self.state.get('drop')

    def _border_stale(self):
        """True when this border was not asked for the current subject or radius."""
        asked = self.state.get('border_inflight')
        if not asked:
            return True
        inner, width, swap = asked[:3]
        asked_radius = asked[3] if len(asked) > 3 else None
        if bool(self.state['swapped']) != bool(swap):
            return True
        if abs(self.state['lengths']['inner'] - float(inner)) > 1e-9:
            return True
        if abs(self.state['lengths']['border'] - float(width)) > 1e-9:
            return True
        radius = _optional_length(self.state['lengths'], 'corner_radius')
        if _radius_moved(asked_radius, radius):
            return True
        return False

    def _ask_border(self):
        # The child calls piece_border. This thread only paints the reply.
        if not self._border_due():
            return False
        if self.state['swapped'] != self.state.get('regions_swap'):
            return False
        regions = self._ensure_regions()
        if regions is None or regions.subject is None or regions.subject.isEmpty():
            return False
        if self.state.get('ask') or not self._border_stale():
            return False
        inner = float(self.state['lengths']['inner'])
        width = float(self.state['lengths']['border'])
        elements, rule = _pack_path(regions.subject)
        radius = _optional_length(self.state['lengths'], 'corner_radius')
        self.state['border_inflight'] = (
            inner, width, bool(self.state['swapped']), radius)
        started = self._begin_ask(_with_corner_radius({
            'kind': 'border',
            'elements': elements,
            'rule': rule,
            'inner_distance': inner,
            'border_width': width,
        }, radius))
        if not started:
            self.state['border_inflight'] = None
        return started

    def _follow_surround(self):
        """Start the newer ask, if one was waiting. Do not paint the old one."""
        if self.state.get('ask') or self.state.get('drop'):
            return
        if self.state['swapped'] != self.state.get('regions_swap'):
            self._begin_ask(self._subject_request())
            return
        if self._border_due() and self._border_stale():
            if self._ask_border():
                return
        waiting = (
            not self.state.get('surround_finished')
            and self.state.get('surround_inflight') is None)
        if self._surround_due() and (self._surround_stale() or waiting):
            self._ask_surrounds()
            return
        pending = self.state.get('solver_request')
        if pending:
            self.state['solver_request'] = None
            if self.mode_box.currentData() != pending:
                if pending in self.state['cut_started']:
                    self.state['cut_started'][pending] = False
                return
            request = self._solver_request(pending)
            if request is None:
                if pending in self.state['cut_started']:
                    self.state['cut_started'][pending] = False
                return
            if not self._begin_ask(request):
                self.state['solver_request'] = pending

    def _after_classify(self, inbox):
        if self.state.get('drop'):
            self.state['opening'] = False
            return
        if inbox.get('error'):
            raise RuntimeError(inbox['error'])
        if inbox.get('cancelled'):
            self.append_log('Cancelled.\n')
            self._end_abort()
            self.state['opening'] = False
            self.set_controls(False)
            return
        self._store_classify(inbox)
        if not self._begin_ask(self._subject_request()):
            raise RuntimeError('subject ask did not start')

    def _after_subject(self, inbox):
        if self.state.get('drop'):
            self._set_ask(None)
            self.state['opening'] = False
            return
        if inbox.get('error'):
            if not self.state.get('opening'):
                self.state['swapped'] = not self.state['swapped']
                self.append_log('Error: %s\n' % inbox['error'])
                self._set_ask(None)
                self.set_controls(False)
                return
            raise RuntimeError(inbox['error'])
        if inbox.get('cancelled'):
            self.append_log('Cancelled.\n')
            if not self.state.get('opening'):
                self.state['swapped'] = not self.state['swapped']
            self._end_abort()
            self._set_ask(None)
            self.state['opening'] = False
            self.set_controls(False)
            return
        self._store_subject(inbox)
        due = self._surround_due()
        if due:
            self.state['surround_paths'] = []
        was_opening = bool(self.state.get('opening'))
        if was_opening:
            # Unlock the form after the first paint. _form_locked
            # still sees opening until this flag drops.
            self.state['opening'] = False
        self.refresh_preview()
        self.set_controls(False)
        self._set_ask(None)
        if was_opening:
            # Ready stays on this turn, after the subject paint. The
            # border ask is the next turn, still without Start.
            if not self.blocked and not self.state.get('drop'):
                self.QtCore.QTimer.singleShot(0, self._ask_border)
            self.root.invalidate()
            self.root.activate()
            self._fit()
            if self.ready is not None:
                self.ready(self.dialog)
            return
        if not self._ask_border() and due:
            self._ask_surrounds()

    def _after_surround(self, inbox):
        if self.state.get('drop'):
            self._set_ask(None)
            return
        abort = bool(inbox.get('cancelled')) or self.state['cancel'].is_set()
        if abort:
            self.append_log('Cancelled.\n')
            self.state['surround_paths'] = []
            self.state['surround_started'] = False
            self.state['surround_finished'] = False
            self.state['surround_inflight'] = None
            self.refresh_preview()
            self._end_abort()
            self._set_ask(None)
            self.set_controls(False)
            self._follow_surround()
            return
        if inbox.get('error'):
            self.append_log('Error: %s\n' % inbox['error'])
            self._set_ask(None)
            self.set_controls(False)
            self._follow_surround()
            return
        # A newer distance, join, or swap is waiting. Do not paint this one.
        if not self._surround_due() or self._surround_stale():
            self._set_ask(None)
            self.set_controls(False)
            self._follow_surround()
            return
        paths = []
        for elements, rule in inbox.get('surrounds') or []:
            paths.append(_unpack_path(elements, rule))
        self.state['surround_paths'] = paths
        self.state['surround_finished'] = True
        self.refresh_preview()
        self._set_ask(None)
        self.set_controls(False)
        self._follow_surround()

    def _after_border(self, inbox):
        if self.state.get('drop'):
            self._set_ask(None)
            return
        if inbox.get('cancelled'):
            self._set_ask(None)
            self.set_controls(False)
            self._follow_surround()
            return
        if inbox.get('error'):
            self.append_log('Error: %s\n' % inbox['error'])
            self._set_ask(None)
            self.set_controls(False)
            self._follow_surround()
            return
        # A newer length or subject is waiting. Do not paint this one.
        if not self._border_due() or self._border_stale():
            self._set_ask(None)
            self.set_controls(False)
            self._follow_surround()
            return
        paths = []
        for elements, rule in inbox.get('borders') or []:
            paths.append(_unpack_path(elements, rule))
        self.state['border_paths'] = paths
        self.refresh_preview()
        self._set_ask(None)
        self.set_controls(False)
        self._follow_surround()

    def _after_solver(self, inbox):
        if self.state.get('close_when_done'):
            self.state['result'] = None
            self.state['accepted'] = False
            self._end_abort()
            self._set_ask(None)
            self.set_controls(False)
            self.dialog.reject()
            return
        if (inbox.get('cancelled') or self.state['cancel'].is_set()
                or self.state.get('aborting')):
            self.append_log('Algorithm cancelled.\n')
            self.state['result'] = None
            self.state['accepted'] = False
            mode = self.state.get('run_mode')
            if mode in self.state['cut_started']:
                self.state['cut_started'][mode] = False
                self.state['cut_finished'][mode] = False
            self.clear_weed_items()
            self.state['work'] = None
            self.state['seg_q'].clear()
            self._end_abort()
            self._set_ask(None)
            self.set_controls(False)
            self.refresh_preview()
            self._follow_surround()
            return
        if inbox.get('error'):
            self.append_log('Algorithm failed: %s\n' % inbox['error'])
            self.state['result'] = None
            self._set_ask(None)
            self.set_controls(False)
            self._follow_surround()
            return
        packed = inbox.get('result')
        if packed:
            self.state['result'] = _unpack_path(packed[0], packed[1])
        else:
            self.state['result'] = self.QPainterPath()
        mode = self.state.get('run_mode')
        if mode in self.state['cut_finished']:
            self.state['cut_finished'][mode] = True
        self._set_ask(None)
        self.set_controls(False)
        if self.state['result'] is None or self.state['result'].isEmpty():
            self.append_log('No weed cuts produced.\n')
            self.apply_btn.setEnabled(False)
            self._follow_surround()
            return
        self.append_log('Done. Review cuts, then Apply.\n')
        rect = self.scene.itemsBoundingRect()
        if not rect.isNull():
            self.view.fitInView(rect, self.QtCore.Qt.KeepAspectRatio)
        self.apply_btn.setEnabled(True)
        self._follow_surround()

    def _fail_ask(self, exc):
        self._set_ask(None)
        self.state['opening'] = False
        self.state['ready_error'] = exc
        self.dialog.reject()
