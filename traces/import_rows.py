import sqlite3

from records.commit import atomic_write
from specimen.coordinates import parse_point
from specimen.registry import get_trial
from traces.lineage import resolve_parent_revision
from traces.loop_validation import InvalidTrace, TraceLoops, validate_loops
from traces.revisions import save_revision


def decode_trace_rows(rows: object) -> TraceLoops:
    if not isinstance(rows, (list, tuple)):
        raise InvalidTrace('trace export must contain a sequence of loops')
    decoded = []
    for loop_number, loop in enumerate(rows, start=1):
        if not isinstance(loop, (list, tuple)):
            raise InvalidTrace(f'loop {loop_number} must contain a sequence of points')
        points = []
        for point_number, row in enumerate(loop, start=1):
            try:
                points.append(parse_point(row))
            except ValueError as error:
                raise InvalidTrace(f'loop {loop_number}, point {point_number}: {error}') from error
        decoded.append(tuple(points))
    return tuple(decoded)


def import_traces(
    connection: sqlite3.Connection,
    trial_id: str,
    rows: object,
    parent_id: int | None = None,
) -> int:
    loops = decode_trace_rows(rows)
    with atomic_write(connection):
        trial = get_trial(connection, trial_id)
        parent = resolve_parent_revision(connection, trial_id, parent_id)
        validate_loops(loops, trial.frame)
        revision_id = save_revision(connection, trial.trial_id, parent, loops)
    return revision_id
