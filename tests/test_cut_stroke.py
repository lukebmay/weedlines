# -*- coding: utf-8 -*-
"""Weed-cut stroke follows the window color. Default is #FF0000."""
from __future__ import division

import json
import os
import sys
from xml.etree import ElementTree as ET

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest

_EXT = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'extensions', 'inkscape'))
if _EXT not in sys.path:
    sys.path.insert(0, _EXT)

import weedlines_job as JOB  # noqa: E402
import weedlines_svg as SVG  # noqa: E402

_INK = 'http://www.inkscape.org/namespaces/inkscape'
_SVG = 'http://www.w3.org/2000/svg'
_LABEL = '{%s}label' % _INK
_DS = ['M 0,0 L 12,0', 'M 0,4 L 8,4']
_DOC = {'width': '20', 'height': '20', 'viewBox': '0 0 20 20'}
_RED = '#FF0000'
_PERSON_D = 'M 2,3 L 4,5'

_OPEN = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<svg xmlns="%s" xmlns:inkscape="%s" '
    'width="100" height="80" viewBox="0 0 100 80">\n'
    '  <g id="layer1" inkscape:groupmode="layer" inkscape:label="Layer 1">\n'
    '    <path id="person-path" d="%s"/>\n'
    '  </g>\n'
    '</svg>\n'
) % (_SVG, _INK, _PERSON_D)

_CORRECTION = (
    "<?xml version='1.0' encoding='utf-8'?>\n"
    '<svg xmlns="%s" xmlns:inkscape="%s" '
    'width="100" height="80" viewBox="0 0 100 80">\n'
    '  <g id="weedlines-correction-dangling" inkscape:label="Dangling ends">\n'
    '    <path id="weedlines-correction-dangling-shaft-0000" '
    'style="fill:none;stroke:#FF00FF;stroke-width:0.25" d="M 0,0 L 10,10"/>\n'
    '    <path id="weedlines-correction-dangling-head-0000" '
    'style="fill:#FF00FF;stroke:none" d="M 10,10 L 12,8 L 8,8 Z"/>\n'
    '  </g>\n'
    '</svg>\n'
) % (_SVG, _INK)

_RECT = [{
    'id': 'panel',
    'd': 'M 0,0 L 40,0 L 40,30 L 0,30 Z',
    'closed': [True],
    'fill': '#112233',
}]


def _stroke(color):
    return (
        'fill:none;stroke:%s;stroke-width:0.25;'
        'stroke-linecap:round;stroke-linejoin:round'
    ) % color


def _need_inkex():
    try:
        import inkex
        return inkex
    except ImportError:
        inkex_dir = '/usr/share/inkscape/extensions'
        if (os.path.isdir(os.path.join(inkex_dir, 'inkex'))
                and inkex_dir not in sys.path):
            sys.path.insert(0, inkex_dir)
        return pytest.importorskip('inkex')


def _qt():
    try:
        from weedlib.qt import QPainterPath, load_widgets
        QtCore, _QtGui, QtWidgets = load_widgets()
    except Exception as exc:
        pytest.skip('Qt cannot load: %s' % exc)
    return QtCore, QtWidgets, QPainterPath


def _cache(tmp_path, monkeypatch):
    monkeypatch.setattr(JOB, 'cache_dir', lambda: str(tmp_path))


def _write(color):
    kwargs = {}
    if color is not None:
        kwargs['weed_line_color'] = color
    JOB.write_result(
        'Weed lines',
        list(_DS),
        keep_d='M 0,0 L 8,0 L 8,8 Z',
        doc_attrs=dict(_DOC),
        **kwargs)
    with open(JOB.result_path(), 'r', encoding='utf-8') as fh:
        payload = json.load(fh)
    cuts = _file_cuts(SVG.result_svg_path())
    return payload, cuts


def _file_cuts(path):
    root = ET.parse(path).getroot()
    found = []
    for el in root.iter('{%s}path' % _SVG):
        if (el.get('id') or '').startswith('weed-cut-'):
            found.append(el)
    return found


def _assert_file_cuts(cuts, color):
    assert [el.get('id') for el in cuts] == ['weed-cut-0000', 'weed-cut-0001']
    assert [el.get('d') for el in cuts] == list(_DS)
    assert [el.get('style') for el in cuts] == [_stroke(color), _stroke(color)]


def _walk(el):
    found = [el]
    for child in el:
        found.extend(_walk(child))
    return found


def _open_root(inkex):
    return inkex.load_svg(_OPEN.encode('utf-8')).getroot()


def _import(root):
    import weedlines_import as IMP
    effect = IMP.WeedLinesImportEffect()
    effect.svg = root
    effect.effect()
    return root


def _assert_layer_cuts(root, color):
    person = root.getElementById('person-path')
    assert person.get('d') == _PERSON_D
    cuts = [
        el for el in _walk(root)
        if (el.get('id') or '').startswith('weed-cut-')
    ]
    assert [el.get('id') for el in cuts] == ['weed-cut-0000', 'weed-cut-0001']
    assert [el.get('d') for el in cuts] == list(_DS)
    assert [el.get('style') for el in cuts] == [_stroke(color), _stroke(color)]
    assert all(
        el.get(_LABEL) != 'Weedlines corrections' for el in _walk(root))


