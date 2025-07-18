import requests
import pandas as pd
from time import sleep
from streamlit import cache_data

from utility.datasources import mech_data, roster_links, team_rosters
from utility.database import unique_match_ids, write_comp_data
from utility.methods import error, convert_to_int
from utility.globals import API_URL, API_KEY

#---------------------------------------------------------------------
# MWO API
#---------------------------------------------------------------------

def match_data_columns():
    return ['MatchID', 'Tournament', 'Division', 'Map', 'WinningTeam', 'Team1Score', 'Team2Score', 'MatchDuration', 'CompleteTime', 'MatchResult', 'Score',
        'Username', 'Team', 'TeamName', 'Lance', 'MechItemID', 'Mech', 'Chassis', 'Tonnage', 'Class', 'Type',
        'HealthPercentage', 'Kills', 'KillsMostDamage', 'Assists', 'ComponentsDestroyed', 'MatchScore', 'Damage', 'TeamDamage']

def new_record(data):
    id = data['id']
    tournament = data['tournament']
    division = data['division']
    pilot = data['pilot']
    team = data['team']
    mech = data['mech']
    match = data['match']
    details = data['details']

    new_record = {}
    new_record['MatchID'] = id
    new_record['Tournament'] = tournament
    new_record['Division'] = division
    new_record['Map'] = match['Map']
    new_record['WinningTeam'] = match['WinningTeam']
    new_record['Team1Score'] = match['Team1Score']
    new_record['Team2Score'] = match['Team2Score']
    new_record['MatchDuration'] = match['MatchDuration']
    new_record['CompleteTime'] = match['CompleteTime']
    new_record['MatchResult'] = 'WIN' if details['Team'] == match['WinningTeam'] else 'LOSS'
    new_record['Score'] = 1 if details['Team'] == match['WinningTeam'] else -1
    new_record['Username'] = pilot
    new_record['Team'] = details['Team']
    new_record['TeamName'] = team
    new_record['Lance'] = details['Lance']
    new_record['MechItemID'] = mech['ID']
    new_record['Mech'] = mech['Mech']
    new_record['Chassis'] = mech['Chassis']
    new_record['Tonnage'] = mech['Tonnage']
    new_record['Class'] = mech['Class']
    new_record['Type'] = mech['Type']
    new_record['HealthPercentage'] = details['HealthPercentage']
    new_record['Kills'] = details['Kills']
    new_record['KillsMostDamage'] = details['KillsMostDamage']
    new_record['Assists'] = details['Assists']
    new_record['ComponentsDestroyed'] = details['ComponentsDestroyed']
    new_record['MatchScore'] = details['MatchScore']
    new_record['Damage'] = details['Damage']
    new_record['TeamDamage'] = details['TeamDamage']

    return new_record

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

        data = {
            'id': id,
            'tournament': tournament,
            'division': division,
            'pilot': pilot,
            'team': team,
            'mech': mech,
            'match': match_details,
            'details': line
        }
        new_line = new_record(data)
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
    # Removing duplicate IDs
    match_ids = list(dict.fromkeys(match_ids))

    unique_ids = unique_match_ids()

    for match_id in match_ids:
        id = convert_to_int(match_id)
        if not id or id in unique_ids:
            continue

        df = request_match_data(match_id, tournament)
        write_comp_data(df)

        unique_ids.append(id)

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

#---------------------------------------------------------------------
# JARL'S LIST API
#---------------------------------------------------------------------

def jarls_pilot_overview_link(pilot):
    return f"https://leaderboard.isengrim.org/search?u={pilot.replace(' ', '+')}"

@cache_data(ttl=300)
def jarls_pilot_stats(pilot):
    url = f'https://leaderboard.isengrim.org/api/usernames/{pilot}'
    result = {}
    try:
        response = requests.get(url)
        if response.status_code == 200:
            result = response.json()
            if not result['Rank']:
                last_season_url = f"https://leaderboard.isengrim.org/api/usernames/{pilot}/seasons/{result['LastSeason']}"
                response = requests.get(last_season_url)
                if response.status_code == 200:
                    result = response.json()
                else:
                    error(f"Error fetching pilot's last season details: {pilot}\nCode={response.status_code},Text={response.text}") 
        else:
            if response.status_code == 404:
                error(f"Pilot {pilot} was not found on Jarl's list.")
            else:
                error(f"Error fetching pilot stats for: {pilot}\nCode={response.status_code},Text={response.text}")
    except Exception as e:
        error(f"Error fetching pilot stats for: {pilot}\n{e}")

    return result
