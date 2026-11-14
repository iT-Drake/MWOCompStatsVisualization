import streamlit as st

from utility.database import read_comp_data
from utility.documents import DOCS, expander_document, markdown_document, patch_note_paths
from utility.methods import nunique
from utility.blocks import metrics_block

def header():
    st.header('Welcome to MWO Stats Tool!')

def general_statistics(df):
    # Metrics
    tournaments = nunique(df, 'Tournament')
    teams = nunique(df, 'TeamName')
    players = nunique(df, 'Username')
    games = nunique(df, 'MatchID')

    start_date = df['CompleteTime'].iloc[0].strftime("%Y-%m-%d") if df.size > 0 else "--/--/----"

    metrics = {
        'Tournaments': tournaments,
        'Teams': teams,
        'Players': players,
        'Games': games,
        'Tracking data since': f'{start_date}'
    }
    metrics_block(metrics)

    st.divider()

def patch_notes_block():
    """Newest release inline, the rest folded away once there are enough of them."""
    notes = patch_note_paths()
    if not notes:
        return

    st.header('What changed')

    # A couple of notes fit on the page; a pile of them does not.
    show_all = len(notes) < 5
    for position, path in enumerate(notes):
        if position == 0 or show_all:
            markdown_document(path, level='subheader')
        else:
            expander_document(path)

def introduction():
    page = DOCS / 'introduction.md'
    if not page.is_file():
        st.caption('Add `docs/introduction.md` to fill this section.')
        return

    st.divider()

    markdown_document(page)

df = read_comp_data()

header()
general_statistics(df)
patch_notes_block()
introduction()
