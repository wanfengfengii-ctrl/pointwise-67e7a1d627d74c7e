from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True, slots=True)
class Point:
    x: Fraction
    y: Fraction


def parse_rational(value: object) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if type(value) is int:
        return Fraction(value)
    if isinstance(value, (list, tuple)) and len(value) == 2:
        numerator, denominator = value
        if type(numerator) is int and type(denominator) is int:
            if denominator == 0:
                raise ValueError('rational denominator must be nonzero')
            return Fraction(numerator, denominator)
    raise ValueError('expected an integer, Fraction, or integer numerator and denominator')


def parse_point(value: object) -> Point:
    if isinstance(value, Point):
        return Point(parse_rational(value.x), parse_rational(value.y))
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError('a point must contain two coordinates')
    return Point(parse_rational(value[0]), parse_rational(value[1]))


def parse_bounds(value: object) -> tuple[Fraction, Fraction, Fraction, Fraction]:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise ValueError('bounds must contain left, bottom, right, and top')
    left, bottom, right, top = value
    return parse_rational(left), parse_rational(bottom), parse_rational(right), parse_rational(top)
