# Job mode

**Status:** done

## Goal

When the person has not chosen a mode, the job names Surround
and Conquer. The window then opens on that mode.

## Do

- Edit `extensions/inkscape/weedlines.py` only, plus the new
  test below. The mode value is `Surround and Conquer`, the same
  value the window task shows.
- The argument default, and the fallback when the mode is missing
  or blank, store that exact string on the job. Do not fold it
  to a slug. A chosen `frame`, `grid`, or `island-hop` stays that
  lowercase value. This is the unchosen path in both the detached
  job and the inline path, which share those defaults.
- Do not change `generate_weeds`. An unknown mode still runs as
  frame inside the solver. Do not edit the dialog, `src/weedlib/`,
  `extensions/inkscape/weedlines.inx`, `docs/`, or `README.md`.
- Tests go in `tests/test_default_mode.py`. Load the extension
  the way `tests/test_inkscape_args.py` does. No Inkscape. Do not
  edit `tests/test_window_gate.py`.

## Checks

- An omitted mode and a blank mode store `Surround and Conquer`.
- `--mode=frame` stays `frame`. `--mode=island-hop` stays
  `island-hop`.
- `pytest tests/test_default_mode.py tests/test_inkscape_args.py`
  passes without Inkscape.

## Note

An omitted `--mode` now defaults to `Surround and Conquer`. A
missing mode, an empty mode, or a whitespace-only mode stores
that same string on the job. The value is not lowercased and not
turned into a slug. A chosen `frame`, `grid`, or `island-hop`
stays that lowercase string. Both the detached job and the inline
path use this one `defaults` dict. `generate_weeds` is unchanged,
so an unknown mode still runs as frame inside the solver.

Why: the host was still naming `frame` when the person had not
chosen, and `.lower()` would have folded the window's mode string.

Checked on `master` with `pytest tests/test_default_mode.py
tests/test_inkscape_args.py`: 4 passed. No Inkscape. The dialog,
`src/weedlib/`, `docs/`, and `README.md` were not edited.
Status left `in-progress`.

Summary: No defects. An omitted, missing, empty, or whitespace-only
mode stores `Surround and Conquer` on the job. A chosen `frame`,
`grid`, or `island-hop` stays that lowercase string. The detached
job and the inline path share one `defaults` dict. `generate_weeds`
is unchanged.

Context worth keeping: `_UNCHOSEN_MODE` is the argument default and
the fallback in `_mode_on_job`. A non-blank string is stored as
given, not lowercased and not slugged. `effect` puts that value on
one `defaults` dict before the inline branch. `write_job` and
`run_weedlines_dialog` both use it. `write_job` does not rewrite
`mode`. `weedlines.inx` has no mode parameter, so an Inkscape launch
omits `--mode`. `src/weedlib/solvers.py` is not in this diff; an
unknown mode there still runs as `frame`. Opening the window on
that string is the window-surround task. This pass did not edit
the dialog, `docs/user/surround.md`, or the window tests. The pass
is `cr-01.md`.

Result: No defects remain. The named checks passed.
`pytest tests/test_default_mode.py tests/test_inkscape_args.py`
passed: 4 passed, no Inkscape.
