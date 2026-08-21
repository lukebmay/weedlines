# Inkcut weed lines (Inkscape extension)

Same **deterministic weed solvers** as Inkcut (`inkcut.weedlib`), exposed
inside Inkscape so you can edit weed cuts as ordinary paths/layers before
send.

## Install

Preferred (also installs send extensions — selection / page / document):

```sh
inkcut install-plugin
inkcut install-plugin --dry-run   # preview only
```

See `plugins/inkscape/README.md` for `--uninstall` / `--copy` / `--dest`.

Manual / prerequisites:

1. Install Inkcut (or keep this repo on disk) so `inkcut.weedlib` imports.
2. Install a Qt binding usable from the **same Python** Inkscape’s
   extensions use: `PyQt5` / `PyQt6` / `PySide2` / `PySide6` (or run from
   an environment that already has `enaml.qt`).
3. Install `pyclipper` for full **auto** mode (optional for frame/grid).
4. Or symlink just the weed files:

   ```sh
   ln -s /path/to/inkcut/extensions/inkscape/inkcut_weeds.py \
         /path/to/inkcut/extensions/inkscape/inkcut_weeds_dialog.py \
         /path/to/inkcut/extensions/inkscape/inkcut_weeds.inx \
         ~/.config/inkscape/extensions/
   ```

5. Restart Inkscape → **Extensions → Inkcut → Auto-gen Weedlines layer from selection…**

   A custom dialog opens: **Start Algorithm** / **Cancel…**, expandable
   stdout/stderr log, and a live preview of weed cuts as they are emitted.
   **Apply layer & Close** writes the Weedlines layer into the document.
   (No Inkcut travel/TSP planning here — send the layer to Inkcut next.)

Without Inkscape, unit tests and previews still use the shared core:

```sh
QT_QPA_PLATFORM=offscreen PYTHONPATH=. python3 -m pytest tests/test_weeds.py -q
```

`inkex` is **not** required for pytest.

### Keep vs waste

- **Filled design geometry** = keep (land on the liner).
- **Empty / transparent regions** = waste (water / weedable vinyl).

Weed cuts run in waste. The extension does not fork solvers; it calls
`inkcut.weedlib.generate_weeds`.

## Design note (hosts + units)

### One algorithm, two hosts

| Host | Entry | Path type at core |
| --- | --- | --- |
| **Inkcut** | `inkcut.job.weeds` → `inkcut.weedlib.solvers` | `QPainterPath` |
| **Inkscape** | `extensions/inkscape/inkcut_weeds.py` | `QPainterPath` via edge convert |

Do not fork peel logic. Change solvers only under `inkcut/weedlib/`.

### Layer naming

- Default output layer label: **`Weed lines`** (override in the dialog).
- Each open cut is a child `svg:path` with id `weed-cut-NNNN`.
- Style: **stroke only** (`fill:none`), distinct color (`#c04000`), thin
  stroke (~0.25 user units) so paths stay editable and clearly not design
  keep geometry.

### Units (mm)

- Solver knobs (`padding`, `spacing`, `collar`, …) are **device/user
  units**. In Inkcut jobs that is typically **mm**.
- The extension treats document user units as **mm** when the SVG width is
  in mm (common Inkscape default). Padding/spacing/collar spinners are
  labeled **mm**.
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
- Edge helpers: `inkcut.weedlib.svg_paths` (`svg_d_to_qpainterpath`,
  `qpainterpath_to_svg_d`, `weed_path_to_open_d_list`).

### Modes

| Mode | Behavior |
| --- | --- |
| `frame` | Padded rectangle around keep bbox |
| `grid` | Axis-aligned grid; omit even-odd keep |
| `auto` | Collar + channels / bays (D007); needs pyclipper |

Inkcut default remains `frame` — do not switch the app default to `auto`
until preview pictures are accepted.

### Layout in the repo

| Path | Role |
| --- | --- |
| `inkcut/weedlib/solvers.py` | Frame / grid / enclosure solvers |
| `inkcut/weedlib/svg_paths.py` | SVG `d` ↔ `QPainterPath` |
| `inkcut/job/weeds.py` | Thin re-export for Inkcut |
| `extensions/inkscape/` | This extension (`.inx` + entry) |
| `tests/test_weeds.py` | Shared core tests (no Inkscape) |
