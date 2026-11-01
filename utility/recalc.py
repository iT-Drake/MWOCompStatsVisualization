import sqlite3 as sql
import pandas as pd

from time import time

from utility.database import DB_NAME, RATING_COLUMNS, clear_watermarks, fetch_comp_data, read_watermarks
from utility.rating import MWO_Rating_System

#---------------------------------------------------------------------
# RATING RECALCULATION
#
# The rating system is chronological and stateful: the rating of a match
# depends on every match that was played before it. When a match shows up
# late, everything that was played after it has to be recalculated.
#
# The recalculation is resumed instead of restarted. The database stores the
# full rating state of every pilot at every match (RatingBase holds the
# openskill mu, RatingUncertainty holds sigma), so the state at the cut
# point can be restored and the replay continues from there. The result is
# identical to a full recalculation.
#---------------------------------------------------------------------

def pending_recalc_point():
    """
    The earliest date that needs a recalculation, or None if there is nothing to do.

    The oldest uploaded match is the earliest point where anything can have
    changed. Rows without a rating are pulled in as well, so a match that
    entered the database without a marker still gets rated.
    """
    dates = [row[1] for row in read_watermarks()]

    conn = sql.connect(DB_NAME)
    unrated = conn.execute("SELECT MIN(CompleteTime) FROM CompData WHERE PilotRating IS NULL").fetchone()[0]
    conn.close()

    if unrated:
        dates.append(unrated)

    return min(dates) if dates else None

def _first_positions(df):
    """Position of the first row of every match."""
    return {match_id: positions.min() for match_id, positions in df.groupby('MatchID', sort=False).indices.items()}

def _restore_ratings(mwo_rating, history):
    """Restores the rating state of every pilot from the rows before the cut."""
    restored = 0

    if history.empty:
        return restored

    for _, row in history.groupby('Username').tail(1).iterrows():
        if pd.isna(row['RatingBase']) or pd.isna(row['RatingUncertainty']):
            continue
        mwo_rating.player_ratings[row['Username']] = mwo_rating.model.rating(
            name=row['Username'],
            mu=float(row['RatingBase']),
            sigma=float(row['RatingUncertainty'])
        )
        restored += 1

    return restored

def _write_ratings(sub_table):
    """Writes the recalculated ratings back into CompData."""
    conn = sql.connect(DB_NAME)

    try:
        sub_table.to_sql('temp_table', conn, if_exists='replace', index=False)
        conn.execute("CREATE INDEX idx_temp_table ON temp_table (MatchID, Team, Username, MatchResult)")
        conn.execute("""
            UPDATE CompData
            SET
                PilotRating = temp_table.PilotRating,
                Performance = temp_table.Performance,
                TeamRating = temp_table.TeamRating,
                OpponentRating = temp_table.OpponentRating,
                RatingBase = temp_table.RatingBase,
                RatingUncertainty = temp_table.RatingUncertainty
            FROM temp_table
            WHERE
                CompData.MatchID = temp_table.MatchID
                AND CompData.Team = temp_table.Team
                AND CompData.Username = temp_table.Username
                AND CompData.MatchResult = temp_table.MatchResult
            ;
            """)
        conn.commit()
        conn.execute("DROP TABLE temp_table")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def _count_unrated(recalc_from):
    """Rows at or after the recalculation point that still have no rating."""
    conn = sql.connect(DB_NAME)
    count = conn.execute(
        "SELECT COUNT(*) FROM CompData WHERE CompleteTime >= ? AND PilotRating IS NULL",
        (recalc_from,)
    ).fetchone()[0]
    conn.close()

    return count

def recalculate_ratings(recalc_from=None, progress=None):
    """
    Recalculates the ratings of every match at or after recalc_from.

    Args:
        recalc_from: ISO date of the earliest match to recalculate. When None the
            oldest pending watermark is used.
        progress: optional callable that receives (processed, total) matches.

    Returns a summary of what was done.
    """
    pending = read_watermarks()

    if recalc_from is None:
        recalc_from = pending_recalc_point()

    if recalc_from is None:
        return {'status': 'skipped', 'reason': 'nothing pending'}

    # Only the matches that are covered by this recalculation are cleared. A match
    # that is older than the recalculation point still has to be recalculated later.
    pending_ids = [match_id for match_id, complete_time in pending if complete_time >= recalc_from]

    started = time()

    df = fetch_comp_data()
    if df.empty:
        return {'status': 'skipped', 'reason': 'no data', 'recalc_from': recalc_from}

    # TeamSize has to be counted on the whole frame before it gets sliced
    team_counts = df.groupby(['Tournament', 'MatchID', 'TeamName'])['Username'].transform('count')
    df['TeamSize'] = team_counts.round().astype(int)

    cutoff = pd.to_datetime(recalc_from, format='ISO8601', utc=True)
    positions = df.index[df['CompleteTime'] >= cutoff]
    if len(positions) == 0:
        return {'status': 'skipped', 'reason': 'no matches to recalculate', 'recalc_from': recalc_from}

    start = positions[0]
    history = df.iloc[:start]
    window = df.iloc[start:].copy()

    mwo_rating = MWO_Rating_System()
    mwo_rating.processed_matches = history['MatchID'].nunique()
    restored = _restore_ratings(mwo_rating, history)

    sub_table = window[['MatchID', 'Team', 'Username', 'MatchResult']].copy()
    for column in RATING_COLUMNS:
        sub_table[column] = 0.0

    first_positions = _first_positions(df)
    match_ids = window['MatchID'].drop_duplicates().tolist()

    processed = 0
    for match_id, match in window.groupby('MatchID', sort=False):
        processed += 1
        records = mwo_rating.process_match(match, df.iloc[:first_positions[match_id]])

        for key, value in records.items():
            for column in RATING_COLUMNS:
                sub_table.loc[key, column] = value[column]

        if progress:
            progress(processed, len(match_ids))

    _write_ratings(sub_table)

    unrated = _count_unrated(recalc_from)
    if unrated:
        raise RuntimeError(f'{unrated} rows at or after {recalc_from} still have no rating')

    # Only the matches that were covered by this recalculation are cleared
    clear_watermarks(pending_ids)

    return {
        'status': 'done',
        'recalc_from': recalc_from,
        'matches': len(match_ids),
        'rows': len(window),
        'restored': restored,
        'cleared': len(pending_ids),
        'seconds': round(time() - started, 1),
    }
