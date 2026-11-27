import streamlit as st
import pandas as pd
import altair as alt
import numpy as np

from utility.requests import jarls_pilot_stats
from utility.methods import filter_dataframe, nunique, safe_division, unique
from utility.database import read_comp_data
from utility.blocks import metrics_block
from utility.admission import MIN_GAMES
from utility.divisions import SPECIAL_DIVISIONS, average_divisions, decode_division, division_letters
from utility.globals import RATING_BASE

COMP_DATA = read_comp_data()
DIVISIONS = unique(COMP_DATA, 'Division').to_list()
DIVISION_DECODING = {i + 1:DIVISIONS[i] for i in range(len(DIVISIONS))}
DIVISION_ENCODING = {value:key for key, value in DIVISION_DECODING.items()}
DIVISION_LETTERS = division_letters(COMP_DATA)
DIVISION_HIGH = DIVISION_ENCODING[DIVISION_LETTERS[-1]]

def back_button():
    if st.button('< Back'):
        st.switch_page('views/admin.py')

def header():
    st.header('Compare Tool')

def display_inputs():
    col1, col2 = st.columns(2)
    team1 = col1.text_area('Team 1')
    team2 = col2.text_area('Team 2')

    if not st.button('Compare', width='stretch'):
        st.markdown("#### Each pilot name should be on a new line.\n#### Error will be displayed if pilot wasn't found on Jarl's list.")
    else:
        team1_pilots = [pilot.strip().lower() for pilot in team1.splitlines() if pilot]
        team2_pilots = [pilot.strip().lower() for pilot in team2.splitlines() if pilot]
        
        col1, col2 = st.columns(2)
        
        display_stats(col1, team1_pilots, COMP_DATA)
        display_stats(col2, team2_pilots, COMP_DATA)

def display_stats(container, pilots, df):
    if not pilots:
        return
    
    pilots_data = df[df['Username'].str.lower().isin(pilots)]
    with container:
        display_metrics(pilots_data)

    team_data = {
        'Pilot': [],
        'Rank': [],
        'CompGames': [],
        'HighestDiv': [],
        'LastDiv': [],
        'AverageDiv': [],
        'Rating': [],
        'SortCode': []
    }
    for pilot in pilots:
        pilot_stats = jarls_pilot_stats(pilot)
        
        pilot_data = pilots_data[pilots_data['Username'].str.lower() == pilot.lower()].copy()
        division = calculate_pilot_division(pilot_data)
        comp_games = nunique(pilot_data, 'MatchID')
        
        if pilot_stats:
            team_data['Pilot'].append(pilot_stats['PilotName'])
            team_data['Rank'].append(pilot_stats['Rank'])
        else:
            team_data['Pilot'].append(pilot)
            team_data['Rank'].append(0)
        team_data['CompGames'].append(comp_games)

        if comp_games:
            ordered = pilot_data.sort_values('CompleteTime')
            ladder_data = ordered[~ordered['Division'].isin(SPECIAL_DIVISIONS)]
            if ladder_data.empty:
                highest_div = ordered['Division'].iloc[0]
                sort_code = DIVISION_HIGH + 1
            else:
                highest_div = min(ladder_data['Division'], key=lambda value: DIVISION_ENCODING[value])
                sort_code = DIVISION_ENCODING[highest_div]
            last_div = ordered['Division'].iloc[-1]

            team_data['HighestDiv'].append(format_division(highest_div, pilot_data))
            team_data['LastDiv'].append(format_division(last_div, pilot_data))
            team_data['AverageDiv'].append(division)
            team_data['SortCode'].append(sort_code)
            team_data['Rating'].append(ordered['PilotRating'].iloc[-1])
        else:
            team_data['HighestDiv'].append('--')
            team_data['LastDiv'].append('--')
            team_data['AverageDiv'].append(np.nan)
            team_data['SortCode'].append(DIVISION_HIGH + 1)
            team_data['Rating'].append(np.nan)

    team_data = pd.DataFrame.from_dict(team_data).sort_values(by=['SortCode','CompGames','Rank'], ascending=[True, False, True])

    measured = team_data['AverageDiv'].dropna()
    team_division = measured.mean() if not measured.empty else np.nan

    measurable = team_data['AverageDiv'].notna() & (team_data['CompGames'] >= MIN_GAMES)
    team_confidence = float(measurable.mean())

    team_rating = team_data['Rating'].mean()
    if not np.isfinite(team_rating):
        team_rating = RATING_BASE

    team_data['AverageDiv'] = [decode_division(value, DIVISION_LETTERS) for value in team_data['AverageDiv']]
    team_data = team_data.drop(columns=['SortCode'])
    team_data.columns = ['Pilot', 'QP Rank', 'Games', 'Div (High)', 'Div (Last)', 'Div (Avg.)', 'Rating']

    df_height = 35 * (team_data.shape[0] + 1) + 3
    container.dataframe(team_data.style.format({'Rating': '{:.1f}'}, na_rep=''), hide_index=True, width='stretch', height=df_height)
    container.info(f'Confidence: {team_confidence:.0%} ({int(measurable.sum())} of {team_data.shape[0]} pilots measured)\n\n'
                   f'Division: {format_average(team_division)}\n\n'
                   f'Rating: {team_rating:.1f}')

    grouped_df = pilots_data.groupby('Division').agg({
        'MatchResult': [
            ('Total', 'count'),
            ('Wins', lambda x: (x == 'WIN').sum())
        ]
    }).droplevel(0, axis=1).reset_index()

    # Convert wide dataframe to a tall one
    tall_df = pd.melt(grouped_df,
                    id_vars=['Division'],
                    value_vars=['Total', 'Wins'],
                    var_name='Metric',
                    value_name='Count')
    
    chart = alt.Chart(tall_df, title='Games per division').mark_bar().encode(
        x=alt.X(f'Division:O', axis=alt.Axis(labelAngle=0), title=None),
        y=alt.Y('Count:Q', title=None).stack(None),
        color=alt.Color('Metric:N', legend=alt.Legend(title='Legend'))
    )
    container.altair_chart(chart, width='stretch')

def display_metrics(df):
    match_stats = df.groupby('MatchID')['MatchResult'].value_counts().reset_index()
    total_games = match_stats['count'].sum()
    total_wins = match_stats[match_stats['MatchResult'] == 'WIN']['count'].sum()
    total_losses = total_games - total_wins

    metrics = {
        'Games': total_games,
        'Wins': total_wins,
        'Losses': total_losses,
        'Winrate': f'{safe_division(total_wins, total_games):.0%}'
    }
    metrics_block(metrics)

def calculate_pilot_division(df):
    """The shared average division, read for one pilot's rows."""
    estimates = average_divisions(df, DIVISION_LETTERS)
    return float(estimates.iloc[0]) if not estimates.empty else np.nan

def format_division(division, df):
    """'A (25)' - the bracket and how many of the pilot's games he played in it."""
    return f'{division} ({nunique(filter_dataframe(df, "Division", division), "MatchID")})'

def format_average(division):
    if division is None or not np.isfinite(division):
        return '--'
    return f'{decode_division(division, DIVISION_LETTERS)} ({float(division):.2f})'

header()
display_inputs()
