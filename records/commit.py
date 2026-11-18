import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager


@contextmanager
def atomic_write(connection: sqlite3.Connection) -> Iterator[None]:
    connection.execute('BEGIN IMMEDIATE')
    try:
        yield
        connection.commit()
    except BaseException:
        if connection.in_transaction:
            connection.rollback()
        raise
