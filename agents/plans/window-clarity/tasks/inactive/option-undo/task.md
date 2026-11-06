# Option undo

**Status:** done

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

Committed option edits share one history on the dialog. It records
the mode, each length (padding, spacing, collar, surround distance,
join gap), the output layer name, and the four preview colors.
Ctrl+Z undoes. Ctrl+Y and Ctrl+Shift+Z redo. There is no button.

A spin enters the history when its value changes. The stored value
is document user units. Undo and redo put that length back through
the existing display conversion, so the person sees the current
unit and the library still receives user units. Opening the
window and switching the display unit rewrite the spins from
those user units and are not history entries. Restoring the mode
shows that mode's knobs and does not clear a surround or a cut.

A layer name or a color that is still being typed undoes in that
field and is not a history entry. It joins the history when the
field commits. Swap, the run controls, the log, and cuts are not
entries. The binding's widget module has no undo stack, so the
history is a small stack in the dialog rather than a second Qt.

Checked offscreen, no Inkscape, with `pytest tests/test_window_options.py
tests/test_window_surround.py tests/test_window_timing.py`:
39 passed. The new file checks a committed mode, length, layer
name, and preview color, including a length that reaches the
solver as user units; a color still being typed; undo after swap;
and undo while a surround and a cut are on screen. Status left
`in-progress`.

## Summary

No defects. Committed option edits share one history: the
mode, the five lengths, the layer name, and the four preview
colors. Ctrl+Z undoes. Ctrl+Y and Ctrl+Shift+Z redo. There
is no button. A spin commits when its value changes, so
typing 2 and then 5 is two entries and Ctrl+Z can return to
the length from before those digits. The spin's line edit
cannot. A layer name or a color still being typed undoes in
that field until it commits. Restoring a length shows the
current unit and the library still receives user units.
Restoring the mode shows that mode's knobs and does not
clear a surround or a cut. Swap, the run controls, the log,
and cuts are not entries.

## Context worth keeping

The history is a small stack in the dialog. The binding's
widgets have no undo stack. A length is stored in document
user units and restored through `_show_lengths`. Keyboard
tracking stays on. Each accepted spin value is one entry.
The line edit's own undo of a typed `25 mm` stops at `2 mm`
and then is empty, so the option history is what returns
the earlier length. Do not move that commit to
`editingFinished` alone. A layer or a color joins the
history on `editingFinished`. The same text is written back
first so the field's undo stack drops those keystrokes.

Opening the window and switching the display unit are not
entries. After inches to mm, undo of a 1 inch padding shows
4.0 mm and redo shows 25.4. Undo of a surround distance
asks again and the lines match the restored length. Apply
stays disabled. Mode restore does not ask and does not
clear a surround or a cut. On this Qt, `QKeySequence.Redo`
already matches Ctrl+Y and Ctrl+Shift+Z. The extra Shift
check matches Redo and not Undo.

A layer name still being typed has no test. A typed spin,
as opposed to `setValue`, has no test. Run controls and
work marks have no test as history entries. This stage does
not paint work marks. The pass is `cr-01.md`.

## Result

No defects remain. The named checks passed.
`QT_QPA_PLATFORM=offscreen pytest tests/test_window_options.py
tests/test_window_surround.py tests/test_window_timing.py`:
39 passed in 14.37s. Qt loaded through enaml (PyQt 5.15.11).
Nothing skipped. The tests did not start Inkscape.
