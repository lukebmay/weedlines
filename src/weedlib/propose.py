# -*- coding: utf-8 -*-
"""Proposals for defects the figure check already reported."""
from __future__ import division

from dataclasses import dataclass

from .figures.types import Defect


@dataclass
class Proposal:
    """One defect and its replacement path, or none when it is kept."""

    defect: Defect
    path: object


def propose(check):
    """One proposal per self-overlap on *check*, in that order.

    *check* is the figure check the caller already ran. Each
    self-overlap is kept, so the path is none. The check does not
    separate a smooth stack, a corner stack, and a larger overlap.
    Dangling ends and separate-figure overlaps are omitted.
    """
    proposals = []
    for defect in check.defects:
        if defect.kind != "self-overlap":
            continue
        proposals.append(Proposal(defect, None))
    return proposals
