import streamlit as st
import pandas as pd

from utility.methods import error
from utility.datasources import mech_data
from utility.requests import mech_list

def back_button():
    if st.button('< Back'):
        st.switch_page('views/admin.py')

def header():
    st.header('Checking for new mechs')

def valid_response(response):
    key = 'error'
    if key in response:
        error(response[key])
        return False
    
    return True

def check_for_new_mechs():
    mechs = mech_data()
    new_mechs = mech_list()
    
    new_list = {}
    if valid_response(new_mechs):
        for key, value in new_mechs.items():
            int_key = int(key)
            if not int_key in mechs:
                new_list[key] = value.upper()

    if new_list:
        df = pd.DataFrame.from_dict(new_list, orient='index', columns=["Mech"])
        st.dataframe(df)
    else:
        st.write('No new mechs found ...')

back_button()
header()
check_for_new_mechs()
