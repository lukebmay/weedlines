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


def _is_svg_path_element(node, inkex):
    tag = (
        inkex.addNS('path', 'svg') if hasattr(inkex, 'addNS')
        else '{http://www.w3.org/2000/svg}path'
    )
    return (
        node.tag == tag
        or (isinstance(node.tag, str) and node.tag.endswith('}path'))
        or (isinstance(node.tag, str) and node.tag == 'path')
    )


def _iter_path_elements(node, inkex):
    """Yield every ``svg:path`` element under *node* (including *node*)."""
    if _is_svg_path_element(node, inkex):
        yield node
    for child in list(node):
        for el in _iter_path_elements(child, inkex):
            yield el


def _apply_node_transform(path, node, inkex, QTransform):
    """Map *path* by this element's composed transform (document user units)."""
    try:
        t = node.composed_transform()
        m = t.matrix if hasattr(t, 'matrix') else None
        if m is None:
            return path
        # inkex: ((a, c, e), (b, d, f)) — SVG matrix(a,b,c,d,e,f)
        a, c, e = m[0]
        b, d, f = m[1]
        qt = QTransform(a, b, c, d, e, f)
        return qt.map(path)
    except Exception:
        return path


def _keep_path_from_selection(nodes, inkex, QPainterPath, QTransform):
    """Build keep geometry in document user units.

    Each path element uses *its own* ``composed_transform()`` so nested
    group scales/translates are not dropped (that was shifting/sizing
    imports wrong when a parent/group/svg was selected).
    """
    from weedlib.svg_paths import svg_d_to_qpainterpath

    keep = QPainterPath()
    for root in nodes:
        for el in _iter_path_elements(root, inkex):
            d = el.get('d')
            if not d:
                continue
            sub = svg_d_to_qpainterpath(d)
            if sub.isEmpty():
                continue
            sub = _apply_node_transform(sub, el, inkex, QTransform)
            keep.addPath(sub)
    return keep


def _add_weed_layer_from_d(svg, inkex, PathElement, d_list, layer_label):
    """Write open SVG path `d` strings into a new Weedlines layer."""
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


def _add_weed_layer(svg, inkex, PathElement, weed_path, layer_label):
    from weedlib.svg_paths import weed_path_to_open_d_list

    d_list = weed_path_to_open_d_list(weed_path)
    _add_weed_layer_from_d(svg, inkex, PathElement, d_list, layer_label)


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

        _ensure_weedlib_on_path()

        ext_dir = os.path.abspath(os.path.dirname(__file__))
        if ext_dir not in sys.path:
            sys.path.insert(0, ext_dir)

        nodes = list(self.svg.selection.values()) if self.svg.selection else []
        if not nodes:
            nodes = [self.svg]

        opts = self.options
        defaults = {
            'mode': (getattr(opts, 'mode', None) or 'frame').strip().lower(),
            'padding': float(getattr(opts, 'padding', 4.0) or 4.0),
            'spacing': float(getattr(opts, 'spacing', 25.0) or 25.0),
            'collar': float(getattr(opts, 'collar', 4.0) or 4.0),
            'layer_name': getattr(opts, 'layer_name', None) or 'Weed lines',
        }

        try:
            from weedlib.qt import QPainterPath, QTransform
        except ImportError as exc:
            raise inkex.AbortExtension(
                'weedlib / Qt not available: {}'.format(exc)
            )

        from weedlib.svg_paths import qpainterpath_to_svg_d
        from weedlines_job import write_job, spawn_host
        from weedlines_svg import doc_root_attrs

        keep = _keep_path_from_selection(
            nodes, inkex, QPainterPath, QTransform)

        if keep.isEmpty():
            raise inkex.AbortExtension(
                'No path geometry found. Convert objects to paths '
                'and select them.'
            )

        doc_attrs = doc_root_attrs(self.svg)
        br = keep.boundingRect()
        defaults['keep_bbox'] = [
            br.x(), br.y(), br.width(), br.height(),
        ]

        # Default: detach so Inkscape's main thread is free. Set
        # WEEDLINES_INLINE=1 to keep the old in-process blocking dialog.
        inline = os.environ.get('WEEDLINES_INLINE', '').strip() in (
            '1', 'true', 'yes', 'on')
        if not inline:
            keep_d = qpainterpath_to_svg_d(keep, close_subpaths=True)
            job_path = write_job(
                keep_d, defaults, doc_attrs=doc_attrs)
            # Keep Inkscape's stderr clean — any chatter becomes the
            # "additional data from the script" dialog.
            old_err = sys.stderr
            try:
                sys.stderr = open(os.devnull, 'w')
                try:
                    spawn_host(job_path)
                except Exception as exc:
                    sys.stderr = old_err
                    raise inkex.AbortExtension(
                        'Could not start Weedlines window: {}'.format(exc)
                    )
            finally:
                try:
                    if sys.stderr is not old_err:
                        sys.stderr.close()
                except Exception:
                    pass
                sys.stderr = old_err
            # Return immediately so Inkscape unblocks; the host window is
            # already open. After Apply there: Import last result.
            return

        # Legacy in-process path (blocks Inkscape until the dialog closes).
        from stdio_capture import NativeStdioCapture
        from inkex import PathElement
        from weedlines_dialog import run_weedlines_dialog

        old_out, old_err = sys.stdout, sys.stderr
        null_out = open(os.devnull, 'w')
        null_err = open(os.devnull, 'w')
        weed, layer_name = None, None
        try:
            sys.stdout = null_out
            sys.stderr = null_err
            with NativeStdioCapture() as capture:
                weed, layer_name = run_weedlines_dialog(
                    keep, defaults=defaults,
                    platform_lines=capture.lines)
        finally:
            sys.stdout, sys.stderr = old_out, old_err
            try:
                null_out.close()
            except Exception:
                pass
            try:
                null_err.close()
            except Exception:
                pass

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
