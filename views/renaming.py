import streamlit as st

from utility.database import read_comp_data, update_values
from utility.blocks import filters_block
from utility.methods import error

def back_button():
    if st.button('< Back'):
        st.switch_page('views/admin.py')

def team_renaming(df):
    st.header('Team renaming')

    key = 'TeamName'
    _, options = filters_block(df, {key: 'Team'}, multiselect=False)
    new_value = st.text_input('New name', '', key='team_name_input', placeholder='New name', label_visibility='hidden')
    button_pressed = st.button('Change name', key='team_name_button', use_container_width=True)
    if button_pressed:
        old_value = options[key] if key in options and options[key] else ''
        if old_value and new_value and new_value != old_value:
            result = update_values(key, old_value, new_value)
            if result:
                error(result)
    
def pilot_renaming(df):
    st.header('Pilot renaming')

    key = 'Username'
    _, options = filters_block(df, {key: 'Pilot'}, multiselect=False)
    new_value = st.text_input('New name', '', key='pilot_name_input', placeholder='New name', label_visibility='hidden')
    button_pressed = st.button('Change name', key='pilot_name_button', use_container_width=True)
    if button_pressed:
        old_value = options[key] if key in options and options[key] else ''
        if old_value and new_value and new_value != old_value:
            result = update_values(key, old_value, new_value)
            if result:
                error(result)

back_button()

df = read_comp_data()

team, pilot = st.columns(2)
with team:
    team_renaming(df)

with pilot:
    pilot_renaming(df)
