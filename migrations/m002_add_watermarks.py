"""
Creates the Watermarks table.

Shipped with 0.5.0, together with the incremental rating recalculation: one row
per uploaded match that is still waiting to be replayed. The table does not
exist on a 0.4.0 database, so this is the first migration that does real work
on production.

The SQL is a copy of WATERMARKS_TABLE_SQL as it is in 0.5.0, not an import of
it - see the note in migration_helpers.py.
"""

import migration_helpers as helpers

VERSION = 2
RELEASE = '0.5.0'
DESCRIPTION = 'add the Watermarks table'

SQL = """CREATE TABLE IF NOT EXISTS Watermarks (
    MatchID INTEGER PRIMARY KEY,
    CompleteTime TEXT NOT NULL,
    AddedAt TEXT
)"""


def is_applied(conn):
    return helpers.table_exists(conn, 'Watermarks')


def apply(conn):
    conn.execute(SQL)
