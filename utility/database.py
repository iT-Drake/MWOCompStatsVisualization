import streamlit as st
import sqlite3 as sql
import pandas as pd

from os import path

from utility.globals import DB_NAME
from utility.caching import CACHE_TTL

def initialize_database():
    if not path.exists(DB_NAME):
        conn = sql.connect(DB_NAME)
        cursor = conn.cursor()

        create_table_sql = """CREATE TABLE IF NOT EXISTS CompData (
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
            Rating INTEGER,
            Rating_change INTEGER
        )"""

        cursor.execute(create_table_sql)
        conn.commit()
        conn.close()

@st.cache_data(ttl=CACHE_TTL)
def read_comp_data():
    initialize_database()

    conn = sql.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM CompData ORDER BY CompleteTime, Team, Lance, Username", conn, index_col='ID')
    conn.close()

    return df

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
