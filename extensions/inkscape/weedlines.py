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
import re
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


_INKSCAPE_LABEL = '{http://www.inkscape.org/namespaces/inkscape}label'
_CORRECTION_LABEL = 'Weedlines corrections'
_CORRECTION_ID_PREFIX = 'weedlines-correction'

_PATH_TOKEN_RE = re.compile(
    r'([MmLlHhVvCcSsQqTtAaZz])|'
    r'([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)'
)
_PATH_ARITY = {
    'M': 2, 'L': 2, 'H': 1, 'V': 1, 'C': 6, 'S': 4,
    'Q': 4, 'T': 2, 'A': 7, 'Z': 0,
}


def _load_named_colors():
    raw = (
        'aliceblue:f0f8ff antiquewhite:faebd7 aqua:00ffff aquamarine:7fffd4 '
        'azure:f0ffff beige:f5f5dc bisque:ffe4c4 black:000000 '
        'blanchedalmond:ffebcd blue:0000ff blueviolet:8a2be2 brown:a52a2a '
        'burlywood:deb887 cadetblue:5f9ea0 chartreuse:7fff00 '
        'chocolate:d2691e coral:ff7f50 cornflowerblue:6495ed '
        'cornsilk:fff8dc crimson:dc143c cyan:00ffff darkblue:00008b '
        'darkcyan:008b8b darkgoldenrod:b8860b darkgray:a9a9a9 '
        'darkgreen:006400 darkgrey:a9a9a9 darkkhaki:bdb76b '
        'darkmagenta:8b008b darkolivegreen:556b2f darkorange:ff8c00 '
        'darkorchid:9932cc darkred:8b0000 darksalmon:e9967a '
        'darkseagreen:8fbc8f darkslateblue:483d8b darkslategray:2f4f4f '
        'darkslategrey:2f4f4f darkturquoise:00ced1 darkviolet:9400d3 '
        'deeppink:ff1493 deepskyblue:00bfff dimgray:696969 dimgrey:696969 '
        'dodgerblue:1e90ff firebrick:b22222 floralwhite:fffaf0 '
        'forestgreen:228b22 fuchsia:ff00ff gainsboro:dcdcdc '
        'ghostwhite:f8f8ff gold:ffd700 goldenrod:daa520 gray:808080 '
        'green:008000 greenyellow:adff2f grey:808080 honeydew:f0fff0 '
        'hotpink:ff69b4 indianred:cd5c5c indigo:4b0082 ivory:fffff0 '
        'khaki:f0e68c lavender:e6e6fa lavenderblush:fff0f5 '
        'lawngreen:7cfc00 lemonchiffon:fffacd lightblue:add8e6 '
        'lightcoral:f08080 lightcyan:e0ffff lightgoldenrodyellow:fafad2 '
        'lightgray:d3d3d3 lightgreen:90ee90 lightgrey:d3d3d3 '
        'lightpink:ffb6c1 lightsalmon:ffa07a lightseagreen:20b2aa '
        'lightskyblue:87cefa lightslategray:778899 lightslategrey:778899 '
        'lightsteelblue:b0c4de lightyellow:ffffe0 lime:00ff00 '
        'limegreen:32cd32 linen:faf0e6 magenta:ff00ff maroon:800000 '
        'mediumaquamarine:66cdaa mediumblue:0000cd mediumorchid:ba55d3 '
        'mediumpurple:9370db mediumseagreen:3cb371 '
        'mediumslateblue:7b68ee mediumspringgreen:00fa9a '
        'mediumturquoise:48d1cc mediumvioletred:c71585 '
        'midnightblue:191970 mintcream:f5fffa mistyrose:ffe4e1 '
        'moccasin:ffe4b5 navajowhite:ffdead navy:000080 oldlace:fdf5e6 '
        'olive:808000 olivedrab:6b8e23 orange:ffa500 orangered:ff4500 '
        'orchid:da70d6 palegoldenrod:eee8aa palegreen:98fb98 '
        'paleturquoise:afeeee palevioletred:db7093 papayawhip:ffefd5 '
        'peachpuff:ffdab9 peru:cd853f pink:ffc0cb plum:dda0dd '
        'powderblue:b0e0e6 purple:800080 rebeccapurple:663399 red:ff0000 '
        'rosybrown:bc8f8f royalblue:4169e1 saddlebrown:8b4513 '
        'salmon:fa8072 sandybrown:f4a460 seagreen:2e8b57 seashell:fff5ee '
        'sienna:a0522d silver:c0c0c0 skyblue:87ceeb slateblue:6a5acd '
        'slategray:708090 slategrey:708090 snow:fffafa springgreen:00ff7f '
        'steelblue:4682b4 tan:d2b48c teal:008080 thistle:d8bfd8 '
        'tomato:ff6347 turquoise:40e0d0 violet:ee82ee wheat:f5deb3 '
        'white:ffffff whitesmoke:f5f5f5 yellow:ffff00 yellowgreen:9acd32'
    )
    colors = {}
    for item in raw.split():
        name, hex6 = item.split(':')
        colors[name] = (
            int(hex6[0:2], 16),
            int(hex6[2:4], 16),
            int(hex6[4:6], 16),
        )
    return colors


