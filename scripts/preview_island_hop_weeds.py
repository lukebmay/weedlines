#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render keep + weed paths for peel strategies (agent SVG harness).

Usage:
  QT_QPA_PLATFORM=offscreen PYTHONPATH=src python3 scripts/preview_island_hop_weeds.py
  PYTHONPATH=src python3 scripts/preview_island_hop_weeds.py --svg path/to/keep.svg

Writes SVG with design-keep fill and weeds. Prints stats per mode;
island-hop also prints residual-trap count.
"""
from __future__ import division, print_function

import argparse
import math
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from weedlib.qt import QPointF, QRectF, QPainterPath, load_widgets
from weedlib import (
    even_odd_keep_fill, generate_weeds, padded_work_rect,
    residual_waste_traps, weed_sample_stats,
)
from weedlib.svg_paths import keep_fill_to_svg_d

_QtCore, _QtGui, _QtWidgets = load_widgets()
QApplication = _QtWidgets.QApplication
QFont = _QtGui.QFont

# Keep a process-wide ref; addText segfaults if QApplication is GC'd.
_QT_APP = QApplication.instance() or QApplication([])

__version__ = '0.3.0'


def rect_path(x, y, w, h):
    p = QPainterPath()
    p.addRect(QRectF(x, y, w, h))
    return p


def circle_path(cx, cy, r):
    p = QPainterPath()
    p.addEllipse(QPointF(cx, cy), r, r)
    return p


def letter_o():
    p = QPainterPath()
    p.addPath(circle_path(50, 50, 40))
    p.addPath(circle_path(50, 50, 20))
    return p


def star12(cx=50, cy=50, r_outer=40, r_inner=16):
    p = QPainterPath()
    n = 12
    for i in range(n * 2):
        ang = -math.pi / 2.0 + i * math.pi / float(n)
        r = r_outer if (i % 2 == 0) else r_inner
        x = cx + r * math.cos(ang)
        y = cy + r * math.sin(ang)
        if i == 0:
            p.moveTo(x, y)
        else:
            p.lineTo(x, y)
    p.closeSubpath()
    return p


def diamond_path():
    p = QPainterPath()
    p.moveTo(50, 5)
    p.lineTo(80, 50)
    p.lineTo(50, 95)
    p.lineTo(20, 50)
    p.closeSubpath()
    return p


def two_islands():
    p = QPainterPath()
    p.addPath(rect_path(10, 30, 25, 40))
    p.addPath(rect_path(45, 30, 25, 40))
    return p


def _united_rects(rects):
    acc = QPainterPath()
    for x, y, w, h in rects:
        acc = acc.united(rect_path(x, y, w, h)) if not acc.isEmpty() else rect_path(x, y, w, h)
    return acc


def letters_hi(ox=0, oy=0):
    """Separated H and I (unioned strokes so even-odd does not punch holes)."""
    h = _united_rects((
        (8 + ox, 18 + oy, 8, 54),
        (30 + ox, 18 + oy, 8, 54),
        (8 + ox, 39 + oy, 30, 10),
    ))
    i = rect_path(62 + ox, 18 + oy, 8, 54)
    p = QPainterPath()
    p.addPath(h)
    p.addPath(i)
    return p


def framed_hi():
    p = QPainterPath()
    p.addRect(QRectF(0, 0, 120, 100))
    p.addRect(QRectF(6, 6, 108, 88))
    p.addPath(letters_hi(ox=20, oy=8))
    return p


def wreath_hi():
    p = QPainterPath()
    for x, y in ((4, 4), (54, 2), (104, 4), (4, 40), (104, 40),
                 (4, 76), (54, 80), (104, 76)):
        p.addPath(rect_path(x, y, 12, 12))
    p.addPath(letters_hi(ox=26, oy=10))
    return p


def quoted_word():
    """Real glyphs: letters, comma, apostrophe, quotes, bang."""
    font = QFont('Noto Sans')
    font.setPixelSize(36)
    p = QPainterPath()
    p.addText(8, 48, font, 'Hi, it\'s "OK!"')
    return p


def _quoted_blocks_geo(ox=0, oy=0):
    """Geometric stand-in for quoted word (no font): H i , t + quotes + O."""
    def _united(rects):
        acc = QPainterPath()
        for x, y, w, h in rects:
            r = rect_path(x + ox, y + oy, w, h)
            acc = acc.united(r) if not acc.isEmpty() else r
        return acc

    p = QPainterPath()
    p.addPath(_united((
        (8, 18, 8, 54), (30, 18, 8, 54), (8, 39, 30, 10),
    )))
    p.addPath(rect_path(50 + ox, 36 + oy, 6, 36))
    p.addPath(rect_path(50 + ox, 18 + oy, 6, 8))
    p.addPath(rect_path(64 + ox, 62 + oy, 6, 12))
    p.addPath(rect_path(80 + ox, 18 + oy, 6, 54))
    p.addPath(rect_path(80 + ox, 18 + oy, 16, 8))
    p.addPath(rect_path(112 + ox, 16 + oy, 4, 16))
    p.addPath(rect_path(120 + ox, 16 + oy, 4, 16))
    p.addPath(rect_path(132 + ox, 18 + oy, 24, 54))
    p.addPath(circle_path(144 + ox, 45 + oy, 10))
    p.addPath(rect_path(166 + ox, 16 + oy, 4, 16))
    p.addPath(rect_path(174 + ox, 16 + oy, 4, 16))
    return p


def quoted_in_frame():
    """Quoted geometric word inside a hollow rectangular keep frame."""
    p = QPainterPath()
    p.addRect(QRectF(0, 0, 200, 100))
    p.addRect(QRectF(8, 8, 184, 84))
    p.addPath(_quoted_blocks_geo(ox=8, oy=10))
    return p


def quoted_frame_punched():
    """Quoted word in a frame with circular punches cut out of the border."""
    p = QPainterPath()
    p.addRect(QRectF(0, 0, 200, 100))
    p.addRect(QRectF(8, 8, 184, 84))
    for cx, cy, r in ((18, 18, 5), (100, 14, 6), (182, 18, 5),
                      (18, 82, 5), (100, 86, 6), (182, 82, 5),
                      (4, 50, 4), (196, 50, 4)):
        p.addPath(circle_path(cx, cy, r))
    p.addPath(_quoted_blocks_geo(ox=8, oy=10))
    return p


def letter_a():
    """Capital A: keep with a triangular counter."""
    outer = QPainterPath()
    outer.moveTo(40, 12)
    outer.lineTo(68, 72)
    outer.lineTo(54, 72)
    outer.lineTo(49, 56)
    outer.lineTo(31, 56)
    outer.lineTo(26, 72)
    outer.lineTo(12, 72)
    outer.closeSubpath()
    hole = QPainterPath()
    hole.moveTo(40, 30)
    hole.lineTo(47, 50)
    hole.lineTo(33, 50)
    hole.closeSubpath()
    p = QPainterPath()
    p.addPath(outer)
    p.addPath(hole)
    return p


def load_svg_path(path):
    """Load keep geometry from an SVG file.

    Prefers Inkcut ``QtSvgDoc`` if installed; otherwise raises with a
    clear message (fixtures under tests/data are usually enough).
    """
    try:
        from inkcut.core.svg import QtSvgDoc
    except ImportError as exc:
        raise SystemExit(
            'Loading arbitrary SVG needs inkcut.core.svg.QtSvgDoc, or use '
            'built-in fixtures (no --svg). Install inkcut or omit --svg.'
        ) from exc
    return QPainterPath(QtSvgDoc(path))


def path_to_svg_d(path, close_subpaths=False):
    """SVG path d. Keep fill uses evenodd polygons; weeds stay open."""
    if close_subpaths:
        return keep_fill_to_svg_d(path)
    parts = []
    for i in range(path.elementCount()):
        e = path.elementAt(i)
        if e.isMoveTo():
            parts.append('M %.3f %.3f' % (e.x, e.y))
        elif e.isLineTo():
            parts.append('L %.3f %.3f' % (e.x, e.y))
        else:
            parts.append('L %.3f %.3f' % (e.x, e.y))
    return ' '.join(parts)


def _united_rect(rects):
    acc = None
    for r in rects:
        if r is None or r.isEmpty():
            continue
        acc = QRectF(r) if acc is None else acc.united(r)
    return acc


def render_case(name, keep, modes, padding, spacing, out_dir, auto_kw=None):
    auto_kw = dict(auto_kw or {})
    keep_fill = even_odd_keep_fill(keep)
    work = padded_work_rect(keep, padding)

    panels = []
    content_rects = [keep.boundingRect(), work]
    for mode in modes:
        weed = generate_weeds(
            keep, mode=mode, padding=padding, spacing=spacing, **auto_kw)
        st = weed_sample_stats(
            weed, keep_fill=keep_fill, work_rect=work, step=1.0)
        if mode == 'island-hop':
            st['traps'] = len(residual_waste_traps(
                keep, weed, work=work, padding=padding))
        else:
            st['traps'] = None
        panels.append((mode, weed, st))
        if not weed.isEmpty():
            content_rects.append(weed.boundingRect())

    content = _united_rect(content_rects)
    if content is None or content.isEmpty():
        content = QRectF(0, 0, 100, 100)
    margin = 8.0
    vb_x = content.x() - margin
    vb_y = content.y() - margin
    vb_w = content.width() + 2 * margin
    vb_h = content.height() + 2 * margin

    gap = 15
    x_off = 0
    laid = []
    for mode, weed, st in panels:
        laid.append((mode, weed, st, x_off))
        x_off += vb_w + gap

    total_w = x_off - gap
    total_h = vb_h + 28
    # Gray keep / white waste / orange cuts (design_keep_fill = overlaps stay keep).
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'width="%.1f" height="%.1f" viewBox="0 0 %.1f %.1f">' % (
            total_w, total_h, total_w, total_h),
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="4" y="14" font-family="sans-serif" font-size="11" '
        'fill="#333">%s (gray=design keep, white=waste, orange=weed)</text>'
        % name,
    ]
    y0 = 22
    for mode, weed, st, xo in laid:
        lines.append(
            '<g transform="translate(%.1f,%.1f)">' % (xo, y0))
        lines.append(
            '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" '
            'fill="#ffffff" stroke="#ddd"/>' % (0, 0, vb_w, vb_h))
        lines.append(
            '<g transform="translate(%.1f,%.1f)">' % (-vb_x, -vb_y))
        kf = path_to_svg_d(keep_fill, close_subpaths=True)
        kd = path_to_svg_d(keep, close_subpaths=True)
        wd = path_to_svg_d(weed, close_subpaths=False)
        if kf:
            # evenodd: toSubpathPolygons same-winding rings (Qt OddEvenFill)
            lines.append(
                '<path d="%s" fill="#9a9a9a" fill-opacity="1" '
                'fill-rule="evenodd" stroke="none"/>' % kf)
        if kd:
            lines.append(
                '<path d="%s" fill="none" stroke="#666666" '
                'stroke-width="1.2"/>' % kd)
        if wd:
            lines.append(
                '<path d="%s" fill="none" stroke="#e67e22" '
                'stroke-width="1.0"/>' % wd)
        lines.append('</g>')
        trap_bit = ''
        if st.get('traps') is not None:
            trap_bit = ' traps=%d' % st['traps']
        lines.append(
            '<text x="4" y="%.1f" font-family="sans-serif" font-size="9" '
            'fill="#555">%s · segs=%d len=%.0f out=%d inkeep=%d%s</text>' % (
                vb_h - 4, mode, st['segments'], st['length'],
                st['outside_work'], st['in_keep'], trap_bit))
        lines.append('</g>')

    lines.append('</svg>')
    path = os.path.join(out_dir, 'weed_%s.svg' % name)
    with open(path, 'w') as f:
        f.write('\n'.join(lines))
    print('wrote', path)
    for mode, weed, st, _ in laid:
        extra = ''
        if st.get('traps') is not None:
            extra = ' traps=%d' % st['traps']
        print('  %s: segs=%d length=%.1f outside-work=%d in-keep=%d '
              '(frac out=%.3f in=%.3f)%s' % (
                  mode, st['segments'], st['length'],
                  st['outside_work'], st['in_keep'],
                  st['outside_work_frac'], st['in_keep_frac'], extra))
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--version', action='version', version=__version__)
    ap.add_argument(
        '--out-dir', default=os.path.join(
            os.path.dirname(__file__), '..', 'tests', 'data', 'weed_preview'),
        help='Directory for SVG previews')
    ap.add_argument('--svg', help='Load keep geometry from an SVG file')
    ap.add_argument(
        '--mode', action='append', dest='modes',
        help='Weed mode (repeatable). Default: frame,grid,auto')
    ap.add_argument('--spacing', type=float, default=None)
    ap.add_argument('--padding', type=float, default=12.0)
    ap.add_argument('--max-chunk', type=float, default=None)
    ap.add_argument('--bridge-width', type=float, default=None)
    ap.add_argument('--clearance', type=float, default=None)
    ap.add_argument('--min-cut', type=float, default=None)
    ap.add_argument('--delicate-angle', type=float, default=None)
    ap.add_argument('--collar', type=float, default=None)
    ap.add_argument('--body-clearance', type=float, default=None)
    ap.add_argument('--alpha-min', type=float, default=None)
    ap.add_argument('--frame-clearance', type=float, default=None)
    ap.add_argument('--max-spokes', type=int, default=None)
    ap.add_argument('--peninsula-ratio', type=float, default=None)
    args = ap.parse_args(argv)
    out_dir = os.path.abspath(args.out_dir)
    os.makedirs(out_dir, exist_ok=True)

    pad = [args.padding, args.padding, args.padding, args.padding]
    modes = args.modes or ['frame', 'grid', 'island-hop']
    auto_kw = {}
    if args.max_chunk is not None:
        auto_kw['max_chunk'] = args.max_chunk
    if args.bridge_width is not None:
        auto_kw['bridge_width'] = args.bridge_width
    if args.clearance is not None:
        auto_kw['clearance'] = args.clearance
    if args.min_cut is not None:
        auto_kw['min_cut'] = args.min_cut
    if args.delicate_angle is not None:
        auto_kw['delicate_angle_deg'] = args.delicate_angle
    if args.collar is not None:
        auto_kw['collar'] = args.collar
    if args.body_clearance is not None:
        auto_kw['body_clearance'] = args.body_clearance
    if args.alpha_min is not None:
        auto_kw['alpha_min'] = args.alpha_min
    if args.frame_clearance is not None:
        auto_kw['frame_clearance'] = args.frame_clearance
    if args.max_spokes is not None:
        auto_kw['max_spokes'] = args.max_spokes
    if args.peninsula_ratio is not None:
        auto_kw['peninsula_ratio'] = args.peninsula_ratio

    default_spacing = 15.0 if args.spacing is None else args.spacing
    cases = [
        ('rect', rect_path(20, 20, 60, 40), default_spacing),
        ('letter_o', letter_o(), default_spacing),
        ('star12', star12(), 20.0 if args.spacing is None else args.spacing),
        ('diamond', diamond_path(), 20.0 if args.spacing is None else args.spacing),
        ('two_islands', two_islands(), default_spacing),
        ('letters_hi', letters_hi(), default_spacing),
        ('quoted_word', quoted_word(), default_spacing),
        ('letter_a', letter_a(), default_spacing),
        ('framed_hi', framed_hi(), default_spacing),
        ('wreath_hi', wreath_hi(), default_spacing),
        ('quoted_in_frame', quoted_in_frame(), default_spacing),
        ('quoted_frame_punched', quoted_frame_punched(), default_spacing),
    ]
    if args.svg:
        cases.append((
            'svg', load_svg_path(os.path.abspath(args.svg)), default_spacing))

    for name, keep, spacing in cases:
        render_case(
            name, keep, modes, pad, spacing, out_dir, auto_kw=auto_kw)
    print('done →', out_dir)
    return 0


if __name__ == '__main__':
    sys.exit(main())
