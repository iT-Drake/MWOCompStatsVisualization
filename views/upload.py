import streamlit as st

from utility.requests import roster_links, batch_request

def back_button():
    if st.button('< Back'):
        st.switch_page('views/admin.py')

back_button()
st.subheader('This is an upload page')

# Match ID submission form
form = st.form("data_fetching", clear_on_submit=True)

all_rosters = roster_links()
tournaments = list(all_rosters.keys())

tournament = form.selectbox('Tournament', tournaments, label_visibility='hidden')

submitted_text = form.text_area('Get API data for provided IDs:', placeholder='List of Match IDs', key='match_ids')
match_ids = submitted_text.strip().splitlines() if submitted_text else []
button_pressed = form.form_submit_button('Submit', use_container_width=True)

if button_pressed and not tournament:
    st.write('Tournament must be selected to connect pilot names to the teams they played for.')
elif button_pressed:
    batch_request(match_ids, tournament)
