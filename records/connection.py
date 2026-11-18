import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from os import PathLike


@contextmanager
def open_database(path: str | PathLike[str]) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(path, isolation_level=None)
    try:
        connection.row_factory = sqlite3.Row
        connection.execute('PRAGMA foreign_keys = ON')
        yield connection
    finally:
        connection.close()
