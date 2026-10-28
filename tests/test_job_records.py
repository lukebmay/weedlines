# -*- coding: utf-8 -*-
"""Job path records: open geometry, computed fill, correction skip."""
from __future__ import division

import importlib.util
import os
import re

from weedlib.qt import QTransform


def _load(name, filename):
    path = os.path.join(
        os.path.dirname(__file__), '..', 'extensions', 'inkscape', filename)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


EXT = _load('weedlines_ext_under_test', 'weedlines.py')
JOB = _load('weedlines_job_under_test', 'weedlines_job.py')

_INK_LABEL = '{http://www.inkscape.org/namespaces/inkscape}label'


class _Matrix(object):
    def __init__(self, matrix):
        self.matrix = matrix


class _Node(object):
    """Stand-in for an SVG element. No Inkscape."""

    def __init__(self, tag, attrib=None, children=None, matrix=None):
        self.tag = tag
        self.attrib = dict(attrib or {})
        self.children = []
        self.parent = None
        self._matrix = matrix
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
        a, b, c, d, e, f = self._matrix or (1, 0, 0, 1, 0, 0)
        return _Matrix(((a, c, e), (b, d, f)))


def _closed_flags_in_d(d):
    """True per absolute subpath when that subpath's data has a closepath."""
    parts = re.findall(r'M [^M]*', d or '')
    return ['Z' in part for part in parts]


def test_stored_open_path_has_no_added_closepath():
    # First subpath is open. Second was closed. Translate bakes document units.
    element = _Node(
        'path',
        {
            'id': 'open-then-closed',
            'd': 'M 0 0 L 10 0 M 0 20 L 10 20 L 10 30 Z',
        },
        matrix=(1, 0, 0, 1, 5, 0),
    )
    records = EXT._path_records([element], None, QTransform)
    assert len(records) == 1
    record = records[0]
    assert record['d'] == (
        'M 5,0 L 15,0 M 5,20 L 15,20 L 15,30 L 5,20 Z'
    )
    assert 'Z' not in record['d'].split('M ')[1]
    assert record['closed'] == [False, True]
    assert record['closed'] == _closed_flags_in_d(record['d'])


def test_computed_fill_records():
    d = 'M 0 0 L 1 0'
    root = _Node('g', {}, [
        _Node('path', {'id': 'none', 'd': d, 'fill': 'none'}),
        _Node('path', {
            'id': 'clear', 'd': d, 'fill': '#ff0000', 'opacity': '0',
        }),
        _Node('path', {
            'id': 'solid', 'd': d, 'fill': 'none',
            'style': 'fill:#123456',
        }),
        _Node('path', {'id': 'other', 'd': d, 'fill': 'url(#fade)'}),
        _Node('g', {'style': 'fill:#00aa00'}, [
            _Node('path', {'id': 'inherited', 'd': d}),
        ]),
    ])
    records = EXT._path_records([root], None, QTransform)
    assert [(rec['id'], rec['fill']) for rec in records] == [
        ('none', 'none'),
        ('clear', 'none'),
        ('solid', '#123456'),
        ('other', 'other'),
        ('inherited', '#00aa00'),
    ]


def test_correction_paths_are_omitted():
    d = 'M 0 0 L 2 0'
    root = _Node('g', {}, [
        _Node('g', {_INK_LABEL: 'Weedlines corrections'}, [
            _Node('g', {}, [
                _Node('path', {'id': 'arrow', 'd': d, 'fill': '#ff0000'}),
            ]),
        ]),
        _Node('path', {
            'id': 'weedlines-correction-9', 'd': d, 'fill': '#00ff00',
        }),
        _Node('path', {'id': 'keep', 'd': d, 'fill': '#0000ff'}),
    ])
    records = EXT._path_records([root], None, QTransform)
    assert [rec['id'] for rec in records] == ['keep']


def test_read_job_returns_keep_d_and_document_size(tmp_path, monkeypatch):
    monkeypatch.setattr(JOB, 'cache_dir', lambda: str(tmp_path))
    records = [{
        'id': 'p',
        'd': 'M 0,0 L 1,0',
        'closed': [False],
        'fill': 'none',
    }]
    doc = {'width': '210mm', 'height': '297mm', 'viewBox': '0 0 210 297'}
    path = JOB.write_job(
        'M 0 0 L 1 1 Z', {'mode': 'frame'},
        doc_attrs=doc, records=records)
    loaded = JOB.read_job(path)
    assert loaded['keep_d'] == 'M 0 0 L 1 1 Z'
    assert loaded['doc_attrs']['width'] == '210mm'
    assert loaded['doc_attrs']['height'] == '297mm'
    assert loaded['doc_attrs']['viewBox'] == '0 0 210 297'
    assert loaded['records'] == records
