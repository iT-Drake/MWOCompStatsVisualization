import streamlit as st
import sqlite3 as sql

from utility.globals import DB_NAME
from utility.methods import parse_match_ids
from utility.database import run_query

def back_button():
    if st.button('< Back'):
        st.switch_page('views/admin.py')

def header():
    st.header('Game deletion tool')

def delete_game(conn, id):
    run_query(conn, "DELETE FROM CompData WHERE MatchID = ?", [id])
    conn.commit()

def display_interface():
    match_ids = st.text_input('Enter match id', value=None, placeholder='Enter match ID', label_visibility='hidden')
    button_pressed = st.button('Delete', width='stretch')

    if button_pressed and not match_ids:
        return
    elif button_pressed:
        conn = sql.connect(DB_NAME)

        id_list = parse_match_ids(match_ids)
        for id in id_list:
            delete_game(conn, id)

        conn.close()

back_button()
header()

display_interface()
