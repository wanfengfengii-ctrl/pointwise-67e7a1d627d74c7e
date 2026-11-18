from os import PathLike

from records.commit import atomic_write
from records.connection import open_database


_SCHEMA = (
    '''CREATE TABLE IF NOT EXISTS trial (
           trial_id TEXT PRIMARY KEY NOT NULL,
           frame TEXT NOT NULL
       )''',
    '''CREATE TABLE IF NOT EXISTS trace_revision (
           revision_id INTEGER PRIMARY KEY,
           trial_id TEXT NOT NULL REFERENCES trial(trial_id),
           parent_id INTEGER REFERENCES trace_revision(revision_id),
           archived INTEGER NOT NULL DEFAULT 0 CHECK (archived IN (0, 1))
       )''',
    '''CREATE TABLE IF NOT EXISTS online_traces (
           revision_id INTEGER PRIMARY KEY REFERENCES trace_revision(revision_id),
           payload TEXT NOT NULL
       )''',
    '''CREATE TABLE IF NOT EXISTS archived_traces (
           revision_id INTEGER PRIMARY KEY REFERENCES trace_revision(revision_id),
           payload TEXT NOT NULL
       )''',
    '''CREATE TABLE IF NOT EXISTS frozen_analysis (
           analysis_id INTEGER PRIMARY KEY,
           revision_id INTEGER NOT NULL REFERENCES trace_revision(revision_id),
           evidence TEXT NOT NULL,
           UNIQUE (analysis_id, revision_id)
       )''',
    '''CREATE TABLE IF NOT EXISTS inspection_report (
           body_id INTEGER PRIMARY KEY,
           analysis_id INTEGER NOT NULL,
           revision_id INTEGER NOT NULL,
           payload TEXT NOT NULL,
           FOREIGN KEY (analysis_id, revision_id) REFERENCES frozen_analysis(analysis_id, revision_id)
       )''',
    '''CREATE TABLE IF NOT EXISTS report_index (
           report_number INTEGER PRIMARY KEY,
           body_id INTEGER NOT NULL UNIQUE REFERENCES inspection_report(body_id)
       )''',
)


def initialize_database(path: str | PathLike[str]) -> None:
    with open_database(path) as connection, atomic_write(connection):
        for statement in _SCHEMA:
            connection.execute(statement)
