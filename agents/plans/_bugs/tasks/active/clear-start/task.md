# Clear start

**Status:** ready

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
