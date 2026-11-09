import streamlit as st
import pandas as pd

from utility.blocks import metrics_block
from utility.matches import (
    divisions_in, drop_index, opponents_of, pair_drops, rows_with_signature, team_label, teams_in)
from utility.methods import error

# The same green Streamlit uses for `:green[...]`, so a table cell and a markdown line match.
WINNER_COLOUR = '#09ab3b'

ALL_DIVISIONS = 'All divisions'

def header():
    st.header('Match details')

#---------------------------------------------------------------------
# FILTERS
#---------------------------------------------------------------------

def change_tournament():
    st.session_state['match_division'] = ALL_DIVISIONS
    st.session_state['match_team_first'] = None
    st.session_state['match_team_second'] = None

def change_division():
    st.session_state['match_team_first'] = None
    st.session_state['match_team_second'] = None

def change_team_first():
    st.session_state['match_team_second'] = None

def filters_block():
    """Tournament, Division, Team 1 and Team 2. The division is optional, the rest is required."""
    index = drop_index()
    tournaments = sorted(index['Tournament'].unique(), reverse=True)
    columns = st.columns(4)

    tournament = columns[0].selectbox(
        'Tournament', tournaments, index=None, placeholder='Tournament',
        label_visibility='collapsed', key='match_tournament', on_change=change_tournament)

    divisions = [ALL_DIVISIONS] + divisions_in(index, tournament)
    division = columns[1].selectbox(
        'Division', divisions, index=0, label_visibility='collapsed', key='match_division',
        on_change=change_division, disabled=tournament is None)
    if division == ALL_DIVISIONS:
        division = None

    teams = teams_in(index, tournament, division) if tournament else []
    first = columns[2].selectbox(
        'Team 1', teams, index=None, placeholder='Team 1', format_func=team_label,
        label_visibility='collapsed', key='match_team_first', on_change=change_team_first,
        disabled=tournament is None)

    opponents = opponents_of(index, tournament, first, division) if first else []
    second = columns[3].selectbox(
        'Team 2', opponents, index=None, placeholder='Team 2', format_func=team_label,
        label_visibility='collapsed', key='match_team_second', disabled=first is None)

    return index, tournament, first, second

#---------------------------------------------------------------------
# FORMATTING
#---------------------------------------------------------------------

def drops_label(count):
    return '1 drop' if count == 1 else f'{count} drops'

def tag_label(name):
    return f'[{name}]' if isinstance(name, str) and name else ''

def health_label(value):
    return 'DEAD' if value == 0 else f'{int(value)}%'

def table_height(rows):
    return 35 * (rows + 1) + 3

def winner_label(text, won):
    """Green when the side won the drop, plain otherwise."""
    return f':green[{text}]' if won else text

#---------------------------------------------------------------------
# DISPLAY
#---------------------------------------------------------------------

def drops_table(match, rows):
    """One row per drop, by map side: whoever played side 1 is on the left, side 2 on the right."""
    records = []

    for drop in match.to_dict('records'):
        pilots = rows[rows['MatchID'] == drop['Drop']]
        dead = pilots['HealthPercentage'] == 0

        records.append({
            'Map': drop['Map'],
            'Team 1': team_label(drop['Signature1']),
            'Kills 1': int((dead & (pilots['Team'] == '2')).sum()),
            'Score': f"{drop['Score1']} - {drop['Score2']}",
            'Kills 2': int((dead & (pilots['Team'] == '1')).sum()),
            'Team 2': team_label(drop['Signature2']),
            'Result': drop['WinningTeam'],
            'ID': str(drop['Drop'])
        })

    table = pd.DataFrame(records)

    def mark_winner(row):
        styles = [''] * len(row)
        if row['Result'] in ('1', '2'):
            column = 'Team 1' if row['Result'] == '1' else 'Team 2'
            styles[table.columns.get_loc(column)] = f'color: {WINNER_COLOUR}; font-weight: 600'

        return styles

    st.dataframe(
        table.style.apply(mark_winner, axis=1), hide_index=True, width='stretch',
        column_order=['Map', 'Team 1', 'Kills 1', 'Score', 'Kills 2', 'Team 2', 'ID'],
        column_config={'Kills 1': 'Kills', 'Kills 2': 'Kills', 'Result': None})

def pilots_table(pilots):
    table = pd.DataFrame({
        'Tag': pilots['TeamName'].map(tag_label),
        'Pilot': pilots['Username'],
        'Mech': pilots['Mech'],
        'Health': pilots['HealthPercentage'].map(health_label),
        'Score': pilots['MatchScore'],
        'Damage': pilots['Damage'],
        'Kills': pilots['Kills'],
        'TD': pilots['TeamDamage']
    })

    st.dataframe(
        table, hide_index=True, width='stretch', height=table_height(len(table)),
        column_order=['Tag', 'Pilot', 'Mech', 'Health', 'Score', 'Damage', 'Kills', 'TD'])

