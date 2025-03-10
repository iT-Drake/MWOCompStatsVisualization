import streamlit as st
import pandas as pd
import altair as alt

from utility.requests import jarls_pilot_stats
from utility.methods import filter_dataframe, nunique, safe_division
from utility.database import read_comp_data
from utility.blocks import metrics_block
from utility.charts import bar_chart

def back_button():
    if st.button('< Back'):
        st.switch_page('views/admin.py')

def header():
    st.header('Compare Tool')

def display_inputs():
    col1, col2 = st.columns(2)
    team1 = col1.text_area('Team 1')
    team2 = col2.text_area('Team 2')

    if not st.button('Compare', use_container_width=True):
        st.markdown("#### Each pilot name should be on a new line.\n#### Error will be displayed if pilot wasn't found on Jarl's list.")
    else:
        team1_pilots = [pilot.strip().lower() for pilot in team1.splitlines()]
        team2_pilots = [pilot.strip().lower() for pilot in team2.splitlines()]
        
        df = read_comp_data()
        col1, col2 = st.columns(2)
        
        display_stats(col1, team1_pilots, df)
        display_stats(col2, team2_pilots, df)

def display_stats(container, pilots, df):
    if not pilots:
        return
    
    pilots_data = df[df['Username'].str.lower().isin(pilots)]
    with container:
        display_metrics(pilots_data)

    team_data = {
        'Pilot': [],
        'Rank': [],
        'CompGames': [],
        'HighestDiv': [],
        'HighestDivGames': [],
        'MostPlayedDiv': [],
        'MostPlayedDivGames': []
    }
    for pilot in pilots:
        pilot_stats = jarls_pilot_stats(pilot)
        if not pilot_stats:
            continue

        team_data['Pilot'].append(pilot_stats['PilotName'])
        team_data['Rank'].append(pilot_stats['Rank'])
    
        pilot_data = pilots_data[pilots_data['Username'].str.lower() == pilot.lower()]
        comp_games = nunique(pilot_data, 'MatchID')
        team_data['CompGames'].append(comp_games)

        if comp_games:
            highest_div = pilot_data['Division'].min()
            team_data['HighestDiv'].append(highest_div)

            highest_div_games = nunique(filter_dataframe(pilot_data, 'Division', highest_div), 'MatchID')
            team_data['HighestDivGames'].append(highest_div_games)

            groupped_data = pilot_data.groupby('Division')['Division'].value_counts()
            team_data['MostPlayedDiv'].append(groupped_data.idxmax())
            team_data['MostPlayedDivGames'].append(int(groupped_data.max()))
        else:
            team_data['HighestDiv'].append("--")
            team_data['HighestDivGames'].append(0)
            team_data['MostPlayedDiv'].append("--")
            team_data['MostPlayedDivGames'].append(0)

    team_data = pd.DataFrame.from_dict(team_data).sort_values(by=['HighestDiv','CompGames','Rank'], ascending=[True, False, True])
    team_data.columns = ['Pilot', 'QP Rank', 'Games', 'Div (High)', 'Games (High)', 'Div (Avg)', 'Games (Avg)']

    df_height = 35 * (team_data.shape[0] + 1) + 3
    container.dataframe(team_data, hide_index=True, use_container_width=True, height=df_height)

    grouped_df = pilots_data.groupby('Division').agg({
        'MatchResult': [
            ('Total', 'count'),
            ('Wins', lambda x: (x == 'WIN').sum())
        ]
    }).droplevel(0, axis=1).reset_index()

    # Convert wide dataframe to a tall one
    tall_df = pd.melt(grouped_df,
                    id_vars=['Division'],
                    value_vars=['Total', 'Wins'],
                    var_name='Metric',
                    value_name='Count')
    
    chart = alt.Chart(tall_df, title='Games per division').mark_bar().encode(
        x=alt.X(f'Division:O', axis=alt.Axis(labelAngle=0), title=None),
        y=alt.Y('Count:Q', title=None).stack(None),
        color=alt.Color('Metric:N', legend=alt.Legend(title='Legend'))
    )
    container.altair_chart(chart, use_container_width=True)

def display_metrics(df):
    match_stats = df.groupby('MatchID')['MatchResult'].value_counts().reset_index()
    total_games = match_stats['count'].sum()
    total_wins = match_stats[match_stats['MatchResult'] == 'WIN']['count'].sum()
    total_losses = total_games - total_wins

    metrics = {
        'Games': total_games,
        'Wins': total_wins,
        'Losses': total_losses,
        'Winrate': f'{safe_division(total_wins, total_games):.0%}'
    }
    metrics_block(metrics)

back_button()
header()
display_inputs()
