from dataclasses import dataclass
from fractions import Fraction

from specimen.coordinates import Point, parse_bounds


@dataclass(frozen=True, slots=True)
class MeasurementFrame:
    left: Fraction
    bottom: Fraction
    right: Fraction
    top: Fraction

    def __post_init__(self) -> None:
        if self.left >= self.right or self.bottom >= self.top:
            raise ValueError('measurement frame must have positive width and height')

    def contains(self, point: Point) -> bool:
        return self.left <= point.x <= self.right and self.bottom <= point.y <= self.top

    def bounds(self) -> tuple[Fraction, Fraction, Fraction, Fraction]:
        return self.left, self.bottom, self.right, self.top


def make_frame(bounds: object) -> MeasurementFrame:
    return MeasurementFrame(*parse_bounds(bounds))
