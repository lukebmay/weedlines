# -*- coding: utf-8 -*-
"""Import places correction arrows on one layer. Weed lines stay."""
from __future__ import division

import os
import sys

import pytest

_EXT = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'extensions', 'inkscape'))
if _EXT not in sys.path:
    sys.path.insert(0, _EXT)

try:
    import inkex
except ImportError:
    # Inkscape ships inkex beside the app, not on the default module path.
    _inkex_dir = '/usr/share/inkscape/extensions'
    if os.path.isdir(os.path.join(_inkex_dir, 'inkex')) and _inkex_dir not in sys.path:
        sys.path.insert(0, _inkex_dir)
    inkex = pytest.importorskip('inkex')

import weedlines_import as IMP  # noqa: E402
import weedlines_job as JOB  # noqa: E402

_INK = 'http://www.inkscape.org/namespaces/inkscape'
_LABEL = '{%s}label' % _INK
_MODE = '{%s}groupmode' % _INK
_PERSON_D = 'M 2,3 L 4,5'

_OPEN = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="%s" '
    'width="100" height="80" viewBox="0 0 100 80">\n'
    '  <g id="layer1" inkscape:groupmode="layer" inkscape:label="Layer 1">\n'
    '    <path id="person-path" d="%s"/>\n'
    '  </g>\n'
    '</svg>\n'
) % (_INK, _PERSON_D)

_CORRECTION = (
    "<?xml version='1.0' encoding='utf-8'?>\n"
    '<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="%s" '
    'width="100" height="80" viewBox="0 0 100 80">\n'
    '  <g id="weedlines-correction-dangling" inkscape:label="Dangling ends">\n'
    '    <path id="weedlines-correction-dangling-shaft-0000" '
    'style="fill:none;stroke:#FF00FF;stroke-width:0.25" d="M 0,0 L 10,10"/>\n'
    '    <path id="weedlines-correction-dangling-head-0000" '
    'style="fill:#FF00FF;stroke:none" d="M 10,10 L 12,8 L 8,8 Z"/>\n'
    '  </g>\n'
    '  <g id="weedlines-correction-self-overlap" '
    'inkscape:label="Self-overlaps">\n'
    '    <path id="weedlines-correction-self-overlap-shaft-0000" '
    'style="fill:none;stroke:#00E5FF;stroke-width:0.25" d="M 1,1 L 4,4"/>\n'
    '    <path id="weedlines-correction-self-overlap-head-0000" '
    'style="fill:#00E5FF;stroke:none" d="M 4,4 L 6,3 L 3,3 Z"/>\n'
    '  </g>\n'
    '</svg>\n'
) % _INK


def _open_document():
    return inkex.load_svg(_OPEN.encode('utf-8')).getroot()


def _import(root):
    effect = IMP.WeedLinesImportEffect()
    effect.svg = root
    effect.effect()
    return root


def _descendants(el):
    found = []
    for child in el:
        found.append(child)
        found.extend(_descendants(child))
    return found


def test_correction_file_becomes_one_layer_of_groups(tmp_path, monkeypatch):
    monkeypatch.setattr(JOB, 'cache_dir', lambda: str(tmp_path))
    svg_path = os.path.join(str(tmp_path), 'last_result.svg')
    with open(svg_path, 'w', encoding='utf-8') as fh:
        fh.write(_CORRECTION)

    root = _import(_open_document())
    person = root.getElementById('person-path')
    assert person.get('d') == _PERSON_D
    assert person.getparent().get('id') == 'layer1'
    assert len(list(person.getparent())) == 1

    layers = [
        el for el in root
        if el.get(_LABEL) == 'Weedlines corrections'
    ]
    assert len(layers) == 1
    layer = layers[0]
    assert list(root)[-1] is layer
    assert layer.get(_MODE) == 'layer'
    assert [el.get(_LABEL) for el in layer] == [
        'Dangling ends', 'Self-overlaps',
    ]
    by_id = {el.get('id'): el for el in _descendants(layer)}
    assert list(by_id) == [
        'weedlines-correction-dangling',
        'weedlines-correction-dangling-shaft-0000',
        'weedlines-correction-dangling-head-0000',
        'weedlines-correction-self-overlap',
        'weedlines-correction-self-overlap-shaft-0000',
        'weedlines-correction-self-overlap-head-0000',
    ]
    assert by_id['weedlines-correction-dangling-shaft-0000'].get('d') == (
        'M 0,0 L 10,10')
    assert by_id['weedlines-correction-self-overlap-head-0000'].get('d') == (
        'M 4,4 L 6,3 L 3,3 Z')
    assert root.getElementById('weedlines-design') is None
    assert all(el.get(_LABEL) != 'Weedlines design' for el in _descendants(root))


def test_weed_line_file_still_contributes_design_and_cuts(tmp_path, monkeypatch):
    monkeypatch.setattr(JOB, 'cache_dir', lambda: str(tmp_path))
    JOB.write_result(
        'Weed lines',
        ['M 0,0 L 12,0'],
        keep_d='M 0,0 L 8,0 L 8,8 Z',
        doc_attrs={'width': '20', 'height': '20', 'viewBox': '0 0 20 20'},
    )
    root = _import(_open_document())
    person = root.getElementById('person-path')
    assert person.get('d') == _PERSON_D
    assert person.getparent().get('id') == 'layer1'

    design = root.getElementById('weedlines-design')
    cuts = root.getElementById('weedlines-cuts')
    assert design is not None
    assert design.get(_LABEL) == 'Weedlines design'
    assert root.getElementById('weedlines-keep') is not None
    assert cuts is not None
    assert cuts.getparent() is design.getparent()
    assert design.getparent().get(_LABEL) == 'Weed lines'
    cut = root.getElementById('weed-cut-0000')
    assert cut is not None and cut.getparent() is cuts
    assert cut.get('d') == 'M 0,0 L 12,0'
    assert root.getElementByName('Weedlines corrections') is None
