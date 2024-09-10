import requests
import sqlite3 as sql

import pandas as pd
import streamlit as st
import altair as alt

from time import sleep
from os import path, getenv
from dotenv import load_dotenv

##-------------------------------------------------------------------------------------------
## UTILITY METHODS
##-------------------------------------------------------------------------------------------

def write_error(message):
    st.sidebar.error(message, icon=':material/error:')

def convert_to_int(value):
    formatted_value = value.replace(',', '').strip()
    try:
        return int(formatted_value)
    except ValueError as e:
        write_error(f'Incorrect match id: {value}')
        return ''

##-------------------------------------------------------------------------------------------
## DATA SOURCES
##-------------------------------------------------------------------------------------------

@st.cache_data(ttl=180)
def mech_data(url):
    try:
        df = pd.read_csv(url, index_col=0)
        zipped_data = zip(df['ItemID'], df['Name'], df['Chassis'], df['Tonnage'], df['Class'], df['Type'])
        result = {item[0]:{'Mech': item[1], 'Chassis': item[2], 'Tonnage': item[3], 'Class': item[4], 'Type': item[5]} for item in zipped_data}
    except Exception as e:
        write_error(f"An error occurred while fetching mech data:\n{e}")
        result = {}
    
    return result

@st.cache_data(ttl=180)
def team_rosters(url):
    try:
        df = pd.read_csv(url, index_col=0)
        result = {item[0]: item[1] for item in zip(df['Pilot'], df['Team'])}
    except Exception as e:
        write_error(f"An error occurred while fetching team rosters:\n{e}")
        result = {}
    
    return result

##-------------------------------------------------------------------------------------------
## DATABASE
##-------------------------------------------------------------------------------------------

def initialize_database(db_name):
    if not path.exists(db_name):
        conn = sql.connect(db_name)
        cursor = conn.cursor()

        create_table_sql = """CREATE TABLE IF NOT EXISTS CompData (
            ID INTEGER PRIMARY KEY,
            MatchID INTEGER,
            Map TEXT,
            WinningTeam TEXT,
            Team1Score INTEGER,
            Team2Score INTEGER,
            MatchDuration TEXT,
            CompleteTime TEXT,
            MatchResult TEXT,
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
            TeamDamage INTEGER
        )"""

        cursor.execute(create_table_sql)
        conn.commit()
        conn.close()

@st.cache_data(ttl=60)
def read_comp_data(db_name):
    initialize_database(db_name)

    conn = sql.connect(db_name)
    df = pd.read_sql_query("SELECT * FROM CompData", conn, index_col='ID')
    conn.close()

    return df

##-------------------------------------------------------------------------------------------
## API REQUEST
##-------------------------------------------------------------------------------------------

def match_data_columns():
    return ['MatchID', 'Map', 'WinningTeam', 'Team1Score', 'Team2Score', 'MatchDuration', 'CompleteTime', 'MatchResult',
        'Username', 'Team', 'TeamName', 'Lance', 'MechItemID', 'Mech', 'Chassis', 'Tonnage', 'Class', 'Type',
        'HealthPercentage', 'Kills', 'KillsMostDamage', 'Assists', 'ComponentsDestroyed', 'MatchScore', 'Damage', 'TeamDamage']

