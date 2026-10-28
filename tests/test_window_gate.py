# -*- coding: utf-8 -*-
"""Window gate: figure check before Start, subject region as keep."""
from __future__ import division

import importlib.util
import json
import os
import sys
import types
from collections import deque

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest

try:
    from weedlib.qt import QPainterPath, load_widgets
    QtCore, _QtGui, QtWidgets = load_widgets()
except Exception as exc:
    pytest.skip('Qt cannot load: %s' % exc, allow_module_level=True)

try:
    import pyclipper  # noqa: F401
    _HAS_CLIPPER = True
except ImportError:
    _HAS_CLIPPER = False

requires_clipper = pytest.mark.skipif(
    not _HAS_CLIPPER, reason='pyclipper required for island-hop')

_EXT_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'extensions', 'inkscape'))
if _EXT_DIR not in sys.path:
    sys.path.insert(0, _EXT_DIR)

from weedlines_dialog import run_weedlines_dialog  # noqa: E402

_APP = None

_RECT = 'M 0,0 L 50,0 L 50,50 L 0,50 Z'
_RECT_RECORDS = [{
    'id': 'panel',
    'd': _RECT,
    'closed': [True],
    'fill': '#112233',
}]
_OPEN_RECORDS = [{
    'id': 'gap',
    'd': 'M 5,6 L 15,6 L 15,20',
    'closed': [False],
    'fill': 'none',
}]
_OUTER = 'M 0,0 L 40,0 L 40,30 L 0,30 Z'
_INNER = 'M 10,10 L 20,10 L 20,20 L 10,20 Z'
_NESTED_RECORDS = [
    {'id': 'frame', 'd': _OUTER, 'closed': [True], 'fill': 'none'},
    {'id': 'letter', 'd': _INNER, 'closed': [True], 'fill': '#ff0000'},
]


class _QuietCapture(object):
    def __init__(self):
        self.lines = deque()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _Matrix(object):
    def __init__(self, matrix):
        self.matrix = matrix


class _Node(object):
    def __init__(self, tag, attrib=None, children=None):
        self.tag = tag
        self.attrib = dict(attrib or {})
        self.children = []
        self.parent = None
        for child in children or ():
            self.append(child)

    def append(self, child):
        child.parent = self
        self.children.append(child)

    def get(self, key, default=None):
        return self.attrib.get(key, default)

    def __iter__(self):
        return iter(self.children)

    def getparent(self):
        return self.parent

    def composed_transform(self):
        return _Matrix(((1, 0, 0), (0, 1, 0)))


class _Sel(object):
    def values(self):
        return []

    def __bool__(self):
        return False


class _Opts(object):
    mode = 'frame'
    padding = 4.0
    spacing = 25.0
    collar = 4.0
    layer_name = 'Weed lines'


def _fill_rule(path):
    rule = path.fillRule()
    return getattr(rule, 'value', rule)


def _same_path(got, expected):
    assert _fill_rule(got) == _fill_rule(expected)
    assert got.elementCount() == expected.elementCount()
    for index in range(expected.elementCount()):
        left = got.elementAt(index)
        right = expected.elementAt(index)
        assert left.type == right.type
        assert left.x == pytest.approx(right.x)
        assert left.y == pytest.approx(right.y)


def _button(dialog, name):
    widget = dialog.findChild(QtWidgets.QPushButton, name)
    assert widget is not None, name
    return widget


def _mode_box(dialog):
    widget = dialog.findChild(QtWidgets.QComboBox, 'mode')
    assert widget is not None
    return widget


def _set_mode(dialog, mode):
    box = _mode_box(dialog)
    for index in range(box.count()):
        if box.itemData(index) == mode:
            box.setCurrentIndex(index)
            return box
    raise AssertionError('missing mode %s' % mode)


def _run(records, drive, **kwargs):
    global _APP
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    _APP = app

    def ready(dialog):
        timer = QtCore.QTimer(dialog)
        timer.setSingleShot(True)
        timer.timeout.connect(dialog.reject)
        timer.start(20000)
        drive(dialog)

    return run_weedlines_dialog(records, ready=ready, quit_app=False, **kwargs)


