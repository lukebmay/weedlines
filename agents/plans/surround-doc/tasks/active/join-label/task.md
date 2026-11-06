# Join label

**Status:** ready

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

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
