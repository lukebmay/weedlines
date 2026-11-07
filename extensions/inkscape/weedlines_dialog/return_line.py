# -*- coding: utf-8 -*-
"""Defect line and the two return actions."""
from __future__ import division

from .form import _hex_color

_ARROW_KINDS = ('dangling', 'overlap', 'self-overlap')


_KIND_WORDS = (
    ('dangling', 'dangling ends'),
    ('overlap', 'figure overlaps'),
    ('self-overlap', 'self-overlaps'),
)


_PROBLEM_SENTENCE = (
    'Correct the marked problems in Inkscape before weed lines will run.')


_IMPORT_SENTENCE = (
    'Run Extensions → Weedlines → Reimport last ready to place the arrows.')


def _kind_swatch(color):
    """A square in the arrow color. Empty when the color is not a hex."""
    shown = _hex_color(color)
    if not shown:
        return ''
    # The name that follows this span is not given a color.
    return '<span style="color:%s;">&#9608;</span>' % shown


def _arrow_colors(arrow_paths):
    """Kind to the color on the arrow the library returned."""
    colors = {}
    for kind, batch in (arrow_paths or {}).items():
        if not batch:
            continue
        color = batch[0].color
        if _hex_color(color) is None:
            continue
        colors[kind] = color
    return colors


def _defect_line(defects, colors=None):
    """Name each defect kind that is present. Empty when the check is clear.

    ``colors`` maps a kind to that arrow's color. A swatch of the
    color precedes the name. The name itself is not colored.
    """
    present = set()
    for defect in defects or ():
        present.add(defect.kind)
    names = []
    for kind, word in _KIND_WORDS:
        if kind not in present:
            continue
        color = None if not colors else colors.get(kind)
        swatch = _kind_swatch(color) if color else ''
        if swatch:
            names.append('%s %s' % (swatch, word))
        else:
            names.append(word)
    if not names:
        return ''
    if len(names) == 1:
        named = names[0]
    elif len(names) == 2:
        named = '%s and %s' % (names[0], names[1])
    else:
        named = '%s, %s, and %s' % (names[0], names[1], names[2])
    return '%s %s.' % (_PROBLEM_SENTENCE, named)


class _Defect(object):
    def __init__(self, kind, target):
        self.kind = kind
        self.target = target


class _Check(object):
    def __init__(self, defects):
        self.defects = defects
        self.figures = []


class _ReturnLine(object):

    def _show_return_line(self):
        # The import sentence replaces this line. A later subject
        # ask must not put the defect names back.
        if self.return_line.text() == _IMPORT_SENTENCE:
            return
        defects = () if self.check is None else self.check.defects
        text = _defect_line(defects, _arrow_colors(self.state.get('arrow_paths')))
        if '<' in text:
            self.return_line.setTextFormat(self.QtCore.Qt.RichText)
        else:
            self.return_line.setTextFormat(self.QtCore.Qt.PlainText)
        self.return_line.setText(text)

    def on_return(self):
        self.on_close()

    def on_return_arrows(self):
        if not self.blocked or self.state['busy']:
            return
        arrows = self.state.get('arrows') or {}
        if not arrows:
            return
        self.write_correction_result(
            arrows,
            doc_attrs=self._doc_attrs(),
            labels=self.state.get('correction_labels'),
        )
        self.return_line.setTextFormat(self.QtCore.Qt.PlainText)
        self.return_line.setText(_IMPORT_SENTENCE)

    def _doc_attrs(self):
        doc_attrs = {}
        if self.dialog.doc_width:
            doc_attrs['width'] = self.dialog.doc_width
        if self.dialog.doc_height:
            doc_attrs['height'] = self.dialog.doc_height
        if self.dialog.doc_viewbox:
            doc_attrs['viewBox'] = self.dialog.doc_viewbox
        return doc_attrs

    def _store_classify(self, inbox):
        plain_figures = []
        for fig_id, fill, elements, rule in inbox['figures']:
            plain_figures.append({
                'id': fig_id,
                'fill': fill,
                'elements': elements,
                'rule': rule,
            })
        defects = []
        plain_defects = []
        for kind_name, x, y in inbox['defects']:
            defects.append(_Defect(kind_name, self.QtCore.QPointF(x, y)))
            plain_defects.append({'kind': kind_name, 'x': x, 'y': y})
        self.check = _Check(defects)
        self.state['plain_figures'] = plain_figures
        self.state['plain_defects'] = plain_defects
        labels = []
        for text, color, x, y in inbox.get('marks') or []:
            labels.append({
                'text': text,
                'color': color,
                'point': (float(x), float(y)),
            })
        self.state['correction_labels'] = labels
        self.blocked = bool(defects)
        self._show_return_line()
        if self.blocked and not self.state.get('arrows_button'):
            arrows_btn = self.QtWidgets.QPushButton(
                'Return to Inkscape with correction arrows')
            arrows_btn.setObjectName('return-arrows')
            self.return_row.insertWidget(1, arrows_btn)
            arrows_btn.clicked.connect(self.on_return_arrows)
            # setParent from the layout hides a widget added after show.
            arrows_btn.show()
            self.state['arrows_button'] = arrows_btn
