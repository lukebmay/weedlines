# -*- coding: utf-8 -*-
"""Pump the pipe on the GUI thread."""
from __future__ import division

from .geometry_ask import _unpack_path

def _empty_inbox():
    return {
        'figures': [],
        'defects': [],
        'subject': None,
        'weed': None,
        'bounds': None,
        'fills': [],
        'arrows': [],
        'marks': [],
        'surrounds': [],
        'borders': [],
        'result': None,
        'error': None,
        'cancelled': False,
    }


class _Inbox(object):

    def append_log(self, text):
        self.log_view.moveCursor(self.QtGui.QTextCursor.End)
        self.log_view.insertPlainText(text)
        self.log_view.moveCursor(self.QtGui.QTextCursor.End)

    def drain_platform_lines(self):
        """Pull Qt/OS stderr captures into the dialog log (not Inkscape)."""
        if self.platform_lines is None:
            return
        while self.platform_lines:
            try:
                line = self.platform_lines.popleft()
            except IndexError:
                break
            self.append_log('[platform] %s\n' % line)

    def _conn_pending(self, conn):
        try:
            return conn.poll()
        except (EOFError, OSError):
            return False

    def _take_message(self, msg):
        kind = msg[0]
        inbox = self.state.get('inbox')
        if kind == 'log':
            self.append_log(msg[1])
        elif kind == 'focus':
            mark = (msg[1], msg[2])
            self.state['focus'] = mark
            self.dialog.focus_mark = mark
            outline, line = mark
            if outline or line:
                self.dialog.focus_named = mark
        elif kind == 'phase':
            self.state['phase'] = msg[1]
            self.dialog.last_phase = msg[1]
            if self.state['busy'] and not self.state.get('aborting'):
                self._render_status()
        elif kind == 'segment':
            if self.state.get('aborting') or self.state['cancel'].is_set():
                return
            self.state['seg_q'].append(msg[1])
        elif kind == 'keep':
            path = _unpack_path(msg[2], msg[3])
            self.state['solver_keeps'].append((msg[1], path))
        elif kind == 'result':
            inbox['result'] = (msg[1], msg[2])
        elif kind == 'call':
            self.state['calls'].append(msg[1])
            if msg[1] == 'subject' and len(msg) > 2:
                self.state['swaps'].append(bool(msg[2]))
            elif msg[1] == 'surrounds' and len(msg) >= 4:
                self.state['surround_args'].append((float(msg[2]), float(msg[3])))
                if len(msg) >= 5:
                    self.state['surround_inner'].append(float(msg[4]))
            elif msg[1] == 'piece_border' and len(msg) >= 4:
                self.state['border_args'].append((float(msg[2]), float(msg[3])))
            elif msg[1] == 'solver' and len(msg) >= 5:
                self.state['solver_args'].append((
                    [float(value) for value in msg[2]],
                    float(msg[3]),
                    float(msg[4]),
                ))
                if len(msg) >= 7:
                    self.state['solver_border'].append((float(msg[5]), float(msg[6])))
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
        elif kind == 'mark':
            inbox['marks'].append(msg[1:])
        elif kind == 'surround':
            inbox['surrounds'].append((msg[1], msg[2]))
        elif kind == 'border':
            inbox['borders'].append((msg[1], msg[2]))
        elif kind == 'cancelled':
            inbox['cancelled'] = True
        elif kind == 'error':
            inbox['error'] = msg[1]
        elif kind == 'done':
            self.state['ask_done'] = True

    def _reap_proc(self, proc):
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
                self.QtCore.QTimer.singleShot(50, once)
                return
            proc.join(0)
            close = getattr(proc, 'close', None)
            if close is not None:
                close()

        self.QtCore.QTimer.singleShot(0, once)

    def _finish_ask(self, token):
        if self.state.get('ask_token') != token:
            return
        if self.state.get('closed_token') == token:
            return
        self.state['closed_token'] = token
        kind = self.state.get('ask')
        inbox = self.state.get('inbox') or _empty_inbox()
        proc = self.state.get('proc')
        conn = self.state.get('conn')
        self.state['ask_token'] = None
        self.state['proc'] = None
        self.state['conn'] = None
        self.state['mp_pause'] = None
        self.state['mp_cancel'] = None
        self._reap_proc(proc)
        if conn is not None:
            try:
                conn.close()
            except OSError:
                pass
        if not self.state.get('ask_done') and not inbox.get('error'):
            if not inbox.get('cancelled'):
                if kind == 'solver':
                    inbox['error'] = 'solver stopped'
                else:
                    inbox['error'] = 'figure check stopped'
        try:
            if kind == 'classify':
                self._set_ask(None)
                self._after_classify(inbox)
            elif kind == 'subject':
                self._after_subject(inbox)
            elif kind == 'surround':
                self._after_surround(inbox)
            elif kind == 'border':
                self._after_border(inbox)
            elif kind == 'solver':
                self._after_solver(inbox)
        except Exception as exc:
            self._fail_ask(exc)

    def _pump_ask(self):
        token = self.state.get('pump_token')
        if token is None or self.state.get('ask_token') != token:
            return
        self.drain_platform_lines()
        conn = self.state.get('conn')
        if conn is not None:
            while self._conn_pending(conn):
                try:
                    msg = conn.recv()
                except EOFError:
                    inbox = self.state.get('inbox')
                    if inbox is not None and not inbox.get('error'):
                        if self.state.get('ask') == 'solver':
                            inbox['error'] = 'solver stopped'
                        else:
                            inbox['error'] = 'figure check stopped'
                    self.state['ask_done'] = True
                    break
                self._take_message(msg)
                if msg[0] == 'done':
                    break
        if self.state.get('ask_token') != token:
            return
        if self.state.get('ask') == 'solver':
            self._paint_solver_segments()
        if self.state.get('ask') == 'solver' and self.state['seg_q']:
            self.QtCore.QTimer.singleShot(15, self._pump_ask)
            return
        proc = self.state.get('proc')
        alive = proc is not None and proc.is_alive()
        if self.state.get('ask_done') or not alive:
            self._finish_ask(token)
            return
        self.QtCore.QTimer.singleShot(15, self._pump_ask)
