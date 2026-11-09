import streamlit as st
import pandas as pd

from utility.admission import ACTIVE_DAYS, MIN_GAMES, eligible_pilots
from utility.caching import CACHE_TTL
from utility.database import read_comp_data
from utility.blocks import filters_block
from utility.globals import get_leaderboard_size, RATING_BASE

# Admission to the ladder: a pilot needs games behind the rating and has to
# still be playing. Both are measured on the whole database, not on the filters.

PAGE_KEY = 'ladder_page'
FIND_KEY = 'ladder_pilot'

def reset_page():
    st.session_state[PAGE_KEY] = 0

def header():
    st.header('Ladder')
    st.caption(f'Ranked by rating. A pilot qualifies with at least {MIN_GAMES} games '
               f'and a match in the last {ACTIVE_DAYS // 365} years.')

def filters():
    df = read_comp_data()
    options = {'Tournament': None, 'Division': None}
    return filters_block(df, options, on_change=reset_page)

@st.cache_data(ttl=CACHE_TTL)
def ladder_data():
    """
    One row per qualifying pilot: the rating they carry now, how their most
    recent tournament moved it, and which tournament that was.
    """
    df = read_comp_data().sort_values(['Username', 'CompleteTime'])
    games = df.groupby('Username')['MatchID'].nunique()
    latest = df.groupby('Username').tail(1).set_index('Username')

    # Net effect of the most recent tournament: the rating after it minus the
    # rating the pilot carried into its first game. A debut starts from the
    # rating base, so a first tournament reports what it was worth.
    df['PrevRating'] = df.groupby('Username')['PilotRating'].shift(1)
    last_tournament = df.groupby('Username')['Tournament'].last()
    before_last = df[df['Tournament'] == df['Username'].map(last_tournament)] \
        .groupby('Username').head(1).set_index('Username')['PrevRating']

    ladder = pd.DataFrame({
        'Pilot': latest.index,
        'Games': latest.index.map(games),
        'Rating': latest['PilotRating'],
        'Tournament': latest['Tournament'],
        'Division': latest['Division'],
    })
    ladder['Change'] = ladder['Rating'] - ladder['Pilot'].map(before_last).fillna(RATING_BASE)

    ladder = ladder[ladder['Pilot'].isin(eligible_pilots())]
    ladder = ladder.sort_values(['Rating', 'Pilot'], ascending=[False, True], ignore_index=True)
    ladder.insert(0, 'Rank', range(1, len(ladder) + 1))

    return ladder[['Rank', 'Pilot', 'Games', 'Rating', 'Change', 'Tournament', 'Division']]

def page_count(rows, page_size):
    # A full last page must not produce an empty page after it.
    return max((rows - 1) // page_size, 0)

def change_color(value):
    if value > 0:
        return 'color: #1a7f37'
    if value < 0:
        return 'color: #c0392b'
    return ''

def ladder_table(view, selected):
    def highlight(row):
        if row['Pilot'] == selected:
            return ['background-color: rgba(255, 193, 7, 0.20)'] * len(row)
        return [''] * len(row)

    styler = view.style.format({'Rating': '{:.2f}', 'Change': '{:+.2f}'})
    styler = styler.map(change_color, subset=['Change'])
    if selected:
        styler = styler.apply(highlight, axis=1)

    height = 35 * (view.shape[0] + 1) + 3

    st.dataframe(
        styler,
        hide_index=True,
        width='stretch',
        height=height,
        column_order=['Rank', 'Pilot', 'Games', 'Rating', 'Change', 'Tournament', 'Division'],
        column_config={
            'Change': st.column_config.Column('Last change', help='Rating change over the most recent tournament'),
            'Tournament': st.column_config.Column('Last tournament played'),
            'Games': st.column_config.Column('Games', help='Total games played, whole database'),
            'Division': st.column_config.Column('Division', help='Division of the most recent tournament'),
        },
    )

def ladder_page():
    ladder = ladder_data()
    page_size = get_leaderboard_size()

    df, options = filters()

    view = ladder
    if any(options.values()):
        pilots = set(df['Username'])
        view = ladder[ladder['Pilot'].isin(pilots)].reset_index(drop=True)

    last_page = page_count(view.shape[0], page_size)
    page_number = min(st.session_state.get(PAGE_KEY, 0), last_page)

    column_find, column_controls = st.columns(2, vertical_alignment='center')
    with column_find:
        selected = st.selectbox('Find pilot', ladder['Pilot'], index=None, key=FIND_KEY,
                                placeholder='Find a player on the ladder',
                                label_visibility='collapsed')

    with column_controls:
        action_find, action_previous, action_page, action_next = st.columns(
            [1, 1, 1, 1], vertical_alignment='center')

        with action_find:
            # A button, not on_change: the same pilot can be looked up again after
            # browsing away, and selecting the same value does not fire a callback.
            jump = st.button('Find', width='stretch')

        with action_previous:
            if st.button('Previous', width='stretch'):
                page_number = last_page if page_number - 1 < 0 else page_number - 1

        with action_next:
            if st.button('Next', width='stretch'):
                page_number = 0 if page_number + 1 > last_page else page_number + 1

    if jump and selected:
        position = view.index[view['Pilot'] == selected]
        if len(position):
            page_number = int(position[0]) // page_size

    # Drawn after the jump so the number always belongs to the page being shown.
    with action_page:
        st.markdown(f'<p style="text-align:center;">{page_number + 1} / {last_page + 1}</p>', unsafe_allow_html=True)

    st.session_state[PAGE_KEY] = page_number

    if selected:
        pilot = ladder[ladder['Pilot'] == selected]
        if pilot.empty:
            st.info(f'{selected} is not on the ladder.')
        else:
            row = pilot.iloc[0]
            st.markdown(f'**#{row["Rank"]}** of {len(ladder)} · {row["Rating"]:.2f} rating '
                        f'({row["Change"]:+.2f} last tournament) · {row["Tournament"]}')
            if row['Pilot'] not in set(view['Pilot']):
                st.info(f'{selected} is outside the current filters.')

    start_idx = page_number * page_size
    end_idx = (1 + page_number) * page_size

    ladder_table(view.iloc[start_idx:end_idx], selected)

header()
ladder_page()
