# Extension sentence

**Status:** ready

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

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
