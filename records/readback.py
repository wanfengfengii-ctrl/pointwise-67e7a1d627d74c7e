import sqlite3

from records.report_index import resolve_report_number
from reports.breakdown import InspectionReport, decode_breakdown


class ReportNotFound(LookupError):
    pass


def read_report(connection: sqlite3.Connection, number: int) -> InspectionReport:
    body_id = resolve_report_number(connection, number)
    if body_id is None:
        raise ReportNotFound(number)
    row = connection.execute(
        'SELECT analysis_id, revision_id, payload FROM inspection_report WHERE body_id = ?',
        (body_id,),
    ).fetchone()
    if row is None:
        raise sqlite3.IntegrityError(f'body is missing for report {number}')
    return InspectionReport(number, row['analysis_id'], row['revision_id'], decode_breakdown(row['payload']))
