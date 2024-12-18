import streamlit as st

st.logo('./img/Logo.png', icon_image='./img/Logo.png')
st.set_page_config(page_title="Stats Tool", layout='wide')

home_page = st.Page('views/home.py', icon=":material/home:", title='Home', default=True)
tournament_page = st.Page('views/tournament.py', icon=":material/trophy:", title='Tournaments')
leaderboard_page = st.Page('views/leaderboard.py', icon=":material/leaderboard:", title='Leaderboard')
team_page = st.Page('views/team.py', icon=":material/group:", title='Teams')
player_page = st.Page('views/player.py', icon=":material/person:", title='Players')
map_page = st.Page('views/map.py', icon=":material/public:", title='Maps')
download_page = st.Page('views/download.py', icon=":material/download:", title='Download data')
settings_page = st.Page('views/settings.py', icon=":material/settings:", title='General')

admin_page = st.Page('views/admin.py', title=' ')
upload_page = st.Page('views/upload.py', title=' ')
renaming_page = st.Page('views/renaming.py', title=' ')
new_mechs_page = st.Page('views/new_mechs.py', title=' ')
match_details_page = st.Page('views/match_details.py', title=' ')

navigation = st.navigation({
    "Statistics": [home_page, tournament_page, leaderboard_page, team_page, player_page, map_page],
    "Data": [download_page],
    "Settings": [settings_page, admin_page, upload_page, renaming_page, new_mechs_page, match_details_page]
})

navigation.run()
