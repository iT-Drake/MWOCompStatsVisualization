import streamlit as st
import pandas as pd
import altair as alt

from utility.database import read_comp_data
from utility.methods import safe_division, filter_dataframe
from utility.blocks import filters_block
# from utility.methods import

def header():
    st.header('ELO')

def filters(df):
    options = {'Username': 'Pilot'}
    return filters_block(df, options)

def calculate_wlr(values):
    return safe_division(values.eq('WIN').sum(), values.eq('LOSS').sum())

def leaderboard_data(df):
    current_top100 = df.groupby('Username').last().sort_values(by='Rating', ascending=False).reset_index().head(100)
    filtered_df = df[df['Username'].isin(current_top100['Username'])].copy()

    filtered_df['Deaths'] = [1 if health == 0 else 0 for health in filtered_df['HealthPercentage']]
    pilot_stats = filtered_df.groupby(['Username'], as_index=False).agg(
        Tonnage=('Tonnage', 'mean'),
        MS=('MatchScore', 'mean'),
        Kills=('Kills', 'mean'),
        KMDDs=('KillsMostDamage', 'mean'),
        Assists=('Assists', 'mean'),
        CD=('ComponentsDestroyed', 'mean'),
        Deaths=('Deaths', 'mean'),
        DMG=('Damage', 'mean'),
        TD=('TeamDamage', 'mean'),
        WLR=('MatchResult', lambda values: calculate_wlr(values)),
        Games=('MatchID','nunique'),
        Score=('Score','sum'),
        Rating=('Rating','last'),
        MaxGain=('Rating_change','max'),
        MaxLoss=('Rating_change','min')
    ).rename(columns={'Username': 'Pilot'}).sort_values(by='Rating', ascending=False).reset_index()

    pilot_stats['Rank'] = pilot_stats.index + 1

    return pilot_stats

def display_data(df, leaderboard):
    def get_team_names(df, match_ids):
        subset_df = df[df['MatchID'].isin(match_ids)]
        return pd.pivot_table(subset_df, values='TeamName', index='MatchID', columns='Team', aggfunc='max').to_dict(orient='index')
    
    filtered_df, options = filters(df)
    if not options['Username']:
        df_height = 35 * (leaderboard.shape[0] + 1) + 3

        leaderboard = leaderboard.style.format(subset=['Tonnage', 'MS', 'Kills', 'KMDDs', 'Assists', 'CD', 'Deaths', 'DMG', 'TD', 'WLR'], formatter="{:.2f}")

        column_order = ['Rank', 'Pilot', 'Tonnage', 'MS', 'Kills', 'KMDDs', 'Assists', 'CD', 'Deaths', 'DMG', 'TD', 'WLR', 'Games', 'Score', 'MaxGain', 'MaxLoss', 'Rating']
        st.dataframe(leaderboard, hide_index=True, column_order=column_order, use_container_width=True, height=df_height)
    else:
        match_ids = filtered_df['MatchID'].drop_duplicates()
        team_names = get_team_names(df, match_ids)
        filtered_df['Opponent'] = filtered_df.apply(
            lambda row: team_names[row['MatchID']]['2' if row['Team'] == '1' else '1'],
            axis=1
        )
        filtered_df['CompleteTime'] = pd.to_datetime(filtered_df['CompleteTime'], format='ISO8601')

        for pilot in options['Username']:
            pilot_data = filter_dataframe(filtered_df, 'Username', pilot)
            maximum_rating = pilot_data['Rating'].max()
            minimum_rating = pilot_data['Rating'].min()

            base = alt.Chart(pilot_data).encode(
                x=alt.X('yearmonthdate(CompleteTime):O', title='Date', axis=alt.Axis(format='%Y-%m-%d', labelAngle=-90)),
                y=alt.Y('Rating:Q', title='ELO Rating',
                    scale=alt.Scale(domain=[minimum_rating, maximum_rating])
                ),
                tooltip=[
                    alt.Tooltip('CompleteTime', title='Date', format='%Y-%m-%d'),
                    alt.Tooltip('Tournament', title='Tournament'),
                    alt.Tooltip('TeamName', title='Team'),
                    alt.Tooltip('Opponent', title='Opponent'),
                    alt.Tooltip('Map', title='Map'),
                    alt.Tooltip('Rating', title='Rating'),
                    alt.Tooltip('Rating_change', title='Change')
                ]
            ).properties(
                title=f"ELO Rating History for {pilot}",
                height=800
            )

            # Layer 1: The line connecting the rating points
            line = base.mark_line(
                strokeWidth=3,
                color='steelblue'
            )

            # Layer 2: The points for each match, with tooltips
            points = base.mark_point(
                size=30,
                opacity=1,
                color='steelblue'
            )

            # Combine the line and points layers
            chart = line + points

            st.altair_chart(chart, use_container_width=True)

            st.divider()

df = read_comp_data()
header()
leaderboard = leaderboard_data(df)
display_data(df, leaderboard)
