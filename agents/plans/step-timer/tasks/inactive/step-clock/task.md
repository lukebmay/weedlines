# Step clock

**Status:** done

## Goal

The window shows how long each started step has been
working. The clock stays in the window.

## Do

Edit `extensions/inkscape/weedlines_dialog/run_controls.py`.
The step row is built in `_step_line`. Put each step's
time on that row. The object names are `step-cut-time`,
`step-surround-time`, and `step-conquer-time`.

The window owns the clock. Do not edit the library, and
do not let it read or advance the clock. Do not edit
`__init__.py`, `inbox.py`, `geometry_ask.py`, `form.py`,
`preview.py`, or `return_line.py`.

A step that has not been started shows no time. The
label stays, and its text is empty. Conquer's Start
stays disabled, so that step shows no time. The border
ask is not a started step and does not advance a time.
Do not edit the piece-border lengths. Do not name the
two border labels. Do not invent a cavern measure.

The time advances only while that step is working. It
holds while the step is paused. When the step finishes,
the window keeps showing that working time. The status
text stays ready, working, paused, or done. A phase
name stays in that status and is not a time. The time
is not part of the status text and not a log line.

Frame, grid, and island-hop share the cut step row.
Each of those steps keeps its own time. The row shows
the time for the mode on screen. Changing mode does
not zero a time. Restart starts the current step from
zero and discards every later step's time with its
lines. Earlier steps keep theirs. Clear All discards
every step's time with the lines. When a step is no
longer started, it shows no time.

Ticking does not run geometry and does not change a
cut. The tick does not ask for a border, a surround,
or a solver, and it does not repaint the preview.

## Checks

Window tests run offscreen when Qt is available. Follow
the skip in `tests/test_window_timing.py`. Add
`tests/test_window_step_time.py`. Add one line for it
in `tests/README.md`, beside the timing line. A run
those timing tests can hold open is long enough for
this time to change. Do not sleep the GUI thread.

- Before Start, the three time labels are empty.
  Conquer's Start is disabled.
- While a started step is working, its time changes.
  The status still starts with working. A phase name
  does not add a time.
- While that step is paused, the time text stays put
  and the status starts with paused.
- When the step is done, that same time stays.
- Restart of that step starts its time from zero.
  Conquer's time stays empty. Another mode's started
  step keeps its time.
- Clear All leaves every time label empty and the
  status ready.
- Pumping the clock does not add a solver or surround
  call and does not change the cut.
- The library is unchanged.

## Note

Each step row has a time label: `step-cut-time`,
`step-surround-time`, and `step-conquer-time`. The text is
empty until that step is started. A started step shows its
working time in seconds, to a tenth. The cut row shows the
time for the mode on screen. Frame, grid, and island-hop
each keep their own time. Conquer's label stays empty.

The time advances only while that step's ask is working.
Pause holds it. A finished step keeps the working time.
Restart sets that step back to zero and drops a later
step's time. Clear All drops every time. A border ask
does not advance one. The tick only rewrites the labels.
It does not ask, log, or repaint the preview. The status
text is unchanged. The library was not edited.

Why: the window owns the clock. The person can see how
long the started step has been working, and a pause is
not counted as the algorithm running.

Checked with `QT_QPA_PLATFORM=offscreen python3 -m pytest
tests/test_window_step_time.py tests/test_window_timing.py`:
12 passed in 5.87s. No Inkscape. `tests/README.md` has one
line for `test_window_step_time.py` beside the timing line.

Summary: No defects. The three time labels are empty before
Start, and conquer stays empty. A working step's time
changes while the status starts with working. Pause holds
that text. Done keeps it. Restart starts that step from a
smaller time and another mode keeps its own. Clear All
empties every label and the status is ready. A border ask
does not move a finished time. Pumping the clock does not
add a solver or surround call or change the preview.

Context worth keeping: The labels are `step-cut-time`,
`step-surround-time`, and `step-conquer-time`. The text is
seconds to a tenth. The slice is monotonic time while the
ask is a working solver or surround. Pause freezes it. The
cut row shows the mode on screen, and frame, grid, and
island-hop keep separate totals. Restart of surround drops
conquer's total. Conquer's Start stays disabled, so that
label is always empty. The tick only rewrites the labels.
The status text is still ready, working, paused, or done,
and a phase name stays there. The pass is `cr-01.md`. The
library was not edited. `docs/user/surround.md` is not this
change.

Result: No defects remain. The named checks passed.
`QT_QPA_PLATFORM=offscreen python3 -m pytest
tests/test_window_step_time.py tests/test_window_timing.py`:
12 passed in 6.12s. No Inkscape. `src/weedlib` was not
edited.
