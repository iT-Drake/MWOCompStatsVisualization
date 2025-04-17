import streamlit as st

from utility.requests import roster_links, batch_request
from utility.methods import error, parse_match_ids

def back_button():
    if st.button('< Back'):
        st.switch_page('views/admin.py')

def header():
    st.subheader('Upload games')

def display_form():
    # Match ID submission form
    form = st.form("data_fetching", clear_on_submit=True)

    all_rosters = roster_links()
    tournaments = [key for key, value in all_rosters.items() if isinstance(value, str) and value]

    tournament = form.selectbox('Tournament', tournaments, index=None, placeholder='Tournament', label_visibility='hidden')

    submitted_text = form.text_area('Get API data for provided IDs:', placeholder='List of Match IDs', key='match_ids')
    match_ids = parse_match_ids(submitted_text)
    button_pressed = form.form_submit_button('Submit', use_container_width=True)

    if button_pressed and not tournament:
        error('Tournament must be selected to connect pilot names to the teams they played for.')
    elif button_pressed:
        batch_request(match_ids, tournament)

back_button()
header()
display_form()
