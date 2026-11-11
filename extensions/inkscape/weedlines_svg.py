# -*- coding: utf-8 -*-
"""Build / load Weedlines result SVGs (document units)."""
from __future__ import division

import os
import re
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
_READY_LABEL = 'Ready fixes'
_READY_BLOCK = re.compile(
    r'  <g id="weedlines-correction-ready" inkscape:label="Ready fixes">\n'
    r'.*?'
    r'  </g>\n',
    re.DOTALL,
)


def _qn(ns, tag):
    return '{%s}%s' % (ns, tag)


def result_svg_path():
    from weedlines_job import cache_dir
    return os.path.join(cache_dir(), 'last_result.svg')


# Inches in one of that unit. A unitless length is one px (1/96 inch).
_INCHES_PER_UNIT = {
    'px': 1.0 / 96.0,
    'in': 1.0,
    'pt': 1.0 / 72.0,
    'pc': 12.0 / 72.0,
    'mm': 1.0 / 25.4,
    'cm': 10.0 / 25.4,
    'm': 1000.0 / 25.4,
    'km': 1000000.0 / 25.4,
    'q': 0.25 / 25.4,
    'ft': 12.0,
    'yd': 36.0,
    '': 1.0 / 96.0,
}
_LENGTH_RE = re.compile(
    r'^\s*([-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][-+]?[0-9]+)?)\s*'
    r'([A-Za-z%]*)\s*$'
)
_UNIT_ATTRS = (
    'inkscape:document-units',
    '{%s}document-units' % INK_NS,
)


def _element_get(node, key):
    getter = getattr(node, 'get', None)
    if not callable(getter):
        return None
    try:
        return getter(key)
    except Exception:
        return None


def _named_display_unit(svg):
    """The unit the document names, or None.

    ``document_unit`` is not used: it fills in px and creates a namedview.
    """
    for child in _children(svg):
        tag = getattr(child, 'tag', None)
        if isinstance(tag, str) and tag.endswith('namedview'):
            unit = _unit_attr(child)
            if unit:
                return unit
    return _unit_attr(svg)


def _unit_attr(node):
    for key in _UNIT_ATTRS:
        val = _element_get(node, key)
        if val is None:
            continue
        text = str(val).strip()
        if text:
            return text
    return None


def _children(node):
    try:
        return list(node)
    except Exception:
        return []


def _length_inches(text):
    if text is None:
        return None
    match = _LENGTH_RE.match(str(text))
    if not match:
        return None
    try:
        number = float(match.group(1))
    except ValueError:
        return None
    factor = _INCHES_PER_UNIT.get(match.group(2).lower())
    if factor is None:
        return None
    return number * factor


def _viewbox_size(svg):
    raw = _element_get(svg, 'viewBox') or _element_get(svg, 'viewbox')
    if raw:
        parts = [part for part in re.split(r'[,\s]+', str(raw).strip()) if part]
        if len(parts) == 4:
            try:
                return float(parts[2]), float(parts[3])
            except ValueError:
                return None, None
    getter = getattr(svg, 'get_viewbox', None)
    if not callable(getter):
        return None, None
    try:
        vb = getter()
        if vb is not None and len(vb) == 4:
            return float(vb[2]), float(vb[3])
    except Exception:
        return None, None
    return None, None


def _user_unit_scale(svg):
    """Inches in one user unit. No absolute scale is one px."""
    width_in = _length_inches(_element_get(svg, 'width'))
    height_in = _length_inches(_element_get(svg, 'height'))
    box_w, box_h = _viewbox_size(svg)
    scales = []
    if width_in and box_w:
        scales.append(width_in / box_w)
    if height_in and box_h:
        scales.append(height_in / box_h)
    if scales:
        return max(scales)
    scale = getattr(svg, 'scale', None)
    if (isinstance(scale, (int, float)) and not isinstance(scale, bool)
            and scale > 0):
        return float(scale) / 96.0
    return 1.0 / 96.0


def doc_root_attrs(svg):
    """Capture root sizing so the result SVG matches the Inkscape document.

    ``display_unit`` is set only when the document names one.
    ``user_unit_scale`` is inches per user unit.
    """
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
    unit = _named_display_unit(svg)
    if unit:
        attrs['display_unit'] = unit
    attrs['user_unit_scale'] = _user_unit_scale(svg)
    return attrs


def cut_style(color=None):
    """Stroke for one weed cut. An omitted color is ``#FF0000``."""
    if color is None:
        color = '#FF0000'
    return (
        'fill:none;stroke:%s;stroke-width:0.25;'
        'stroke-linecap:round;stroke-linejoin:round'
    ) % color


