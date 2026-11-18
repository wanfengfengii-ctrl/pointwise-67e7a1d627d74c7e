import sqlite3
from dataclasses import dataclass

from analysis.evidence import FrozenEvidence, decode_evidence, encode_evidence


class UnknownAnalysis(LookupError):
    pass


@dataclass(frozen=True, slots=True)
class FrozenAnalysis:
    analysis_id: int
    revision_id: int
    evidence: FrozenEvidence


def save_analysis(connection: sqlite3.Connection, revision_id: int, evidence: FrozenEvidence) -> int:
    cursor = connection.execute(
        'INSERT INTO frozen_analysis(revision_id, evidence) VALUES (?, ?)',
        (revision_id, encode_evidence(evidence)),
    )
    return cursor.lastrowid


def get_analysis(connection: sqlite3.Connection, analysis_id: int) -> FrozenAnalysis:
    if type(analysis_id) is not int or analysis_id <= 0:
        raise UnknownAnalysis(analysis_id)
    row = connection.execute(
        'SELECT analysis_id, revision_id, evidence FROM frozen_analysis WHERE analysis_id = ?',
        (analysis_id,),
    ).fetchone()
    if row is None:
        raise UnknownAnalysis(analysis_id)
    return FrozenAnalysis(row['analysis_id'], row['revision_id'], decode_evidence(row['evidence']))
