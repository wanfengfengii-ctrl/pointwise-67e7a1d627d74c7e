from typing import TypeAlias

from specimen.coordinates import Point
from specimen.frame import MeasurementFrame


TraceLoops: TypeAlias = tuple[tuple[Point, ...], ...]


class InvalidTrace(ValueError):
    pass


def validate_loops(loops: TraceLoops, frame: MeasurementFrame) -> None:
    for loop_number, points in enumerate(loops, start=1):
        if len(points) < 2 or points[0] != points[-1]:
            raise InvalidTrace(f'loop {loop_number} must be a closed polyline')
        for point_number, point in enumerate(points, start=1):
            if not frame.contains(point):
                raise InvalidTrace(f'loop {loop_number}, point {point_number} lies outside the frame')
