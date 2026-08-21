# Weed cut hard rules (human freeze — D012)

**Status:** design locked 2026-08-18; implemented in `inkcut/weedlib/solvers.py`
**Canonical decision:** `docs/DECISIONS.md` D012
**Supersedes for emit/ranking:** D006 collar-always-full; D009 α=18° /
parallel-hug as primary floors
**Tone:** geometry-generic only. Glyphs / preview SVGs are calibration
anecdotes — never branch on letter identity.

## Hard floors (all modes: frame, grid, auto)

### Body clearance

- Knob: `weed_body_clearance` (default **5** device units / mm-scale).
- For a candidate cut, ignore the first and last clearance length of the
  segment (those ends must meet design or weed).
- If the **remaining middle** comes within `weed_body_clearance` of any
  **design coast** or **other weed segment**, **reject** the candidate.
- Terminology: **body clearance** (not “semi-parallel”).

### Minimum created angle

- Knob: `weed_alpha_min` (default **30°**).
- Every peel-relevant included angle the cut creates at a landing must
  be ≥ this floor.
- Measure with **created peel angles** at the true corner vertex when
  the anchor is a corner. Emit chosen anchors **exactly** (no hairline
  fuse pull off the corner).

### Non-divergent peel

- If peeling a water region would fork into **two peel fronts** (sticky
  vinyl risk onto land), a **seal is required**.
- Endpoint / 180° ranking chooses *how*; non-divergence chooses *that*.

### No proper weed–weed crosses

- Weed cut interiors must **not** cross other weed cut interiors
  (T-junctions OK). Applies to peel-frame rails and every seal, not
  only body channels. Debug audit: `INKCUT_WEED_DEBUG=1` →
  `audit.cross_weed` (see `agents/notes/weed-debug.md`).

## Peel frame (place first)

### Purpose (soft process — why we frame)

1. Provide **nearby edges** so later seals have legal landings.
2. Keep waste sheets from growing **too large next to small / complex
   keep**. Large waste is easy to pull alone; it becomes a hazard when
   it sits against delicate design.

A few **extra weed cuts outside** the framed region are OK (easy peel).
Do not over-minimize outer cuts at the cost of good isolation.

### Clearance (soft band)

- Knob today: `weed_frame_clearance` (default **20**).
- Human guidance 2026-08-19: treat framing standoff as a **soft range
  ~20–30** device units (mm-scale), not a brittle single 20. Exact
  min/max knobs optional later; planner may pick within the band.
- Mental model when we *do* grow a rail: ~clearance of water inside the
  peel frame along a **simple** path (multi-seg / mild curve OK — not a
  dense offset maze).

### Reuse design frames (firm intent + D013)

- If the design **already has a frame / container**, **do not** grow a
  second peel collar for that interior (D013). Container coasts **are**
  the walls.
- Those same design-frame edges may be used as **partial frame rails**
  for interior object groups that need a nearby landing (only cut
  missing arcs; never a second full collar).
- Still emit one **keep↔container-wall** channel so the inner waste
  loop peels as a corridor (target = container outline).

### When there is no design frame

- Prefer **one outer weed rail** around the working set, then isolate
  with **chords / multi-segs**. Do **not** emit separate peel boxes per
  ornament / tiny cluster that then cross each other.
- **Partial frame** (open water): existing design coasts count as walls;
  only cut missing arcs.
- Frame cuts **never** cross design or other weeds (same firm no-cross
  rule as every weed segment — rails must not bypass the cross gate).
- Emit peel rails **before** other seals so later cuts can begin/end on
  them.
- **Corridor open (auto):** after placing a peel frame, cut one
  keep→frame radial. The peel-rail stays **continuous** (no literal rail
  gap — the radial alone opens the outer collar). Channel length may be
  up to ~frame clearance (ceiling tracks collar gap).
- Legacy `frame` weed mode stays a closed padded box (not auto peel).

## Ranking (among legal candidates)

**Endpoint preference (class order):**

1. &gt;180° weed-side (waste) corners
2. Peel-frame edges
3. Design edges (flat coasts / walls)

**Cost (lower better), after legality:**

- \(E\) = total distance of created angles from 180° (smoother peel →
  smaller \(E\))
- \(L\) = cut length
- Prefer \(\mathrm{cost} \approx E\sqrt{L}\) so **180° quality is about
  twice as important as length** (a cut ~2× longer is OK if ~2× closer
  to 180°).
- Never accept α &lt; `weed_alpha_min` to manufacture a 180° look.

**Search order (auto):** grow the weed graph **outside-in** (outer bays /
frame ties first, then inward seals). Example calibration:
`weed_quoted_in_frame.svg` — close H bays → tie i-dot → dot→stem →
stem→H, using design + peel-frame as rails.

## Forced seal fallback

If non-divergence requires a seal and no fully legal candidate exists:
take least-bad with **never** α &lt; 30°; allow only a tiny body-clearance
backoff as last resort.

## Grid

Same body-clearance and α floors; snap ends toward preferred anchors
when near. **No** outside-in peel planner.

## Knobs (user-facing)

| Knob | Default | Role |
| --- | --- | --- |
| `weed_body_clearance` | 5 | Mid-segment clearance to design/weeds |
| `weed_alpha_min` | 30° | Hard minimum created angle |
| `weed_frame_clearance` | 20 | Grow-and-frame margin; soft band ~20–30 |

Optional later: `weed_frame_mode` = `auto` / `off` / `full` / `partial`;
explicit frame clearance min/max if a single default proves too stiff.

## Do not

- Letter / star / quote type branches
- Default `weed_mode=auto` before picture accept
- Hard-code fixture coordinates
- Re-introduce mid-coast dual-lip fans (D011 still stands for body bays
  under these floors)
- Re-introduce a second peel collar inside a design container (D013)
