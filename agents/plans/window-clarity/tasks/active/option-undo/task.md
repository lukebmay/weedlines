# Option undo

**Status:** ready

## Goal

The person can undo and redo committed option values across
the form.

## Do

`extensions/inkscape/weedlines_dialog.py`. The history
covers the mode, the length options, the output layer name,
and the four preview colors. Use the usual undo and redo
keys. Do not add buttons for them.

A spin commits when its value commits. A layer name or a
color still being typed undoes as text in that field until
it commits, and that keystroke does not enter the option
history. Restoring a length restores what the person sees,
and the library still receives user units afterward.
Restoring the mode restores which knobs are visible.

Undo does not include swap, the run controls, the log, work
marks, or any cut.

## Checks

Offscreen, when Qt loads. Put the test in
`tests/test_window_options.py`.

Undo and redo a committed mode change, a committed length,
the layer name, and one preview color. Each returns to the
value that was committed, and a length still reaches the
library in user units.

A color that is still being typed undoes inside the field
and does not undo the previous committed option. Undo after
swap does not swap back. Undo does not remove a surround or
a cut that is already on screen.

## Note

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
