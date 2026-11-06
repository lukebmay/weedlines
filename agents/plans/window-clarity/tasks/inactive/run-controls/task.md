# Run controls

**Status:** done

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

The window has one status and a spinner, and the run controls
are Start, Restart, Pause, Clear All, Apply, and Close. Cancel
and Change surround are gone. The hint names Pause, Resume, and
Clear All.

Frame, grid, and island-hop each show one step. Surround and
Conquer shows Surround, then Conquer. One Start button, object
name `start`, moves onto the step that can run. It reads Start
until that step has been started, then Restart until Clear All.
Restart stays disabled while the step is running. It drops that
step's lines and runs the step again. Conquer's Start, object
name `conquer-start`, stays disabled and does nothing. A phase
name from the library is written into the one status. It does
not add a step.

The status is ready, working, paused, or done. A phase may
follow working or paused. The spinner shows only while the run
is working and is not paused. Idle and Clear All are ready. A
finished step is done, including an empty surround. That step
does not invent lines and does not enable Apply. Apply still
returns cuts from frame, grid, and island-hop.

Pause holds the cut at the next progress check and leaves the
lines up. Resume continues that same run. Clear All, including
from pause, aborts and drops this visit's lines and result.
Option values, swap, and colors stay. Close while a run is
going aborts and returns nothing. The geometry child is not
joined. No progress call was added in the library.

The new step rows and the status row made the window's size
hint too short for the preview. The splitter keeps the log and
the preview, and the dialog's minimum height is that hint
before it is shown, so the return line stays under the preview.

Checked offscreen, no Inkscape, from the repo root:
`pytest tests/test_window_surround.py tests/test_window_timing.py
tests/test_window_gate.py tests/test_window_return.py
tests/test_window_options.py tests/test_window_preview.py`:
71 passed. Status left `in-progress`.

The reviewer then writes the summary, the context worth keeping,
and the result.

## Summary

No defects. The window has one status and a spinner. The
run controls are Start, Restart, Pause, Clear All, Apply,
and Close. There is no Cancel button and no Change surround
button. The hint does not name Cancel.

Frame, grid, and island-hop each show one step. Surround
and Conquer shows Surround, then Conquer. One Start button,
object name `start`, reads Start until that step has been
started, then Restart until Clear All. It stays disabled
while the step is running. Conquer's Start stays disabled
and produces no cuts. A phase name is written into the one
status. It does not add a step.

After the surround step the button reads Restart, the
status is done, and the spinner is hidden. That step does
not run a solver. Apply stays off. While a cut is running
the status is working and the spinner shows. Pause hides
the spinner and Resume continues that run. Clear All,
including from pause, drops the lines and the result, keeps
the mode and a color, and the status is ready. The button
reads Start. Close during a run returns nothing and does
not join the geometry child.

## Context worth keeping

The status words are ready, working, paused, and done. A
phase is `working: <name>` or `paused: <name>` while that
run is busy. Finish clears the phase and shows done.
`dialog.last_phase` keeps the last name. No test reads the
status text that includes the phase. The label list is
what shows that a phase did not add a step.

Clear All drops the lines and the result in the window,
then sets cancel. It does not kill the child. The status
is ready while the child is still stopping, and Pause
stays visible until that child finishes. The mode, the
lengths, swap, and the colors are not written. A later
Start asks again. An empty surround has no test. The
finish path still marks that step done and does not set
a result.

Close on a live solver waits for the next progress check,
then rejects. `join` is only `join(0)` after the child is
already dead. Close on a surround ask rejects immediately.
That branch has no test. The phase message is sent from
the solver hook in the child. The library diff is empty.

On this Qt the size hint and the minimum height are 998.
The open size is 720 by 998. The preview stays 180 tall
and the return line sits under it. The window cannot be
shortened below that hint. The log still says
`Cancel requested` and `Cancelled.` The hint and the
buttons do not. This diff does not edit docs.

`test_clear_check_has_an_empty_line_and_start_works` still
observes the child. Do not patch `generate_weeds` on the
parent. The pass is `cr-01.md`.

## Result

No defects remain. The named checks passed.
`QT_QPA_PLATFORM=offscreen pytest tests/test_window_surround.py
tests/test_window_timing.py tests/test_window_gate.py
tests/test_window_return.py tests/test_window_options.py
tests/test_window_preview.py`: 71 passed in 30.92s. Qt
loaded through enaml (PyQt 5.15.11). Nothing skipped. The
tests did not start Inkscape.
