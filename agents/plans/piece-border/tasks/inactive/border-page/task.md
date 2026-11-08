# Border page

**Status:** done

## Goal

A person can see when the piece border is drawn. The
page does not name the two length options.

## Do

Add `docs/user/piece-border.md`. Write it for a person
following along. The tone rules are
`agents/installed/documentation.md`. The behavior is
Piece border in `agents/architecture/preview.md`. Do
not copy that part into the page.

When the line under the preview names problems, the
rectangles are not drawn. Point at
`docs/user/correction-arrows.md`. Do not repeat that
page. When the line is empty, the two rectangles are
drawn in the weed-line color without choosing Start.
Swap subject and weed area draws them again for the
new subject. They are not the surround, and they are
not padding.

Do not invent the two option labels. Do not tell the
person to find a length control for them. Do not name
a cavern measure. Do not take a measure from
`docs/weed-hard-rules.md`. Do not invent conquer. Do
not remove island-hop. Do not edit the root
`README.md`, `docs/user/surround.md`,
`docs/user/correction-arrows.md`, or any code.

## Checks

- The page is `docs/user/piece-border.md`. The root
  README, `docs/user/surround.md`, and
  `docs/user/correction-arrows.md` are unchanged.
- The steps follow the order a person does them.
  A clear check draws the rectangles without Start.
  A line that names problems does not, and points at
  the correction page.
- The page does not name a control for either border
  length. It does not describe conquer.

## Note

Added `docs/user/piece-border.md`. A person opens the window,
then reads the line under the preview. When that line names
problems, the two rectangles are not drawn, and the page points
at `docs/user/correction-arrows.md` instead of repeating it.
When the line is empty, the rectangles are drawn in the Weed
line color without choosing Start. Swap subject and weed area
draws them again for the new subject. The page says they are
not the surround and not padding. It names no control for
either border length, and it does not describe conquer.

Why: a person had no page for when the piece border is drawn,
and the two length labels are still unnamed.

Checked by reading the page against Piece border in
`agents/architecture/preview.md`. The steps are open the
window, read the line, see the rectangles without Start, then
swap. `git diff -- README.md docs/user/surround.md
docs/user/correction-arrows.md` is empty. No code was edited.
A search of the page finds no conquer, no cavern, no
length-option label, and no measure. The only "padding" is
the sentence that the rectangles are not padding. Status left
`in-progress`.

Not this task: `docs/user/surround.md` and the root `README.md`
still said **Weedlines from selection…** when this page was
written. The menu entry is `1 Auto generate weedlines` in
`extensions/inkscape/weedlines.inx` and
`agents/architecture/host.md`. Those two files were not
edited by this task.

Summary: No defects. The page tells a person to open the
window, read the line under the preview, and see the two
rectangles in the Weed line color without choosing Start
when that line is empty. When the line names problems, the
rectangles are not drawn, and the page points at the
correction page. Swap draws them again for the new subject.
They are not the surround and not padding. The page names
no length control and does not describe conquer.

Context worth keeping: The menu step on this page is
`1 Auto generate weedlines`, matching the host part and the
inx. `git diff -- docs/user/correction-arrows.md` is empty.
The working-tree diff on `README.md` and
`docs/user/surround.md` is only that menu phrase, from the
menu-name task, not from this page. Do not treat that phrase,
or older **Start Algorithm** wording, as a defect here. The
page does not name the two border lengths, a cavern, or a
measure, and it does not copy the Piece border part. The
only "padding" says the rectangles are not padding. The
pass is `cr-01.md`.

Result: No defects remain. The named checks passed. There
is no automated test. The checks are reading the page.
