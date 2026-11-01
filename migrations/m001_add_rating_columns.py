"""
Adds the six columns the openskill rating system stores per row.

The rating feature was released with the project on 0.4.0, so this migration
records a schema that production already has. On an older database it adds the
missing columns one by one: a database can have some of them and not the
others, and a partial set is worse than none, because the reader would then
mix stored and NULL ratings.
"""

import migration_helpers as helpers

VERSION = 1
RELEASE = '0.4.0'
DESCRIPTION = 'add the rating columns'

# Column order matches utility/database.py::RATING_COLUMNS.
COLUMNS = ['PilotRating', 'Performance', 'TeamRating', 'OpponentRating', 'RatingBase', 'RatingUncertainty']


def is_applied(conn):
    return all(helpers.column_exists(conn, 'CompData', column) for column in COLUMNS)


def apply(conn):
    """Returns a note per column it actually had to add."""
    added = []
    for column in COLUMNS:
        if not helpers.column_exists(conn, 'CompData', column):
            conn.execute(f'ALTER TABLE CompData ADD COLUMN {column} NUMERIC')
            added.append(f'added CompData.{column}')

    return added
