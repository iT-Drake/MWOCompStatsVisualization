import streamlit as st
import pandas as pd

from utility.methods import error, parse_match_ids
from utility.requests import fetch_api_data, new_record, match_data_columns
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

def display_match_details(id, details):
    match_details = details['MatchDetails']
    user_details = details['UserDetails']
    
    team1_score = match_details['Team1Score']
    team2_score = match_details['Team2Score']
    dur_min, dur_sec = divmod(int(match_details['MatchDuration']), 60)

    metrics = {
        'ID': id,
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
                "Kills": line['Kills'],
                "TD": line['TeamDamage']
            }
            teams[line['Team']].append(player)

    spectators_block(spectators)
    teams_block(teams, team1_score, team2_score)

def get_match_details(id_list):
    result = {}
    for match_id in id_list:
        json_data = fetch_api_data(match_id)
        if not json_data:
            st.stop()
        result[match_id] = json_data

    return result

def json2df(json_list):
    lines = []
    mechs = mech_data()

    for id, json_data in json_list.items():
        match_details = json_data['MatchDetails']
        user_details = json_data['UserDetails']
        for line in user_details:
            if line['IsSpectator'] == True or line['MechItemID'] == 0:
                continue

            mech_id = line['MechItemID']
            if mech_id not in mechs:
                raise Exception(f'Mech with id `{mech_id}` not found')
            mech = mechs[mech_id]

            data = {
                'id': id,
                'tournament': "",
                'division': "",
                'pilot': line['Username'],
                'team': "",
                'mech': mech,
                'match': match_details,
                'details': line
            }
            new_line = new_record(data)
            lines.append(new_line)
    
    df = pd.DataFrame(lines)
    df.columns = match_data_columns()
    return df

def download_button(details_list):
    df = json2df(details_list)
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download data as CSV",
        data=csv,
        file_name="data_dump.csv",
        mime='text/csv',
        type='primary',
        use_container_width=True
    )

def display_inputs():
    match_ids = st.text_input('Enter match id', value=None, placeholder='Enter match ID', label_visibility='hidden')
    button_pressed = st.button('Submit', use_container_width=True)

    if button_pressed and not match_ids:
        error('Please, specify match ID to fetch data for.')
    elif button_pressed:
        id_list = parse_match_ids(match_ids)
        details_list = get_match_details(id_list)
        download_button(details_list)
        for id, details in details_list.items():
            display_match_details(id, details)

header()
display_inputs()
