import json
from collections.abc import Iterable
from fractions import Fraction

from specimen.coordinates import Point


def encode_fraction(value: Fraction) -> list[str]:
    # Hex keeps large exact integers independent of the decimal conversion limit.
    return [format(value.numerator, 'x'), format(value.denominator, 'x')]


def decode_fraction(value: list[str]) -> Fraction:
    numerator, denominator = value
    return Fraction(int(numerator, 16), int(denominator, 16))


def encode_bounds(bounds: Iterable[Fraction]) -> list[list[str]]:
    return [encode_fraction(value) for value in bounds]


def decode_bounds(bounds: Iterable[list[str]]) -> tuple[Fraction, ...]:
    return tuple(decode_fraction(value) for value in bounds)


def encode_point(point: Point) -> list[list[str]]:
    return [encode_fraction(point.x), encode_fraction(point.y)]


def decode_point(value: list[list[str]]) -> Point:
    x, y = value
    return Point(decode_fraction(x), decode_fraction(y))


def encode_payload(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def decode_payload(payload: str):
    return json.loads(payload)
