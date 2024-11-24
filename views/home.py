import streamlit as st
import pandas as pd

from utility.database import read_comp_data
from utility.methods import nunique, unique
from utility.charts import line_chart_submitted_games

def header():
    st.header('Welcome to MWO Stats Tool!')

def general_statistics(df):
    # Metrics
    tournaments = nunique(df, 'Tournament')
    teams = nunique(df, 'TeamName')
    players = nunique(df, 'Username')
    games = nunique(df, 'MatchID')

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(label='Tournaments', value=tournaments)
    col2.metric(label='Teams', value=teams)
    col3.metric(label='Players', value=players)
    col4.metric(label='Games', value=games)

    st.divider()

def submitted_games(df):
    df['CompleteTime'] = pd.to_datetime(df['CompleteTime'], format='ISO8601')
    st.altair_chart(line_chart_submitted_games(df), use_container_width=True)

def recently_added(df):
    st.write('Last 10 uploaded games:')

    unique_matches = df['MatchID'].unique()
    last_10_matches = unique_matches[-10:]

    result = df[df['MatchID'].isin(last_10_matches)]
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

df = read_comp_data()

header()
general_statistics(df)
submitted_games(df)
recently_added(df)
