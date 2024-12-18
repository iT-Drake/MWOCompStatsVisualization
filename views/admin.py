import streamlit as st

st.header('Admin page')

if st.button('Upload data >'):
    st.switch_page('views/upload.py')

if st.button('Team and pilot renaming >'):
    st.switch_page('views/renaming.py')

if st.button('Check for new mechs >'):
    st.switch_page('views/new_mechs.py')

if st.button('Match details >'):
    st.switch_page('views/match_details.py')

# Intentional backup page
