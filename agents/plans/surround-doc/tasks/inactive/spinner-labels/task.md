# Spinner labels

**Status:** done

## Goal

`docs/inkscape-extension.md` stops saying the padding,
spacing, and collar spinners are labeled mm.

## Do

`docs/inkscape-extension.md` only. Lines 81–82 say the
extension treats document user units as mm and that those
spinners are labeled mm. The labels are "Padding",
"Grid spacing", and "Collar (island-hop)". The unit is
the display unit, and the library receives document user
units.

Correct those sentences. Do not edit the window or the
solvers. Do not invent a unit story past what the
boundary part says.

## Checks

Read the file. The words "labeled **mm**" are gone from
that units section. The three labels above are the names
a person sees. No product test reads this file.

## Note

Changed one bullet in the units section of
`docs/inkscape-extension.md`. It no longer says the extension
treats document user units as mm, or that the padding, spacing,
and collar spinners are labeled mm. Those spinners are labeled
**Padding**, **Grid spacing**, and **Collar (island-hop)**. The
unit is the display unit. The library receives document user
units. The **Start Algorithm** / **Cancel…** sentence is
unchanged. The window and the solvers were not edited.

Why: the labels a person sees do not say mm. The unit is the
display unit, and the library receives document user units.

Checked by reading the file. The words "labeled **mm**" are gone
from that units section. The three labels above are the names
in that bullet, and island-hop is still in the collar label.
`git diff -- docs/inkscape-extension.md` is that one bullet.
No product test reads this file. Status left in-progress.

Summary: No defects. The units bullet no longer says the
spinners are labeled mm, or that the extension treats document
user units as mm. The names are **Padding**, **Grid spacing**,
and **Collar (island-hop)**. The unit is the display unit. The
library receives document user units.

Context worth keeping: `git diff -- docs/inkscape-extension.md`
is that one bullet. The three names match the window labels.
No test under `tests/` reads this file. The Start Algorithm /
Cancel sentence was not edited and stays with control-names.
The pass is `cr-01.md`.

Result: No defects remain. The named checks passed. The checks
are reading the page, not pytest.

## Stopped

2026-11-07. Review found no defect. The named checks passed.
The task is done. control-names still owns the Start
Algorithm / Cancel sentence in this page.
