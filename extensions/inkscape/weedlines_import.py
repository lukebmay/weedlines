# -*- coding: utf-8 -*-
"""Inkscape extension: import the last Weedlines result.

Prefers ``last_result.svg`` so a weed-line result keeps the design and
cuts in the job's user units. A correction result has no design copy;
its arrow groups go on one new layer above the open document.
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


class WeedLinesImportEffect(object):
    def add_arguments(self, pars):
        pars.add_argument('--tab', type=str, default='')

    def effect(self):
        import inkex

        _ensure_paths()
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
            design, cuts = load_result_svg_groups(svg_file)
            # Arrow groups and no design copy: do not use the weed-line layer.
            if groups and design is None:
                layer = _append_layer(self.svg, inkex, 'Weedlines corrections')
                for group in groups:
                    _append_etree_element(layer, group, inkex)
                return

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
