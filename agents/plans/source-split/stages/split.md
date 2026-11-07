# split

The behavior-preserving move. The NP-hard designer owns
the stage files inside `figures/`, `surround/`, and
`solvers/`. The senior developer owns the dialog
package. `keep.py` sits beside those packages so the
figure check does not import a cutter.

## Order

1. `src/weedlib/keep.py` and `src/weedlib/figures/`,
   with the figure tests.
2. `src/weedlib/surround/` and `src/weedlib/solvers/`,
   after keep exists. Those two name different files.
3. `extensions/inkscape/weedlines_dialog/`. It names
   different files from the library tasks and may run
   beside them.

`extensions/inkscape/weedlines.py` is not edited.
Files under 500 lines stay whole: `paths.py`, `qt.py`,
`debug.py`, `progress.py`, `arrows.py`, `svg_paths.py`,
and the host modules other than the dialog.
`src/weedlib/__init__.py` keeps today's `__all__` and
imports those names from the new modules.

A directory with more than one source file gets
`README.md`: the file name and one sentence. The index
does not copy the file. `tests/README.md` is the test
index.

## Keep

`src/weedlib/keep.py` owns closed subpaths, the one
twin collapse, nesting, and keep fill. `even_odd_keep_fill`,
`design_keep_fill`, `closed_fill_union`,
`list_closed_subpaths`, `_dedupe_closed_subpaths`,
`_subpath_is_closed`, `_nest_closed_paths`,
`padded_work_rect`, and the area and sample helpers that
exist only to serve those. `figures/check.py` calls
`keep._dedupe_closed_subpaths`. `solvers/__init__.py`
re-exports the public keep names. There is no second
collapse. `paths.py` does not gain it.

## Figures

`src/weedlib/figures/` replaces `figures.py`.
`figures/__init__.py` re-exports `classify_figures`,
`subject_weed_regions`, `Figure`, `Defect`,
`FigureCheck`, `SubjectWeed`, and `_painted_parts`.

- `types.py` — the four records.
- `check.py` — classify, twins, dangling ends, subject
  and weed area. Dangling ends stay with classify.
- `overlap.py` — one connected shared area. Nesting, a
  touch, and a shared boundary stay non-defects.
- `interior.py` — sample points and area tests.
- `borders.py` — self-overlap and the cubic hit test.
  The cubic solver stays in this file.

Progress calls that exist today stay on the module that
receives the function: `_without_twins`,
`_overlap_defects`, `_one_point_per_region`,
`_linked_mark_groups`, `_self_overlap_defects`.

## Surround

`src/weedlib/surround/` replaces `surround.py`.
`surround/__init__.py` re-exports `build_surrounds` and
`_bridge_clears`.

- `build.py` — dilate, cluster, bridge, smooth, in
  today's order.
- `bridge.py` — one inner bridge and its clearance test.
- `union.py` — union of surrounds that meet.
- `offset.py` — dilate and the outer loops.
- `smooth.py` — fillets out to the surround distance.

Every `progress.check` in those stages stays on the
function that has it today.

## Solvers

`src/weedlib/solvers/` replaces `solvers.py`.
`solvers/__init__.py` re-exports the names
`weedlib/__init__.py` already exports from solvers, plus
`frame_weeds`, `grid_weeds`, and `island_hop_weeds`.
It does not re-export private helpers. A test that
patches a private helper patches the defining module.

- `rules.py` — mode list and the numeric floors.
- `dispatch.py` — `generate_weeds` and the mode switch.
  `auto` stays island-hop. `region` stays grid. An
  unknown mode stays frame. Frame stays here.
- `grid.py` — hatch plus the closed work rectangle.
- `clip.py` — clip a segment to a rectangle or a region.
- `clipper.py` — pyclipper offset and collar rings.
  Frame and grid do not import it.
- `geom.py` — point, ray, and ring predicates with no
  stage policy.
- `emit.py` — accept or drop one segment. The
  `report=False` seen-path copy stays.
- `rank.py` — rank candidate seals. One job. It stays
  whole.
- `island.py` — island-hop's pass order only.
  `phase()` blocks stay here. Hole splits stay here.
- `peel.py` — the grow-clearance peel frame.
- `cluster.py` — nearby keep bodies and a design frame.
- `bay.py` — bay and peninsula predicates. One job.
- `pockets.py` — one body's bay seal.
- `frame_peninsulas.py` — frame-to-letter bay seals.
- `ties.py` — a compact island tied to a host.
- `gaps.py` — the gap between two keep bodies.
- `corridors.py` — a channel-core seal.
- `agglomerate.py` — join until one island remains.
- `channels.py` — keep-to-wall channel and tip spokes.
- `cluster_bays.py` — multi-body bays and hanging gutters.
- `traps.py` — residual open waste. It emits no cuts.
- `stats.py` — segment counts and sample audits.

`_add_seg` and `_publish_path_segments` stay the only
ways a segment is reported. A stage does not grow its
own pause flag.

## Dialog

`extensions/inkscape/weedlines_dialog/` replaces
`weedlines_dialog.py`. Tests that import
`run_weedlines_dialog`, `_spawn_ask`, `_ASK_HOLD`,
`_ASK_TRACE`, or `_burn_hold` keep importing them from
`weedlines_dialog`.

- `__init__.py` — build the dialog, run it, and return
  the Apply path, the layer name, and the weed-line color.
- `geometry_ask.py` — spawn one ask and install progress,
  cancel, pause, focus, and the solver log in the child.
- `inbox.py` — pump the pipe on the GUI thread.
- `preview.py` — checkerboard, subject, arrows,
  surrounds, and accepted segments. Work marks stay
  stored and unpainted.
- `run_controls.py` — Start, Restart, Pause, Clear All,
  Apply, Close, the step row, and the status. Start
  stays in this file with the other four.
- `form.py` — mode, display unit, lengths, colors, swap,
  and option history. One form.
- `return_line.py` — the defect line and the two return
  actions.

The GUI thread does not call `classify_figures`,
`build_surrounds`, or `generate_weeds`. Close and Clear
All do not join the child.

## Tests

Move tests with the source they cover. A test file that
is already one responsibility and under 1000 lines stays
whole. `tests/test_window_surround.py` is past 1000. The
dialog task splits it before editing it, by the window
behaviors it already tests.

From `tests/test_weeds.py`:

- `tests/weed_shapes.py` — shared shapes.
- `tests/test_frame.py` — frame and the mode switch.
- `tests/test_grid.py` — grid, snap, and the region alias.
- `tests/test_keep.py` — keep fill, twins, and samples.
- `tests/test_island.py` — island-hop through `generate_weeds`.
- `tests/test_peel.py` — the peel frame.
- `tests/test_bays.py` — bay, peninsula, and pocket seals.
- `tests/test_corridors.py` — corridors, agglomerate, gutters.
- `tests/test_ties.py` — compact ties.
- `tests/test_emit.py` — clearance, alpha, hugs, slivers, rank.
- `tests/test_traps.py` — `residual_waste_traps` only.

`tests/test_progress.py` stays one file. Patches retarget
to the defining module.

From `tests/test_figures.py`:

- `tests/test_figures.py` — classify, dangling ends, twins,
  subject, swap.
- `tests/test_self_overlap.py` — real-border crossings.
- `tests/test_overlap.py` — separate-figure overlap.

From `tests/test_surround.py`:

- `tests/test_surround.py` — offset, join gap, preamble.
- `tests/test_surround_smooth.py` — fillets.
- `tests/test_surround_bridge.py` — inner bridges.

## Not this stage

Conquer. The piece border. Cut-geometry changes. Menu
names. `weedlines.py`.
