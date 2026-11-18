from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from fractions import Fraction

from records.codec import decode_payload, decode_point, encode_payload, encode_point
from specimen.coordinates import Point


@dataclass(frozen=True, slots=True)
class DirectedPassage:
    start: Point
    end: Point

    @property
    def left(self) -> Fraction:
        return min(self.start.x, self.end.x)

    @property
    def right(self) -> Fraction:
        return max(self.start.x, self.end.x)

    @property
    def vertical(self) -> bool:
        return self.start.x == self.end.x


@dataclass(frozen=True, slots=True)
class FrozenEvidence:
    passages: tuple[DirectedPassage, ...]


def build_evidence(loops: Iterable[Sequence[Point]]) -> FrozenEvidence:
    support = set()
    for loop in loops:
        for start, end in zip(loop, loop[1:]):
            if (end.x, end.y) < (start.x, start.y):
                start, end = end, start
            support.add(DirectedPassage(start, end))
    return FrozenEvidence(tuple(sorted(
        support,
        key=lambda passage: (passage.start.x, passage.start.y, passage.end.x, passage.end.y),
    )))


def encode_evidence(evidence: FrozenEvidence) -> str:
    return encode_payload({
        'version': 1,
        'kind': 'directed-passages',
        'passages': [
            [encode_point(passage.start), encode_point(passage.end)]
            for passage in evidence.passages
        ],
    })


def decode_evidence(payload: str) -> FrozenEvidence:
    value = decode_payload(payload)
    if value['version'] != 1 or value['kind'] != 'directed-passages':
        raise ValueError('unsupported frozen evidence format')
    return FrozenEvidence(tuple(
        DirectedPassage(decode_point(start), decode_point(end))
        for start, end in value['passages']
    ))
