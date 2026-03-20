import streamlit as st
import pandas as pd
import altair as alt
import numpy as np
import sqlite3 as sql

from utility.requests import jarls_pilot_stats
from utility.methods import filter_dataframe, nunique, safe_division, unique, error
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
    except Exception as e:
        error(e)

def back_button():
    if st.button('< Back'):
        st.switch_page('views/admin.py')

def header():
    st.header('ELO calculation tool')

def update_columns(conn):
    # run_query(conn, "ALTER TABLE CompData ADD COLUMN Rating INTEGER")
    # run_query(conn, "ALTER TABLE CompData ADD COLUMN Rating_change INTEGER")
    # run_query(conn, "ALTER TABLE CompData DROP COLUMN PilotRating")
    # run_query(conn, "ALTER TABLE CompData DROP COLUMN RatingBase")
    # run_query(conn, "ALTER TABLE CompData DROP COLUMN RatingUncertainty")
    run_query(conn, "ALTER TABLE CompData ADD COLUMN PilotRating NUMERIC")
    run_query(conn, "ALTER TABLE CompData ADD COLUMN TeamRating NUMERIC")
    run_query(conn, "ALTER TABLE CompData ADD COLUMN OpponentRating NUMERIC")
    run_query(conn, "ALTER TABLE CompData ADD COLUMN RatingBase NUMERIC")
    run_query(conn, "ALTER TABLE CompData ADD COLUMN RatingUncertainty NUMERIC")

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
    if not st.button('Calculate', use_container_width=True):
        return
    
    from utility.rating import MWO_Rating_System

    mwo_rating = MWO_Rating_System()
    
    sub_table = df[['MatchID', 'Team', 'Username', 'MatchResult']].copy()
    sub_table['PilotRating'] = 0.0
    sub_table['TeamRating'] = 0.0
    sub_table['OpponentRating'] = 0.0
    sub_table['RatingBase'] = 0.0
    sub_table['RatingUncertainty'] = 0.0

    processed_games = 0
    container = st.empty()
    for _, match in df.groupby('MatchID', sort=False):
        records = mwo_rating.process_match(match)
        for key, value in records.items():
            sub_table.loc[key, 'PilotRating'] = value['PilotRating']
            sub_table.loc[key, 'TeamRating'] = value['TeamRating']
            sub_table.loc[key, 'OpponentRating'] = value['OpponentRating']
            sub_table.loc[key, 'RatingBase'] = value['RatingBase']
            sub_table.loc[key, 'RatingUncertainty'] = value['RatingUncertainty']
        
        processed_games += 1
        if processed_games % 100 == 0:
            container.write(f"Processed games: {processed_games}")
        # break

    container.write(f"Processed games: {processed_games}, correct predictions: {mwo_rating.correct_predictions}, brackets: {mwo_rating.prediction_brackets}")

    # ----------------------------------------------------------------------------------------------------------------------------
    # team1 = ['FCVanillaICE','Colonel  David Renard','-jbv-','TremZaLysiS','1e0n','Da Red Goes DA FASTA','Neon30','Winters Rigor']
    # team2 = ['Bacon Lord','shadowace007','AiiBa','Luminios','Sleepy Human','TheCanadianDJ','CarbonFire','GoodTry']
    # teams = [team1, team2]
    # predictions = mwo_rating.predict_result(teams)

    # st.write('Mantra vs Revenants:')
    # st.write(predictions)

    # team1 = ['Bassault','Stimraug','Monk Gyatso','Krasnopesky','Chickenman919','JP Jango','PASHA','GeeRam']
    # team2 = ['redbearin','SirEpicPwner','PinkyFeldman','Fire Ant','GLaDOSauR','Andilard','MercJ','Windscape']
    # teams = [team1, team2]
    # predictions = mwo_rating.predict_result(teams)

    # st.write('Coalition vs 228:')
    # st.write(predictions)

    # team1 = ['KIPPERS','Jiffy','MechWarrior414712','CAUTERIZER','Doobix','Cpt Leprechaun','Lizzee','Bows3r']
    # team2 = ['WhiskeyTangoFox007','Trilik','J a y','Jormangunder','snek','stoolsoftener','Way of the Ferret','CaLL Me GiL']
    # teams = [team1, team2]
    # predictions = mwo_rating.predict_result(teams)

    # st.write('V1LE vs KDCM:')
    # st.write(predictions)

    # team1 = ['KIPPERS','Jiffy','MechWarrior414712','CAUTERIZER','Doobix','Cpt Leprechaun','Lizzee','Bows3r']
    # team2 = ['Bacon Lord','shadowace007','AiiBa','Luminios','Sleepy Human','TheCanadianDJ','CarbonFire','GoodTry']
    # teams = [team1, team2]
    # predictions = mwo_rating.predict_result(teams)

    # st.write('V1LE vs Revenants:')
    # st.write(predictions)

    # ----------------------------------------------------------------------------------------------------------------------------

    sub_table.to_sql('temp_table', conn, if_exists='replace', index=False)

    run_query(conn, """
        UPDATE CompData
        SET
            PilotRating = temp_table.PilotRating,
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

back_button()
header()

conn = sql.connect(DB_NAME)
update_columns(conn)

# calculate_elo(COMP_DATA, conn)
calculate_skill(COMP_DATA, conn)
conn.close()
