# Inkscape index

**Status:** done

## Goal

`extensions/inkscape/README.md` names each source
file directly in that directory, with one sentence
for what the file owns. Product behavior does not
change.

## Do

Create `extensions/inkscape/README.md`. Do not edit
any other file.

The heading is `inkscape`. One entry for each of
these files, once, in this order:

- `stdio_capture.py`
- `weedlines.py`
- `weedlines_host.py`
- `weedlines_import.py`
- `weedlines_job.py`
- `weedlines_ready.py`
- `weedlines_svg.py`

The entry is the file name and one sentence. Read
the file for what it owns. Do not copy the module
into the index.

Do not list `.inx` files. Do not list files under
`weedlines_dialog/`. Leave
`weedlines_dialog/README.md` as it is. Do not
restate it.

No product code changes.

## Checks

- The index is `extensions/inkscape/README.md`.
- Each file in the list above appears once, with
  one sentence, in that order.
- No other file is listed.
- `weedlines_dialog/README.md` is unchanged.
- The only change is the new index.

## Note

Created `extensions/inkscape/README.md`. The heading
is `inkscape`. One sentence each, in order, for
`stdio_capture.py`, `weedlines.py`,
`weedlines_host.py`, `weedlines_import.py`,
`weedlines_job.py`, `weedlines_ready.py`, and
`weedlines_svg.py`. No other file is listed.
`.inx` files and files under `weedlines_dialog/`
are not listed. `weedlines_dialog/README.md` was
not edited. No product code was edited.

Why: `extensions/inkscape/` has more than one
source file and had no index. The next reader
opens the index, then one file.

Checked by reading the index against the seven
modules and the list in this task. Each name
appears once, in that order, and each entry is
one sentence. No other product file changed.
Status left `in-progress`.

Summary: No defect. `extensions/inkscape/README.md`
names the seven source files in that directory,
once each, in the task order, with one sentence.
No other file is listed. The sentences point at
the file that owns the work. No product code
changed.

Context worth keeping: `.inx` files and
`weedlines_dialog/` stay off this index.
`weedlines_dialog/README.md` was not edited and
was not copied. The effect records the selection
and writes the weed layer only on the inline
path. The host writes result files when Apply
returns cuts. Import places a weed-line result
on one new layer, or the ready file on the
corrections layer. The ready file is written
only when that check finds a defect. The pass
is `cr-01.md`.

Result: No defect. The check was reading the
index. There is no test command. Each named
file appears once, in order, with one sentence,
and no other file is listed. The dialog index
is unchanged. No product code changed.
