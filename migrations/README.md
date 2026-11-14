# Schema migrations

Brings a database up to the schema the current code expects. One Python runner,
one small script per release that changed the schema, and a version record
inside the database.

Run it with the **application stopped** — a migration writes to the database and
the app would be reading it underneath.

```
python3 migrations/migrate.py --dry-run     # prove the statements, write nothing
python3 migrations/migrate.py               # apply
sqlite3 database.sqlite3 "VACUUM;"          # shrinks database
```

`--db` is optional and defaults to `DB_NAME` from `.streamlit/secrets.toml`.
`--no-backup` skips the copy the runner takes before writing.

---

## The version record

A `Metadata(Key, Value)` table in the same database:

| key | example | meaning |
| --- | --- | --- |
| `schema_version` | `2` | ordering integer, the guards compare this |
| `schema_release` | `0.5.0` | the release the last applied script shipped with |
| `schema_applied_at` | `2026-11-01T14:32:07+00:00` | when that script was recorded |

The integer decides what runs; the release string is a label. Two scripts may
ship in one release, and a database can be on an older schema than the code
running against it, so the app version (`utility/version.py`) is deliberately
**not** written here.

`Metadata` is infrastructure, not a migration: the runner creates it with
`CREATE TABLE IF NOT EXISTS` before it does anything else, because it cannot
read a version out of a table that a migration would have to create first. Its
**absence is the "unversioned database" signal** — version 0.

## Timeline

| schema | release | change |
| --- | --- | --- |
| 0 | before 0.4.0 | no rating columns, no `Watermarks` |
| 1 | 0.4.0 | six rating columns on `CompData` (`m001`) |
| 2 | 0.5.0 | `Watermarks` table (`m002`); `Metadata` appears with the tool |
| 3 | 0.6.0 | drop the retired `Rating` / `Rating_change` columns (`m003`); run `VACUUM` by hand afterwards |

`m003` drops columns with `ALTER TABLE ... DROP COLUMN`, which SQLite has had since
3.35 (the project venv runs 3.35.5). Older SQLite refuses the statement and the runner
reports it — recreate the table instead of working around it.

Production was on 0.4.0 when the tool shipped, so its first run creates
`Metadata`, finds the rating columns already there and stamps `1`, then creates
`Watermarks` and stamps `2`. No column is touched and no row is rewritten.

`initialize_database()` also creates `Watermarks` on the first write, so either
order converges. Migrating first is the honest one: the version record then
matches reality instead of being a stamp over something the app already did.

---

## Writing a migration

One file per schema change, named `mNNN_short_description.py`, where `NNN`
continues the sequence. It must define:

```python
VERSION = 3                          # ordering integer, no gaps, no duplicates
RELEASE = '0.6.0'                    # the release that ships this change
DESCRIPTION = 'drop the retired Elo columns'

def is_applied(conn):
    """True when this database already has the change."""

def apply(conn):
    """Makes the change. Runs inside a transaction with the version stamp.
    May return notes for the runner to print, e.g. ['added CompData.Foo']."""
```

**`is_applied()` is mandatory and is what establishes the baseline.** On an
unversioned database the runner cannot know whether a step was applied years
ago or never; it asks the script. If the check says "already there", the script
is stamped instead of re-applied. Writing `return False` is therefore a
deliberate statement that the step must run on every database that reaches it.

Rules:

- **SQL stays inline and frozen.** A migration is a historical record: `m002`
  must create the `Watermarks` table *as it was in 0.5.0*. Do not import DDL
  from `utility/database.py` — when that helper grows a column in 0.7, every old
  database brought up to date would silently get the 0.7 table instead.
- **Stdlib only** (`sqlite3`, plus `migration_helpers` next to the scripts).
  Importing `utility.*` pulls in Streamlit and pandas for no reason.
- **Forward only.** No `down()`. Rolling back a data change has no safe general
  answer, and one exception would turn this into a framework.
- **One change per script.** If it fails halfway, the version tells you exactly
  where it stopped.

`migration_helpers.py` has `table_exists()`, `column_names()`, `column_exists()`.

### Adding one

1. Pick the next `VERSION` and the release that will ship it.
2. Write the file above, with a real `is_applied()`.
3. Run `--dry-run` against a **copy** of the live database.
4. Run it for real against that copy, then check the schema and the app.
5. Nothing else to register — scripts are discovered by filename and validated
   as a contiguous `1..N` sequence.

## Update procedure

```
stop the app
back up the database
update the code
python3 migrations/migrate.sh --dry-run
python3 migrations/migrate.sh
start the app
```

`migrate.sh` is the same runner: it changes into the project root first, so
`.streamlit/secrets.toml` is found the way Streamlit finds it. It is committed
with LF line endings (`.gitattributes`); a CRLF checkout gives
`bad interpreter: /usr/bin/env bash^M`.

## What the runner guarantees

- **Nothing pending** → prints the version and exits 0. It does not rewrite
  `schema_applied_at`; that key means "when the schema changed", not "when it was
  last looked at".
- **One transaction per script**, with the stamp in the same transaction. SQLite
  DDL is transactional, so a failure leaves the previous version in place and
  the next run resumes at the failed script.
- **Backup before writing**, taken through `Connection.backup()` rather than a
  file copy so a `-wal` file cannot make it incomplete. It lands next to the
  database as `<name>.sqlite3.backup-vN-<timestamp>.sqlite3`.

And it refuses to run when:

| condition | why |
| --- | --- |
| `schema_version` > the newest script | database ahead of the code: deploy the code first |
| versions are not a contiguous `1..N` | a script was lost in a merge |
| `RELEASE` goes backwards as `VERSION` grows | the timeline no longer reads |
| a recorded version's `is_applied()` is false | the record and the schema disagree |
| the file has no `CompData` table | not a project database |
| `Metadata` exists but `schema_version` is not an integer | unreadable record, do not guess |

## What it does not do

Data migrations. A rating recalculation is expensive, changes visible numbers
and needs its own decision — `utility/recalc.py` stays out of this tool. Neither
does it rotate backups, verify checksums, or run `VACUUM`: after a migration
that drops a column, run `VACUUM` by hand once the app is happy.
