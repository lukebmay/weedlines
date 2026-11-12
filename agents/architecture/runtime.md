# Runtime

When to use: Pause, cancel, logging, how long a step took, or the job cache.

**Owner:** human. Agents may propose edits; apply only with explicit
permission.

The host owns the process boundary. The library owns the progress
hooks and the log. The window owns the buttons that set those
hooks. A log line is not a cut, and a log setting does not change
which segments the solver emits.

## Run

The usual path is detached. The extension writes the job and
spawns the window, then returns, so Inkscape stays usable.
`WEEDLINES_INLINE` set to `1`, `true`, `yes`, or `on` is the old
path: the window blocks inside the extension, and the extension
writes the layer itself. Import is not required on that path.

The job carries the path records, the document size, and the
dialog defaults. [`host.md`](./host.md) is that record. The
window runs the figure check before Start.
[`preflight.md`](./preflight.md) is the gate.

The window's GUI thread keeps handling paint and input from
the moment the window is shown. That includes the figure
check, the surround, and every solver. Geometry does not run
on that thread. Qt objects the window paints stay on it. A
run that still leaves the window or Inkscape not responding
has not met this. Moving the work off the GUI thread is not
a widget and not a second solver.

The run controls are Start, Pause, Clear All, Apply, and
Close. Start reads Restart after that step has been started,
until Clear All. Restart discards that step's lines and any
later step's lines, then runs the step again. It stays
disabled while the step is actively running. Pause holds the
run at the next progress check and leaves the lines up.
Resume continues that same run. Clear All aborts, including
while paused, and discards this visit's lines and result.
Option values, swap, and colors stay. Close while a run is
going aborts too and returns nothing. Apply is the control
that returns weed lines. Close, Clear All, or an empty result
returns nothing.

A mode this guide gives no steps the person starts is one
step. Frame, grid, and island-hop are each one step.
Surround and Conquer is one run. An internal surround
is not its own step. [`algorithms.md`](./algorithms.md) is
what the run cuts. The window shows one
status for the run: ready, working, paused, or done. A
spinner shows only while the run is working and is not
paused. A phase name from the library can appear in that
status. The window does not turn those names into steps
the person starts. The preview adds each accepted segment.

When a mode has steps the person starts, each step has its
own Start control. That control reads Restart after the
step has been started. Restart on an earlier step discards
that step and every later step, then runs the earlier step
again. The window shows those steps, which one is current,
and which are left.

The window times each step the person has started.
Surround and Conquer is timed like the other runs. While
the step is working, the time advances and is shown with
that step's status. A phase name may appear in the status and is not
its own time. While the step is paused, the time holds, so
a pause is not counted as the algorithm running. When the
step finishes, the window keeps showing that working time
until the step is discarded. Restart starts that step's
time from zero and discards every later step's time with
its lines. Earlier steps keep theirs. A step not started
has no time. Each started step has its own time. The
window owns the clock. The library does not. Ticking the
clock does not run geometry. The time is not a log line.
The time does not change the cuts. Clear All discards the
times with the lines.

On Apply, the detached window writes the result and does not
edit the open document. The person then runs
`3 Reimport last weedlines`.
The cache directory is `$XDG_CACHE_HOME/weedlines` when that
variable is set. Otherwise it is `~/.cache/weedlines` on Linux,
`%LOCALAPPDATA%\weedlines\cache` on Windows, and
`~/Library/Caches/weedlines` on macOS. The label above the run pane is **Algorithm output**.
The pane shows one line when the library enters a stage,
and one line when it enters a substage. It does not show
a line for each accepted segment. Those segments still
update the preview. A reject stays out of the pane unless
the log level below asks for it. The lines do not change
the cuts. The run's stdout and stderr still arrive in
that pane. The detached window's stdout and stderr also
go to `host.log` in that directory.

The detached split exists so the extension can return. A long
run must not hold Inkscape's main thread, and solver stderr
must not come back as Inkscape's additional-data dialog.

## Progress

The host installs one run's hooks: a phase label, each accepted
segment as `(x0, y0, x1, y1)`, pause, and cancel. Pause blocks
inside the progress check until the host clears it. Clear All
raises `WeedCancelled` through the cancel hook, including
while paused. The solvers call the hooks. They do not decide
the widgets.

Every long run calls those checks during the work. That
includes the figure check, the surround, and frame, grid,
and island-hop. A check only at the start, or only when a
segment is accepted, does not cover a stretch that can run
long. Between checks the GUI thread has to be able to paint
and take input. Pause and Clear All take effect at the next
check. A check may name one object outline and one candidate
line. That naming is not a cut.
[`preview.md`](./preview.md) is how the window paints it.

## Logging

`WEEDLINES_LOG` is the switch. `INKCUT_WEED_DEBUG` is the legacy
alias. Unset, empty, `0`, `false`, `no`, or `off` is quiet. Any
other value, including `1`, logs decisions, phases, rejects, and
audits. `2`, `verbose`, `all`, `trace`, or `debug` also logs
every `emit.accept`. The logger name is `weedlib`.

The window sets level `1` for the run only when both variables
are unset or empty, so a deliberate `0` or `2` survives. The
library reads the environment at log time. `phase()` still
reports to progress when logging is off. A stderr handler is
added only when the logger has no handler yet. The lines to
search are `phase.`, `island_hop.`, `emit.`, and `reject`.
