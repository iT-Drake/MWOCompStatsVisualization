import streamlit as st
import numpy as np

from utility.database import read_comp_data
from utility.blocks import filters_block
from utility.globals import get_leaderboard_size

def header():
    st.header('Leaderboard')

def filters():
    df = read_comp_data()
    options = {'Tournament': None, 'Division': None, 'TeamName': 'Team'}
    return filters_block(df, options)

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
    df['Deaths'] = np.where(df['HealthPercentage'] == 0, 1, 0)
    pilot_stats = df.groupby(['Username'], as_index=False).agg(
        Tonnage=('Tonnage','mean'),
        MS=('MatchScore','mean'),
        Kills=('Kills','mean'),
        KMDDs=('KillsMostDamage','mean'),
        Assists=('Assists','mean'),
        CD=('ComponentsDestroyed','mean'),
        Deaths=('Deaths','mean'),
        DMG=('Damage','mean'),
        TD=('TeamDamage','mean'),
        Games=('MatchID','nunique'),
        Score=('Score','sum')
    )

    return pilot_stats

def leaderboard(df):
    pilot_stats = pilots_data(df)
    
    page_size = get_leaderboard_size()
    last_page = pilot_stats.shape[0] // page_size
    page_number = get_page_number(last_page)

    col1, _ , col2, col3, col4 = st.columns([4, 2, 1, 1, 1])
    with col1:
        with st.expander("Column descriptions:"):
            st.markdown('''
                - `Tonnage`: Average mech tonnage
                - `MS`: Match Score (avg.)
                - `Kills`: Kills (avg.)
                - `KMDDs`: Kills Most Damage Dealt (avg.)
                - `Assists`: Assists (avg.)
                - `CDs`: Components Destroyed (avg.)
                - `Deaths`: Deaths (avg.)
                - `DMG`: Damage Dealt (avg.)
                - `TD`: Team Damage (avg.)
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
    
    pilot_stats = pilot_stats.sort_values(['Score', 'Games', 'MS'], ascending=[False, True, False], ignore_index=True).iloc[start_idx:end_idx]

    df_height = 35 * (pilot_stats.shape[0] + 1) + 3
    pilot_stats = pilot_stats.style.format(subset=['Tonnage', 'MS', 'Kills', 'KMDDs', 'Assists', 'CD', 'Deaths', 'DMG', 'TD'], formatter="{:.2f}")

    st.dataframe(pilot_stats, use_container_width=True, height=df_height)

header()
df, options = filters()
leaderboard(df)
