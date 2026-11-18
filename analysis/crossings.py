from fractions import Fraction

from analysis.evidence import DirectedPassage


def height_at(passage: DirectedPassage, x: Fraction) -> Fraction:
    start, end = passage.start, passage.end
    if passage.vertical:
        raise ValueError('a vertical passage has no single-valued height')
    return start.y + (x - start.x) * (end.y - start.y) / (end.x - start.x)


def intersection_x(first: DirectedPassage, second: DirectedPassage) -> Fraction | None:
    if first.vertical or second.vertical:
        return None
    left = max(first.left, second.left)
    right = min(first.right, second.right)
    if left >= right:
        return None
    difference_left = height_at(first, left) - height_at(second, left)
    difference_right = height_at(first, right) - height_at(second, right)
    if difference_left * difference_right >= 0:
        # Endpoints already form events. Collinear lines stay coincident in the strip.
        return None
    return left - difference_left * (right - left) / (difference_right - difference_left)


def horizontal_crossing_x(passage: DirectedPassage, y: Fraction) -> Fraction | None:
    start, end = passage.start, passage.end
    if passage.vertical or not min(start.y, end.y) < y < max(start.y, end.y):
        return None
    return start.x + (y - start.y) * (end.x - start.x) / (end.y - start.y)
