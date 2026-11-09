import streamlit as st

from utility.caching import CACHE_TTL
from utility.database import read_comp_data

# A gap longer than this between two consecutive drops of the same pairing starts a new match.
# No pairing in the database has a maximum gap between 2 h and 5 h, so the exact value is not
# a knife edge. See tools/match-splitting-notes.md.
MATCH_GAP_MINUTES = 300

#---------------------------------------------------------------------
# NAMING
#---------------------------------------------------------------------

def team_label(signature):
    """Readable team name for a side signature."""
    if isinstance(signature, str):
        return signature

    if not len(signature):
        return 'Unknown team'

    return ' + '.join(signature)

def side_signatures(df):
    """
    One signature per side: the roster names that the whole database uses more than once.

    A side is normally a single roster name. A TOC25 10v10 side is a coalition of two or
    three rosters, so its signature is a tuple. A name used exactly once is a one-off roster
    tag and is dropped, which is what stops a stray tag from renaming a whole side.

    The majority name is not safe here: a coalition has no majority, so the tie is arbitrary
    and flips between drops, which invents rematches that never happened.
    """
    frequency = df['TeamName'].value_counts()

    signature = df.groupby(['MatchID', 'Team'])['TeamName'].apply(
        lambda names: tuple(sorted({name for name in names if frequency[name] > 1})))

    return signature

#---------------------------------------------------------------------
# GROUPING
#---------------------------------------------------------------------

@st.cache_data(ttl=CACHE_TTL)
def drop_index():
    """
    One row per drop, carrying the match it belongs to.

    A match is the run of drops between the same two sides without a gap longer than
    MATCH_GAP_MINUTES. Duel stages (1v1, 2v2, 4v4) belong to the match that follows them and
    are grouped with it whenever they were played in the same session.

    `MatchKey` is an integer that is only stable while the database is unchanged, so resolve
    it from a `MatchID` at render time instead of storing it.
    """
    df = read_comp_data()

    signature = side_signatures(df).unstack()
    signature.columns = ['Signature1', 'Signature2']

    size = df.groupby(['MatchID', 'Team']).size().unstack()
    size.columns = ['Size1', 'Size2']

    index = df.groupby('MatchID').agg(
        Tournament=('Tournament', 'first'),
        Division=('Division', 'first'),
        Map=('Map', 'first'),
        Time=('CompleteTime', 'first'),
        Score1=('Team1Score', 'first'),
        Score2=('Team2Score', 'first'),
        WinningTeam=('WinningTeam', 'first'),
        Duration=('MatchDuration', 'first')
    )
    index = index.join(signature).join(size)
    index['Duration'] = index['Duration'].astype(int)
    index['Pair'] = [tuple(sorted((first, second))) for first, second in zip(index['Signature1'], index['Signature2'])]

    # `Team` is the map side, so the winner has to be resolved to the side's signature before
    # it means anything: the two teams swap sides between drops.
    index['WinnerSignature'] = index['Signature1'].where(
        index['WinningTeam'] == '1',
        index['Signature2'].where(index['WinningTeam'] == '2', None))

    # Sorted by time only: grouping preserves the row order inside a group, so the gap is
    # always measured against the previous drop of the same pairing.
    ordered = index.sort_values('Time')
    gap = ordered.groupby(['Tournament', 'Pair'])['Time'].diff().dt.total_seconds().div(60)
    session = (gap.isna() | (gap > MATCH_GAP_MINUTES)).groupby([ordered['Tournament'], ordered['Pair']]).cumsum()
    ordered['MatchKey'] = ordered.groupby([ordered['Tournament'], 'Pair', session], sort=False).ngroup()

    return ordered.sort_index()

#---------------------------------------------------------------------
# SELECTING A PAIRING
#---------------------------------------------------------------------

def divisions_in(index, tournament):
    """Every division the tournament used, alphabetically."""
    part = index[index['Tournament'] == tournament]

    return sorted(part['Division'].dropna().unique())

def teams_in(index, tournament, division=None):
    """Every side signature that played in the tournament (or in one of its divisions)."""
    part = index[index['Tournament'] == tournament]
    if division is not None:
        part = part[part['Division'] == division]

    teams = set(part['Signature1']) | set(part['Signature2'])

    return sorted(teams, key=team_label)

def opponents_of(index, tournament, signature, division=None):
    """Every side signature that met the given one in the tournament (or one of its divisions)."""
    part = index[index['Tournament'] == tournament]
    if division is not None:
        part = part[part['Division'] == division]

    home = part.loc[part['Signature1'] == signature, 'Signature2']
    away = part.loc[part['Signature2'] == signature, 'Signature1']

    return sorted(set(home) | set(away), key=team_label)

def pair_drops(index, tournament, first, second, division=None):
    """Every drop the two sides played against each other in the tournament, oldest first."""
    pair = tuple(sorted((first, second)))
    part = index[(index['Tournament'] == tournament) & (index['Pair'] == pair)]
    if division is not None:
        part = part[part['Division'] == division]

    return part.sort_values('Time')

#---------------------------------------------------------------------
# SIDES
#---------------------------------------------------------------------

def rows_with_signature(drop_ids):
    """
    Pilot rows of the given drops, with the signature of the side each pilot played for.

    The `Team` column is the map side a pilot started on ('1' or '2'), not the team, so a
    pilot who is on side 2 in one drop and side 1 in the next would be counted for two
    different teams by `Team` alone.
    """
    df = read_comp_data()
    rows = df[df['MatchID'].isin(drop_ids)].copy()

    sides = drop_index()[['Signature1', 'Signature2']]
    rows = rows.merge(sides, left_on='MatchID', right_index=True, how='left')
    rows['Signature'] = rows['Signature1'].where(rows['Team'] == '1', rows['Signature2'])

    return rows.drop(columns=['Signature1', 'Signature2'])

