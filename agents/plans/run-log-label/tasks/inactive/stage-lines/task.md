# Stage lines

**Status:** done

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

The label above the log is Algorithm output.
`generate_weeds` reports its mode as a stage. A
`phase()` entered while that stage is open is a
substage, including while the log is quiet. The
pane appends one line for each of those reports.
An accepted segment does not add a line. The
preview still takes it. A `[phase]` line is not
also sent for that report. Stdout and stderr
still arrive in the pane. A reject stays a logger
line: a quiet log omits it, and a set level still
records it, including every accepted segment at
verbose. The cuts and the step clock are unchanged.
The phase name can still show in the status.

The pane was one `[phase]` line per report, so a
segment and a stage looked the same kind of event.
The report now names which entry it is, and the
pane shows that entry once.

`python3 -m pytest tests/test_window_gate.py tests/test_progress.py`:
34 passed. Nothing failed. No Inkscape. The window
tests run offscreen.

## Summary

The label above the log is Algorithm output. The
stdout/stderr words are gone. `generate_weeds`
reports its mode as a stage. A `phase()` while that
stage is open is a substage, including while the log
is quiet. The pane appends one line for each of
those reports and does not also append `[phase]`.
An accepted segment updates the preview and does
not add a pane line. Stdout and stderr still arrive.
A reject stays a logger line. A quiet log omits it,
and a set level still records it, including every
accepted segment at verbose. The cuts and the step
clock are unchanged. The phase name can still show
in the status.

## Context worth keeping

The stage name is the mode `generate_weeds` already
reported. The substage names are the `phase()` calls
the run already makes. No new stage name was added.
The kind is chosen in `progress.report` before the
log write. A phase outside an open stage has an
empty kind and no pane line. Logger lines at a set
level still reach the pane through the existing
handler. They are not the stage report.
`geometry_ask.py` is 946 lines and `__init__.py` is
518. The new lines stay in the label and the phase
callback those files already own. No split. The
parked log-label task was not edited. The guide,
`cavern.py`, and `propose.py` are not in this diff.
The pass is `cr-01.md`.

## Result

No defect. `python3 -m pytest tests/test_window_gate.py tests/test_progress.py`:
34 passed in 12.13s. No Inkscape. The window was
offscreen.
