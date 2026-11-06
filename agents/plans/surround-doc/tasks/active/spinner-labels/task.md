# Spinner labels

**Status:** ready

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

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
