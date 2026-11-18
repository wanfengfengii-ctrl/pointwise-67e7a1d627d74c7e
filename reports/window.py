from dataclasses import dataclass
from fractions import Fraction

from specimen.coordinates import parse_bounds


@dataclass(frozen=True, slots=True)
class InspectionWindow:
    left: Fraction
    bottom: Fraction
    right: Fraction
    top: Fraction

    def __post_init__(self) -> None:
        if self.left >= self.right or self.bottom >= self.top:
            raise ValueError('inspection window must have positive width and height')

    @property
    def area(self) -> Fraction:
        return (self.right - self.left) * (self.top - self.bottom)

    def bounds(self) -> tuple[Fraction, Fraction, Fraction, Fraction]:
        return self.left, self.bottom, self.right, self.top


def make_window(bounds: object) -> InspectionWindow:
    return InspectionWindow(*parse_bounds(bounds))