def match_data(id, match_details, user_details):
    lines = []
    mechs = mech_data(MECH_DATA_URL)
    rosters = team_rosters(ROSTERS_URL)
    for line in user_details:
        if line['IsSpectator'] == True:
            continue

        mech_id = line['MechItemID']
        pilot = line['Username']
        if mech_id not in mechs:
            raise Exception(f'Mech with id={mech_id} not found')
        if pilot not in rosters:
            raise Exception(f'Pilot {pilot} not found in the rosters')
        mech = mechs[mech_id]
        team = rosters[pilot]

        new_line = {}
        new_line['MatchID'] = id
        new_line['Map'] = match_details['Map']
        new_line['WinningTeam'] = match_details['WinningTeam']
        new_line['Team1Score'] = match_details['Team1Score']
        new_line['Team2Score'] = match_details['Team2Score']
        new_line['MatchDuration'] = match_details['MatchDuration']
        new_line['CompleteTime'] = match_details['CompleteTime']
        new_line['MatchResult'] = 'WIN' if line['Team'] == match_details['WinningTeam'] else 'LOSS'
        new_line['Username'] = pilot
        new_line['Team'] = line['Team']
        new_line['TeamName'] = team
        new_line['Lance'] = line['Lance']
        new_line['MechItemID'] = mech_id
        new_line['Mech'] = mech['Mech']
        new_line['Chassis'] = mech['Chassis']
        new_line['Tonnage'] = mech['Tonnage']
        new_line['Class'] = mech['Class']
        new_line['Type'] = mech['Type']
        new_line['HealthPercentage'] = line['HealthPercentage']
        new_line['Kills'] = line['Kills']
        new_line['KillsMostDamage'] = line['KillsMostDamage']
        new_line['Assists'] = line['Assists']
        new_line['ComponentsDestroyed'] = line['ComponentsDestroyed']
        new_line['MatchScore'] = line['MatchScore']
        new_line['Damage'] = line['Damage']
        new_line['TeamDamage'] = line['TeamDamage']
        lines.append(new_line)
    
    return lines

def request_match_data(match_id, api_url):
    url = api_url.replace('%1', match_id)
    response = requests.get(url)
    if response.status_code == 200:
        try:
            json_data = response.json()
            match_details = json_data['MatchDetails']
            user_details = json_data['UserDetails']
            data = match_data(match_id, match_details, user_details)
            df = pd.DataFrame(data)
            df.columns = match_data_columns()
        except requests.exceptions.JSONDecodeError as e:
            write_error(f"Error fetching id={match_id}:\n{e}")
        except Exception as e:
            write_error(f"Error fetching id={match_id}:\n{e}")
    else:
        write_error(f"Error fetching id={match_id}:\nCode={response.status_code},Text={response.text}")
        df = pd.DataFrame(match_data_columns())

    return df

def batch_request(match_ids, api_url, db_name):
    conn = sql.connect(db_name)
    cursor = conn.cursor()
    unique_ids = [row[0] for row in cursor.execute("SELECT DISTINCT MatchID FROM CompData")]

    for match_id in match_ids:
        id = convert_to_int(match_id)
        if not id or id in unique_ids:
            continue

        df = request_match_data(match_id, api_url)
        df.to_sql('CompData', conn, if_exists='append', index=False)

        # API calls limited by 60 per minute
        sleep(1)

    conn.close()

##-------------------------------------------------------------------------------------------
## MAIN CONTENT
##-------------------------------------------------------------------------------------------

def sidebar(df):
    options = {}

    teams = df['TeamName'].unique()
    team = st.sidebar.selectbox('Select a team', teams, index=None, placeholder='Select a team', label_visibility='hidden')
    if team:
        team_data = df[df['TeamName'] == team]
        players = team_data['Username'].unique()
    else:
        players = df['Username'].unique()

    player = st.sidebar.selectbox('Select a pilot', players, index=None, placeholder='Select a pilot', label_visibility='hidden')

    # maps = df['Map'].unique()
    # map = st.sidebar.selectbox('Select a map', maps, index=None, placeholder='Select a map', label_visibility='hidden')

    form = st.sidebar.form("data_fetching", clear_on_submit=True)
    text_area = form.text_area('Get API data for provided IDs:', placeholder='List of Match IDs', key='match_ids')
    match_ids = text_area.strip().splitlines() if text_area else []
    form.form_submit_button('Submit', use_container_width=True)

    csv = df.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button(
        label="Download data as CSV",
        data=csv,
        file_name="data_dump.csv",
        mime='text/csv',
        use_container_width=True
    )

    options['team'] = team
    options['player'] = player
    options['match_ids'] = match_ids
    # options['map'] = map

    return options

