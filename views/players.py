import streamlit as st
import pandas as pd
import altair as alt

from utility.admission import ACTIVE_DAYS, MIN_GAMES
from utility.baselines import STATS, WEIGHT_CLASSES, class_percentiles
from utility.database import read_comp_data
from utility.methods import nunique, safe_division
from utility.blocks import change_color, filters_block, metrics_block, winner_label
from utility.ranking import ladder_data, pilot_ratings
from utility.requests import jarls_pilot_overview_link
from utility.charts import bar_chart
from utility.globals import RATING_BASE

# One range slider per career, so a stored window can never be replayed against a
# career too short for it; the selection name is what `st.altair_chart` hands back
# on a click.
CHART_RANGE_KEY = 'rating_chart_range'
MATCH_SELECTION = 'match_data'

def header():
    st.header('Players')
    st.caption('Each filter narrows the next one: a division limits the teams, a team limits '
               'the pilots. The tabs describe the selected scope; the pilot card above them '
               'always describes the whole career.')

def filters(df):
    # Dict order is the cascade, so Username is last and only offers the pilots of
    # the selected team. It is a selectbox because a profile belongs to one pilot.
    options = {'Tournament': None, 'Division': None, 'TeamName': 'Team', 'Username': 'Player'}
    return filters_block(df, options, single=('Username',))

def general_statistics(df):
    """What the current scope contains, not who leads it.

    The scope belongs to the filters, so the numbers move when they do; keeping a
    'best player' here would pull a ranking onto a page that is about one pilot at
    a time, and the ladder is the only ranking.
    """
    tournaments = nunique(df, 'Tournament')
    divisions = nunique(df, 'Division')
    teams = nunique(df, 'TeamName')
    players = nunique(df, 'Username')
    games = nunique(df, 'MatchID')
    games_per_player = df.groupby('Username')['MatchID'].nunique().median()

    metrics = {
        'Tournaments': tournaments,
        'Divisions': divisions,
        'Teams': teams,
        'Players': players,
        'Games': games,
        'Median games/player': f'{games_per_player:.0f}',
    }

    metrics_block(metrics, columns=6)

def identity_block(pilot):
    """Who the pilot is right now, read from the whole database.

    Filters narrow the tabs, never this card: the rating and the ladder position
    are properties of the career, and a tournament filter would otherwise turn
    the card into 'their rating at the end of that tournament'.
    """
    row = pilot_ratings().set_index('Pilot').loc[pilot]

    ranked = ladder_data()
    position = ranked.index[ranked['Pilot'] == pilot]
    rank = int(ranked.loc[position[0], 'Rank']) if len(position) else None

    st.markdown(f'### {pilot} ([jarls]({jarls_pilot_overview_link(pilot)}))')

    metrics = {
        'Rating': (f'{row["Rating"]:.2f}', f'{row["Change"]:+.2f}'),
        'Rank': f'#{rank}' if rank else 'Unranked',
        'Games': int(row['Games']),
        'Tournaments': int(row['Tournaments']),
    }
    metrics_block(metrics, columns=4)

    st.caption(f'{row["Team"]} · Division {row["Division"]} · '
               f'last played {row["LastPlayed"]:%Y-%m-%d} ({row["Tournament"]})')

    if rank is None:
        st.caption(f'Not on the ladder: it takes at least {MIN_GAMES} games and a match in the '
                   f'last {ACTIVE_DAYS // 365} years. The rating above is the stored one either '
                   f'way.')

def opponent_names(df, match_ids):
    """MatchID and side -> the team that played it.

    `Team` is the map side, not the team (landmine 12), so the opponent is read
    off the pair of TeamName values in the same game. A side can carry two names
    in one game (2 % of sides do), hence the aggregate; `max` matches what
    `elo.py` already resolves. The frame is narrowed to the games asked for first
    - the same aggregate over the whole database costs 15x more.
    """
    sides = df[df['MatchID'].isin(match_ids)]
    return sides.groupby(['MatchID', 'Team'])['TeamName'].max()

