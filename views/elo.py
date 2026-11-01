import streamlit as st
import pandas as pd
import altair as alt

from utility.database import read_comp_data
from utility.methods import safe_division, filter_dataframe
from utility.blocks import filters_block, metrics_block
from utility.globals import RATING_BASE

from datetime import datetime, timedelta, timezone

def header():
    st.header('ELO')

def filters(df):
    options = {'Username': 'Pilot'}
    return filters_block(df, options)

def calculate_wlr(values):
    return safe_division(values.eq('WIN').sum(), values.eq('LOSS').sum())

def calculate_kdr(dividend, divisor):
    return dividend.div(divisor).where(divisor > 0, dividend)

def leaderboard_data(df):
    # df['CompleteTime'] = pd.to_datetime(df['CompleteTime'], format='ISO8601').dt.tz_convert(None)
    two_years_ago = datetime.now(timezone.utc) - timedelta(days=730)

    current_top100 = df[df['CompleteTime'] > two_years_ago].groupby('Username').last().sort_values(by='PilotRating', ascending=False).reset_index().head(100)
    filtered_df = df[df['Username'].isin(current_top100['Username'])].copy()

    filtered_df['Deaths'] = (filtered_df['HealthPercentage'] == 0).astype(int)
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
        TotalKills=('Kills', 'sum'),
        TotalDeaths=('Deaths', 'sum'),
        Games=('MatchID','nunique'),
        Rating=('PilotRating','last')
    ).rename(columns={'Username': 'Pilot'}).sort_values(by='Rating', ascending=False).reset_index()

    pilot_stats['Rank'] = pilot_stats.index + 1
    pilot_stats['KDR'] = calculate_kdr(pilot_stats['TotalKills'], pilot_stats['TotalDeaths'])

    return pilot_stats

