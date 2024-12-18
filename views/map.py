import streamlit as st
import pandas as pd

from utility.database import read_comp_data
from utility.methods import nunique, filter_dataframe, safe_division
from utility.charts import bar_chart, stacked_ordered_bar_chart
from utility.blocks import filters_block, metrics_block, charts_block

import altair as alt

def header():
    st.header('Maps')

def filters():
    df = read_comp_data()
    options = {'Tournament': None, 'Division': None, 'TeamName': 'Team', 'Map': None}
    return filters_block(df, options)

def general_statistics(df, options):
    map_pool = nunique(df, 'Map')
    games_played = nunique(df, 'MatchID')

    groupped_data = df.groupby('Map')

    games_per_map = groupped_data['MatchID'].nunique()
    most_played_map = games_per_map.idxmax()
    most_games = int(games_per_map.max())

    least_played_map = games_per_map.idxmin()
    least_games = int(games_per_map.min())

    col1, col2, col3, col4 = st.columns(4)
    col1.metric('Map pool', map_pool)
    col2.metric('Games', games_played)
    col3.metric('Most played', most_played_map, most_games, delta_color='off')
    col4.metric('Least played', least_played_map, least_games, delta_color='off')

def map_statistics(df, options):
    overview, details, mechs, tournaments = st.tabs(['Overview', 'Details', 'Mechs', 'Tournaments'])
    for map in options['Map']:
        map_data = filter_dataframe(df, 'Map', map)

        with overview:
            map_overview(map_data, map)
        
        with details:
            map_details(map_data, map)

        with mechs:
            map_mechs(map_data, map)

        with tournaments:
            map_tournaments(map_data, map)

def map_overview(df, map):
    st.subheader(map)

    games_played = nunique(df, 'MatchID')
    t1_games = filter_dataframe(df, 'Team', '1')
    t1_wins = safe_division(filter_dataframe(t1_games, 'MatchResult', 'WIN').shape[0], t1_games.shape[0])
    t2_games = filter_dataframe(df, 'Team', '2')
    t2_wins = safe_division(filter_dataframe(t2_games, 'MatchResult', 'WIN').shape[0], t2_games.shape[0])
    df.loc[:, 'MatchDuration'] = df['MatchDuration'].astype(int)
    avg_duration = df['MatchDuration'].mean() / 60

    metrics = {
        'Games played': games_played,
        'Team 1 Wins': f'{100 * t1_wins:.0f} %',
        'Team 2 Wins': f'{100 * t2_wins:.0f} %',
        'Average Duration (min)': f'{avg_duration:.2f}'
    }
    metrics_block(metrics)

    st.divider()

def map_details(df, map):
    st.subheader(map)

    t1_games = filter_dataframe(df, 'Team', '1')
    t2_games = filter_dataframe(df, 'Team', '2')

    lance_map = {'1': 'Alpha', '2': 'Bravo', '3': 'Charlie'}
    weight_class_order = ['LIGHT', 'MEDIUM', 'HEAVY', 'ASSAULT']

    t1_data = t1_games.groupby(['Lance', 'Class']).size().reindex(weight_class_order, level=1).reset_index(name='Count')
    t1_data['Lance'] = t1_data['Lance'].replace(lance_map)

    t2_data = t2_games.groupby(['Lance', 'Class']).size().reindex(weight_class_order, level=1).reset_index(name='Count')
    t2_data['Lance'] = t2_data['Lance'].replace(lance_map)

    charts = [
        stacked_ordered_bar_chart(t1_data, 'Class distribution by Lance Team 1', 'Lance', 'Count', 'Class', weight_class_order),
        stacked_ordered_bar_chart(t2_data, 'Class distribution by Lance Team 2', 'Lance', 'Count', 'Class', weight_class_order, 'darkred')
    ]
    charts_block(charts)
    
    st.divider()

def map_mechs(df, map):
    st.subheader(map)

    top_chassis = df['Chassis'].value_counts().sort_values(ascending=False).head(10).reset_index()

    chassis_stats = df.groupby('Chassis')['MatchResult'].apply(lambda x: safe_division(x.value_counts().get('WIN', 0), x.value_counts().get('LOSS', 0)))
    chassis_stats = chassis_stats.reset_index().rename(columns={'MatchResult': 'WLR'}).sort_values(by=['WLR'], ascending=False).head(10)

    charts = [
        bar_chart(top_chassis, 'Most used chassis', 'Chassis', 'count'),
        bar_chart(chassis_stats, 'Highest winrate chassis', 'Chassis', 'WLR', style='alternate')
    ]
    charts_block(charts)
    
    st.divider()

def map_tournaments(df, map):
    win_percentage = df.groupby(['Tournament', 'Team'])['MatchResult'].apply(
        lambda x: (x == 'WIN').sum() / len(x) if len(x) > 0 else 0
    ).reset_index()

    chart = alt.Chart(win_percentage).mark_bar().encode(
        x=alt.X('MatchResult:Q', axis=alt.Axis(format='.0%'), title='Win rate'),
        y=alt.Y('Tournament:N', sort='-x'),
        color='Team:N'
    ).properties(
        title=map
    )
    st.altair_chart(chart)

    st.divider()

header()
df, options = filters()
if options['Map']:
    map_statistics(df, options)
else:
    general_statistics(df, options)
