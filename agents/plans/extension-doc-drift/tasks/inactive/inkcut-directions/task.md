# Inkcut directions

**Status:** done

## Goal

`docs/inkscape-extension.md` describes this repo's
extension. It stops sending the person to the old
Inkcut extension.

## Do

Edit only `docs/inkscape-extension.md`.

Replace the old Inkcut directions. That is the title
that calls this the Inkcut extension, the opening that
names `inkcut.weedlib`, the `inkcut install-plugin`
steps, the symlink of `inkcut_weeds.py`, the menu
**Extensions → Inkcut**, the clause that sends the
layer to Inkcut next, and the later lines that name
`inkcut.weedlib`, `inkcut/weedlib/`, or
`inkcut/job/` as this extension. The sentence that
the Inkcut app default stays `frame` is one of those
lines.

Install follows the install part. The menu follows
the host part. Do not invent a menu name. Do not
invent a module path, a solver file, or a mode
default. Where a line only describes the old Inkcut
tree and those parts do not name a replacement, drop
the Inkcut claim.

Leave the rest of the page. That includes the
run-control names, the Apply sentence, and the
sentence that Close is a separate control. Leave the
existing log phrase. Do not invent a log label.
Leave the units section, including the spinner
labels. Do not add a join-gap sentence. Do not add
piece-border labels, a cavern measure, or a
design-copy sentence.

Do not edit the window, the solvers, or any other
file. The product does not change.

## Checks

- The file does not tell the person to open
  Extensions → Inkcut, to run `inkcut install-plugin`,
  or to symlink `inkcut_weeds.py`.
- It does not name `inkcut.weedlib` as this extension.
- The menu it names is the menu in the host part. No
  invented entry.
- The run-control names, the Apply sentence, and the
  units section are unchanged. No join-gap sentence
  is added.
- The page does not gain piece-border labels, a log
  label, a cavern measure, or a design-copy sentence.
- `docs/inkscape-extension.md` is the only changed
  file. No product test reads this file.

## Note

`docs/inkscape-extension.md` no longer calls this the Inkcut
extension. The title is Weedlines. Install is `weedlines
install`, which symlinks `extensions/inkscape/`, with
`--copy`, `--force`, `--dry-run`, `--uninstall`, and
`--dest`, plus the checkout and the Linux destination from
the install part. `weedlines update` and `./install` are
there too, including the restart after a real install. The
menu is **Extensions → Weedlines**, with `1 Auto generate
weedlines`, `2 Make ready to cut`, `3 Reimport last
weedlines`, and `4 Reimport last ready cut`. No divider,
and no name ends in an ellipsis. Entry 1 opens the detached
window. The clause that sent the layer to Inkcut is gone.
Lines that named `inkcut.weedlib`, `inkcut/weedlib/`, or
`inkcut/job/` as this extension are gone, including the
sentence that the Inkcut app default stays `frame`. No
solver file and no mode default were added. The host entry
on the page is `extensions/inkscape/`.

The run-control names, the Apply sentence, the Close
sentence, and the expandable stdout/stderr log phrase are
unchanged. The units section, including the spinner labels,
is unchanged. No join-gap sentence, piece-border label, log
label, cavern measure, or design-copy sentence was added.
"In Inkcut jobs" stays in the units section. "same as
Inkcut" stays on the open-cut sentence. Those lines do not
name the old tree as this extension.

Why: the page still sent the person through `inkcut
install-plugin`, a symlink of `inkcut_weeds.py`, and
**Extensions → Inkcut**. The install part and the host part
name the replacement. Where they name none, the old claim
was dropped.

Checked by reading the page against the menu in
`agents/architecture/host.md` and the install steps in
`agents/architecture/install.md`. A search of the page
finds no `inkcut install-plugin`, no `inkcut_weeds.py`, no
`inkcut.weedlib`, no `inkcut/weedlib/`, no `inkcut/job/`,
and no Extensions → Inkcut. The four menu names are the
host entries. `git diff -- docs/inkscape-extension.md` does
not include the units section, the Apply sentence, or the
log phrase. A search of `tests/` finds no reader of this
file. No other product file was edited for this task.
Status left `in-progress`.

Summary: No defects. The page no longer sends the person
to the old Inkcut extension. Install follows the install
part. The menu is the four host entries, and none is
invented. The run-control names, the Apply sentence, and
the units section are unchanged. No join-gap sentence,
piece-border label, log label, cavern measure, or
design-copy sentence was added.

Context worth keeping: The only file in this change is
`docs/inkscape-extension.md`. Other dirty files belong
to other work. "In Inkcut jobs" stays in the units
section, which the task says to leave. "same as Inkcut"
on the open-cut sentence compares the cut. It does not
tell the person to use the old Inkcut extension, and the
task did not list it. It is not a defect. No file under
`tests/` reads this page. There is no automated test.
The pass is `cr-01.md`.

Result: No defects. The named checks passed. There is
no automated test. The checks are reading the page, the
diff, the host part, and the install part.
