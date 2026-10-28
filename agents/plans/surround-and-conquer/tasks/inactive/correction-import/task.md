# Correction import

**Status:** done

## Goal

Import places a correction result on a new layer above the
document, and a weed-line result still imports as it does now.

## Do

- Edit `extensions/inkscape/weedlines_import.py` only.
- When the correction loader returns arrow groups and the file has
  no design copy, add one layer labeled "Weedlines corrections"
  and put those groups in it, above the open document.
- Do not add a design copy. Do not delete or rewrite the person's
  paths. A weed-line result still imports as it does now.
- The rules are the Result section of
  `agents/architecture/host.md`.
- Tests go in `tests/test_correction_import.py`. Skip when inkex
  is missing. Do not require a running Inkscape.

## Checks

- A correction file becomes that one layer and those groups, and
  no design group is added.
- A weed-line file still contributes its design group and its cuts.
- `pytest tests/test_correction_import.py` passes, or skips only
  because inkex is missing.

## Note

Import of a correction result adds one layer labeled "Weedlines
corrections" and puts the loader's arrow groups in it. The layer is
the last child of the document, so it paints above the open paths.
Those paths are not deleted or rewritten, and no design group is
added. A weed-line result still uses the existing layer: the payload
layer name, the design group, and the cuts.

A correction file has no design group and no cuts, so the old import
treated it as an empty result and aborted. The branch runs only when
`load_correction_svg_groups` returns groups and
`load_result_svg_groups` finds no design copy. The loader already
returns an empty list for a design-plus-cuts file. The new layer sets
`inkscape:groupmode` to `layer`. `Group.new(..., is_layer=True)` on
the weed-line path does not; that path was left as it was.

Checked with `pytest tests/test_correction_import.py` (2 passed, not
skipped). inkex is not on the default module path here. The test
adds `/usr/share/inkscape/extensions` only when `import inkex` fails,
then skips if it is still missing. No Inkscape process. The loader
was not edited.

Summary: No defects. A correction file becomes one "Weedlines
corrections" layer of the loader's groups, above the open
document, with no design copy. A weed-line file still contributes
its design group and its cuts.

Context worth keeping: The branch runs only when
`load_correction_svg_groups` returns groups and
`load_result_svg_groups` finds no design copy. The layer is the
last child of the document and `inkscape:groupmode` is `layer`.
The person's paths are not edited. `Group.new(..., is_layer=True)`
on the unchanged weed-line path does not set groupmode; that path
stays as it was. A file from `write_correction_result` imported
all three kind groups with shaft and head styles kept. The suite
locks labels, ids, and `d`, not style. The pass is `cr-01.md`.

Result: No defects remain. The named checks passed.
`pytest tests/test_correction_import.py` passed (2 passed, not
skipped). inkex loaded. No Inkscape process.
