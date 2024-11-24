import streamlit as st
from utility.globals import get_labels_angle, set_labels_angle, get_leaderboard_size, set_leaderboard_size

def display_options(label, options, get_method, set_method):
    keys = [key for key in options.keys()]
    values = [value for value in options.values()]

    current_value = get_method()
    index = values.index(current_value)

    new_value = st.selectbox(label, keys, index=index)
    new_value = options[new_value]

    if new_value != current_value:
        set_method(new_value)

st.header('Settings')

st.subheader('Charts')

options = {'Horizontal': 0, '45 degree': -45, 'Vertical': -90}
display_options('Labels angle', options, get_labels_angle, set_labels_angle)

st.subheader('Leaderboard')

options = {'10': 10, '15': 15, '20': 20, '25': 25, '50': 50, '100': 100}
display_options('Leaderboard page size', options, get_leaderboard_size, set_leaderboard_size)