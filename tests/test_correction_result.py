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


def _write(tmp_path, monkeypatch, arrows, labels=None):
    monkeypatch.setattr(JOB, 'cache_dir', lambda: str(tmp_path))
    json_path = JOB.write_correction_result(
        arrows, doc_attrs=_DOC, labels=labels)
    svg_path = os.path.join(str(tmp_path), 'last_ready.svg')
    return json_path, svg_path


def _paths(group):
    found = []
    for el in list(group):
        tag = el.tag
        local = tag.rsplit('}', 1)[-1] if isinstance(tag, str) else ''
        if local == 'path':
            found.append(el)
    return found


def _local(el):
    tag = el.tag
    if not isinstance(tag, str):
        return ''
    return tag.rsplit('}', 1)[-1]


def _texts(group):
    return [el for el in list(group) if _local(el) == 'text']


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
    assert 'inkscape:label="Border"' not in text
    assert 'inkscape:label="Weed lines"' not in text
    assert 'inkscape:label="Original design"' not in text
    assert 'weed-cut-' not in text
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
    assert payload.get('svg') == 'last_ready.svg'
    assert not os.path.isfile(os.path.join(str(tmp_path), 'last_result.svg'))


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


def test_present_kind_has_one_text_at_the_mark_origin(tmp_path, monkeypatch):
    from weedlib.ready import CorrectionLabel, build_correction_marks

    records = [{
        'id': 'gap',
        'd': 'M 5,6 L 15,6 L 15,20',
        'closed': [True],
        'fill': 'none',
    }]
    marks = build_correction_marks(records)
    assert [label.text for label in marks.labels] == ['Dangling ends']
    extra = list(marks.labels) + [
        CorrectionLabel('Figure overlaps', '#FF6A00', (1.0, 2.0)),
    ]
    _json_path, svg_path = _write(
        tmp_path, monkeypatch, marks.arrows, labels=extra)
    groups = SVG.load_correction_svg_groups(svg_path)
    assert [group.get(_INK_LABEL) for group in groups] == ['Dangling ends']
    texts = _texts(groups[0])
    assert len(texts) == 1
    label = marks.labels[0]
    assert texts[0].text == label.text
    assert float(texts[0].get('x')) == pytest.approx(label.point[0])
    assert float(texts[0].get('y')) == pytest.approx(label.point[1])
    assert label.color == '#FF00FF'
    assert label.color in (texts[0].get('style') or '')
    with open(svg_path, encoding='utf-8') as fh:
        written = fh.read()
    assert 'Figure overlaps' not in written
    assert 'Self-overlaps' not in written
    shapes = [
        el for el in list(groups[0])
        if _local(el) not in ('path', 'text')
    ]
    assert shapes == []


def test_default_result_is_border_and_weed_lines(tmp_path, monkeypatch):
    monkeypatch.setattr(JOB, 'cache_dir', lambda: str(tmp_path))
    JOB.write_result(
        'Weed lines',
        ['M 0,0 L 12,0'],
        keep_d='M 9,9 L 8,8',
        doc_attrs={'width': '20', 'height': '20', 'viewBox': '0 0 20 20'},
        border_d_list=['M 1,1 L 4,1 L 4,3'],
    )
    svg_path = os.path.join(str(tmp_path), 'last_result.svg')
    group = SVG.load_result_svg_groups(svg_path)
    assert group is not None
    assert group.get('id') == 'weedlines'
    assert [el.get(_INK_LABEL) for el in list(group)] == [
        'Border', 'Weed lines',
    ]
    cut_ds = [
        el.get('d') for el in group.iter()
        if (el.get('id') or '').startswith('weed-cut-')
    ]
    assert cut_ds == ['M 0,0 L 12,0']
    with open(svg_path, encoding='utf-8') as fh:
        text = fh.read()
    assert 'M 9,9 L 8,8' not in text
    assert 'Weedlines design' not in text
    assert 'Original design' not in text
    assert 'Weedlines corrections' not in text
    assert text.count('inkscape:groupmode="layer"') == 1
    assert SVG.load_correction_svg_groups(svg_path) == []


