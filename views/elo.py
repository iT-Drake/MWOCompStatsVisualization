import streamlit as st
import pandas as pd
import altair as alt

from utility.database import read_comp_data
from utility.methods import safe_division, filter_dataframe
from utility.blocks import filters_block
# from utility.methods import

from datetime import datetime, timedelta

def header():
    st.header('ELO')

def filters(df):
    options = {'Username': 'Pilot'}
    return filters_block(df, options)

def calculate_wlr(values):
    return safe_division(values.eq('WIN').sum(), values.eq('LOSS').sum())

def leaderboard_data(df):
    df['CompleteTime'] = pd.to_datetime(df['CompleteTime'], format='ISO8601').dt.tz_convert(None)
    two_years_ago = datetime.now() - timedelta(days=730)

    current_top100 = df[df['CompleteTime'] > two_years_ago].groupby('Username').last().sort_values(by='PilotRating', ascending=False).reset_index().head(100)
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
        Rating=('PilotRating','last')
    ).rename(columns={'Username': 'Pilot'}).sort_values(by='Rating', ascending=False).reset_index()

    pilot_stats['Rank'] = pilot_stats.index + 1

    return pilot_stats

def display_data(df, leaderboard):
    def get_team_names(df, match_ids):
        subset_df = df[df['MatchID'].isin(match_ids)]
        return pd.pivot_table(subset_df, values='TeamName', index='MatchID', columns='Team', aggfunc='max').to_dict(orient='index')
    
    filtered_df, options = filters(df)
    if not options['Username']:
        # Create a summary dataframe: latest rating for every player
        latest_stats = df.sort_values('CompleteTime').groupby('Username').tail(1)

        # Add a 'Games Played' column to color the dots (context is key!)
        game_counts = df['Username'].value_counts().reset_index()
        game_counts.columns = ['Username', 'TotalGames']
        latest_stats = latest_stats.merge(game_counts, on='Username')

        scatter = alt.Chart(latest_stats).mark_point(opacity=0.5).encode(
            x=alt.X('RatingBase:Q', title='Mean Rating (Mu)'),
            y=alt.Y('RatingUncertainty:Q', title='Uncertainty (Sigma)'),
            color=alt.Color('TotalGames:Q', scale=alt.Scale(scheme='viridis'), title='Games Played'),
            tooltip=['Username', 'RatingBase', 'RatingUncertainty', 'TotalGames']
        ).properties(
            title="Base rating vs. Uncertainty level",
            width=800,
            height=500
        ).interactive()

        st.altair_chart(scatter, use_container_width=True)

        df_height = 35 * (leaderboard.shape[0] + 1) + 3

        leaderboard = leaderboard.style.format(subset=['Tonnage', 'MS', 'Kills', 'KMDDs', 'Assists', 'CD', 'Deaths', 'DMG', 'TD', 'WLR', 'Rating'], formatter="{:.2f}")

        column_order = ['Rank', 'Pilot', 'Tonnage', 'MS', 'Kills', 'KMDDs', 'Assists', 'CD', 'Deaths', 'DMG', 'TD', 'WLR', 'Games', 'Score', 'Rating']
        st.dataframe(leaderboard, hide_index=True, column_order=column_order, use_container_width=True, height=df_height)
    else:
        filtered_df = filtered_df.copy()
        match_ids = filtered_df['MatchID'].drop_duplicates()
        team_names = get_team_names(df, match_ids)
        filtered_df['Opponent'] = filtered_df.apply(
            lambda row: team_names[row['MatchID']]['2' if row['Team'] == '1' else '1'],
            axis=1
        )
        
        for pilot in options['Username']:
            pilot_data = filter_dataframe(filtered_df, 'Username', pilot)
            
            pilot_data = pilot_data.sort_values('CompleteTime').reset_index()
            pilot_data['GameNumber'] = pilot_data.index + 1

            pilot_data['Year'] = pd.to_datetime(pilot_data['CompleteTime']).dt.year
            year_data = pilot_data.groupby('Year')['GameNumber'].agg(['min', 'max', 'mean']).reset_index()

            pilot_data['Upper'] = pilot_data['PilotRating'] + pilot_data['RatingUncertainty']
            pilot_data['Lower'] = pilot_data['PilotRating'] - pilot_data['RatingUncertainty']

            minimum_rating = pilot_data['Lower'].min()
            maximum_rating = pilot_data['Upper'].max()
            games = pilot_data.shape[0]

            domain = ['PilotRating', 'OpponentRating', 'TeamRating']
            division_scale = alt.Scale(scheme='dark2')
            
            # Baseline data and chart shape
            base = alt.Chart(pilot_data).transform_fold(
                domain,
                as_=['RatingType', 'RatingValue'] 
            ).encode(
                x=alt.X('GameNumber:Q', title='Game Sequence'),
                tooltip=[
                    alt.Tooltip('CompleteTime', title='Date', format='%Y-%m-%d'),
                    alt.Tooltip('Tournament', title='Tournament'),
                    alt.Tooltip('Division', title='Division'),
                    alt.Tooltip('TeamName', title='Team'),
                    alt.Tooltip('Opponent', title='Opponent'),
                    alt.Tooltip('Map', title='Map'),
                    alt.Tooltip('MatchResult', title='Result'),
                    alt.Tooltip('PilotRating', title='Rating', format='.2f'),
                    alt.Tooltip('TeamRating', title='Team rating', format='.2f'),
                    alt.Tooltip('OpponentRating', title='Opponent rating', format='.2f'),
                ]
            ).properties(
                title=f"ELO Rating History for {pilot}, {games} games.",
                height=800
            )

            # Layer 0: The Uncertainty Band
            uncertainty_band = base.mark_area(
                opacity=0.2,
                color='gray'
            ).encode(
                x='GameNumber:Q',
                y='Lower:Q',
                y2='Upper:Q',
                color=alt.value('gray')
            )

            # Layer 1: Team and opponent rating
            background_lines = base.transform_filter(
                alt.datum.RatingType != 'PilotRating'
            ).mark_line(strokeWidth=2, strokeDash=[4,4]).encode(
                y=alt.Y('RatingValue:Q', title='Rating'),
                color=alt.Color('RatingType:N', 
                    scale=alt.Scale(domain=['OpponentRating', 'TeamRating'], range=['steelblue', 'seagreen']),
                    title="Lines"
                ),
                opacity=alt.value(0.4)
            )

            # Layer 2: Pilot rating
            pilot_line = base.transform_filter(
                alt.datum.RatingType == 'PilotRating'
            ).mark_line(
                strokeWidth=4,
                color='darkslateblue'
            ).encode(
                y=alt.Y('RatingValue:Q', title='Rating'),
            )

            # Layer 3: points
            points = base.transform_filter(
                alt.datum.RatingType == 'PilotRating'
            ).mark_point(
                size=60, 
                filled=True
            ).encode(
                y='RatingValue:Q',
                color=alt.Color('Division:N', scale=division_scale, title='Division')
            )

            # Layer 4: Year Labels
            year_labels = alt.Chart(year_data).mark_text(
                align='center',
                baseline='bottom',
                dy=-10, # 10 pixels above the top of the chart
                fontWeight='bold',
                color='gray'
            ).encode(
                x=alt.X('mean:Q', title='Timeline (Years)'),
                text=alt.Text('Year:N'),
                y=alt.value(-1) # Keeping labels on top
            )

            chart = alt.layer(
                uncertainty_band,
                background_lines,
                pilot_line,
                points,
                year_labels,
            ).resolve_scale(
                x='shared',
                color='independent'
            ).encode(
                y=alt.Y('PilotRating:Q', scale=alt.Scale(domain=[minimum_rating, maximum_rating], zero=False))
            )

            st.altair_chart(chart, use_container_width=True)

            st.divider()

df = read_comp_data()
header()
leaderboard = leaderboard_data(df)
display_data(df, leaderboard)