_NAMED_COLORS = _load_named_colors()


def _parent_of(node):
    if node is None:
        return None
    getparent = getattr(node, 'getparent', None)
    if callable(getparent):
        try:
            return getparent()
        except Exception:
            return None
    parent = getattr(node, 'parent', None)
    if parent is node:
        return None
    return parent


def _walk_up(node):
    seen = set()
    current = node
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        current = _parent_of(current)


def _group_label(node):
    if not hasattr(node, 'get'):
        return ''
    for key in (_INKSCAPE_LABEL, 'inkscape:label'):
        val = node.get(key)
        if val:
            return str(val).strip()
    return ''


def _omitted_correction(node):
    """Arrows imported earlier are not design paths."""
    ident = ''
    if hasattr(node, 'get') and node.get('id') is not None:
        ident = str(node.get('id'))
    if ident.startswith(_CORRECTION_ID_PREFIX):
        return True
    for ancestor in _walk_up(node):
        if _group_label(ancestor) == _CORRECTION_LABEL:
            return True
    return False


def _style_declarations(element):
    if not hasattr(element, 'get'):
        return {}
    raw = element.get('style')
    if raw is None or raw == '':
        return {}
    if not isinstance(raw, str):
        if hasattr(raw, 'items'):
            return {
                str(key).strip().lower(): str(val).strip()
                for key, val in raw.items()
                if str(val).strip()
            }
        raw = str(raw)
    return _parse_style_attribute(raw)


