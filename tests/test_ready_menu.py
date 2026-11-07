# -*- coding: utf-8 -*-
"""Make ready returns at once. Reimport places that file."""
from __future__ import division

import json
import os
import sys

import pytest

_EXT = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'extensions', 'inkscape'))
if _EXT not in sys.path:
    sys.path.insert(0, _EXT)

_INK = 'http://www.inkscape.org/namespaces/inkscape'
_LABEL = '{%s}label' % _INK
_MODE = '{%s}groupmode' % _INK
_PERSON_D = 'M 2,3 L 4,5'
_OPEN_DOC = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="%s" '
    'width="100" height="80" viewBox="0 0 100 80">\n'
    '  <g id="layer1" inkscape:groupmode="layer" inkscape:label="Layer 1">\n'
    '    <path id="person-path" d="%s"/>\n'
    '  </g>\n'
    '</svg>\n'
) % (_INK, _PERSON_D)
_DANGLING = [{
    'id': 'gap',
    'd': 'M 5,6 L 15,6 L 15,20',
    'closed': [True],
    'fill': 'none',
}]
_SQUARE = [{
    'id': 'square',
    'd': 'M 0,0 L 10,0 L 10,10 L 0,10 Z',
    'closed': [True],
    'fill': 'none',
}]
_MENU = (
    '1 Auto generate weedlines',
    '2 Make ready to cut',
    '4 Reimport last ready cut',
    '3 Reimport last weedlines',
)
_SORTED = (
    '1 Auto generate weedlines',
    '2 Make ready to cut',
    '3 Reimport last weedlines',
    '4 Reimport last ready cut',
)
_INX = (
    'weedlines.inx',
    'weedlines_ready.inx',
    'weedlines_reimport_ready.inx',
    'weedlines_import.inx',
)


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


class _Options(object):
    def __init__(self, kind):
        self.reimport = kind


def _cache(monkeypatch, tmp_path):
    import weedlines_job as JOB
    monkeypatch.setattr(JOB, 'cache_dir', lambda: str(tmp_path))
    return JOB


def _inx_name(filename):
    path = os.path.join(_EXT, filename)
    text = open(path, encoding='utf-8').read()
    start = text.index('<name>') + len('<name>')
    return text[start:text.index('</name>')].strip()


