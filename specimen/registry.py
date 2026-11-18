import sqlite3
from dataclasses import dataclass

from records.codec import decode_bounds, decode_payload, encode_bounds, encode_payload
from records.commit import atomic_write
from specimen.frame import MeasurementFrame, make_frame
from specimen.intake_policy import should_create_trial


class UnknownTrial(LookupError):
    pass


@dataclass(frozen=True, slots=True)
class Trial:
    trial_id: str
    frame: MeasurementFrame


def _find_frame(connection: sqlite3.Connection, trial_id: str) -> MeasurementFrame | None:
    row = connection.execute('SELECT frame FROM trial WHERE trial_id = ?', (trial_id,)).fetchone()
    if row is None:
        return None
    return make_frame(decode_bounds(decode_payload(row['frame'])))


def get_trial(connection: sqlite3.Connection, trial_id: str) -> Trial:
    if not isinstance(trial_id, str) or not trial_id.strip():
        raise UnknownTrial(trial_id)
    frame = _find_frame(connection, trial_id)
    if frame is None:
        raise UnknownTrial(trial_id)
    return Trial(trial_id, frame)


def register_trial(connection: sqlite3.Connection, trial_id: str, bounds: object) -> str:
    if not isinstance(trial_id, str) or not trial_id.strip():
        raise ValueError('trial identifier must be a nonblank string')
    requested = make_frame(bounds)
    with atomic_write(connection):
        current = _find_frame(connection, trial_id)
        if should_create_trial(trial_id, current, requested):
            payload = encode_payload(encode_bounds(requested.bounds()))
            connection.execute('INSERT INTO trial(trial_id, frame) VALUES (?, ?)', (trial_id, payload))
    return trial_id
