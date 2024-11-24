import streamlit as st
import pandas as pd

from utility.database import read_comp_data
from utility.methods import nunique, filter_dataframe, safe_division
from utility.charts import bar_chart
from utility.blocks import filters_block, metrics_block, charts_block

def header():
    st.header('Players')

def filters():
    df = read_comp_data()
    options = {'Tournament': None, 'Division': None, 'TeamName': 'Team', 'Username': 'Player'}
    return filters_block(df, options)

def general_statistics(df, options):
    players_count = nunique(df, 'Username')
    teams_count = nunique(df, 'TeamName')

    groupped_data = df.groupby('Username')

    score_sum = groupped_data['Score'].sum()
    score_player = score_sum.idxmax()
    score_value = int(score_sum.max())

    kills_sum = groupped_data['Kills'].sum()
    kills_player = kills_sum.idxmax()
    kills_value = int(kills_sum.max())

    col1, col2, col3, col4 = st.columns(4)
    col1.metric('Players', players_count)
    col2.metric('Teams', teams_count)
    col3.metric('Highest score', score_player, score_value, delta_color='off')
    col4.metric('Most kills', kills_player, kills_value, delta_color='off')

def player_overview(df, options):
    for player in options['Username']:
        st.subheader(player)

        player_data = filter_dataframe(df, 'Username', player)

        games_played = nunique(player_data, 'MatchID')
        score = player_data['Score'].sum()

        wins = filter_dataframe(player_data, 'Score', 1).shape[0]
        losses = filter_dataframe(player_data, 'Score', -1).shape[0]
        WLR = safe_division(wins, losses)

        kills = player_data['Kills'].sum()
        deaths = player_data[player_data['HealthPercentage'] == 0].shape[0]
        KDR = safe_division(kills, deaths)

        col1, col2 = st.columns([2, 1])
        with col1:
            metrics = {
                'Games played': games_played,
                'Win/Loss ratio': f'{WLR:.2f}',
                'Score': score,
                'Kills/Deaths ratio': f'{KDR:.2f}'
            }
            metrics_block(metrics, columns=2)

        weight_class_order = ['LIGHT', 'MEDIUM', 'HEAVY', 'ASSAULT']
        class_distribution = player_data.groupby('Class')['Class'].value_counts().reindex(weight_class_order).reset_index()
        
        col2.altair_chart(
            bar_chart(class_distribution, 'Weight class distribution', 'Class', 'count').properties(
                width=300,
                height=200
            ))

        st.divider()

def player_teams(df, options):
    teams_data = df.groupby(['Username', 'Tournament', 'Division', 'TeamName'], as_index=False).agg(
        Games=('MatchID','nunique'),
        Score=('Score','sum')
    ).rename(columns={'Username': 'Player', 'TeamName': 'Team'})

    st.dataframe(teams_data, hide_index=True, use_container_width=True)

def player_mechs(df, options):
    for player in options['Username']:
        st.subheader(player)

        player_data = filter_dataframe(df, 'Username', player)
        top_chassis = player_data['Chassis'].value_counts().sort_values(ascending=False).head(10).reset_index()

        chassis_stats = player_data.groupby('Chassis')['MatchResult'].apply(lambda x: safe_division(x.value_counts().get('WIN', 0), x.value_counts().get('LOSS', 0)))
        chassis_stats = chassis_stats.reset_index().rename(columns={'MatchResult': 'WLR'}).sort_values(by=['WLR'], ascending=False).head(10)

        charts = [
            bar_chart(top_chassis, 'Most used chassis', 'Chassis', 'count'),
            bar_chart(chassis_stats, 'Highest winrate chassis', 'Chassis', 'WLR', style='alternate')
        ]
        charts_block(charts)

        st.divider()

def player_statistics(df, options):
    overview, teams, mechs = st.tabs(['Overview', 'Teams', 'Mechs'])

    with overview:
        player_overview(df, options)

    with teams:
        player_teams(df, options)

    with mechs:
        player_mechs(df, options)

header()
df, options = filters()
if options['Username']:
    player_statistics(df, options)
else:
    general_statistics(df, options)
