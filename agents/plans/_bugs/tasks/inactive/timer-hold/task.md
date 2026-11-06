# Timer hold

**Status:** ready

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

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
