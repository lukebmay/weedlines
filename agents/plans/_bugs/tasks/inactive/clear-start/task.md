# Clear start

**Status:** done

## Goal

A clear figure check still has an empty return line, and
Start on frame runs.

## Do

Confirm the report on master before editing anything.

The report: `test_clear_check_has_an_empty_line_and_start_works`
in `tests/test_window_return.py` ends with "start did not
run". The empty-line asserts pass. The test patches
`weedlib.generate_weeds` in the parent process. The solver
runs in a spawned child.

If the test passes on master, stop. It is unconfirmed.

If it fails that way, fix the check so Start on a clear
frame is observed. Keep the empty line and the absent
correction action. Do not drop those asserts. Do not edit
the guide. Do not change cut geometry. Edit
`extensions/inkscape/weedlines_dialog.py` only if the run
itself is wrong.

## Checks

Offscreen, when Qt loads. No Inkscape.

`pytest tests/test_window_return.py::test_clear_check_has_an_empty_line_and_start_works`

The empty line and the missing correction action still
hold. Start on frame is observed.

## Note

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.

Confirmed on master `081dcec`. Nothing was changed. The dirty
dialog and tests in the main checkout were not used.

Ran from a detached worktree at
`/tmp/weedlines-clear-start-081dcec` (HEAD `081dcec`), then
removed it:

`QT_QPA_PLATFORM=offscreen pytest tests/test_window_return.py::test_clear_check_has_an_empty_line_and_start_works`

Failed in 5.47s. Qt loaded (PyQt6 6.7.1). No Inkscape. The
rootdir was the worktree.

```
AssertionError: start did not run
assert 'start did not run' is None
```

at `tests/test_window_return.py:326`
(`assert holder['error'] is None`).

The empty-line asserts passed before that error. They run in
`drive()` before Start is clicked and before the poll sets
`holder['error']`. Pytest failed only on the later assert, so
`line.text() == ''` and the absent correction action had
already passed. Start was enabled on every mode. The parent
patch of `weedlib.generate_weeds` did not observe a run:
`seen` stayed empty or Apply never enabled, for 100 polls.

Reproduced on this tree at `5df5b07` before editing. The empty
line and the absent correction action still held, and Start
was enabled on every mode. One poll after Start on frame,
Apply was enabled, `worker_calls` included `solver`, and
`solver_keeps` was `frame`. The parent `seen` list stayed
empty. The log was `Starting frame…`, `[phase] frame`, and
`Done. Review cuts, then Apply.` Start does launch the
solver. The parent patch cannot see the child, because
`_ask_solver` imports `generate_weeds` in the spawned
process. The dialog was not edited.

The check now waits until Apply is enabled and the child has
reported a keep. It then requires that keep to be `frame`
and exactly one `solver` call. Apply stays disabled until
the child returns a non-empty result, so a run that does
not happen still sets `start did not run`. The empty line
and the absent correction action are unchanged. The parent
patch of `generate_weeds` is gone.

Checked offscreen, no Inkscape, with `QT_QPA_PLATFORM=offscreen`.
Qt loaded (PyQt6 6.7.1).

`pytest tests/test_window_return.py::test_clear_check_has_an_empty_line_and_start_works`:
1 passed in 0.49s.

`pytest tests/test_window_return.py tests/test_window_timing.py`:
11 passed in 3.52s.

Review summary: no defect remains. The check still tests
the product. A clear figure has an empty return line and
no correction action. Start on frame is observed. Apply
enables only after the child returns a path that is not
empty, the keep mode is `frame`, and there is one
`solver` call. A run that does not happen still sets
`start did not run`. The dialog was not edited. The pass
is `cr-01.md`.

Context worth keeping: `_ask_solver` imports
`generate_weeds` in the spawned child. It sends `keep`
and the `solver` call before it calls `generate_weeds`.
The parent cannot patch `generate_weeds`. `solver_keeps`
stores the mode from that `keep`. `_after_solver` enables
Apply only when the returned path is not empty. The wait
needs both,
then requires `['frame']` and one `solver` call. Apply
starts disabled, and `on_start` clears the result, so a
click that does not start the child still fails. The
empty line and the absent correction action are asserted
before Start. The swatches from `5df5b07` stay on the
defect line, in
`test_defect_line_and_actions_sit_under_the_preview` and
`test_line_names_only_the_kinds_present`. The product
diff is `tests/test_window_return.py` only.

Result: No defects remain. The named checks passed.
`QT_QPA_PLATFORM=offscreen pytest tests/test_window_return.py::test_clear_check_has_an_empty_line_and_start_works`
passed (1 passed in 0.47s).
`QT_QPA_PLATFORM=offscreen pytest tests/test_window_return.py tests/test_window_timing.py`
passed (11 passed in 3.46s). Qt loaded (PyQt6 6.7.1).
Nothing skipped. The tests did not start Inkscape. Pid
471572 was already running, started Thu Nov 5 17:48:12
2026. That pid and start time were the same after both
commands. No bug outside this change.