def general_statistics(df):
    games_played = df['MatchID'].nunique()
    teams_number = df['TeamName'].nunique()
    mechs_killed = df['Kills'].sum()
    components_destroyed = df['ComponentsDestroyed'].sum()
    team_damage = df['TeamDamage'].sum()

    top_mechs = df['Mech'].value_counts().sort_values(ascending=False).head(10).reset_index()

    light_mechs_data = df[df['Class'] == 'LIGHT']
    top_light_mechs = light_mechs_data['Mech'].value_counts().sort_values(ascending=False).head(5).reset_index()

    medium_mechs_data = df[df['Class'] == 'MEDIUM']
    top_medium_mechs = medium_mechs_data['Mech'].value_counts().sort_values(ascending=False).head(5).reset_index()

    heavy_mechs_data = df[df['Class'] == 'HEAVY']
    top_heavy_mechs = heavy_mechs_data['Mech'].value_counts().sort_values(ascending=False).head(5).reset_index()

    assault_mechs_data = df[df['Class'] == 'ASSAULT']
    top_assault_mechs = assault_mechs_data['Mech'].value_counts().sort_values(ascending=False).head(5).reset_index()

    left_column, right_column = st.columns(2, gap='medium')

    # left_column
    left_column.subheader(f'Teams number: {teams_number}')
    left_column.subheader(f'Games played: {games_played}')
    left_column.subheader(f'Mechs killed: {mechs_killed}')
    left_column.subheader(f'Components destroyed: {components_destroyed}')
    left_column.subheader(f'Team damage dealt: {team_damage}')

    # right_column
    right_column.altair_chart(alt.Chart(top_mechs, title='Most used mechs').mark_bar().encode(
        x=alt.X('Mech', sort=None, axis=alt.Axis(labelAngle=-45)),
        y=alt.Y('count', title='Uses')
    ), use_container_width=True)

    st.divider()

    left_column, right_column = st.columns(2, gap='medium')

    # left_column
    left_column.altair_chart(alt.Chart(top_light_mechs, title='Most used light mechs').mark_bar().encode(
        x=alt.X('Mech', sort=None, axis=alt.Axis(labelAngle=-45)),
        y=alt.Y('count', title='Uses')
    ), use_container_width=True)

    left_column.altair_chart(alt.Chart(top_heavy_mechs, title='Most used heavy mechs').mark_bar().encode(
        x=alt.X('Mech', sort=None, axis=alt.Axis(labelAngle=-45)),
        y=alt.Y('count', title='Uses')
    ), use_container_width=True)

    # right_column
    right_column.altair_chart(alt.Chart(top_medium_mechs, title='Most used medium mechs').mark_bar().encode(
        x=alt.X('Mech', sort=None, axis=alt.Axis(labelAngle=-45)),
        y=alt.Y('count', title='Uses')
    ), use_container_width=True)

    right_column.altair_chart(alt.Chart(top_assault_mechs, title='Most used assault mechs').mark_bar().encode(
        x=alt.X('Mech', sort=None, axis=alt.Axis(labelAngle=-45)),
        y=alt.Y('count', title='Uses')
    ), use_container_width=True)

def team_statistics(df, team):
    team_data = df[df['TeamName'] == team]
    if team_data.shape[0] == 0:
        write_error(f'Data not found for team: {team}')
        return
    
    total_games = team_data.shape[0]
    wins = team_data[team_data['MatchResult'] == 'WIN'].shape[0]
    win_loss_ratio = wins / total_games

    avg_kills = team_data['Kills'].mean()
    avg_damage = team_data['Damage'].mean()

    class_distribution = team_data.groupby('Class')['Class'].value_counts().sort_values(ascending=False).reset_index()
    top_mechs = team_data['Mech'].value_counts().sort_values(ascending=False).head(10).reset_index()
    
    st.subheader(f'Team: {team}')
    st.subheader(f'Games played: {total_games}')
    st.subheader(f'Win/Loss ratio: {win_loss_ratio:.2f}')
    st.subheader(f'Avg. kills per drop: {avg_kills:.2f}')
    st.subheader(f'Avg. damage per drop: {avg_damage:.2f}')

    st.divider()

    left_column, right_column = st.columns(2, gap='medium')

    left_column.altair_chart(alt.Chart(class_distribution, title='Weight class distribution').mark_bar().encode(
        x=alt.X('Class', sort=None),
        y=alt.Y('count', title='Uses')
    ), use_container_width=True)

    right_column.altair_chart(alt.Chart(top_mechs, title='Most used mechs').mark_bar().encode(
        x=alt.X('Mech', sort=None, axis=alt.Axis(labelAngle=-45)),
        y=alt.Y('count', title='Uses')
    ), use_container_width=True)

