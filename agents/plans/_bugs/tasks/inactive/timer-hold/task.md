# Timer hold

**Status:** done

## Goal

`test_hold_on_a_thread_blocks_the_gui_timer` passes on
repeated runs. A thread hold in this process still blocks
a GUI timer. A hold in the child still does not.

## Do

Confirmed. In `tests/test_window_timing.py`,
`test_hold_on_a_thread_blocks_the_gui_timer` fails when
`processEvents` returns before the worker enters the
non-yielding loop. The assert at line 338 sees about 0
instead of more than 0.05. It failed 1 of 20 runs with
the current dialog, and 3 of 30 on the same `_burn_hold`
body at `93cd4be`. The solver spawn did not cause it.

Make that check stable. Do not change it so a thread
hold that does not block the timer still passes. Do not
edit the guide. Do not move the figure check, the
surround, or the solvers.

## Checks

Run `pytest tests/test_window_timing.py` at least 20
times, offscreen when Qt loads, with no Inkscape.

- The thread-hold check passes on every run.
- The child-hold check still passes.
- A thread hold that returns at once still fails the
  thread-hold check.

## Note

`test_hold_on_a_thread_blocks_the_gui_timer` holds the worker
on an event until just before `processEvents`, then arms a
0ms timer and calls `processEvents` until that call both
delivers the timer and takes more than 0.05s. One call could
return before the worker reached the non-yielding loop. The
dialog was not edited.

Why: the old check measured a single `processEvents`. That
call can return while the worker is still starting, so the
assert saw about 0. A hold that returns at once still leaves
that call near 0, and the assert fails.

Checked with `QT_QPA_PLATFORM=offscreen pytest
tests/test_window_timing.py`: 20 runs, 6 passed each time.
Qt loaded. No Inkscape. The child-hold check passed in those
runs. A `_burn_hold` that returns at once failed the
thread-hold check at `assert blocked > 0.05` (`3.7e-05`).
Status left `in-progress`.

## Summary

No defects remain. The thread-hold check waits until the
worker is released, then calls `processEvents` until that
call both delivers the timer and takes more than 0.05s. A
hold that returns at once still fails that assert. The
dialog was not edited. The child-hold check is unchanged
and still shows the child can paint.

## Context worth keeping

The only edit is `test_hold_on_a_thread_blocks_the_gui_timer`
in `tests/test_window_timing.py`. The worker waits on an
event, then runs `_burn_hold(20000000)`. One `processEvents`
can still return before that loop. The test keeps calling
until the same call appends to `fired` and takes more than
0.05s. Three direct runs needed more than one call. The
call that passed took about 0.22s. Earlier calls were about
0 or about 0.005s.

An immediate `_burn_hold` still fires the timer and fails
at line 357, `assert blocked > 0.05`. `blocked` was about
3.5e-05.

`test_figure_check_hold_lets_the_gui_timer_fire` was not
edited. The timer records that the dialog is visible and
the child is alive, and every sample must be true.
`extensions/inkscape/weedlines_dialog.py` has no diff.

## Result

No defects remain. The named checks passed.
`QT_QPA_PLATFORM=offscreen pytest tests/test_window_timing.py`
passed 20 of 20 runs, 6 passed each time (1.80s to 1.84s).
Qt loaded. Nothing skipped. The tests did not start
Inkscape. Pid 471572 was already running; that pid and its
start time were unchanged. A direct call of the thread-hold
check passed 80 of 80 times. No bug outside this change.
