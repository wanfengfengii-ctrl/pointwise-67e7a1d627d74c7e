import sqlite3

from traces.revisions import UnknownRevision, load_revision_identity


class InvalidParentRevision(ValueError):
    pass


def resolve_parent_revision(
    connection: sqlite3.Connection, trial_id: str, parent_id: int | None,
) -> int | None:
    if parent_id is None:
        return None
    try:
        parent = load_revision_identity(connection, parent_id)
    except UnknownRevision as error:
        raise InvalidParentRevision(f'unknown parent revision {parent_id!r}') from error
    if parent.trial_id != trial_id:
        raise InvalidParentRevision(f'parent revision {parent_id} belongs to a different trial')
    return parent.revision_id
