# -*- coding: utf-8 -*-
"""Start, Restart, Pause, Clear All, Apply, Close, the step row, and the status."""
from __future__ import division

import time

from .form import _SURROUND_MODE
from .geometry_ask import _optional_length, _pack_path, _with_corner_radius

# A tenth of a second. The label shows that much, and the tick is the same.
_STEP_TICK_MS = 100
# Restart of surround discards conquer. The cut modes are not later steps.
_LATER_STEPS = {
    'surround': ('conquer',),
}

_STEP_TITLES = {
    'frame': 'Frame',
    'grid': 'Grid',
    'island-hop': 'Island hop',
}


class _RunControls(object):

    def _step_line(self, name, title, mark):
        widget = self.QtWidgets.QWidget()
        widget.setObjectName(name)
        layout = self.QtWidgets.QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        label = self.QtWidgets.QLabel(title)
        label.setObjectName(name + '-label')
        stamp = self.QtWidgets.QLabel(mark)
        stamp.setObjectName(name + '-mark')
        clock = self.QtWidgets.QLabel('')
        clock.setObjectName(name + '-time')
        layout.addWidget(label)
        layout.addWidget(stamp)
        layout.addStretch(1)
        layout.addWidget(clock)
        if getattr(self, '_step_clocks', None) is None:
            self._step_clocks = {}
        self._step_clocks[name] = clock
        return widget, layout, label

    def _solver_running(self):
        return self.state.get('ask') == 'solver'

    def _form_locked(self):
        # Distance, join, swap, and mode stay live during a surround
        # ask so a newer one can wait. The solver still locks the form.
        if self.state.get('opening') or self._solver_running():
            return True
        if self.state.get('ask') in ('surround', 'border'):
            return False
        return self.state['busy']

    def _current_started(self):
        if self._in_surround():
            return bool(self.state['surround_started'])
        return bool(self.state['cut_started'].get(self.mode_box.currentData()))

    def _current_finished(self):
        if self._in_surround():
            return bool(self.state['surround_finished'])
        return bool(self.state['cut_finished'].get(self.mode_box.currentData()))

    def _render_status(self):
        # A phase from the library stays in this one status. It is not a step.
        if self.state.get('aborting'):
            self.status_label.setText('ready')
            self.spinner.setVisible(False)
            return
        if not self.state['busy']:
            if self._current_finished():
                self.status_label.setText('done')
            else:
                self.status_label.setText('ready')
            self.spinner.setVisible(False)
            return
        text = 'paused' if self.state['paused'] else 'working'
        phase = self.state.get('phase')
        if phase:
            text = '%s: %s' % (text, phase)
        self.status_label.setText(text)
        self.spinner.setVisible(not self.state['paused'])

    def _sync_start_tip(self):
        # A border ask is not a run. Stopping a step is not a defect.
        running = self.state.get('aborting') or (
            self.state.get('busy') and self.state.get('ask') != 'border')
        tip = ''
        if self.blocked and not running:
            tip = self._marked_problem_text()
        # A disabled button does not show a tooltip unless this is set.
        self.start_btn.setAttribute(
            self.QtCore.Qt.WA_AlwaysShowToolTips, True)
        self.start_btn.setToolTip(tip)

    def _sync_start_button(self):
        self.start_btn.setText('Restart' if self._current_started() else 'Start')
        border = self.state.get('ask') == 'border'
        self.start_btn.setEnabled(
            (not self.state['busy'] or border) and not self.blocked)
        self._sync_start_tip()
        self.conquer_btn.setEnabled(False)
        if border:
            self.spinner.setVisible(False)
            if self._current_finished():
                self.status_label.setText('done')
            else:
                self.status_label.setText('ready')
            return
        self._render_status()

    def _end_abort(self):
        self.state['cancel'].clear()
        self.state['pause'].clear()
        self.state['aborting'] = False
        self.state['phase'] = None

    def _place_start(self, home, home_layout):
        if self.start_btn.parentWidget() is home:
            return
        previous = self.start_btn.parentWidget()
        if previous is not None and previous.layout() is not None:
            previous.layout().removeWidget(self.start_btn)
        home_layout.insertWidget(2, self.start_btn)
        self.start_btn.setVisible(True)

    def _show_steps(self):
        surround = self._in_surround()
        if surround:
            self._place_start(self.surround_step, self.surround_layout)
        else:
            self.cut_label.setText(
                _STEP_TITLES.get(self.mode_box.currentData(), 'Frame'))
            self._place_start(self.cut_step, self.cut_layout)
        self.cut_step.setVisible(not surround)
        self.surround_step.setVisible(surround)
        self.conquer_step.setVisible(surround)
        self.start_btn.setVisible(True)
        self._paint_step_times()

    def set_controls(self, busy, paused=False):
        self.state['busy'] = busy
        self.state['paused'] = bool(paused) if busy else False
        if not busy:
            self.state['phase'] = None
            self.state['aborting'] = False
        self.start_btn.setVisible(True)
        self.pause_btn.setVisible(busy)
        self.pause_btn.setEnabled(busy and not self.state['cancel'].is_set())
        if busy and self.state['paused']:
            self.pause_btn.setText('Resume')
        else:
            self.pause_btn.setText('Pause')
        self.clear_btn.setEnabled(not self.state.get('opening'))
        locked = self._form_locked()
        self.mode_box.setEnabled(not locked)
        self.pad_spin.setEnabled(not busy)
        self.space_spin.setEnabled(not busy)
        self.collar_spin.setEnabled(not busy)
        self.layer_edit.setEnabled(not busy)
        self.swap_btn.setEnabled(not locked)
        self.light_edit.setEnabled(not busy)
        self.dark_edit.setEnabled(not busy)
        self.weed_edit.setEnabled(not busy)
        self.subject_edit.setEnabled(not busy)
        self.apply_btn.setEnabled((not busy) and self.state['result'] is not None)
        self._arm_surround_controls()
        self._show_steps()
        self._sync_start_button()
        if busy and self.state.get('ask') == 'border':
            self._relax_border_controls()
        self._sync_step_clock()

    def _relax_border_controls(self):
        # The border ask is not a run. Pause stays up so a wait can see it.
        self.spinner.setVisible(False)
        if self._current_finished():
            self.status_label.setText('done')
        else:
            self.status_label.setText('ready')
        self.start_btn.setEnabled(not self.blocked)
        self._sync_start_tip()
        self.pad_spin.setEnabled(True)
        self.space_spin.setEnabled(True)
        self.collar_spin.setEnabled(True)
        self.layer_edit.setEnabled(True)
        self.light_edit.setEnabled(True)
        self.dark_edit.setEnabled(True)
        self.weed_edit.setEnabled(True)
        self.subject_edit.setEnabled(True)
        self.mode_box.setEnabled(True)
        self.swap_btn.setEnabled(True)
        self.apply_btn.setEnabled(self.state['result'] is not None)
        self._arm_surround_controls()

    def on_start(self):
        ask = self.state.get('ask')
        if self.blocked or self.state.get('aborting'):
            return
        if ask not in (None, 'border'):
            return
        if self.state['busy'] and ask != 'border':
            return
        self.state['cancel'].clear()
        self.state['pause'].clear()
        self.state['phase'] = None
        if self._in_surround():
            # Start asks for the surround. It does not run a solver.
            self.state['surround_started'] = True
            self.state['surround_finished'] = False
            self.state['surround_paths'] = []
            self._reset_step_time('surround')
            self.refresh_preview()
            if not self._ask_surrounds():
                if self.state.get('ask') == 'border':
                    # The finished tuple still matches this distance.
                    # The follow would not ask. The lines are already gone.
                    self.state['surround_inflight'] = None
                    return
                if self.state.get('ask'):
                    return
                self.state['surround_started'] = False
                self._forget_step_time('surround')
                self.set_controls(False)
            return
        self.clear_weed_items()
        self.state['work'] = None
        self.state['result'] = None
        self.state['error'] = None
        self.state['seg_q'].clear()
        self.apply_btn.setEnabled(False)
        mode = self.mode_box.currentData()
        self.state['run_mode'] = mode
        if mode in self.state['cut_started']:
            self.state['cut_started'][mode] = True
            self.state['cut_finished'][mode] = False
            self._reset_step_time(mode)
        self.log_view.clear()
        self.append_log('Starting %s…\n' % mode)
        self.refresh_preview()
        self.state['last_fit'] = 0.0
        self.state['close_when_done'] = False
        if self.state.get('ask') == 'border':
            # The path and the lengths are read when this ask starts.
            self.state['solver_request'] = mode
            return
        request = self._solver_request(mode)
        if request is None or not self._begin_ask(request):
            if mode in self.state['cut_started']:
                self.state['cut_started'][mode] = False
            self._forget_step_time(mode)
            self.set_controls(False)
            self.append_log('Error: solver did not start\n')

    def _solver_request(self, mode):
        """One solver ask from the subject and lengths stored now."""
        regions = self._ensure_regions()
        if regions is None or regions.subject is None:
            return None
        padding = self.state['lengths']['padding']
        spacing = self.state['lengths']['spacing']
        collar = self.state['lengths']['collar']
        inner = self.state['lengths']['inner']
        border = self.state['lengths']['border']
        radius = _optional_length(self.state['lengths'], 'corner_radius')
        keep = self.QPainterPath(regions.subject)
        self.state['solved_keep'] = keep
        self.state['solved_pad'] = [padding, padding, padding, padding]
        elements, rule = _pack_path(keep)
        return _with_corner_radius({
            'kind': 'solver',
            'mode': mode,
            'padding': [padding, padding, padding, padding],
            'spacing': spacing,
            'collar': collar,
            'inner_distance': inner,
            'border_width': border,
            'elements': elements,
            'rule': rule,
        }, radius)

    def _sync_worker_flags(self):
        mp_pause = self.state.get('mp_pause')
        if mp_pause is not None:
            if self.state['pause'].is_set():
                mp_pause.set()
            else:
                mp_pause.clear()
        if self.state['cancel'].is_set():
            mp_cancel = self.state.get('mp_cancel')
            if mp_cancel is not None:
                mp_cancel.set()

    def on_pause_toggle(self):
        if self.state.get('ask') == 'border':
            return
        if (not self.state['busy'] or self.state['cancel'].is_set()
                or self.state.get('aborting')):
            return
        if self.state['pause'].is_set():
            self.state['pause'].clear()
            self.append_log('Resumed.\n')
            self.set_controls(True, paused=False)
        else:
            self.state['pause'].set()
            self.append_log('Paused — worker waiting; inspect preview.\n')
            self.set_controls(True, paused=True)
        self._sync_worker_flags()

    def _drop_visit_lines(self):
        self.state['result'] = None
        self.state['accepted'] = False
        self.state['error'] = None
        self.state['work'] = None
        self.state['seg_q'].clear()
        self.clear_weed_items()
        self.state['surround_paths'] = []
        self.state['surround_started'] = False
        self.state['surround_finished'] = False
        self.state['surround_inflight'] = None
        self.state['solver_request'] = None
        for key in self.state['cut_started']:
            self.state['cut_started'][key] = False
            self.state['cut_finished'][key] = False
        self._clear_step_times()
        self.apply_btn.setEnabled(False)
        self.refresh_preview()

    def on_clear(self):
        # Lines go now. A running child is not killed; it sees cancel.
        self._drop_visit_lines()
        self.start_btn.setText('Start')
        if not self.state['busy'] and not self.state.get('ask'):
            self._end_abort()
            self.set_controls(False)
            return
        self.state['aborting'] = True
        self.state['pause'].clear()
        self.state['paused'] = False
        self.state['cancel'].set()
        self._sync_worker_flags()
        self.append_log('Cancel requested — stopping algorithm…\n')
        self.pause_btn.setText('Pause')
        self.pause_btn.setEnabled(False)
        self.start_btn.setEnabled(False)
        self._sync_start_tip()
        self._render_status()

    def on_conquer(self):
        # Conquer is not specified, so this step emits no cuts.
        return

    def on_apply(self):
        # The border ask is not a run. A finished result can still apply.
        if self.state['result'] is None:
            return
        if self.state['busy'] and self.state.get('ask') != 'border':
            return
        self.state['accepted'] = True
        self.dialog.accept()

    def on_close(self):
        # Drop a late result. Do not join or kill the child. A solver
        # keeps pumping until the next progress check ends the run.
        self.state['drop'] = True
        self.state['pause'].clear()
        self.state['cancel'].set()
        self._sync_worker_flags()
        proc = self.state.get('proc')
        if (self.state.get('ask') == 'solver' and proc is not None
                and proc.is_alive()):
            self.state['close_when_done'] = True
            self.append_log('Cancel requested — stopping algorithm…\n')
            self.set_controls(True, paused=False)
            return
        self.dialog.reject()

    def _in_surround(self):
        return self.mode_box.currentData() == _SURROUND_MODE

    def _ensure_step_clock(self):
        if getattr(self, '_step_seconds', None) is not None:
            return
        self._step_seconds = {}
        self._step_active = None
        self._step_slice = None
        timer = self.QtCore.QTimer(self.dialog)
        timer.setInterval(_STEP_TICK_MS)
        timer.timeout.connect(self._tick_step_clock)
        timer.start()
        self._step_timer = timer

    def _working_step_key(self):
        # The border ask is not a started step. It does not own a time.
        if (not self.state.get('busy') or self.state.get('paused')
                or self.state.get('aborting')):
            return None
        ask = self.state.get('ask')
        if ask == 'solver':
            mode = self.state.get('run_mode')
            if mode and self.state['cut_started'].get(mode):
                return mode
        if ask == 'surround' and self.state.get('surround_started'):
            return 'surround'
        return None

    def _freeze_step_clock(self):
        key = self._step_active
        if key is None or self._step_slice is None:
            self._step_active = None
            self._step_slice = None
            return
        elapsed = time.monotonic() - self._step_slice
        if elapsed < 0.0:
            elapsed = 0.0
        self._step_seconds[key] = self._step_seconds.get(key, 0.0) + elapsed
        self._step_active = None
        self._step_slice = None

    def _sync_step_clock(self):
        self._ensure_step_clock()
        working = self._working_step_key()
        if working != self._step_active:
            self._freeze_step_clock()
            if working is not None:
                self._step_active = working
                self._step_slice = time.monotonic()
                self._step_seconds.setdefault(working, 0.0)
        self._paint_step_times()

    def _reset_step_time(self, key):
        self._ensure_step_clock()
        if self._step_active == key:
            self._step_active = None
            self._step_slice = None
        self._step_seconds[key] = 0.0
        for later in _LATER_STEPS.get(key, ()):
            self._step_seconds.pop(later, None)
        self._paint_step_times()

    def _forget_step_time(self, key):
        if getattr(self, '_step_seconds', None) is None:
            return
        if self._step_active == key:
            self._step_active = None
            self._step_slice = None
        self._step_seconds.pop(key, None)
        self._paint_step_times()

    def _clear_step_times(self):
        if getattr(self, '_step_seconds', None) is None:
            self._paint_step_times()
            return
        self._step_active = None
        self._step_slice = None
        self._step_seconds.clear()
        self._paint_step_times()

    def _shown_step_seconds(self, key):
        total = 0.0
        if getattr(self, '_step_seconds', None) is not None:
            total = self._step_seconds.get(key, 0.0)
        if self._step_active == key and self._step_slice is not None:
            live = time.monotonic() - self._step_slice
            if live > 0.0:
                total += live
        if total < 0.0:
            total = 0.0
        return total

    def _format_step_time(self, seconds):
        return '%.1f' % seconds

    def _paint_step_times(self):
        clocks = getattr(self, '_step_clocks', None)
        if not clocks or not hasattr(self, 'state'):
            return
        mode = self.mode_box.currentData()
        cut = clocks.get('step-cut')
        if cut is not None:
            if mode and self.state['cut_started'].get(mode):
                cut.setText(self._format_step_time(self._shown_step_seconds(mode)))
            else:
                cut.setText('')
        surround = clocks.get('step-surround')
        if surround is not None:
            if self.state.get('surround_started'):
                surround.setText(self._format_step_time(
                    self._shown_step_seconds('surround')))
            else:
                surround.setText('')
        conquer = clocks.get('step-conquer')
        if conquer is not None:
            conquer.setText('')

    def _tick_step_clock(self):
        # The tick only rewrites the time labels. It does not ask or repaint.
        self._paint_step_times()