def pilot_history(df, pilot):
    """Every game the pilot played, with the columns the tabs derive from it.

    The derivations happen on the whole career before any filter is applied: a
    rating change diffed inside a tournament would turn its first game into a
    fake jump, and the chart's axis needs the career range even when only a
    slice of it is on screen.
    """
    history = df[df['Username'] == pilot].sort_values('CompleteTime').copy()
    history['GameNumber'] = range(1, len(history) + 1)

    # First game starts from the rating base, so a debut shows what it was worth.
    history['PrevRating'] = history['PilotRating'].shift(1).fillna(RATING_BASE)
    history['RatingChange'] = history['PilotRating'] - history['PrevRating']
    history['TeamDifference'] = history['TeamRating'] - history['OpponentRating']

    # A stem is drawn from the dot by the team-vs-opponent gap: down when the
    # pilot's team was the stronger side, up when the opponents were.
    history['Matchup'] = 'Stronger opponent'
    history.loc[history['TeamDifference'] > 0, 'Matchup'] = 'Weaker opponent'
    history['StemEnd'] = history['PilotRating'] - history['TeamDifference']

    names = opponent_names(df, history['MatchID'])
    other_side = history['Team'].map({'1': '2', '2': '1'})
    history['Opponent'] = names.reindex(list(zip(history['MatchID'], other_side))).to_numpy()

    return history

def game_range(view):
    """The window of the games on screen, in game numbers.

    The bounds are the games the filters left, so the slider describes the same scope
    as the chart: a tournament that holds 21 games gets 21 positions, not the whole
    career. A scope with one game (or none) has nothing to slide, so the widget is
    skipped and the scope is drawn whole.
    """
    if view.empty:
        return (1, 1)

    first = int(view['GameNumber'].min())
    last = int(view['GameNumber'].max())
    if first == last:
        return (first, last)

    pilot = view['Username'].iloc[0]

    return st.slider(
        'Games',
        min_value=first,
        max_value=last,
        value=(first, last),
        # The scope is part of the key, so a stored window can never be replayed
        # against a scope too short to hold it.
        key=f'{CHART_RANGE_KEY}_{pilot}_{first}_{last}',
    )

def rating_history_chart(history, scope, window):
    """Career chart: line, dots and a stem per game, drawn for the games in `scope`.

    The vertical axis stays on the whole career: a quiet stretch must not look like a
    collapse because the window around it is short. The horizontal axis fits what is
    on screen, so a tournament filter or the range slider zooms instead of cropping a
    fixed timeline. Games are counted along the career, not by date - the games of one
    tournament fall into a single week and would pile up on one pixel; the year labels
    give the dates back.
    """
    career = pd.concat([history['PilotRating'], history['StemEnd']]).dropna()
    low, high = float(career.min()), float(career.max())
    padding = (high - low) * 0.05 or 1.0

    # Year labels follow the visible games, so a label never points at an empty
    # stretch of the axis it is no longer drawn on.
    years = scope.assign(Year=scope['CompleteTime'].dt.year) \
        .groupby('Year')['GameNumber'].mean().reset_index()

    if len(scope):
        x_low, x_high = float(scope['GameNumber'].min()), float(scope['GameNumber'].max())
    else:
        x_low, x_high = float(window[0]), float(window[1])

    # A window holding one game would otherwise draw a zero-width axis.
    if x_low == x_high:
        x_low, x_high = x_low - 0.5, x_high + 0.5

    tooltip = [
        alt.Tooltip('CompleteTime:T', title='Date', format='%Y-%m-%d'),
        alt.Tooltip('Tournament:N', title='Tournament'),
        alt.Tooltip('Division:N', title='Division'),
        alt.Tooltip('TeamName:N', title='Team'),
        alt.Tooltip('Opponent:N', title='Opponent'),
        alt.Tooltip('Map:N', title='Map'),
        alt.Tooltip('MatchResult:N', title='Result'),
        alt.Tooltip('PilotRating:Q', title='Rating', format='.2f'),
        alt.Tooltip('RatingChange:Q', title='Rating change', format='+.2f'),
        alt.Tooltip('Performance:Q', title='Performance', format='.0%'),
        alt.Tooltip('TeamRating:Q', title='Team rating', format='.2f'),
        alt.Tooltip('OpponentRating:Q', title='Opponent rating', format='.2f'),
    ]

    # One x encoding, reused by every layer: a layer carrying its own `axis=None`
    # switches the merged shared axis off for the whole chart, which is what used
    # to drop the title, the ticks and the gridlines. The ticks are game numbers,
    # so they are forced to whole steps - a wide chart otherwise asks Vega-Lite
    # for half-game steps and labels the axis 300.5, 301.0.
    x_encoding = alt.X(
        'GameNumber:Q',
        title='Game sequence',
        axis=alt.Axis(format='d', tickMinStep=1),
        scale=alt.Scale(domain=[x_low, x_high], nice=True),
    )

    base = alt.Chart(scope).encode(
        x=x_encoding,
        y=alt.Y('PilotRating:Q', title='Rating',
                scale=alt.Scale(domain=[low - padding, high + padding], zero=False)),
        tooltip=tooltip,
    )

    opponent_stems = base.mark_rule(strokeWidth=2, opacity=0.55).encode(
        y2=alt.Y2('StemEnd:Q'),
        color=alt.Color(
            'Matchup:N',
            scale=alt.Scale(domain=['Weaker opponent', 'Stronger opponent'],
                            range=['firebrick', 'seagreen']),
            title='Opponent',
        ),
    )

    # `detail` breaks the line where the filters cut games out, so the segments
    # never draw a straight line across a gap they did not play.
    line = base.mark_line(strokeWidth=2.5, color='darkslateblue').encode(
        detail=alt.Detail('Segment:N')
    )

    # Clicking a dot selects its game; `nearest` means the click does not have to
    # land on the dot itself, which is 8 px wide at this size.
    selection = alt.selection_point(
        name=MATCH_SELECTION,
        fields=['MatchID'],
        on='click',
        nearest=True,
    )

    points = base.mark_point(size=45, filled=True).encode(
        color=alt.Color('Division:N', scale=alt.Scale(scheme='dark2'), title='Division')
    ).add_params(selection)

    year_labels = alt.Chart(years).mark_text(
        align='center',
        baseline='bottom',
        dy=-10,
        fontWeight='bold',
        color='gray',
    ).encode(
        x=x_encoding,
        text=alt.Text('Year:N'),
        y=alt.value(-1),
    )

    return alt.layer(
        opponent_stems,
        line,
        points,
        year_labels,
    ).resolve_scale(
        color='independent'
    ).properties(
        height=320
    )

