# Join label

**Status:** done

## Goal

`docs/user/surround.md` names the join gap the way the
window shows it. The unset value is a quarter inch under
the document scale, and the label does not say mm.

## Do

Edit only `docs/user/surround.md`.

Both **Join gap (mm)** names become **Join gap**. That is
the label on the window. The unit is not part of the name.

The sentence that says the unset join gap is 6.35 stops
naming that count. It is a quarter of an inch under the
document scale, shown in the unit the window is using. Do
not put another fixed count in its place.

Leave the rest of those steps. The control is on the form
only in this mode. It cannot go below zero. Zero joins only
surrounds that meet or overlap. A larger number joins
surrounds that stay at most that far apart. Changing the
length still redraws the surround.

Do not edit the window, product code, tests, or any other
file. Follow the boundary part. Do not copy it onto the
page.

## Checks

- The page does not tell the person to find "Join gap (mm)".
- It does not say the unset join gap is the fixed count
  6.35, or any other fixed count.
- Both names are **Join gap**. The unset value is a quarter
  of an inch under the document scale, in the unit the
  window shows.
- `docs/user/surround.md` is the only changed file.

## Note

`docs/user/surround.md` now names the control **Join gap** in
both places. The unset value is a quarter of an inch under
the document scale, shown in the unit the window is using.
The form-only rule, the zero floor, meet-or-overlap at zero,
the larger-gap rule, and the redraw step are unchanged.
Start Algorithm and Change surround sentences are unchanged.

Why: the page told the person to find "Join gap (mm)" and
said the unset value was the fixed count 6.35. The window
label is "Join gap". The unit is not part of the name. The
unset value follows the document scale.

Checked by reading `docs/user/surround.md`. Neither name is
"Join gap (mm)". The page does not say 6.35 or any other
fixed count for the unset join gap. Both names are
**Join gap**. `git diff -- docs/user/surround.md` is only
those two edits. Status left `in-progress`.

Summary: No defects. Both names are **Join gap**. The unset
value is a quarter of an inch under the document scale, shown
in the unit the window is using. No fixed count remains. The
diff is only those two edits.

Context worth keeping: The form-only rule, the zero floor,
meet-or-overlap at zero, the larger-gap rule, and the redraw
step are the old sentences. Start Algorithm and Change surround
were not edited. Those sentences stay with control-names. The
window label is `Join gap`. The other product diff is
spinner-labels on `docs/inkscape-extension.md`. The pass is
`cr-01.md`.

Result: No defects remain. The named checks passed. The checks
are reading the page, not pytest.

## Stopped

2026-11-07. Review found no defect. The named checks passed.
The task is done. control-names still owns the Start
Algorithm and Change surround sentences in this page.
