# -*- coding: utf-8 -*-
"""Inkscape extension: import last Weedlines result (design + cuts).

Prefers ``last_result.svg`` so design keep and weed cuts arrive together in
the same document user units / viewBox as when the job was started.
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


class WeedLinesImportEffect(object):
    def add_arguments(self, pars):
        pars.add_argument('--tab', type=str, default='')

    def effect(self):
        import inkex

        _ensure_paths()
        from weedlines_job import read_result, result_path, result_svg_file
        from weedlines_svg import load_result_svg_groups, result_svg_path
        from weedlines import _add_weed_layer_from_d
        from inkex import PathElement

        payload = read_result()
        svg_file = result_svg_file()
        if not os.path.isfile(svg_file):
            svg_file = result_svg_path()

        layer_name = (payload or {}).get('layer_name') or 'Weed lines'

        if os.path.isfile(svg_file):
            design, cuts = load_result_svg_groups(svg_file)
            if design is None and cuts is None:
                raise inkex.AbortExtension(
                    'Weedlines result SVG was empty:\n%s' % svg_file
                )

            # Parent layer holding design + cuts (same user units as source).
            ns_ink = 'http://www.inkscape.org/namespaces/inkscape'
            if hasattr(inkex, 'Group') and hasattr(inkex.Group, 'new'):
                layer = self.svg.add(
                    inkex.Group.new(layer_name, is_layer=True))
            else:
                layer = inkex.etree.SubElement(
                    self.svg, inkex.addNS('g', 'svg'))
                layer.set('{%s}groupmode' % ns_ink, 'layer')
                layer.set('{%s}label' % ns_ink, layer_name)

            if design is not None:
                _append_etree_element(layer, design, inkex)
            if cuts is not None:
                _append_etree_element(layer, cuts, inkex)
            return

        # Legacy JSON-only fallback (cuts only).
        if not payload or not payload.get('paths'):
            raise inkex.AbortExtension(
                'No Weedlines result found.\n'
                'Run Extensions → Weedlines → Weedlines from selection…, '
                'Apply in the Weedlines window, then Import again.\n'
                '(Looking for %s or %s)' % (result_path(), svg_file)
            )

        d_list = [d for d in payload['paths'] if d]
        if not d_list:
            raise inkex.AbortExtension('Weedlines result file had empty paths.')
        _add_weed_layer_from_d(
            self.svg, inkex, PathElement, d_list, layer_name)


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
