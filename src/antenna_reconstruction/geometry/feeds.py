"""Composable feed structures.

Nearly every printed antenna has one, and three of the four reconstructable
sample papers show a feed the templates could not express. These are built from
the same primitives as everything else and follow the same rule: a feed part is
emitted only when its dimensions are determined, never defaulted.
"""
from typing import List, Optional, Tuple

from .primitives import GeometryError, Point, Ring, difference, rectangle

__all__ = [
    "microstrip_line", "inset_notches", "inset_feed_length", "feed_to_patch_gap",
]


def microstrip_line(cx: float, y_start: float, y_end: float,
                    width: float) -> Ring:
    """A straight feed line of `width`, centred on x = cx."""
    if width <= 0:
        raise GeometryError(f"feed width must be > 0, got {width}")
    if y_end <= y_start:
        raise GeometryError(
            f"feed must have positive length, got y {y_start} -> {y_end}"
        )
    return rectangle(cx - width / 2.0, y_start, cx + width / 2.0, y_end)


def feed_to_patch_gap(substrate_length: float, patch_length: float) -> float:
    """Distance from the substrate's bottom edge to a centred patch's edge."""
    gap = (substrate_length - patch_length) / 2.0
    if gap <= 0:
        raise GeometryError(
            f"patch length {patch_length} leaves no room on a substrate of "
            f"{substrate_length}"
        )
    return gap


def inset_feed_length(substrate_length: float, patch_length: float,
                      inset_depth: float) -> float:
    """Total feed length for a centred, inset-fed patch.

    The line runs from the substrate edge to the patch edge, then continues
    `inset_depth` into the patch. This identity is what lets an inset-fed
    design be checked: the microstrip paper prints 23.7 mm of feed and a
    9.25 mm inset on a 57.8/28.9 substrate-patch pair, and
    (57.8 - 28.9)/2 + 9.25 = 23.7 exactly.
    """
    return feed_to_patch_gap(substrate_length, patch_length) + inset_depth


def inset_notches(cx: float, patch_y_bottom: float, feed_width: float,
                  gap: float, depth: float) -> List[Ring]:
    """The two slots cut into a patch to accept an inset feed."""
    if gap <= 0:
        raise GeometryError(f"inset gap must be > 0, got {gap}")
    if depth <= 0:
        raise GeometryError(f"inset depth must be > 0, got {depth}")
    half = feed_width / 2.0
    top = patch_y_bottom + depth
    return [
        rectangle(cx - half - gap, patch_y_bottom, cx - half, top),
        rectangle(cx + half, patch_y_bottom, cx + half + gap, top),
    ]


def apply_inset(patch_ring: Ring, cx: float, patch_y_bottom: float,
                feed_width: float, gap: float, depth: float) -> List[Ring]:
    """Cut the inset slots out of a patch outline."""
    notches = inset_notches(cx, patch_y_bottom, feed_width, gap, depth)
    return difference(patch_ring, notches)
