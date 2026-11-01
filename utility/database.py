import streamlit as st
import sqlite3 as sql
import pandas as pd

from os import path
from datetime import datetime, timezone

from utility.globals import DB_NAME
from utility.caching import CACHE_TTL
from utility.methods import error

COMP_DATA_TABLE_SQL = """CREATE TABLE IF NOT EXISTS CompData (
    ID INTEGER PRIMARY KEY,
    MatchID INTEGER,
    Tournament TEXT,
    Division TEXT,
    Map TEXT,
    WinningTeam TEXT,
    Team1Score INTEGER,
    Team2Score INTEGER,
    MatchDuration TEXT,
    CompleteTime TEXT,
    MatchResult TEXT,
    Score INTEGER,
    Username TEXT,
    Team TEXT,
    TeamName TEXT,
    Lance TEXT,
    MechItemID INTEGER,
    Mech TEXT,
    Chassis TEXT,
    Tonnage INTEGER,
    Class TEXT,
    Type TEXT,
    HealthPercentage INTEGER,
    Kills INTEGER,
    KillsMostDamage INTEGER,
    Assists INTEGER,
    ComponentsDestroyed INTEGER,
    MatchScore INTEGER,
    Damage INTEGER,
    TeamDamage INTEGER,
    PilotRating NUMERIC,
    Performance NUMERIC,
    TeamRating NUMERIC,
    OpponentRating NUMERIC,
    RatingBase NUMERIC,
    RatingUncertainty NUMERIC
)"""

WATERMARKS_TABLE_SQL = """CREATE TABLE IF NOT EXISTS Watermarks (
    MatchID INTEGER PRIMARY KEY,
    CompleteTime TEXT NOT NULL,
    AddedAt TEXT
)"""

RATING_COLUMNS = ['PilotRating', 'Performance', 'TeamRating', 'OpponentRating', 'RatingBase', 'RatingUncertainty']

#---------------------------------------------------------------------
# INITIALIZATION
#---------------------------------------------------------------------

def database_exists():
    """True when the database file is already on disk."""
    return path.exists(DB_NAME)


def table_exists(conn, table):
    """True when the given table is present in the database."""
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()

    return row is not None


def column_names(conn, table):
    """Column names of the given table."""
    return [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]


def create_comp_data_table(conn):
    conn.execute(COMP_DATA_TABLE_SQL)
    conn.commit()


def create_watermarks_table(conn):
    conn.execute(WATERMARKS_TABLE_SQL)
    conn.commit()


def ensure_rating_columns(conn):
    """
    Adds the current rating columns to CompData when they are missing.

    Idempotent, so it can run on every startup. Returns the columns it added.
    """
    existing = column_names(conn, 'CompData')
    added = []

    for column in RATING_COLUMNS:
        if column in existing:
            continue
        try:
            conn.execute(f"ALTER TABLE CompData ADD COLUMN {column} NUMERIC")
            added.append(column)
        except sql.OperationalError:
            # Added concurrently by another session
            pass

    if added:
        conn.commit()

    return added


def initialize_database():
    """
    Makes sure the database file, the CompData table and the Watermarks table exist.

    Safe to call on every startup: existing tables and columns are left alone.
    """
    if not database_exists():
        conn = sql.connect(DB_NAME)
        create_comp_data_table(conn)
        create_watermarks_table(conn)
        conn.close()
        return

    conn = sql.connect(DB_NAME)

    if not table_exists(conn, 'CompData'):
        create_comp_data_table(conn)
    else:
        ensure_rating_columns(conn)

    if not table_exists(conn, 'Watermarks'):
        create_watermarks_table(conn)

    conn.close()

#---------------------------------------------------------------------
# READING
#---------------------------------------------------------------------

def fetch_comp_data():
    """
    Reads CompData without caching.

    Anything that writes ratings has to use this. read_comp_data() may return
    data that predates the rows that were just uploaded.
    """
    initialize_database()

    conn = sql.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM CompData ORDER BY CompleteTime, Team, Lance, Username", conn, index_col='ID', parse_dates=['CompleteTime']).reset_index()
    conn.close()

    return df

@st.cache_data(ttl=CACHE_TTL)
def read_comp_data():
    return fetch_comp_data()

#---------------------------------------------------------------------
# WRITING
#---------------------------------------------------------------------

def unique_match_ids():
    conn = sql.connect(DB_NAME)
    cursor = conn.cursor()
    unique_ids = [row[0] for row in cursor.execute("SELECT DISTINCT MatchID FROM CompData")]
    conn.close()

    return unique_ids

def write_comp_data(df):
    conn = sql.connect(DB_NAME)
    if df.shape[0] > 0:
        df.to_sql('CompData', conn, if_exists='append', index=False)
    conn.close()

def update_values(column, old_value, new_value):
    initialize_database()

    conn = sql.connect(DB_NAME)
    update_statement = f'UPDATE CompData SET {column} = ? WHERE {column} = ?'
    cursor = conn.cursor()

    result = ''
    try:
        cursor.execute(update_statement, (new_value, old_value))
        conn.commit()
    except sql.Error as e:
        result = e.message

    conn.close()
    return result

#---------------------------------------------------------------------
# EXECUTING
#---------------------------------------------------------------------

def run_query(connection, query, parameters = ()):
    """
    Executes query on opened connection.

    Args:
        parameters: empty tuple for a query without bindings. It must not be None -
            sqlite3 raises "parameters are of unsupported type" for None, and because
            this function reports failures instead of raising, the query would silently
            not run.
    """
    try:
        cursor = connection.cursor()
        cursor.execute(query, parameters)
        connection.commit()
    except Exception as e:
        error(e)

#---------------------------------------------------------------------
# WATERMARKS
#---------------------------------------------------------------------

def write_watermark(match_id, complete_time):
    """
    Marks an uploaded match as waiting for a rating recalculation.

    Written per match, so an interrupted upload still leaves a marker behind.
    """
    initialize_database()

    conn = sql.connect(DB_NAME)
    conn.execute(
        "INSERT OR IGNORE INTO Watermarks (MatchID, CompleteTime, AddedAt) VALUES (?, ?, ?)",
        (int(match_id), complete_time, datetime.now(timezone.utc).isoformat())
    )
    conn.commit()
    conn.close()

def read_watermarks():
    """Uploaded matches waiting for a recalculation, oldest first."""
    initialize_database()

    conn = sql.connect(DB_NAME)
    rows = conn.execute("SELECT MatchID, CompleteTime FROM Watermarks ORDER BY CompleteTime").fetchall()
    conn.close()

    return rows

def clear_watermarks(match_ids):
    """Removes the given matches from the pending list."""
    if not match_ids:
        return

    initialize_database()

    conn = sql.connect(DB_NAME)
    conn.executemany("DELETE FROM Watermarks WHERE MatchID = ?", [(int(match_id),) for match_id in match_ids])
    conn.commit()
    conn.close()
