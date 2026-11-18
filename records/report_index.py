import sqlite3


def allocate_report_number(connection: sqlite3.Connection, body_id: int) -> int:
    cursor = connection.execute('INSERT INTO report_index(body_id) VALUES (?)', (body_id,))
    return cursor.lastrowid


def resolve_report_number(connection: sqlite3.Connection, number: int) -> int | None:
    if type(number) is not int or number <= 0:
        return None
    row = connection.execute(
        'SELECT body_id FROM report_index WHERE report_number = ?', (number,),
    ).fetchone()
    return None if row is None else row['body_id']
