import sqlite3
from dataclasses import dataclass

from records.codec import decode_payload, decode_point, encode_payload, encode_point
from traces.loop_validation import TraceLoops


class UnknownRevision(LookupError):
    pass


class ArchivedRevision(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class RevisionIdentity:
    revision_id: int
    trial_id: str
    parent_id: int | None
    archived: bool


@dataclass(frozen=True, slots=True)
class TraceRevision:
    identity: RevisionIdentity
    loops: TraceLoops


def save_revision(
    connection: sqlite3.Connection,
    trial_id: str,
    parent_id: int | None,
    loops: TraceLoops,
) -> int:
    payload = encode_payload([[encode_point(point) for point in loop] for loop in loops])
    cursor = connection.execute(
        'INSERT INTO trace_revision(trial_id, parent_id) VALUES (?, ?)',
        (trial_id, parent_id),
    )
    revision_id = cursor.lastrowid
    connection.execute(
        'INSERT INTO online_traces(revision_id, payload) VALUES (?, ?)',
        (revision_id, payload),
    )
    return revision_id


def _read_identity(row: sqlite3.Row | None, revision_id: int) -> RevisionIdentity:
    if row is None:
        raise UnknownRevision(revision_id)
    return RevisionIdentity(row['revision_id'], row['trial_id'], row['parent_id'], bool(row['archived']))


def load_revision_identity(connection: sqlite3.Connection, revision_id: int) -> RevisionIdentity:
    if type(revision_id) is not int or revision_id <= 0:
        raise UnknownRevision(revision_id)
    row = connection.execute(
        'SELECT revision_id, trial_id, parent_id, archived FROM trace_revision WHERE revision_id = ?',
        (revision_id,),
    ).fetchone()
    return _read_identity(row, revision_id)


def load_online_revision(connection: sqlite3.Connection, revision_id: int) -> TraceRevision:
    if type(revision_id) is not int or revision_id <= 0:
        raise UnknownRevision(revision_id)
    row = connection.execute(
        '''SELECT r.revision_id, r.trial_id, r.parent_id, r.archived, o.payload
           FROM trace_revision AS r LEFT JOIN online_traces AS o USING (revision_id)
           WHERE r.revision_id = ?''',
        (revision_id,),
    ).fetchone()
    identity = _read_identity(row, revision_id)
    if identity.archived:
        raise ArchivedRevision(f'revision {revision_id} is archived')
    if row['payload'] is None:
        raise sqlite3.IntegrityError(f'online traces are missing for revision {revision_id}')
    loops = tuple(tuple(decode_point(point) for point in loop) for loop in decode_payload(row['payload']))
    return TraceRevision(identity, loops)