def test_omitted_color_strokes_red_and_is_not_stored(tmp_path, monkeypatch):
    _cache(tmp_path, monkeypatch)
    payload, cuts = _write(None)
    assert 'weed_line_color' not in payload
    assert payload['paths'] == list(_DS)
    _assert_file_cuts(cuts, _RED)


def test_explicit_red_is_stored_and_strokes_red(tmp_path, monkeypatch):
    _cache(tmp_path, monkeypatch)
    payload, cuts = _write(_RED)
    assert payload['weed_line_color'] == _RED
    _assert_file_cuts(cuts, _RED)


def test_window_color_is_the_stroke_and_the_record(tmp_path, monkeypatch):
    _cache(tmp_path, monkeypatch)
    payload, cuts = _write('#123456')
    assert payload['weed_line_color'] == '#123456'
    assert payload['keep_d'] == 'M 0,0 L 8,0 L 8,8 Z'
    _assert_file_cuts(cuts, '#123456')


def test_inline_writer_uses_the_given_color():
    inkex = _need_inkex()
    from inkex import PathElement
    import weedlines
    root = _open_root(inkex)
    weedlines._add_weed_layer_from_d(
        root, inkex, PathElement, list(_DS), 'Weed lines', '#112233')
    _assert_layer_cuts(root, '#112233')


def test_inline_writer_defaults_when_color_is_omitted():
    inkex = _need_inkex()
    from inkex import PathElement
    import weedlines
    root = _open_root(inkex)
    weedlines._add_weed_layer_from_d(
        root, inkex, PathElement, list(_DS), 'Weed lines')
    _assert_layer_cuts(root, _RED)


def test_add_weed_layer_passes_the_color(monkeypatch):
    inkex = _need_inkex()
    from inkex import PathElement
    import weedlib.svg_paths as svg_paths
    import weedlines
    monkeypatch.setattr(
        svg_paths, 'weed_path_to_open_d_list', lambda _path: list(_DS))
    root = _open_root(inkex)
    weedlines._add_weed_layer(
        root, inkex, PathElement, object(), 'Weed lines', '#445566')
    _assert_layer_cuts(root, '#445566')


def test_json_only_import_uses_the_recorded_color(tmp_path, monkeypatch):
    _need_inkex()
    _cache(tmp_path, monkeypatch)
    path = os.path.join(str(tmp_path), 'last_result.json')
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump({
            'version': 2,
            'layer_name': 'Weed lines',
            'paths': list(_DS),
            'weed_line_color': '#ABCDEF',
        }, fh)
    root = _import(_open_root(_need_inkex()))
    _assert_layer_cuts(root, '#ABCDEF')


def test_json_only_import_defaults_when_color_is_absent(tmp_path, monkeypatch):
    inkex = _need_inkex()
    _cache(tmp_path, monkeypatch)
    path = os.path.join(str(tmp_path), 'last_result.json')
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump({
            'version': 2,
            'layer_name': 'Weed lines',
            'paths': list(_DS),
        }, fh)
    root = _import(_open_root(inkex))
    _assert_layer_cuts(root, _RED)


def test_result_svg_import_keeps_the_file_style(tmp_path, monkeypatch):
    inkex = _need_inkex()
    _cache(tmp_path, monkeypatch)
    _write('#111111')
    svg_path = SVG.result_svg_path()
    with open(svg_path, 'r', encoding='utf-8') as fh:
        text = fh.read()
    text = text.replace('stroke:#111111', 'stroke:#222222')
    with open(svg_path, 'w', encoding='utf-8') as fh:
        fh.write(text)
    root = _import(_open_root(inkex))
    _assert_layer_cuts(root, '#222222')
    assert root.getElementById('weedlines-design') is not None
    assert root.getElementById('weedlines-keep') is not None


def test_correction_file_imports_as_arrow_groups_only(tmp_path, monkeypatch):
    inkex = _need_inkex()
    _cache(tmp_path, monkeypatch)
    svg_path = os.path.join(str(tmp_path), 'last_result.svg')
    with open(svg_path, 'w', encoding='utf-8') as fh:
        fh.write(_CORRECTION)
    with open(JOB.result_path(), 'w', encoding='utf-8') as fh:
        json.dump({
            'version': 2,
            'result': 'correction',
            'weed_line_color': '#123456',
        }, fh)
    root = _import(_open_root(inkex))
    person = root.getElementById('person-path')
    assert person.get('d') == _PERSON_D
    assert root.getElementById('weed-cut-0000') is None
    assert root.getElementById('weedlines-design') is None
    layers = [
        el for el in root if el.get(_LABEL) == 'Weedlines corrections'
    ]
    assert len(layers) == 1
    by_id = {el.get('id'): el for el in _walk(layers[0])}
    assert by_id['weedlines-correction-dangling-shaft-0000'].get('style') == (
        'fill:none;stroke:#FF00FF;stroke-width:0.25')
    assert by_id['weedlines-correction-dangling-head-0000'].get('style') == (
        'fill:#FF00FF;stroke:none')
    assert by_id['weedlines-correction-dangling-shaft-0000'].get('d') == (
        'M 0,0 L 10,10')


