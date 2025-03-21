import streamlit as st

from utility.enums import AggregationMethod, SortingOption

# SECRETS

DB_NAME = st.secrets["DB_NAME"]
API_KEY = st.secrets["API_KEY"]
API_URL = st.secrets["API_URL"]
MECH_DATA_URL = st.secrets["MECH_DATA_URL"]
ROSTER_URLS = st.secrets["ROSTER_URLS"]

# SETTINGS

def get_cached_value(key, default=None):
    return default if key not in st.session_state else st.session_state[key]

def set_cached_value(key, value):
    st.session_state[key] = value

def set_labels_angle(value):
    set_cached_value('chart_labels_angle', value)

def get_labels_angle():
    return get_cached_value('chart_labels_angle', 0)

def set_leaderboard_size(value):
    set_cached_value('leaderboard_size', value)

def get_leaderboard_size():
    return get_cached_value('leaderboard_size', 100)

def set_leaderboard_default_sorting(value):
    set_cached_value('leaderboard_default_sorting', value)

def get_leaderboard_default_sorting():
    return get_cached_value('leaderboard_default_sorting', SortingOption.Default())

def set_leaderboard_aggregation_method(value):
    set_cached_value('leaderboard_aggregation_method', value)

def get_leaderboard_aggregation_method():
    return get_cached_value('leaderboard_aggregation_method', AggregationMethod.Default())
