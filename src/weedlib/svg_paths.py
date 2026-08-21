# -*- coding: utf-8 -*-
"""SVG path `d` ↔ QPainterPath edge conversion (mm user units).

Open weed cuts become stroked path elements (not filled faces).
Coordinates are in the same user units as the document (Inkscape
mm documents stay in mm when `viewBox` / document units match).
"""
from __future__ import division

import re

from .qt import QPainterPath, QPointF, QTransform


_CMD_RE = re.compile(
    r'([MmLlHhVvCcSsQqTtAaZz])|'
    r'([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)'
)


def _tokens(d):
    for m in _CMD_RE.finditer(d or ''):
        cmd, num = m.group(1), m.group(2)
        if cmd:
            yield cmd
        else:
            yield float(num)


def svg_d_to_qpainterpath(d):
    """Parse an SVG path `d` string into a QPainterPath.

    Supports M/L/H/V/C/S/Q/T/Z (absolute and relative). Arcs (A/a) are
    linearized via lineTo of the endpoint (hosts should convert arcs
    first when accuracy matters).
    """
    path = QPainterPath()
    if not d:
        return path
    tokens = list(_tokens(d))
    i = 0
    cx = cy = 0.0
    sx = sy = 0.0
    last_cmd = ''
    x1 = y1 = 0.0  # last control for smooth curves

    def take(n):
        nonlocal i
        vals = tokens[i:i + n]
        i += n
        if len(vals) < n:
            raise ValueError('incomplete SVG path command')
        return vals

    while i < len(tokens):
        t = tokens[i]
        if not isinstance(t, str):
            # implicit repeat of last command
            if last_cmd in ('M', 'm'):
                cmd = 'L' if last_cmd == 'M' else 'l'
            else:
                cmd = last_cmd
        else:
            i += 1
            cmd = t

        if cmd == 'M':
            x, y = take(2)
            path.moveTo(x, y)
            cx, cy = x, y
            sx, sy = x, y
            last_cmd = 'M'
            while i < len(tokens) and not isinstance(tokens[i], str):
                x, y = take(2)
                path.lineTo(x, y)
                cx, cy = x, y
            continue
        if cmd == 'm':
            dx, dy = take(2)
            cx, cy = cx + dx, cy + dy
            path.moveTo(cx, cy)
            sx, sy = cx, cy
            last_cmd = 'm'
            while i < len(tokens) and not isinstance(tokens[i], str):
                dx, dy = take(2)
                cx, cy = cx + dx, cy + dy
                path.lineTo(cx, cy)
            continue
        if cmd == 'L':
            x, y = take(2)
            path.lineTo(x, y)
            cx, cy = x, y
        elif cmd == 'l':
            dx, dy = take(2)
            cx, cy = cx + dx, cy + dy
            path.lineTo(cx, cy)
        elif cmd == 'H':
            x, = take(1)
            path.lineTo(x, cy)
            cx = x
        elif cmd == 'h':
            dx, = take(1)
            cx = cx + dx
            path.lineTo(cx, cy)
        elif cmd == 'V':
            y, = take(1)
            path.lineTo(cx, y)
            cy = y
        elif cmd == 'v':
            dy, = take(1)
            cy = cy + dy
            path.lineTo(cx, cy)
        elif cmd == 'C':
            x1, y1, x2, y2, x, y = take(6)
            path.cubicTo(x1, y1, x2, y2, x, y)
            cx, cy = x, y
            x1, y1 = x2, y2
        elif cmd == 'c':
            dx1, dy1, dx2, dy2, dx, dy = take(6)
            path.cubicTo(
                cx + dx1, cy + dy1, cx + dx2, cy + dy2, cx + dx, cy + dy)
            x1, y1 = cx + dx2, cy + dy2
            cx, cy = cx + dx, cy + dy
        elif cmd == 'S':
            x2, y2, x, y = take(4)
            if last_cmd in ('C', 'c', 'S', 's'):
                rx, ry = 2 * cx - x1, 2 * cy - y1
            else:
                rx, ry = cx, cy
            path.cubicTo(rx, ry, x2, y2, x, y)
            x1, y1 = x2, y2
            cx, cy = x, y
        elif cmd == 's':
            dx2, dy2, dx, dy = take(4)
            if last_cmd in ('C', 'c', 'S', 's'):
                rx, ry = 2 * cx - x1, 2 * cy - y1
            else:
                rx, ry = cx, cy
            path.cubicTo(rx, ry, cx + dx2, cy + dy2, cx + dx, cy + dy)
            x1, y1 = cx + dx2, cy + dy2
            cx, cy = cx + dx, cy + dy
        elif cmd == 'Q':
            x1, y1, x, y = take(4)
            path.quadTo(x1, y1, x, y)
            cx, cy = x, y
        elif cmd == 'q':
            dx1, dy1, dx, dy = take(4)
            path.quadTo(cx + dx1, cy + dy1, cx + dx, cy + dy)
            x1, y1 = cx + dx1, cy + dy1
            cx, cy = cx + dx, cy + dy
        elif cmd == 'T':
            x, y = take(2)
            if last_cmd in ('Q', 'q', 'T', 't'):
                rx, ry = 2 * cx - x1, 2 * cy - y1
            else:
                rx, ry = cx, cy
            path.quadTo(rx, ry, x, y)
            x1, y1 = rx, ry
            cx, cy = x, y
        elif cmd == 't':
            dx, dy = take(2)
            if last_cmd in ('Q', 'q', 'T', 't'):
                rx, ry = 2 * cx - x1, 2 * cy - y1
            else:
                rx, ry = cx, cy
            path.quadTo(rx, ry, cx + dx, cy + dy)
            x1, y1 = rx, ry
            cx, cy = cx + dx, cy + dy
        elif cmd in ('A', 'a'):
            # Endpoint only; convert arcs to paths in the host first.
            rx, ry, rot, laf, sf, x, y = take(7)
            if cmd == 'a':
                x, y = cx + x, cy + y
            path.lineTo(x, y)
            cx, cy = x, y
        elif cmd in ('Z', 'z'):
            path.closeSubpath()
            cx, cy = sx, sy
        else:
            raise ValueError('unsupported SVG path command: {!r}'.format(cmd))
        last_cmd = cmd
    return path


