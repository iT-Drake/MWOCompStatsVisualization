"""
Applies the pending schema migrations to a project database.

    python3 migrations/migrate.py --dry-run
    python3 migrations/migrate.py

Run it with the application stopped: a migration rewrites tables and takes a
write lock, and the app would be reading the database underneath it.

The schema version is kept in a Metadata table inside the database. When that
table is missing the database is unversioned (0), and every script is asked
whether it is already applied - that is how the first run on production works
out what it has to do without anyone inspecting the schema by hand.
"""

import argparse
import importlib.util
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MIGRATIONS_DIR.parent

# migration_helpers.py lives next to the scripts, utility/ above them.
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(MIGRATIONS_DIR))

import migration_helpers

METADATA_SQL = """CREATE TABLE IF NOT EXISTS Metadata (
    Key TEXT PRIMARY KEY,
    Value TEXT NOT NULL
)"""

REQUIRED_ATTRIBUTES = ('VERSION', 'RELEASE', 'DESCRIPTION', 'is_applied', 'apply')


def fail(message):
    sys.stdout.flush()
    print(f'error: {message}', file=sys.stderr)
    sys.exit(1)


def release_tuple(release):
    try:
        return tuple(int(part) for part in str(release).split('.'))
    except ValueError:
        fail(f'RELEASE must look like 0.5.0, got {release!r}')


