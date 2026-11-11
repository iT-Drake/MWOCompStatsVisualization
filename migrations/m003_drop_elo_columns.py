"""
Drops the retired Elo columns from CompData.

The legacy Elo rating (`Rating`, `Rating_change`) was retired during 0.5.0: its
writer is gone, the columns are absent from COMP_DATA_TABLE_SQL, and in the live
database every value is NULL. The deletion was postponed to 0.6.0 on purpose, so
the release that replaced the rating system did not also have to drop data.

Only a database that predates the retirement still has the columns. Any value
written back then is lost here - no reader takes it and no code can regenerate
it - so `apply()` reports how many non-NULL values it discarded instead of
removing them silently.

SQLite refuses `DROP COLUMN` on a column used by an index, a view, a trigger or
a UNIQUE/PRIMARY KEY constraint. CompData has none of those, and if a database
ever does the runner stops and reports it; the fix belongs in that database,
not in this script.
"""

import migration_helpers as helpers

VERSION = 3
RELEASE = '0.6.0'
DESCRIPTION = 'drop the retired Elo columns'

# Legacy column -> nothing reads it. Order only affects the notes.
COLUMNS = ['Rating', 'Rating_change']


def is_applied(conn):
    return not any(helpers.column_exists(conn, 'CompData', column) for column in COLUMNS)


def apply(conn):
    """Returns a note per column it actually had to drop."""
    dropped = []
    for column in COLUMNS:
        if helpers.column_exists(conn, 'CompData', column):
            values = conn.execute(f'SELECT COUNT({column}) FROM CompData').fetchone()[0]
            conn.execute(f'ALTER TABLE CompData DROP COLUMN {column}')
            dropped.append(f'dropped CompData.{column} ({values} non-NULL value(s) discarded)')

    return dropped
