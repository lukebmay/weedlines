# Handoff (weedlines)

**Updated:** 2026-08-21
**Branch:** `master`
**GitHub:** `lukebmay/weedlines`
**Path:** `~/dev/me/weedlines`

## Status

Initial extract landed from `inkcut_luke` archive:

- `src/weedlib/` — solvers (frame / grid / island-hop), progress, debug
- `extensions/inkscape/` — Start/Cancel dialog + live preview
- `weedlines` CLI — `install` / `update`
- Logging: `WEEDLINES_LOG=0|1|2` (legacy `INKCUT_WEED_DEBUG` alias)
- Tests: 136 passed, 4 skipped (Job pipeline)

## Next

1. Island-hop picture QA / refine algorithms
2. Keep adding named algorithms; do not default island-hop
3. Later: integrate `weedlib` into `~/dev/me/inkcut` → PR to OG

## Installed locally

`weedlines install` → symlinks in `~/.config/inkscape/extensions/`.
Restart Inkscape after pulls. Pause/Resume is in the dialog (2026-08-21).

## Source archive

`~/dev/me/inkcut_luke` @ `archive/pre-repartner-2026-08-21`
