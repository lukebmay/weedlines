# -*- coding: utf-8 -*-
"""Inkscape extension: import the last Weedlines result.

Prefers ``last_result.svg``. A weed-line result places its Weedlines
group on one new layer. A ready file stays on the corrections layer.
"""
from __future__ import division

import os
import sys


def _ensure_paths():
    ext_dir = os.path.abspath(os.path.dirname(__file__))
    if ext_dir not in sys.path:
        sys.path.insert(0, ext_dir)
    try:
        import weedlib  # noqa: F401
        return
    except ImportError:
        pass
    root = os.path.abspath(os.path.join(ext_dir, '..', '..'))
    src = os.path.join(root, 'src')
    if os.path.isdir(os.path.join(src, 'weedlib')) and src not in sys.path:
        sys.path.insert(0, src)


def _append_etree_element(parent, el, inkex):
    """Deep-copy an ElementTree element into an inkex/lxml parent."""
    # inkex uses lxml; ElementTree elements need re-serialization.
    from xml.etree import ElementTree as ET
    raw = ET.tostring(el, encoding='unicode')
    try:
        from lxml import etree
        node = etree.fromstring(raw)
    except Exception:
        # Fallback: inkex.etree
        node = inkex.etree.fromstring(raw)
    parent.append(node)
    return node


def _append_layer(svg, inkex, label):
    """Append a layer. A later sibling paints above the open document."""
    ns_ink = 'http://www.inkscape.org/namespaces/inkscape'
    layer_cls = getattr(inkex, 'Layer', None)
    if layer_cls is not None and hasattr(layer_cls, 'new'):
        layer = svg.add(layer_cls.new(label))
    elif hasattr(inkex, 'Group') and hasattr(inkex.Group, 'new'):
        layer = svg.add(inkex.Group.new(label))
    else:
        layer = inkex.etree.SubElement(svg, inkex.addNS('g', 'svg'))
        layer.set('{%s}label' % ns_ink, label)
    layer.set('{%s}groupmode' % ns_ink, 'layer')
    return layer


def _reimport_kind(effect):
    options = getattr(effect, 'options', None)
    kind = getattr(options, 'reimport', None) if options is not None else None
    if kind in ('ready', 'weedlines'):
        return kind
    return 'weedlines'


def _place_correction_layer(svg, inkex, groups):
    layer = _append_layer(svg, inkex, 'Weedlines corrections')
    for group in groups:
        _append_etree_element(layer, group, inkex)
    return layer


class WeedLinesImportEffect(object):
    def add_arguments(self, pars):
        pars.add_argument('--tab', type=str, default='')
        pars.add_argument('--reimport', type=str, default='weedlines')

    def effect(self):
        import inkex

        _ensure_paths()
        if _reimport_kind(self) == 'ready':
            self._import_ready(inkex)
            return
        self._import_weedlines(inkex)

    def _import_ready(self, inkex):
        from weedlines_job import ready_svg_file
        from weedlines_svg import load_correction_svg_groups

        svg_file = ready_svg_file()
        if not os.path.isfile(svg_file):
            raise inkex.AbortExtension(
                'No Weedlines ready file found.\n'
                'Run Extensions → Weedlines → 2 Make ready to cut, '
                'then 4 Reimport last ready cut.\n'
                '(Looking for %s)' % svg_file
            )
        groups = load_correction_svg_groups(svg_file)
        if not groups:
            raise inkex.AbortExtension(
                'The ready file has no correction groups:\n%s' % svg_file
            )
        _place_correction_layer(self.svg, inkex, groups)

    def _import_weedlines(self, inkex):
        from weedlines_job import read_result, result_path, result_svg_file
        from weedlines_svg import (
            load_correction_svg_groups,
            load_result_svg_groups,
            result_svg_path,
        )
        from weedlines import _add_weed_layer_from_d
        from inkex import PathElement

        payload = read_result()
        svg_file = result_svg_file()
        if not os.path.isfile(svg_file):
            svg_file = result_svg_path()

        layer_name = (payload or {}).get('layer_name') or 'Weed lines'

        if os.path.isfile(svg_file):
            groups = load_correction_svg_groups(svg_file)
            weedlines = load_result_svg_groups(svg_file)
            # A ready file is correction groups and no Weedlines group.
            if groups and weedlines is None:
                raise inkex.AbortExtension(
                    'That file is a ready result.\n'
                    'Run Extensions → Weedlines → 4 Reimport last ready cut.'
                )

            if weedlines is None:
                raise inkex.AbortExtension(
                    'Weedlines result SVG was empty:\n%s' % svg_file
                )

            layer = _append_layer(self.svg, inkex, layer_name)
            _append_etree_element(layer, weedlines, inkex)
            return

        # Legacy JSON-only fallback (cuts only).
        if not payload or not payload.get('paths'):
            raise inkex.AbortExtension(
                'No Weedlines result found.\n'
                'Run Extensions → Weedlines → 1 Auto generate weedlines, '
                'Apply in the Weedlines window, then 3 Reimport last weedlines.\n'
                '(Looking for %s or %s)' % (result_path(), svg_file)
            )

        d_list = [d for d in payload['paths'] if d]
        if not d_list:
            raise inkex.AbortExtension('Weedlines result file had empty paths.')
        recorded = payload.get('weed_line_color')
        color = recorded if recorded else '#FF0000'
        _add_weed_layer_from_d(
            self.svg, inkex, PathElement, d_list, layer_name, color)


def main():
    try:
        import inkex
    except ImportError:
        sys.stderr.write('inkex not installed.\n')
        sys.exit(2)

    _ensure_paths()
    base = getattr(inkex, 'EffectExtension', None) or inkex.Effect

    class _Plugin(WeedLinesImportEffect, base):
        pass

    _Plugin().run()


if __name__ == '__main__':
    main()
