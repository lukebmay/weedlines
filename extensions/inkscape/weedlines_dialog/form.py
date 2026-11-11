# -*- coding: utf-8 -*-
"""Options form: mode, display unit, lengths, colors, swap, and option history."""
from __future__ import division



_SURROUND_MODE = 'Surround and Conquer'


_CUT_MODES = ('frame', 'grid', 'island-hop')


# Quarter inch. The user-unit count is this divided by the document scale.
_QUARTER_INCH = 0.25


# Eighth inch. The user-unit count is this divided by the document scale.
_EIGHTH_INCH = 0.125


# Inkscape's linear display units. Percent and em are not lengths.
# q, yd, and km stay off this list. They remain SVG length units.
_DISPLAY_UNITS = (
    'px', 'in', 'ft', 'mm', 'cm', 'm', 'pt', 'pc',
)


# Solver counts, in document user units. The spin shows them converted.
_LENGTH_LIMITS = {
    'padding': (0.0, 200.0),
    'spacing': (1.0, 200.0),
    'collar': (0.0, 50.0),
    'distance': (0.0, 1000000.0),
    'join': (0.0, 1000000.0),
    'inner': (0.0, 1000000.0),
    'border': (0.0, 1000000.0),
}


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
    # Without a border, the button style does not paint the fill.
    edit.setStyleSheet(
        'background-color: %s; color: %s; border: 1px solid %s;'
        % (color, ink, ink))


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


def _display_unit_name(name):
    """An absolute display length, or px when *name* is not one."""
    key = str(name or '').strip().lower()
    if key in _DISPLAY_UNITS:
        return key
    return 'px'


def _to_display(user_units, scale, inches):
    return float(user_units) * float(scale) / float(inches)


def _to_user(shown, scale, inches):
    return float(shown) * float(inches) / float(scale)


class _OptionCommand(object):
    def __init__(self, redo_fn, undo_fn):
        self._redo_fn = redo_fn
        self._undo_fn = undo_fn
        # push() calls redo while the control already shows the new value.
        self._armed = False

    def redo(self):
        if not self._armed:
            self._armed = True
            return
        self._redo_fn()

    def undo(self):
        self._undo_fn()


class _OptionStack(object):
    def __init__(self):
        self._items = []
        self._index = 0

    def push(self, command):
        del self._items[self._index:]
        self._items.append(command)
        self._index += 1
        command.redo()

    def undo(self):
        if self._index <= 0:
            return
        self._index -= 1
        self._items[self._index].undo()

    def redo(self):
        if self._index >= len(self._items):
            return
        self._items[self._index].redo()
        self._index += 1


