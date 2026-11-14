"""Per weight-class baselines behind every percentile table.

Raw damage is 1.85x higher in assaults than in lights, so a percentile read off a
flat pool of pilots would rank a good light pilot by their tonnage. Baselines are
therefore per class, against pilots with at least `MIN_GAMES` games *in that
class*, which is the same admission rule the ladder applies per pilot.

The players page and the S.O.P.A. page both show these numbers, so the table is
built here once and each page decides which columns to render.
"""

import pandas as pd
import streamlit as st

from utility.admission import MIN_GAMES
from utility.caching import CACHE_TTL
from utility.database import read_comp_data

WEIGHT_CLASSES = ['LIGHT', 'MEDIUM', 'HEAVY', 'ASSAULT']

# Column order of the percentile table. Every one of them reads higher = better,
# which is why Survival is stored as 1 - death rate.
STATS = ['Kills', 'KMDDs', 'Assists', 'CD', 'DMG', 'MS', 'Survival']

@st.cache_data(ttl=CACHE_TTL)
def class_baselines():
    """Per pilot and weight class: per-game averages and the games behind them."""
    df = read_comp_data().assign(Deaths=lambda frame: (frame['HealthPercentage'] == 0).astype(int))

    baselines = df.groupby(['Class', 'Username']).agg(
        Games=('MatchID', 'nunique'),
        Kills=('Kills', 'mean'),
        KMDDs=('KillsMostDamage', 'mean'),
        Assists=('Assists', 'mean'),
        CD=('ComponentsDestroyed', 'mean'),
        DMG=('Damage', 'mean'),
        MS=('MatchScore', 'mean'),
        Deaths=('Deaths', 'mean'),
    )

    # Every column then reads higher = better, so the table has one direction.
    baselines['Survival'] = 1 - baselines['Deaths']

    return baselines.drop(columns='Deaths')[baselines['Games'] >= MIN_GAMES]

def class_percentiles(view):
    """One row per weight class in `view`: the averages ranked inside that class.

    Returns None when the scope holds no games at all. The cells are **strings**
    (`'84%'`, `'-'`), not floats with a Styler formatter: a dataframe renders a
    NaN cell as "None" whatever the formatter returns, and a class under
    `MIN_GAMES` games in this scope has to read as a dash.
    """
    if view.empty:
        return None

    baselines = class_baselines()
    classes = set(baselines.index.get_level_values('Class'))

    rows = []
    for klass in WEIGHT_CLASSES:
        games = view[view['Class'] == klass]
        if games.empty or klass not in classes:
            continue

        row = {'Class': klass, 'Games': len(games)}

        # One or two games are not a comparison: the class keeps its row so the
        # coverage is visible, but there is no percentile to read off it.
        if len(games) < MIN_GAMES:
            row.update({stat: '-' for stat in STATS})
            rows.append(row)
            continue

        pool = baselines.xs(klass, level='Class')
        own = {
            'Kills': games['Kills'].mean(),
            'KMDDs': games['KillsMostDamage'].mean(),
            'Assists': games['Assists'].mean(),
            'CD': games['ComponentsDestroyed'].mean(),
            'DMG': games['Damage'].mean(),
            'MS': games['MatchScore'].mean(),
            'Survival': 1 - (games['HealthPercentage'] == 0).mean(),
        }

        row.update({stat: f'{(pool[stat] < own[stat]).mean() * 100:.0f}%' for stat in STATS})
        rows.append(row)

    if not rows:
        return None

    return pd.DataFrame(rows)