def drop_block(number, drop, rows):
    pilots = rows[rows['MatchID'] == drop['Drop']]
    winner = drop['WinningTeam']
    columns = st.columns([1, 1.6, 2, 1.4, 2])

    columns[0].subheader(f'Drop {number}')
    columns[1].subheader(drop['Map'])
    columns[2].subheader(winner_label(team_label(drop['Signature1']), winner == '1'))
    columns[3].subheader(f"{drop['Score1']} - {drop['Score2']}")
    columns[4].subheader(winner_label(team_label(drop['Signature2']), winner == '2'))

    left, right = st.columns(2)
    with left:
        pilots_table(pilots[pilots['Team'] == '1'])
    with right:
        pilots_table(pilots[pilots['Team'] == '2'])

def wins_for(match, signature):
    """Drops the signature won. A voided drop is nobody's win."""
    return int((match['WinnerSignature'] == signature).sum())

def match_block(number, match, rows, first, second):
    """Headed in filter order: Team 1 as you picked it, even where the sides below are swapped."""
    match = match.sort_values('Time')
    match['Drop'] = match.index
    wins = wins_for(match, first)
    losses = wins_for(match, second)
    date = match['Time'].iloc[0].strftime('%Y-%m-%d')

    columns = st.columns([1, 1.2, 2, 1, 2])
    columns[0].header(f'Match {number}')
    columns[1].header(date)
    columns[2].header(team_label(first))
    columns[3].header(f'{wins} - {losses}')
    columns[4].header(team_label(second))

    drops_table(match, rows)

    no_result = int(match['WinnerSignature'].isna().sum())
    if no_result:
        st.caption(f'{drops_label(no_result)} without a recorded winner, left out of the series score.')

    for position, drop in enumerate(match.to_dict('records'), start=1):
        drop_block(position, drop, rows)

    st.divider()

def pilot_table(rows):
    pilots = rows.groupby(['Signature', 'Username'], as_index=False).agg(
        Games=('MatchID', 'nunique'),
        Kills=('Kills', 'sum'),
        KMDDs=('KillsMostDamage', 'sum'),
        Assists=('Assists', 'sum'),
        CDs=('ComponentsDestroyed', 'sum'),
        DMG=('Damage', 'sum'),
        TD=('TeamDamage', 'sum'),
        MS=('MatchScore', 'mean'),
        Deaths=('Deaths', 'sum')
    )
    pilots['Team'] = pilots['Signature'].map(team_label)
    pilots = pilots.drop(columns=['Signature'])
    pilots = pilots.rename(columns={'Username': 'Pilot'}).sort_values(['Team', 'DMG'], ascending=[True, False])

    display = pilots.style.format(subset=['MS'], formatter='{:.2f}')
    height = table_height(pilots.shape[0])

    st.dataframe(
        display, hide_index=True, width='stretch', height=height,
        column_order=['Team', 'Pilot', 'Games', 'Kills', 'KMDDs', 'Assists', 'CDs', 'DMG', 'TD', 'MS', 'Deaths'])

def display_pair(index, tournament, first, second):
    drops = pair_drops(index, tournament, first, second)
    if drops.empty:
        error(f'`{team_label(first)}` did not meet `{team_label(second)}` in {tournament}.')
        return

    matches = list(drops.sort_values('Time').groupby('MatchKey', sort=False))

    series1 = sum(1 for _, match in matches if wins_for(match, first) > wins_for(match, second))
    series2 = sum(1 for _, match in matches if wins_for(match, second) > wins_for(match, first))
    tied = len(matches) - series1 - series2

    metrics = {
        'Matches': len(matches),
        'Drops': len(drops),
        'Series': f'{series1} - {series2}',
        'Last met': f"{drops['Time'].max():%Y-%m-%d}"
    }
    metrics_block(metrics, 4)

    if tied:
        noun = 'match' if tied == 1 else 'matches'
        st.caption(f'{tied} {noun} between them ended level on drops.')

    rows = rows_with_signature(drops.index)
    rows['Deaths'] = (rows['HealthPercentage'] == 0).astype(int)
    st.divider()

    for number, (_, match) in enumerate(matches, start=1):
        match_block(number, match, rows, first, second)

    st.markdown('**Pilot totals**')
    pilot_table(rows)

header()
index, tournament, first, second = filters_block()

if tournament is None or first is None or second is None:
    st.caption('Pick a tournament and the two teams to list every match they played against each other.')
else:
    display_pair(index, tournament, first, second)