def _finish_start(dialog, mode, padding=None, spacing=None):
    _set_mode(dialog, mode)
    if padding is not None:
        pad = dialog.findChild(QtWidgets.QDoubleSpinBox, 'padding')
        assert pad is not None
        pad.setValue(padding)
    if spacing is not None:
        space = dialog.findChild(QtWidgets.QDoubleSpinBox, 'spacing')
        assert space is not None
        space.setValue(spacing)
    start = _button(dialog, 'start')
    apply_btn = _button(dialog, 'apply')
    assert start.isEnabled() is True
    done = {'error': None}
    start.click()
    log = dialog.findChild(QtWidgets.QPlainTextEdit)
    ticks = {'n': 0}

    def poll():
        ticks['n'] += 1
        if apply_btn.isEnabled():
            apply_btn.click()
            return
        running = (not start.isVisible()) or (not start.isEnabled())
        if not running and ticks['n'] > 5:
            text = log.toPlainText() if log is not None else ''
            done['error'] = 'no cuts\n' + text
            dialog.reject()
            return
        if ticks['n'] > 300:
            text = log.toPlainText() if log is not None else ''
            done['error'] = 'timeout\n' + text
            dialog.reject()
            return
        QtCore.QTimer.singleShot(50, poll)

    QtCore.QTimer.singleShot(50, poll)
    return done


def _design_svg():
    paths = [
        _Node('path', {
            'id': 'a',
            'd': 'M 0 0 L 10 0 L 10 10 L 0 10 Z',
            'style': 'fill:#ff0000',
        }),
        _Node('path', {
            'id': 'b',
            'd': 'M 30 0 L 40 0 L 40 10 L 30 10 Z',
            'style': 'fill:none',
        }),
    ]
    svg = _Node('svg', {
        'id': 'doc',
        'width': '100',
        'height': '50',
        'viewBox': '0 0 100 50',
    }, paths)
    svg.selection = _Sel()
    return svg


