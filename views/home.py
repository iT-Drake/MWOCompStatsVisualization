import streamlit as st
import pandas as pd

from utility.database import read_comp_data
from utility.methods import nunique, unique
from utility.charts import line_chart_submitted_games
from utility.blocks import metrics_block

def header():
    st.header('Welcome to MWO Stats Tool!')

def general_statistics(df):
    # Metrics
    tournaments = nunique(df, 'Tournament')
    teams = nunique(df, 'TeamName')
    players = nunique(df, 'Username')
    games = nunique(df, 'MatchID')

    start_date = pd.to_datetime(df['CompleteTime'].iloc[0], format='ISO8601').strftime("%Y-%m-%d") if df.size > 0 else "--/--/----"

    metrics = {
        'Tournaments': tournaments,
        'Teams': teams,
        'Players': players,
        'Games': games,
        'Tracking data since': f'{start_date}'
    }
    metrics_block(metrics)

    st.divider()

def submitted_games(df):
    df['CompleteTime'] = pd.to_datetime(df['CompleteTime'], format='ISO8601')
    st.altair_chart(line_chart_submitted_games(df), use_container_width=True)

def recently_added(df):
    st.write('Last 10 uploaded games:')

    unique_matches = df['MatchID'].unique()
    last_10_matches = unique_matches[-10:]

    result = df[df['MatchID'].isin(last_10_matches)].copy()
    result['CompleteTime'] = pd.to_datetime(result['CompleteTime'], format='ISO8601')
    
    result = result.sort_values(by=['CompleteTime', 'MatchID', 'MatchResult'], ascending=False).groupby('MatchID').agg(
        Map=('Map', 'first'),
        Team1=('TeamName', 'first'),
        Result=('MatchResult', 'first'),
        Team2=('TeamName', 'last')
    ).reset_index()
    result['MatchID'] = result['MatchID'].astype(str)

    result.columns = ['ID', 'Map', 'Team 1', 'Result', 'Team 2']

    st.dataframe(result, hide_index=True, use_container_width=True)

def introduction():
    st.header("Introduction to the tool")

    st.write("The tool contains all the data from major competitive tournaments.")
    st.write("There are a few pages that help you dig through all the games and find the stats you need:")
    st.markdown("""
                - `Tournaments`: you can find most used mechs and chassis and general tonnage breakdow;
                - `Leaderboard`: performance metrics for all the players;
                - `Teams`: team general statistics, map performance and rosters;
                - `Players`: pilot's mech and tonnage preferences, stats and teams they played for;
                - `Maps`: side winrates, spawn points usage, most picked mechs and tournaments where map have been played;
                - `Mechs`: tournaments chassis or mech have been used in and their general performance.
                """)

    st.header("Filters")

    st.write("Each page have filters that help you specify the data you search for.")
    st.write("All filter select fields support multiple choices and are chained together")
    st.write("E.g. if you select a tournament on Teams page, then only divisions and teams from that tournament could be selected in the following filters.")

    st.image('img/Filters.png')

    st.write('Some filters are required (like "Team" and "Player" on "Teams" and "Players" pages respectively), others are optional.')

    st.header("Settings")

    st.write('You may find Charts and Leaderboard settings there. They can help give you different sorting options or better presentation on lower display resolutions.')

df = read_comp_data()

header()
general_statistics(df)
introduction()
