# Solver run

**Status:** done

## Goal

Frame, grid, and island-hop leave the window able to paint
and take input for the whole run. The solver does not run
on the GUI thread. The Qt objects the window paints are
created on it. Pause and Clear All stay cooperative at the
progress checks. The algorithm log stays the transcript.

## Do

- `extensions/inkscape/weedlines_dialog.py`: the cut branch
  of `on_start`, the nested `work` and `pump`,
  `on_pause_toggle`, `on_cancel`, and `on_close`.
- Replace `threading.Thread` with the spawn target from
  figure-check-run. Do not add another mechanism. A thread
  does not meet the goal: `generate_weeds` is Python in
  this interpreter and holds the GIL, so the GUI thread
  cannot paint. The spawned process does not share that
  GIL. Do not record the process as a product rule, and
  do not edit the guide.
- The child runs `generate_weeds` for `frame`, `grid`, and
  `island-hop`. It installs the hooks already in `work`
  (`weed_progress.install`: phase, segment, pause, cancel).
  Pause blocks in `check_pause`. Clear All is `on_cancel`:
  it raises `WeedCancelled` from `check_cancel`, including
  while paused. The child reads plain pause and cancel
  flags. Do not kill the process to pause or clear. Do
  not edit `src/weedlib/progress.py`.
- Segments stay `(x0, y0, x1, y1)` messages on the channel
  from figure-check-run. `pump` creates the line items on
  the GUI thread. `state['result']` is built there from
  plain data. The child must not touch the scene, the log
  widget, or a `QPainterPath` the window paints.
- Stdout, stderr, and the `weedlib` handler stay the
  source of the algorithm log. The child sends those
  lines. `append_log` and `drain_platform_lines` stay on
  the GUI thread. Keep the `WEEDLINES_LOG` setup `work`
  does now, in the child, so a deliberate `0` or `2`
  still survives. No second log.
- `on_close` must not `join` on the GUI thread. Set cancel
  and keep pumping until the next progress check ends the
  run. The window stays responsive while that happens.
- Do not remove the progress checks solver-checks added.
  Forward a focus named by a check to the GUI thread. Do
  not paint it.
- Do not change cut geometry, the figure check, the
  surround ask, or the display unit. No clip, piece
  border, unit dropdown, or work-mark paint. Do not emit
  conquer cuts. Do not touch
  `agents/plans/surround-and-conquer/`.

## Checks

- Geometry tests need no Inkscape. Window tests run
  offscreen when Qt loads.
- A CPU-bound hold inside the solver worker, not a sleep
  and not a GUI-thread loop: a timer on the dialog fires
  while it runs, before the run finishes.
- Pause still blocks at `check_pause`, and Resume
  continues that same run. Clear All while paused still
  raises `WeedCancelled` at the check and does not freeze
  the window.
- Frame, grid, and island-hop still receive the subject
  region (`test_start_passes_the_subject_region`). A
  parent monkeypatch of `generate_weeds` will not see the
  child. Keep the path comparison.
- The algorithm log shows that run's stdout and stderr,
  including a phase line and a stderr line from the hold.
- `pytest tests/test_progress.py tests/test_window_gate.py tests/test_cut_stroke.py tests/test_window_preview.py`
  passes. `test_clear_filled_rectangle_cuts` still returns
  a non-empty weed path for frame, grid, and island-hop.

## Note

Frame, grid, and island-hop no longer run `generate_weeds` on a
thread in this process. The cut branch of `on_start` starts one
solver ask on the existing `_geometry_worker`. The child installs
the phase, segment, pause, and cancel hooks, and the focus hook.
It sends `(x0, y0, x1, y1)` segments, log lines, the keep it
unpacked, and the result elements. `pump` is the ask pump: it
appends the log, builds the line items, and builds `state['result']`
on the GUI thread. The child does not touch the scene, the log
widget, or a path the window paints.

Pause and Clear All still set the flags. The child blocks in
`check_pause` and raises `WeedCancelled` from `check_cancel`,
including while paused. Nothing kills the process. `on_close`
does not `join`. It sets cancel and the pump keeps running until
that check ends the run, then the window closes. `WEEDLINES_LOG`
is still set to `1` only when both variables are unset, inside
the child, so `0` and `2` survive. Stdout, stderr, and the
`weedlib` handler are the one log. A focus name is stored and
not painted. `src/weedlib/progress.py` was not edited.

Why: the thread ran Python in this interpreter and held the GIL,
so the GUI thread could not paint or take input. Close also
blocked on `join` for up to 2 seconds.

