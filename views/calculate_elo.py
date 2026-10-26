import streamlit as st
import pandas as pd
import altair as alt
import numpy as np
import sqlite3 as sql

from datetime import datetime

from utility.requests import jarls_pilot_stats
from utility.methods import filter_dataframe, nunique, safe_division, unique, error, parse_match_ids
from utility.database import read_comp_data, ensure_rating_columns
from utility.blocks import metrics_block

from utility.globals import DB_NAME, RATING_BASE

COMP_DATA = read_comp_data()

def k_factor(rating1, rating2, result):
    factor = 32
    return factor

def rating_base(rating1, rating2, result):
    base = 400
    return base

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

def calculate_elo(df, conn):
    if not st.button('Calculate', width='stretch'):
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

def run_query(connection, query):
    try:
        cursor = connection.cursor()
        cursor.execute(query)
        connection.commit()
    except Exception as e:
        error(e)

def back_button():
    if st.button('< Back'):
        st.switch_page('views/admin.py')

def header():
    st.header('ELO calculation tool')

def update_columns(conn):
    # run_query(conn, "ALTER TABLE CompData DROP COLUMN PilotRating")
    # run_query(conn, "ALTER TABLE CompData DROP COLUMN RatingBase")
    # run_query(conn, "ALTER TABLE CompData DROP COLUMN RatingUncertainty")
    added = ensure_rating_columns(conn)
    if added:
        st.info(f"Added columns: {', '.join(added)}")

def historical_data(df):
    first_ten_records = df.groupby("Chassis").head(10)
    aggregated_values = first_ten_records.groupby("Chassis").agg(
        # Tonnage=('Tonnage', 'max'),
        MatchScore=('MatchScore', 'mean'),
        Kills=('Kills', 'mean'),
        KillsMostDamage=('KillsMostDamage', 'mean'),
        Assists=('Assists', 'mean'),
        ComponentsDestroyed=('ComponentsDestroyed', 'mean'),
        Damage=('Damage', 'mean'),
        Uses=('MatchID', 'count')
    ).to_dict(orient='index')

    return aggregated_values

def calculate_skill(df, conn):
    if not st.button('Calculate', width='stretch'):
        return
    
    from utility.rating import MWO_Rating_System

    mwo_rating = MWO_Rating_System()
    
    sub_table = df[['MatchID', 'Team', 'Username', 'MatchResult']].copy()
    sub_table['PilotRating'] = 0.0
    sub_table['Performance'] = 0.0
    sub_table['TeamRating'] = 0.0
    sub_table['OpponentRating'] = 0.0
    sub_table['RatingBase'] = 0.0
    sub_table['RatingUncertainty'] = 0.0

    team_counts = df.groupby(['Tournament', 'MatchID', 'TeamName'])['Username'].transform('count')
    df['TeamSize'] = team_counts.round().astype(int)

    processed_games = 0
    container = st.empty()
    for _, match in df.groupby('MatchID', sort=False):
        id = match.iloc[0]['MatchID']
        row_idx = df.index[df['MatchID'] == id][0]
        history_df = df.iloc[:row_idx]
        
        records = mwo_rating.process_match(match, history_df)
        for key, value in records.items():
            sub_table.loc[key, 'PilotRating'] = value['PilotRating']
            sub_table.loc[key, 'Performance'] = value['Performance']
            sub_table.loc[key, 'TeamRating'] = value['TeamRating']
            sub_table.loc[key, 'OpponentRating'] = value['OpponentRating']
            sub_table.loc[key, 'RatingBase'] = value['RatingBase']
            sub_table.loc[key, 'RatingUncertainty'] = value['RatingUncertainty']
        
        processed_games += 1
        if processed_games % 100 == 0:
            container.write(f"Processed games: {processed_games}")
        # return

    container.write(f"Processed games: {processed_games}, correct predictions: {mwo_rating.correct_predictions}, brackets: {mwo_rating.prediction_brackets}")

    sub_table.to_sql('temp_table', conn, if_exists='replace', index=False)

    run_query(conn, """
        UPDATE CompData
        SET
            PilotRating = temp_table.PilotRating,
            Performance = temp_table.Performance,
            TeamRating = temp_table.TeamRating,
            OpponentRating = temp_table.OpponentRating,
            RatingBase = temp_table.RatingBase,
            RatingUncertainty = temp_table.RatingUncertainty
        FROM temp_table
        WHERE
            CompData.MatchID = temp_table.MatchID
            AND CompData.Team = temp_table.Team
            AND CompData.Username = temp_table.Username
            AND CompData.MatchResult = temp_table.MatchResult
            ;
        """)

    run_query(conn, "DROP TABLE temp_table")

def check_match_stats(df, conn):
    match_ids = st.text_input('Enter match id', value=None, placeholder='Enter match ID', label_visibility='hidden')
    button_pressed = st.button('Check', width='stretch')

    if button_pressed and not match_ids:
        return
    elif button_pressed:
        id_list = parse_match_ids(match_ids)
        for id in id_list:
            calculate_rating_change(df, id)

def calculate_rating_change(df, id):
    def pilot_ratings(data, pilots):
        pilot_data = data[(data['Username'].isin(pilots))]
        last_records = pilot_data.groupby('Username').tail(1)
        
        rating_map = dict(zip(last_records['Username'], last_records['PilotRating']))
        return {pilot: rating_map.get(pilot, RATING_BASE) for pilot in pilots}

    id = int(id)

    row_idx = df.index[df['MatchID'] == id][0]
    history_df = df.iloc[:row_idx]
    match_data = df[df['MatchID'] == id]
    
    first_line = match_data.iloc[0]
    team1_rating = first_line['TeamRating']
    team2_rating = first_line['OpponentRating']
    winner = first_line['WinningTeam']
    
    unique_pilots = match_data['Username'].tolist()
    ratings = pilot_ratings(history_df, unique_pilots)

    metrics = {
        'Team 1': f"{team1_rating:.2f}",
        'Winner': winner,
        'Team 2': f"{team2_rating:.2f}",
        'History': history_df.shape[0],
        'Date': first_line['CompleteTime'].strftime("%Y-%m-%d %H:%M:%S"),
    }
    metrics_block(metrics, 5)

    teams = ["1", "2"]
    columns = st.columns(len(teams))
    for index, column in enumerate(columns):
        team_id = teams[index]
        team_data = match_data[match_data['Team'] == team_id].copy()

        pre_ratings = []

        for _, row in team_data.iterrows():
            pre_ratings.append(round(ratings.get(row['Username'], 50.0), 2))

        team_data['StartingRating'] = pre_ratings

        display_df = team_data[[
            'Username', 'Mech', 'MatchScore', 'Damage', 'Kills', 'KillsMostDamage', 'PilotRating', 'Performance', 'StartingRating'
        ]]

        with column:
            st.dataframe(
                display_df, 
                width='stretch', 
                hide_index=True
            )
        
    st.divider()

back_button()
header()

conn = sql.connect(DB_NAME)
# update_columns(conn)

calculate_skill(COMP_DATA, conn)
check_match_stats(COMP_DATA, conn)

conn.close()
