import streamlit as st
import pandas as pd
import altair as alt
import numpy as np

from utility.requests import jarls_pilot_stats
from utility.methods import filter_dataframe, nunique, safe_division, unique
from utility.database import read_comp_data
from utility.blocks import metrics_block

COMP_DATA = read_comp_data()
AVERAGE_GAMES = COMP_DATA.groupby('Username')['Username'].value_counts().mean()
DIVISIONS = unique(COMP_DATA, 'Division').to_list()
DIVISION_DECODING = {i + 1:DIVISIONS[i] for i in range(len(DIVISIONS))}
DIVISION_ENCODING = {value:key for key, value in DIVISION_DECODING.items()}

def back_button():
    if st.button('< Back'):
        st.switch_page('views/admin.py')

def header():
    st.header('Compare Tool')

def display_inputs():
    col1, col2 = st.columns(2)
    team1 = col1.text_area('Team 1')
    team2 = col2.text_area('Team 2')

    if not st.button('Compare', use_container_width=True):
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
        'HighestDivGames': [],
        'AverageDiv': [],
        'Confidence': []
    }
    for pilot in pilots:
        pilot_stats = jarls_pilot_stats(pilot)
        
        pilot_data = pilots_data[pilots_data['Username'].str.lower() == pilot.lower()].copy()
        division, confidence = calculate_pilot_division(pilot_data)
        comp_games = nunique(pilot_data, 'MatchID')
        
        if pilot_stats:
            team_data['Pilot'].append(pilot_stats['PilotName'])
            team_data['Rank'].append(pilot_stats['Rank'])
        else:
            team_data['Pilot'].append(pilot)
            team_data['Rank'].append(0)
        team_data['CompGames'].append(comp_games)

        if comp_games:
            highest_div = pilot_data['Division'].min()
            team_data['HighestDiv'].append(highest_div)

            highest_div_games = nunique(filter_dataframe(pilot_data, 'Division', highest_div), 'MatchID')
            team_data['HighestDivGames'].append(highest_div_games)

            team_data['AverageDiv'].append(division)
            team_data['Confidence'].append(confidence)
        else:
            team_data['HighestDiv'].append('--')
            team_data['HighestDivGames'].append(0)
            team_data['AverageDiv'].append(0)
            team_data['Confidence'].append(0)

    team_data = pd.DataFrame.from_dict(team_data).sort_values(by=['HighestDiv','CompGames','Rank'], ascending=[True, False, True])
    team_division = team_data[team_data['AverageDiv'] > 0]['AverageDiv'].mean()
    team_confidence = team_data[team_data['Confidence'] > 0]['Confidence'].mean()

    team_data['AverageDiv'] = [decode_division(value) for value in team_data['AverageDiv']]
    team_data['Confidence'] = round(100 * team_data['Confidence'], 1)
    team_data.columns = ['Pilot', 'QP Rank', 'Games', 'Div (High)', 'Games (High)', 'Div (Avg)', 'Conf.']

    df_height = 35 * (team_data.shape[0] + 1) + 3
    container.dataframe(team_data, hide_index=True, use_container_width=True, height=df_height)
    container.info(f'Division: {decode_division(team_division)} ({float(team_division):.2})\n\nConfidence: {team_confidence:.1%}')

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
    container.altair_chart(chart, use_container_width=True)

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
    special_divisions = ['S', 'Swiss']
    groupped_data = df[~df['Division'].isin(special_divisions)].groupby(['Tournament', 'Division'], sort=False).agg(
        Games=('MatchID', 'count'),
        Losses=('MatchResult', lambda x: (x == 'LOSS').sum())
    ).reset_index()

    total_games = groupped_data['Games'].sum()
    groupped_data['Lossrate'] = groupped_data['Losses'] / groupped_data['Games']
    groupped_data['Weight'] = groupped_data['Games'] / total_games
    groupped_data['Division'] = [DIVISION_ENCODING[label] for label in groupped_data['Division']]

    groupped_data['AdjustedWeight'] = groupped_data['Weight'] * weights_range(0.8, 1.2, groupped_data.shape[0]) if groupped_data.shape[0] > 2 else groupped_data['Weight']
    average_division = ((groupped_data['Division'] + 2 * (groupped_data['Lossrate'] - 0.5)) * groupped_data['AdjustedWeight']).sum()

    confidence = min(1.0, float(total_games) / AVERAGE_GAMES)

    return average_division, confidence

def weights_range(start, stop, count):
    return np.linspace(start, stop, num=count)

def decode_division(division):
    return DIVISION_DECODING[int(round(division))] if division > 0 else "--"

header()
display_inputs()