def test_original_design_copies_records_when_included(tmp_path, monkeypatch):
    monkeypatch.setattr(JOB, 'cache_dir', lambda: str(tmp_path))
    records = [
        {
            'id': 'gap',
            'd': 'M 5,6 L 15,6 L 15,20',
            'closed': [True],
            'fill': 'none',
        },
        {
            'id': 'weedlines-correction-arrow',
            'd': 'M 7,7 L 8,9',
            'closed': [False],
            'fill': 'none',
        },
        {
            'id': 'panel',
            'd': 'M 1,1 L 2,1',
            'closed': [False],
            'fill': '#112233',
        },
    ]
    job_path = JOB.write_job('', {'mode': 'frame'}, records=records)
    JOB.write_result(
        'Weed lines',
        ['M 0,0 L 12,0'],
        doc_attrs=_DOC,
        border_d_list=['M 0,0 L 3,0'],
        records=records,
    )
    svg_path = os.path.join(str(tmp_path), 'last_result.svg')
    group = SVG.load_result_svg_groups(svg_path)
    assert [el.get(_INK_LABEL) for el in list(group)] == [
        'Border', 'Weed lines', 'Original design',
    ]
    original = list(group)[-1]
    paths = _paths(original)
    assert [el.get('id') for el in paths] == ['gap', 'panel']
    assert [el.get('d') for el in paths] == [
        'M 5,6 L 15,6 L 15,20',
        'M 1,1 L 2,1',
    ]
    assert all(not _CLOSEPATH.search(el.get('d') or '') for el in paths)
    with open(svg_path, encoding='utf-8') as fh:
        text = fh.read()
    assert 'weedlines-correction' not in text
    assert 'Weedlines corrections' not in text
    assert 'M 7,7 L 8,9' not in text
    job = JOB.read_job(job_path)
    assert job['records'] == records
    from weedlib.figures.check import classify_figures
    figures = classify_figures(job['records']).figures
    assert [figure.id for figure in figures] == ['gap', 'panel']


def _arrow_ds(svg_path):
    return [
        el.get('d')
        for group in SVG.load_correction_svg_groups(svg_path)
        if group.get(_INK_LABEL) != 'Ready fixes'
        for el in _paths(group)
    ]


def test_approved_paths_are_one_ready_fixes_group(tmp_path, monkeypatch):
    arrows = _arrow_sets({
        'dangling': [(30, 40)],
        'overlap': [],
        'self-overlap': [(20, 70)],
    })
    _json_path, svg_path = _write(tmp_path, monkeypatch, arrows)
    before = _arrow_ds(svg_path)
    assert before
    SVG.write_ready_fixes(
        ['M 0,0 L 3,0', 'M 1,1 L 1,4'], path=svg_path)
    groups = SVG.load_correction_svg_groups(svg_path)
    assert [group.get(_INK_LABEL) for group in groups] == [
        'Dangling ends', 'Self-overlaps', 'Ready fixes',
    ]
    assert _arrow_ds(svg_path) == before
    ready = groups[-1]
    assert ready.get('id') == 'weedlines-correction-ready'
    assert [el.get('d') for el in _paths(ready)] == [
        'M 0,0 L 3,0', 'M 1,1 L 1,4',
    ]
    assert all(_fill(el) == 'none' for el in _paths(ready))

    from weedlib.qt import QPainterPath
    from weedlib.svg_paths import qpainterpath_to_svg_d
    path = QPainterPath()
    path.moveTo(0, 0)
    path.lineTo(6, 0)
    SVG.write_ready_fixes([path], path=svg_path)
    groups = SVG.load_correction_svg_groups(svg_path)
    assert [group.get(_INK_LABEL) for group in groups] == [
        'Dangling ends', 'Self-overlaps', 'Ready fixes',
    ]
    assert _arrow_ds(svg_path) == before
    ready_paths = _paths(groups[-1])
    assert len(ready_paths) == 1
    assert ready_paths[0].get('d') == qpainterpath_to_svg_d(
        path, close_subpaths=False)
    assert ready_paths[0].get('id') == 'weedlines-ready-0000'


def test_no_approved_paths_leaves_the_arrow_file(tmp_path, monkeypatch):
    arrows = _arrow_sets({
        'dangling': [(30, 40)],
        'overlap': [],
        'self-overlap': [],
    })
    _json_path, svg_path = _write(tmp_path, monkeypatch, arrows)
    with open(svg_path, encoding='utf-8') as fh:
        before = fh.read()
    assert 'Ready fixes' not in before
    SVG.write_ready_fixes([], path=svg_path)
    SVG.write_ready_fixes(['', '  '], path=svg_path)
    with open(svg_path, encoding='utf-8') as fh:
        assert fh.read() == before
    missing = os.path.join(str(tmp_path), 'absent.svg')
    SVG.write_ready_fixes(['M 0,0 L 1,0'], path=missing)
    assert not os.path.isfile(missing)
