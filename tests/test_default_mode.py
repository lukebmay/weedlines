# -*- coding: utf-8 -*-
"""Unchosen job mode is Surround and Conquer. Chosen modes stay."""
from __future__ import division

import argparse
import importlib.util
import os

EXT = os.path.join(
    os.path.dirname(__file__), '..', 'extensions', 'inkscape', 'weedlines.py')

_UNCHOSEN = 'Surround and Conquer'


def _load(name):
    spec = importlib.util.spec_from_file_location(name, EXT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _parse(mod, argv):
    class Base(object):
        def add_arguments(self, pars):
            pass

    class Plugin(mod.WeedLinesEffect, Base):
        pass

    pars = argparse.ArgumentParser()
    Plugin().add_arguments(pars)
    return pars.parse_args(argv)


def _stored(mod, raw):
    return mod._mode_on_job(raw)


def test_omitted_and_blank_mode_store_surround_and_conquer():
    mod = _load('weedlines_default_mode')
    omitted = _parse(mod, [])
    assert omitted.mode == _UNCHOSEN
    assert _stored(mod, omitted.mode) == _UNCHOSEN
    blank = _parse(mod, ['--mode='])
    assert _stored(mod, blank.mode) == _UNCHOSEN
    assert _stored(mod, None) == _UNCHOSEN
    assert _stored(mod, '   ') == _UNCHOSEN


def test_chosen_mode_stays_lowercase():
    mod = _load('weedlines_default_mode_chosen')
    assert _stored(mod, _parse(mod, ['--mode=frame']).mode) == 'frame'
    assert _stored(mod, _parse(mod, ['--mode=grid']).mode) == 'grid'
    assert _stored(
        mod, _parse(mod, ['--mode=island-hop']).mode) == 'island-hop'
