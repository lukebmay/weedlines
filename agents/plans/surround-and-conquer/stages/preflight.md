# Preflight

## This stage

Make the shared figure check, the preview, and the correction
return real for every algorithm that already cuts.

The library classifies figures and builds the arrow paths. The
host carries the original paths and fills into the job, and
import places a correction result above the document. The window
paints subject and weed area, gates Start, and offers the two
return actions under the preview.

User-visible correction steps belong in `docs/user/`. The root
README does not gain a Surround and Conquer row in this stage.

Tests for the check and the result writer do not need Inkscape.
Window tests run offscreen when Qt is available.

## Not yet

This stage is finished. The surround step is the algorithm
stage. This file does not add tasks.
