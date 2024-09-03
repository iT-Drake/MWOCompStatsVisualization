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

top_damage_players = df.groupby('name')['damage'].sum().sort_values(ascending=False).head(5)

fig, ax = plt.subplots()
fig.patch.set_facecolor('black')
ax.set_facecolor('black')
ax.tick_params(axis='both', colors='white')
ax.grid(True, color='white')

top_damage_players.plot(kind='bar', ax=ax)
ax.set_xlabel('Pilot', color='white')
ax.set_ylabel('Total Damage', color='white')
ax.set_title('Top-5 Players with Highest Damage', color='white')

st.pyplot(fig)

top_kills_players = df.groupby('name')['kills'].sum().sort_values(ascending=False).head(5)

fig, ax = plt.subplots()
fig.patch.set_facecolor('black')
ax.set_facecolor('black')
ax.tick_params(axis='both', colors='white')
ax.grid(True, color='white')

top_kills_players.plot(kind='bar', ax=ax)
ax.set_xlabel('Pilot', color='white')
ax.set_ylabel('Total Kills', color='white')
ax.set_title('Top-5 Players with Most Kills', color='white')

st.pyplot(fig)

player = st.selectbox('Select a player', df['name'].unique())
if player:
    player_data = df[df['name'] == player]
    total_matches = player_data.shape[0]
    wins = player_data['winner'].sum()
    win_loss_ratio = wins / total_matches if total_matches > 0 else 0

    st.write(f"### {player}")
    st.write(f"Games played: {total_matches}")
    st.write(f"Total Kills: {player_data['kills'].sum()}")
    st.write(f"Total Damage: {player_data['damage'].sum()}")
    st.write(f"Win/Loss Ratio: {win_loss_ratio:.2f}")

    if player_data.shape[0] > 0:
        st.write("### Match Details:")
        st.write(player_data[['team', 'winner', 'mechname', 'health', 'damage', 'kills']])