def discover():
    """Loads the migration scripts in filename order and validates the set."""
    scripts = []
    for path in sorted(MIGRATIONS_DIR.glob('m[0-9]*.py')):
        spec = importlib.util.spec_from_file_location(f'migration_{path.stem}', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        missing = [name for name in REQUIRED_ATTRIBUTES if not hasattr(module, name)]
        if missing:
            fail(f'{path.name}: missing {", ".join(missing)}')
        scripts.append(module)

    if not scripts:
        fail('no migration scripts found')

    versions = [script.VERSION for script in scripts]
    expected = list(range(1, len(scripts) + 1))
    if versions != expected:
        fail(f'versions must be {expected[0]}..{expected[-1]} without gaps or duplicates, got {versions}')

    releases = [release_tuple(script.RELEASE) for script in scripts]
    if releases != sorted(releases):
        fail('RELEASE must not go backwards as VERSION grows')

    return scripts


def app_version():
    try:
        from utility.version import __version__
    except ImportError:
        return 'unknown'
    return __version__


def read_schema(conn):
    """(version, release) recorded in Metadata. 0 when the database is unversioned."""
    try:
        rows = conn.execute(
            "SELECT Key, Value FROM Metadata WHERE Key IN ('schema_version', 'schema_release')"
        ).fetchall()
    except sqlite3.OperationalError:
        return 0, None

    values = dict(rows)
    try:
        version = int(values.get('schema_version', 0))
    except ValueError:
        fail(f'schema_version is not an integer: {values["schema_version"]!r}')

    return version, values.get('schema_release')


def ensure_metadata(conn):
    """Creates the version table. It is infrastructure, not a migration: it has
    to exist before the first version can be read or written."""
    conn.execute(METADATA_SQL)


def stamp(conn, script, applied_at):
    """Records one script as applied."""
    values = {
        'schema_version': str(script.VERSION),
        'schema_release': script.RELEASE,
        'schema_applied_at': applied_at,
    }
    conn.executemany(
        "INSERT INTO Metadata (Key, Value) VALUES (?, ?) "
        "ON CONFLICT(Key) DO UPDATE SET Value = excluded.Value",
        values.items()
    )


def create_backup(conn, database, version):
    """Consistent copy of the database, taken through SQLite rather than the
    filesystem, so a -wal file cannot make it incomplete."""
    # UTC, like schema_applied_at: the server may not be in the same zone.
    stamp_time = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    name = f'{database.name}.backup-v{version}-{stamp_time}.sqlite3'
    backup = database.with_name(name)

    destination = sqlite3.connect(str(backup))
    try:
        conn.backup(destination)
    finally:
        destination.close()

    return backup


def print_plan(database, scripts, version, release, target):
    print(f'database : {database}')
    print(f'app      : {app_version()}')
    print(f'schema   : {version}' + (f' (release {release})' if release else ' (unversioned)'))
    print(f'target   : {target} (release {scripts[-1].RELEASE})')


def run_dry(conn, pending, applied_at):
    """Applies every pending script inside one transaction and rolls it back.

    This does not just list the plan, it proves the statements execute."""
    current = None
    work = 0
    notes = []
    conn.execute('BEGIN')
    try:
        ensure_metadata(conn)
        for script in pending:
            current = script
            if not script.is_applied(conn):
                result = script.apply(conn)
                work += 1
                notes.extend(f'script {script.VERSION}: {note}' for note in result or ())
            stamp(conn, script, applied_at)
    except Exception as exception:
        conn.execute('ROLLBACK')
        fail(f'dry run failed in migration {current.VERSION} ({current.DESCRIPTION}): {exception}')

    conn.execute('ROLLBACK')
    print(f'dry run  : {len(pending)} migration(s) checked, {work} had work to do, nothing written')
    for note in notes:
        print(f'   {note}')


def main():
    parser = argparse.ArgumentParser(description='Applies pending schema migrations.')
    parser.add_argument('--db', help='database file, defaults to DB_NAME from .streamlit/secrets.toml')
    parser.add_argument('--dry-run', action='store_true', help='run every pending migration, then roll back')
    parser.add_argument('--no-backup', action='store_true', help='do not copy the database before writing')
    args = parser.parse_args()

    scripts = discover()
    target = scripts[-1].VERSION

    if args.db:
        database = Path(args.db).resolve()
    else:
        try:
            from utility.globals import DB_NAME
        except Exception as exception:
            fail(f'cannot read DB_NAME from .streamlit/secrets.toml ({exception}); pass --db')
        database = (PROJECT_ROOT / DB_NAME).resolve()

    if not database.is_file():
        fail(f'database not found: {database}')

    conn = sqlite3.connect(str(database))
    conn.isolation_level = None  # explicit BEGIN/COMMIT, so DDL is transactional too

    if not migration_helpers.table_exists(conn, 'CompData'):
        fail(f'{database} has no CompData table - not a project database')

    version, release = read_schema(conn)

    print_plan(database, scripts, version, release, target)

    if version > target:
        fail(f'database schema {version} is newer than the code ({target}); update the code first')

    # A version that is recorded but whose change is not there means the
    # database and the record disagree, which is exactly the drift worth
    # stopping for.
    for script in scripts:
        if script.VERSION <= version and not script.is_applied(conn):
            fail(f'schema_version is {version}, but migration {script.VERSION} '
                 f'({script.DESCRIPTION}) does not look applied - fix the database or the check')

    pending = [script for script in scripts if script.VERSION > version]
    if not pending:
        print('nothing pending')
        conn.close()
        return

    print('pending  :')
    for script in pending:
        state = 'already applied, will stamp' if script.is_applied(conn) else 'will apply'
        print(f'  {script.VERSION}  {script.DESCRIPTION:<42} {state}')

    applied_at = datetime.now(timezone.utc).isoformat(timespec='seconds')

    if args.dry_run:
        run_dry(conn, pending, applied_at)
        conn.close()
        return

    ensure_metadata(conn)
    if not args.no_backup:
        print(f'backup   : {create_backup(conn, database, version)}')

    for script in pending:
        applied = script.is_applied(conn)

        conn.execute('BEGIN')
        try:
            notes = []
            if not applied:
                notes = script.apply(conn) or []
            stamp(conn, script, applied_at)
            conn.execute('COMMIT')
        except Exception as exception:
            conn.execute('ROLLBACK')
            fail(f'migration {script.VERSION} ({script.DESCRIPTION}) failed: {exception}')

        state = 'stamped' if applied else 'applied'
        print(f'{state} {script.VERSION}: {script.DESCRIPTION}')
        for note in notes:
            print(f'   {note}')

    print(f'done     : schema {target} (release {scripts[-1].RELEASE})')
    conn.close()


if __name__ == '__main__':
    main()
