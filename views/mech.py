import streamlit as st
import pandas as pd

from utility.blocks import filters_block
from utility.database import read_comp_data
from utility.methods import nunique, filter_dataframe, unique, safe_division
from utility.datasources import mech_data

def header():
    st.header('Mechs')

def filters():
    df = read_comp_data()
    options = {'Tournament': None, 'Division': None, 'Class': 'Weight class', 'Chassis': None, 'Mech': None}
    return filters_block(df, options)

def calculate_wlr(values):
    return safe_division(values.eq('WIN').sum(), values.eq('LOSS').sum())

def calculate_kdr(dividend, divisor):
    divisor.replace(0, 1, inplace=True)
    result = dividend.div(divisor)
    
    return result

def mechs_data(df):
    aggregation_method = 'mean'

    df['Deaths'] = [1 if health == 0 else 0 for health in df['HealthPercentage']]
    
    mech_stats = df.groupby(['Mech', 'Chassis'], as_index=False).agg(
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
        Uses=('MatchID','count'),
        Score=('Score','sum')
    )
    mech_stats['KDR'] = calculate_kdr(mech_stats['TotalKills'], mech_stats['TotalDeaths'].copy())

    return mech_stats

def get_full_list(options):
    def match_filters(value, options):
        return (not options['Class'] or value['Class'] in options['Class']) \
            and (not options['Chassis'] or value['Chassis'] in options['Chassis']) \
            and (not options['Mech'] or value['Mech'] in options['Mech'])
    
    data = mech_data()
    all_mechs = [[value['Mech'], value['Chassis']] for _, value in data.items() if match_filters(value, options)]

    df = pd.DataFrame(all_mechs, columns=['Mech', 'Chassis'])
    return df.drop_duplicates(subset=['Mech', 'Chassis'])

def get_page_number(last_page):
    if 'mech_page_number' not in st.session_state:
        page_number = 0
    else:
        page_number = st.session_state['mech_page_number']

    if page_number > last_page:
        page_number = 0

    return page_number

def set_page_number(new_value):
    st.session_state['mech_page_number'] = new_value

def mech_statistics(df, options):
    all_mechs = get_full_list(options)
    mech_stats = mechs_data(df)

    merged_data = all_mechs.merge(mech_stats, on=['Mech', 'Chassis'], how='left')
    merged_data.fillna(0, inplace=True)

    merged_data['Uses'] = merged_data['Uses'].astype(int)
    merged_data['Score'] = merged_data['Score'].astype(int)
    merged_data['Order'] = [1 if uses > 0 else 0 for uses in merged_data['Uses']]

    page_size = 100
    last_page = merged_data.shape[0] // page_size
    page_number = get_page_number(last_page)

    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

    with col1:
        with st.popover("Column descriptions:", use_container_width=True):
            st.markdown('''
                - `Tonnage`: Mech tonnage
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
                - `Uses`: Total use count
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
    
    # Rows to display
    start_idx = page_number * page_size 
    end_idx = (1 + page_number) * page_size

    # Sorting dataset
    merged_data = merged_data.sort_values(['Order', 'Score', 'Uses', 'MS'], ascending=[False, False, False, False], ignore_index=True).iloc[start_idx:end_idx]

    merged_data['Rank'] = merged_data.index + 1
    df_height = 35 * (merged_data.shape[0] + 1) + 3

    merged_data = merged_data.style.format(subset=['Tonnage', 'MS', 'Kills', 'KMDDs', 'Assists', 'CD', 'Deaths', 'DMG', 'TD', 'WLR', 'KDR'], formatter="{:.2f}")
    column_order = ['Rank', 'Mech', 'Chassis', 'Tonnage', 'MS', 'Kills', 'KMDDs', 'Assists', 'CD', 'Deaths', 'KDR', 'DMG', 'TD', 'WLR', 'Uses', 'Score']

    st.dataframe(merged_data, hide_index=True, column_order=column_order, use_container_width=True, height=df_height)

header()
df, options = filters()
mech_statistics(df, options)
