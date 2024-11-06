import requests
import sqlite3 as sql

import pandas as pd
import numpy as np
import streamlit as st
import altair as alt

from time import sleep
from os import path, getenv
from dotenv import load_dotenv

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
TOURNAMENT = getenv("TOURNAMENT")
API_URL = API_URL.replace('%2', API_KEY)

CHART_LABELS_ANGLE = 0

##-------------------------------------------------------------------------------------------
## SETTINGS
##-------------------------------------------------------------------------------------------

def set_chart_labels_angle(draw_horizontally=True):
    global CHART_LABELS_ANGLE
    CHART_LABELS_ANGLE = 0 if draw_horizontally else -90

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

def safe_division(dividend, divisor):
    return dividend / divisor if divisor != 0 else dividend

##-------------------------------------------------------------------------------------------
## CHARTS
##-------------------------------------------------------------------------------------------

def bar_chart(df, title, x_axis, y_axis, style='main'):
    if style == 'alternate':
        return bar_chart_alternate(df, title, x_axis, y_axis)
    elif style == 'team2':
        return bar_chart_team2(df, title, x_axis, y_axis)
    else:
        return bar_chart_main(df, title, x_axis, y_axis)

def bar_chart_main(df, title, x_axis, y_axis):
    return alt.Chart(df, title=title).mark_bar().encode(
        x=alt.X(f'{x_axis}:O', sort=None, axis=alt.Axis(labelAngle=CHART_LABELS_ANGLE), title=None),
        y=alt.Y(y_axis, title=None))

def bar_chart_alternate(df, title, x_axis, y_axis):
    return alt.Chart(df, title=title).mark_bar().encode(
        x=alt.X(x_axis, sort=None, axis=alt.Axis(labelAngle=CHART_LABELS_ANGLE), title=None),
        y=alt.Y(y_axis, title=None)
    ).configure_bar(
        color='yellowgreen',
        opacity=0.8
    )

def bar_chart_team2(df, title, x_axis, y_axis):
    return alt.Chart(df, title=title).mark_bar().encode(
        x=alt.X(x_axis, sort=None, axis=alt.Axis(labelAngle=CHART_LABELS_ANGLE), title=None),
        y=alt.Y(y_axis, title=None)
    ).configure_bar(
        color='orangered',
        opacity=0.8
    )

def stacked_bar_chart(df, title, x_axis, y_axis, color):
    return alt.Chart(df, title=title).mark_bar().encode(
        x=alt.X(f'{x_axis}:N', sort=alt.EncodingSortField(field=y_axis, op='sum', order='descending'), axis=alt.Axis(labelAngle=CHART_LABELS_ANGLE), title=None),
        y=alt.Y(f'{y_axis}:Q', title=None),
        color=alt.Color(f'{color}:N', legend=alt.Legend(title=color), scale=alt.Scale(domain=['1', '2'], range=['lightskyblue', 'orangered'])),
        tooltip=[
            alt.Tooltip(f'{color}:N', title=color),
            alt.Tooltip(f'{y_axis}:Q', title=y_axis)
        ]
    )

def negative_stacked_bar_chart_mech_usage(df):
    base = alt.Chart(df, title='Mech usage by tonnage').mark_bar().encode(
        x=alt.X('Tonnage:N', title=None, sort=None, axis=alt.Axis(labelAngle=CHART_LABELS_ANGLE)),
        y=alt.Y('Positive:Q', title=None, stack='zero'),
        y2=alt.Y2('Negative:Q'),
        tooltip=[
            alt.Tooltip('Result:N', title="Result"),
            alt.Tooltip('count:Q', title="Uses")
        ]
    )
    bars = base.mark_bar().encode(
        color=alt.Color('Result', scale=alt.Scale(domain=['WIN', 'LOSS']))
    )
    return bars

