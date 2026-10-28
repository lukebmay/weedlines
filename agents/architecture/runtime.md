# Runtime

When to use: Pause, cancel, logging, or the job cache.

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

Start runs the solver on a worker thread. The preview adds each
accepted segment. Pause freezes the worker at the next progress
check. Resume clears that flag. Cancel aborts, including while
paused. Close while a run is going aborts too. Apply is the
control that returns weed lines. Close, cancel, or an empty
result returns nothing.

On Apply, the detached window writes the result and does not
edit the open document. The person then runs Import last result.
The cache directory is `$XDG_CACHE_HOME/weedlines` when that
variable is set. Otherwise it is `~/.cache/weedlines` on Linux,
`%LOCALAPPDATA%\weedlines\cache` on Windows, and
`~/Library/Caches/weedlines` on macOS. The detached window's
stdout and stderr go to `host.log` in that directory.

The detached split exists so the extension can return. A long
run must not hold Inkscape's main thread, and solver stderr
must not come back as Inkscape's additional-data dialog.

## Progress

The host installs one run's hooks: a phase label, each accepted
segment as `(x0, y0, x1, y1)`, pause, and cancel. Pause blocks
inside the progress check until the host clears it. Cancel
raises `WeedCancelled` and still applies while paused. The
solvers call the hooks. They do not decide the widgets.

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