Checked with `pytest tests/test_progress.py tests/test_window_gate.py tests/test_cut_stroke.py tests/test_window_preview.py tests/test_window_timing.py tests/test_window_surround.py`:
71 passed, 1 failed, 18.85s. Qt loaded. Window tests ran
offscreen. No Inkscape. The failure is
`tests/test_window_timing.py::test_hold_on_a_thread_blocks_the_gui_timer`
(`0.0001 > 0.05`). The same test passed on the next run
(0.29s). `_burn_hold` was not changed. The named four files
passed in that run, including `test_clear_filled_rectangle_cuts`
for frame, grid, and island-hop.

A parent patch of `generate_weeds` stays empty. `dialog.solver_keeps`
is the path comparison. A hold in the child lets a 0ms timer fire
before Apply, with the dialog visible. The log has the stdout
marker, the stderr marker, `[phase]`, and a `hold` line. Pause
holds that same run until Resume. Clear All while paused logs
`Cancelled.` and `Algorithm cancelled.`, does not kill the child,
and a GUI timer fires. Close returns in well under 0.3s, leaves
the dialog visible while the child is alive, and closes after the
run ends. A grid focus name is stored and is not painted.
`WEEDLINES_LOG` `0` stays quiet. `2` still logs `phase.enter`.

Outside this task: Clear All still leaves solver preview lines
up. `on_cancel` and `_after_solver` in
`extensions/inkscape/weedlines_dialog.py` do not call
`clear_weed_items`. The runtime says Clear All discards this
visit's lines. No named check failed for it. The timing flake
above is the same file's thread-hold check, not this solver.

The reviewer then writes the summary, the context worth keeping,
and the result.

## Summary

No defects remain. Frame, grid, and island-hop run `generate_weeds` in the existing `_geometry_worker` process. The GUI thread paints the segments and builds `state['result']`. Pause blocks in `check_pause`. Clear All raises `WeedCancelled` and does not kill the child. `on_close` does not join. `pytest tests/test_progress.py tests/test_window_gate.py tests/test_cut_stroke.py tests/test_window_preview.py` passed (48 passed, 12.71s). Qt loaded. No Inkscape.

## Context worth keeping

`_ask_solver` is a branch of `_geometry_worker`, started with `multiprocessing` spawn through `_spawn_ask`. One ask at a time. The child sends segments as `(x0, y0, x1, y1)`, log lines, the packed keep, and the packed result. It does not send a `QPainterPath` and does not touch the scene or the log widget. `_pump_ask` on the GUI thread appends the log, creates the line items, and `_after_solver` unpacks `state['result']`.

Pause and Clear All set the flags. The child blocks in `check_pause` and raises `WeedCancelled` from `check_cancel`, including while paused. Nothing kills the process. `on_close` sets cancel and returns while the solver process is alive. The pump ends the run, then the window closes. It does not join. `_reap_proc` calls `join(0)` only after the process is already dead.

`WEEDLINES_LOG` is set to `1` in the child only when both variables are unset or empty. Stdout, stderr, and the `weedlib` handler are the one log. A focus name is stored and not painted. A parent patch of `generate_weeds` stays empty. `dialog.solver_keeps` matches the subject region. The frame, grid, and island-hop results match an in-process `generate_weeds` after the pack round-trip. `src/weedlib/progress.py` and the solvers were not edited. Classify, subject, and surround still use the same target. `pytest tests/test_window_timing.py tests/test_window_surround.py` passed (24 passed, 6.69s).

`tests/test_window_timing.py::test_hold_on_a_thread_blocks_the_gui_timer` failed once in 20 runs (`assert 3.8e-05 > 0.05`, line 338). `_burn_hold` matches `93cd4be`, and that body failed 3 of 30 times on its own. This diff did not cause it. Clear All still leaves solver preview lines up. Parent `on_cancel` did not call `clear_weed_items` either. That discard is already `agents/plans/window-clarity/tasks/active/run-controls/task.md`. No named check failed. The pass is `cr-01.md`.

## Result

No defects remain. The window stays visible and a GUI timer can fire while frame, grid, or island-hop runs in the child. Pause resumes the same run. Clear All while paused cancels without killing the child. Close returns immediately and the dialog closes after the run ends.
`pytest tests/test_progress.py tests/test_window_gate.py tests/test_cut_stroke.py tests/test_window_preview.py` passed (48 passed, 12.71s, Qt loaded, no Inkscape).