def previous_ratings(df, drop):
    """Each pilot's rating going into the drop, from their last game before it.

    Needs the whole database, not the drop: the drop holds one row per pilot and the
    previous game is usually a different team's. A debut starts from `RATING_BASE`,
    the same baseline `pilot_history()` uses, so the two readings agree.

    `RatingBase` is *not* the pre-match value despite its name - the writer stores the
    rating after `rate()` has run (landmine 15), so the change cannot be read off the
    row itself.
    """
    roster = set(drop['Username'])
    moment = drop['CompleteTime'].iloc[0]

    before = df[df['Username'].isin(roster) & (df['CompleteTime'] < moment)]
    return before.sort_values('CompleteTime').groupby('Username')['PilotRating'].last()

def match_details(df, view, match_id):
    """The drop behind a clicked dot: the two sides that played it, one table each.

    `Team` is the map side, not the team (landmine 12), so each table is labelled with
    the team that played that side in this drop. Ratings are the ones the drop ended
    with; `Change` is the move each pilot brought into it, so it covers the whole
    roster and not only the pilot whose career the page shows.
    """
    game = view[view['MatchID'] == match_id]
    if game.empty:
        # A selection left over from another pilot or an earlier filter.
        return
    game = game.iloc[0]

    drop = df[df['MatchID'] == match_id]
    names = drop.groupby('Team')['TeamName'].max()
    previous = previous_ratings(df, drop)

    st.divider()

    metrics = {
        'Date': f'{game["CompleteTime"]:%Y-%m-%d}',
        'Tournament': game["Tournament"],
        'Division': game["Division"],
        'Map': game["Map"],
        'Match': match_id,
    }
    metrics_block(metrics)

    for column, side in zip(st.columns(2), ['1', '2']):
        side_rows = drop[drop['Team'] == side]
        # `WinningTeam` is the side that won, not the team name (landmine 12), so it
        # is compared to the side this table lists; a draw leaves both plain.
        won = game['WinningTeam'] == side
        with column:
            st.markdown(f'### {winner_label(names.get(side, f"Side {side}"), won)}')
            if side_rows.empty:
                st.caption('No rows for this side.')
                continue

            hp = side_rows['HealthPercentage'].mask(side_rows['HealthPercentage'] <= 0, 'DEAD')
            table = pd.DataFrame({
                'Pilot': side_rows['Username'],
                'Mech': side_rows['Mech'],
                'HP': hp,
                'Kills': side_rows['Kills'],
                'KMDDs': side_rows['KillsMostDamage'],
                'CD': side_rows['ComponentsDestroyed'],
                'DMG': side_rows['Damage'],
                'MS': side_rows['MatchScore'],
                'Perf': side_rows['Performance'] * 100,
                'Rating': side_rows['PilotRating'],
                'Change': side_rows['PilotRating']
                          - side_rows['Username'].map(previous).fillna(RATING_BASE),
            })

            st.dataframe(
                table.style.format(
                    subset=['Perf', 'Rating', 'Change'],
                    formatter={'Perf': '{:.0f}%', 'Rating': '{:.2f}', 'Change': '{:+.2f}'},
                ).map(
                    lambda name: 'font-weight: 600' if name == game['Username'] else '',
                    subset=['Pilot'],
                ),
                hide_index=True,
                width='stretch',
                height=35 * (len(table) + 1) + 3,
            )

