"""
Schema checks used by the migration scripts.

Kept separate from utility/database.py on purpose: a migration has to describe
the schema as it was on its release, so it must not follow code that keeps
evolving.
"""


def table_exists(conn, table):
    """True when the table is present in the database."""
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()

    return row is not None


def column_names(conn, table):
    """Column names of the table, in the order they are stored."""
    return [row[1] for row in conn.execute(f'PRAGMA table_info({table})')]


def column_exists(conn, table, column):
    """True when the table has the column."""
    return column in column_names(conn, table)
