from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction

from records.codec import (
    decode_bounds, decode_fraction, decode_payload, encode_bounds, encode_fraction, encode_payload,
)
from reports.window import InspectionWindow, make_window


@dataclass(frozen=True, slots=True)
class AreaRow:
    winding: int
    area: Fraction


@dataclass(frozen=True, slots=True)
class ReportBreakdown:
    window: InspectionWindow
    rows: tuple[AreaRow, ...]
    total_area: Fraction


@dataclass(frozen=True, slots=True)
class InspectionReport:
    number: int
    analysis_id: int
    revision_id: int
    breakdown: ReportBreakdown


def build_breakdown(window: InspectionWindow, areas: Mapping[int, Fraction]) -> ReportBreakdown:
    for winding, area in areas.items():
        if type(winding) is not int or not isinstance(area, Fraction) or area <= 0:
            raise ValueError('each area row must have an integer winding and positive rational area')
    rows = tuple(AreaRow(winding, areas[winding]) for winding in sorted(areas))
    total = sum((row.area for row in rows), Fraction())
    if total != window.area:
        raise ValueError('area rows must account for the entire inspection window')
    return ReportBreakdown(window, rows, total)


def encode_breakdown(breakdown: ReportBreakdown) -> str:
    return encode_payload({
        'version': 1,
        'window': encode_bounds(breakdown.window.bounds()),
        'rows': [[row.winding, encode_fraction(row.area)] for row in breakdown.rows],
        'total_area': encode_fraction(breakdown.total_area),
    })


def decode_breakdown(payload: str) -> ReportBreakdown:
    value = decode_payload(payload)
    if value['version'] != 1:
        raise ValueError('unsupported inspection report format')
    window = make_window(decode_bounds(value['window']))
    rows = value['rows']
    areas = {winding: decode_fraction(area) for winding, area in rows}
    if len(areas) != len(rows):
        raise ValueError('repeated winding in stored area rows')
    breakdown = build_breakdown(window, areas)
    if decode_fraction(value['total_area']) != breakdown.total_area:
        raise ValueError('stored area total disagrees with area rows')
    return breakdown
