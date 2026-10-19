# Architecture

**Owner:** human. Agents may propose edits; apply only with explicit permission.

This file is the **target** architecture: how the product is supposed
to work. After reading it, you should be able to walk a user action
from event to result without guessing which layer owns the change.

Gaps between this file and the running code are closed with a plan.
Do not rewrite this file to describe leftovers.

Words: [`glossary.md`](./glossary.md). When work is complete:
[`acceptance.md`](./acceptance.md). How work is run, including what
is stone: catalog `general.md` and [`general.md`](./general.md) when
this project has one.

## This file can be wrong

This file is what we **currently believe** is the best structure. It
is not a proof. It will change. Parts of it will turn out to be
wrong.

If you think a lock here is **directionally wrong** (the structure
or the product intent, not a leftover in the code), **stop work on
that issue**. Do not paper over it with a second path. Do not silently
edit this file. Do not silently change the code to match a sentence
you suspect is stale. We meet, we decide, then we write the decision
here **with why**: the user-visible problem, what was rejected, what
the lock does, and what it does not apply to.

**Why this paragraph exists:** agents treated exploratory fences and
this file as unchangeable, then hid misses behind fallbacks. A lock
without why cannot be reasoned about when the facts change.

Code that merely lags this file is a plan, not a meeting. A meeting
is for when this file itself looks like the mistake.

## What is being built

Weedlines cuts **weed lines** in the waste around vinyl (and similar)
keep geometry. Solvers live in `weedlib`. Inkscape is the host: a
Start / Pause / Resume / Cancel dialog with a live preview of accepted
cuts. The usual path opens that dialog in a detached window so Inkscape
stays usable, then **Import last result** writes the layer back.

Stay standalone until the algorithms are solid. Default mode is
`frame`. Do not make `island-hop` the default until picture QA is
accepted. Moving `weedlib` into `~/dev/me/inkcut`, then a PR upstream,
is later work named in [`priority.md`](./priority.md). It is not a
layer in this file.

## Layers

| Piece | Owns | Must not own |
| --- | --- | --- |
| `weedlib` solvers | A weed `QPainterPath` from a keep `QPainterPath`, via `generate_weeds`. Modes are `frame` (padded box around the keep bbox), `grid` (axis-aligned hatch over waste, plus a closed surround on the padded work rect; `region` is the same call), and `island-hop` (peel frame, then ranked seals, in `enclosure_weeds`). Unknown modes become `frame`. `auto` is a deprecated alias of `island-hop`. Closed subpaths nest into keep islands; open strokes are not keep interiors. Collar offsets in island-hop require `pyclipper`. Frame and grid do not. | SVG documents, the dialog, the result cache, install paths, and git. It must not change which segments are emitted because a log variable is set. Hosts call the `weedlib` package API, not private helpers in `solvers.py`. |
| `weedlib` progress | One run's hooks, installed by the host: phase label, accepted segment `(x0, y0, x1, y1)`, cooperative pause, and cancel. Pause blocks inside `check_pause` until the host clears it. Cancel raises `WeedCancelled` and still applies while paused. | Which segment is legal, Qt widgets, and the preview scene. Solvers only call the hooks. |
| `weedlib` debug | `WEEDLINES_LOG`, else the legacy alias `INKCUT_WEED_DEBUG`. Unset, empty, `0`, `false`, `no`, or `off` is quiet. Any other value (including `1`) logs decisions, phases, rejects, and audits. `2`, `verbose`, `all`, `trace`, or `debug` also logs every `emit.accept`. Logger name is `weedlib`. A stderr handler is added only when the host has not already attached one. `phase()` still reports to progress when logging is off. | Emit rules. A log line is not a cut. |
| SVG and Qt edge | `weedlib.svg_paths` converts SVG `d` and `QPainterPath` at the host boundary. `weed_path_to_open_d_list` is the open-cut list the extension writes. `A`/`a` arcs are linearized to the endpoint; hosts that need a true arc convert it before this step. `weedlib.qt` loads one binding, in order: `enaml.qt`, PyQt5, PySide2, PyQt6, PySide6. Coordinates stay in the caller's user units. | Mode choice, cut acceptance, and Inkscape layer XML. The dialog labels padding, spacing, and collar as mm; solvers do not convert units. |
| Inkscape extension | `extensions/inkscape/`. Menu **Extensions → Weedlines → Weedlines from selection…** builds keep from selected `svg:path` nodes, or from the whole document when the selection is empty. Each path uses its own composed transform. No path geometry aborts and tells the user to convert objects to paths. The dialog offers `frame` (default), `grid`, and `island-hop`, one padding number copied to all four sides, grid spacing, island-hop collar, and the output layer name (`Weed lines` if blank). Other knobs stay at solver defaults. Start calls `generate_weeds` on a worker thread. If neither log variable is set, that run sets `WEEDLINES_LOG=1` and restores the environment afterward. An explicit level, including `0`, is left as set. | A second copy of frame, grid, or island-hop. Pip, git, and the Inkscape extensions directory. Cutter travel and Inkcut device config. The on-screen hint is weed cuts only. |
| CLI install / update | Putting the extension files into the user Inkscape extensions directory, and `weedlines update`'s fast-forward pull when the git tree is clean. Console script `weedlines` (`src/weedlines/`). Repo `./install` is the same linker plus a best-effort editable pip install. | `generate_weeds`, the dialog, and editing solver or extension source. |