def percentiles_block(view):
    """The pilot's per-class averages, ranked inside that class."""
    table = class_percentiles(view)

    if table is None:
        return

    st.divider()
    st.caption('Percentile inside the weight class, against pilots with at least '
               f'{MIN_GAMES} games in that class: 84 % means 84 % of them average less. '
               'Survival counts games not died in, so every column reads higher = better. '
               f'A class needs {MIN_GAMES} games in the selected scope to be ranked at all; '
               'the games column is what the rest of the row is based on.')

    st.dataframe(
        table,
        hide_index=True,
        column_order=['Class', 'Games', *STATS],
        width='stretch',
    )

def overview_tab(df, history, view):
    """Per-game numbers first, then how they compare, then the career shape."""
    career_games = nunique(history, 'MatchID')

    wins = int(view['MatchResult'].eq('WIN').sum())
    losses = int(view['MatchResult'].eq('LOSS').sum())
    deaths = (view['HealthPercentage'] == 0)

    metrics = {
        'Kills (avg.)': f'{view["Kills"].mean():.2f}',
        'KMDDs (avg.)': f'{view["KillsMostDamage"].mean():.2f}',
        'Assists (avg.)': f'{view["Assists"].mean():.2f}',
        'CD (avg.)': f'{view["ComponentsDestroyed"].mean():.2f}',
        'Damage (avg.)': f'{view["Damage"].mean():.2f}',
        'Match score (avg.)': f'{view["MatchScore"].mean():.2f}',
        'Deaths (avg.)': f'{deaths.mean():.2f}',
        'Win/Loss ratio': f'{safe_division(wins, losses):.2f}',
    }

    column_stats, column_classes = st.columns([4, 2])
    with column_stats:
        metrics_block(metrics, columns=4)

    with column_classes:
        class_counts = view['Class'].value_counts().reindex(
            WEIGHT_CLASSES, fill_value=0).reset_index()
        class_counts.columns = ['Class', 'Games']

        column_classes.altair_chart(
            bar_chart(class_counts, 'Weight class distribution', 'Class', 'Games')
            .properties(height=210),
            width='stretch',
        )

    percentiles_block(view)

    chart_view = view.copy()
    chart_view['Segment'] = (chart_view['GameNumber'].diff() != 1).cumsum()

    st.divider()

    window = game_range(view)
    scope = chart_view[chart_view['GameNumber'].between(window[0], window[1])]

    chart = rating_history_chart(history, scope, window)
    event = st.altair_chart(chart, width='stretch', on_select='rerun')

    visible = nunique(scope, 'MatchID')
    caption = ('Dots are games, coloured by division. A stem runs from the dot by the '
               'team-vs-opponent rating gap: red below the dot means the pilot\'s team was '
               'the stronger side, green above means the opponents were. The vertical axis '
               'is the whole career, the horizontal one fits the games on screen. Click a '
               'game for its details.')
    if visible != career_games:
        caption += f' Showing {visible} of {career_games} games.'
    st.caption(caption)

    selected = (event or {}).get('selection', {}).get(MATCH_SELECTION, [])
    if selected:
        match_details(df, scope, selected[0]['MatchID'])

def matches_tab(view):
    """The game log: the receipts behind the chart, newest first."""
    if view.empty:
        st.info('No games in the selected scope.')
        return

    games = view.sort_values('CompleteTime', ascending=False)

    table = pd.DataFrame({
        'Date': games['CompleteTime'].dt.strftime('%Y-%m-%d'),
        'Tournament': games['Tournament'],
        'Division': games['Division'],
        'Team': games['TeamName'],
        'Opponent': games['Opponent'],
        'Map': games['Map'],
        'Mech': games['Mech'],
        'Class': games['Class'],
        'Result': games['MatchResult'],
        'Kills': games['Kills'],
        'KMDDs': games['KillsMostDamage'],
        'Assists': games['Assists'],
        'CD': games['ComponentsDestroyed'],
        'DMG': games['Damage'],
        'MS': games['MatchScore'],
        # Performance is a per-team centred weight, so a percentage is a share
        # of the team average for that game, not a score to add up.
        'Performance': games['Performance'] * 100,
        'Rating change': games['RatingChange'],
    })

    height = 35 * (len(table) + 1) + 3

    st.caption(f'{len(table)} games, newest first. Performance is the weight the rating gave '
               f'that game: 100 % is an average game for the pilot\'s team.')

    st.dataframe(
        table.style.format(
            subset=['Performance', 'Rating change'],
            formatter={'Performance': '{:.0f}%', 'Rating change': '{:+.2f}'},
        ).map(change_color, subset=['Rating change']),
        hide_index=True,
        column_order=['Date', 'Tournament', 'Division', 'Team', 'Opponent', 'Map', 'Mech',
                      'Class', 'Result', 'Kills', 'KMDDs', 'Assists', 'CD', 'DMG', 'MS',
                      'Performance', 'Rating change'],
        width='stretch',
        height=height,
    )

