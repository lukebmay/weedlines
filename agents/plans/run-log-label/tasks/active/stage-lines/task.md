# Stage lines

**Status:** ready

## Goal

The pane is labeled Algorithm output. It shows one
line when a stage starts and one line when a
substage starts, and not one line per segment.

## Do

The rule is [the runtime part](../../../../../architecture/runtime.md).
Do not copy it.

`extensions/inkscape/weedlines_dialog/__init__.py`
holds the label above `log_view`. The text is
Algorithm output. Do not leave the stdout/stderr
words on it. Do not revive
[log-label](../../inactive/log-label/task.md)
as a rename only.

`src/weedlib/progress.py`, `src/weedlib/debug.py`,
and `src/weedlib/solvers/dispatch.py` report the
entry. The mode `generate_weeds` already reports
is the stage. A `phase()` entered while that stage
is open is a substage. The report knows which,
even when the log is quiet. Do not add stage names
the run does not already report.

`extensions/inkscape/weedlines_dialog/geometry_ask.py`
appends one pane line for a stage report and one
for a substage report. An accepted segment does
not add a line. The preview still takes the
segment. Do not also keep a `[phase]` line for
the same report.

Stdout and stderr still arrive in that pane. A
reject is not a stage line. It stays out of the
pane unless the log level already asks for it. A
deliberate level still records what it recorded,
including every accepted segment at the verbose
level. Those logger lines are not the stage
report.

Do not change the cuts or the step clock. The
phase name may still appear in the status. It is
not its own time.

Tests in `tests/test_window_gate.py` and
`tests/test_progress.py`. Offscreen when a test
opens a window. No Inkscape.

## Checks

- The label above the log is Algorithm output.
- A stage report and a substage report each add
  one line. An accepted segment does not add a
  line.
- The pane still shows the run's stdout and stderr.
- The lines do not change the cuts or the step
  clock.
- What a deliberate log level records does not
  shrink. A reject stays out of the pane unless
  that level asks for it.

## Note

The developer writes what changed, why, and how it
was checked. The reviewer then writes the summary,
the context worth keeping, and the result.
