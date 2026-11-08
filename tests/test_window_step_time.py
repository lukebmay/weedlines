# -*- coding: utf-8 -*-
"""Window step clock: working time on the step row. No Inkscape."""
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

_CLEAR = [{
    'id': 'panel',
    'd': 'M 0,0 L 50,0 L 50,50 L 0,50 Z',
    'closed': [True],
    'fill': '#112233',
}]
_TIME_NAMES = ('step-cut-time', 'step-surround-time', 'step-conquer-time')


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


def _time_label(dialog, name):
    label = dialog.findChild(QtWidgets.QLabel, name)
    assert label is not None, name
    return label


def _times(dialog):
    return tuple(_time_label(dialog, name).text() for name in _TIME_NAMES)


def _log(dialog):
    view = dialog.findChild(QtWidgets.QPlainTextEdit)
    assert view is not None
    return view.toPlainText()


def _scene_count(dialog):
    view = dialog.findChild(QtWidgets.QGraphicsView, 'preview')
    assert view is not None
    return len(view.scene().items())


def _pump_until(predicate, timeout=20):
    import time
    app = QtWidgets.QApplication.instance()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents(QtCore.QEventLoop.AllEvents, 30)
        if predicate():
            return
    raise AssertionError('timed out')


def _pump(dialog, rounds=6):
    app = QtWidgets.QApplication.instance()
    for _ in range(rounds):
        app.processEvents(QtCore.QEventLoop.AllEvents, 50)


def _wait_idle(dialog, timeout=20):
    import time
    app = QtWidgets.QApplication.instance()
    deadline = time.monotonic() + timeout
    quiet = 0
    while time.monotonic() < deadline:
        app.processEvents(QtCore.QEventLoop.AllEvents, 30)
        text = _status(dialog).text()
        busy = text.startswith('working') or text.startswith('paused')
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
    raise AssertionError('step did not finish')


def _hold_solver(monkeypatch):
    import weedlines_dialog as dialog_mod
    real_spawn = dialog_mod._spawn_ask

    def wrapped(request, hold, pausing, cancelled):
        return real_spawn(request, hold, pausing, cancelled)

    monkeypatch.setattr(dialog_mod, '_spawn_ask', wrapped)
    old = dialog_mod._ASK_HOLD
    dialog_mod._ASK_HOLD = 8000000
    return dialog_mod, old


def test_step_time_follows_the_run(monkeypatch):
    dialog_mod, old = _hold_solver(monkeypatch)

    def drive(dialog):
        try:
            assert _times(dialog) == ('', '', '')
            assert _button(dialog, 'conquer-start').isEnabled() is False
            _wait_idle(dialog)
            assert _times(dialog) == ('', '', '')
            assert _button(dialog, 'conquer-start').isEnabled() is False

            _set_mode(dialog, 'frame')
            assert _time_label(dialog, 'step-cut-time').text() == ''
            _button(dialog, 'start').click()
            _pump_until(
                lambda: _time_label(dialog, 'step-cut-time').text() not in ('', '0.0'))
            status = _status(dialog).text()
            assert status.startswith('working')
            shown = _time_label(dialog, 'step-cut-time').text()
            if ': ' in status:
                assert status.split(': ', 1)[1] not in shown
            assert ':' not in shown
            assert shown not in _log(dialog).splitlines()
            assert _time_label(dialog, 'step-surround-time').text() == ''
            assert _time_label(dialog, 'step-conquer-time').text() == ''

            _button(dialog, 'pause').click()
            _pump_until(lambda: _status(dialog).text().startswith('paused'))
            held = _time_label(dialog, 'step-cut-time').text()
            calls = list(dialog.worker_calls)
            scene = _scene_count(dialog)
            log_text = _log(dialog)
            _pump(dialog)
            assert _time_label(dialog, 'step-cut-time').text() == held
            assert _status(dialog).text().startswith('paused')
            assert dialog.worker_calls == calls
            assert _scene_count(dialog) == scene
            assert _log(dialog) == log_text
            assert _time_label(dialog, 'step-conquer-time').text() == ''

            _button(dialog, 'pause').click()
            _wait_idle(dialog)
            done = _time_label(dialog, 'step-cut-time').text()
            assert done != ''
            calls = list(dialog.worker_calls)
            scene = _scene_count(dialog)
            _pump(dialog)
            assert _time_label(dialog, 'step-cut-time').text() == done
            assert _status(dialog).text() == 'done'
            assert dialog.worker_calls == calls
            assert _scene_count(dialog) == scene
            assert dialog.worker_calls.count('solver') == 1
            assert dialog.worker_calls.count('surrounds') == 0

            borders = len(dialog.border_args)
            dialog.lengths['border'] = dialog.lengths['border'] + 1.0
            dialog.change_piece_length('border')
            _wait_idle(dialog)
            assert len(dialog.border_args) == borders + 1
            assert _time_label(dialog, 'step-cut-time').text() == done
            assert dialog.worker_calls.count('solver') == 1
            assert dialog.worker_calls.count('surrounds') == 0

            _button(dialog, 'start').click()
            restarted = _time_label(dialog, 'step-cut-time').text()
            assert restarted != ''
            assert float(restarted) < float(done)
            _pump_until(
                lambda: _time_label(dialog, 'step-cut-time').text() != restarted)
            assert _status(dialog).text().startswith('working')
            assert _time_label(dialog, 'step-conquer-time').text() == ''
            _wait_idle(dialog)
            assert _time_label(dialog, 'step-conquer-time').text() == ''

            _button(dialog, 'clear-all').click()
            _wait_idle(dialog)
            assert _times(dialog) == ('', '', '')
            assert _status(dialog).text() == 'ready'
            dialog.reject()
        finally:
            if dialog.isVisible():
                dialog.reject()

    try:
        _run(_CLEAR, drive)
    finally:
        dialog_mod._ASK_HOLD = old


def test_another_mode_keeps_its_step_time(monkeypatch):
    dialog_mod, old = _hold_solver(monkeypatch)

    def drive(dialog):
        try:
            _wait_idle(dialog)
            _set_mode(dialog, 'grid')
            _button(dialog, 'start').click()
            _pump_until(
                lambda: _time_label(dialog, 'step-cut-time').text() not in ('', '0.0'))
            _wait_idle(dialog)
            kept = _time_label(dialog, 'step-cut-time').text()
            assert kept not in ('', '0.0')
            assert _time_label(dialog, 'step-conquer-time').text() == ''

            _set_mode(dialog, 'frame')
            assert _time_label(dialog, 'step-cut-time').text() == ''
            _button(dialog, 'start').click()
            _pump_until(
                lambda: _time_label(dialog, 'step-cut-time').text() not in ('', '0.0'))
            _wait_idle(dialog)
            frame_done = _time_label(dialog, 'step-cut-time').text()
            _button(dialog, 'start').click()
            assert float(_time_label(dialog, 'step-cut-time').text()) < float(frame_done)
            _wait_idle(dialog)

            _set_mode(dialog, 'grid')
            assert _time_label(dialog, 'step-cut-time').text() == kept
            assert _time_label(dialog, 'step-surround-time').text() == ''
            assert _time_label(dialog, 'step-conquer-time').text() == ''
            dialog.reject()
        finally:
            if dialog.isVisible():
                dialog.reject()

    try:
        _run(_CLEAR, drive)
    finally:
        dialog_mod._ASK_HOLD = old
