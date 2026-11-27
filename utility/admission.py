from datetime import datetime, timedelta, timezone

import streamlit as st

from utility.caching import CACHE_TTL
from utility.database import read_comp_data

# Ladder and Stats leaderboard admission rule: more than 5 games, active in the past 2 years.
MIN_GAMES = 5
ACTIVE_DAYS = 730

# Career games tiers a viewer can narrow a table to.
GAMES_TIERS = [MIN_GAMES, 20, 50, 100, 200]

@st.cache_data(ttl=CACHE_TTL)
def eligible_pilots():
    """Every pilot with enough games and a match inside the active window."""
    df = read_comp_data()
    games = df.groupby('Username')['MatchID'].nunique()
    latest = df.groupby('Username')['CompleteTime'].max()
    cutoff = datetime.now(timezone.utc) - timedelta(days=ACTIVE_DAYS)

    return set(games[games >= MIN_GAMES].index.intersection(latest[latest > cutoff].index))
