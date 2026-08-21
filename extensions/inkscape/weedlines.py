#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inkscape extension: run shared weedlib weed solvers.

Opens an interactive dialog (Start / Cancel, log, live cut preview) so
Inkscape is not fed stderr chatter, and long island-hop runs can be
cancelled.

Install via ``weedlines install``. Requires Qt + weedlib.
"""
from __future__ import division

import os
import sys


def _ensure_weedlib_on_path():
    """Prefer installed weedlib; else walk up to a repo with src/weedlib."""
    try:
        import weedlib  # noqa: F401
        return
    except ImportError:
        pass
    here = os.path.abspath(os.path.dirname(__file__))
    for _ in range(8):
        for candidate in (
            os.path.join(here, 'src'),
            here,
        ):
            if os.path.isdir(os.path.join(candidate, 'weedlib')):
                if candidate not in sys.path:
                    sys.path.insert(0, candidate)
                try:
                    import weedlib  # noqa: F401
                    return
                except ImportError:
                    pass
        parent = os.path.dirname(here)
        if parent == here:
            break
        here = parent
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    src = os.path.join(root, 'src')
    if os.path.isdir(os.path.join(src, 'weedlib')) and src not in sys.path:
        sys.path.insert(0, src)


def _collect_path_d(node, inkex):
    """Yield path d strings from a node tree (paths only)."""
    tag = (
        inkex.addNS('path', 'svg') if hasattr(inkex, 'addNS')
        else '{http://www.w3.org/2000/svg}path'
    )
    if node.tag == tag or (isinstance(node.tag, str) and node.tag.endswith('path')):
        d = node.get('d')
        if d:
            yield d
    for child in list(node):
        for d in _collect_path_d(child, inkex):
            yield d


def _apply_node_transform(path, node, inkex, QTransform):
    """Apply SVG transform attribute if inkex can parse it; else identity."""
    try:
        t = node.composed_transform()
        m = t.matrix if hasattr(t, 'matrix') else None
        if m is None:
            return path
        a, c, e = m[0]
        b, d, f = m[1]
        qt = QTransform(a, b, c, d, e, f)
        return qt.map(path)
    except Exception:
        return path


def _add_weed_layer(svg, inkex, PathElement, weed_path, layer_label):
    from weedlib.svg_paths import weed_path_to_open_d_list

    d_list = weed_path_to_open_d_list(weed_path)
    if not d_list:
        raise inkex.AbortExtension('Weed solver produced no cuts.')

    layer = None
    if hasattr(inkex, 'Group') and hasattr(inkex.Group, 'new'):
        layer = svg.add(inkex.Group.new(layer_label, is_layer=True))
    if layer is None:
        ns_ink = 'http://www.inkscape.org/namespaces/inkscape'
        layer = inkex.etree.SubElement(svg, inkex.addNS('g', 'svg'))
        layer.set('{%s}groupmode' % ns_ink, 'layer')
        layer.set('{%s}label' % ns_ink, layer_label)

    style = (
        'fill:none;stroke:#c04000;stroke-width:0.25;'
        'stroke-linecap:round;stroke-linejoin:round'
    )
    for i, d in enumerate(d_list):
        el = PathElement()
        el.set('d', d)
        el.set('style', style)
        el.set('id', 'weed-cut-{:04d}'.format(i))
        layer.append(el)


class WeedLinesEffect(object):
    """inkex.EffectExtension body (mixed into a subclass of EffectExtension)."""

    def add_arguments(self, pars):
        pars.add_argument('--tab', type=str, default='')
        pars.add_argument('--mode', type=str, default='frame')
        pars.add_argument('--padding', type=float, default=4.0)
        pars.add_argument('--spacing', type=float, default=25.0)
        pars.add_argument('--collar', type=float, default=4.0)
        pars.add_argument('--layer_name', type=str, default='Weed lines')

    def effect(self):
        import inkex
        from inkex import PathElement

        _ensure_weedlib_on_path()
        try:
            from weedlib.qt import QPainterPath, QTransform
        except ImportError as exc:
            raise inkex.AbortExtension(
                'weedlib / Qt not available: {}'.format(exc)
            )

        ext_dir = os.path.abspath(os.path.dirname(__file__))
        if ext_dir not in sys.path:
            sys.path.insert(0, ext_dir)

        nodes = list(self.svg.selection.values()) if self.svg.selection else []
        if not nodes:
            nodes = [self.svg]

        from weedlib.svg_paths import svg_d_to_qpainterpath

        keep = QPainterPath()
        for node in nodes:
            for d in _collect_path_d(node, inkex):
                sub = svg_d_to_qpainterpath(d)
                if hasattr(node, 'composed_transform'):
                    sub = _apply_node_transform(sub, node, inkex, QTransform)
                keep.addPath(sub)

        if keep.isEmpty():
            raise inkex.AbortExtension(
                'No path geometry found. Convert objects to paths and select them.'
            )

        opts = self.options
        defaults = {
            'mode': (getattr(opts, 'mode', None) or 'frame').strip().lower(),
            'padding': float(getattr(opts, 'padding', 4.0) or 4.0),
            'spacing': float(getattr(opts, 'spacing', 25.0) or 25.0),
            'collar': float(getattr(opts, 'collar', 4.0) or 4.0),
            'layer_name': getattr(opts, 'layer_name', None) or 'Weed lines',
        }

        from weedlines_dialog import run_weedlines_dialog

        old_out, old_err = sys.stdout, sys.stderr
        try:
            sys.stdout = open(os.devnull, 'w')
            sys.stderr = open(os.devnull, 'w')
            weed, layer_name = run_weedlines_dialog(keep, defaults=defaults)
        finally:
            try:
                sys.stdout.close()
            except Exception:
                pass
            try:
                sys.stderr.close()
            except Exception:
                pass
            sys.stdout, sys.stderr = old_out, old_err

        if weed is None:
            return

        _add_weed_layer(self.svg, inkex, PathElement, weed, layer_name)


def main():
    try:
        import inkex
    except ImportError:
        sys.stderr.write(
            'inkex not installed — this script is an Inkscape extension.\n'
            'Shared algorithms: python3 -c "from weedlib import generate_weeds"\n'
        )
        sys.exit(2)

    _ensure_weedlib_on_path()

    base = getattr(inkex, 'EffectExtension', None) or inkex.Effect

    class _Plugin(WeedLinesEffect, base):
        pass

    _Plugin().run()


if __name__ == '__main__':
    main()
