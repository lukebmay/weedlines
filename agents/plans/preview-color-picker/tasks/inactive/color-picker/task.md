# Color picker

**Status:** done

## Goal

Each of the four preview colors opens a color picker, the
window shows the chosen color, and a committed color still
undoes.

## Do

The four settings stay Checkerboard light, Checkerboard
dark, Weed line color, and Default subject color.
`extensions/inkscape/weedlines_dialog/form.py` owns them,
including `_color_edit` and the option history.
`extensions/inkscape/weedlines_dialog/__init__.py` adds
the four rows and is where a finished color edit commits
today.

Each setting opens a color picker. After the person
chooses a color, that setting shows it. The other three
stay as they were. The initial colors stay the ones the
window already opens with. A choice commits the way a
finished color edit does now.

A committed color joins the option history the form
already uses. Undo and redo restore it on the setting and
in the preview. Opening the window is not an entry. A
color that is not committed yet does not enter the
history and does not change the preview. If the setting
still has an uncommitted edit, undo changes that edit
first and does not undo the previous committed option.
Do not add undo or redo buttons.

`extensions/inkscape/weedlines_dialog/preview.py` paints
from these four settings. Change it only if a chosen
color would not otherwise be the color it paints. The
correction arrows stay `#FF00FF`, `#FF6A00`, and
`#00E5FF`. They are not picker settings. Do not add rows
for them, and do not edit the library colors.

`extensions/inkscape/weedlines_dialog/run_controls.py`
enables and disables the four settings while a run is
busy. A busy run still does not take a new color,
including from the picker. Update this file only if
disabling the four settings would leave the picker
usable.

The window does not write a preferences file. Do not
store the colors in one. Apply still returns the
weed-line color the person set.

Leave `extensions/inkscape/weedlines_dialog/README.md`
as it is unless the picker is a new source file. Then
add one sentence for that file. The four settings stay
the options form's.

Do not edit the guide.

## Checks

Offscreen, when Qt loads. No Inkscape. The check chooses
a color through the picker the setting opens. It does not
stop for a person.

- Each of the four settings opens a color picker, and the
  chosen color shows on that setting.
- The preview paints that color where the setting already
  paints. Choosing one color does not change the other
  three.
- Undo and redo of a committed color restore it on the
  setting and in the preview. An uncommitted edit, when
  the setting still has one, does not enter the history.
- The arrow colors stay `#FF00FF`, `#FF6A00`, and
  `#00E5FF`, and the form has no picker setting for them.
- Changing a color does not write a preferences file.
- While a run is busy, the four settings do not take a
  new color.

Window tests that commit these colors do it as line edits
today: `tests/test_window_options.py`,
`tests/test_window_preview.py`,
`tests/test_window_timing.py`,
`tests/test_window_border.py`,
`tests/test_window_surround.py`, and
`tests/test_window_surround_run.py`.
`tests/test_window_units.py` expects the four settings to
be line edits that stay visible. If a setting is no
longer a line edit, update those lookups so the same
checks still commit a color. Add a check that fails when
a setting does not open a picker. Do not add a test whose
only job is the missing preferences file.

## Note

The four preview colors are tinted buttons. Each opens the Qt color
dialog. Accepting commits through the option history a finished color
edit already used, and the button shows the color. Cancelling, or
undoing text still being typed in the picker, does not enter that
history and does not change the preview. Custom colors are hidden so
the dialog does not write a Qt preferences file. The arrow colors are
unchanged and are not settings. A busy run still disables the four
buttons, so the picker does not open.

Checked offscreen, no Inkscape, with `QT_QPA_PLATFORM=offscreen
python3 -m pytest tests/test_window_options.py
tests/test_window_preview.py tests/test_window_timing.py
tests/test_window_border.py tests/test_window_surround.py
tests/test_window_units.py tests/test_window_surround_run.py
tests/test_cut_stroke.py`: 76 passed. Accepting a color in the picker
wrote no preferences file.

The reviewer then writes the summary, the context worth keeping,
and the result.

## Summary

No defects. Each of the four settings is a tinted button.
Clicking it opens a non-native Qt color dialog. Accepting
commits through the option history a finished color edit
already used, and the button shows that color. The other
three stay as they were. Cancelling, or undoing text still
being typed in the picker, does not enter the history and
does not change the preview. Custom colors are hidden so
the dialog does not write a Qt preferences file. The arrow
colors stay `#FF00FF`, `#FF6A00`, and `#00E5FF` and are not
settings. A solver run still disables the four buttons, so
the picker does not open. Apply still returns the weed-line
color.

## Context worth keeping

`_color_edit` still owns the four settings and now returns
a `QPushButton`. The object names are unchanged. Commit
stays `_commit_color`: it reads the button text, stores the
uppercase hex on the `color` property, tints the button,
repaints, and pushes the option stack. The same color
again is not an entry. Opening the window is not an entry.

The picker is parented to the dialog, named `color-picker`,
and uses `DontUseNativeDialog`. The platform dialog cannot
be driven offscreen, and it can store colors. Custom
colors are hidden before `exec_`: the Add button, the
custom-colors label, and that label's wells. Qt writes
`QtProject.conf` when a custom color is set and that dialog
is destroyed. Hiding those controls leaves no file, and
Alt+A does not add a color. The task forbids a test whose
only job is the missing file.

While a picker is visible, the option-key filter does not
take Ctrl+Z, so the hex field undoes first. After it
closes, the filter still handles undo when the key target
is the dialog or a descendant. The active window may not
be the dialog then. The button sets `autoDefault` and
`default` false so it is not the dialog default. The fill
needs a border in the style sheet or Qt does not paint it.

A border ask is not a run. `run_controls.py` was not
edited: it still re-enables the four settings for that
ask. `_open_color` allows the picker then, and refuses it
when the button is disabled or the ask is a real run.
`preview.py` was not edited. It still paints the `color`
property. The dialog README and the guide were not edited.

## Result

No defects remain. The named checks passed.
`QT_QPA_PLATFORM=offscreen python3 -m pytest tests/test_window_options.py tests/test_window_preview.py tests/test_window_timing.py tests/test_window_border.py tests/test_window_surround.py tests/test_window_units.py tests/test_window_surround_run.py tests/test_cut_stroke.py`:
76 passed in 23.48s. Qt loaded through enaml (PyQt 5.15.11,
Qt 5.15.14). Nothing skipped. The tests did not start
Inkscape. Accepting colors under a fresh `XDG_CONFIG_HOME`
wrote no preferences file. The pass is `cr-01.md`.
