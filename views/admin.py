import streamlit as st

st.header('Admin page')

if st.button('Upload data >'):
    st.switch_page('views/upload.py')

if st.button('Team and pilot renaming >'):
    st.switch_page('views/renaming.py')

if st.button('Check for new mechs >'):
    st.switch_page('views/new_mechs.py')

if st.button('Compare rosters >'):
    st.switch_page('views/compare_tool.py')

if st.button('Calculate ELO >'):
    st.switch_page('views/calculate_elo.py')

# Intentional backup page