def _load_effect():
    path = os.path.join(_EXT_DIR, 'weedlines.py')
    spec = importlib.util.spec_from_file_location('weedlines_gate_ext', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run_effect(mod, svg, monkeypatch):
    inkex = types.ModuleType('inkex')
    inkex.AbortExtension = type('AbortExtension', (Exception,), {})
    inkex.PathElement = object
    inkex.addNS = lambda name, ns: '{%s}%s' % (ns, name)
    monkeypatch.setitem(sys.modules, 'inkex', inkex)
    import stdio_capture
    monkeypatch.setattr(stdio_capture, 'NativeStdioCapture', _QuietCapture)
    effect = mod.WeedLinesEffect()
    effect.svg = svg
    effect.options = _Opts()
    effect.effect()


def test_defect_disables_start(monkeypatch):
    import weedlib
    seen = []

    def fake(keep_path, **kwargs):
        seen.append(keep_path)
        return QPainterPath()

    monkeypatch.setattr(weedlib, 'generate_weeds', fake)

    def drive(dialog):
        start = _button(dialog, 'start')
        assert start.isEnabled() is False
        box = _mode_box(dialog)
        box.setCurrentIndex(1)
        box.setCurrentIndex(2)
        start.click()
        apply_btn = _button(dialog, 'apply')
        assert apply_btn.isEnabled() is False
        apply_btn.click()
        dialog.reject()

    _run(_OPEN_RECORDS, drive)
    assert seen == []


def test_clear_design_enables_start_for_frame_grid_and_island_hop():
    def drive(dialog):
        box = _mode_box(dialog)
        labels = [box.itemText(index) for index in range(box.count())]
        data = [box.itemData(index) for index in range(box.count())]
        assert data == ['frame', 'grid', 'island-hop']
        for label in labels:
            lowered = label.lower()
            assert 'surround' not in lowered
            assert 'conquer' not in lowered
        start = _button(dialog, 'start')
        for index in range(box.count()):
            box.setCurrentIndex(index)
            assert start.isEnabled() is True
        assert dialog.doc_width == '210mm'
        assert dialog.doc_height == '297mm'
        assert dialog.doc_viewbox == '0 0 210 297'
        dialog.reject()

    _run(
        _RECT_RECORDS,
        drive,
        width='210mm',
        height='297mm',
        view_box='0 0 210 297',
    )


def test_start_passes_the_subject_region(monkeypatch):
    import weedlib
    from weedlib.figures import classify_figures, subject_weed_regions

    expected = subject_weed_regions(
        classify_figures(_NESTED_RECORDS).figures, swap=False).subject
    seen = []

    def fake(keep_path, **kwargs):
        seen.append((kwargs.get('mode'), keep_path))
        out = QPainterPath()
        out.addRect(0, 0, 1, 1)
        return out

    monkeypatch.setattr(weedlib, 'generate_weeds', fake)
    for mode in ('frame', 'grid', 'island-hop'):
        holder = {}

        def drive(dialog, mode=mode):
            holder['done'] = _finish_start(dialog, mode)

        _run(_NESTED_RECORDS, drive)
        assert holder['done']['error'] is None, holder['done']['error']
        assert seen[-1][0] == mode
        _same_path(seen[-1][1], expected)


@pytest.mark.parametrize('mode', [
    'frame',
    'grid',
    pytest.param('island-hop', marks=requires_clipper),
])
def test_clear_filled_rectangle_cuts(mode):
    holder = {}

    def drive(dialog):
        holder['done'] = _finish_start(
            dialog, mode, padding=2.0, spacing=20.0)

    weed, _layer, _color = _run(_RECT_RECORDS, drive)
    assert holder['done']['error'] is None, holder['done']['error']
    assert weed is not None and not weed.isEmpty()


def test_host_passes_records_not_the_union(tmp_path, monkeypatch):
    import weedlines_dialog
    import weedlines_host
    records = [
        {
            'id': 'a',
            'd': 'M 0,0 L 10,0 L 10,10 L 0,10 Z',
            'closed': [True],
            'fill': '#ff0000',
        },
        {
            'id': 'b',
            'd': 'M 20,0 L 30,0 L 30,10 L 20,10 Z',
            'closed': [True],
            'fill': 'none',
        },
    ]
    calls = []

    def fake(records, defaults=None, platform_lines=None, quit_app=True,
             width=None, height=None, view_box=None, ready=None):
        calls.append({
            'records': records,
            'quit_app': quit_app,
            'width': width,
            'height': height,
            'view_box': view_box,
        })
        return None, None, None

    monkeypatch.setattr(weedlines_dialog, 'run_weedlines_dialog', fake)
    job = {
        'version': 2,
        'keep_d': 'M 0,0 L 100,0 L 100,100 L 0,100 Z',
        'records': records,
        'defaults': {'mode': 'frame'},
        'doc_attrs': {
            'width': '210mm',
            'height': '297mm',
            'viewBox': '0 0 210 297',
        },
    }
    path = tmp_path / 'job.json'
    path.write_text(json.dumps(job), encoding='utf-8')
    assert weedlines_host.main([str(path)]) == 0
    assert calls == [{
        'records': records,
        'quit_app': False,
        'width': '210mm',
        'height': '297mm',
        'view_box': '0 0 210 297',
    }]


def _refuse_spawn(path):
    raise AssertionError('spawned %s' % path)


def test_inline_path_passes_records_not_the_union(monkeypatch):
    from weedlib.qt import QTransform
    import weedlines_dialog
    import weedlines_job
    monkeypatch.setenv('WEEDLINES_INLINE', '1')
    monkeypatch.setattr(weedlines_job, 'spawn_host', _refuse_spawn)
    calls = []

    def fake(records, defaults=None, platform_lines=None, quit_app=True,
             width=None, height=None, view_box=None, ready=None):
        calls.append({
            'records': records,
            'quit_app': quit_app,
            'width': width,
            'height': height,
            'view_box': view_box,
            'platform_lines': platform_lines,
        })
        return None, None, None

    monkeypatch.setattr(weedlines_dialog, 'run_weedlines_dialog', fake)
    mod = _load_effect()
    svg = _design_svg()
    expected = mod._path_records([svg], None, QTransform)
    _run_effect(mod, svg, monkeypatch)
    assert len(calls) == 1
    got = calls[0]
    assert got['records'] == expected
    assert [record['id'] for record in got['records']] == ['a', 'b']
    assert got['quit_app'] is True
    assert got['width'] == '100'
    assert got['height'] == '50'
    assert got['view_box'] == '0 0 100 50'
    assert got['platform_lines'] is not None


def test_detached_spawn_keeps_per_path_records(tmp_path, monkeypatch):
    import weedlines_dialog
    import weedlines_job
    monkeypatch.delenv('WEEDLINES_INLINE', raising=False)
    monkeypatch.setattr(weedlines_job, 'cache_dir', lambda: str(tmp_path))
    spawned = []

    def fake_spawn(path):
        with open(path, 'r', encoding='utf-8') as handle:
            spawned.append(json.load(handle))

    monkeypatch.setattr(weedlines_job, 'spawn_host', fake_spawn)
    calls = []
    monkeypatch.setattr(
        weedlines_dialog, 'run_weedlines_dialog',
        lambda *args, **kwargs: calls.append((args, kwargs)) or (None, None, None))
    _run_effect(_load_effect(), _design_svg(), monkeypatch)
    assert calls == []
    assert len(spawned) == 1
    assert [record['id'] for record in spawned[0]['records']] == ['a', 'b']
    assert spawned[0]['doc_attrs']['width'] == '100'
    assert spawned[0]['doc_attrs']['height'] == '50'
    assert spawned[0]['doc_attrs']['viewBox'] == '0 0 100 50'
    assert isinstance(spawned[0]['keep_d'], str) and spawned[0]['keep_d']
