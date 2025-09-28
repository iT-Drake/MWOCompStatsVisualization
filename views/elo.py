import streamlit as st

from utility.database import read_comp_data
from utility.methods import safe_division

def header():
    st.header('ELO')

def calculate_wlr(values):
    return safe_division(values.eq('WIN').sum(), values.eq('LOSS').sum())

def leaderboard(df):
    current_top100 = df.groupby('Username').last().sort_values(by='Rating', ascending=False).reset_index().head(100)
    filtered_df = df[df['Username'].isin(current_top100['Username'])]

    filtered_df['Deaths'] = [1 if health == 0 else 0 for health in filtered_df['HealthPercentage']]
    pilot_stats = filtered_df.groupby(['Username'], as_index=False).agg(
        Tonnage=('Tonnage', 'mean'),
        MS=('MatchScore', 'mean'),
        Kills=('Kills', 'mean'),
        KMDDs=('KillsMostDamage', 'mean'),
        Assists=('Assists', 'mean'),
        CD=('ComponentsDestroyed', 'mean'),
        Deaths=('Deaths', 'mean'),
        DMG=('Damage', 'mean'),
        TD=('TeamDamage', 'mean'),
        WLR=('MatchResult', lambda values: calculate_wlr(values)),
        Games=('MatchID','nunique'),
        Score=('Score','sum'),
        Rating=('Rating','last'),
        MaxGain=('Rating_change','max'),
        MaxLoss=('Rating_change','min')
    ).rename(columns={'Username': 'Pilot'}).sort_values(by='Rating', ascending=False).reset_index()

    pilot_stats['Rank'] = pilot_stats.index + 1
    df_height = 35 * (pilot_stats.shape[0] + 1) + 3

    pilot_stats = pilot_stats.style.format(subset=['Tonnage', 'MS', 'Kills', 'KMDDs', 'Assists', 'CD', 'Deaths', 'DMG', 'TD', 'WLR'], formatter="{:.2f}")

    column_order = ['Rank', 'Pilot', 'Tonnage', 'MS', 'Kills', 'KMDDs', 'Assists', 'CD', 'Deaths', 'DMG', 'TD', 'WLR', 'Games', 'Score', 'Rating', 'MaxGain', 'MaxLoss']
    st.dataframe(pilot_stats, hide_index=True, column_order=column_order, use_container_width=True, height=df_height)

df = read_comp_data()
header()
leaderboard(df)