def mechs_tab(view):
    """Every mech variant the pilot used, sorted by games.

    `Mech` is the variant and `Chassis` the family: a chassis row hides which
    variant did the work, and under a tournament filter a chassis can look like
    one line when it was several mechs. No cut-off and no top-10 - the widest
    career holds 207 variants, and the table is meant to be read against the
    filters, so hiding rows would just hide the answer.
    """
    if view.empty:
        st.info('No games in the selected scope.')
        return

    table = view.groupby(['Mech', 'Chassis'], as_index=False).agg(
        Tonnage=('Tonnage', 'max'),
        Games=('MatchID', 'nunique'),
        Wins=('MatchResult', lambda values: int(values.eq('WIN').sum())),
        Losses=('MatchResult', lambda values: int(values.eq('LOSS').sum())),
        Kills=('Kills', 'mean'),
        KMDDs=('KillsMostDamage', 'mean'),
        Assists=('Assists', 'mean'),
        CD=('ComponentsDestroyed', 'mean'),
        DMG=('Damage', 'mean'),
        MS=('MatchScore', 'mean'),
        Deaths=('HealthPercentage', lambda values: float((values == 0).mean())),
    )
    table['WLR'] = table.apply(lambda row: safe_division(row['Wins'], row['Losses']), axis=1)
    table = table.sort_values(['Games', 'Mech'], ascending=[False, True])

    height = 35 * (len(table) + 1) + 3

    st.caption(f'{len(table)} mechs played, sorted by games.')

    st.dataframe(
        table.style.format(
            subset=['WLR', 'Kills', 'KMDDs', 'Assists', 'CD', 'DMG', 'MS', 'Deaths'],
            formatter='{:.2f}',
        ),
        hide_index=True,
        column_order=['Mech', 'Chassis', 'Tonnage', 'Games', 'Wins', 'Losses', 'WLR', 'Kills',
                      'KMDDs', 'Assists', 'CD', 'DMG', 'MS', 'Deaths'],
        width='stretch',
        height=height,
    )

def teams_tab(view):
    """Which teams the pilot played for, per tournament, most recent first."""
    if view.empty:
        st.info('No games in the selected scope.')
        return

    table = view.groupby(['Tournament', 'Division', 'TeamName'], as_index=False).agg(
        Games=('MatchID', 'nunique'),
        Wins=('MatchResult', lambda values: int(values.eq('WIN').sum())),
        Losses=('MatchResult', lambda values: int(values.eq('LOSS').sum())),
        LastPlayed=('CompleteTime', 'max'),
    ).rename(columns={'TeamName': 'Team'})

    table['WLR'] = table.apply(lambda row: safe_division(row['Wins'], row['Losses']), axis=1)
    table = table.sort_values('LastPlayed', ascending=False).drop(columns='LastPlayed')

    height = 35 * (len(table) + 1) + 3

    st.caption(f'{len(table)} tournament teams, most recent first.')

    st.dataframe(
        table.style.format(subset=['WLR'], formatter='{:.2f}'),
        hide_index=True,
        column_order=['Tournament', 'Division', 'Team', 'Games', 'Wins', 'Losses', 'WLR'],
        width='stretch',
        height=height,
    )

def pilot_tabs(df, pilot):
    """The tabs read the filtered frame, so the scope survives into the details.

    `df` is already narrowed to the selected pilot by the cascade; the whole database
    is read again for the career-wide derivations and for the rosters behind a click.
    """
    all_data = read_comp_data()
    history = pilot_history(all_data, pilot)
    view = history[history['MatchID'].isin(df['MatchID'])]

    overview, matches, mechs, teams = st.tabs(['Overview', 'Matches', 'Mechs', 'Teams'])

    with overview:
        overview_tab(all_data, history, view)

    with matches:
        matches_tab(view)

    with mechs:
        mechs_tab(view)

    with teams:
        teams_tab(view)

header()
df = read_comp_data()
scoped, options = filters(df)

if options['Username']:
    identity_block(options['Username'])
    pilot_tabs(scoped, options['Username'])
else:
    general_statistics(scoped)
