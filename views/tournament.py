import streamlit as st
import pandas as pd

from utility.database import read_comp_data
from utility.methods import nunique, filter_dataframe, safe_division
from utility.charts import bar_chart
from utility.blocks import filters_block, metrics_block, charts_block

def header():
    st.header('Tournaments')

def filters():
    df = read_comp_data()
    options = {'Tournament': None, 'Division': None}
    return filters_block(df, options)

def general_statistics(df, options):
    tournaments_count = nunique(df, 'Tournament')
    teams_count = nunique(df, 'TeamName')
    players_count = nunique(df, 'Username')
    games_played = nunique(df, 'MatchID')

    metrics = {
        'Tournaments': tournaments_count,
        'Teams': teams_count,
        'Players': players_count,
        'Games': games_played
    }
    metrics_block(metrics)

def tournament_statistics(df, options):
    overview, details = st.tabs(['Overview', 'Details'])

    with overview:
        tournament_overview(df, options)

    with details:
        tournament_details(df, options)

def tournament_overview(df, options):
    for tournament in options['Tournament']:
        st.subheader(tournament)

        tournament_data = filter_dataframe(df, 'Tournament', tournament)

        metrics = {
            'Teams': nunique(tournament_data, 'TeamName'),
            'Players': nunique(tournament_data, 'Username'),
            'Games': nunique(tournament_data, 'MatchID'),
        }
        metrics_block(metrics, 3)

        tonnage_order = [i for i in range(20, 105, 5)]
        weight_distribution = tournament_data['Tonnage'].value_counts().reindex(tonnage_order).reset_index()

        top_mechs = tournament_data['Mech'].value_counts().sort_values(ascending=False).head(10).reset_index()
        top_chassis = tournament_data['Chassis'].value_counts().sort_values(ascending=False).head(10).reset_index()

        charts = [
            bar_chart(weight_distribution, 'Weight distribution', 'Tonnage', 'count'),
            bar_chart(top_mechs, 'Most used mechs', 'Mech', 'count'),
            bar_chart(top_chassis, 'Most used chassis', 'Chassis', 'count', style='alternate')
        ]
        charts_block(charts)

        st.divider()

def tournament_details(df, options):
    for tournament in options['Tournament']:
        st.subheader(tournament)

        tournament_data = filter_dataframe(df, 'Tournament', tournament)

        light_mechs_data = filter_dataframe(tournament_data, 'Class', 'LIGHT')
        top_light_mechs = light_mechs_data['Mech'].value_counts().sort_values(ascending=False).head(5).reset_index()
        top_light_chassis = light_mechs_data['Chassis'].value_counts().sort_values(ascending=False).head(5).reset_index()

        medium_mechs_data = filter_dataframe(tournament_data, 'Class', 'MEDIUM')
        top_medium_mechs = medium_mechs_data['Mech'].value_counts().sort_values(ascending=False).head(5).reset_index()
        top_medium_chassis = medium_mechs_data['Chassis'].value_counts().sort_values(ascending=False).head(5).reset_index()

        heavy_mechs_data = filter_dataframe(tournament_data, 'Class', 'HEAVY')
        top_heavy_mechs = heavy_mechs_data['Mech'].value_counts().sort_values(ascending=False).head(5).reset_index()
        top_heavy_chassis = heavy_mechs_data['Chassis'].value_counts().sort_values(ascending=False).head(5).reset_index()

        assault_mechs_data = filter_dataframe(tournament_data, 'Class', 'ASSAULT')
        top_assault_mechs = assault_mechs_data['Mech'].value_counts().sort_values(ascending=False).head(5).reset_index()
        top_assault_chassis = assault_mechs_data['Chassis'].value_counts().sort_values(ascending=False).head(5).reset_index()

        charts = [
            bar_chart(top_light_mechs, 'Most used light mechs', 'Mech', 'count'),
            bar_chart(top_medium_mechs, 'Most used medium mechs', 'Mech', 'count'),
            bar_chart(top_heavy_mechs, 'Most used heavy mechs', 'Mech', 'count'),
            bar_chart(top_assault_mechs, 'Most used assault mechs', 'Mech', 'count'),
            bar_chart(top_light_chassis, 'Most used light chassis', 'Chassis', 'count', style='alternate'),
            bar_chart(top_medium_chassis, 'Most used medium chassis', 'Chassis', 'count', style='alternate'),
            bar_chart(top_heavy_chassis, 'Most used heavy chassis', 'Chassis', 'count', style='alternate'),
            bar_chart(top_assault_chassis, 'Most used assault chassis', 'Chassis', 'count', style='alternate')
        ]
        charts_block(charts, columns=4)

        st.divider()

header()
df, options = filters()
if options['Tournament']:
    tournament_statistics(df, options)
else:
    general_statistics(df, options)
