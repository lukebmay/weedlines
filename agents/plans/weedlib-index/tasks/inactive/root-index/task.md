# Root index

**Status:** done

## Goal

`src/weedlib/README.md` names each source file directly
in that directory, with one sentence for what the file
owns.

## Do

Create `src/weedlib/README.md`. Do not edit any other
file.

The heading is `weedlib`. One entry for each of these
files, once, in this order:

- `__init__.py`
- `arrows.py`
- `debug.py`
- `keep.py`
- `paths.py`
- `piece_border.py`
- `progress.py`
- `qt.py`
- `ready.py`
- `svg_paths.py`

The entry is the file name and one sentence. Read the
file for what it owns. Do not copy the module into the
index.

Do not list files under `figures/`, `solvers/`, or
`surround/`. Leave `figures/README.md`,
`solvers/README.md`, and `surround/README.md` as they
are. Do not restate them.

No product code changes.

## Checks

- The index is `src/weedlib/README.md`.
- Each file in the list above appears once, with one
  sentence, in that order.
- No other source file is listed.
- `figures/README.md`, `solvers/README.md`, and
  `surround/README.md` are unchanged.
- The only change is the new index.

## Note

Created `src/weedlib/README.md`. The heading is
`weedlib`. One sentence each, in order, for
`__init__.py`, `arrows.py`, `debug.py`, `keep.py`,
`paths.py`, `piece_border.py`, `progress.py`, `qt.py`,
`ready.py`, and `svg_paths.py`. No other source file
is listed. The source files were not edited.
`figures/README.md`, `solvers/README.md`, and
`surround/README.md` were not edited.

Why: `src/weedlib/` has more than one source file and
had no index. Each sentence names what that file owns,
so the next reader opens the index and then one file.
The subdirectory indexes stay the maps of those
directories.

Checked by reading `src/weedlib/README.md` against the
ten modules and the list in this task. Each name
appears once, in that order, and each entry is one
sentence. The ten `*.py` files directly in
`src/weedlib/` are that same list.
`git diff -- src/weedlib/figures/README.md
src/weedlib/solvers/README.md
src/weedlib/surround/README.md` is empty. No source
file under `src/weedlib/` was edited. Status left
`in-progress`.

Summary: No defects. `src/weedlib/README.md` is the
new index. The heading is `weedlib`. The ten root
files appear once, in the task order, each with one
sentence that names what that file owns. No file
under `figures/`, `solvers/`, or `surround/` is
listed.

Context worth keeping: `git status --short --
src/weedlib` is only untracked `src/weedlib/README.md`.
`git diff` is empty for the ten modules and for
`figures/README.md`, `solvers/README.md`, and
`surround/README.md`. Other dirty paths are outside
`src/weedlib` and are not this change. There is no
automated test. No test reads the index. The pass is
`cr-01.md`. Status stays `in-progress`.

Result: No defects remain. The named checks passed.
There is no automated test.
