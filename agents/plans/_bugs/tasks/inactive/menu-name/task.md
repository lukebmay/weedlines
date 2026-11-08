# Menu name

**Status:** done

## Goal

Confirm the reported menu name. If the pages already
use the host entry, stop with no edit. If they do not,
those pages use that entry.

## Do

A developer on the piece-border page reported this.
Confirm it before changing any file.

The report: `README.md` and `docs/user/surround.md`
tell the person to open **Weedlines from selection…**.
The menu entry is `1 Auto generate weedlines` in
`extensions/inkscape/weedlines.inx` and
`agents/architecture/host.md`.

Read those four files. If both pages already name
`1 Auto generate weedlines`, stop. Do not change
files. Say what each page says.

If a page names the other phrase, change only that
phrase to the host entry. Do not add an ellipsis.
Do not edit `docs/user/piece-border.md`. Do not do
the control-names edits: Start / Cancel, Start
Algorithm, and Change surround stay for those tasks.
Do not edit the window, the inx, or the host part.

## Checks

- If the report is wrong, no file changes, and the
  note says what the pages say.
- If it is right, `README.md` and
  `docs/user/surround.md` name `1 Auto generate
  weedlines` where they told the person to open the
  window. They do not say Weedlines from selection.
- Those pages still say Start / Cancel, Start
  Algorithm, or Change surround where they did
  before this task. `docs/user/piece-border.md` is
  unchanged.
- There is no automated test for this sentence. Say
  so. The check is reading the pages against the
  host part.

## Note

Confirmed. `extensions/inkscape/weedlines.inx` names the entry
`1 Auto generate weedlines`. `agents/architecture/host.md` uses
that same entry, and none of the names end in an ellipsis.
`README.md` told the person to open **Weedlines from
selection…**. `docs/user/surround.md` did the same, split
across the open-the-window step.

Those two phrases are now `1 Auto generate weedlines`. No
ellipsis was added. Start / Cancel in `README.md`, and Start
Algorithm and Change surround in `docs/user/surround.md`,
were left as they were. `docs/user/piece-border.md`, the
window, the inx, and the host part were not edited.

Why: the pages named a menu entry the host does not have.

Checked by reading the two pages against the host part and
the inx name. `git diff` is those two phrases. Neither page
says Weedlines from selection. There is no automated test
for this sentence. Status left `in-progress`.

Summary: No defects. Both pages now name `1 Auto generate
weedlines` where they told the person to open the window.
They do not say Weedlines from selection. No ellipsis was
added. Start / Cancel, Start Algorithm, and Change surround
are still where this task left them.

Context worth keeping: `git diff -- README.md
docs/user/surround.md` is only those two phrases. The inx
name and the host entry are both `1 Auto generate
weedlines`, and the host says none of the names end in an
ellipsis. `docs/user/piece-border.md` was not edited. It
already used that entry and belongs to the border-page
task. Other dirty files are not this change. There is no
automated test for this sentence. The check was reading
the pages against the host part and the inx. The pass is
`cr-01.md`.

Result: No defects remain. The named checks passed.