class _Form(object):

    def _color_edit(self, name, initial):
        edit = self.QtWidgets.QPushButton(initial)
        edit.setObjectName(name)
        edit.setAutoDefault(False)
        edit.setDefault(False)
        edit.setProperty('color', initial)
        _tint_edit(edit, initial)
        edit.clicked.connect(lambda _checked=False, edit=edit: self._open_color(edit))
        return edit

    def _hide_saved_colors(self, picker):
        # Custom colors are written to a Qt preferences file.
        add = picker.tr('&Add to Custom Colors')
        heading = picker.tr('&Custom colors')
        for button in picker.findChildren(self.QtWidgets.QPushButton):
            if button.text() == add:
                button.hide()
        for label in picker.findChildren(self.QtWidgets.QLabel):
            if label.text() != heading:
                continue
            label.hide()
            buddy = label.buddy()
            if buddy is not None:
                buddy.hide()

    def _open_color(self, edit):
        if not edit.isEnabled():
            return
        if self.state['busy'] and self.state.get('ask') != 'border':
            return
        picker = self.QtWidgets.QColorDialog(self.dialog)
        picker.setObjectName('color-picker')
        # The platform dialog cannot be driven offscreen, and it can store colors.
        picker.setOption(
            self.QtWidgets.QColorDialog.DontUseNativeDialog, True)
        picker.setCurrentColor(self.QtGui.QColor(edit.property('color')))
        self._hide_saved_colors(picker)
        accepted = picker.exec_() == self.QtWidgets.QDialog.Accepted
        chosen = picker.selectedColor() if accepted else None
        picker.setObjectName('')
        picker.deleteLater()
        self.dialog.activateWindow()
        if chosen is None or not chosen.isValid():
            return
        edit.setText(chosen.name())
        self._commit_color(edit)

    def _show_surround_controls(self):
        show = self._in_surround()
        self.distance_label.setVisible(show)
        self.distance_spin.setVisible(show)
        self.join_label.setVisible(show)
        self.join_spin.setVisible(show)

    def _show_mode_knobs(self):
        # Hiding keeps the value.
        mode = self.mode_box.currentData()
        cut = mode in _CUT_MODES
        self.pad_label.setVisible(cut)
        self.pad_spin.setVisible(cut)
        self.space_label.setVisible(mode == 'grid')
        self.space_spin.setVisible(mode == 'grid')
        hop = mode == 'island-hop'
        self.collar_label.setVisible(hop)
        self.collar_spin.setVisible(hop)
        self.layer_label.setVisible(cut)
        self.layer_edit.setVisible(cut)

    def _arm_surround_controls(self):
        live = not self._form_locked()
        self.distance_spin.setEnabled(live)
        self.join_spin.setEnabled(live)
        self._arm_border_controls()

    def _arm_border_controls(self):
        if getattr(self, 'inner_spin', None) is None:
            return
        # A border ask is not a solver run. The spins stay editable.
        busy = bool(self.state.get('busy')) and self.state.get('ask') != 'border'
        self.inner_spin.setEnabled(not busy)
        self.border_spin.setEnabled(not busy)
        self.round_box.setEnabled(not busy)
        self.radius_spin.setEnabled(not busy)

    def _on_swap(self):
        if self.state.get('opening') or self._solver_running():
            return
        if self.state['busy'] and self.state.get('ask') not in ('surround', 'border'):
            return
        self.state['swapped'] = not self.state['swapped']
        if self.state.get('ask') == 'surround':
            # The swap flag is already toggled. The arrival starts
            # the subject ask. This thread does not wait on the child.
            return
        app_loop = self.QtWidgets.QApplication.instance()
        while self.state.get('ask') == 'border' and self.dialog.isVisible():
            app_loop.processEvents(self.QtCore.QEventLoop.AllEvents, 50)
        if self.state['swapped'] != self.state.get('regions_swap'):
            if self.state.get('ask') != 'subject':
                if not self._begin_ask(self._subject_request()):
                    self.state['swapped'] = not self.state['swapped']
                    return
            while self.state.get('ask') == 'subject' and self.dialog.isVisible():
                app_loop.processEvents(self.QtCore.QEventLoop.AllEvents, 50)
        # The new subject is stored. Ask for its border.
        self._ask_border()

    def _on_mode(self, _index=None):
        self._remember_mode()
        if self.state.get('applying_history'):
            # Restoring the mode shows its knobs. It does not remove
            # a surround or a cut already on screen.
            self._show_surround_controls()
            self._show_mode_knobs()
            self._arm_surround_controls()
            self._show_steps()
            self._sync_start_button()
            return
        if self._solver_running() or self.state.get('ask') not in (None, 'surround', 'border'):
            return
        had_surrounds = bool(self.state['surround_paths'])
        self._show_surround_controls()
        self._show_mode_knobs()
        self._arm_surround_controls()
        self._show_steps()
        self._sync_start_button()
        if self.state['surround_started'] and not self.blocked and self._in_surround():
            if self.state.get('ask'):
                return
            self._ask_surrounds()
            return
        self.state['surround_paths'] = []
        # Cut-mode changes do not rebuild arrows or the checkerboard.
        if had_surrounds:
            self.refresh_preview()

    def _on_surround_length(self, value=None):
        if isinstance(value, str):
            return
        if (self.blocked or self.state.get('opening') or self._solver_running()
                or not self.state['surround_started'] or not self._in_surround()):
            return
        if self.state.get('ask'):
            # The spin already holds the newer length. Do not paint
            # the in-flight result when it arrives.
            return
        self._ask_surrounds()

    def _on_piece_length(self, key=None):
        # Border width asks for the border only. Padding, the checkbox,
        # and the radius also ask for a surround that is already showing.
        if not isinstance(key, str):
            key = None
        if key not in (None, 'inner', 'border', 'corner_radius'):
            return
        self._show_radius_spin()
        self._sync_applied_radius()
        if (self.blocked or self.state.get('opening') or self._solver_running()
                or self.state.get('drop')):
            return
        if self.state.get('ask'):
            # The stored length is already new. Do not paint this ask.
            return
        if self._ask_border():
            return
        if key == 'border':
            return
        if self._surround_due() and self._surround_stale():
            self._ask_surrounds()

    def _form_layout(self):
        root = self.dialog.layout()
        if root is None:
            return None
        for index in range(root.count()):
            item = root.itemAt(index)
            if item is None:
                continue
            layout = item.layout()
            if isinstance(layout, self.QtWidgets.QFormLayout):
                return layout
        return None

    def _ensure_border_controls(self):
        if getattr(self, 'inner_spin', None) is not None:
            return
        scale = float(self.dialog.user_unit_scale) or 1.0
        # Kept even while the box is off. corner_radius is the applied one.
        self.state['lengths']['border_radius'] = _QUARTER_INCH / scale
        self.state['history_round'] = False
        self.state['history_include'] = False
        label = self.QtWidgets.QLabel
        spin = self.QtWidgets.QDoubleSpinBox
        self.inner_label = label('Border Padding')
        self.inner_label.setObjectName('border-padding-label')
        self.inner_spin = spin()
        self.inner_spin.setObjectName('border-padding')
        self.inner_spin.setDecimals(4)
        self.inner_spin.setSingleStep(0.1)
        self.border_label = label('Border Width')
        self.border_label.setObjectName('border-width-label')
        self.border_spin = spin()
        self.border_spin.setObjectName('border-width')
        self.border_spin.setDecimals(4)
        self.border_spin.setSingleStep(0.1)
        self.round_label = label('Border Rounded Corners')
        self.round_label.setObjectName('border-rounded-label')
        self.round_box = self.QtWidgets.QCheckBox()
        self.round_box.setObjectName('border-rounded')
        self.radius_label = label('Border Corner Radius')
        self.radius_label.setObjectName('border-corner-radius-label')
        self.radius_spin = spin()
        self.radius_spin.setObjectName('border-corner-radius')
        self.radius_spin.setDecimals(4)
        self.radius_spin.setSingleStep(0.1)
        self.include_label = label('Include original design')
        self.include_label.setObjectName('include-original-label')
        self.include_box = self.QtWidgets.QCheckBox()
        self.include_box.setObjectName('include-original')
        form = self._form_layout()
        if form is not None:
            found = form.getWidgetPosition(self.join_spin)
            row = found[0] if found else -1
            if row < 0:
                form.addRow(self.inner_label, self.inner_spin)
                form.addRow(self.border_label, self.border_spin)
                form.addRow(self.round_label, self.round_box)
                form.addRow(self.radius_label, self.radius_spin)
                form.addRow(self.include_label, self.include_box)
            else:
                form.insertRow(row + 1, self.include_label, self.include_box)
                form.insertRow(row + 1, self.radius_label, self.radius_spin)
                form.insertRow(row + 1, self.round_label, self.round_box)
                form.insertRow(row + 1, self.border_label, self.border_spin)
                form.insertRow(row + 1, self.inner_label, self.inner_spin)
        self._show_radius_row(False)
        self._remember_length(
            'inner', self.inner_spin, lambda: self._on_piece_length('inner'))
        self._remember_length(
            'border', self.border_spin, lambda: self._on_piece_length('border'))
        self._remember_length(
            'border_radius', self.radius_spin, self._on_kept_radius)
        self.round_box.toggled.connect(self._on_round_toggled)
        self.include_box.toggled.connect(self._on_include_toggled)

    def _show_radius_row(self, show):
        visible = bool(show)
        self.radius_label.setVisible(visible)
        self.radius_spin.setVisible(visible)

    def _subject_rect(self):
        regions = self.state.get('regions')
        if regions is None or regions.subject is None or regions.subject.isEmpty():
            return None
        return regions.subject.boundingRect()

    def _radius_cap(self):
        """Half the shorter side of the inner rectangle, in user units."""
        rect = self._subject_rect()
        if rect is None:
            return None
        inner = float(self.state['lengths'].get('inner') or 0.0)
        width = float(rect.width()) + 2.0 * inner
        height = float(rect.height()) + 2.0 * inner
        shorter = min(width, height)
        if shorter <= 0.0:
            return 0.0
        return shorter * 0.5

    def _clamp_kept_radius(self):
        if getattr(self, 'radius_spin', None) is None:
            return
        if 'border_radius' not in self.state['lengths']:
            return
        kept = float(self.state['lengths']['border_radius'])
        if kept < 0.0:
            kept = 0.0
        cap = self._radius_cap()
        if cap is not None and kept > cap:
            kept = cap
        self.state['lengths']['border_radius'] = kept

    def _sync_applied_radius(self):
        # The ask forwards corner_radius whenever the key is set.
        if getattr(self, 'round_box', None) is None:
            return
        if self.round_box.isChecked():
            self.state['lengths']['corner_radius'] = float(
                self.state['lengths']['border_radius'])
        else:
            self.state['lengths'].pop('corner_radius', None)

    def _show_radius_spin(self):
        if getattr(self, 'radius_spin', None) is None:
            return
        self._clamp_kept_radius()
        scale = self.dialog.user_unit_scale
        inches = self.state['unit_inches']
        kept = float(self.state['lengths']['border_radius'])
        cap = self._radius_cap()
        hi_user = max(kept, 1000000.0) if cap is None else max(cap, kept)
        shown = _to_display(kept, scale, inches)
        shown_hi = _to_display(hi_user, scale, inches)
        spin = self.radius_spin
        spin.blockSignals(True)
        spin.setSuffix(' ' + self.state['unit'])
        spin.setRange(min(0.0, shown), max(shown_hi, shown))
        if spin.maximum() < shown:
            spin.setMaximum(shown)
        if spin.minimum() > shown:
            spin.setMinimum(shown)
        spin.setValue(shown)
        spin.blockSignals(False)

    def _on_kept_radius(self, _value=None):
        self._on_piece_length('corner_radius')

    def _on_round_toggled(self, checked):
        self._show_radius_row(bool(checked))
        self._clamp_kept_radius()
        self._sync_applied_radius()
        if self.state.get('applying_history') or self.state.get('applying_unit'):
            return
        old = bool(self.state.get('history_round'))
        new = bool(checked)
        self.state['history_round'] = new
        self._on_piece_length('corner_radius')
        if new == old or self.state.get('opening'):
            return
        self._push_option(
            lambda value=new: self._restore_round(value),
            lambda value=old: self._restore_round(value))

    def _restore_round(self, checked):
        self.state['applying_history'] = True
        try:
            self.state['history_round'] = bool(checked)
            self.round_box.setChecked(bool(checked))
        finally:
            self.state['applying_history'] = False
        self._show_radius_row(bool(checked))
        self._sync_applied_radius()
        self._on_piece_length('corner_radius')

    def _on_include_toggled(self, checked):
        # The choice is the result. It does not ask for the border.
        if self.state.get('applying_history'):
            return
        old = bool(self.state.get('history_include'))
        new = bool(checked)
        self.state['history_include'] = new
        if new == old or self.state.get('opening'):
            return
        self._push_option(
            lambda value=new: self._restore_include(value),
            lambda value=old: self._restore_include(value))

    def _restore_include(self, checked):
        self.state['applying_history'] = True
        try:
            self.state['history_include'] = bool(checked)
            self.include_box.setChecked(bool(checked))
        finally:
            self.state['applying_history'] = False

    def _show_lengths(self):
        """Show stored user-unit lengths in the current display unit."""
        self._ensure_border_controls()
        scale = self.dialog.user_unit_scale
        inches = self.state['unit_inches']
        suffix = ' ' + self.state['unit']
        spins = (
            ('distance', self.distance_spin),
            ('join', self.join_spin),
            ('padding', self.pad_spin),
            ('spacing', self.space_spin),
            ('collar', self.collar_spin),
            ('inner', self.inner_spin),
            ('border', self.border_spin),
        )
        self.state['applying_unit'] = True
        try:
            for key, spin in spins:
                shown = _to_display(self.state['lengths'][key], scale, inches)
                lo, hi = self.state['limits'][key]
                shown_lo = _to_display(lo, scale, inches)
                shown_hi = _to_display(hi, scale, inches)
                if shown_lo > shown_hi:
                    shown_lo, shown_hi = shown_hi, shown_lo
                # A count the user-unit range allows must survive the spin.
                shown_lo = min(shown_lo, shown)
                shown_hi = max(shown_hi, shown)
                spin.blockSignals(True)
                spin.setSuffix(suffix)
                spin.setRange(shown_lo, shown_hi)
                if spin.maximum() < shown:
                    spin.setMaximum(shown)
                if spin.minimum() > shown:
                    spin.setMinimum(shown)
                spin.setValue(shown)
                spin.blockSignals(False)
        finally:
            self.state['applying_unit'] = False
        self._show_radius_spin()
        self._sync_applied_radius()
        # A show from user units is not a committed edit.
        for key, value in self.state['lengths'].items():
            self.state['history_lengths'][key] = float(value)

    def _remember_length(self, key, spin, follow):
        def edited(_value):
            if self.state.get('applying_unit'):
                return
            old_user = float(self.state['history_lengths'][key])
            new_user = _to_user(
                spin.value(), self.dialog.user_unit_scale, self.state['unit_inches'])
            self.state['lengths'][key] = new_user
            if follow is not None:
                follow()
            if self.state.get('applying_history'):
                return
            if abs(new_user - old_user) <= 1e-9:
                return
            self.state['history_lengths'][key] = new_user
            self._push_length(key, old_user, new_user)
        spin.valueChanged.connect(edited)

    def _on_unit(self, _index=None):
        name = self.unit_box.currentData()
        inches = self._UNIT_INCHES.get(name)
        if not inches:
            return
        self.state['unit'] = name
        self.state['unit_inches'] = inches
        self._show_lengths()

    def _push_option(self, redo_fn, undo_fn):
        if self.state.get('applying_history'):
            return
        self.option_stack.push(_OptionCommand(redo_fn, undo_fn))

    def _restore_length(self, key, user_units):
        self.state['applying_history'] = True
        try:
            self.state['lengths'][key] = float(user_units)
            self._show_lengths()
        finally:
            self.state['applying_history'] = False
        if key in ('distance', 'join'):
            self._on_surround_length(self.state['lengths'][key])
        elif key == 'inner':
            self._clamp_kept_radius()
            self._sync_applied_radius()
            self._on_piece_length('inner')
        elif key == 'border':
            self._on_piece_length('border')
        elif key == 'border_radius':
            self._clamp_kept_radius()
            self._sync_applied_radius()
            self._on_piece_length('corner_radius')

    def _push_length(self, key, old_user, new_user):
        self._push_option(
            lambda key=key, value=new_user: self._restore_length(key, value),
            lambda key=key, value=old_user: self._restore_length(key, value))

    def _restore_mode(self, index):
        self.state['applying_history'] = True
        try:
            self.state['history_mode'] = index
            self.mode_box.setCurrentIndex(index)
        finally:
            self.state['applying_history'] = False

    def _remember_mode(self):
        if self.state.get('applying_history'):
            return
        new_index = self.mode_box.currentIndex()
        old_index = self.state['history_mode']
        if new_index == old_index:
            return
        self.state['history_mode'] = new_index
        self._push_option(
            lambda index=new_index: self._restore_mode(index),
            lambda index=old_index: self._restore_mode(index))

    def _restore_layer(self, text):
        self.state['applying_history'] = True
        try:
            self.state['history_layer'] = text
            self.layer_edit.blockSignals(True)
            self.layer_edit.setText(text)
            self.layer_edit.blockSignals(False)
        finally:
            self.state['applying_history'] = False

    def _commit_layer(self):
        if self.state.get('applying_history'):
            return
        text = self.layer_edit.text()
        # Same text still drops keystrokes from the field's own undo.
        self.layer_edit.blockSignals(True)
        self.layer_edit.setText(text)
        self.layer_edit.blockSignals(False)
        old = self.state['history_layer']
        if text == old:
            return
        self.state['history_layer'] = text
        self._push_option(
            lambda value=text: self._restore_layer(value),
            lambda value=old: self._restore_layer(value))

    def _restore_color(self, edit, color):
        self.state['applying_history'] = True
        try:
            edit.blockSignals(True)
            edit.setText(color)
            edit.setProperty('color', color)
            edit.blockSignals(False)
            _tint_edit(edit, color)
        finally:
            self.state['applying_history'] = False
        self.refresh_preview()

    def _push_color(self, edit, old, new):
        if old == new:
            return
        self._push_option(
            lambda edit=edit, value=new: self._restore_color(edit, value),
            lambda edit=edit, value=old: self._restore_color(edit, value))

    def _commit_color(self, edit):
        if self.state['busy'] and self.state.get('ask') != 'border':
            edit.blockSignals(True)
            edit.setText(edit.property('color'))
            edit.blockSignals(False)
            return
        color = _hex_color(edit.text())
        old = edit.property('color')
        if color is None or color == old:
            edit.blockSignals(True)
            edit.setText(old)
            edit.blockSignals(False)
            return
        edit.blockSignals(True)
        edit.setText(color)
        edit.setProperty('color', color)
        edit.blockSignals(False)
        _tint_edit(edit, color)
        self.refresh_preview()
        self._push_color(edit, old, color)

    def _is_shift_redo(self, event):
        if event.key() != self.QtCore.Qt.Key_Z:
            return False
        ctrl = self.QtCore.Qt.ControlModifier
        shift = self.QtCore.Qt.ShiftModifier
        alt = self.QtCore.Qt.AltModifier
        meta = self.QtCore.Qt.MetaModifier
        kept = event.modifiers() & (ctrl | shift | alt | meta)
        return kept == (ctrl | shift)

    def _install_option_keys(self):
        layer_edit = self.layer_edit
        QtCore = self.QtCore
        QtGui = self.QtGui
        QtWidgets = self.QtWidgets
        dialog = self.dialog
        option_stack = self.option_stack
        _is_shift_redo = self._is_shift_redo
        _text_edits = (layer_edit,)

        class _OptionKeyFilter(QtCore.QObject):
            def __init__(self, parent):
                QtCore.QObject.__init__(self, parent)

            def eventFilter(self, obj, event):
                if event.type() != QtCore.QEvent.KeyPress:
                    return False
                app = QtWidgets.QApplication.instance()
                if app is None:
                    return False
                # A color picker is its own window, so this stack does not see it.
                for picker in dialog.findChildren(
                        QtWidgets.QColorDialog, 'color-picker'):
                    if picker.isVisible():
                        return False
                if (app.activeWindow() is not dialog
                        and obj is not dialog
                        and not dialog.isAncestorOf(obj)):
                    return False
                undo = bool(event.matches(QtGui.QKeySequence.Undo))
                redo = (
                    bool(event.matches(QtGui.QKeySequence.Redo))
                    or _is_shift_redo(event))
                if not undo and not redo:
                    return False
                # A layer name still being typed undoes in the field.
                # A spin value is already committed, so the key is the history.
                focus = app.focusWidget()
                if focus in _text_edits and (
                        (undo and focus.isUndoAvailable())
                        or (redo and focus.isRedoAvailable())):
                    return False
                if undo:
                    option_stack.undo()
                else:
                    option_stack.redo()
                return True

        _key_filter = _OptionKeyFilter(dialog)
        QtWidgets.QApplication.instance().installEventFilter(_key_filter)

        def _drop_option_keys():
            app = QtWidgets.QApplication.instance()
            if app is not None:
                app.removeEventFilter(_key_filter)

        dialog.finished.connect(_drop_option_keys)
