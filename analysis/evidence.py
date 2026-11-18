from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from fractions import Fraction

from records.codec import decode_payload, decode_point, encode_payload, encode_point
from specimen.coordinates import Point

# Version 2 keeps every directed passage as traced: repeated coincident passages
# accumulate and opposite passages stay distinct so they can cancel downstream.
EVIDENCE_VERSION = 2
# Version 1 canonicalized each passage into an undirected support segment. It is
# accepted on read so databases frozen before the signed-evidence repair stay
# readable; the stored geometric order is then treated as the directed order.
LEGACY_EVIDENCE_VERSIONS = frozenset({1})


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

    @property
    def stationary(self) -> bool:
        return self.start == self.end


@dataclass(frozen=True, slots=True)
class FrozenEvidence:
    passages: tuple[DirectedPassage, ...]


def build_evidence(loops: Iterable[Sequence[Point]]) -> FrozenEvidence:
    # Each traced segment is a signed passage. A stationary passage (identical
    # endpoints) cannot cross any inspection ray and is dropped. Coincident
    # passages are retained once per traversal, including opposite directions,
    # so winding counts accumulate and reverse traversals cancel.
    passages: list[DirectedPassage] = []
    for loop in loops:
        for start, end in zip(loop, loop[1:]):
            if start == end:
                continue
            passages.append(DirectedPassage(start, end))
    return FrozenEvidence(tuple(sorted(
        passages,
        key=lambda passage: (
            passage.start.x, passage.start.y, passage.end.x, passage.end.y,
        ),
    )))


def encode_evidence(evidence: FrozenEvidence) -> str:
    return encode_payload({
        'version': EVIDENCE_VERSION,
        'kind': 'directed-passages',
        'passages': [
            [encode_point(passage.start), encode_point(passage.end)]
            for passage in evidence.passages
        ],
    })


def decode_evidence(payload: str) -> FrozenEvidence:
    value = decode_payload(payload)
    version = value.get('version')
    if value.get('kind') != 'directed-passages' or (
        version != EVIDENCE_VERSION and version not in LEGACY_EVIDENCE_VERSIONS
    ):
        raise ValueError('unsupported frozen evidence format')
    return FrozenEvidence(tuple(
        DirectedPassage(decode_point(start), decode_point(end))
        for start, end in value['passages']
    ))
