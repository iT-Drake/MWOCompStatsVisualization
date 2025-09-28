import streamlit as st
import pandas as pd
import altair as alt
import numpy as np
import sqlite3 as sql

from utility.requests import jarls_pilot_stats
from utility.methods import filter_dataframe, nunique, safe_division, unique
from utility.database import read_comp_data
from utility.blocks import metrics_block

from utility.globals import DB_NAME

COMP_DATA = read_comp_data()
RATING_BASE = 400
K_FACTOR = 32

def k_factor(rating1, rating2, result):
    return K_FACTOR

def rating_base(rating1, rating2, result):
    return RATING_BASE

def elo_rating_change(rating1, rating2, side1_result):
    if side1_result == 'WIN':
        rating_difference = rating2 - rating1
        sign = 1
    else:
        rating_difference = rating1 - rating2
        sign = -1

    exponent = rating_difference / rating_base(rating1, rating2, side1_result)
    result = 1 / (1 + 10 ** exponent)
    return sign * round(k_factor(rating1, rating2, side1_result) * (1 - result), 0)

def run_query(connection, query):
    try:
        cursor = connection.cursor()
        cursor.execute(query)
        connection.commit()
    except:
         pass

def back_button():
    if st.button('< Back'):
        st.switch_page('views/admin.py')

def header():
    st.header('ELO calculation tool')

def update_columns(conn):
    run_query(conn, "ALTER TABLE CompData ADD COLUMN Rating INTEGER")
    run_query(conn, "ALTER TABLE CompData ADD COLUMN Rating_change INTEGER")


def calculate_elo(df, conn):
    if not st.button('Calculate', use_container_width=True):
        return

    pilots = unique(df, 'Username')
    elo = {pilot: 1500 for pilot in pilots.tolist()}

    sub_table = df[['MatchID', 'Team', 'Username', 'MatchResult']].copy()
    sub_table['Rating'] = 0
    sub_table['Rating_change'] = 0

    processed_games = 0
    container = st.empty()
    for _, game_group in sub_table.groupby('MatchID', sort=False):
        team_elos = game_group.groupby('Team')['Username'].apply(
            lambda x: sum(elo[p] for p in x) // len(x)
        )
        
        for _, match in game_group.groupby('Team'):
            team_result = match['MatchResult'].iloc[0]
            for index, row in match.iterrows():
                player = row['Username']
                
                opponent_team = '2' if row['Team'] == '1' else '1'
                opponent_team_elo = int(team_elos[opponent_team])
                
                elo_change = elo_rating_change(elo[player], opponent_team_elo, team_result)
                new_elo = elo[player] + elo_change
                elo[player] = new_elo

                sub_table.loc[index, 'Rating'] = new_elo
                sub_table.loc[index, 'Rating_change'] = elo_change

        processed_games += 1
        if processed_games % 100 == 0:
            container.write(f"Processed games: {processed_games}")

    sub_table.to_sql('temp_table', conn, if_exists='replace', index=False)

    run_query(conn, """
        UPDATE CompData
        SET
            Rating = temp_table.Rating,
            Rating_change = temp_table.Rating_change
        FROM temp_table
        WHERE
            CompData.MatchID = temp_table.MatchID
            AND CompData.Team = temp_table.Team
            AND CompData.Username = temp_table.Username
            AND CompData.MatchResult = temp_table.MatchResult
            ;
        """)

    run_query(conn, "DROP TABLE temp_table")

back_button()
header()

conn = sql.connect(DB_NAME)
update_columns(conn)

calculate_elo(COMP_DATA, conn)
conn.close()
