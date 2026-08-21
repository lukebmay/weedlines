# -*- coding: utf-8 -*-
"""Build / load the Weedlines result SVG (design + cuts, document units)."""
from __future__ import division

import os
from xml.etree import ElementTree as ET

SVG_NS = 'http://www.w3.org/2000/svg'
INK_NS = 'http://www.inkscape.org/namespaces/inkscape'
SOD_NS = 'http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd'

ET.register_namespace('', SVG_NS)
ET.register_namespace('inkscape', INK_NS)
ET.register_namespace('sodipodi', SOD_NS)


def _qn(ns, tag):
    return '{%s}%s' % (ns, tag)


def result_svg_path():
    from weedlines_job import cache_dir
    return os.path.join(cache_dir(), 'last_result.svg')


def doc_root_attrs(svg):
    """Capture root sizing so the result SVG matches the Inkscape document."""
    attrs = {}
    for key in ('width', 'height', 'viewBox', 'viewbox'):
        val = svg.get(key) if hasattr(svg, 'get') else None
        if val:
            # Normalize to viewBox spelling used in SVG.
            attrs['viewBox' if key.lower() == 'viewbox' else key] = val
    # Prefer explicit viewBox from inkex if attribute missing.
    if 'viewBox' not in attrs:
        try:
            vb = svg.get_viewbox()
            if vb is not None and len(vb) == 4:
                attrs['viewBox'] = '%g %g %g %g' % tuple(vb)
        except Exception:
            pass
    if 'width' not in attrs:
        try:
            w = svg.viewport_width
            if w:
                attrs['width'] = str(w)
        except Exception:
            pass
    if 'height' not in attrs:
        try:
            h = svg.viewport_height
            if h:
                attrs['height'] = str(h)
        except Exception:
            pass
    return attrs


def write_result_svg(keep_d, weed_d_list, doc_attrs=None, layer_name=None,
                     path=None):
    """Write a standalone SVG: design keep + weed cuts in document user units.

    *doc_attrs* should be the source document's width/height/viewBox so opening
    or importing the file preserves physical size. Path coordinates are already
    in that user-unit space (composed transforms baked in).
    """
    path = path or result_svg_path()
    doc_attrs = dict(doc_attrs or {})
    layer_name = layer_name or 'Weed lines'

    # Build as a plain string to control namespaces cleanly (ElementTree
    # register_namespace + explicit xmlns duplicates attributes).
    width = doc_attrs.get('width') or ''
    height = doc_attrs.get('height') or ''
    view_box = doc_attrs.get('viewBox') or doc_attrs.get('viewbox') or ''
    if not view_box and not width:
        width = width or '100%'
        height = height or '100%'

    parts = [
        "<?xml version='1.0' encoding='utf-8'?>\n",
        '<svg xmlns="%s" xmlns:inkscape="%s"' % (SVG_NS, INK_NS),
    ]
    if width:
        parts.append(' width="%s"' % _xml_escape_attr(width))
    if height:
        parts.append(' height="%s"' % _xml_escape_attr(height))
    if view_box:
        parts.append(' viewBox="%s"' % _xml_escape_attr(view_box))
    parts.append('>\n')

    parts.append(
        '  <g inkscape:label="Weedlines design" id="weedlines-design">\n'
    )
    if keep_d:
        parts.append(
            '    <path id="weedlines-keep" fill-rule="evenodd" '
            'style="fill:#9a9a9a;fill-opacity:1;fill-rule:evenodd;'
            'stroke:#666666;stroke-width:0.25;stroke-opacity:1" d="%s"/>\n'
            % _xml_escape_attr(keep_d)
        )
    parts.append('  </g>\n')

    parts.append(
        '  <g inkscape:groupmode="layer" inkscape:label="%s" '
        'id="weedlines-cuts">\n'
        % _xml_escape_attr(layer_name)
    )
    style = (
        'fill:none;stroke:#c04000;stroke-width:0.25;'
        'stroke-linecap:round;stroke-linejoin:round'
    )
    for i, d in enumerate(weed_d_list or ()):
        if not d:
            continue
        parts.append(
            '    <path id="weed-cut-%04d" style="%s" d="%s"/>\n'
            % (i, style, _xml_escape_attr(d))
        )
    parts.append('  </g>\n</svg>\n')

    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        fh.write(''.join(parts))
    os.replace(tmp, path)
    return path


def _xml_escape_attr(value):
    return (
        str(value)
        .replace('&', '&amp;')
        .replace('"', '&quot;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
    )


def load_result_svg_groups(path=None):
    """Return (design_element_or_None, cuts_element_or_None) from result SVG."""
    path = path or result_svg_path()
    if not os.path.isfile(path):
        return None, None
    tree = ET.parse(path)
    root = tree.getroot()
    design = cuts = None
    for child in list(root):
        tag = child.tag
        if not isinstance(tag, str):
            continue
        cid = child.get('id') or ''
        label = child.get(_qn(INK_NS, 'label')) or ''
        if cid == 'weedlines-design' or label == 'Weedlines design':
            design = child
        elif cid == 'weedlines-cuts' or child.get(_qn(INK_NS, 'groupmode')) == 'layer':
            cuts = child
    return design, cuts
