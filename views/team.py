import streamlit as st
import numpy as np

from utility.database import read_comp_data
from utility.methods import nunique, unique, filter_dataframe, error, safe_division
from utility.charts import bar_chart, negative_horizontal_stacked_bar_chart_map_stats
from utility.blocks import filters_block, metrics_block

def header():
    st.header('Teams')

def filters():
    df = read_comp_data()
    options = {'Tournament': None, 'Division': None, 'TeamName': 'Team', 'Map': None}
    return filters_block(df, options)

def team_mech_statistics(df):
    games_played = nunique(df, 'MatchID')
    wins = filter_dataframe(df, 'MatchResult', 'WIN').drop_duplicates(subset=['MatchID']).shape[0]
    losses = filter_dataframe(df, 'MatchResult', 'LOSS').drop_duplicates(subset=['MatchID']).shape[0]
    win_loss_ratio = safe_division(wins, losses)

    t1_games = filter_dataframe(df, 'Team', '1')
    t1_wins = safe_division(filter_dataframe(t1_games, 'MatchResult', 'WIN').shape[0], t1_games.shape[0])
    t2_games = filter_dataframe(df, 'Team', '2')
    t2_wins = safe_division(filter_dataframe(t2_games, 'MatchResult', 'WIN').shape[0], t2_games.shape[0])

    avg_kills = safe_division(df['Kills'].sum(), games_played)
    avg_damage = safe_division(df['Damage'].sum(), games_played)

    weight_class_order = ['LIGHT', 'MEDIUM', 'HEAVY', 'ASSAULT']
    class_distribution = df.groupby('Class')['Class'].value_counts().reindex(weight_class_order).reset_index()
    top_mechs = df['Mech'].value_counts().sort_values(ascending=False).head(10).reset_index()
    top_chassis = df['Chassis'].value_counts().sort_values(ascending=False).head(10).reset_index()
    
    metrics = {
        'Games played': games_played,
        'Win/Loss ratio': f'{win_loss_ratio:.2f}',
        'Team 1 Wins': f'{100 * t1_wins:.0f} %',
        'Team 2 Wins': f'{100 * t2_wins:.0f} %',
        'Avg kills (per drop)': f'{avg_kills:.2f}',
        'Avg damage (per drop)': f'{avg_damage:.2f}'
    }

    metrics_block(metrics, columns=6)

    st.divider()

    col1, col2, col3 = st.columns(3)
    col1.altair_chart(
        bar_chart(top_mechs, 'Most used mechs', 'Mech', 'count'), use_container_width=True)
    col2.altair_chart(
        bar_chart(top_chassis, 'Most used chassis', 'Chassis', 'count', style='alternate'), use_container_width=True)
    col3.altair_chart(
        bar_chart(class_distribution, 'Weight class distribution', 'Class', 'count'), use_container_width=True)

def team_statistics(df, options):
    mechs, maps, rosters = st.tabs(['Mechs', 'Maps', 'Rosters'])
    with mechs:
        teams = options['TeamName']
        for team in teams:
            team_data = filter_dataframe(df, 'TeamName', team)

            st.subheader(team)
            team_mech_statistics(team_data)

    with maps:
        max_columns = 3
        
        map_stats = df.groupby(['Map', 'TeamName', 'MatchResult'])['MatchID'].nunique().reset_index(name='count').rename(columns={'MatchResult': 'Result', 'TeamName': 'Team'})
        map_stats['Positive'] = map_stats.apply(lambda row: row['count'] if row['Result'] == 'WIN' else 0, axis=1)
        map_stats['Negative'] = map_stats.apply(lambda row: -row['count'] if row['Result'] == 'LOSS' else 0, axis=1)
        map_stats = map_stats.sort_values(by=['Team', 'Map'], ascending=True)

        teams = options['TeamName']
        teams_count = len(teams)

        for i in range(0, teams_count):
            index = i % max_columns
            if index == 0:
                columns = st.columns(max_columns)
            column = columns[index]

            team_name = teams[i]
            team_data = filter_dataframe(map_stats, 'Team', team_name)

            column.altair_chart(
                negative_horizontal_stacked_bar_chart_map_stats(team_data, team_name), use_container_width=True)

    with rosters:
        df['Deaths'] = np.where(df['HealthPercentage'] == 0, 1, 0)
        pilot_stats = df.groupby(['Username', 'TeamName'], as_index=False).agg(
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

def general_statistics(df, options):
    tournaments_count = nunique(df, 'Tournament')
    teams_count = nunique(df, 'TeamName')

    groupped_data = df.groupby('TeamName')

    score_sum = groupped_data['Score'].sum()
    score_team = score_sum.idxmax()
    score_value = int(score_sum.max())

    kills_sum = groupped_data['Kills'].sum()
    kills_team = kills_sum.idxmax()
    kills_value = int(kills_sum.max())

    col1, col2, col3, col4 = st.columns(4)
    col1.metric('Tournaments', tournaments_count)
    col2.metric('Teams', teams_count)
    col3.metric('Highest score', score_team, score_value, delta_color='off')
    col4.metric('Most kills', kills_team, kills_value, delta_color='off')

header()
df, options = filters()
if options['TeamName']:
    team_statistics(df, options)
else:
    general_statistics(df, options)
