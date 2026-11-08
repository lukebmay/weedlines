# weedlines_dialog

- `__init__.py` builds the dialog, runs it, and returns the Apply path, the layer name, and the weed-line color.
- `geometry_ask.py` spawns one ask and installs progress, cancel, pause, focus, and the solver log in the child.
- `inbox.py` pumps the pipe on the GUI thread.
- `preview.py` paints the checkerboard, the subject, the arrows, the piece border, the surrounds, and the accepted segments.
- `run_controls.py` owns Start, Restart, Pause, Clear All, Apply, Close, the step row, and the status.
- `form.py` owns the options form: mode, display unit, lengths, colors, swap, and option history.
- `return_line.py` owns the defect line and the two return actions.
