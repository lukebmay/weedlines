# Figure check run

**Status:** done

## Goal

The window keeps handling paint and input while the figure
check runs. That geometry does not run on the GUI thread.
The Qt objects the window paints are created on it.

## Do

- Product change in `extensions/inkscape/weedlines_dialog.py`.
  `_shown` calls `classify_figures`, `_ensure_regions`
  (`subject_weed_regions`), and `refresh_preview`
  (`build_arrow_paths`, `_painted_parts`) on the GUI thread.
  Move those library calls off it.
- Add one module-level spawn target in that file. Start it
  with spawn, not fork: the window already has a
  `QApplication`. A nested function cannot be that target.
- A `threading.Thread` does not meet the goal. The check is
  Python in the window's interpreter, so the thread holds the
  GIL and the GUI thread cannot paint. A spawned process has
  its own interpreter, so this process can paint and take
  input. Do not record that process as a product rule, and
  do not edit the guide.
- Do not satisfy this by calling the library on the GUI
  thread and pumping `processEvents`.
- The child loads Qt only for the library call and shows no
  window. It returns plain values (strings, numbers, point
  pairs). It does not return a `QPainterPath` or any other
  Qt object. The GUI thread turns element type and
  coordinates into the paths `refresh_preview` paints, so
  the painted path matches the library path. Do not change
  `src/weedlib/figures.py` or the arrow module.
- Wait with the event loop, the way `on_start` already uses
  `QTimer.singleShot`. `_shown` must not block on the child.
  `ready` still runs after that preview is painted, and the
  window is already visible. `on_close` must not join the
  child on the GUI thread.
- One ask at a time. Apply the plain result on the GUI
  thread before the next ask starts. Messages, not a single
  final blob, so a later task can send a log line or a
  segment on the same channel. Do not stream solver
  segments here.
- `_on_swap` uses this ask for a new subject and weed area.
  A plugin color repaints the paths already applied. It
  does not run the figure check again. If that swap still
  needs a surround, call the existing `_ask_surrounds` only
  after the regions are applied. Do not move
  `build_surrounds` or `generate_weeds`.
- Until the first paint, Start, Swap, and the surround
  controls stay inactive, as they do while `_shown` runs
  today. Close still works. Pause and Clear All take
  effect at the progress checks figure-checks added. Do
  not remove those checks, and do not edit
  `src/weedlib/figures.py` in this task. Do not kill the
  child to cancel. If Close won, drop the result when it
  arrives. Forward a focus named by a check to the GUI
  thread. Do not paint it.
- The child's stdout and stderr reach the existing
  algorithm log through `append_log`. No second transcript.
- No clip, piece border, unit dropdown, or work-mark paint.
  No Conquer. Do not touch
  `agents/plans/surround-and-conquer/`.

## Checks

- Geometry tests need no Inkscape. Window tests run
  offscreen when Qt loads, as they already do.
- The spawn target takes a plain hold. Unset, it does
  nothing. Set, the child runs a tight Python loop, not a
  sleep, before the library call. A single-shot timer armed
  on the dialog when the ask starts fires before `ready`,
  and the dialog is visible. The same loop on a thread in
  this process fails the check.
- `tests/test_window_timing.py` still shows one figure
  check and one subject ask, no surround and no solver,
  after the window is visible and before `ready`. A parent
  monkeypatch of `classify_figures` will not see a child
  call. Point that proof at the worker or the painted
  preview. Do not drop it.
- `pytest tests/test_figures.py tests/test_window_timing.py tests/test_window_preview.py tests/test_window_return.py`
  passes. The return test that patches `build_arrow_paths`
  must still prove the written arrows are the paths the
  preview paints.

## Note

`_shown` starts one classify ask and returns. The subject ask
starts after that result is applied on the GUI thread. Both use
the module-level target `_geometry_worker`, started with
`multiprocessing` spawn. The child sends messages (`log`,
`focus`, `call`, `figure`, `defect`, `path`, `bounds`, `fill`,
`arrow`, `cancelled`, `error`, `done`). A `segment` message is
accepted onto the existing segment queue. This ask does not send
one. The GUI thread rebuilds `QPainterPath` and `ArrowPath`
values from element kinds and coordinates, and `refresh_preview`
paints those. A plugin color uses the stored paths. Swap starts
a subject ask for the new subject and weed area.
`_ask_surrounds` runs after those regions are stored, and only
when a surround is already started. `build_surrounds` and
`generate_weeds` stay in this process.

