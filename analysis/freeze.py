import sqlite3

from analysis.catalog import save_analysis
from analysis.evidence import build_evidence
from records.commit import atomic_write
from traces.revisions import load_online_revision


def freeze_revision(connection: sqlite3.Connection, revision_id: int) -> int:
    with atomic_write(connection):
        revision = load_online_revision(connection, revision_id)
        evidence = build_evidence(revision.loops)
        analysis_id = save_analysis(connection, revision.identity.revision_id, evidence)
    return analysis_id
