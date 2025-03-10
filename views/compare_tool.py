import streamlit as st
import pandas as pd

from utility.requests import jarls_pilot_stats
from utility.methods import error, filter_dataframe, nunique
from utility.database import read_comp_data

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
        team1_pilots = [pilot.strip().lower() for pilot in team1.splitlines()]
        team2_pilots = [pilot.strip().lower() for pilot in team2.splitlines()]
        
        df = read_comp_data()
        col1, col2 = st.columns(2)
        
        display_stats(col1, team1_pilots, df)
        display_stats(col2, team2_pilots, df)

def display_stats(container, pilots, df):
    if not pilots:
        return
    
    pilots_data = df[df['Username'].str.lower().isin(pilots)]
    team_data = {
        'Pilot': [],
        'Rank': [],
        # 'Games': [],
        'CompGames': [],
        'HighestDiv': [],
        'HighestDivGames': [],
        'MostPlayedDiv': [],
        'MostPlayedDivGames': []
    }
    for pilot in pilots:
        pilot_stats = jarls_pilot_stats(pilot)
        if not pilot_stats:
            continue

        team_data['Pilot'].append(pilot_stats['PilotName'])
        team_data['Rank'].append(pilot_stats['Rank'])
        # team_data['Games'].append(pilot_stats['GamesPlayed'])

        pilot_data = pilots_data[pilots_data['Username'].str.lower() == pilot.lower()]
        comp_games = nunique(pilot_data, 'MatchID')
        team_data['CompGames'].append(comp_games)

        if comp_games:
            highest_div = pilot_data['Division'].min()
            team_data['HighestDiv'].append(highest_div)

            highest_div_games = nunique(filter_dataframe(pilot_data, 'Division', highest_div), 'MatchID')
            team_data['HighestDivGames'].append(highest_div_games)

            groupped_data = pilot_data.groupby('Division')['Division'].value_counts()
            team_data['MostPlayedDiv'].append(groupped_data.idxmax())
            team_data['MostPlayedDivGames'].append(int(groupped_data.max()))
        else:
            team_data['HighestDiv'].append("--")
            team_data['HighestDivGames'].append("--")
            team_data['MostPlayedDiv'].append("--")
            team_data['MostPlayedDivGames'].append("--")

    team_data = pd.DataFrame.from_dict(team_data).sort_values(by=['HighestDiv','CompGames','Rank'], ascending=[True, False, True])


    team_data.columns = ['Pilot', 'QP Rank', 'Games', 'Div (High)', 'Games (High)', 'Div (Avg)', 'Games (Avg)']

    df_height = 35 * (team_data.shape[0] + 1) + 3
    container.dataframe(team_data, hide_index=True, use_container_width=True, height=df_height)

back_button()
header()
display_inputs()
