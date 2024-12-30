import streamlit as st
import pandas as pd

from utility.globals import ROSTER_URLS, MECH_DATA_URL
from utility.methods import error
from utility.caching import CACHE_TTL

@st.cache_data(ttl=CACHE_TTL)
def roster_links():
    try:
        df = pd.read_csv(ROSTER_URLS)
        zipped_data = zip(df['Tournament'], df['RosterLink'])
        result = {item[0]: item[1] for item in zipped_data}
    except Exception as e:
        error(f"An error occurred while fetching team rosters:\n{e}")
        result = {}

    return result

@st.cache_data(ttl=CACHE_TTL)
def mech_data():
    try:
        df = pd.read_csv(MECH_DATA_URL)
        zipped_data = zip(df['ItemID'], df['Name'], df['Chassis'], df['Tonnage'], df['Class'], df['Type'])
        result = {item[0]:{'Mech': item[1], 'Chassis': item[2], 'Tonnage': item[3], 'Class': item[4], 'Type': item[5]} for item in zipped_data}
    except Exception as e:
        error(f"An error occurred while fetching mech data:\n{e}")
        result = {}
    
    return result

@st.cache_data(ttl=CACHE_TTL)
def team_rosters(url):
    result = {}
    if not url:
        error(f"An empty rosters URL provided.")
        return result

    try:
        df = pd.read_csv(url)
        zipped_data = zip(df['Pilot'].str.upper(), df['Team'], df['Division'])
        result = {item[0]: {'Team': item[1], 'Division': item[2]} for item in zipped_data}
    except Exception as e:
        error(f"An error occurred while fetching team rosters:\n{e}")
    
    return result
