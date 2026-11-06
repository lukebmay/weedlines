# Surround run

**Status:** done

## Goal

The window keeps handling paint and input while the surround
runs. `build_surrounds` does not run on the GUI thread. The
surround paths the window paints are created on it.

## Do

- `extensions/inkscape/weedlines_dialog.py`. Use the spawn
  target from figure-check-run. Do not add a second
  mechanism, and do not record the process as a product rule.
- `_ask_surrounds` calls `build_surrounds` on the GUI thread.
  The callers are the surround branch of `on_start`,
  `_on_swap`, `_on_mode`, and `_on_surround_length`. Move
  that call onto the spawn target. The same GIL reason as
  the figure check: a thread in this process cannot paint
  while that Python runs.
- Plain values come back. The GUI thread builds the paths,
  then `refresh_preview` paints them. Do not call
  `generate_weeds`. This step writes no result.
- Do not block the GUI thread on the child. One ask at a
  time, applied before the next. If a newer distance, join
  gap, or swap is already waiting, drop the older result
  and do not paint it.
- Pause and Clear All take effect at the progress checks
  surround-checks added. Do not remove those checks, and
  do not edit the surround module. Clear All is
  `on_cancel`. Do not rename it. Do not kill the child to
  pause or clear. If abort is set when the paths arrive,
  discard them. Forward a focus named by a check to the
  GUI thread. Do not paint it.
- The child's stdout and stderr use `append_log`. That log
  is the transcript.
- Leave the frame, grid, and island-hop branch of
  `on_start` on its current worker.
- No clip, piece border, unit dropdown, or work-mark paint.
  No Conquer. Do not edit the surround library, and do not
  touch `agents/plans/surround-and-conquer/`.

## Checks

- `pytest tests/test_window_surround.py tests/test_window_timing.py`
  with the window tests offscreen when Qt loads.
- A CPU-bound hold inside the surround worker, not a sleep:
  a timer on the dialog fires before the surround is
  painted, the dialog stays visible, and Start in this mode
  does not run the solver or enable Apply.
- Distance, join gap, swap, and returning to this mode ask
  again. A defect does not ask. Change surround clears the
  lines and returns to the wait.
- A parent monkeypatch of `build_surrounds` will not see
  the child. Keep the existing proofs on the worker or the
  painted strokes.

## Note

`_ask_surrounds` no longer calls `build_surrounds` on the GUI
thread. The surround branch of `on_start`, a swap after the new
regions are stored, returning to this mode, and a distance or
join change start one surround ask on the existing
`_geometry_worker`. The child sends plain path elements. The
GUI thread builds the paths and `refresh_preview` paints them.
`generate_weeds` stays on the frame, grid, and island-hop
worker. `src/weedlib/surround.py` was not edited.

Why: that call held the GUI thread, so the window could not
paint or take input. The parent waits with `QTimer.singleShot`.
It does not join or kill the child. One ask at a time. If the
distance, join gap, or swap changed while that ask was in
flight, the arrival does not paint those paths and the newer
ask starts. Clear All is still `on_cancel`. It sets the cancel
event. If abort is set when the paths arrive, they are
discarded and the step returns to the wait. Pause is mirrored
and blocks at the progress checks. A focus name is stored on
`dialog.focus_mark` and is not painted. Child stdout and
stderr use `append_log`. `_ASK_HOLD`, when set, is the same
tight loop in the child before the library call. Opening stays
locked until the first paint is stored, then the form unlocks.
During a surround ask, distance, join, swap, and mode stay
live so a newer value can wait.

Checked with `pytest tests/test_window_surround.py
tests/test_window_timing.py`: 24 passed in 6.72s. Qt loaded.
Window tests ran offscreen. No Inkscape. A parent patch of
`build_surrounds` stays empty. `dialog.worker_calls`,
`dialog.surround_args`, and the painted strokes are the proof.
A hold in the child lets a 0ms timer fire before the surround
is painted. The dialog stays visible. Start does not run the
solver or enable Apply. The same hold on a thread in this
process still blocks a GUI timer. Distance, join gap, swap,
and returning to this mode ask again. A defect does not.
Change surround clears the lines and does not ask. A newer
distance, join, and swap during the hold is not painted.
Pause holds until Resume. Clear All discards the paths and
does not kill the child. `tests/test_window_preview.py`,
`tests/test_window_return.py`, and `tests/test_window_gate.py`
also passed after the form unlock (44 passed in 10.19s,
including the two named files).

Outside this task: `on_close` still joins the solver thread
for up to 2 seconds in `extensions/inkscape/weedlines_dialog.py`.
solver-run already owns that join. No check in this run failed
for it. The two Apply checks in `tests/test_cut_stroke.py`
pass on frame.

The reviewer then writes the summary, the context worth keeping,
and the result.

## Summary

No defects remain. `build_surrounds` runs on the existing
`_geometry_worker` spawn target. The GUI thread builds the paths
and `refresh_preview` paints them. A newer distance, join gap, or
swap is not painted from the older ask. Close does not join that
process. `pytest tests/test_window_surround.py
tests/test_window_timing.py` passed (24 passed, 6.62s).

## Context worth keeping

`_ask_surround` is a branch of `_geometry_worker`, started with
`multiprocessing` spawn through `_spawn_ask`. One ask at a time.
The child sends plain `surround` elements and `odd` or `wind`. It
does not send a `QPainterPath`. The GUI thread rebuilds the paths
in `_after_surround`. A parent patch of `build_surrounds` stays
empty. `dialog.worker_calls`, `dialog.surround_args`, and the
painted strokes are the proof.

Start, a distance or join change, a swap after the new regions are
stored, and returning to this mode each ask that way. The parent
waits with `QTimer.singleShot`. It does not join or kill the child.
If the distance, join gap, or swap changed during the ask, that
arrival is not painted and the newer ask starts. A swap runs the
subject ask first. Clear All is `on_cancel`. It sets the cancel
event. Paths that arrive after abort are discarded. Pause blocks at
the progress checks. A focus name is stored on `dialog.focus_mark`
and is not painted. Child stdout and stderr use `append_log`.

`_ASK_HOLD` is the tight loop in the child before the library call.
The same loop on a thread in this process blocks a GUI timer.
Opening unlocks after the first paint. During a surround ask,
distance, join, swap, and mode stay live. Frame, grid, and
island-hop still use their thread and `generate_weeds`.
`src/weedlib/surround.py` was not edited.

`on_close` still joins the solver thread for up to 2 seconds when
that thread is alive. A surround ask does not start it, so this
close does not wait on the geometry process. The join was not made
worse. It is already the solver-run task. No check in the named
files failed for it. The pass is `cr-01.md`.

## Result

No defects remain. The window stays visible and a GUI timer can
fire while the surround runs in the child. The painted strokes are
the paths built on the GUI thread. An older distance, join gap, or
swap is not painted. `pytest tests/test_window_surround.py
tests/test_window_timing.py` passed (24 passed, 6.62s, Qt loaded,
no Inkscape).