## Notes

### Run

1. The user chooses **Extensions → Weedlines → Weedlines from
   selection…**. `weedlines.py` builds the keep path. Empty keep stops
   there.
1. Unless `WEEDLINES_INLINE` is `1`, `true`, `yes`, or `on`, the effect
   writes a job JSON (keep `d`, dialog defaults, document width, height,
   and viewBox) and spawns `weedlines_host.py` in a new session, then
   returns. Inkscape stays usable. The inline flag is the old path: the
   dialog blocks inside the extension process, and `weedlines.py` writes
   the layer itself. Import is not required on that path.
1. The host turns the job `d` back into a `QPainterPath` and opens the
   dialog. **Start Algorithm** runs the solver. The preview adds each
   accepted segment. **Pause** freezes the worker at the next progress
   check so the preview can be inspected. **Resume** clears that flag.
   **Cancel** (and **Close** while running) aborts with `WeedCancelled`.
   **Apply** is the only control that returns a path. Close, cancel, or
   an empty result returns nothing.
1. On Apply, the detached host writes `last_result.json` and
   `last_result.svg` (design keep plus cuts, source document size) and
   does not edit the open document. The user then runs **Extensions →
   Weedlines → Import last result**. That command inserts the layer.
   Each open cut is a stroke-only path: `fill:none`, stroke `#c04000`,
   width `0.25`, id `weed-cut-NNNN`.
1. Cache directory: `$XDG_CACHE_HOME/weedlines` if set, otherwise
   `~/.cache/weedlines` on Linux, `%LOCALAPPDATA%\weedlines\cache` on
   Windows, `~/Library/Caches/weedlines` on macOS. Detached host
   stdout and stderr go to `host.log` in that directory.
1. `src/weedlib/paths.py` only splits and joins `QPainterPath` subpaths
   for the solvers. Tests and other library callers import `weedlib`
   directly. They do not need `inkex`.

The split exists so Inkscape's extension script can exit. A long
island-hop run must not hold Inkscape's main thread, and solver stderr
must not come back as Inkscape's "additional data" dialog.

### Logging

Level rules are the table in [`project.md`](./project.md). This file
adds who acts. `weedlib.debug` reads the environment at log time. The
dialog is the only host that forces level `1`, and only when both
`WEEDLINES_LOG` and `INKCUT_WEED_DEBUG` are unset or empty, so a
deliberate `0` or `2` survives the run. Logging is for the live log and
for `rg` of `phase.`, `island_hop.`, `emit.`, and `reject`. It is not
an input to the solver.

### Install and update

1. `weedlines install` symlinks `extensions/inkscape/` into the user
   extensions directory. `--copy` copies instead. An existing symlink
   that already points at the same source is left alone. A symlink that
   points elsewhere is replaced. A real file is skipped unless
   `--force`. `--dry-run` prints and writes nothing. `--uninstall`
   removes only destinations that resolve to this checkout's sources.
1. Destination is `--dest`, else `$INKSCAPE_PROFILE_DIR/extensions`,
   else the platform Inkscape config `extensions` folder
   (`$XDG_CONFIG_HOME/inkscape/extensions` or
   `~/.config/inkscape/extensions` on Linux). The checkout is
   `$WEEDLINES_ROOT` when that tree contains
   `extensions/inkscape/weedlines.inx`; otherwise the repo that contains
   the package. The files are not inside the installed wheel. A tree
   without those sources fails the install instead of inventing them.
1. `weedlines update` installs the current tree when this is not a git
   checkout, or when `git status --porcelain` is non-empty. It does not
   pull in those cases. A clean checkout runs `git pull --ff-only` and,
   on failure, stops without installing. `--dry-run` neither pulls nor
   writes links.
1. `./install` (`scripts/install.py`) sets `WEEDLINES_ROOT` to the
   checkout and, unless `--skip-pip`, `--dry-run`, or `--uninstall`,
   runs `pip install -e .` when `import weedlib` fails. The `weedlines`
   console script does not run pip. Restart Inkscape after a real
   install so it reloads extensions.

Symlinks are the default so a later pull is what Inkscape loads, without
a second copy of the extension drifting from `weedlib`.

### Direction

[`priority.md`](./priority.md) is the queue, not a second architecture.
Next work is island-hop picture QA and algorithm refinement. That work
must not switch the default mode off `frame`. Later, move `weedlib`
into `~/dev/me/inkcut` and open an upstream PR. Until that lands, this
repo is the home of the solvers, and every host calls `weedlib` rather
than a copied fork.
