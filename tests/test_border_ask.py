# -*- coding: utf-8 -*-
"""A stored corner radius reaches the three border asks. No Inkscape."""
from __future__ import division

import importlib
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest

try:
    from weedlib.qt import QPainterPath
except ImportError:
    pytest.skip('Qt cannot load', allow_module_level=True)

_EXT_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'extensions', 'inkscape'))
if _EXT_DIR not in sys.path:
    sys.path.insert(0, _EXT_DIR)

import weedlib  # noqa: E402
from weedlines_dialog.geometry_ask import (  # noqa: E402
    _Ask,
    _ask_piece_border,
    _ask_solver,
    _ask_surround,
    _pack_path,
    _plain_int,
    _unpack_path,
)
from weedlines_dialog.run_controls import _RunControls  # noqa: E402

_MISSING = object()
_MOVE = _plain_int(QPainterPath.MoveToElement)
_LINE = _plain_int(QPainterPath.LineToElement)
_CURVE = _plain_int(QPainterPath.CurveToElement)


class _Flag(object):

    def is_set(self):
        return False


class _Regions(object):

    def __init__(self, subject):
        self.subject = subject


class _Host(_Ask, _RunControls):
    """The ask methods, with the spawn replaced by the request itself."""

    def __init__(self, subject):
        self._subject = subject
        self.blocked = False
        self.QPainterPath = QPainterPath
        self.requests = []
        self.state = {
            'lengths': {
                'padding': 4.0,
                'spacing': 10.0,
                'collar': 2.0,
                'distance': 3.0,
                'join': 1.0,
                'inner': 2.0,
                'border': 2.0,
            },
            'swapped': False,
            'regions_swap': False,
            'ask': None,
            'border_inflight': None,
            'surround_inflight': None,
            'surround_started': True,
            'drop': False,
            'cancel': _Flag(),
        }

    def _in_surround(self):
        return True

    def _ensure_regions(self):
        return _Regions(self._subject)

    def _begin_ask(self, request):
        self.requests.append(dict(request))
        self.state['ask'] = request['kind']
        return True


class _Conn(object):

    def __init__(self):
        self.sent = []

    def send(self, message):
        self.sent.append(message)


def _subject():
    path = QPainterPath()
    path.addRect(0, 0, 40, 30)
    return path


def _collect(host):
    host.requests = []
    assert host._ask_border() is True
    host.state['ask'] = None
    assert host._ask_surrounds() is True
    host.state['ask'] = None
    host.requests.append(host._solver_request('frame'))
    assert len(host.requests) == 3
    return list(host.requests)


def _kinds(packed):
    elements, _rule = packed
    return [element[0] for element in elements]


def _sent(conn, kind):
    return [message[1:] for message in conn.sent if message[0] == kind]


def _watch(monkeypatch):
    seen = []
    piece_mod = importlib.import_module('weedlib.piece_border')
    real_piece = piece_mod.piece_border
    real_surrounds = weedlib.build_surrounds
    real_weeds = weedlib.generate_weeds

    def piece(*args, **kwargs):
        seen.append(('piece_border', kwargs.get('corner_radius', _MISSING)))
        return real_piece(*args, **kwargs)

    def surrounds(*args, **kwargs):
        seen.append(('build_surrounds', kwargs.get('corner_radius', _MISSING)))
        return real_surrounds(*args, **kwargs)

    def weeds(*args, **kwargs):
        seen.append(('generate_weeds', kwargs.get('corner_radius', _MISSING)))
        return real_weeds(*args, **kwargs)

    monkeypatch.setattr(piece_mod, 'piece_border', piece)
    monkeypatch.setattr(weedlib, 'build_surrounds', surrounds)
    monkeypatch.setattr(weedlib, 'generate_weeds', weeds)
    return seen, real_piece, real_surrounds, real_weeds


def _run(requests):
    border_conn = _Conn()
    surround_conn = _Conn()
    solver_conn = _Conn()
    _ask_piece_border(requests[0], border_conn)
    _ask_surround(requests[1], surround_conn)
    _ask_solver(requests[2], solver_conn, _Flag(), _Flag())
    return border_conn, surround_conn, solver_conn


def _library_border(real_piece, request):
    subject = _unpack_path(request['elements'], request['rule'])
    kwargs = {}
    if 'corner_radius' in request:
        kwargs['corner_radius'] = request['corner_radius']
    paths = real_piece(
        subject, request['inner_distance'], request['border_width'], **kwargs)
    return [_pack_path(path) for path in paths]


