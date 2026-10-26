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
    button_pressed = form.form_submit_button('Submit', width='stretch')

    if button_pressed and not tournament:
        error('Tournament must be selected to connect pilot names to the teams they played for.')
    elif button_pressed:
        result = batch_request(match_ids, tournament)
        uploaded = result['uploaded']
        recalculation = result['recalculation']

        if uploaded:
            st.success(f"Uploaded {uploaded} new matches.")
        else:
            st.info("No new matches were uploaded.")

        if recalculation.get('status') == 'done':
            st.info(
                f"Ratings recalculated for {recalculation['matches']} matches "
                f"({recalculation['rows']} rows) from {recalculation['recalc_from']} "
                f"in {recalculation['seconds']} seconds."
            )
        elif recalculation.get('status') == 'skipped':
            st.info(f"No rating recalculation was needed. {recalculation.get('reason', '')}")

back_button()
header()
display_form()
