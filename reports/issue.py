import sqlite3
from collections.abc import Callable

from analysis.catalog import get_analysis
from records.commit import atomic_write
from records.report_index import allocate_report_number
from reports.area import calculate_winding_areas
from reports.breakdown import InspectionReport, build_breakdown, encode_breakdown
from reports.window import make_window


def issue_report(
    connection: sqlite3.Connection,
    analysis_id: int,
    bounds: object,
    *,
    before_commit: Callable[[int], None] | None = None,
) -> InspectionReport:
    window = make_window(bounds)
    analysis = get_analysis(connection, analysis_id)
    areas = calculate_winding_areas(analysis.evidence, window)
    breakdown = build_breakdown(window, areas)
    payload = encode_breakdown(breakdown)

    with atomic_write(connection):
        cursor = connection.execute(
            'INSERT INTO inspection_report(analysis_id, revision_id, payload) VALUES (?, ?, ?)',
            (analysis.analysis_id, analysis.revision_id, payload),
        )
        number = allocate_report_number(connection, cursor.lastrowid)
        if before_commit is not None:
            before_commit(number)
    return InspectionReport(number, analysis.analysis_id, analysis.revision_id, breakdown)
