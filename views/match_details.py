import streamlit as st
import pandas as pd

from utility.methods import error, parse_match_ids
from utility.requests import fetch_api_data
from utility.datasources import mech_data
from utility.blocks import metrics_block

from datetime import datetime

def header():
    st.header('API Data')

def spectators_block(spectators):
    if len(spectators) > 1:
        st.divider()

        columns = st.columns(len(spectators))
        index = 0
        for item in spectators:
            column = columns[index]
            column.subheader(item)
            index += 1

        st.divider()

def teams_block(teams, team1_score, team2_score):
    team1, team2 = st.columns(2)
    with team1:
        container = st.container(border=True)
        container.write(f'Team 1 score: {team1_score}')

    with team2:
        container = st.container(border=True)
        container.write(f'Team 2 score: {team2_score}')
        
    columns = st.columns(len(teams))
    index = 0
    for key, value in teams.items():
        column = columns[index]
        with column:
            df = pd.DataFrame(value)
            st.dataframe(df, hide_index=True, use_container_width=True)
        index += 1

def display_match_details(match_id):
    json_data = fetch_api_data(match_id)
    if not json_data:
        st.stop()

    match_details = json_data['MatchDetails']
    user_details = json_data['UserDetails']
    
    team1_score = match_details['Team1Score']
    team2_score = match_details['Team2Score']
    dur_min, dur_sec = divmod(int(match_details['MatchDuration']), 60)

    metrics = {
        'ID': match_id,
        'Map': match_details['Map'],
        'Mode': match_details['GameMode'],
        'Region': match_details['Region'],
        '': '',
        'Winner': f"Team {match_details['WinningTeam']}",
        'Date': datetime.fromisoformat(match_details['CompleteTime']).strftime("%Y-%m-%d %H:%M:%S"),
        'Duration': f"{dur_min:02d}:{dur_sec:02d}"
    }
    metrics_block(metrics, 4)

    mechs = mech_data()

    spectators = ['Spectators:']
    teams = {'1': [], '2': []}
    for line in user_details:
        if line['IsSpectator'] == True:
            spectators.append(line['Username'])
        else:
            mech = mechs[line['MechItemID']]['Mech'] if line['MechItemID'] else 'NONE'
            player = {
                "Tag": f"[{line['UnitTag']}]" if line['UnitTag'] else '',
                "Pilot": line['Username'],
                "Mech": mech,
                "Health": "DEAD" if line['HealthPercentage'] == 0 else f"{line['HealthPercentage']}%",
                "Score": line['MatchScore'],
                "Damage": line['Damage'],
                "Kills": line['Kills']
            }
            teams[line['Team']].append(player)

    spectators_block(spectators)
    teams_block(teams, team1_score, team2_score)

def display_inputs():
    match_ids = st.text_input('Enter match id', value=None, placeholder='Enter match ID', label_visibility='hidden')
    button_pressed = st.button('Submit', use_container_width=True)

    if button_pressed and not match_ids:
        error('Please, specify match ID to fetch data for.')
    elif button_pressed:
        id_list = parse_match_ids(match_ids)
        for match_id in id_list:
            display_match_details(match_id)

header()
display_inputs()
