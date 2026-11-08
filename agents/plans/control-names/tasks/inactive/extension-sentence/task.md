# Extension sentence

**Status:** done

## Goal

The opening docstring of `extensions/inkscape/weedlines.py`
stops saying Start / Cancel. It stays one sentence for a
reader of that file.

## Do

Edit only the opening docstring of
`extensions/inkscape/weedlines.py`.

Where that sentence says Start / Cancel, name Start, Pause,
Clear All, Apply, and Close. Keep the log, the live
preview, and island-hop. A long run can still be stopped.
Do not name Cancel as a control, and do not name the
library exception.

The sentence is not a second window. Do not describe
Restart, the steps, or the widgets. Do not change any code
below the docstring. Do not invent conquer. Do not remove
island-hop. Leave the dialog and the uncommitted
run-control work.

## Checks

- The opening docstring does not say "Start / Cancel".
- It names Start, Pause, Clear All, Apply, and Close, and
  it still names island-hop.
- It is still a sentence for a reader of that file.
- Nothing below the docstring changes.
- No product test reads this sentence.

## Note

The opening sentence of `extensions/inkscape/weedlines.py` named
Start / Cancel. It now names Start, Pause, Clear All, Apply, and
Close, and it still names the log, the live cut preview, and
island-hop. A long run can be stopped. It does not name Cancel,
the library exception, Restart, the steps, or the widgets, and
it does not invent conquer. It is still one sentence. Nothing
below the docstring changed. The dialog was not edited.

Why: that sentence told a reader of the file to use Cancel. The
run controls are Start, Pause, Clear All, Apply, and Close.

Checked by reading the docstring and `git diff --
extensions/inkscape/weedlines.py`. The diff is those three
lines. The file does not say "Start / Cancel". No product test
reads this sentence. Status left `in-progress`.

Summary: No defects. The opening sentence names Start, Pause,
Clear All, Apply, and Close. It does not say Start / Cancel.
It still names the log, the live cut preview, and island-hop.
A long island-hop run can be stopped. It does not name the
library exception, Restart, the steps, or the widgets, and it
does not invent conquer. It is still one sentence. Nothing
below the docstring changed.

Context worth keeping: `git diff -- extensions/inkscape/weedlines.py`
is only those three docstring lines. The five names are the
run controls in `agents/architecture/runtime.md`. The title
line and the install line were already there. Other
control-names tasks edit other files and are not this change.
No product test reads this sentence. A search of `tests/`
does not match it. There is no automated test. The check was
reading the docstring and that diff. The pass is `cr-01.md`.

Result: No defects remain. The named checks passed. There
is no automated test.
