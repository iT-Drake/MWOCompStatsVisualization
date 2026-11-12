import streamlit as st

from utility.admission import MIN_GAMES, ACTIVE_DAYS, eligible_pilots
from utility.database import read_comp_data
from utility.blocks import filters_block
from utility.methods import safe_division
from utility.globals import get_leaderboard_size, get_leaderboard_default_sorting, get_leaderboard_aggregation_method
from utility.enums import SortingOption, AggregationMethod
from utility.ranking import current_ratings

SORT_KEY = 'leaderboard_sorting'
PAGE_KEY = 'page_number'

def current_sorting():
    # Read before the control is drawn, so the control can sit anywhere on the page.
    if SORT_KEY not in st.session_state:
        st.session_state[SORT_KEY] = get_leaderboard_default_sorting()
    return st.session_state[SORT_KEY]

def reset_page():
    # Changing the filters or the sorting moves the view back to the first page.
    st.session_state[PAGE_KEY] = 0

def header():
    st.header('Stats')

def prepare_data():
    """
    The frame every filter reads from: only pilots who qualify, counted on the whole
    database. Cut here rather than after the stats so the Team and Player options cannot
    offer a pilot the table would then drop.
    """
    df = read_comp_data()

    return df[df['Username'].isin(eligible_pilots())]

def filters():
    df = prepare_data()
    options = {'Tournament': None, 'Division': None, 'Class': 'Class', 'TeamName': 'Team', 'Username': 'Player'}
    return filters_block(df, options, on_change=reset_page)

def get_sorting_settings(value):
    match value:
        case SortingOption.WLR: return ['WLR', 'Games', 'MS'], [False, False, False]
        case SortingOption.Damage: return ['DMG', 'Games', 'MS'], [False, True, False]
        case SortingOption.Kills: return ['Kills', 'Games', 'MS'], [False, True, False]
        # Deaths is the only column where a high value is bad, so it is read the other
        # way: fewest first. Every other option puts the better number on top.
        case SortingOption.Deaths: return ['Deaths', 'Games', 'MS'], [True, False, False]
        case SortingOption.KDR: return ['KDR', 'Games', 'MS'], [False, True, False]
        case SortingOption.Games: return ['Games', 'MS', 'Kills'], [False, False, False]
        case SortingOption.Rating: return ['Rating', 'Games', 'MS'], [False, False, False]
        case _: return ['MS', 'Games'], [False, True]

def calculate_wlr(values):
    return safe_division(values.eq('WIN').sum(), values.eq('LOSS').sum())

def calculate_kdr(dividend, divisor):
    # Returning dividend if divisor is equal to zero.
    return dividend.div(divisor).where(divisor > 0, dividend)

def get_page_number(last_page):
    page_number = st.session_state.get(PAGE_KEY, 0)

    if page_number > last_page:
        page_number = 0

    return page_number

def set_page_number(new_value):
    st.session_state[PAGE_KEY] = new_value

def aggregation_method():
    match get_leaderboard_aggregation_method():
        case AggregationMethod.Sum: return 'sum'
        case _: return 'mean'

def pilots_data(df, method):
    df['Deaths'] = (df['HealthPercentage'] == 0).astype(int)
    pilot_stats = df.groupby(['Username'], as_index=False).agg(
        Tonnage=('Tonnage', 'mean'),
        MS=('MatchScore', method),
        Kills=('Kills', method),
        KMDDs=('KillsMostDamage', method),
        Assists=('Assists', method),
        CD=('ComponentsDestroyed', method),
        Deaths=('Deaths', method),
        DMG=('Damage', method),
        TD=('TeamDamage', method),
        WLR=('MatchResult', lambda values: calculate_wlr(values)),
        TotalKills=('Kills', 'sum'),
        TotalDeaths=('Deaths', 'sum'),
        Games=('MatchID','nunique'),
    ).rename(columns={'Username': 'Pilot'})

    pilot_stats['KDR'] = calculate_kdr(pilot_stats['TotalKills'], pilot_stats['TotalDeaths'])
    
    return pilot_stats

def leaderboard(df):
    method = aggregation_method()
    sorting = current_sorting()

    pilot_stats = pilots_data(df, method)
    pilot_stats = pilot_stats.merge(current_ratings(), on='Pilot', how='left')

    page_size = get_leaderboard_size()
    last_page = max((pilot_stats.shape[0] - 1) // page_size, 0)
    page_number = get_page_number(last_page)
    sorting_columns, sorting_order = get_sorting_settings(sorting)

    col1, col2, col3, col4, col5 = st.columns([3, 2, 1, 1, 1])
    with col1:
        with st.popover("Column descriptions:", width='stretch'):
            st.markdown('''
                - `Tonnage`: Average mech tonnage
                - `MS`: Match Score (avg.)
                - `Kills`: Kills (avg.)
                - `KMDDs`: Kills Most Damage Dealt (avg.)
                - `Assists`: Assists (avg.)
                - `CDs`: Components Destroyed (avg.)
                - `Deaths`: Deaths (avg.)
                - `KDR`: Kills to Deaths ratio
                - `DMG`: Damage Dealt (avg.)
                - `TD`: Team Damage (avg.)
                - `WLR`: Wins to Losses ratio
                - `Games`: Total games played
                - `Rating`: Current rating, whole database, filters do not change it
            ''')

    with col2:
        st.selectbox('Sorting column', list(SortingOption), key=SORT_KEY, format_func=str,
                     on_change=reset_page, label_visibility='collapsed')

    with col3:
        if st.button("Previous", width='stretch'):
            if page_number - 1 < 0:
                page_number = last_page
            else:
                page_number -= 1

    with col5:
        if st.button("Next", width='stretch'):
            if page_number + 1 > last_page:
                page_number = 0
            else:
                page_number += 1

    set_page_number(page_number)
    
    with col4:
        st.markdown(f'<p style="text-align:center;">{page_number + 1} / {last_page + 1}</p>', unsafe_allow_html=True)
    
    start_idx = page_number * page_size 
    end_idx = (1 + page_number) * page_size
    
    pilot_stats = pilot_stats.sort_values(sorting_columns, ascending=sorting_order, ignore_index=True).iloc[start_idx:end_idx]
    
    df_height = 35 * (pilot_stats.shape[0] + 1) + 3
    pilot_stats = pilot_stats.style.format(subset=['Tonnage', 'MS', 'Kills', 'KMDDs', 'Assists', 'CD', 'Deaths', 'DMG', 'TD', 'WLR', 'KDR', 'Rating'], formatter="{:.2f}")

    column_order = ['Pilot', 'Tonnage', 'MS', 'Kills', 'KMDDs', 'Assists', 'CD', 'Deaths', 'KDR', 'DMG', 'TD', 'WLR', 'Games', 'Rating']
    st.dataframe(pilot_stats, hide_index=True, column_order=column_order, width='stretch', height=df_height)

header()
df, options = filters()
leaderboard(df)