def _run_dialog(records, drive):
    from weedlines_dialog import run_weedlines_dialog
    QtCore, QtWidgets, _path = _qt()

    def ready(dialog):
        timer = QtCore.QTimer(dialog)
        timer.setSingleShot(True)
        timer.timeout.connect(dialog.reject)
        timer.start(20000)
        drive(dialog, QtCore, QtWidgets)

    return run_weedlines_dialog(records, ready=ready, quit_app=False)


def _color_edit(dialog, QtWidgets):
    edit = dialog.findChild(QtWidgets.QLineEdit, 'weed-line-color')
    assert edit is not None
    return edit


def test_closed_window_returns_no_color():
    def drive(dialog, _QtCore, QtWidgets):
        edit = _color_edit(dialog, QtWidgets)
        assert edit.text() == _RED
        assert edit.property('color') == _RED
        edit.setText('#00aa00')
        edit.editingFinished.emit()
        dialog.reject()

    assert _run_dialog(_RECT, drive) == (None, None, None)


def _apply(dialog, QtCore, QtWidgets, text):
    edit = _color_edit(dialog, QtWidgets)
    if text is not None:
        edit.setText(text)
        edit.editingFinished.emit()
    start = dialog.findChild(QtWidgets.QPushButton, 'start')
    apply_btn = dialog.findChild(QtWidgets.QPushButton, 'apply')
    assert start is not None and start.isEnabled()
    assert apply_btn is not None
    start.click()
    ticks = {'n': 0}

    def poll():
        ticks['n'] += 1
        if apply_btn.isEnabled():
            apply_btn.click()
            return
        if ticks['n'] > 40:
            dialog.reject()
            return
        QtCore.QTimer.singleShot(50, poll)

    QtCore.QTimer.singleShot(50, poll)


def test_untouched_apply_returns_the_initial_color(monkeypatch):
    import weedlib
    _QtCore, _QtWidgets, QPainterPath = _qt()

    def fake(*_args, **_kwargs):
        path = QPainterPath()
        path.moveTo(0, 0)
        path.lineTo(12, 0)
        return path

    monkeypatch.setattr(weedlib, 'generate_weeds', fake)
    weed, layer, color = _run_dialog(
        _RECT, lambda dialog, QtCore, QtWidgets: _apply(
            dialog, QtCore, QtWidgets, None))
    assert color == _RED
    assert layer == 'Weed lines'
    assert weed is not None and not weed.isEmpty()


def test_apply_returns_the_changed_weed_line_color(monkeypatch):
    import weedlib
    _QtCore, _QtWidgets, QPainterPath = _qt()

    def fake(*_args, **_kwargs):
        path = QPainterPath()
        path.moveTo(0, 0)
        path.lineTo(12, 0)
        return path

    monkeypatch.setattr(weedlib, 'generate_weeds', fake)
    weed, _layer, color = _run_dialog(
        _RECT, lambda dialog, QtCore, QtWidgets: _apply(
            dialog, QtCore, QtWidgets, '#00aa00'))
    assert color == '#00AA00'
    assert weed is not None and not weed.isEmpty()


def test_host_writes_the_window_color(tmp_path, monkeypatch):
    _QtCore, QtWidgets, QPainterPath = _qt()
    import weedlines_dialog
    import weedlines_host
    _cache(tmp_path, monkeypatch)
    path = QPainterPath()
    path.moveTo(0, 0)
    path.lineTo(8, 0)

    def fake(*_args, **_kwargs):
        return path, 'Weed lines', '#ABCDEF'

    monkeypatch.setattr(weedlines_dialog, 'run_weedlines_dialog', fake)
    shown = {}

    def information(*args, **_kwargs):
        shown['args'] = args

    monkeypatch.setattr(QtWidgets.QMessageBox, 'information', information)
    job = {
        'keep_d': 'M 0,0 L 10,0 L 10,10 Z',
        'records': [],
        'defaults': {'mode': 'frame'},
        'doc_attrs': dict(_DOC),
    }
    job_path = os.path.join(str(tmp_path), 'job.json')
    with open(job_path, 'w', encoding='utf-8') as fh:
        json.dump(job, fh)
    assert weedlines_host.main([job_path]) == 0
    with open(JOB.result_path(), 'r', encoding='utf-8') as fh:
        payload = json.load(fh)
    assert payload['weed_line_color'] == '#ABCDEF'
    cuts = _file_cuts(SVG.result_svg_path())
    assert len(cuts) == 1
    assert cuts[0].get('id') == 'weed-cut-0000'
    assert cuts[0].get('style') == _stroke('#ABCDEF')
    assert 'fill:none' in cuts[0].get('style')
    assert 'stroke-width:0.25' in cuts[0].get('style')
    text = shown['args'][2]
    assert text.startswith('Saved design + weed cuts.')
    assert 'Extensions → Weedlines → Import last result' in text
    assert '#ABCDEF' not in text
