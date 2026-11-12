import streamlit as st

st.logo('./static/Logo.png', icon_image='./static/Logo.png')
st.set_page_config(page_title="Stats Tool", layout='wide')

home_page = st.Page('views/home.py', icon=":material/home:", title='Home', default=True)
tournament_page = st.Page('views/tournament.py', icon=":material/trophy:", title='Tournaments')
stats_page = st.Page('views/leaderboard.py', icon=":material/query_stats:", title='Stats')
ladder_page = st.Page('views/ladder.py', icon=":material/stairs:", title='Ladder')
team_page = st.Page('views/team.py', icon=":material/group:", title='Teams')
player_page = st.Page('views/players.py', icon=":material/person:", title='Players')
map_page = st.Page('views/map.py', icon=":material/public:", title='Maps')
mech_page = st.Page('views/mech.py', icon=":material/robot:", title='Mechs')
elo_page = st.Page('views/elo.py', icon=":material/trending_up:", title='Rating', visibility='hidden')
download_page = st.Page('views/download.py', icon=":material/download:", title='Download data')
drop_details_page = st.Page('views/drop_details.py', icon=":material/search:", title='Drop details')
match_details_page = st.Page('views/match_details.py', icon=":material/sports_score:", title='Match details')
settings_page = st.Page('views/settings.py', icon=":material/settings:", title='General')

admin_page = st.Page('views/admin.py', title='Admin', visibility='hidden')
upload_page = st.Page('views/upload.py', title='Upload', visibility='hidden')
renaming_page = st.Page('views/renaming.py', title='Renaming', visibility='hidden')
new_mechs_page = st.Page('views/new_mechs.py', title='New mechs', visibility='hidden')
compare_tool_page = st.Page('views/compare_tool.py', title='Compare tool', visibility='hidden')
calculate_elo_page = st.Page('views/calculate_elo.py', title='ELO calculation', visibility='hidden')
delete_game_page = st.Page('views/delete_game.py', title='Delete game', visibility='hidden')

navigation = st.navigation({
    "Statistics": [home_page, tournament_page, ladder_page, stats_page, team_page, player_page, map_page, mech_page, elo_page],
    "Data": [download_page, drop_details_page, match_details_page],
    "Settings": [settings_page, admin_page, upload_page, renaming_page, new_mechs_page, compare_tool_page, calculate_elo_page, delete_game_page]
})

navigation.run()
