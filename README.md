# Weedlines

Inkscape extension and shared solvers for **weed cuts** on vinyl (and
similar) designs. Algorithms run in a Start / Cancel dialog with a live
preview of SVG constructions as cuts are emitted.

Extracted from a private Inkcut fork; intended to stay standalone until
the algorithms are solid, then optionally integrate back into
[Inkcut](https://github.com/inkcut/inkcut).

## Algorithms

| Mode | Behavior |
| --- | --- |
| `frame` | Padded outer box |
| `grid` | Axis-aligned grid over waste |
| `island-hop` | Peel-frame + ranked seals / island merge (needs `pyclipper`) |

Default mode is `frame`. Do not treat `island-hop` as production-default
until picture QA is accepted.

## Install

```bash
cd ~/dev/me/weedlines
python3 -m pip install -e '.[island-hop,dev]'   # editable + pyclipper + pytest
# Qt binding required (one of):
#   python3 -m pip install PyQt5   # or PyQt6 / PySide6 / …

weedlines install          # symlink into ~/.config/inkscape/extensions
weedlines install --dry-run
weedlines update           # git pull if clean, then install
```

Restart Inkscape → **Extensions → Weedlines → Weedlines from selection…**

## Logging

| Env | Effect |
| --- | --- |
| unset / `0` | Quiet (default) |
| `WEEDLINES_LOG=1` | Decisions, phases, rejects, audits |
| `WEEDLINES_LOG=2` / `trace` | Also every `emit.accept` |

```bash
WEEDLINES_LOG=1 rg 'phase\.|island_hop\.|emit\.|reject' …
```

The dialog enables level `1` for the run so the live log is useful.

## Library

```python
from weedlib import generate_weeds, frame_weeds, grid_weeds, island_hop_weeds
```

`weedlib` is the stable import for a future Inkcut integration. The CLI
package is `weedlines`.

## License

GPL-3.0-or-later (Inkcut lineage).