def player_statistics(df, player):
    player_data = df[df['Username'] == player]
    if player_data.shape[0] == 0:
        write_error(f'Data not found for player: {player}')
        return
    
    total_games = player_data.shape[0]
    wins = player_data[player_data['MatchResult'] == 'WIN'].shape[0]
    win_loss_ratio = wins / total_games

    kills = player_data['Kills'].sum()
    kmdds = player_data['KillsMostDamage'].sum()
    assists = player_data['Assists'].sum()
    deaths = player_data[player_data['HealthPercentage'] == 0].shape[0]
    kills_deaths_ratio = kills / deaths if deaths > 0 else kills

    avg_damage = player_data['Damage'].mean()
    total_damage = player_data['Damage'].sum()

    top_mechs = player_data['Mech'].value_counts().sort_values(ascending=False).head(3).reset_index()
    avg_damage_per_mech = player_data.groupby('Mech')['Damage'].mean()
    win_loss_per_mech = player_data.groupby('Mech')['MatchResult'].apply(lambda x: x.value_counts().get('WIN', 0) / x.value_counts().get('LOSS', 1))
    kills_to_deaths_per_mech = player_data.groupby('Mech').apply(lambda x: (x['Kills'].sum() / x['HealthPercentage'].eq(0).sum()) if x['HealthPercentage'].eq(0).sum() > 0 else x['Kills'].sum())

    mech_stats = top_mechs.copy().rename(columns={'count': 'Uses'})
    mech_stats['Avg Dmg'] = mech_stats['Mech'].map(avg_damage_per_mech)
    mech_stats['W/L'] = mech_stats['Mech'].map(win_loss_per_mech)
    mech_stats['K/D'] = mech_stats['Mech'].map(kills_to_deaths_per_mech)

    left_column, right_column = st.columns(2, gap='medium')

    left_column.subheader(f'Player: {player}')
    left_column.subheader(f'Games played: {total_games}')
    left_column.subheader(f'Win/Loss ratio: {win_loss_ratio:.2f}')
    left_column.subheader(f'Kills/Deaths ratio: {kills_deaths_ratio:.2f}')
    
    right_column.subheader(f'Kills: {kills}')
    right_column.subheader(f'KMDDs: {kmdds}')
    right_column.subheader(f'Assists: {assists}')
    right_column.subheader(f'Damage (avg./total): {avg_damage:.2f} / {total_damage}')

    st.divider()

    st.dataframe(mech_stats, hide_index=True, use_container_width=True)

def map_statistics(df, map_name):
    pass

##-------------------------------------------------------------------------------------------
## INITIALIZATION
##-------------------------------------------------------------------------------------------

load_dotenv()
DB_NAME = getenv("DB_NAME")
API_KEY = getenv("API_KEY")
API_URL = getenv("API_URL")
MECH_DATA_URL = getenv("MECH_DATA_URL")
ROSTERS_URL = getenv("ROSTERS_URL")
APP_TITLE = getenv("APP_TITLE")
API_URL = API_URL.replace('%2', API_KEY)

st.logo('Logo.png', icon_image='Logo.png')
st.set_page_config(page_title="Stats Tool", layout='wide')
st.title(APP_TITLE)

df = read_comp_data(DB_NAME)
options = sidebar(df)

if options['match_ids']:
    batch_request(options['match_ids'], API_URL, DB_NAME)

if not options['team'] and not options['player']:
    general_statistics(df)
elif options['player']:
    player_statistics(df, options['player'])
elif options['team']:
    team_statistics(df, options['team'])