def display_data(df, leaderboard):
    def get_team_names(df, match_ids):
        subset_df = df[df['MatchID'].isin(match_ids)]
        return pd.pivot_table(subset_df, values='TeamName', index='MatchID', columns='Team', aggfunc='max').to_dict(orient='index')
    
    filtered_df, options = filters(df)
    if not options['Username']:
        latest_stats = df.sort_values('CompleteTime').groupby('Username').tail(1)

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

        st.altair_chart(scatter, width='stretch')

        # ----------------------------------------------------

        chart = alt.Chart(df).mark_bar(opacity=0.6, color='seagreen').encode(
            alt.X("Performance:Q", bin=alt.Bin(maxbins=30), title="Performance Weight"),
            alt.Y('count()', title="Number of Player-Games"),
        ).properties(
            title="Distribution of Performance Weights",
            width=700,
            height=400
        )

        rule = alt.Chart(pd.DataFrame({'x': [1.0]})).mark_rule(color='red', strokeDash=[4,4]).encode(x='x:Q')

        st.altair_chart(chart + rule, width='stretch')

        # ----------------------------------------------------

        # chart = alt.Chart(df).mark_area(
        #     opacity=0.4,
        #     interpolate='monotone',
        #     line=True
        # ).encode(
        #     x=alt.X("Performance:Q", 
        #             bin=alt.Bin(maxbins=40), 
        #             title="Performance Weight (0.75 - 1.25)",
        #             scale=alt.Scale(domain=[0.7, 1.3])),
        #     y=alt.Y('count():Q', stack=None, title="Player-Games Count"),
        #     color=alt.Color('Division:N', scale=alt.Scale(scheme='category20'), title="Division")
        # ).properties(
        #     title="Performance Distribution by Division",
        #     width=800,
        #     height=400
        # )

        # rule = alt.Chart(pd.DataFrame({'x': [1.0]})).mark_rule(color='red', strokeDash=[4,4]).encode(x='x:Q')

        # st.altair_chart(chart + rule, width='stretch')

        # ----------------------------------------------------

        # df['PrevRating'] = df.groupby('Username')['PilotRating'].shift(1).fillna(50.0)
        # df['RatingChange'] = df['PilotRating'] - df['PrevRating']
        # df['StrengthDiff'] = df['TeamRating'] - df['OpponentRating']

        # # Create the scatter plot
        # chart = alt.Chart(df).mark_circle(size=60, opacity=0.4).encode(
        #     x=alt.X('StrengthDiff:Q', title='Team Rating Advantage (vs Opponent)'),
        #     y=alt.Y('RatingChange:Q', title='Rating Gained/Lost'),
        #     color=alt.condition(
        #         alt.datum.RatingChange > 0, 
        #         alt.value('steelblue'), # Wins/Gains
        #         alt.value('orange')     # Losses/Drops
        #     ),
        #     tooltip=['Username', 'StrengthDiff', 'RatingChange']
        # ).properties(
        #     width=700,
        #     height=400,
        #     title="Validation: Rating Change vs. Team Strength Matchup"
        # )

        # Create bins for the rating difference to calculate average change
        # binned_chart = alt.Chart(df).mark_line(point=True).encode(
        #     x=alt.X('StrengthDiff:Q', bin=alt.Bin(maxbins=30), title='Team Rating Advantage'),
        #     y=alt.Y('mean(RatingChange):Q', title='Average Rating Change'),
        #     color=alt.Color('MatchResult:N', scale=alt.Scale(scheme='dark2'), title="Result")
        # ).properties(
        #     title="Average Rating Change by Matchup Difficulty"
        # )

        # Add a trend line to see the correlation clearly
        # line = chart.transform_regression('StrengthDiff', 'RatingChange').mark_line(color='red')

        # st.altair_chart(chart + line, width='stretch')

        # ----------------------------------------------------

        df_height = 35 * (leaderboard.shape[0] + 1) + 3

        leaderboard = leaderboard.style.format(subset=['Tonnage', 'MS', 'Kills', 'KMDDs', 'Assists', 'CD', 'Deaths', 'DMG', 'TD', 'KDR', 'WLR', 'Rating'], formatter="{:.2f}")

        column_order = ['Rank', 'Pilot', 'Tonnage', 'MS', 'Kills', 'KMDDs', 'Assists', 'CD', 'Deaths', 'DMG', 'TD', 'KDR', 'WLR', 'Games', 'Rating']
        st.dataframe(leaderboard, hide_index=True, column_order=column_order, width='stretch', height=df_height)
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

            max_games = int(pilot_data['GameNumber'].max())

            pilot_data['Upper'] = pilot_data['PilotRating'] + pilot_data['RatingUncertainty']
            pilot_data['Lower'] = pilot_data['PilotRating'] - pilot_data['RatingUncertainty']

            pilot_data['PrevRating'] = pilot_data['PilotRating'].shift(1).fillna(50.0)
            pilot_data['RatingChange'] = pilot_data['PilotRating'] - pilot_data['PrevRating']
            pilot_data['VsTeam'] = pilot_data['PilotRating'] - pilot_data['TeamRating']
            pilot_data['VsOpponent'] = pilot_data['PilotRating'] - pilot_data['OpponentRating']
            pilot_data['TeamDifference'] = pilot_data['TeamRating'] - pilot_data['OpponentRating']

            game_range = st.slider(
                "Games range",
                min_value=1,
                max_value=max_games,
                value=(1, max_games)
            )

            filtered_pilot_data = pilot_data[
                (pilot_data['GameNumber'] >= game_range[0]) & 
                (pilot_data['GameNumber'] <= game_range[1])
            ]

            x_scale = alt.Scale(domain=[game_range[0], game_range[1]], nice=True)

            filtered_pilot_data['Year'] = pd.to_datetime(pilot_data['CompleteTime']).dt.year
            year_data = filtered_pilot_data.groupby('Year')['GameNumber'].agg(['min', 'max', 'mean']).reset_index()

            # Create a list of all potential Y values
            all_y_values = pd.concat([
                filtered_pilot_data['Lower'], 
                filtered_pilot_data['Upper'], 
                filtered_pilot_data['OpponentRating'], 
                filtered_pilot_data['TeamRating']
            ])

            minimum_rating = all_y_values.min()
            maximum_rating = all_y_values.max()

            # Add a small 5% buffer so lines don't touch the very top/bottom edges
            padding = (maximum_rating - minimum_rating) * 0.05
            minimum_rating -= padding
            maximum_rating += padding

            games = filtered_pilot_data.shape[0]

            domain = ['PilotRating', 'OpponentRating', 'TeamRating']
            division_scale = alt.Scale(scheme='dark2')
            
            # Baseline data and chart shape
            base = alt.Chart(filtered_pilot_data).transform_fold(
                domain,
                as_=['RatingType', 'RatingValue'] 
            ).encode(
                x=alt.X('GameNumber:Q', scale=x_scale, title='Game Sequence'),
                tooltip=[
                    alt.Tooltip('MatchID:N', title='ID'),
                    alt.Tooltip('CompleteTime', title='Date', format='%Y-%m-%d'),
                    alt.Tooltip('Tournament', title='Tournament'),
                    alt.Tooltip('Division', title='Division'),
                    alt.Tooltip('TeamName', title='Team'),
                    alt.Tooltip('Opponent', title='Opponent'),
                    alt.Tooltip('Map', title='Map'),
                    alt.Tooltip('MatchResult', title='Result'),
                    alt.Tooltip('PilotRating', title='Rating', format='.2f'),
                    alt.Tooltip('RatingChange', title='Rating change', format='.2f'),
                    alt.Tooltip('Performance', title='Performance', format='.2f'),
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
                y=alt.Y('Lower:Q', scale=alt.Scale(domain=[minimum_rating, maximum_rating], zero=False)),
                y2=alt.Y2('Upper:Q'),
                color=alt.value('gray')
            )

            # Layer 1: Team and opponent rating
            background_lines = base.transform_filter(
                alt.datum.RatingType != 'PilotRating'
            ).mark_line(strokeWidth=2, strokeDash=[4,4]).encode(
                y=alt.Y('RatingValue:Q', title='Rating', scale=alt.Scale(domain=[minimum_rating, maximum_rating], zero=False)),
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

            # Interactive selection
            root_key = 'selection'
            selection_key = 'match_data'
            selection = alt.selection_point(name=selection_key, fields=['MatchID', 'TeamName', 'Opponent', 'Division'])

            chart = alt.layer(
                uncertainty_band,
                background_lines,
                pilot_line,
                points,
                year_labels,
            ).resolve_scale(
                x='shared',
                color='independent'
            ).add_params(
                selection
            )

            event_data = st.altair_chart(chart, width='stretch', on_select='rerun')
            selected_data = event_data[root_key][selection_key]
            if selected_data:
                display_match_data(df, selected_data)

            # Rating change correlation

            # top_chart = alt.Chart(filtered_pilot_data).transform_fold(
            #     ['RatingChange', 'Performance'],
            #     as_=['Metric', 'Value']
            # ).mark_line(strokeWidth=2, interpolate='monotone').encode(
            #     x=alt.X('GameNumber:Q', title='Game Sequence'),
            #     y=alt.Y('Value:Q', title='Performance'),
            #     color=alt.Color('Metric:N', 
            #         scale=alt.Scale(domain=['RatingChange', 'Performance'], range=['#E74C3C', '#2ECC71'])
            #     ),
            #     tooltip=['GameNumber', 'RatingChange', 'Performance']
            # ).properties(height=300, title="Rating sensitivity vs Performance")

            # bottom_chart = alt.Chart(filtered_pilot_data).transform_fold(
            #     ['VsTeam', 'VsOpponent'],
            #     as_=['Metric', 'Value']
            # ).mark_line(strokeWidth=2, strokeDash=[4,4]).encode(
            #     x=alt.X('GameNumber:Q', title='Game Sequence'),
            #     y=alt.Y('Value:Q', title='Rating Gap'),
            #     color=alt.Color('Metric:N', 
            #         scale=alt.Scale(domain=['VsTeam', 'VsOpponent'], range=['#3498DB', '#9B59B6'])
            #     ),
            #     tooltip=['GameNumber', 'VsTeam', 'VsOpponent']
            # ).properties(height=300, title="Relative Pilot Strength")

            # third_chart = alt.Chart(filtered_pilot_data).transform_fold(
            #     ['RatingChange', 'TeamDifference'],
            #     as_=['Metric', 'Value']
            # ).mark_line().encode(
            #     x=alt.X('GameNumber:Q', title='Game Sequence'),
            #     y=alt.Y('Value:Q', title='Rating difference'),
            #     color=alt.Color('Metric:N', 
            #         scale=alt.Scale(domain=['RatingChange', 'TeamDifference'], range=['#E74C3C', '#2ECC71'])
            #     ),
            #     tooltip=['GameNumber', 'RatingChange', 'Performance', 'TeamDifference']
            # ).properties(height=300, title="Rating difference effect on rating gain")

            # final_diag_chart = alt.vconcat(
            #     top_chart,
            #     bottom_chart,
            #     third_chart
            # ).resolve_scale(
            #     x='shared',
            #     color='independent'
            # )

            # st.altair_chart(final_diag_chart, width='stretch')

            st.divider()

def display_match_data(df, selected_data):
    def pilot_ratings(data, pilots):
        pilot_data = data[(data['Username'].isin(pilots))]
        last_records = pilot_data.groupby('Username').tail(1)
        
        rating_map = dict(zip(last_records['Username'], last_records['PilotRating']))
        return {pilot: rating_map.get(pilot, RATING_BASE) for pilot in pilots}
    
    for match_data in selected_data:
        id = match_data['MatchID']
        team1 = match_data['TeamName']
        team2 = match_data['Opponent']
        division = match_data['Division']
        
        row_idx = df.index[df['MatchID'] == id][0]
        history_df = df.iloc[:row_idx]
        match_data = df[df['MatchID'] == id]
        
        first_line = match_data.iloc[0]
        team1_rating = first_line['TeamRating']
        team2_rating = first_line['OpponentRating']
        winner = first_line['WinningTeam']
        
        unique_pilots = match_data['Username'].tolist()
        ratings = pilot_ratings(history_df, unique_pilots)

        metrics = {
            'Match': id,
            'Team 1': team1,
            'Team 2': team2,
            'Division': division,
            'Date': first_line['CompleteTime'].strftime("%Y-%m-%d %H:%M:%S"),
            'T1 Rating': f"{team1_rating:.2f}",
            'T2 Rating': f"{team2_rating:.2f}",
            'Winner': winner,
        }
        metrics_block(metrics, 4)

        teams = ["1", "2"]
        columns = st.columns(len(teams))
        for index, column in enumerate(columns):
            team_id = teams[index]
            team_data = match_data[match_data['Team'] == team_id].copy()

            pre_ratings = []

            for _, row in team_data.iterrows():
                pre_ratings.append(round(ratings.get(row['Username'], 50.0), 2))

            team_data['StartingRating'] = pre_ratings

            display_df = team_data[[
                'Username', 'Mech', 'MatchScore', 'Damage', 'Kills', 'KillsMostDamage', 'PilotRating', 'Performance', 'StartingRating'
            ]]

            with column:
                st.dataframe(
                    display_df, 
                    width='stretch', 
                    hide_index=True
                )

df = read_comp_data()
header()
leaderboard = leaderboard_data(df)
display_data(df, leaderboard)
