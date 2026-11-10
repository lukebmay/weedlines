# Design records

**Status:** parked

**Blocker:** the plan changed. The default export is
the border and the weed lines. The original design is
the Include original design checkbox. Do not revive
this task as an always-on design copy.

## Goal

The weed-line result's design copy is the path records the
figure check sees. Correction groups are omitted. No
closepath is added.

## Do

- In `extensions/inkscape/weedlines_svg.py`, write the design
  group from those records. One path per record, in that
  order, `d` copied as stored. Do not union the records.
  Do not append a closepath. Skip a record whose id starts
  with `weedlines-correction`. Do not write a group labeled
  "Weedlines corrections", and do not write an id that
  starts with `weedlines-correction`. Keep the design group
  import already finds (`weedlines-design`, label "Weedlines
  design"). Keep the design path presentation that file
  already uses. Do not take paint from the record. Do not
  change cut path data, cut ids, or cut style.
- In `extensions/inkscape/weedlines_job.py`, pass those
  records into that writer. `keep_d` may still be stored on
  the JSON when the caller passes it. It is not the design
  path data. Do not change `write_correction_result`.
- In `extensions/inkscape/weedlines_host.py`, pass the job's
  records into `write_result` on Apply. The dialog still
  receives those records. Do not pass the design copy into
  the dialog.
- Tests go in `tests/test_design_copy.py`. No Inkscape.
- Where `tests/test_cut_stroke.py` or
  `tests/test_correction_import.py` requires the single path
  `weedlines-keep`, point that assertion at the record
  paths. Do not change their cut assertions.
- Do not edit `extensions/inkscape/weedlines.py`, the figure
  check, the correction writer, or import.

## Checks

- A design path uses the record's `d`. An open record gains
  no closepath. A closepath the record already had stays.
- The design copy has no "Weedlines corrections" group and
  no id starting with `weedlines-correction`.
- Cut `d` values are unchanged.
- The dialog still receives the job records. The figure
  check is not given this design copy.
- A correction result still has no design copy.
- `pytest tests/test_design_copy.py tests/test_cut_stroke.py tests/test_correction_import.py tests/test_correction_result.py`
  passes. The new test does not need Inkscape.

## Note

Stopped. No code change. The design-copy sentences in
`agents/architecture/host.md` say a weed-line result is the
design copy and the cut paths, that import puts the design
group and the cuts on one layer, and that a correction
result and its import have no design copy. They do not say
the design group is the path records the figure check sees,
one path per record, `d` copied as stored, with no union and
no added closepath. They do not say to skip a
`weedlines-correction` id, to omit a "Weedlines corrections"
group from that copy, to ignore record paint, or that
`keep_d` is not the design path data. The job section's
one-record, no-closepath, no-union, and omit-corrections
rules are about the job, not this copy. The plan and the
stage say the missing behavior. The guide does not. Nothing
was checked.
