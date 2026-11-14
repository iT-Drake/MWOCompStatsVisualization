import streamlit as st

from utility.admission import ACTIVE_DAYS, MIN_GAMES
from utility.database import read_comp_data
from utility.blocks import change_color, filters_block
from utility.documents import DOCS, expander_document
from utility.globals import get_leaderboard_size
from utility.ranking import ladder_data

# Admission to the ladder: a pilot needs games behind the rating and has to
# still be playing. Both are measured on the whole database, not on the filters.

PAGE_KEY = 'ladder_page'
FIND_KEY = 'ladder_pilot'

def reset_page():
    st.session_state[PAGE_KEY] = 0

def header():
    st.header('Ladder')

def filters():
    df = read_comp_data()
    options = {'Tournament': None, 'Division': None}
    return filters_block(df, options, on_change=reset_page)

def page_count(rows, page_size):
    # A full last page must not produce an empty page after it.
    return max((rows - 1) // page_size, 0)

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

def rating_document():
    """The rating article, folded away under the table."""
    document = DOCS / 'rating.md'
    if not document.is_file():
        return

    expander_document(document)

header()
rating_document()
ladder_page()
