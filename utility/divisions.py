"""The average division a pilot's tournament history points at.

A pilot who played three tournaments in B and one in A sits somewhere between the
two. The number is a games-weighted mean of his divisions - renormalised, with the
older tournaments discounted - plus a term for how far above or below a 50 % win
rate he was inside that bracket. It answers "which bracket has he been playing"
without asking for a rating: it is built from division labels and results only, so
a rating recalculation never moves it.

S and Swiss are left out. They are mixed-roster events: a pilot with no experience
can be drafted into one, so placing there says nothing about the bracket he belongs
in - in one TOS26 division, 94 % and 18 % win rates sat side by side.

Both `views/compare_tool.py` and the ladder read the number from here, so the two
pages cannot disagree about the same pilot.
"""

import numpy as np
import pandas as pd
import streamlit as st

from utility.caching import CACHE_TTL
from utility.database import read_comp_data
from utility.methods import unique

SPECIAL_DIVISIONS = ['S', 'Swiss']

# Older tournaments count less. The ramp is applied on a pilot's *relative* position
# in his own history, so two tournaments and twenty get the same spread - that is
# what makes it work for a newcomer and a veteran without knowing which is which.
RECENCY_FROM, RECENCY_TO = 0.4, 1.6

# Each division owns half a bracket either side of its number, and the gap between
# two of them is split into the lower one's "-" and the upper one's "+":
# A [0.75, 1.25), A- [1.25, 1.50), B+ [1.50, 1.75), B [1.75, 2.25), ...
BRACKET_HALF = 0.25


def division_letters(df):
    """The ladder itself in strength order: A..I today, and a future J after I."""
    return [division for division in unique(df, 'Division') if division not in SPECIAL_DIVISIONS]


def average_divisions(df, letters):
    """Pilot -> the average division his history points at, as a Series.

    `letters` has to describe the whole database even when `df` is one
    pilot - a slice that starts at C would otherwise renumber the ladder and turn
    an E into a C. Returns an empty Series when nothing in `df` has a division.
    """
    cells = (
        df[~df['Division'].isin(SPECIAL_DIVISIONS)]
        .assign(Lost=lambda frame: (frame['MatchResult'] == 'LOSS').astype('int8'))
        .groupby(['Username', 'Tournament', 'Division'], sort=False)
        .agg(Games=('MatchID', 'size'), Losses=('Lost', 'sum'), Played=('CompleteTime', 'min'))
        .reset_index()
        .sort_values(['Username', 'Played', 'Division'])
    )
    if cells.empty:
        return pd.Series(dtype=float)

    codes = {letter: position + 1 for position, letter in enumerate(letters)}

    group = cells.groupby('Username', sort=False)
    names = cells['Username'].to_numpy()
    size = group['Games'].transform('size').to_numpy()
    position = group.cumcount().to_numpy()
    total = group['Games'].transform('sum').to_numpy()

    weight = cells['Games'].to_numpy(float) / total
    weight = weight * np.where(size > 2, RECENCY_FROM + (RECENCY_TO - RECENCY_FROM) * position / np.maximum(size - 1, 1), 1.0)
    # The ramp scales the weights without keeping them summing to 1, which inflates
    # the number by up to 60 %. Renormalise so it stays in division units.
    weight = weight / pd.Series(weight).groupby(names).transform('sum').to_numpy()

    value = (cells['Division'].map(codes).to_numpy(float)
             + 2 * (cells['Losses'].to_numpy(float) / cells['Games'].to_numpy(float) - 0.5))

    return pd.Series(weight * value, index=cells.index).groupby(names).sum()


def decode_division(value, letters):
    """Turn the average division back into a bracket.

    Below A's band is "A+" (better than the top bracket there is)
    and past I's is "I-" (worse than the bottom one).
    """
    if value is None or not np.isfinite(value):
        return '--'

    if value < 1 - BRACKET_HALF:
        return f'{letters[0]}+'
    if value >= len(letters) + BRACKET_HALF:
        return f'{letters[-1]}-'

    band = int(np.floor(value + BRACKET_HALF))
    offset = value - band
    if offset < BRACKET_HALF:
        return letters[band - 1]
    if offset < 2 * BRACKET_HALF:
        return f'{letters[band - 1]}-'
    return f'{letters[band]}+'


@st.cache_data(ttl=CACHE_TTL)
def pilot_divisions():
    """Pilot -> bracket label over the whole database, for merging into a table.

    Describes the whole database. The same number has to survive a Tournament or Division filter.
    """
    df = read_comp_data()
    letters = division_letters(df)

    return average_divisions(df, letters).apply(lambda value: decode_division(value, letters))