def qpainterpath_to_svg_d(path, close_subpaths=False):
    """Serialize a QPainterPath to an SVG `d` string (absolute cmds).

    Open subpaths stay open (weed lines are open cuts). Set
    ``close_subpaths`` to force Z on each finished subpath.
    """
    if path is None or path.isEmpty():
        return ''
    MoveToElement = QPainterPath.MoveToElement
    LineToElement = QPainterPath.LineToElement
    CurveToElement = QPainterPath.CurveToElement
    CurveToDataElement = QPainterPath.CurveToDataElement

    parts = []
    params = []
    started = False
    last_move = None

    def flush_curve():
        nonlocal params
        if not params:
            return
        if len(params) == 2:
            c, e = params
            parts.append('Q {:g},{:g} {:g},{:g}'.format(
                c.x(), c.y(), e.x(), e.y()))
        elif len(params) == 3:
            c1, c2, e = params
            parts.append('C {:g},{:g} {:g},{:g} {:g},{:g}'.format(
                c1.x(), c1.y(), c2.x(), c2.y(), e.x(), e.y()))
        params = []

    n = path.elementCount()
    for i in range(n):
        e = path.elementAt(i)
        if params and e.type != CurveToDataElement:
            flush_curve()
        if e.type == MoveToElement:
            if close_subpaths and started and last_move is not None:
                parts.append('Z')
            parts.append('M {:g},{:g}'.format(e.x, e.y))
            last_move = (e.x, e.y)
            started = True
        elif e.type == LineToElement:
            parts.append('L {:g},{:g}'.format(e.x, e.y))
        elif e.type == CurveToElement:
            params = [QPointF(e.x, e.y)]
        elif e.type == CurveToDataElement:
            params.append(QPointF(e.x, e.y))
    flush_curve()
    if close_subpaths and started:
        parts.append('Z')
    return ' '.join(parts)


def keep_fill_to_svg_d(path):
    """Flatten ``design_keep_fill`` to closed SVG polygons.

    ``toSubpathPolygons`` emits same-winding outer+hole rings. Paint with
    ``fill-rule="evenodd"`` (matches Qt OddEvenFill); ``nonzero`` fills holes.
    """
    if path is None or path.isEmpty():
        return ''
    try:
        polys = path.toSubpathPolygons()
    except TypeError:
        polys = path.toSubpathPolygons(QTransform())
    parts = []
    for poly in polys:
        pts = list(poly)
        if not pts:
            continue
        parts.append('M {:.3f} {:.3f}'.format(pts[0].x(), pts[0].y()))
        for p in pts[1:]:
            parts.append('L {:.3f} {:.3f}'.format(p.x(), p.y()))
        parts.append('Z')
    return ' '.join(parts)


def weed_path_to_open_d_list(path):
    """Split weed QPainterPath into one open `d` string per subpath."""
    from .paths import split_painter_path
    out = []
    for sp in split_painter_path(path):
        d = qpainterpath_to_svg_d(sp, close_subpaths=False)
        if d:
            out.append(d)
    return out