def test_menu_names_match_the_four_entries():
    found = [_inx_name(name) for name in _INX]
    assert found == list(_MENU)
    assert sorted(found) == list(_SORTED)
    assert all('…' not in name and '...' not in name for name in found)
    for filename in _INX:
        text = open(os.path.join(_EXT, filename), encoding='utf-8').read()
        assert '<separator' not in text
        assert 'divider' not in text.lower()
    import importlib.util
    path = os.path.join(
        os.path.dirname(__file__), '..', 'src', 'weedlines', 'install_ext.py')
    spec = importlib.util.spec_from_file_location('install_ext_under_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert 'weedlines_ready.py' in module.WEED_FILES
    assert 'weedlines_ready.inx' in module.WEED_FILES
    assert 'weedlines_reimport_ready.inx' in module.WEED_FILES


def _open_document():
    try:
        import inkex
    except ImportError:
        inkex_dir = '/usr/share/inkscape/extensions'
        if os.path.isdir(os.path.join(inkex_dir, 'inkex')) and inkex_dir not in sys.path:
            sys.path.insert(0, inkex_dir)
        inkex = pytest.importorskip('inkex')
    return inkex.load_svg(_OPEN_DOC.encode('utf-8')).getroot()


def _import(root, kind):
    import weedlines_import as IMP
    effect = IMP.WeedLinesImportEffect()
    effect.options = _Options(kind)
    effect.svg = root
    effect.effect()
    return root


def _local(el):
    tag = el.tag
    if not isinstance(tag, str):
        return ''
    return tag.rsplit('}', 1)[-1]


def test_defect_writes_ready_file_and_clear_check_removes_it(tmp_path, monkeypatch):
    pytest.importorskip('PyQt5', reason='Qt binding required')
    import weedlines_ready as ready
    import weedlines_svg as SVG
    JOB = _cache(monkeypatch, tmp_path)
    calls = []
    real_write = SVG.write_correction_svg

    def wrapped(arrows, doc_attrs=None, path=None, labels=None):
        calls.append(path)
        return real_write(
            arrows, doc_attrs=doc_attrs, path=path, labels=labels)

    monkeypatch.setattr(SVG, 'write_correction_svg', wrapped)
    written = ready.apply_ready(_DANGLING, {
        'width': '20', 'height': '30', 'viewBox': '0 0 20 30',
    })
    assert written == JOB.ready_svg_file()
    assert calls == [written]
    assert os.path.isfile(written)
    text = open(written, encoding='utf-8').read()
    assert 'Dangling ends' in text
    assert '#FF00FF' in text
    assert 'Figure overlaps' not in text
    assert 'Self-overlaps' not in text
    assert 'weedlines-design' not in text
    assert os.path.basename(written) != 'last_result.svg'

    calls[:] = []
    stale = JOB.ready_svg_file()
    assert os.path.isfile(stale)
    assert ready.apply_ready(_SQUARE, {'width': '10', 'height': '10'}) is None
    assert calls == []
    assert not os.path.isfile(stale)
    assert not os.path.isfile(JOB.result_svg_file())


def test_effect_returns_without_waiting_or_changing_the_document(
        tmp_path, monkeypatch):
    pytest.importorskip('PyQt5', reason='Qt binding required')
    import weedlib.ready as ready_lib
    import weedlines_ready as ready
    import weedlines_svg as SVG
    JOB = _cache(monkeypatch, tmp_path)

    def fail_check(records):
        raise AssertionError('effect ran the check')

    def fail_write(*_args, **_kwargs):
        raise AssertionError('effect wrote the ready file')

    monkeypatch.setattr(ready_lib, 'build_correction_marks', fail_check)
    monkeypatch.setattr(SVG, 'write_correction_svg', fail_write)
    spawned = {}

    def fake_spawn(path):
        spawned['path'] = path
        return None

    monkeypatch.setattr(ready, 'spawn_ready', fake_spawn)
    svg = _Node('svg', {
        'id': 'doc',
        'width': '100',
        'height': '80',
        'viewBox': '0 0 100 80',
    }, [
        _Node('path', {'id': 'gap', 'd': 'M 5,6 L 15,6 L 15,20'}),
    ])
    before = [child.get('id') for child in svg]
    effect = ready.ReadyEffect()
    effect.svg = svg
    assert effect.effect() is False
    import inkex
    class _Plugin(ready.ReadyEffect, inkex.EffectExtension):
        pass
    assert _Plugin().has_changed(True) is False
    assert [child.get('id') for child in svg] == before
    assert svg.get('id') == 'doc'
    assert not os.path.isfile(JOB.ready_svg_file())
    with open(spawned['path'], encoding='utf-8') as fh:
        payload = json.load(fh)
    assert payload['records']
    assert payload['records'][0]['id'] == 'gap'


def test_spawn_ready_detaches_and_does_not_wait(tmp_path, monkeypatch):
    import weedlines_job as JOB
    import weedlines_ready as ready
    monkeypatch.setattr(JOB, 'cache_dir', lambda: str(tmp_path))

    class _Proc(object):
        def __init__(self):
            self.returncode = None

        def wait(self, *_args, **_kwargs):
            raise AssertionError('waited on the ready child')

        def communicate(self, *_args, **_kwargs):
            raise AssertionError('waited on the ready child')

    seen = {}

    def popen(cmd, **kwargs):
        seen['cmd'] = cmd
        seen['kwargs'] = kwargs
        return _Proc()

    monkeypatch.setattr(JOB.subprocess, 'Popen', popen)
    ready.spawn_ready(os.path.join(str(tmp_path), 'ready-job.json'))
    assert seen['kwargs'].get('start_new_session') is True
    assert '--ready-job' in seen['cmd']
    assert seen['cmd'][-1].endswith('ready-job.json')


def test_reimport_ready_places_the_layer_and_weedlines_refuses_it(
        tmp_path, monkeypatch):
    pytest.importorskip('PyQt5', reason='Qt binding required')
    _open_document()
    import inkex
    import weedlines_ready as ready
    JOB = _cache(monkeypatch, tmp_path)
    ready.apply_ready(_DANGLING, {
        'width': '100', 'height': '80', 'viewBox': '0 0 100 80',
    })
    ready_path = JOB.ready_svg_file()
    with open(ready_path, encoding='utf-8') as fh:
        ready_text = fh.read()
    with open(JOB.result_svg_file(), 'w', encoding='utf-8') as fh:
        fh.write(ready_text)

    root = _open_document()
    try:
        from weedlib.qt import load_widgets
        widgets = load_widgets()[2]

        def fail_box(*_args, **_kwargs):
            raise AssertionError('message box')

        monkeypatch.setattr(widgets.QMessageBox, 'information', fail_box)
        monkeypatch.setattr(widgets.QMessageBox, 'warning', fail_box)
        monkeypatch.setattr(widgets.QMessageBox, 'critical', fail_box)
    except Exception:
        pass
    _import(root, 'ready')
    person = root.getElementById('person-path')
    assert person.get('d') == _PERSON_D
    assert person.getparent().get('id') == 'layer1'
    layers = [el for el in root if el.get(_LABEL) == 'Weedlines corrections']
    assert len(layers) == 1
    layer = layers[0]
    assert list(root)[-1] is layer
    assert layer.get(_MODE) == 'layer'
    assert [el.get(_LABEL) for el in layer] == ['Dangling ends']
    group = list(layer)[0]
    texts = [el for el in group if _local(el) == 'text']
    assert len(texts) == 1
    assert texts[0].text == 'Dangling ends'
    assert '#FF00FF' in (texts[0].get('style') or '')
    assert root.getElementById('weedlines-design') is None

    refused = _open_document()
    with pytest.raises(inkex.AbortExtension):
        _import(refused, 'weedlines')
    assert refused.getElementById('person-path').get('d') == _PERSON_D
    assert [el.get(_LABEL) for el in refused] == ['Layer 1']


def test_reimport_weedlines_still_places_cuts(tmp_path, monkeypatch):
    import weedlines_job as JOB
    _cache(monkeypatch, tmp_path)
    JOB.write_result(
        'Weed lines',
        ['M 0,0 L 12,0'],
        keep_d='M 0,0 L 8,0 L 8,8 Z',
        doc_attrs={'width': '20', 'height': '20', 'viewBox': '0 0 20 20'},
    )
    root = _import(_open_document(), 'weedlines')
    assert root.getElementById('person-path').get('d') == _PERSON_D
    cuts = root.getElementById('weedlines-cuts')
    assert cuts is not None
    cut = root.getElementById('weed-cut-0000')
    assert cut is not None and cut.get('d') == 'M 0,0 L 12,0'
    assert all(el.get(_LABEL) != 'Weedlines corrections' for el in root)
