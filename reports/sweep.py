from fractions import Fraction
from itertools import combinations

from analysis.crossings import horizontal_crossing_x, intersection_x
from analysis.evidence import DirectedPassage
from reports.window import InspectionWindow


def window_cuts(
    passages: tuple[DirectedPassage, ...], window: InspectionWindow,
) -> tuple[Fraction, ...]:
    cuts = {window.left, window.right}
    spanning = []
    for passage in passages:
        for x in (passage.left, passage.right):
            if window.left < x < window.right:
                cuts.add(x)
        if passage.vertical or passage.right <= window.left or passage.left >= window.right:
            continue
        spanning.append(passage)
        for y in (window.bottom, window.top):
            x = horizontal_crossing_x(passage, y)
            if x is not None and window.left < x < window.right:
                cuts.add(x)

    for first, second in combinations(spanning, 2):
        x = intersection_x(first, second)
        if x is not None and window.left < x < window.right:
            cuts.add(x)
    return tuple(sorted(cuts))
