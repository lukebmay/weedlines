# Weedlines (Inkscape extension)

Weed lines run inside Inkscape as ordinary paths and layers.

## Install

```sh
weedlines install
weedlines install --dry-run   # preview only
```

`weedlines install` symlinks `extensions/inkscape/` into the user
extensions directory. `--copy` copies instead. An existing symlink
that already points at this source is left alone. A symlink that
points elsewhere is replaced. A real file is skipped unless
`--force`. `--dry-run` prints and writes nothing. `--uninstall`
removes only destinations that resolve to this checkout.

The destination is `--dest`, else `$INKSCAPE_PROFILE_DIR/extensions`,
else the platform Inkscape config `extensions` folder. On Linux
that is `$XDG_CONFIG_HOME/inkscape/extensions` or
`~/.config/inkscape/extensions`. The checkout is `$WEEDLINES_ROOT`
when that tree contains `extensions/inkscape/weedlines.inx`.
Otherwise it is the repo that contains the package. The extension
files are not inside the installed wheel. A tree without those
sources fails the install instead of inventing them.

`weedlines update` installs the current tree when this is not a
git checkout, or when `git status --porcelain` is non-empty. It
does not pull in those cases. A clean checkout runs
`git pull --ff-only` and, on failure, stops without installing.
`--dry-run` neither pulls nor writes links.

`./install` sets `WEEDLINES_ROOT` to the checkout and, unless
`--skip-pip`, `--dry-run`, or `--uninstall`, runs `pip install -e .`
when `import weedlib` fails. The `weedlines` console script does
not run pip. Restart Inkscape after a real install so it reloads
the extension.

Symlinks are the default so a later pull is what Inkscape loads.

Prerequisites:

1. Install a Qt binding usable from the **same Python** Inkscape’s
   extensions use: `PyQt5` / `PyQt6` / `PySide2` / `PySide6` (or run from
   an environment that already has `enaml.qt`).
2. Install `pyclipper` for full **auto** mode (optional for frame/grid).
3. Restart Inkscape. The menu is **Extensions → Weedlines**.
   Inkscape sorts the entries by name. The number is part of each
   name, and none of the names end in an ellipsis. The entries are
   `1 Auto generate weedlines`, `2 Make ready to cut`,
   `3 Reimport last weedlines`, and `4 Reimport last ready cut`.
   There is no divider. `1 Auto generate weedlines` opens the
   detached window.

   A custom dialog opens: **Start**, **Pause**, **Clear All**, **Apply**,
   and **Close**, expandable
   stdout/stderr log, and a live preview of weed cuts as they are emitted.
   **Apply** is its own control. On Apply, the detached window writes
   the result and does not edit the open document. The person then
   runs `3 Reimport last weedlines`. **Close** is a separate control.

Without Inkscape, unit tests and previews still use the shared core:

```sh
QT_QPA_PLATFORM=offscreen PYTHONPATH=. python3 -m pytest tests/test_weeds.py -q
```

`inkex` is **not** required for pytest.

### Keep vs waste

- **Filled design geometry** = keep (land on the liner).
- **Empty / transparent regions** = waste (water / weedable vinyl).

Weed cuts run in waste. The extension does not fork solvers.

## Design note (hosts + units)

### Inkscape host

| Host | Entry | Path type at core |
| --- | --- | --- |
| **Inkscape** | `extensions/inkscape/` | `QPainterPath` via edge convert |

Do not fork peel logic.

### Layer naming

- Default output layer label: **`Weed lines`** (override in the dialog).
- Each open cut is a child `svg:path` with id `weed-cut-NNNN`.
- Style: **stroke only** (`fill:none`), the window color (default `#FF0000`),
  width 0.25, so paths stay editable and clearly not design
  keep geometry.

### Units (mm)

- Solver knobs (`padding`, `spacing`, `collar`, …) are **device/user
  units**. In Inkcut jobs that is typically **mm**.
- The padding, spacing, and collar spinners are labeled **Padding**,
  **Grid spacing**, and **Collar (island-hop)**. The unit is the
  display unit. The library receives document user units.
- Keep geometry is read from selected paths (or the whole document if
  nothing is selected). Convert text/clones to paths first.

### Open cuts ↔ Inkscape strokes

- Weed results are **open polylines/curves**, not filled faces.
- Serialization: each `QPainterPath` subpath → one SVG `d` with `M`/`L`/`C`
  only (no forced `Z`). That matches blade-down open cuts.
- Frame mode’s padded rectangle is a **closed** rect path from the solver;
  it still exports as a subpath (may close via start=end points). Auto
  channels remain open and must meet keep/other weeds at both ends (same
  as Inkcut).

### Modes

| Mode | Behavior |
| --- | --- |
| `frame` | Padded rectangle around keep bbox |
| `grid` | Axis-aligned grid; omit even-odd keep |
| `auto` | Collar + channels / bays (D007); needs pyclipper |

### Layout in the repo

| Path | Role |
| --- | --- |
| `extensions/inkscape/` | This extension (`.inx` + entry) |
| `tests/test_weeds.py` | Shared core tests (no Inkscape) |