Why: the figure check, the subject and weed area, and the arrow
paths were running on the GUI thread, so the window could not
paint or take input. The parent waits with `QTimer.singleShot`.
`ready` runs after the preview is painted, with the window
already visible. Close sets a drop flag and the cancel event. It
does not join the geometry process and does not kill it. Pause
and Cancel are mirrored onto that process and take effect at the
progress checks. A focus name is stored on the dialog and is not
painted. Child stdout and stderr arrive as log messages.
`_ASK_HOLD` is a tight loop in the child before the library
call. Unset, it does nothing. Path kinds use `_plain_int`
because the spawned interpreter's element type is an enum. Fill
rules travel as `odd` or `wind`, and the GUI thread applies
`Qt.OddEvenFill` or `Qt.WindingFill` when the path has elements.

Checked with `pytest tests/test_figures.py
tests/test_window_timing.py tests/test_window_preview.py
tests/test_window_return.py`: 57 passed in 15.80s. Qt loaded.
Window tests ran offscreen. The timing tests show one classify
and one subject ask before `ready`, with no surround and no
solver. A parent patch of `classify_figures` stays empty;
`dialog.worker_calls` and the painted paths are the proof. A
hold on a thread in this process blocks a GUI timer. The same
hold in the child lets a 0ms timer fire before `ready` while the
dialog is visible and `_shown` has returned. The return test
matches the written arrows to the paths the preview paints.
`src/weedlib/figures.py`, the surround module, and the solvers
were not edited. Status left `in-progress`.

Outside this task: `on_close` still joins the solver thread for
up to 2 seconds. `tests/test_cut_stroke.py` still fails
`test_untouched_apply_returns_the_initial_color` (`None ==
'#FF0000'`) and `test_apply_returns_the_changed_weed_line_color`
(`None == '#00AA00'`). Start on the default Surround and Conquer
mode paints a surround and leaves Apply disabled, so those
dialogs return `(None, None, None)`.

The reviewer then writes the summary, the context worth keeping,
and the result.

## Summary

No defects remain. The figure check, the subject and weed area, and the arrow paths run in one spawned process. The GUI thread rebuilds the painted paths. `_shown` returns before `ready`. Close does not join that process. `pytest tests/test_figures.py tests/test_window_timing.py tests/test_window_preview.py tests/test_window_return.py` passed (57 passed, 17.61s).

## Context worth keeping

`_geometry_worker` is the module-level spawn target. One ask at a time. Classify is applied on the GUI thread before the subject ask starts. Messages are `log`, `focus`, `call`, `figure`, `defect`, `path`, `bounds`, `fill`, `arrow`, `cancelled`, `error`, `done`, and `segment`. This ask does not send `segment`. The parent waits with `QTimer.singleShot`. Swap waits in `processEvents` so the click returns after the new paint. The library call is still in the child.

Path kinds use `_plain_int`. Fill rules travel as `odd` or `wind`. A cubic, a quad, a winding rule, and the boolean subject and weed area round-trip. A parent patch of `classify_figures` stays empty. `dialog.worker_calls` and the painted paths are the proof. `_ASK_HOLD` is a tight loop in the child. The same loop on a thread here blocks a GUI timer.

Close sets the drop flag and the cancel event. It does not join the geometry process and does not kill it. Pause and Cancel are mirrored and take effect at the progress checks. A focus name is stored and not painted. Child stdout and stderr reach the algorithm log. `build_surrounds` and `generate_weeds` stay in this process. `src/weedlib/figures.py` was not edited.

The two `tests/test_cut_stroke.py` Apply failures already fail on `d08fccd`. `on_close` still joins the solver thread. That join was not made worse. It is already the solver-run task. The pass is `cr-01.md`.

## Result

No defects remain. The window stays visible and a GUI timer can fire while the figure check runs in the child. The painted arrows are the paths the correction result writes.
`pytest tests/test_figures.py tests/test_window_timing.py tests/test_window_preview.py tests/test_window_return.py` passed (57 passed, 17.61s, Qt loaded, no Inkscape).
