# inkscape

- `stdio_capture.py` captures stdout and stderr so Qt chatter never reaches Inkscape, and keeps those lines for the dialog log.
- `weedlines.py` records the selection, detaches the window, and writes the weed layer only when the run stays inline.
- `weedlines_host.py` runs the detached window and writes the result files when Apply returns cuts.
- `weedlines_import.py` places the last weed-line result on one new layer, or the ready file on the corrections layer.
- `weedlines_job.py` owns the cache directory, writes the job and result records, and launches a detached script.
- `weedlines_ready.py` detaches the ready check and writes the ready file only when that check finds a defect.
- `weedlines_svg.py` writes and loads the result and correction SVGs, including document size and the ready-fixes group.
