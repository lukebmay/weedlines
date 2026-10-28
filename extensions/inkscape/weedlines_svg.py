# -*- coding: utf-8 -*-
"""Build / load Weedlines result SVGs (document units)."""
from __future__ import division

import os
from xml.etree import ElementTree as ET

SVG_NS = 'http://www.w3.org/2000/svg'
INK_NS = 'http://www.inkscape.org/namespaces/inkscape'
SOD_NS = 'http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd'

ET.register_namespace('', SVG_NS)
ET.register_namespace('inkscape', INK_NS)
ET.register_namespace('sodipodi', SOD_NS)

# Result groups, in the order the guide names them. An empty kind is omitted.
_CORRECTION_KINDS = (
    ('dangling', 'Dangling ends'),
    ('overlap', 'Figure overlaps'),
    ('self-overlap', 'Self-overlaps'),
)


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


def _local_tag(tag):
    if not isinstance(tag, str):
        return ''
    return tag.rsplit('}', 1)[-1]


def _correction_rows(arrows):
    """Kinds that have at least one arrow, in guide order."""
    if arrows is None:
        arrows = {}
    if not isinstance(arrows, dict):
        raise TypeError(
            'arrows must map a kind to arrow paths, got: {}'.format(
                type(arrows).__name__))
    known = {kind for kind, _label in _CORRECTION_KINDS}
    unknown = [key for key in arrows if key not in known]
    if unknown:
        raise ValueError('unknown arrow kind: {!r}'.format(unknown[0]))
    rows = []
    for kind, label in _CORRECTION_KINDS:
        batch = [
            arrow for arrow in (arrows.get(kind) or ()) if arrow is not None
        ]
        if batch:
            rows.append((kind, label, batch))
    return rows


def _correction_path_id(kind, role, index):
    return 'weedlines-correction-%s-%s-%04d' % (kind, role, index)


def _shaft_style(color):
    # Same user-unit width as the weed-line strokes. The guide names none.
    return 'fill:none;stroke:%s;stroke-width:0.25' % color


def _head_style(color):
    return 'fill:%s;stroke:none' % color


def write_correction_svg(arrows, doc_attrs=None, path=None):
    """Write one group per kind that has an arrow. No design copy.

    *arrows* maps dangling, overlap, or self-overlap to objects with
    shaft, head, and color. Shaft and head are ``QPainterPath`` values.
    """
    from weedlib.svg_paths import qpainterpath_to_svg_d

    path = path or result_svg_path()
    doc_attrs = dict(doc_attrs or {})
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

    for kind, label, batch in _correction_rows(arrows):
        body = []
        for index, arrow in enumerate(batch):
            # close_subpaths would add Z and close an open shaft.
            shaft_d = qpainterpath_to_svg_d(
                arrow.shaft, close_subpaths=False)
            head_d = qpainterpath_to_svg_d(arrow.head, close_subpaths=False)
            color = arrow.color
            if shaft_d:
                body.append(
                    '    <path id="%s" style="%s" d="%s"/>\n' % (
                        _correction_path_id(kind, 'shaft', index),
                        _xml_escape_attr(_shaft_style(color)),
                        _xml_escape_attr(shaft_d),
                    )
                )
            if head_d:
                body.append(
                    '    <path id="%s" style="%s" d="%s"/>\n' % (
                        _correction_path_id(kind, 'head', index),
                        _xml_escape_attr(_head_style(color)),
                        _xml_escape_attr(head_d),
                    )
                )
        if not body:
            continue
        parts.append(
            '  <g id="weedlines-correction-%s" inkscape:label="%s">\n'
            % (kind, _xml_escape_attr(label))
        )
        parts.extend(body)
        parts.append('  </g>\n')
    parts.append('</svg>\n')

    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        fh.write(''.join(parts))
    os.replace(tmp, path)
    return path


def load_correction_svg_groups(path=None):
    """Return correction arrow groups, in document order.

    Each item is the group for one kind that had an arrow. A missing
    file, or a design-plus-cuts file, returns an empty list.
    """
    path = path or result_svg_path()
    if not os.path.isfile(path):
        return []
    labels = {label for _kind, label in _CORRECTION_KINDS}
    groups = []
    root = ET.parse(path).getroot()
    for child in list(root):
        if _local_tag(child.tag) != 'g':
            continue
        label = child.get(_qn(INK_NS, 'label')) or ''
        cid = child.get('id') or ''
        if label in labels or cid.startswith('weedlines-correction'):
            groups.append(child)
    return groups