def horizontal_bar_chart_match_duration(df):
    return alt.Chart(df, title='Average match duration (min)').mark_bar().encode(
        x=alt.X('Duration:Q', title=None),
        y=alt.Y('Team:N', title=None, sort=None),
        tooltip=['Team', alt.Tooltip('Duration:Q', format='.2f')]
    )

def negative_horizontal_stacked_bar_chart_map_stats(df, title):
    upper_bound = df['Positive'].max()
    lower_bound = df['Negative'].min()
    ticks = int(upper_bound - lower_bound)

    base = alt.Chart(df, title=title).mark_bar().encode(
        x=alt.X('Positive:Q', title=None, stack='zero', sort=None).axis(tickCount=ticks),
        y=alt.Y('Map:N', title=None, sort=None),
        x2=alt.X2('Negative:Q'),
        tooltip=[
            alt.Tooltip('Result:N', title="Result"),
            alt.Tooltip('count:Q', title="Count")
        ]
    )
    bars = base.mark_bar().encode(
        color=alt.Color('Result', scale=alt.Scale(domain=['WIN', 'LOSS']))
    )
    return bars

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
        zipped_data = zip(df['Pilot'].str.upper(), df['Team'])
        result = {item[0]: item[1] for item in zipped_data}
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
            Tournament TEXT,
            Division TEXT,
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
    df = pd.read_sql_query("SELECT * FROM CompData ORDER BY CompleteTime, Team, Lance, Username", conn, index_col='ID')
    conn.close()

    return df

##-------------------------------------------------------------------------------------------
## API REQUEST
##-------------------------------------------------------------------------------------------

