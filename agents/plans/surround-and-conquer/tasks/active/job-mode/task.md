# Job mode

**Status:** in-progress

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

The developer writes what changed, why, and how it was checked.
The reviewer then writes the summary, the context worth keeping,
and the result.
