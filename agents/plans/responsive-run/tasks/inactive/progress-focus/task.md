# Progress focus

**Status:** done

## Goal

A progress check can name one object outline and one
candidate line, and pause and cancel still behave as the
runtime part says.

## Do

`src/weedlib/progress.py`. Keep `report`, `check_pause`,
`check_cancel`, and `report_segment`. Add a way for a
check to name one outline and one candidate line as plain
coordinates. A missing name means there is no mark of
that kind. The name is not a cut and not a `QPainterPath`.

Do not change solvers, the surround, or the figure check
in this task. Do not paint anything.

## Checks

`pytest tests/test_progress.py` with no Inkscape.

- A host that installed no hooks can still call the check.
- Pause blocks in the check and then returns when the host
  clears it. Cancel during the pause raises `WeedCancelled`.
- A named outline and a named line reach the host. A check
  that names neither clears the previous name.

## Note

`progress.check(outline=None, line=None)` names one object outline
and one candidate line, then pauses and cancels the same way
`check_cancel` does. `report`, `check_pause`, `check_cancel`, and
`report_segment` are unchanged. `check_cancel` does not name and
does not clear a name.

The host installs `focus(outline, line)` on `progress.install`.
Each argument is a tuple of `(x, y)` points, or `None` when that
mark is absent. A line is exactly two points. Callers may pass the
line as `(x0, y0, x1, y1)` or as two points. An omitted name or an
empty sequence is no mark of that kind. A call that names neither
sends `(None, None)` and clears the previous name. The host
receives a copy. A `QPainterPath` is rejected. The geometry hook
is not called, so the name is not a cut.

With no hooks installed, `check` still returns. Pause blocks
inside `check` until the host clears it. Cancel during that pause
raises `WeedCancelled`.

Why: a later run can name the one outline and the one trial line
it is on, without turning that name into a cut, and pause and
cancel stay on that same check.

Checked with `pytest tests/test_progress.py`: 8 passed. No
Inkscape. The new checks do not need Qt. The older solver checks
still load Qt. Solvers, the surround, the figure check, and the
window were not edited. Status left `in-progress`.

Summary: No defects. `progress.check` names one outline and one
candidate line as plain `(x, y)` points, then pauses and cancels
through `check_cancel`. A missing or empty name is no mark of
that kind, and naming neither sends `(None, None)`. The host
gets a copy through `focus`. The name is not a cut and not a
`QPainterPath`. `report`, `check_pause`, `check_cancel`, and
`report_segment` are unchanged.

Context worth keeping: `progress.install` takes
`focus(outline, line)` and still replaces the whole hook set,
so focus has to be passed on the same call as pause and cancel.
Each value is a tuple of `(x, y)` points, or `None`. A line is
exactly two points, accepted as `(x0, y0, x1, y1)` or as two
points. Naming only one mark clears the other. The name is
published before pause blocks. `check_cancel`, `report`, and
`report_segment` do not name and do not clear. A bad value,
including a `QPainterPath`, raises `TypeError` before the host
is called and before pause. The geometry hook is not called.
With no hooks, `check` returns. Importing `weedlib` still loads
Qt, so `tests/test_progress.py` does not collect without a
binding; the new tests themselves do not construct Qt objects.
Solvers, the surround, the figure check, and the window were
not edited. The pass is `cr-01.md`.

Result: No defects remain. The named checks passed.
`pytest tests/test_progress.py` passed (8 passed, no Inkscape).
