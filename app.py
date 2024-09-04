import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

from os import getenv
from dotenv import load_dotenv

load_dotenv()
edit_url = getenv("URL")
export_url = edit_url.replace('/edit?usp=sharing', '/export?format=csv')

@st.cache_data(ttl=180)
def load_data(url):
    return pd.read_csv(url, index_col=0, parse_dates=['match_time'])

df = load_data(export_url)

st.logo('Logo.png')

teams = df['team'].unique()

team = st.sidebar.selectbox('', teams, index=None, placeholder='Select a team')
if team:
    team_data = df[df['team'] == team]
    players = team_data['name'].unique()
else:
    players = df['name'].unique()

player = st.sidebar.selectbox('', players, index=None, placeholder='Select a pilot')

st.title('Statistics for competitive matches CS 2024')

col1, col2 = st.columns(2, gap='medium')

top_damage_players = df.groupby('name')['damage'].sum().sort_values(ascending=False).head(5)
col1.subheader('Players with highest damage')
col1.bar_chart(top_damage_players, )

top_kills_players = df.groupby('name')['kills'].sum().sort_values(ascending=False).head(5)
col2.subheader('Players with most kills')
col2.bar_chart(top_kills_players)

if player:
    col1, col2 = st.columns(2, gap='medium')

    player_data = df[df['name'] == player]
    total_matches = player_data.shape[0]
    wins = player_data['winner'].sum()
    win_loss_ratio = wins / total_matches if total_matches > 0 else 0

    col1.write(f"### {player}")
    col1.write(f"Games played: {total_matches}")
    col1.write(f"Total Kills: {player_data['kills'].sum()}")
    col1.write(f"Total Damage: {player_data['damage'].sum()}")
    col1.write(f"Win/Loss Ratio: {win_loss_ratio:.2f}")

    if player_data.shape[0] > 0:
        col2.write("### Match Details:")
        col2.write(player_data[['team', 'winner', 'mechname', 'health', 'damage', 'kills']])
