"""Ranking data shared by the ladder and the players page.

Both pages need the same numbers - the rating a pilot carries now, where it was
earned, and how the most recent tournament moved it - so they are derived here
once instead of in each page. Filters are never part of it: a rating belongs to
the whole database, not to the tournament currently on screen.
"""

import pandas as pd
import streamlit as st

from utility.admission import eligible_pilots
from utility.caching import CACHE_TTL
from utility.database import read_comp_data
from utility.globals import RATING_BASE


@st.cache_data(ttl=CACHE_TTL)
def pilot_ratings():
    """One row per pilot in the whole database, ranked or not."""
    df = read_comp_data().sort_values(['Username', 'CompleteTime'])
    games = df.groupby('Username')['MatchID'].nunique()
    tournaments = df.groupby('Username')['Tournament'].nunique()
    latest = df.groupby('Username').tail(1).set_index('Username')

    # Net effect of the most recent tournament, not of the last game: the rating
    # after it minus the rating carried into its first game (RATING_BASE on a
    # debut). Last-game deltas are noise - median |d| 0.37 against 1.32 here.
    df['PrevRating'] = df.groupby('Username')['PilotRating'].shift(1)
    last_tournament = df.groupby('Username')['Tournament'].last()
    before_last = df[df['Tournament'] == df['Username'].map(last_tournament)] \
        .groupby('Username').head(1).set_index('Username')['PrevRating']

    table = pd.DataFrame({
        'Pilot': latest.index,
        'Games': latest.index.map(games),
        'Tournaments': latest.index.map(tournaments),
        'Rating': latest['PilotRating'],
        'Tournament': latest['Tournament'],
        'Division': latest['Division'],
        'Team': latest['TeamName'],
        'LastPlayed': latest['CompleteTime'],
    })
    table['Change'] = table['Rating'] - table['Pilot'].map(before_last).fillna(RATING_BASE)

    return table.reset_index(drop=True)


@st.cache_data(ttl=CACHE_TTL)
def ladder_data():
    """The ranked pilots: admission applied, ordered by rating, numbered."""
    ladder = pilot_ratings()
    ladder = ladder[ladder['Pilot'].isin(eligible_pilots())]
    ladder = ladder.sort_values(['Rating', 'Pilot'], ascending=[False, True], ignore_index=True)
    ladder.insert(0, 'Rank', range(1, len(ladder) + 1))

    return ladder[['Rank', 'Pilot', 'Games', 'Rating', 'Change', 'Tournament', 'Division']]


def current_ratings():
    """Pilot -> the rating they carry now, for merging into a filtered table."""
    return pilot_ratings()[['Pilot', 'Rating']]