def _parse_style_attribute(style):
    decls = {}
    depth = 0
    buf = []
    parts = []
    for ch in style:
        if ch == '(':
            depth += 1
            buf.append(ch)
        elif ch == ')':
            depth = max(0, depth - 1)
            buf.append(ch)
        elif ch == ';' and depth == 0:
            parts.append(''.join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append(''.join(buf))
    for part in parts:
        if ':' not in part:
            continue
        key, value = part.split(':', 1)
        key = key.strip().lower()
        value = value.strip()
        if value.lower().endswith('!important'):
            value = value[:-10].strip()
        if key and value:
            decls[key] = value
    return decls


def _local_value(node, prop):
    if node is None or not hasattr(node, 'get'):
        return None
    styles = _style_declarations(node)
    if prop in styles and styles[prop].strip():
        return styles[prop].strip()
    raw = node.get(prop)
    if raw is None:
        return None
    value = str(raw).strip()
    return value or None


def _computed_inherited(node, prop, initial):
    for ancestor in _walk_up(node):
        val = _local_value(ancestor, prop)
        if val is not None and val.lower() != 'inherit':
            return val
    return initial


def _unit_interval(value):
    text = str(value).strip()
    try:
        if text.endswith('%'):
            number = float(text[:-1]) / 100.0
        else:
            number = float(text)
    except ValueError:
        return 1.0
    if number < 0.0:
        return 0.0
    if number > 1.0:
        return 1.0
    return number


def _stacked_opacity(node):
    """Product of opacity from this element through its ancestors."""
    product = 1.0
    for ancestor in _walk_up(node):
        val = _local_value(ancestor, 'opacity')
        if val is None or val.lower() == 'inherit':
            continue
        product *= _unit_interval(val)
        if product <= 0.0:
            return 0.0
    return product


def _opacity_is_zero(element):
    fill_opacity = _unit_interval(
        _computed_inherited(element, 'fill-opacity', '1'))
    if fill_opacity <= 0.0:
        return True
    return _stacked_opacity(element) <= 0.0


def _parse_hex_color(body):
    h = body.strip()
    if len(h) not in (3, 4, 6, 8):
        return None
    if any(c not in '0123456789abcdefABCDEF' for c in h):
        return None
    original = len(h)
    if original in (3, 4):
        h = ''.join(ch * 2 for ch in h)
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    if original in (4, 8):
        a = int(h[6:8], 16) / 255.0
    else:
        a = 1.0
    return r, g, b, a


def _color_args(body):
    body = body.strip()
    alpha = None
    if '/' in body:
        body, alpha = body.split('/', 1)
    parts = body.replace(',', ' ').split()
    if alpha is not None:
        parts.append(alpha.strip())
    return parts


def _channel_byte(text):
    text = text.strip()
    if text.endswith('%'):
        number = float(text[:-1]) / 100.0 * 255.0
    else:
        number = float(text)
    if number < 0.0:
        number = 0.0
    if number > 255.0:
        number = 255.0
    return int(round(number))


def _fraction(text):
    text = text.strip()
    if text.endswith('%'):
        number = float(text[:-1]) / 100.0
    else:
        number = float(text)
    if number < 0.0:
        return 0.0
    if number > 1.0:
        return 1.0
    return number


def _hue_degrees(text):
    text = text.strip().lower()
    if text.endswith('deg'):
        text = text[:-3]
    if text.endswith('%'):
        return float(text[:-1]) / 100.0 * 360.0
    return float(text)


def _hsl_to_rgb(hue, sat, light):
    hue = hue % 360.0
    chroma = (1.0 - abs(2.0 * light - 1.0)) * sat
    sector = hue / 60.0
    x = chroma * (1.0 - abs(sector % 2.0 - 1.0))
    m = light - chroma / 2.0
    if sector < 1:
        r1, g1, b1 = chroma, x, 0.0
    elif sector < 2:
        r1, g1, b1 = x, chroma, 0.0
    elif sector < 3:
        r1, g1, b1 = 0.0, chroma, x
    elif sector < 4:
        r1, g1, b1 = 0.0, x, chroma
    elif sector < 5:
        r1, g1, b1 = x, 0.0, chroma
    else:
        r1, g1, b1 = chroma, 0.0, x

    def byte(channel):
        value = max(0.0, min(1.0, channel + m))
        return int(round(value * 255.0))

    return byte(r1), byte(g1), byte(b1)


def _parse_color(text):
    raw = str(text).strip()
    low = raw.lower()
    if low in _NAMED_COLORS:
        r, g, b = _NAMED_COLORS[low]
        return r, g, b, 1.0
    if raw.startswith('#'):
        return _parse_hex_color(raw[1:])
    match = re.match(r'^(rgba?|hsla?)\((.*)\)\s*$', low, re.DOTALL)
    if not match:
        return None
    kind, body = match.group(1), match.group(2)
    parts = _color_args(body)
    try:
        if kind in ('rgb', 'rgba'):
            if len(parts) not in (3, 4):
                return None
            r = _channel_byte(parts[0])
            g = _channel_byte(parts[1])
            b = _channel_byte(parts[2])
            a = _fraction(parts[3]) if len(parts) == 4 else 1.0
            return r, g, b, a
        if kind in ('hsl', 'hsla'):
            if len(parts) not in (3, 4):
                return None
            hue = _hue_degrees(parts[0])
            sat = _fraction(parts[1])
            light = _fraction(parts[2])
            a = _fraction(parts[3]) if len(parts) == 4 else 1.0
            r, g, b = _hsl_to_rgb(hue, sat, light)
            return r, g, b, a
    except ValueError:
        return None
    return None


def _classify_paint(value, node):
    text = ' '.join(str(value).split())
    low = text.lower()
    if low in ('none', 'transparent'):
        return 'none'
    if 'url(' in low:
        return 'other'
    if low in ('context-fill', 'context-stroke'):
        return 'other'
    if low == 'currentcolor':
        color = _computed_inherited(node, 'color', '#000000')
        if str(color).strip().lower() == 'currentcolor':
            color = '#000000'
        text = ' '.join(str(color).split())
        low = text.lower()
        if low in ('none', 'transparent'):
            return 'none'
        if 'url(' in low or low in ('context-fill', 'context-stroke'):
            return 'other'
    rgb = _parse_color(text)
    if rgb is None:
        return 'other'
    r, g, b, a = rgb
    if a <= 0.0:
        return 'none'
    return '#{:02x}{:02x}{:02x}'.format(r, g, b)


def _computed_fill(element):
    """Resolved paint: ``none``, ``#rrggbb``, or ``other``. Opacity 0 is none."""
    if _opacity_is_zero(element):
        return 'none'
    paint = _computed_inherited(element, 'fill', '#000000')
    return _classify_paint(paint, element)


def _path_tokens(d):
    for match in _PATH_TOKEN_RE.finditer(d or ''):
        cmd, num = match.group(1), match.group(2)
        if cmd:
            yield cmd
        else:
            yield float(num)


def _subpath_closed_flags(d):
    """One flag per subpath, True when that subpath's data has a closepath."""
    tokens = list(_path_tokens(d))
    flags = []
    i = 0
    have = False
    closed = False
    last = ''

    def finish():
        nonlocal have, closed
        if have:
            flags.append(closed)
        have = False
        closed = False

    while i < len(tokens):
        tok = tokens[i]
        if isinstance(tok, str):
            i += 1
            cmd = tok
        elif last in ('M', 'm'):
            cmd = 'L' if last == 'M' else 'l'
        elif last in ('Z', 'z', ''):
            break
        else:
            cmd = last
        if have and last in ('Z', 'z') and cmd not in ('M', 'm', 'Z', 'z'):
            finish()
            have = True
        if cmd in ('M', 'm'):
            if have:
                finish()
            have = True
            closed = False
        elif cmd in ('Z', 'z'):
            if not have:
                have = True
            closed = True
            last = cmd
            continue
        need = _PATH_ARITY.get(cmd.upper())
        if need is None or i + need > len(tokens):
            break
        if any(isinstance(tokens[i + k], str) for k in range(need)):
            break
        i += need
        if not have:
            have = True
        last = cmd
    finish()
    return flags


def _d_with_source_closepaths(path, closed_flags):
    """Serialize *path* without adding a closepath the source did not have."""
    from weedlib.paths import split_painter_path
    from weedlib.svg_paths import qpainterpath_to_svg_d

    subs = split_painter_path(path)
    if len(closed_flags) != len(subs):
        closed_flags = [
            bool(closed_flags[i]) if i < len(closed_flags) else False
            for i in range(len(subs))
        ]
    parts = []
    flags = []
    for sub, flag in zip(subs, closed_flags):
        piece = qpainterpath_to_svg_d(sub, close_subpaths=False)
        if not piece:
            continue
        if flag:
            piece += ' Z'
        parts.append(piece)
        flags.append(bool(flag))
    if not parts:
        return None
    return ' '.join(parts), flags


def _record_from_element(element, QTransform):
    raw = element.get('d') if hasattr(element, 'get') else None
    if raw is None or not str(raw).strip():
        return None
    raw = str(raw)
    from weedlib.svg_paths import svg_d_to_qpainterpath

    path = svg_d_to_qpainterpath(raw)
    if path.isEmpty():
        return None
    path = _apply_node_transform(path, element, None, QTransform)
    if path.isEmpty():
        return None
    rendered = _d_with_source_closepaths(path, _subpath_closed_flags(raw))
    if rendered is None:
        return None
    d, closed = rendered
    ident = element.get('id') if hasattr(element, 'get') else None
    return {
        'id': '' if ident is None else str(ident),
        'd': d,
        'closed': closed,
        'fill': _computed_fill(element),
    }


def _path_records(nodes, inkex, QTransform):
    """One record per path element, in document user units."""
    records = []
    for root in nodes:
        for element in _iter_path_elements(root, inkex):
            if _omitted_correction(element):
                continue
            record = _record_from_element(element, QTransform)
            if record is not None:
                records.append(record)
    return records


def _add_weed_layer_from_d(svg, inkex, PathElement, d_list, layer_label,
                           color=None):
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

    from weedlines_svg import cut_style
    style = cut_style(color)
    for i, d in enumerate(d_list):
        el = PathElement()
        el.set('d', d)
        el.set('style', style)
        el.set('id', 'weed-cut-{:04d}'.format(i))
        layer.append(el)


def _add_weed_layer(svg, inkex, PathElement, weed_path, layer_label,
                    color=None):
    from weedlib.svg_paths import weed_path_to_open_d_list

    d_list = weed_path_to_open_d_list(weed_path)
    _add_weed_layer_from_d(
        svg, inkex, PathElement, d_list, layer_label, color)


_UNCHOSEN_MODE = 'Surround and Conquer'


def _mode_on_job(raw):
    """Mode on the job. Missing or blank is not lowercased."""
    text = raw.strip() if isinstance(raw, str) else ''
    return text or _UNCHOSEN_MODE


class WeedLinesEffect(object):
    """inkex.EffectExtension body (mixed into a subclass of EffectExtension)."""

    def add_arguments(self, pars):
        pars.add_argument('--tab', type=str, default='')
        pars.add_argument('--mode', type=str, default=_UNCHOSEN_MODE)
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
            'mode': _mode_on_job(getattr(opts, 'mode', None)),
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

        records = _path_records(nodes, inkex, QTransform)
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
                keep_d, defaults, doc_attrs=doc_attrs, records=records)
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
        weed, layer_name, color = None, None, None
        try:
            sys.stdout = null_out
            sys.stderr = null_err
            with NativeStdioCapture() as capture:
                weed, layer_name, color = run_weedlines_dialog(
                    records,
                    defaults=defaults,
                    platform_lines=capture.lines,
                    width=doc_attrs.get('width'),
                    height=doc_attrs.get('height'),
                    view_box=(
                        doc_attrs.get('viewBox') or doc_attrs.get('viewbox')),
                )
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

        _add_weed_layer(
            self.svg, inkex, PathElement, weed, layer_name, color)


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
