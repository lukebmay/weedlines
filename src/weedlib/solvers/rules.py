# -*- coding: utf-8 -*-
"""Mode list and the numeric floors."""
from __future__ import division

from collections import namedtuple


WEED_MODES = ('frame', 'grid', 'region', 'island-hop', 'auto')  # auto=alias
DEFAULT_WEED_MODE = 'frame'
DEFAULT_GRID_SPACING = 25.0

# Auto peel defaults (device units; mm-scale when job units are mm)
DEFAULT_MAX_CHUNK = 60.0
DEFAULT_BRIDGE_WIDTH = 4.0
DEFAULT_CLEARANCE = 0.5
DEFAULT_MIN_CUT = 2.0
# Above 90° so box corners are not convex "tips"
DEFAULT_DELICATE_ANGLE_DEG = 95.0
DEFAULT_COLLAR = 4.0
DEFAULT_MAX_SPOKES = 24
# D012 hard floors (all modes).
DEFAULT_BODY_CLEARANCE = 5.0
DEFAULT_ALPHA_MIN = 30.0
DEFAULT_FRAME_CLEARANCE = 20.0
# Soft planner band for grow-and-frame standoff (knob stays one number).
_FRAME_CLEARANCE_SOFT_MAX = 30.0
# Channels stop this far from keep so a slight vinyl slip does not nick it.
DEFAULT_CHANNEL_STANDOFF = 1.0
# Legacy bay depth gate (D001); C8 prefers κ/undercut (D007).
DEFAULT_PENINSULA_RATIO = 0.75
# Ray / flare search probe into waste (not an emit endpoint inset).
_SEARCH_PROBE = 0.08
# Legacy C9 α; emit floor is DEFAULT_ALPHA_MIN (D012).
_ALPHA_HARD = 18.0
_ALPHA_GRAZE = 10.0  # connected-ends only
# Alias of DEFAULT_ALPHA_MIN (bay peel-wall / emit floor).
_ALPHA_MIN_PEEL = DEFAULT_ALPHA_MIN
# Endpoint class order for ranking (lower is better).
_EP_CORNER = 0
_EP_FRAME = 1
_EP_EDGE = 2
CutRules = namedtuple(
    'CutRules', 'body_clearance alpha_min frame_clearance')


def _cut_rules(body_clearance=None, alpha_min=None, frame_clearance=None):
    """Resolve D012 knobs (defaults 5 / 30° / 20)."""
    return CutRules(
        max(float(body_clearance if body_clearance is not None
                  else DEFAULT_BODY_CLEARANCE), 0.0),
        max(float(alpha_min if alpha_min is not None
                  else DEFAULT_ALPHA_MIN), 0.0),
        max(float(frame_clearance if frame_clearance is not None
                  else DEFAULT_FRAME_CLEARANCE), 0.0),
    )


def _hunt_radius(gap_w, overlap_l=0.0):
    """Corner / coast hunt radius: max(8, 1.2w, 0.35L)."""
    return max(8.0, 1.2 * float(gap_w), 0.35 * float(overlap_l))
