from fractions import Fraction
from itertools import pairwise

from analysis.crossings import height_at
from analysis.evidence import DirectedPassage, FrozenEvidence
from reports.sweep import window_cuts
from reports.window import InspectionWindow


def _covered_height(
    passages: tuple[DirectedPassage, ...], window: InspectionWindow, x: Fraction,
) -> Fraction:
    heights = sorted({
        height_at(passage, x) for passage in passages if passage.left < x < passage.right
    })
    covered = Fraction()
    for bottom, top in zip(heights[::2], heights[1::2]):
        lower = max(bottom, window.bottom)
        upper = min(top, window.top)
        if lower < upper:
            covered += upper - lower
    return covered


def calculate_winding_areas(evidence: FrozenEvidence, window: InspectionWindow) -> dict[int, Fraction]:
    cuts = window_cuts(evidence.passages, window)
    covered = Fraction()
    for left, right in pairwise(cuts):
        x = (left + right) / 2
        covered += (right - left) * _covered_height(evidence.passages, window, x)
    return {winding: area for winding, area in ((0, window.area - covered), (1, covered)) if area}
