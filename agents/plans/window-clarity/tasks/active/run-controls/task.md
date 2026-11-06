# Run controls

**Status:** ready

## Goal

One status and a spinner, and the run controls Start,
Restart, Pause, Clear All, Apply, and Close. Frame, grid,
and island-hop are each one step. Surround and Conquer
shows the surround, then conquer.

## Do

`extensions/inkscape/weedlines_dialog.py`. responsive-run
is already required, so the GUI thread stays responsive.
Do not move the figure check, the surround, or a solver
off that thread, and do not wait on that plan.

Frame, grid, and island-hop each have one Start control,
object name `start`. It reads Start until that step has
been started, then Restart until Clear All. Restart stays
disabled while the step is actively running. It discards
that step's lines and runs the step again.

Surround and Conquer shows two steps: Surround, then
Conquer. Surround uses that same Start control. Conquer is
shown as the step that is left. Its Start stays disabled.
The library emits no conquer cuts, and this task does not
define them. A phase name from the library does not become
another step.

Pause holds a cut at the next progress check and leaves
the lines up. Resume continues that same run. Do not add
progress calls inside the library. Clear All aborts,
including while paused, and discards this visit's lines
and result. Option values, swap, and colors stay. Close
while a run is going aborts and returns nothing.

Remove Cancel and Change surround. Clear All is what
returns the surround to the wait. Restart is what runs
that step again. The hint does not name Cancel.

One status: ready, working, paused, or done. A phase name
from the library may appear in that status. A spinner
shows only while the run is working and is not paused.
Idle and Clear All are ready. A finished step is done.

Apply still returns weed lines and stays off when the
surround step produced none. An empty surround is still
that one step: no invented lines. Leave option undo in
place. Do not add work marks or the piece border.

## Checks

Offscreen, when Qt loads. Update
`tests/test_window_surround.py`,
`tests/test_window_timing.py`, and `_finish_start` in
`tests/test_window_gate.py` so a cut still completes.

- No Cancel button and no Change surround button.
- Frame, grid, and island-hop show one step. Surround and
  Conquer shows Surround and Conquer. Conquer's Start is
  disabled and produces no cuts. A library phase name does
  not add a step.
- After the surround step, the button reads Restart, the
  status is done, and the spinner is hidden. Start on
  that step does not run a solver.
- While a cut is running, the status is working and the
  spinner shows. Pause hides the spinner, leaves the
  lines, and Resume continues that run.
- Clear All, including from pause, drops the lines and
  the result, keeps the mode and a color, and the status
  is ready. The start button reads Start again.
- Close during a run returns nothing.

## Note

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
