# Preview

When to use: Preview paint, swap, plugin settings, correction
arrows, or the return actions.

**Owner:** human. Agents may propose edits; apply only with explicit
permission.

The window owns the widgets. The library owns the regions, the
defect targets, and the arrow paths. The window paints the paths
the library returns. It does not invent a second set of arrows.

## Subject and weed area

The design bounds are the axis-aligned box of every figure, in
document user units.

A computed fill is paint when it is a color or a gradient and its
opacity is not zero. `fill:none` is not paint. The host resolves
inheritance before it writes the job.

When at least one figure has paint, each painted interior starts
as subject. An interior with no paint starts as weed area. When
no figure has paint, every figure interior starts as subject.

The weed area before an algorithm runs is the part of the design
bounds that is not subject. That includes gaps and holes inside
the bounds. It does not include the sheet outside the bounds.

Swap exchanges subject and weed area inside those bounds. The
next press exchanges them back. Swap does not move the bounds,
and it does not classify the sheet outside the bounds as subject.

Two cases fix the meaning. Filled letters inside a stroke-only
rectangle start as subject letters and a weed interior out to
the rectangle. Swap makes that interior the subject and the
letters weed. A filled rectangle whose holes are the letters
starts as a subject band and weed holes. Swap makes the holes
the subject and the band weed.

The window shows one button, labeled "Swap subject and weed
area". It sits in the form above the preview. After a swap, or
after a plugin setting changes, the window asks the library
again and repaints.

## Paint

The window paints each subject figure that has a solid fill in
that fill color. A subject figure with no paint, or with a
gradient, uses the default subject color.

The window paints the weed area as a checkerboard of the two
checkerboard colors. The view's own background, outside the weed
area, stays the view background.

When an algorithm has emitted weed lines, the window paints those
lines in the weed-line color, on top of the checkerboard. The
weed area then also includes the work region that algorithm
cuts, and that region is checkerboard too.

The plugin settings are four controls in the form above the
preview. They change paint only. They do not change the figure
check. Their initial values are:

| Setting | Initial color |
| --- | --- |
| Checkerboard light | `#E6E6E6` |
| Checkerboard dark | `#CFCFCF` |
| Weed line color | `#FF0000` |
| Default subject color | `#FFFFFF` |

The window does not keep these in a preferences file.

## Correction arrows

The library builds one arrow path per target. The window and the
result file use those paths.

Each kind shares one origin on the design bounds. In document
user units, minimum y is the top.

| Arrow | Origin | Color |
| --- | --- | --- |
| Dangling arrow | Top left | `#FF00FF` |
| Overlap arrow | Top right | `#FF6A00` |
| Self-overlap arrow | Bottom right | `#00E5FF` |

The shaft is a straight stroke in that color. The head is a
filled triangle in that color. The tip of the head is the
target. The shaft starts at the origin. When the target is the
origin, the arrow is a short mark whose tip is that point, so
the defect is still visible.

The three colors are not plugin settings.

## Return actions

When the figure check reports a defect, the window places one
line under the preview pane, then two actions under that line.
The line and the actions are in the layout. They are not a
popover, a message box, or any other surface that covers the
preview.

The line reads: "Correct the marked problems in Inkscape before
weed lines will run." It names each kind that is present, using
the words dangling ends, figure overlaps, and self-overlaps.

The actions are labeled "Return to Inkscape" and "Return to
Inkscape with correction arrows". The second action is present
only when at least one defect exists. Start stays disabled for
every mode while a defect exists.

"Return to Inkscape" writes no result and closes the window.
"Return to Inkscape with correction arrows" writes the
correction result, then replaces the line with "Run Extensions →
Weedlines → Import last result to place the arrows." It does not
close the window and it does not open a message box. The person
then uses "Return to Inkscape" to close it.

When the check reports no defect, the line is empty, the
correction action is absent, and Start works as it does today.
