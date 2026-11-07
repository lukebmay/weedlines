# -*- coding: utf-8 -*-
"""Build the dialog, run it, and return the Apply path, the layer name, and the weed-line color."""
from __future__ import division

import threading
from collections import deque

from .form import (
    _DISPLAY_UNITS,
    _Form,
    _LENGTH_LIMITS,
    _OptionStack,
    _QUARTER_INCH,
    _SURROUND_MODE,
    _display_unit_name,
    _opening_mode,
)
from .geometry_ask import _ASK_HOLD, _ASK_TRACE, _Ask, _burn_hold, _spawn_ask
from .inbox import _Inbox
from .preview import _Preview, _checker_type
from .return_line import _ReturnLine
from .run_controls import _RunControls

class _Window(_Form, _RunControls, _ReturnLine, _Preview, _Inbox, _Ask):
    def run(self, records, defaults=None, platform_lines=None,
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
        *user_unit_scale* is how many inches one user unit is. Lengths
        on the form are shown in that display unit. Padding, spacing,
        the collar, the surround distance, and the join gap still reach
        the library in document user units. The join gap starts at a
        quarter inch in those units. *defaults*
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
        The surround is not asked until Start. That ask uses
        the same spawn target. This thread builds the paths and paints
        them. It does not run the surround or a solver on this thread.
        """
        self.records = records
        self.platform_lines = platform_lines
        self.ready = ready
        from weedlib import padded_work_rect
        from weedlib.arrows import ArrowPath
        from weedlib.qt import QPainterPath, load_widgets
        from weedlines_job import write_correction_result
        from weedlines_svg import _INCHES_PER_UNIT as _UNIT_INCHES
        self.padded_work_rect = padded_work_rect
        self.ArrowPath = ArrowPath
        self.QPainterPath = QPainterPath
        self.write_correction_result = write_correction_result
        self._UNIT_INCHES = _UNIT_INCHES

        self.QtCore, self.QtGui, self.QtWidgets = load_widgets()
        defaults = dict(defaults or {})
        # Filled once the window is visible, before ready.
        self.check = None
        self.blocked = True

        app = self.QtWidgets.QApplication.instance()
        owns_app = False
        if app is None:
            app = self.QtWidgets.QApplication([])
            owns_app = True

        self.dialog = self.QtWidgets.QDialog()
        self.dialog.setWindowTitle('Weedlines')
        self.dialog.doc_width = width
        self.dialog.doc_height = height
        self.dialog.doc_viewbox = view_box
        self.dialog.display_unit = display_unit or 'px'
        if user_unit_scale is None:
            self.dialog.user_unit_scale = 1.0 / 96.0
        else:
            self.dialog.user_unit_scale = float(user_unit_scale)
        shown_unit = _display_unit_name(self.dialog.display_unit)
        if not self._UNIT_INCHES.get(shown_unit):
            shown_unit = 'px'
        self.dialog.resize(720, 760)
        # WindowModal: don't freeze every Qt window in a multi-app session;
        # when hosted inside Inkscape's process this still blocks that app.
        self.dialog.setWindowModality(self.QtCore.Qt.WindowModal)

        self.root = self.QtWidgets.QVBoxLayout(self.dialog)

        form = self.QtWidgets.QFormLayout()
        self.mode_box = self.QtWidgets.QComboBox()
        self.mode_box.setObjectName('mode')
        self.mode_box.addItem(_SURROUND_MODE, _SURROUND_MODE)
        self.mode_box.addItem('Frame (box)', 'frame')
        self.mode_box.addItem('Grid (clipped)', 'grid')
        self.mode_box.addItem('Island hop', 'island-hop')
        want_mode = _opening_mode(defaults)
        for i in range(self.mode_box.count()):
            if self.mode_box.itemData(i) == want_mode:
                self.mode_box.setCurrentIndex(i)
                break
        self.distance_label = self.QtWidgets.QLabel('Surround distance')
        self.distance_label.setObjectName('surround-distance-label')
        self.distance_spin = self.QtWidgets.QDoubleSpinBox()
        self.distance_spin.setObjectName('surround-distance')
        self.distance_spin.setDecimals(4)
        self.distance_spin.setSingleStep(0.1)
        self.distance_spin.setEnabled(False)
        self.join_label = self.QtWidgets.QLabel('Join gap')
        self.join_label.setObjectName('join-gap-label')
        self.join_spin = self.QtWidgets.QDoubleSpinBox()
        self.join_spin.setObjectName('join-gap')
        self.join_spin.setDecimals(4)
        self.join_spin.setSingleStep(0.1)
        self.join_spin.setEnabled(False)
        self.pad_label = self.QtWidgets.QLabel('Padding')
        self.pad_label.setObjectName('padding-label')
        self.pad_spin = self.QtWidgets.QDoubleSpinBox()
        self.pad_spin.setObjectName('padding')
        self.pad_spin.setDecimals(4)
        self.space_label = self.QtWidgets.QLabel('Grid spacing')
        self.space_label.setObjectName('spacing-label')
        self.space_spin = self.QtWidgets.QDoubleSpinBox()
        self.space_spin.setObjectName('spacing')
        self.space_spin.setDecimals(4)
        self.collar_label = self.QtWidgets.QLabel('Collar (island-hop)')
        self.collar_label.setObjectName('collar-label')
        self.collar_spin = self.QtWidgets.QDoubleSpinBox()
        self.collar_spin.setObjectName('collar')
        self.collar_spin.setDecimals(4)
        self.layer_label = self.QtWidgets.QLabel('Output layer')
        self.layer_edit = self.QtWidgets.QLineEdit(str(defaults.get('layer_name', 'Weed lines')))
        self.layer_edit.setObjectName('layer-name')
        self.unit_box = self.QtWidgets.QComboBox()
        self.unit_box.setObjectName('display-unit')
        for _name in _DISPLAY_UNITS:
            if _name in self._UNIT_INCHES:
                self.unit_box.addItem(_name, _name)
        _unit_index = self.unit_box.findData(shown_unit)
        if _unit_index < 0:
            _unit_index = self.unit_box.findData('px')
        self.unit_box.setCurrentIndex(_unit_index)
        form.addRow('Mode', self.mode_box)
        form.addRow('Display unit', self.unit_box)
        form.addRow(self.distance_label, self.distance_spin)
        form.addRow(self.join_label, self.join_spin)
        form.addRow(self.pad_label, self.pad_spin)
        form.addRow(self.space_label, self.space_spin)
        form.addRow(self.collar_label, self.collar_spin)
        form.addRow(self.layer_label, self.layer_edit)

        self.swap_btn = self.QtWidgets.QPushButton('Swap subject and weed area')
        self.swap_btn.setObjectName('swap')
        self.swap_btn.setEnabled(False)
        form.addRow(self.swap_btn)
        self.light_edit = self._color_edit('checkerboard-light', '#E6E6E6')
        self.dark_edit = self._color_edit('checkerboard-dark', '#CFCFCF')
        self.weed_edit = self._color_edit('weed-line-color', '#FF0000')
        self.subject_edit = self._color_edit('default-subject-color', '#FFFFFF')
        form.addRow('Checkerboard light', self.light_edit)
        form.addRow('Checkerboard dark', self.dark_edit)
        form.addRow('Weed line color', self.weed_edit)
        form.addRow('Default subject color', self.subject_edit)
        self.root.addLayout(form)

        self.cut_step, self.cut_layout, self.cut_label = self._step_line('step-cut', 'Frame', 'current')
        self.surround_step, self.surround_layout, _surround_label = self._step_line(
            'step-surround', 'Surround', 'current')
        self.conquer_step, conquer_layout, _conquer_label = self._step_line(
            'step-conquer', 'Conquer', 'left')
        self.conquer_btn = self.QtWidgets.QPushButton('Start')
        self.conquer_btn.setObjectName('conquer-start')
        self.conquer_btn.setEnabled(False)
        conquer_layout.insertWidget(2, self.conquer_btn)
        steps = self.QtWidgets.QVBoxLayout()
        steps.addWidget(self.cut_step)
        steps.addWidget(self.surround_step)
        steps.addWidget(self.conquer_step)
        self.root.addLayout(steps)

        self.start_btn = self.QtWidgets.QPushButton('Start')
        self.start_btn.setObjectName('start')
        self.start_btn.setEnabled(False)
        self.pause_btn = self.QtWidgets.QPushButton('Pause')
        self.pause_btn.setObjectName('pause')
        self.pause_btn.hide()
        self.clear_btn = self.QtWidgets.QPushButton('Clear All')
        self.clear_btn.setObjectName('clear-all')
        self.clear_btn.setEnabled(False)
        self.apply_btn = self.QtWidgets.QPushButton('Apply')
        self.apply_btn.setObjectName('apply')
        self.apply_btn.setEnabled(False)
        close_btn = self.QtWidgets.QPushButton('Close')
        close_btn.setObjectName('close')
        btn_row = self.QtWidgets.QHBoxLayout()
        btn_row.addWidget(self.pause_btn)
        btn_row.addWidget(self.clear_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(self.apply_btn)
        btn_row.addWidget(close_btn)
        self.root.addLayout(btn_row)

        status_row = self.QtWidgets.QHBoxLayout()
        self.spinner = self.QtWidgets.QProgressBar()
        self.spinner.setObjectName('spinner')
        self.spinner.setRange(0, 0)
        self.spinner.setTextVisible(False)
        self.spinner.setFixedSize(18, 18)
        self.spinner.hide()
        self.status_label = self.QtWidgets.QLabel('ready')
        self.status_label.setObjectName('status')
        self.status_label.setTextFormat(self.QtCore.Qt.PlainText)
        self.status_label.setStyleSheet('color: #c0c0c0;')
        status_row.addWidget(self.spinner)
        status_row.addWidget(self.status_label, stretch=1)
        self.root.addLayout(status_row)

        log_label = self.QtWidgets.QLabel('Algorithm output (stdout / stderr)')
        self.root.addWidget(log_label)
        self.log_view = self.QtWidgets.QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(5000)
        self.log_view.setMinimumHeight(72)
        self.log_view.setSizePolicy(
            self.QtWidgets.QSizePolicy.Expanding, self.QtWidgets.QSizePolicy.Preferred)
        splitter = self.QtWidgets.QSplitter(self.QtCore.Qt.Vertical)
        splitter.addWidget(self.log_view)

        self.scene = self.QtWidgets.QGraphicsScene()
        self.scene.setBackgroundBrush(self.QtGui.QBrush(self.QtCore.Qt.NoBrush))
        self.view = self.QtWidgets.QGraphicsView(self.scene)
        self.view.setObjectName('preview')
        self.view.setRenderHints(
            self.QtGui.QPainter.Antialiasing | self.QtGui.QPainter.SmoothPixmapTransform)
        self.view.setBackgroundBrush(self.QtGui.QBrush(self.QtGui.QColor('#1e1e1e')))
        self.view.setMinimumHeight(180)
        splitter.addWidget(self.view)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setChildrenCollapsible(False)
        splitter.setMinimumHeight(72 + 180)
        splitter.setSizes([90, 400])
        self.root.addWidget(splitter, stretch=1)

        self.return_line = self.QtWidgets.QLabel()
        self.return_line.setObjectName('return-line')
        self.return_line.setWordWrap(True)
        self.return_line.setTextFormat(self.QtCore.Qt.PlainText)
        self.return_line.setText('')
        return_btn = self.QtWidgets.QPushButton('Return to Inkscape')
        return_btn.setObjectName('return-inkscape')
        self.return_row = self.QtWidgets.QHBoxLayout()
        self.return_row.addWidget(return_btn)
        self.return_row.addStretch(1)
        self.root.addWidget(self.return_line)
        self.root.addLayout(self.return_row)

        self.state = {
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
            'surround_finished': False,
            'cut_started': {
                'frame': False,
                'grid': False,
                'island-hop': False,
            },
            'cut_finished': {
                'frame': False,
                'grid': False,
                'island-hop': False,
            },
            'phase': None,
            'aborting': False,
            'run_mode': None,
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
            'correction_labels': [],
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
            'solver_args': [],
            'lengths': {
                'padding': float(defaults.get('padding', 4.0)),
                'spacing': float(defaults.get('spacing', 25.0)),
                'collar': float(defaults.get('collar', 4.0)),
                'distance': 0.0,
                'join': _QUARTER_INCH / self.dialog.user_unit_scale,
            },
            'limits': dict(_LENGTH_LIMITS),
            'unit': shown_unit,
            'unit_inches': self._UNIT_INCHES[shown_unit],
            'applying_unit': False,
            'last_fit': 0.0,
            'close_when_done': False,
        }
        self.dialog.worker_calls = self.state['calls']
        self.dialog.worker_swaps = self.state['swaps']
        self.dialog.surround_args = self.state['surround_args']
        self.dialog.solver_keeps = self.state['solver_keeps']
        self.dialog.solver_args = self.state['solver_args']
        self.dialog.focus_mark = None
        self.dialog.focus_named = None
        self.dialog.ask_name = None
        self.dialog.last_phase = None
        # Baselines for committed options. Opening values are not edits.
        self.state['history_lengths'] = dict(self.state['lengths'])
        self.state['history_mode'] = self.mode_box.currentIndex()
        self.state['history_layer'] = self.layer_edit.text()
        self.state['applying_history'] = False
        self.CheckerItem = _checker_type(self.QtWidgets, self.QtGui, self.QtCore)

        # QApplication often emits the Wayland warning during construction above.
        self.drain_platform_lines()

        self.start_btn.clicked.connect(self.on_start)
        self.pause_btn.clicked.connect(self.on_pause_toggle)
        self.clear_btn.clicked.connect(self.on_clear)
        self.conquer_btn.clicked.connect(self.on_conquer)
        self.apply_btn.clicked.connect(self.on_apply)
        close_btn.clicked.connect(self.on_close)
        return_btn.clicked.connect(self.on_return)
        self.swap_btn.clicked.connect(self._on_swap)
        self.mode_box.currentIndexChanged.connect(self._on_mode)

        self._show_lengths()
        self._remember_length('distance', self.distance_spin, self._on_surround_length)
        self._remember_length('join', self.join_spin, self._on_surround_length)
        self._remember_length('padding', self.pad_spin, None)
        self._remember_length('spacing', self.space_spin, None)
        self._remember_length('collar', self.collar_spin, None)
        self.unit_box.currentIndexChanged.connect(self._on_unit)
        for _edit in (self.light_edit, self.dark_edit, self.weed_edit, self.subject_edit):
            _edit.editingFinished.connect(
                lambda edit=_edit: self._commit_color(edit))

        self.option_stack = _OptionStack()

        self._install_option_keys()

        self.layer_edit.editingFinished.connect(self._commit_layer)

        hint = self.QtWidgets.QLabel(
            'Builds weed cuts only (no cutter travel planning). '
            'Pause holds the run so you can inspect the live preview, '
            'then Resume. Clear All discards the lines from this visit. '
            'After Apply, use Extensions → Weedlines → Reimport last weedlines '
            'in Inkscape — that brings back the design and cuts together at '
            'the original size and position. '
            'Place correction arrows with Extensions → Weedlines → '
            'Reimport last ready.')
        hint.setObjectName('hint')
        hint.setWordWrap(True)
        self.root.addWidget(hint)

        self._show_surround_controls()
        self._show_mode_knobs()
        self._show_steps()

        self.dialog.rejected.connect(self._mark_closed)

        self.QtCore.QTimer.singleShot(0, self._shown)

        self.dialog.setMinimumHeight(self.dialog.sizeHint().height())
        self.dialog.resize(720, max(760, self.dialog.sizeHint().height()))

        result_code = self.dialog.exec_()
        layer_name = self.layer_edit.text().strip() or 'Weed lines'
        weed = self.state['result'] if self.state['accepted'] and result_code else None
        if owns_app and quit_app:
            app.quit()
        ready_error = self.state.pop('ready_error', None)
        if ready_error is not None:
            raise ready_error
        if weed is None:
            return None, None, None
        return weed, layer_name, self.weed_edit.property('color')

    def _shown(self):
        # exec_ has shown the dialog. The ask returns here; ready is later.
        if self.state['asked']:
            return
        self.state['asked'] = True
        self.state['opening'] = True
        try:
            self._begin_ask({
                'kind': 'classify',
                'records': list(self.records or []),
            })
        except Exception as exc:
            self.state['ready_error'] = exc
            self.dialog.reject()

    def _mark_closed(self):
        self.state['drop'] = True


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
    *user_unit_scale* is how many inches one user unit is. Lengths
    on the form are shown in that display unit. Padding, spacing,
    the collar, the surround distance, and the join gap still reach
    the library in document user units. The join gap starts at a
    quarter inch in those units. *defaults*
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
    The surround is not asked until Start. That ask uses
    the same spawn target. This thread builds the paths and paints
    them. It does not run the surround or a solver on this thread.
    """
    return _Window().run(
        records, defaults=defaults, platform_lines=platform_lines,
        quit_app=quit_app, width=width, height=height,
        view_box=view_box, display_unit=display_unit,
        user_unit_scale=user_unit_scale, ready=ready)
