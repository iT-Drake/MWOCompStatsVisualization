import requests
import pandas as pd
from time import sleep

from utility.datasources import mech_data, roster_links, team_rosters
from utility.database import unique_match_ids, write_comp_data
from utility.methods import error, convert_to_int
from utility.globals import API_URL, API_KEY

def match_data_columns():
    return ['MatchID', 'Tournament', 'Division', 'Map', 'WinningTeam', 'Team1Score', 'Team2Score', 'MatchDuration', 'CompleteTime', 'MatchResult', 'Score',
        'Username', 'Team', 'TeamName', 'Lance', 'MechItemID', 'Mech', 'Chassis', 'Tonnage', 'Class', 'Type',
        'HealthPercentage', 'Kills', 'KillsMostDamage', 'Assists', 'ComponentsDestroyed', 'MatchScore', 'Damage', 'TeamDamage']

def match_data(id, match_details, user_details, tournament):
    lines = []
    mechs = mech_data()
    all_rosters = roster_links()
    rosters = team_rosters(all_rosters[tournament])
    for line in user_details:
        if line['IsSpectator'] == True or line['MechItemID'] == 0:
            continue

        mech_id = line['MechItemID']
        pilot = line['Username']
        pilot_upper_case = pilot.upper()
        
        if mech_id not in mechs:
            raise Exception(f'Mech with id `{mech_id}` not found')
        mech = mechs[mech_id]
        
        if pilot_upper_case not in rosters:
            raise Exception(f"Pilot `{pilot}` not found. Mech: {mech['Mech']}. Team: {line['Team']}")
        pilot_data = rosters[pilot_upper_case]
        
        team = pilot_data['Team'].strip()
        if not team:
            raise Exception(f"Empty team on a roster for a pilot `{pilot}`")
        
        division = pilot_data['Division']
        if not division:
            raise Exception(f"Empty division on a roster for a pilot `{pilot}`")

        new_line = {}
        new_line['MatchID'] = id
        new_line['Tournament'] = tournament
        new_line['Division'] = division
        new_line['Map'] = match_details['Map']
        new_line['WinningTeam'] = match_details['WinningTeam']
        new_line['Team1Score'] = match_details['Team1Score']
        new_line['Team2Score'] = match_details['Team2Score']
        new_line['MatchDuration'] = match_details['MatchDuration']
        new_line['CompleteTime'] = match_details['CompleteTime']
        new_line['MatchResult'] = 'WIN' if line['Team'] == match_details['WinningTeam'] else 'LOSS'
        new_line['Score'] = 1 if line['Team'] == match_details['WinningTeam'] else -1
        new_line['Username'] = pilot
        new_line['Team'] = line['Team']
        new_line['TeamName'] = team
        new_line['Lance'] = line['Lance']
        new_line['MechItemID'] = mech_id
        new_line['Mech'] = mech['Mech']
        new_line['Chassis'] = mech['Chassis']
        new_line['Tonnage'] = mech['Tonnage']
        new_line['Class'] = mech['Class']
        new_line['Type'] = mech['Type']
        new_line['HealthPercentage'] = line['HealthPercentage']
        new_line['Kills'] = line['Kills']
        new_line['KillsMostDamage'] = line['KillsMostDamage']
        new_line['Assists'] = line['Assists']
        new_line['ComponentsDestroyed'] = line['ComponentsDestroyed']
        new_line['MatchScore'] = line['MatchScore']
        new_line['Damage'] = line['Damage']
        new_line['TeamDamage'] = line['TeamDamage']
        lines.append(new_line)
    
    return lines

def fetch_api_data(match_id):
    result = None

    url = API_URL.replace('%1', match_id).replace('%2', API_KEY)
    response = requests.get(url)
    if response.status_code == 200:
        result = response.json()
    else:
        error(f"Error fetching id={match_id}:\nCode={response.status_code},Text={response.text}")

    return result

def request_match_data(match_id, tournament):
    df = None

    try:
        json_data = fetch_api_data(match_id)
        if json_data:
            match_details = json_data['MatchDetails']
            user_details = json_data['UserDetails']
            data = match_data(match_id, match_details, user_details, tournament)
            df = pd.DataFrame(data)
            df.columns = match_data_columns()
    except requests.exceptions.JSONDecodeError as e:
        error(f"Error fetching id={match_id}:\n{e}")
    except Exception as e:
        error(f"Error fetching id={match_id}:\n{e}")
    
    if df is None:
        df = pd.DataFrame([], columns=match_data_columns())

    return df

def batch_request(match_ids, tournament):
    unique_ids = unique_match_ids()

    for match_id in match_ids:
        id = convert_to_int(match_id)
        if not id or id in unique_ids:
            continue

        df = request_match_data(match_id, tournament)
        write_comp_data(df)

        unique_ids.append(match_id)

        # API calls limited by 60 per minute
        sleep(1)

def mech_list():
    url = "https://static.mwomercs.com/api/mechs/list/dict.json"

    response = requests.get(url)
    if response.status_code == 200:
        json_data = response.json()
        result = json_data['Mechs']
    else:
        result = {'error': f"Error fetching mech list:\nCode={response.status_code},Text={response.text}"}

    return result
