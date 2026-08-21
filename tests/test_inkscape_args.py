# -*- coding: utf-8 -*-
"""Regression: Inkscape weed extension must register --layer_name etc.

Previously WeedLinesEffect was mixed in *after* EffectExtension, so
EffectExtension.add_arguments won the MRO and Inkscape treated
``--layer_name=Weed lines`` as INPUT_FILE during Live Preview.
"""
from __future__ import division

import argparse
import os
import sys

import pytest

EXT = os.path.join(
    os.path.dirname(__file__), '..', 'extensions', 'inkscape', 'weedlines.py')


def test_weed_plugin_registers_layer_name_with_spaces():
    # Load module without requiring inkex at import of helpers
    import importlib.util
    spec = importlib.util.spec_from_file_location('weedlines_under_test', EXT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    class Base(object):
        def add_arguments(self, pars):
            pass

    # Same MRO as production main()
    class Plugin(mod.WeedLinesEffect, Base):
        pass

    pars = argparse.ArgumentParser()
    pars.add_argument('INPUT_FILE', nargs='?')
    Plugin().add_arguments(pars)
    ns = pars.parse_args([
        '--mode=island-hop',
        '--layer_name=Weed lines',
        '/tmp/doc.svg',
    ])
    assert ns.layer_name == 'Weed lines'
    assert ns.INPUT_FILE == '/tmp/doc.svg'
    assert ns.mode == 'island-hop'


def test_wrong_mro_would_drop_custom_args():
    """Document the failure mode: Base first → custom flags become positionals."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('weedlines_under_test2', EXT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    class Base(object):
        def add_arguments(self, pars):
            pass

    class Broken(Base, mod.WeedLinesEffect):
        pass

    pars = argparse.ArgumentParser()
    pars.add_argument('INPUT_FILE', nargs='?')
    Broken().add_arguments(pars)
    # Base.add_arguments is empty; --layer_name is unknown → SystemExit
    with pytest.raises(SystemExit):
        pars.parse_args(['--layer_name=Weed lines', '/tmp/doc.svg'])