def match_data_columns():
    return ['MatchID', 'Tournament', 'Division', 'Map', 'WinningTeam', 'Team1Score', 'Team2Score', 'MatchDuration', 'CompleteTime', 'MatchResult',
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
        pilot_upper_case = pilot.upper()
        if mech_id not in mechs:
            raise Exception(f'Mech with id={mech_id} not found')
        if pilot_upper_case not in rosters:
            raise Exception(f'Pilot {pilot} not found in the rosters')
        mech = mechs[mech_id]
        team = rosters[pilot_upper_case]

        new_line = {}
        new_line['MatchID'] = id
        new_line['Tournament'] = TOURNAMENT
        new_line['Division'] = ""
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
    df = None

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
    
    if df is None:
        df = pd.DataFrame([], columns=match_data_columns())

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
        if df.shape[0] > 0:
            df.to_sql('CompData', conn, if_exists='append', index=False)

        # API calls limited by 60 per minute
        sleep(1)

    conn.close()

##-------------------------------------------------------------------------------------------
## PAGES
##-------------------------------------------------------------------------------------------

def sidebar(df):
    options = {}
    filtered_data = df

    # Tournament
    tournaments = filtered_data['Tournament'].drop_duplicates().sort_values(ascending=True)
    tournament = st.sidebar.selectbox('Select a tournament', tournaments, index=None, placeholder='Select a tournament', label_visibility='hidden')
    if tournament:
        filtered_data = filtered_data[filtered_data['Tournament'] == tournament]

    # Team
    teams = filtered_data['TeamName'].drop_duplicates().sort_values(ascending=True)
    # team = st.sidebar.selectbox('Select a team', teams, index=None, placeholder='Select a team', label_visibility='hidden')
    # if team:
    #     filtered_data = filtered_data[filtered_data['TeamName'] == team]
    selected_teams = st.sidebar.multiselect('Select teams', teams, placeholder='Select teams', label_visibility='hidden')
    if selected_teams:
        filtered_data = filtered_data[filtered_data['TeamName'].isin(selected_teams)]
    
    # Player
    players = filtered_data['Username'].drop_duplicates().sort_values(ascending=True)
    player = st.sidebar.selectbox('Select a pilot', players, index=None, placeholder='Select a pilot', label_visibility='hidden')
    if player:
        filtered_data = filtered_data[filtered_data['Username'] == player]

    # Map
    maps = filtered_data['Map'].drop_duplicates().sort_values(ascending=True)
    map = st.sidebar.selectbox('Select a map', maps, index=None, placeholder='Select a map', label_visibility='hidden')
    if map:
        filtered_data = filtered_data[filtered_data['Map'] == map]

    # Match ID submission form
    form = st.sidebar.form("data_fetching", clear_on_submit=True)
    text_area = form.text_area('Get API data for provided IDs:', placeholder='List of Match IDs', key='match_ids')
    match_ids = text_area.strip().splitlines() if text_area else []
    form.form_submit_button('Submit', use_container_width=True)

    # CSV data dump
    csv = df.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button(
        label="Download data as CSV",
        data=csv,
        file_name="data_dump.csv",
        mime='text/csv',
        use_container_width=True
    )

    st.sidebar.divider()

    # Settings
    st.sidebar.caption('Settings:')
    horizontal_labels = st.sidebar.checkbox('Draw chart labels horizontally', value=False)

    options['data'] = filtered_data
    # options['team'] = team
    options['teams'] = selected_teams

    options['player'] = player
    options['match_ids'] = match_ids
    options['map'] = map
    options['horizontal_labels'] = horizontal_labels

    return options

def general_statistics(options):
    df = options['data']

    games_played = df['MatchID'].nunique()
    teams_number = df['TeamName'].nunique()
    mechs_killed = df['Kills'].sum()
    components_destroyed = df['ComponentsDestroyed'].sum()
    team_damage = df['TeamDamage'].sum()

    top_mechs = df['Mech'].value_counts().sort_values(ascending=False).head(10).reset_index()
    top_chassis = df['Chassis'].value_counts().sort_values(ascending=False).head(10).reset_index()

    light_mechs_data = df[df['Class'] == 'LIGHT']
    top_light_mechs = light_mechs_data['Mech'].value_counts().sort_values(ascending=False).head(5).reset_index()
    top_light_chassis = light_mechs_data['Chassis'].value_counts().sort_values(ascending=False).head(5).reset_index()

    medium_mechs_data = df[df['Class'] == 'MEDIUM']
    top_medium_mechs = medium_mechs_data['Mech'].value_counts().sort_values(ascending=False).head(5).reset_index()
    top_medium_chassis = medium_mechs_data['Chassis'].value_counts().sort_values(ascending=False).head(5).reset_index()

    heavy_mechs_data = df[df['Class'] == 'HEAVY']
    top_heavy_mechs = heavy_mechs_data['Mech'].value_counts().sort_values(ascending=False).head(5).reset_index()
    top_heavy_chassis = heavy_mechs_data['Chassis'].value_counts().sort_values(ascending=False).head(5).reset_index()

    assault_mechs_data = df[df['Class'] == 'ASSAULT']
    top_assault_mechs = assault_mechs_data['Mech'].value_counts().sort_values(ascending=False).head(5).reset_index()
    top_assault_chassis = assault_mechs_data['Chassis'].value_counts().sort_values(ascending=False).head(5).reset_index()

    mech_usage = df.groupby('Tonnage')['MatchResult'].value_counts().reset_index().rename(columns={'MatchResult': 'Result'})
    mech_usage['Positive'] = mech_usage.apply(lambda row: row['count'] if row['Result'] == 'WIN' else 0, axis=1)
    mech_usage['Negative'] = mech_usage.apply(lambda row: -row['count'] if row['Result'] == 'LOSS' else 0, axis=1)
    mech_usage = mech_usage.sort_values('Tonnage', ascending=True)

    df['MatchDuration'] = df['MatchDuration'].astype(int)
    match_duration = df.groupby('TeamName')['MatchDuration'].mean().sort_values(ascending=True).reset_index()
    match_duration = match_duration.rename(columns={'MatchDuration': 'Duration', 'TeamName': 'Team'})
    match_duration['Duration'] = match_duration['Duration'] / 60

    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
    col1.metric(label='Teams', value=teams_number)
    col2.metric(label='Games played', value=games_played)
    col3.metric(label='Mechs killed', value=mechs_killed)
    col4.metric(label='Components destroyed', value=components_destroyed)
    col5.metric(label='Team damage dealt', value=team_damage)

    st.divider()

    # Row 1
    col1, col2, col3, col4 = st.columns(4)
    col1.altair_chart(
        negative_stacked_bar_chart_mech_usage(mech_usage), use_container_width=True)
    col2.altair_chart(
        horizontal_bar_chart_match_duration(match_duration), use_container_width=True)
    col3.altair_chart(
        bar_chart(top_mechs, 'Most used mechs', 'Mech', 'count'), use_container_width=True)
    col4.altair_chart(
        bar_chart(top_chassis, 'Most used chassis', 'Chassis', 'count', style='alternate'), use_container_width=True)
    
    st.divider()

    # Row 2
    col1, col2, col3, col4 = st.columns(4)
    col1.altair_chart(
        bar_chart(top_light_mechs, 'Most used light mechs', 'Mech', 'count'), use_container_width=True)
    col2.altair_chart(
        bar_chart(top_medium_mechs, 'Most used medium mechs', 'Mech', 'count'), use_container_width=True)
    col3.altair_chart(
        bar_chart(top_heavy_mechs, 'Most used heavy mechs', 'Mech', 'count'), use_container_width=True)
    col4.altair_chart(
        bar_chart(top_assault_mechs, 'Most used assault mechs', 'Mech', 'count'), use_container_width=True)
    
    st.divider()
    
    # Row 3
    col1, col2, col3, col4 = st.columns(4)
    col1.altair_chart(
        bar_chart(top_light_chassis, 'Most used light chassis', 'Chassis', 'count', style='alternate'), use_container_width=True)
    col2.altair_chart(
        bar_chart(top_medium_chassis, 'Most used medium chassis', 'Chassis', 'count', style='alternate'), use_container_width=True)
    col3.altair_chart(
        bar_chart(top_heavy_chassis, 'Most used heavy chassis', 'Chassis', 'count', style='alternate'), use_container_width=True)
    col4.altair_chart(
        bar_chart(top_assault_chassis, 'Most used assault chassis', 'Chassis', 'count', style='alternate'), use_container_width=True)
    
def team_statistics(options):
    if len(options['teams']) == 1:
        team_data = options['data']
        # team = options['team']
        team = options['teams'][0]
        map = options['map']

        if team_data.shape[0] == 0:
            write_error(f'Data not found for team: {team}')
            return
        
        games_played = team_data['MatchID'].nunique()
        wins = team_data[team_data['MatchResult'] == 'WIN'].shape[0]
        losses = team_data[team_data['MatchResult'] == 'LOSS'].shape[0]
        win_loss_ratio = safe_division(wins, losses)

        t1_games = team_data[team_data['Team'] == '1']
        t1_wins = safe_division(t1_games[t1_games['MatchResult'] == 'WIN'].shape[0], t1_games.shape[0])
        t2_games = team_data[team_data['Team'] == '2']
        t2_wins = safe_division(t2_games[t2_games['MatchResult'] == 'WIN'].shape[0], t2_games.shape[0])

        avg_kills = safe_division(team_data['Kills'].sum(), games_played)
        avg_damage = safe_division(team_data['Damage'].sum(), games_played)

        weight_class_order = ['LIGHT', 'MEDIUM', 'HEAVY', 'ASSAULT']
        class_distribution = team_data.groupby('Class')['Class'].value_counts().reindex(weight_class_order).reset_index()
        top_mechs = team_data['Mech'].value_counts().sort_values(ascending=False).head(10).reset_index()
        top_chassis = team_data['Chassis'].value_counts().sort_values(ascending=False).head(10).reset_index()
        
        # Pilot statistics
        team_data['Deaths'] = np.where(team_data['HealthPercentage'] == 0, 1, 0)
        pilot_stats = team_data.groupby('Username', as_index=False).agg(
            Score=('MatchScore','mean'),
            Tonnage=('Tonnage','mean'),
            Kills=('Kills','mean'),
            KMDDs=('KillsMostDamage','mean'),
            Assists=('Assists','mean'),
            CDs=('ComponentsDestroyed','mean'),
            Deaths=('Deaths','mean'),
            DMG=('Damage','mean'),
            TD=('TeamDamage','mean'),
            Games=('MatchID','nunique')
        )
        pilot_stats = pilot_stats.style.format(subset=['Score', 'Tonnage', 'Kills', 'KMDDs', 'Assists', 'CDs', 'Deaths', 'DMG', 'TD'], formatter="{:.2f}")
        
        # Map statistics
        map_stats = team_data.groupby(['Map', 'MatchResult'])['MatchID'].nunique().reset_index(name='count').rename(columns={'MatchResult': 'Result'})
        map_stats['Positive'] = map_stats.apply(lambda row: row['count'] if row['Result'] == 'WIN' else 0, axis=1)
        map_stats['Negative'] = map_stats.apply(lambda row: -row['count'] if row['Result'] == 'LOSS' else 0, axis=1)
        map_stats = map_stats.sort_values('Map', ascending=True)

        if map:
            col1, col2 = st.columns([1, 1])
            col1.subheader(f'Team: {team}')
            col2.subheader(f'Map: {map}')
        else:
            st.subheader(f'Team: {team}')

        col1, col2, col3, col4, col5, col6 = st.columns([1, 1, 1, 1, 1, 1])
        col1.metric(label='Games played', value=games_played)
        col2.metric(label='Win/Loss ratio', value=f'{win_loss_ratio:.2f}')
        col3.metric(label='Team 1 Wins', value=f'{100 * t1_wins:.0f} %')
        col4.metric(label='Team 2 Wins', value=f'{100 * t2_wins:.0f} %')
        col5.metric(label='Avg kills (per drop)', value=f'{avg_kills:.2f}')
        col6.metric(label='Avg damage (per drop)', value=f'{avg_damage:.2f}')

        st.divider()

        # Row 1
        col1, col2, col3 = st.columns(3)
        col1.altair_chart(
            bar_chart(top_mechs, 'Most used mechs', 'Mech', 'count'), use_container_width=True)
        col2.altair_chart(
            bar_chart(top_chassis, 'Most used chassis', 'Chassis', 'count', style='alternate'), use_container_width=True)
        col3.altair_chart(
            bar_chart(class_distribution, 'Weight class distribution', 'Class', 'count'), use_container_width=True)

        st.divider()

        # Row 2
        col1, col2 = st.columns(2)
        col1.subheader('Average pilot statistics')
        col1.dataframe(pilot_stats, hide_index=True, use_container_width=True)
        col2.altair_chart(
            negative_horizontal_stacked_bar_chart_map_stats(map_stats, 'Map statistics'), use_container_width=True)
    elif 'teams' in options:
        data = options['data']

        mechs, maps, rosters = st.tabs(['Mechs', 'Maps', 'Rosters'])
        with mechs:
            for team in options['teams']:
                team_data = data[data['TeamName'] == team]
                map = options['map']

                if team_data.shape[0] == 0:
                    write_error(f'Data not found for team: {team}')
                    return
                
                games_played = team_data['MatchID'].nunique()
                wins = team_data[team_data['MatchResult'] == 'WIN'].drop_duplicates(subset=['MatchID']).shape[0]
                losses = team_data[team_data['MatchResult'] == 'LOSS'].drop_duplicates(subset=['MatchID']).shape[0]
                win_loss_ratio = safe_division(wins, losses)

                t1_games = team_data[team_data['Team'] == '1']
                t1_wins = safe_division(t1_games[t1_games['MatchResult'] == 'WIN'].shape[0], t1_games.shape[0])
                t2_games = team_data[team_data['Team'] == '2']
                t2_wins = safe_division(t2_games[t2_games['MatchResult'] == 'WIN'].shape[0], t2_games.shape[0])

                avg_kills = safe_division(team_data['Kills'].sum(), games_played)
                avg_damage = safe_division(team_data['Damage'].sum(), games_played)

                weight_class_order = ['LIGHT', 'MEDIUM', 'HEAVY', 'ASSAULT']
                class_distribution = team_data.groupby('Class')['Class'].value_counts().reindex(weight_class_order).reset_index()
                top_mechs = team_data['Mech'].value_counts().sort_values(ascending=False).head(10).reset_index()
                top_chassis = team_data['Chassis'].value_counts().sort_values(ascending=False).head(10).reset_index()
                
                if map:
                    col1, col2 = st.columns([1, 1])
                    col1.subheader(f'Team: {team}')
                    col2.subheader(f'Map: {map}')
                else:
                    st.subheader(f'Team: {team}')

                col1, col2, col3, col4, col5, col6 = st.columns([1, 1, 1, 1, 1, 1])
                col1.metric(label='Games played', value=games_played)
                col2.metric(label='Win/Loss ratio', value=f'{win_loss_ratio:.2f}')
                col3.metric(label='Team 1 Wins', value=f'{100 * t1_wins:.0f} %')
                col4.metric(label='Team 2 Wins', value=f'{100 * t2_wins:.0f} %')
                col5.metric(label='Avg kills (per drop)', value=f'{avg_kills:.2f}')
                col6.metric(label='Avg damage (per drop)', value=f'{avg_damage:.2f}')

                st.divider()

                # Row 1
                col1, col2, col3 = st.columns(3)
                col1.altair_chart(
                    bar_chart(top_mechs, 'Most used mechs', 'Mech', 'count'), use_container_width=True)
                col2.altair_chart(
                    bar_chart(top_chassis, 'Most used chassis', 'Chassis', 'count', style='alternate'), use_container_width=True)
                col3.altair_chart(
                    bar_chart(class_distribution, 'Weight class distribution', 'Class', 'count'), use_container_width=True)

        with maps:
            max_columns = 3
            
            map_stats = data.groupby(['Map', 'TeamName', 'MatchResult'])['MatchID'].nunique().reset_index(name='count').rename(columns={'MatchResult': 'Result', 'TeamName': 'Team'})
            map_stats['Positive'] = map_stats.apply(lambda row: row['count'] if row['Result'] == 'WIN' else 0, axis=1)
            map_stats['Negative'] = map_stats.apply(lambda row: -row['count'] if row['Result'] == 'LOSS' else 0, axis=1)
            map_stats = map_stats.sort_values(by=['Team', 'Map'], ascending=True)

            teams = map_stats['Team'].drop_duplicates().sort_values(ascending=True).tolist()
            teams_count = len(teams)

            for i in range(0, teams_count):
                index = i % max_columns
                if index == 0:
                    columns = st.columns(max_columns)
                column = columns[index]

                team_name = teams[i]
                team_data = map_stats[map_stats['Team'] == team_name]

                column.altair_chart(
                    negative_horizontal_stacked_bar_chart_map_stats(team_data, team_name), use_container_width=True)

        with rosters:
            # Pilot statistics
            data['Deaths'] = np.where(data['HealthPercentage'] == 0, 1, 0)
            pilot_stats = data.groupby(['Username', 'TeamName'], as_index=False).agg(
                Score=('MatchScore','mean'),
                Tonnage=('Tonnage','mean'),
                Kills=('Kills','mean'),
                KMDDs=('KillsMostDamage','mean'),
                Assists=('Assists','mean'),
                CDs=('ComponentsDestroyed','mean'),
                Deaths=('Deaths','mean'),
                DMG=('Damage','mean'),
                TD=('TeamDamage','mean'),
                Games=('MatchID','nunique')
            )
            df_height = 35 * (pilot_stats.shape[0] + 1) + 3

            pilot_stats = pilot_stats.style.format(subset=['Score', 'Tonnage', 'Kills', 'KMDDs', 'Assists', 'CDs', 'Deaths', 'DMG', 'TD'], formatter="{:.2f}")
            st.dataframe(pilot_stats, hide_index=True, use_container_width=True, height=df_height)

def player_statistics(options):
    player_data = options['data']
    player = options['player']
    map = options['map']

    if player_data.shape[0] == 0:
        write_error(f'Data not found for player: {player}')
        return
    
    total_games = player_data.shape[0]
    wins = player_data[player_data['MatchResult'] == 'WIN'].shape[0]
    losses = player_data[player_data['MatchResult'] == 'LOSS'].shape[0]
    win_loss_ratio = safe_division(wins, losses)

    kills = player_data['Kills'].sum()
    kmdds = player_data['KillsMostDamage'].sum()
    assists = player_data['Assists'].sum()
    deaths = player_data[player_data['HealthPercentage'] == 0].shape[0]
    kills_deaths_ratio = safe_division(kills, deaths)

    avg_damage = player_data['Damage'].mean()
    total_damage = player_data['Damage'].sum()

    top_mechs = player_data['Mech'].value_counts().sort_values(ascending=False).head(3).reset_index()
    avg_damage_per_mech = player_data.groupby('Mech')['Damage'].mean()
    win_loss_per_mech = player_data.groupby('Mech')['MatchResult'].apply(lambda x: safe_division(x.value_counts().get('WIN', 0), x.value_counts().get('LOSS', 1)))
    kills_to_deaths_per_mech = player_data.groupby('Mech')[['Mech', 'Kills', 'HealthPercentage']].apply(lambda x: safe_division(x['Kills'].sum(), x['HealthPercentage'].eq(0).sum()))

    mech_stats = top_mechs.copy().rename(columns={'count': 'Games'})
    mech_stats['Avg Dmg'] = mech_stats['Mech'].map(avg_damage_per_mech)
    mech_stats['W/L'] = mech_stats['Mech'].map(win_loss_per_mech)
    mech_stats['K/D'] = mech_stats['Mech'].map(kills_to_deaths_per_mech)

    player_history = player_data.groupby(['Tournament', 'TeamName'], as_index=False)['MatchID'].nunique().rename(columns={'TeamName': 'Team', 'MatchID': 'Games'})

    # Subheader
    if map:
        col1, col2 = st.columns([1, 1])
        col1.subheader(f'Player: {player}')
        col2.subheader(f'Map: {map}')
    else:
        st.subheader(f'Player: {player}')

    # Row 1, 2
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    col1.metric(label='Games played', value=total_games)
    col1.metric(label='Win/Loss ratio', value=f'{win_loss_ratio:.2f}')

    col2.metric(label='Kills', value=kills)
    col2.metric(label='Kills/Deaths ratio', value=f'{kills_deaths_ratio:.2f}')

    col3.metric(label='KMDDs', value=kmdds)
    col3.metric(label='Assists', value=assists)

    col4.metric(label='Avg damage (per drop)', value=f'{avg_damage:.2f}')
    col4.metric(label='Total damage', value=total_damage)

    st.divider()

    # Row 3
    col1, col2 = st.columns(2)
    col1.subheader('Teams and tournaments:')
    col1.dataframe(player_history, hide_index=True, use_container_width=True)

    col2.subheader('Most used mechs:')
    col2.dataframe(mech_stats, hide_index=True, use_container_width=True)

def map_statistics(options):
    map_data = options['data']
    map = options['map']

    if map_data.shape[0] == 0:
        write_error(f'No data for the map: {map}')
        return
    
    # Badges
    games_played = map_data['MatchID'].nunique()
    t1_games = map_data[map_data['Team'] == '1']
    t1_wins = safe_division(t1_games[t1_games['MatchResult'] == 'WIN'].shape[0], t1_games.shape[0])
    t2_games = map_data[map_data['Team'] == '2']
    t2_wins = safe_division(t2_games[t2_games['MatchResult'] == 'WIN'].shape[0], t2_games.shape[0])
    map_data['MatchDuration'] = map_data['MatchDuration'].astype(int)
    avg_duration = map_data['MatchDuration'].mean() / 60

    # Average tonnage T1
    lance_map = {'1': 'Alpha', '2': 'Bravo', '3': 'Charlie'}
    total_tonnage_t1 = t1_games.groupby(['MatchID', 'Lance'])['Tonnage'].sum().reset_index()
    avg_tonnage_t1 = total_tonnage_t1.groupby(['Lance'])['Tonnage'].mean().reset_index()
    avg_tonnage_t1['Lance'] = avg_tonnage_t1['Lance'].replace(lance_map)

    # Average tonnage T2
    total_tonnage_t2 = t2_games.groupby(['MatchID', 'Lance'])['Tonnage'].sum().reset_index()
    avg_tonnage_t2 = total_tonnage_t2.groupby(['Lance'])['Tonnage'].mean().reset_index()
    avg_tonnage_t2['Lance'] = avg_tonnage_t2['Lance'].replace(lance_map)

    # Top-10 mechs
    top_10_mechs = map_data['Mech'].value_counts().head(10).index.tolist()
    filtered_data = map_data[map_data['Mech'].isin(top_10_mechs)]

    mech_team_counts = filtered_data.groupby(['Mech', 'Team']).size().sort_values(ascending=False).reset_index(name='count')

    # Top-10 chassis
    top_10_chassis = map_data['Chassis'].value_counts().head(10).index.tolist()
    filtered_data = map_data[map_data['Chassis'].isin(top_10_chassis)]

    chassis_team_counts = filtered_data.groupby(['Chassis', 'Team']).size().sort_values(ascending=False).reset_index(name='count')

    st.subheader(f'Map: {map}')

    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    col1.metric(label='Games played', value=games_played)
    col2.metric(label='Team 1 Wins', value=f'{100 * t1_wins:.0f} %')
    col3.metric(label='Team 2 Wins', value=f'{100 * t2_wins:.0f} %')
    col4.metric(label='Avg Duration (min)', value=f'{avg_duration:.2f}')

    st.divider()

    col1, col2 = st.columns([1, 1])

    col1.altair_chart(
        bar_chart(avg_tonnage_t1, 'Average lance tonnage (Team 1)', 'Lance', 'Tonnage:Q'), use_container_width=True)

    col2.altair_chart(
        bar_chart(avg_tonnage_t2, 'Average lance tonnage (Team 2)', 'Lance', 'Tonnage:Q', style='team2'), use_container_width=True)

    col1.altair_chart(
        stacked_bar_chart(mech_team_counts, 'Top mech picks', 'Mech', 'count', 'Team'), use_container_width=True)
    
    col2.altair_chart(
        stacked_bar_chart(chassis_team_counts, 'Top chassis picks', 'Chassis', 'count', 'Team'), use_container_width=True)

##-------------------------------------------------------------------------------------------
## MAIN
##-------------------------------------------------------------------------------------------

st.logo('./img/Logo.png', icon_image='./img/Logo.png')
st.set_page_config(page_title="Stats Tool", layout='wide')
st.title(APP_TITLE)

df = read_comp_data(DB_NAME)
options = sidebar(df)

if options['match_ids']:
    batch_request(options['match_ids'], API_URL, DB_NAME)
if 'horizontal_labels' in options:
    set_chart_labels_angle(options['horizontal_labels'])

# if not options['team'] and not options['player'] and not options['map']:
#     general_statistics(options)
# elif not options['team'] and not options['player']:
#     map_statistics(options)
# elif options['player']:
#     player_statistics(options)
# elif options['team']:
#     team_statistics(options)
if not options['teams'] and not options['player'] and not options['map']:
    general_statistics(options)
elif not options['teams'] and not options['player']:
    map_statistics(options)
elif options['player']:
    player_statistics(options)
elif options['teams']:
    team_statistics(options)
