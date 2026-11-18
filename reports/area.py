from fractions import Fraction
from itertools import pairwise

from analysis.crossings import crossing_x_at_y, height_at
from analysis.evidence import DirectedPassage, FrozenEvidence
from reports.sweep import window_cuts
from reports.window import InspectionWindow


def winding_at(
    passages: tuple[DirectedPassage, ...], x: Fraction, y: Fraction,
) -> int:
    """Signed winding number of the traced loops around point (x, y).

    A horizontal ray is cast from the point toward +x. A passage directed
    upward across the ray contributes +1 (counterclockwise) and a passage
    directed downward contributes -1, regardless of whether its segment leans
    left or right. Coincident passages add per traversal, opposite passages
    cancel, and a point on any boundary is excluded by the strict span test.
    """
    winding = 0
    for passage in passages:
        cross_x = crossing_x_at_y(passage, y)
        if cross_x is not None and cross_x > x:
            if passage.end.y > passage.start.y:
                winding += 1
            else:
                winding -= 1
    return winding


def _strip_y_cuts(
    passages: tuple[DirectedPassage, ...], window: InspectionWindow, x: Fraction,
) -> tuple[Fraction, ...]:
    cuts = {window.bottom, window.top}
    for passage in passages:
        cuts.add(passage.start.y)
        cuts.add(passage.end.y)
        # Non-vertical passages spanning the sample line fix every height at
        # which the winding can change inside this vertical strip.
        if not passage.vertical and passage.left < x < passage.right:
            cuts.add(height_at(passage, x))
    return tuple(sorted(cuts))


def calculate_winding_areas(evidence: FrozenEvidence, window: InspectionWindow) -> dict[int, Fraction]:
    passages = evidence.passages
    # Between consecutive x cuts no vertex, vertical passage, window edge or
    # non-vertical passage intersection changes the arrangement, so the winding
    # number is constant on each open vertical strip.
    x_cuts = window_cuts(passages, window)
    areas: dict[int, Fraction] = {}
    for strip_left, strip_right in pairwise(x_cuts):
        left = max(strip_left, window.left)
        right = min(strip_right, window.right)
        if left >= right:
            continue
        x = (strip_left + strip_right) / 2
        y_cuts = _strip_y_cuts(passages, window, x)
        for lower, upper in pairwise(y_cuts):
            bottom = max(lower, window.bottom)
            top = min(upper, window.top)
            if bottom >= top:
                continue
            # Cuts include every passage height at x, so the row midpoint never
            # lies on a passage and carries the constant winding of the cell.
            winding = winding_at(passages, x, (lower + upper) / 2)
            if winding:
                areas[winding] = areas.get(winding, Fraction()) + (right - left) * (top - bottom)
    zero_area = window.area - sum(areas.values(), Fraction())
    if zero_area > 0:
        areas[0] = zero_area
    return areas
