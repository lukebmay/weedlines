# Cut stroke

**Status:** done

## Goal

A weed-line cut written from the window uses that window's
weed-line color. An untouched control, and a result that does
not record a color, both use `#FF0000`. Fill is none, width is
0.25, and ids stay `weed-cut-NNNN`.

## Do

- `run_weedlines_dialog` in
  `extensions/inkscape/weedlines_dialog.py` returns
  `(weed, layer_name, color)`. `color` is the weed-line color
  control (`weed-line-color`) when Apply accepts, and None when
  the window does not accept. The control still starts at
  `#FF0000`. Do not change preview paint, the Start gate, or
  correction-arrow colors.
- `extensions/inkscape/weedlines_host.py` passes that color into
  `write_result`. Leave the Apply notice as it is.
- `write_result` in `extensions/inkscape/weedlines_job.py` stores
  the color on the result JSON as `weed_line_color` when the
  caller passes one, and passes it to `write_result_svg`. An
  omitted color is not stored.
- `write_result_svg` in `extensions/inkscape/weedlines_svg.py`
  strokes each cut with that color. An omitted color is
  `#FF0000`. Fill stays none, width stays 0.25, ids stay
  `weed-cut-NNNN`. Do not change correction SVG styles.
- `_add_weed_layer_from_d` in `extensions/inkscape/weedlines.py`
  takes the same color and writes that stroke. An omitted color
  is `#FF0000`. The inline path passes the color returned with
  the cuts. `_add_weed_layer` passes it through.
- The JSON-only branch in
  `extensions/inkscape/weedlines_import.py` passes
  `weed_line_color` from the payload into
  `_add_weed_layer_from_d`, or `#FF0000` when the result does not
  record one. Import of a result SVG still copies that file's
  style and does not restyle the cuts. The correction-import
  branch is unchanged.
- In `docs/inkscape-extension.md`, replace the fixed `#c04000`
  stroke with the window color, default `#FF0000`, fill none,
  width 0.25. Do not rewrite the rest of that page.
- Call sites that unpack two return values must take the third.
  The fakes in `test_host_passes_records_not_the_union` and
  `test_inline_path_passes_records_not_the_union` return a third
  None. The two `result == (None, None)` assertions in
  `tests/test_window_return.py` become a third None.
- Do not edit `src/weedlib/solvers.py` or
  `extensions/inkscape/weedlines.inx`. Do not add a mode. Do not
  change cut geometry. Do not edit the root README.

## Checks

- A result written with no color, and one written with
  `#FF0000`, both stroke `#FF0000`, `fill:none`, width 0.25,
  ids `weed-cut-NNNN`. A different window color is that stroke,
  and the JSON records `weed_line_color`.
- The inline layer writer uses the color it is given. The
  JSON-only import uses the recorded color, and `#FF0000` when
  the payload has no `weed_line_color`. A correction file still
  imports as arrow groups only.
- Tests go in `tests/test_cut_stroke.py`. No Inkscape. The SVG
  and JSON checks do not need inkex. The inline writer and the
  JSON-only import skip only the way
  `tests/test_correction_import.py` skips when inkex is missing.
  A host or dialog check runs offscreen and skips only when Qt
  cannot load.
- `pytest tests/test_cut_stroke.py tests/test_correction_import.py tests/test_correction_result.py`
  passes, aside from that inkex skip.
- `QT_QPA_PLATFORM=offscreen pytest tests/test_window_return.py tests/test_window_gate.py`
  passes, or skips only because Qt cannot load.
- `src/weedlib/solvers.py` and
  `extensions/inkscape/weedlines.inx` are unchanged.
  `docs/inkscape-extension.md` does not say `#c04000`.

## Note

A cut written from the window uses that window's weed-line color.
`run_weedlines_dialog` returns `(weed, layer_name, color)`. `color`
is the `weed-line-color` control when Apply accepts, and None when
the window does not. The control still starts at `#FF0000`. Preview
paint, the Start gate, and the correction-arrow colors are unchanged.

The host passes that color into `write_result`. The Apply notice is
unchanged. `write_result` stores `weed_line_color` only when the
caller passes one, and passes it to `write_result_svg`. An omitted
color is not stored. `cut_style` is the shared stroke: fill none,
width 0.25, round caps and joins. An omitted color is `#FF0000`.
Ids stay `weed-cut-NNNN`. The result SVG and
`_add_weed_layer_from_d` both use it. `_add_weed_layer` passes the
color through, and the inline path passes the color returned with
the cuts.

JSON-only import passes `weed_line_color` from the payload, or
`#FF0000` when the result does not record one. Import of a result
SVG still copies that file's style. The correction-import branch is
unchanged. `docs/inkscape-extension.md` names the window color,
default `#FF0000`, instead of the fixed `#c04000`. Call sites that
unpacked two return values now take the third.
`src/weedlib/solvers.py` and `extensions/inkscape/weedlines.inx`
were not edited.

Checked with `pytest tests/test_cut_stroke.py
tests/test_correction_import.py tests/test_correction_result.py`:
20 passed. `QT_QPA_PLATFORM=offscreen pytest
tests/test_window_return.py tests/test_window_gate.py`: 14 passed.
Qt loaded; nothing skipped. No Inkscape process. The same offscreen
command for `tests/test_window_preview.py` passed (6 passed).
`git diff` of `src/weedlib/solvers.py` and
`extensions/inkscape/weedlines.inx` is empty.
`docs/inkscape-extension.md` does not say `#c04000`.

Review summary: no defects remain. Apply returns the committed
`weed-line-color` property, and a window that does not accept
returns `(None, None, None)`. The host stores that color and
strokes the cuts with it. An omitted color is not stored and
strokes `#FF0000`. `cut_style` is shared by the result SVG and
the inline layer writer. JSON-only import uses the recorded
color, or `#FF0000` when the payload has none. A result SVG is
copied as written. Correction import, preview paint, the Start
gate, correction-arrow styles, and the Apply notice are
unchanged.

Context worth keeping: the returned color is the property, not
the raw field text. `_hex_color` stores `#` and six uppercase
hex digits, so `#00aa00` comes back as `#00AA00`. That is the
color the preview already paints. An untouched Apply therefore
records `#FF0000`, because the host passes the control value.
`write_result` omits the key only when the argument is None.
JSON-only import treats a missing or other falsy value as
`#FF0000`. The window cannot commit an empty color, so those
two checks agree for a color it writes. Round caps and joins
stay in `cut_style`; the old stroke already had them. A result
SVG import does not restyle cuts from the JSON color. The pass
is `cr-01.md`.

Result: no defects remain. The named checks passed.
`QT_QPA_PLATFORM=offscreen pytest tests/test_cut_stroke.py
tests/test_correction_import.py tests/test_correction_result.py
tests/test_window_return.py tests/test_window_gate.py
tests/test_window_preview.py` passed (40 passed, no skips).
That is the named 20, the named 14, and the preview file (6).
Qt loaded. The inkex skip and the Qt skip did not run. The
tests do not start Inkscape. `git diff HEAD --exit-code --
src/weedlib/solvers.py extensions/inkscape/weedlines.inx` is
empty. `docs/inkscape-extension.md` does not say `#c04000`.
Those two checks have no test.
