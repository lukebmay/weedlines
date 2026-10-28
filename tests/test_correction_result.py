# -*- coding: utf-8 -*-
"""Correction result: arrow groups only. The weed-line result stays."""
from __future__ import division

import json
import os
import re
import sys

import pytest

_EXT = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'extensions', 'inkscape'))
if _EXT not in sys.path:
    sys.path.insert(0, _EXT)

import weedlines_job as JOB  # noqa: E402
import weedlines_svg as SVG  # noqa: E402

_INK_LABEL = '{http://www.inkscape.org/namespaces/inkscape}label'
_DOC = {'width': '100', 'height': '80', 'viewBox': '0 0 100 80'}
_CLOSEPATH = re.compile(r'(^|[^A-Za-z0-9])[Zz]($|[^A-Za-z0-9])')


def _arrow_sets(targets_by_kind):
    try:
        from weedlib.arrows import build_arrow_paths
        from weedlib.qt import QRectF
    except ImportError as exc:
        pytest.skip('Qt binding required: %s' % exc)
    bounds = QRectF(0, 0, 100, 80)
    arrows = {}
    for kind, targets in targets_by_kind.items():
        if targets:
            arrows[kind] = build_arrow_paths(kind, targets, bounds)
        else:
            arrows[kind] = []
    return arrows


def _write(tmp_path, monkeypatch, arrows):
    monkeypatch.setattr(JOB, 'cache_dir', lambda: str(tmp_path))
    json_path = JOB.write_correction_result(arrows, doc_attrs=_DOC)
    svg_path = os.path.join(str(tmp_path), 'last_result.svg')
    return json_path, svg_path


def _paths(group):
    found = []
    for el in list(group):
        tag = el.tag
        local = tag.rsplit('}', 1)[-1] if isinstance(tag, str) else ''
        if local == 'path':
            found.append(el)
    return found


def _fill(el):
    for part in (el.get('style') or '').split(';'):
        if ':' not in part:
            continue
        key, value = part.split(':', 1)
        if key.strip() == 'fill':
            return value.strip()
    return el.get('fill')


def test_empty_kind_is_omitted_and_file_has_no_design(tmp_path, monkeypatch):
    arrows = _arrow_sets({
        'dangling': [(30, 40)],
        'overlap': [],
        'self-overlap': [(20, 70)],
    })
    json_path, svg_path = _write(tmp_path, monkeypatch, arrows)
    with open(svg_path, encoding='utf-8') as fh:
        text = fh.read()
    assert 'Weedlines design' not in text
    assert 'weedlines-design' not in text
    assert 'weedlines-keep' not in text
    groups = SVG.load_correction_svg_groups(svg_path)
    assert [group.get(_INK_LABEL) for group in groups] == [
        'Dangling ends', 'Self-overlaps',
    ]
    ids = [el.get('id') for group in groups for el in _paths(group)]
    assert ids
    assert all(path_id and path_id.startswith('weedlines-correction') for path_id in ids)
    with open(json_path, encoding='utf-8') as fh:
        payload = json.load(fh)
    assert payload.get('result') == 'correction'
    assert 'keep_d' not in payload
    assert payload.get('svg') == 'last_result.svg'


def test_shaft_has_no_fill_and_head_uses_arrow_color(tmp_path, monkeypatch):
    arrows = _arrow_sets({
        'dangling': [(30, 40)],
        'overlap': [(40, 50)],
        'self-overlap': [(20, 70)],
    })
    _json_path, svg_path = _write(tmp_path, monkeypatch, arrows)
    by_label = {
        group.get(_INK_LABEL): group
        for group in SVG.load_correction_svg_groups(svg_path)
    }
    expect = {
        'Dangling ends': arrows['dangling'][0].color,
        'Figure overlaps': arrows['overlap'][0].color,
        'Self-overlaps': arrows['self-overlap'][0].color,
    }
    assert set(by_label) == set(expect)
    for label, color in expect.items():
        paths = _paths(by_label[label])
        shafts = [el for el in paths if '-shaft-' in (el.get('id') or '')]
        heads = [el for el in paths if '-head-' in (el.get('id') or '')]
        assert shafts and heads
        assert all(_fill(el) == 'none' for el in shafts)
        assert all(_fill(el) == color for el in heads)


def test_open_shaft_is_not_closed_in_the_file(tmp_path, monkeypatch):
    arrows = _arrow_sets({
        'dangling': [(30, 40)],
        'overlap': [],
        'self-overlap': [],
    })
    _json_path, svg_path = _write(tmp_path, monkeypatch, arrows)
    shafts = [
        el
        for group in SVG.load_correction_svg_groups(svg_path)
        for el in _paths(group)
        if '-shaft-' in (el.get('id') or '')
    ]
    assert len(shafts) == 1
    d = shafts[0].get('d') or ''
    from weedlib.svg_paths import qpainterpath_to_svg_d
    open_d = qpainterpath_to_svg_d(
        arrows['dangling'][0].shaft, close_subpaths=False)
    assert d == open_d
    assert _CLOSEPATH.search(d) is None


def test_write_result_still_writes_design_and_cuts(tmp_path, monkeypatch):
    monkeypatch.setattr(JOB, 'cache_dir', lambda: str(tmp_path))
    JOB.write_result(
        'Weed lines',
        ['M 0,0 L 12,0'],
        keep_d='M 0,0 L 8,0 L 8,8 Z',
        doc_attrs={'width': '20', 'height': '20', 'viewBox': '0 0 20 20'},
    )
    svg_path = os.path.join(str(tmp_path), 'last_result.svg')
    design, cuts = SVG.load_result_svg_groups(svg_path)
    assert design is not None
    assert design.get('id') == 'weedlines-design'
    assert cuts is not None
    cut_ds = [
        el.get('d') for el in list(cuts)
        if (el.get('id') or '').startswith('weed-cut-')
    ]
    assert cut_ds == ['M 0,0 L 12,0']
    assert SVG.load_correction_svg_groups(svg_path) == []
