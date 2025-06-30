import streamlit as st
import numpy as np

from utility.database import read_comp_data
from utility.blocks import filters_block
from utility.methods import safe_division
from utility.globals import get_leaderboard_size, get_leaderboard_default_sorting, get_leaderboard_aggregation_method
from utility.enums import SortingOption, AggregationMethod

def header():
    st.header('Leaderboard')

def filters():
    df = read_comp_data()
    options = {'Tournament': None, 'Division': None, 'TeamName': 'Team', 'Username': 'Player'}
    return filters_block(df, options)

def get_sorting_settings():
    value = get_leaderboard_default_sorting()
    match value:
        case SortingOption.Score: return ['Score', 'Games', 'MS'], [False, True, False]
        case SortingOption.WLR: return ['WLR', 'Games', 'MS'], [False, False, False]
        case SortingOption.AdjustedWLR: return ['AWLR', 'Games', 'MS'], [False, False, False]
        case SortingOption.MatchScore: return ['MS', 'Games'], [False, True]
        case SortingOption.Damage: return ['DMG', 'Games', 'MS'], [False, True, False]
        case _: return ['Score', 'Games', 'MS'], [False, True, False]

def calculate_wlr(values):
    return safe_division(values.eq('WIN').sum(), values.eq('LOSS').sum())

def calculate_awlr(rating, games):
    WLR_Scale = 1/200
    return rating * (1 + games * WLR_Scale)

def calculate_kdr(dividend, divisor):
    result = dividend.div(divisor)
    inf_mask = np.isinf(result)
    result[inf_mask] = dividend[inf_mask]

    return result

def get_page_number(last_page):
    if 'page_number' not in st.session_state:
        page_number = 0
    else:
        page_number = st.session_state['page_number']

    if page_number > last_page:
        page_number = 0

    return page_number

def set_page_number(new_value):
    st.session_state['page_number'] = new_value

def pilots_data(df):
    value = get_leaderboard_aggregation_method()
    match value:
        case AggregationMethod.Mean: aggregation_method = 'mean'
        case AggregationMethod.Sum: aggregation_method = 'sum'
        case _: aggregation_method = 'mean'

    df['Deaths'] = np.where(df['HealthPercentage'] == 0, 1, 0)
    pilot_stats = df.groupby(['Username'], as_index=False).agg(
        Tonnage=('Tonnage', 'mean'),
        MS=('MatchScore', aggregation_method),
        Kills=('Kills', aggregation_method),
        KMDDs=('KillsMostDamage', aggregation_method),
        Assists=('Assists', aggregation_method),
        CD=('ComponentsDestroyed', aggregation_method),
        Deaths=('Deaths', aggregation_method),
        DMG=('Damage', aggregation_method),
        TD=('TeamDamage', aggregation_method),
        WLR=('MatchResult', lambda values: calculate_wlr(values)),
        TotalKills=('Kills', 'sum'),
        TotalDeaths=('Deaths', 'sum'),
        Games=('MatchID','nunique'),
        Score=('Score','sum')
    ).rename(columns={'Username': 'Pilot'})

    pilot_stats['KDR'] = calculate_kdr(pilot_stats['TotalKills'], pilot_stats['TotalDeaths'])
    pilot_stats['AWLR'] = calculate_awlr(pilot_stats['WLR'], pilot_stats['Games'])

    return pilot_stats

def leaderboard(df):
    pilot_stats = pilots_data(df)
    
    page_size = get_leaderboard_size()
    last_page = pilot_stats.shape[0] // page_size
    page_number = get_page_number(last_page)

    col1, _ , col2, col3, col4 = st.columns([4, 2, 1, 1, 1])
    with col1:
        with st.popover("Column descriptions:", use_container_width=True):
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
                - `AWLR`: Adjusted Wins to Losses ratio, gives slight advantage to whose who played more games preserving the same WLR. Calculated as WLR * (1 + Games / 200).
                - `Games`: Total games played
                - `Score`: Calculated by subtracting lost games from the games won
            ''')
    
    with col2:
        if st.button("Previous", use_container_width=True):
            if page_number - 1 < 0:
                page_number = last_page
            else:
                page_number -= 1

    with col4:
        if st.button("Next", use_container_width=True):
            if page_number + 1 > last_page:
                page_number = 0
            else:
                page_number += 1

    set_page_number(page_number)
    
    with col3:
        st.markdown(f'<p style="text-align:center;">{page_number + 1} / {last_page + 1}</p>', unsafe_allow_html=True)
    
    start_idx = page_number * page_size 
    end_idx = (1 + page_number) * page_size
    
    sorting_columns, sorting_order = get_sorting_settings()
    pilot_stats = pilot_stats.sort_values(sorting_columns, ascending=sorting_order, ignore_index=True).iloc[start_idx:end_idx]
    pilot_stats['Rank'] = pilot_stats.index + 1
    
    df_height = 35 * (pilot_stats.shape[0] + 1) + 3
    pilot_stats = pilot_stats.style.format(subset=['Tonnage', 'MS', 'Kills', 'KMDDs', 'Assists', 'CD', 'Deaths', 'DMG', 'TD', 'WLR', 'AWLR', 'KDR'], formatter="{:.2f}")

    column_order = ['Rank', 'Pilot', 'Tonnage', 'MS', 'Kills', 'KMDDs', 'Assists', 'CD', 'Deaths', 'KDR', 'DMG', 'TD', 'WLR', 'AWLR', 'Games', 'Score']
    st.dataframe(pilot_stats, hide_index=True, column_order=column_order, use_container_width=True, height=df_height)

header()
df, options = filters()
leaderboard(df)
