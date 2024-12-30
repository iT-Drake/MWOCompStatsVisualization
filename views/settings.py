import streamlit as st

from utility.globals import get_labels_angle, set_labels_angle, get_leaderboard_size, set_leaderboard_size
from utility.globals import get_leaderboard_aggregation_method, set_leaderboard_aggregation_method, get_leaderboard_default_sorting, set_leaderboard_default_sorting
from utility.enums import AggregationMethod, SortingOption

def main_header():
    st.header('Settings')

def display_options(label, options, get_method, set_method):
    keys = [key for key in options.keys()]
    values = [value for value in options.values()]

    current_value = get_method()
    index = values.index(current_value)

    new_value = st.selectbox(label, keys, index=index)
    new_value = options[new_value]

    if new_value != current_value:
        set_method(new_value)

def charts():
    st.subheader('Charts')

    options = {'Horizontal': 0, '45 degree': -45, 'Vertical': -90}
    display_options('Labels angle', options, get_labels_angle, set_labels_angle)

def leaderboard():
    st.subheader('Leaderboard')

    options = {'10': 10, '15': 15, '20': 20, '25': 25, '50': 50, '100': 100}
    display_options('Leaderboard page size', options, get_leaderboard_size, set_leaderboard_size)

    options = {item.value: item for item in AggregationMethod}
    display_options('Leaderboard stats aggregation method', options, get_leaderboard_aggregation_method, set_leaderboard_aggregation_method)

    options = {item.value: item for item in SortingOption}
    display_options('Default column for leaderboard sorting', options, get_leaderboard_default_sorting, set_leaderboard_default_sorting)

main_header()
charts()
leaderboard()
