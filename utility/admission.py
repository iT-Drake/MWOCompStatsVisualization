from datetime import datetime, timedelta, timezone

import streamlit as st

from utility.caching import CACHE_TTL
from utility.database import read_comp_data

# Admission to the ladder and to the leaderboard: a pilot needs games behind the numbers and
# has to still be playing. Both are measured on the whole database, never on the filters, so
# the two pages list the same population.
MIN_GAMES = 5
ACTIVE_DAYS = 730

@st.cache_data(ttl=CACHE_TTL)
def eligible_pilots():
    """Every pilot with enough games and a match inside the active window."""
    df = read_comp_data()
    games = df.groupby('Username')['MatchID'].nunique()
    latest = df.groupby('Username')['CompleteTime'].max()
    cutoff = datetime.now(timezone.utc) - timedelta(days=ACTIVE_DAYS)

    return set(games[games >= MIN_GAMES].index.intersection(latest[latest > cutoff].index))