def write_result_svg(keep_d, weed_d_list, doc_attrs=None, layer_name=None,
                     path=None, weed_line_color=None):
    """Write a standalone SVG: design keep + weed cuts in document user units.

    *doc_attrs* should be the source document's width/height/viewBox so opening
    or importing the file preserves physical size. Path coordinates are already
    in that user-unit space (composed transforms baked in). An omitted
    *weed_line_color* strokes each cut with ``#FF0000``.
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
    style = cut_style(weed_line_color)
    for i, d in enumerate(weed_d_list or ()):
        if not d:
            continue
        parts.append(
            '    <path id="weed-cut-%04d" style="%s" d="%s"/>\n'
            % (i, _xml_escape_attr(style), _xml_escape_attr(d))
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


def _label_fields(label):
    """Text, color, and point from a mark. No origin is computed here."""
    if isinstance(label, dict):
        text = label.get('text')
        color = label.get('color')
        point = label.get('point')
    else:
        text = getattr(label, 'text', None)
        color = getattr(label, 'color', None)
        point = getattr(label, 'point', None)
    if text is None or point is None:
        return None
    if isinstance(point, (tuple, list)) and len(point) >= 2:
        x, y = point[0], point[1]
    else:
        x = getattr(point, 'x', None)
        y = getattr(point, 'y', None)
        if callable(x):
            x, y = x(), y()
    return text, color, float(x), float(y)


def _label_for_text(text, labels):
    for label in labels or ():
        fields = _label_fields(label)
        if fields is not None and fields[0] == text:
            return fields
    return None


def _xml_escape_text(value):
    return (
        str(value)
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
    )


def _correction_text(kind, text, color, x, y):
    style = 'fill:%s;stroke:none' % color
    return (
        '    <text id="%s" x="%s" y="%s" style="%s">%s</text>\n'
        % (
            _correction_path_id(kind, 'label', 0),
            _xml_escape_attr(x),
            _xml_escape_attr(y),
            _xml_escape_attr(style),
            _xml_escape_text(text),
        )
    )


def write_correction_svg(arrows, doc_attrs=None, path=None, labels=None):
    """Write one group per kind that has an arrow. No design copy.

    *arrows* maps dangling, overlap, or self-overlap to objects with
    shaft, head, and color. Shaft and head are ``QPainterPath`` values.
    *labels* are the marks for those kinds. Each present kind gets one
    text element at that mark's point, in that mark's color.
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
        mark = _label_for_text(label, labels)
        if mark is not None:
            text, color, x, y = mark
            if not color and batch:
                color = batch[0].color
            body.append(_correction_text(kind, text, color, x, y))
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


def write_ready_fixes(paths, path=None):
    """Add one Ready fixes group of approved replacement paths.

    Arrow groups already in the ready file stay. An empty *paths*
    does not add the group and does not create a file. A later call
    replaces the previous Ready fixes group.
    """
    if path is None:
        from weedlines_job import ready_svg_file
        path = ready_svg_file()
    data = _ready_ds(paths)
    if not data or not os.path.isfile(path):
        return path
    with open(path, encoding='utf-8') as fh:
        text = fh.read()
    text = _READY_BLOCK.sub('', text)
    index = text.rfind('</svg>')
    if index < 0:
        return path
    text = text[:index] + _ready_group(data) + text[index:]
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        fh.write(text)
    os.replace(tmp, path)
    return path


def _ready_ds(paths):
    convert = None
    found = []
    for item in paths or ():
        if item is None:
            continue
        if isinstance(item, str):
            text = item.strip()
        else:
            if convert is None:
                from weedlib.svg_paths import qpainterpath_to_svg_d
                convert = qpainterpath_to_svg_d
            text = convert(item, close_subpaths=False)
        if text:
            found.append(text)
    return found


def _ready_group(data):
    style = _xml_escape_attr('fill:none;stroke:#000000;stroke-width:0.25')
    lines = [
        '  <g id="weedlines-correction-ready" '
        'inkscape:label="Ready fixes">\n',
    ]
    for index, d in enumerate(data):
        lines.append(
            '    <path id="weedlines-ready-%04d" style="%s" d="%s"/>\n'
            % (index, style, _xml_escape_attr(d))
        )
    lines.append('  </g>\n')
    return ''.join(lines)


def load_correction_svg_groups(path=None):
    """Return ready-file groups, in document order.

    Arrow groups for each kind that had an arrow, and the Ready
    fixes group when the file has one. A missing file, or a
    design-plus-cuts file, returns an empty list.
    """
    path = path or result_svg_path()
    if not os.path.isfile(path):
        return []
    labels = {label for _kind, label in _CORRECTION_KINDS}
    labels.add(_READY_LABEL)
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