def test_no_radius_leaves_the_square_calls(monkeypatch):
    """No stored radius: the three calls omit it and the border stays square."""
    host = _Host(_subject())
    requests = _collect(host)
    for request in requests:
        assert 'corner_radius' not in request
    host.state['ask'] = None
    assert host._border_stale() is False
    assert host._surround_stale() is False
    assert host._ask_border() is False
    again = host._solver_request('frame')
    assert 'corner_radius' not in again

    seen, real_piece, real_surrounds, real_weeds = _watch(monkeypatch)
    border_conn, surround_conn, solver_conn = _run(requests)
    assert seen == [
        ('piece_border', _MISSING),
        ('build_surrounds', _MISSING),
        ('generate_weeds', _MISSING),
    ]
    borders = _sent(border_conn, 'border')
    assert borders == _library_border(real_piece, requests[0])
    assert borders
    for packed in borders:
        assert _CURVE not in _kinds(packed)
        assert set(_kinds(packed)) <= set((_MOVE, _LINE))

    subject = _unpack_path(requests[1]['elements'], requests[1]['rule'])
    surrounds = real_surrounds(
        subject, requests[1]['distance'], requests[1]['join_gap'],
        inner_distance=requests[1]['inner_distance'])
    assert _sent(surround_conn, 'surround') == [_pack_path(path) for path in surrounds]

    subject = _unpack_path(requests[2]['elements'], requests[2]['rule'])
    weed = real_weeds(
        subject,
        mode='frame',
        padding=requests[2]['padding'],
        spacing=requests[2]['spacing'],
        collar=requests[2]['collar'],
        inner_distance=requests[2]['inner_distance'],
        border_width=requests[2]['border_width'])
    assert _sent(solver_conn, 'result') == [_pack_path(weed)]


def test_stored_radius_reaches_the_three_calls(monkeypatch):
    """A radius stored after the square ask reaches all three library calls."""
    host = _Host(_subject())
    square = _collect(host)
    for request in square:
        assert 'corner_radius' not in request
    host.state['ask'] = None
    host.state['lengths']['corner_radius'] = 4.0
    assert host._border_stale() is True
    assert host._surround_stale() is True
    requests = _collect(host)
    assert [request['corner_radius'] for request in requests] == [4.0, 4.0, 4.0]

    seen, real_piece, real_surrounds, real_weeds = _watch(monkeypatch)
    border_conn, surround_conn, solver_conn = _run(requests)
    assert seen == [
        ('piece_border', 4.0),
        ('build_surrounds', 4.0),
        ('generate_weeds', 4.0),
    ]
    borders = _sent(border_conn, 'border')
    assert borders == _library_border(real_piece, requests[0])
    assert any(_CURVE in _kinds(packed) for packed in borders)

    subject = _unpack_path(requests[1]['elements'], requests[1]['rule'])
    surrounds = real_surrounds(
        subject, requests[1]['distance'], requests[1]['join_gap'],
        inner_distance=requests[1]['inner_distance'], corner_radius=4.0)
    assert _sent(surround_conn, 'surround') == [_pack_path(path) for path in surrounds]

    subject = _unpack_path(requests[2]['elements'], requests[2]['rule'])
    weed = real_weeds(
        subject,
        mode='frame',
        padding=requests[2]['padding'],
        spacing=requests[2]['spacing'],
        collar=requests[2]['collar'],
        inner_distance=requests[2]['inner_distance'],
        border_width=requests[2]['border_width'],
        corner_radius=4.0)
    assert _sent(solver_conn, 'result') == [_pack_path(weed)]

    host.state['ask'] = None
    host.state['lengths']['corner_radius'] = 0.0
    zeroed = _collect(host)
    assert [request['corner_radius'] for request in zeroed] == [0.0, 0.0, 0.0]
    seen[:] = []
    border_conn, _surround_conn, _solver_conn = _run(zeroed)
    assert seen[0] == ('piece_border', 0.0)
    assert seen[1] == ('build_surrounds', 0.0)
    assert seen[2] == ('generate_weeds', 0.0)
    borders = _sent(border_conn, 'border')
    assert borders == _library_border(real_piece, zeroed[0])
    for packed in borders:
        assert _CURVE not in _kinds(packed)
