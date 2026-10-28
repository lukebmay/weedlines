# Job records

**Status:** done

## Goal

The host stores one open record per path element, including the
computed fill, and the current window still launches from `keep_d`.

## Do

- In `extensions/inkscape/weedlines.py`, write one record per path
  element in document user units with that element's transform
  applied. Do not add a closepath. Keep the existing `keep_d` write
  so the current host still runs until the window-gate task.
- Omit a path in a group labeled "Weedlines corrections", and a
  path whose id starts with `weedlines-correction`. The empty-path
  abort stays.
- Computed fill follows the Job section of
  `agents/architecture/host.md`: none, a solid color, or other
  paint. Opacity of zero is none. Resolve style, presentation
  attributes, and inheritance.
- In `extensions/inkscape/weedlines_job.py`, store those records
  with the document width, height, and viewBox already stored.
  Do not change `write_result`.
- Tests go in `tests/test_job_records.py`. The fill mapping does
  not need Inkscape. Use fake elements for inheritance.
- Do not edit the dialog, the solvers, or the result SVG.

## Checks

- A stored path that was open has no added closepath. Its closed
  flags match the path data.
- Fill none, opacity zero, a solid color, other paint, and an
  inherited solid color record as the host part says.
- A corrections-group path and a `weedlines-correction` id are
  absent from the records.
- `read_job` still returns `keep_d` and the document size
  attributes.
- `pytest tests/test_job_records.py` passes without Inkscape.

## Note

The job now stores `records` next to `keep_d` and `doc_attrs`. Each
record is one path element: `id`, `d` in document user units with
that element's transform applied, `closed` (one flag per subpath),
and `fill` (`none`, `#rrggbb`, or `other`). A closepath is kept only
when that subpath already had one, so an open path stays open.
Opacity of zero is `none` (the element's opacity, fill-opacity, or
an ancestor opacity). Style wins over a presentation attribute, and
fill is inherited. Paths in a group labeled "Weedlines corrections",
and ids starting with `weedlines-correction`, are omitted from the
records. The keep union is still written with `close_subpaths=True`,
so the current window still launches from `keep_d`. `write_result`
is unchanged.

Checked with `pytest tests/test_job_records.py` (no Inkscape): 4 passed.

Summary: No defects. One record per path element is stored beside
`keep_d`. An open subpath gains no closepath. Fill is none, a
solid `#rrggbb`, or other. The element's own opacity of zero is
none, style beats a presentation attribute, and a solid fill is
inherited. Correction paths are omitted. `read_job` still returns
`keep_d` and the document size.

Context worth keeping: A record is `id`, `d` in document user
units with that element's transform applied, `closed` (one flag
per subpath), and `fill`. A closepath is written only when that
subpath's source had one. `keep_d` is still the union written
with `close_subpaths=True`, so the current window still launches
from it. `write_result` and the empty-path abort are unchanged.
The host part requires the element's own opacity of zero to
record as none. The test sets that attribute. The code also
records fill-opacity of zero, and an ancestor opacity of zero,
as none. The host part does not name fill-opacity, and opacity
is not inherited, so those two are not required and the test
does not lock them. The pass is `cr-01.md`.

Result: No defects remain. The named checks passed.
`pytest tests/test_job_records.py` passed (4 passed, no Inkscape).
