import sqlite3
from dataclasses import replace

from records.commit import atomic_write
from traces.revisions import RevisionIdentity, load_revision_identity


def archive_revision(connection: sqlite3.Connection, revision_id: int) -> RevisionIdentity:
    with atomic_write(connection):
        identity = load_revision_identity(connection, revision_id)
        if identity.archived:
            return identity
        moved = connection.execute(
            '''INSERT INTO archived_traces(revision_id, payload)
               SELECT revision_id, payload FROM online_traces WHERE revision_id = ?''',
            (revision_id,),
        )
        if moved.rowcount != 1:
            raise sqlite3.IntegrityError(f'online traces are missing for revision {revision_id}')
        connection.execute('DELETE FROM online_traces WHERE revision_id = ?', (revision_id,))
        connection.execute('UPDATE trace_revision SET archived = 1 WHERE revision_id = ?', (revision_id,))
    return replace(identity, archived=True)
