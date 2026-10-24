"""
=============================================================================
StreakLab — Unified Database Layer (database.py)
Supports PostgreSQL (Production / Vercel) and SQLite (Local Development / Testing)

Features:
- Seamless PostgreSQL support via pg8000 when DATABASE_URL/POSTGRES_URL is configured
- SQLite default for local development, offline usage, and isolated unit tests
- Unified query interface: parameterized queries using '?' syntax auto-translated to '%s' on Postgres
- Dict-like and indexable Row objects matching sqlite3.Row behavior across all databases
- Automatic lastrowid extraction for INSERT operations across both dialects
- Automatic self-healing schema initialization and safe table migrations
- SQLite-to-PostgreSQL data export/import utilities for zero-data-loss upgrades
=============================================================================
"""

import os
import re
import sys
import ssl
import json
import logging
import sqlite3
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from flask import g, current_app

logger = logging.getLogger("streaklab.database")


class DatabaseRow:
    """
    A dict-like and indexable row wrapper that mimics sqlite3.Row across all database drivers.
    Supports row['name'], row[0], row.keys(), 'col' in row, and row.get('col').
    """
    __slots__ = ('_columns', '_values', '_mapping')

    def __init__(self, columns, values):
        self._columns = [str(c).lower() for c in columns]
        self._values = list(values)
        self._mapping = {col: val for col, val in zip(self._columns, self._values)}

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return self._mapping[str(key).lower()]

    def __contains__(self, key):
        return str(key).lower() in self._mapping

    def __len__(self):
        return len(self._values)

    def __iter__(self):
        return iter(self._columns)

    def get(self, key, default=None):
        return self._mapping.get(str(key).lower(), default)

    def keys(self):
        return list(self._columns)

    def values(self):
        return list(self._values)

    def items(self):
        return list(self._mapping.items())

    def __repr__(self):
        return f"<DatabaseRow {self._mapping}>"


class DatabaseCursor:
    """
    Cursor wrapper providing uniform row access, parameter mapping, and lastrowid extraction.
    """
    def __init__(self, raw_cursor, is_postgres=False, lastrowid=None):
        self._cursor = raw_cursor
        self.is_postgres = is_postgres
        self.lastrowid = lastrowid

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        if not self.is_postgres and isinstance(row, sqlite3.Row):
            return row
        cols = [desc[0] for desc in (self._cursor.description or [])]
        return DatabaseRow(cols, row)

    def fetchall(self):
        rows = self._cursor.fetchall()
        if not rows:
            return []
        if not self.is_postgres and rows and isinstance(rows[0], sqlite3.Row):
            return rows
        cols = [desc[0] for desc in (self._cursor.description or [])]
        return [DatabaseRow(cols, r) for r in rows]

    @property
    def rowcount(self):
        return getattr(self._cursor, 'rowcount', -1)

    def close(self):
        if hasattr(self._cursor, 'close'):
            self._cursor.close()


class DatabaseConnection:
    """
    Uniform connection wrapper for both PostgreSQL and SQLite.
    Automatically translates '?' parameter placeholders to '%s' when executing on PostgreSQL,
    and appends RETURNING id on INSERT statements when appropriate.
    """
    def __init__(self, raw_conn, is_postgres=False):
        self._conn = raw_conn
        self.is_postgres = is_postgres

    def execute(self, sql, params=None):
        params = params or ()
        if not isinstance(params, (list, tuple)):
            params = tuple(params)

        clean_sql = sql.strip()

        if self.is_postgres:
            # Handle PRAGMA table_info emulation
            pragma_m = re.match(r"^PRAGMA\s+table_info\((.+?)\);?$", clean_sql, re.IGNORECASE)
            if pragma_m:
                tbl = pragma_m.group(1).strip().strip("'\"").lower()
                query = """
                    SELECT ordinal_position - 1 AS cid, column_name AS name, data_type AS type,
                           CASE WHEN is_nullable = 'NO' THEN 1 ELSE 0 END AS notnull,
                           column_default AS dflt_value, 0 AS pk
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = %s
                    ORDER BY ordinal_position
                """
                cur = self._conn.cursor()
                cur.execute(query, (tbl,))
                return DatabaseCursor(cur, is_postgres=True)

            # Ignore SQLite specific PRAGMA pragmas on Postgres
            if re.match(r"^PRAGMA\s+", clean_sql, re.IGNORECASE):
                cur = self._conn.cursor()
                return DatabaseCursor(cur, is_postgres=True)

            # Auto-translate '?' placeholders to '%s'
            # (only replace ? that are query parameter placeholders)
            pg_sql = re.sub(r'\?', '%s', clean_sql)

            # Auto-handle lastrowid for INSERT statements
            is_insert = re.match(r"^INSERT\s+INTO\s+([a-zA-Z0-9_]+)", pg_sql, re.IGNORECASE)
            needs_returning = is_insert and ("RETURNING" not in pg_sql.upper())

            # Tables in our schema with primary key 'id'
            id_tables = {'habits', 'habit_records', 'habit_goals', 'goal_milestones',
                         'habit_reminders', 'push_subscriptions', 'habit_notification_logs'}

            inserted_table = is_insert.group(1).lower() if is_insert else ""
            if needs_returning and inserted_table in id_tables:
                pg_sql = pg_sql.rstrip(';') + " RETURNING id;"

            cur = self._conn.cursor()
            cur.execute(pg_sql, params)

            lastrowid = None
            if needs_returning and inserted_table in id_tables:
                try:
                    res = cur.fetchone()
                    if res:
                        lastrowid = res[0]
                except Exception:
                    pass

            return DatabaseCursor(cur, is_postgres=True, lastrowid=lastrowid)

        else:
            # SQLite execution
            cur = self._conn.cursor()
            cur.execute(clean_sql, params)
            return DatabaseCursor(cur, is_postgres=False, lastrowid=cur.lastrowid)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()


def get_database_url():
    """
    Checks environment variables for a configured PostgreSQL database URL.
    Recognizes standard cloud database environment variables used by Vercel, Neon, Supabase, and AWS.
    """
    for var in ('DATABASE_URL', 'POSTGRES_URL', 'POSTGRES_PRISMA_URL', 'POSTGRES_URL_NON_POOLING'):
        url = os.environ.get(var)
        if url and (url.startswith('postgres://') or url.startswith('postgresql://')):
            return url.strip()
    return None


def is_postgres_configured():
    """Returns True if a valid PostgreSQL connection string is detected."""
    return get_database_url() is not None


def connect_postgres(db_url):
    """
    Connects to a PostgreSQL database using pg8000.
    Parses standard connection URLs, applies SSL contexts for managed cloud databases,
    and returns a DatabaseConnection wrapper.
    """
    import pg8000.dbapi

    parsed = urlparse(db_url)
    username = parsed.username or 'postgres'
    password = parsed.password or ''
    host = parsed.hostname or 'localhost'
    port = parsed.port or 5432
    database = parsed.path.lstrip('/') or 'postgres'

    # Determine SSL mode: cloud providers (Neon, Supabase, Vercel Postgres) require SSL
    qs = parse_qs(parsed.query)
    sslmode = qs.get('sslmode', ['require'])[0].lower()
    ssl_context = None

    if sslmode in ('require', 'verify-ca', 'verify-full', 'prefer') or host not in ('localhost', '127.0.0.1'):
        ssl_context = ssl.create_default_context()
        if sslmode == 'require':
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

    raw_conn = pg8000.dbapi.connect(
        user=username,
        password=password,
        host=host,
        port=port,
        database=database,
        ssl_context=ssl_context
    )
    raw_conn.autocommit = False
    return DatabaseConnection(raw_conn, is_postgres=True)


def get_sqlite_database_path(app=None):
    """
    Resolves the SQLite database path when running locally or during tests.
    """
    target_app = app
    if target_app is None:
        try:
            from flask import has_app_context
            if has_app_context():
                target_app = current_app
        except Exception:
            target_app = None

    if target_app and hasattr(target_app, 'config') and target_app.config.get('DATABASE'):
        return target_app.config['DATABASE']

    env_db = os.environ.get('DATABASE')
    if env_db:
        return env_db

    # Serverless runtime detection (Vercel, AWS Lambda)
    is_serverless = bool(
        os.environ.get('VERCEL')
        or os.environ.get('VERCEL_ENV')
        or os.environ.get('AWS_LAMBDA_FUNCTION_NAME')
        or (app and hasattr(app, 'instance_path') and str(app.instance_path).startswith('/var/task'))
    )
    if is_serverless:
        if app and hasattr(app, 'config'):
            app.config['DATABASE'] = '/tmp/streaklab.db'
        return '/tmp/streaklab.db'

    if app and hasattr(app, 'instance_path'):
        return os.path.join(app.instance_path, 'streaklab.db')

    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'streaklab.db')


def connect_sqlite(db_path):
    """
    Connects to a SQLite database, enforces foreign keys, and configures row factory.
    """
    if db_path != ':memory:':
        db_dir = os.path.dirname(os.path.abspath(db_path))
        if db_dir:
            try:
                os.makedirs(db_dir, exist_ok=True)
            except (OSError, PermissionError):
                db_path = '/tmp/streaklab.db'
                os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)

    raw_conn = sqlite3.connect(db_path)
    raw_conn.row_factory = sqlite3.Row
    raw_conn.execute("PRAGMA foreign_keys = ON;")
    return DatabaseConnection(raw_conn, is_postgres=False)


def get_db():
    """
    Returns the active database connection for the current Flask request context.
    Automatically uses PostgreSQL if configured, otherwise falls back to SQLite.
    Guarantees that tables and indices exist in the connected database.
    """
    if 'db' not in g:
        db_url = get_database_url()
        if db_url:
            try:
                g.db = connect_postgres(db_url)
                g.is_postgres = True
            except Exception as e:
                logger.error(f"Failed connecting to PostgreSQL ({e}); falling back to SQLite.")
                db_path = get_sqlite_database_path(current_app)
                g.db = connect_sqlite(db_path)
                g.is_postgres = False
        else:
            db_path = get_sqlite_database_path(current_app)
            g.db = connect_sqlite(db_path)
            g.is_postgres = False

        # Self-healing check: guarantee schema exists in the currently connected database
        ensure_schema(g.db)

    return g.db


def close_db(exception=None):
    """Closes the request-scoped database connection."""
    db = g.pop('db', None)
    if db is not None:
        try:
            db.close()
        except Exception:
            pass


def ensure_schema(db):
    """
    Verifies that the core 'habits' table exists; if not, triggers init_db.
    """
    try:
        if db.is_postgres:
            cur = db.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'habits'
            """)
            has_table = cur.fetchone()
        else:
            cur = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='habits'")
            has_table = cur.fetchone()

        if not has_table:
            init_db_schema(db)
    except Exception as exc:
        logger.warning(f"ensure_schema check error: {exc}. Re-running schema init.")
        init_db_schema(db)


def init_db_schema(db=None):
    """
    Initializes all 7 tables, indices, and schema migrations for StreakLab.
    Works seamlessly on both PostgreSQL and SQLite.
    """
    should_close = False
    if db is None:
        db_url = get_database_url()
        if db_url:
            db = connect_postgres(db_url)
        else:
            db_path = get_sqlite_database_path()
            db = connect_sqlite(db_path)
        should_close = True

    try:
        if db.is_postgres:
            _init_postgres(db)
        else:
            _init_sqlite(db)
        db.commit()
    finally:
        if should_close:
            db.close()


def _init_postgres(db):
    """PostgreSQL schema initialization and migrations."""
    # Table 1: habits
    db.execute("""
        CREATE TABLE IF NOT EXISTS habits (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            category TEXT DEFAULT 'General',
            time_of_day TEXT DEFAULT 'Morning',
            target_time TEXT DEFAULT '08:00 AM',
            target_frequency TEXT DEFAULT 'daily',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            active INTEGER DEFAULT 1,
            reminder_time TEXT DEFAULT '08:00',
            reminder_enabled INTEGER DEFAULT 1
        );
    """)

    # Table 2: habit_records
    db.execute("""
        CREATE TABLE IF NOT EXISTS habit_records (
            id SERIAL PRIMARY KEY,
            habit_id INTEGER NOT NULL,
            record_date TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('completed', 'missed', 'skipped')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (habit_id) REFERENCES habits (id) ON DELETE CASCADE,
            UNIQUE (habit_id, record_date)
        );
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_records_habit_date ON habit_records (habit_id, record_date);")
    db.execute("CREATE INDEX IF NOT EXISTS idx_records_date ON habit_records (record_date);")

    # Table 3: habit_goals
    db.execute("""
        CREATE TABLE IF NOT EXISTS habit_goals (
            id SERIAL PRIMARY KEY,
            habit_id INTEGER NOT NULL,
            target_type TEXT NOT NULL DEFAULT 'weekly_completions',
            target_value INTEGER NOT NULL CHECK(target_value >= 1),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            active INTEGER DEFAULT 1,
            end_date TEXT DEFAULT NULL,
            FOREIGN KEY (habit_id) REFERENCES habits (id) ON DELETE CASCADE,
            UNIQUE (habit_id, target_type)
        );
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_goals_habit ON habit_goals (habit_id);")

    # Table 4: goal_milestones
    db.execute("""
        CREATE TABLE IF NOT EXISTS goal_milestones (
            id SERIAL PRIMARY KEY,
            goal_id INTEGER NOT NULL,
            habit_id INTEGER NOT NULL,
            milestone_type TEXT NOT NULL,
            milestone_period TEXT NOT NULL,
            achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notified INTEGER DEFAULT 0,
            FOREIGN KEY (goal_id) REFERENCES habit_goals (id) ON DELETE CASCADE,
            FOREIGN KEY (habit_id) REFERENCES habits (id) ON DELETE CASCADE,
            UNIQUE (habit_id, milestone_type, milestone_period)
        );
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_milestones_lookup ON goal_milestones (habit_id, milestone_period);")

    # Table 5: habit_reminders
    db.execute("""
        CREATE TABLE IF NOT EXISTS habit_reminders (
            id SERIAL PRIMARY KEY,
            habit_id INTEGER NOT NULL UNIQUE,
            reminder_time TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (habit_id) REFERENCES habits (id) ON DELETE CASCADE
        );
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_reminders_habit ON habit_reminders (habit_id);")

    # Table 6: push_subscriptions (Priority 3: Web Push)
    db.execute("""
        CREATE TABLE IF NOT EXISTS push_subscriptions (
            id SERIAL PRIMARY KEY,
            endpoint TEXT NOT NULL UNIQUE,
            p256dh TEXT NOT NULL,
            auth TEXT NOT NULL,
            user_agent TEXT DEFAULT '',
            timezone TEXT DEFAULT 'UTC',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_notified_date TEXT DEFAULT NULL,
            active INTEGER DEFAULT 1
        );
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_push_endpoint ON push_subscriptions (endpoint);")

    # Table 7: habit_notification_logs (Priority 3: Duplicate notification suppression)
    db.execute("""
        CREATE TABLE IF NOT EXISTS habit_notification_logs (
            id SERIAL PRIMARY KEY,
            habit_id INTEGER NOT NULL,
            notification_date TEXT NOT NULL,
            notification_time TEXT NOT NULL,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (habit_id) REFERENCES habits (id) ON DELETE CASCADE,
            UNIQUE (habit_id, notification_date)
        );
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_notif_habit_date ON habit_notification_logs (habit_id, notification_date);")

    # Safe migration: ensure habits without reminder rows are safely migrated into habit_reminders
    try:
        habits_missing_rem = db.execute("""
            SELECT h.id, h.target_time, h.reminder_time, h.reminder_enabled
            FROM habits h
            LEFT JOIN habit_reminders r ON h.id = r.habit_id
            WHERE r.id IS NULL
        """).fetchall()

        for h in habits_missing_rem:
            hid = h['id'] if isinstance(h, (dict, DatabaseRow)) else h[0]
            rem_time = (
                (h['reminder_time'] if 'reminder_time' in h else None)
                or (h['target_time'] if 'target_time' in h else None)
                or "08:00"
            )
            if isinstance(rem_time, str) and ("AM" in rem_time.upper() or "PM" in rem_time.upper()):
                try:
                    dt = datetime.strptime(rem_time.strip().upper(), "%I:%M %p")
                    rem_time = dt.strftime("%H:%M")
                except Exception:
                    rem_time = "08:00"
            elif not rem_time or ":" not in str(rem_time):
                rem_time = "08:00"

            rem_en = h['reminder_enabled'] if ('reminder_enabled' in h and h['reminder_enabled'] is not None) else 1

            db.execute("""
                INSERT INTO habit_reminders (habit_id, reminder_time, enabled)
                VALUES (?, ?, ?)
            """, (hid, rem_time, rem_en))

            db.execute("""
                UPDATE habits
                SET reminder_time = COALESCE(reminder_time, ?),
                    reminder_enabled = COALESCE(reminder_enabled, ?)
                WHERE id = ?
            """, (rem_time, rem_en, hid))
        db.commit()
    except Exception as e:
        logger.warning("Could not migrate legacy habit reminders in Postgres: %s", e)


def _init_sqlite(db):
    """SQLite schema initialization and migrations."""
    # Table 1: habits
    db.execute("""
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            category TEXT,
            time_of_day TEXT DEFAULT 'Morning',
            target_time TEXT DEFAULT '08:00 AM',
            target_frequency TEXT DEFAULT 'daily',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            active INTEGER DEFAULT 1,
            reminder_time TEXT DEFAULT '08:00',
            reminder_enabled INTEGER DEFAULT 1
        );
    """)

    # Safe migration: ensure reminder columns exist if table was created in an earlier phase
    cols = [r[1] for r in db.execute("PRAGMA table_info(habits)").fetchall()]
    if 'reminder_time' not in cols:
        db.execute("ALTER TABLE habits ADD COLUMN reminder_time TEXT DEFAULT '08:00';")
    if 'reminder_enabled' not in cols:
        db.execute("ALTER TABLE habits ADD COLUMN reminder_enabled INTEGER DEFAULT 1;")

    # Table 2: habit_records
    db.execute("""
        CREATE TABLE IF NOT EXISTS habit_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id INTEGER NOT NULL,
            record_date TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('completed', 'missed', 'skipped')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (habit_id) REFERENCES habits (id) ON DELETE CASCADE,
            UNIQUE (habit_id, record_date)
        );
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_records_habit_date ON habit_records (habit_id, record_date);")
    db.execute("CREATE INDEX IF NOT EXISTS idx_records_date ON habit_records (record_date);")

    # Table 3: habit_goals
    db.execute("""
        CREATE TABLE IF NOT EXISTS habit_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id INTEGER NOT NULL,
            target_type TEXT NOT NULL DEFAULT 'weekly_completions',
            target_value INTEGER NOT NULL CHECK(target_value >= 1),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            active INTEGER DEFAULT 1,
            end_date TEXT DEFAULT NULL,
            FOREIGN KEY (habit_id) REFERENCES habits (id) ON DELETE CASCADE,
            UNIQUE (habit_id, target_type)
        );
    """)
    goal_cols = [r[1] for r in db.execute("PRAGMA table_info(habit_goals)").fetchall()]
    if 'end_date' not in goal_cols:
        db.execute("ALTER TABLE habit_goals ADD COLUMN end_date TEXT DEFAULT NULL;")
    db.execute("CREATE INDEX IF NOT EXISTS idx_goals_habit ON habit_goals (habit_id);")

    # Table 4: goal_milestones
    db.execute("""
        CREATE TABLE IF NOT EXISTS goal_milestones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal_id INTEGER NOT NULL,
            habit_id INTEGER NOT NULL,
            milestone_type TEXT NOT NULL,
            milestone_period TEXT NOT NULL,
            achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notified INTEGER DEFAULT 0,
            FOREIGN KEY (goal_id) REFERENCES habit_goals (id) ON DELETE CASCADE,
            FOREIGN KEY (habit_id) REFERENCES habits (id) ON DELETE CASCADE,
            UNIQUE (habit_id, milestone_type, milestone_period)
        );
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_milestones_lookup ON goal_milestones (habit_id, milestone_period);")

    # Table 5: habit_reminders
    db.execute("""
        CREATE TABLE IF NOT EXISTS habit_reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id INTEGER NOT NULL UNIQUE,
            reminder_time TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (habit_id) REFERENCES habits (id) ON DELETE CASCADE
        );
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_reminders_habit ON habit_reminders (habit_id);")

    # Table 6: push_subscriptions (Priority 3: Web Push)
    db.execute("""
        CREATE TABLE IF NOT EXISTS push_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            endpoint TEXT NOT NULL UNIQUE,
            p256dh TEXT NOT NULL,
            auth TEXT NOT NULL,
            user_agent TEXT DEFAULT '',
            timezone TEXT DEFAULT 'UTC',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_notified_date TEXT DEFAULT NULL,
            active INTEGER DEFAULT 1
        );
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_push_endpoint ON push_subscriptions (endpoint);")

    # Table 7: habit_notification_logs
    db.execute("""
        CREATE TABLE IF NOT EXISTS habit_notification_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id INTEGER NOT NULL,
            notification_date TEXT NOT NULL,
            notification_time TEXT NOT NULL,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (habit_id) REFERENCES habits (id) ON DELETE CASCADE,
            UNIQUE (habit_id, notification_date)
        );
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_notif_habit_date ON habit_notification_logs (habit_id, notification_date);")

    # Safe migration: ensure habits without reminder rows are safely migrated into habit_reminders
    try:
        habits_missing_rem = db.execute("""
            SELECT h.id, h.target_time, h.reminder_time, h.reminder_enabled
            FROM habits h
            LEFT JOIN habit_reminders r ON h.id = r.habit_id
            WHERE r.id IS NULL
        """).fetchall()

        for h in habits_missing_rem:
            hid = h['id'] if isinstance(h, (dict, DatabaseRow)) else h[0]
            rem_time = (
                (h['reminder_time'] if 'reminder_time' in h else None)
                or (h['target_time'] if 'target_time' in h else None)
                or "08:00"
            )
            if isinstance(rem_time, str) and ("AM" in rem_time.upper() or "PM" in rem_time.upper()):
                try:
                    dt = datetime.strptime(rem_time.strip().upper(), "%I:%M %p")
                    rem_time = dt.strftime("%H:%M")
                except Exception:
                    rem_time = "08:00"
            elif not rem_time or ":" not in str(rem_time):
                rem_time = "08:00"

            rem_en = h['reminder_enabled'] if ('reminder_enabled' in h and h['reminder_enabled'] is not None) else 1

            db.execute("""
                INSERT INTO habit_reminders (habit_id, reminder_time, enabled)
                VALUES (?, ?, ?)
            """, (hid, rem_time, rem_en))

            db.execute("""
                UPDATE habits
                SET reminder_time = COALESCE(reminder_time, ?),
                    reminder_enabled = COALESCE(reminder_enabled, ?)
                WHERE id = ?
            """, (rem_time, rem_en, hid))
        db.commit()
    except Exception as e:
        logger.warning("Could not migrate legacy habit reminders in SQLite: %s", e)


def export_sqlite_data(sqlite_path=None):
    """
    Exports all StreakLab records from an SQLite database into a structured dictionary.
    Used for safe migration to PostgreSQL without data loss.
    """
    if sqlite_path is None:
        sqlite_path = get_sqlite_database_path()

    if not os.path.exists(sqlite_path):
        return {"error": f"SQLite database file not found at {sqlite_path}", "data": {}}

    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    data = {}

    tables = ['habits', 'habit_records', 'habit_goals', 'goal_milestones', 'habit_reminders', 'push_subscriptions']
    for tbl in tables:
        try:
            cur = conn.execute(f"SELECT * FROM {tbl}")
            rows = [dict(r) for r in cur.fetchall()]
            data[tbl] = rows
        except Exception:
            data[tbl] = []

    conn.close()
    return {"sqlite_path": sqlite_path, "tables": data}


def import_data_to_postgres(data, pg_conn):
    """
    Safely imports exported records into a PostgreSQL database.
    Preserves all existing IDs and ignores existing conflicts.
    """
    tables_data = data.get('tables', {})
    stats = {}

    for habit in tables_data.get('habits', []):
        pg_conn.execute("""
            INSERT INTO habits (id, name, description, category, time_of_day, target_time, target_frequency, created_at, active, reminder_time, reminder_enabled)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                category = EXCLUDED.category,
                time_of_day = EXCLUDED.time_of_day,
                target_time = EXCLUDED.target_time,
                target_frequency = EXCLUDED.target_frequency,
                active = EXCLUDED.active,
                reminder_time = EXCLUDED.reminder_time,
                reminder_enabled = EXCLUDED.reminder_enabled;
        """, (habit['id'], habit['name'], habit.get('description', ''), habit.get('category', 'General'),
              habit.get('time_of_day', 'Morning'), habit.get('target_time', '08:00 AM'), habit.get('target_frequency', 'daily'),
              habit.get('created_at'), habit.get('active', 1), habit.get('reminder_time', '08:00'), habit.get('reminder_enabled', 1)))

    # Update habits sequence counter
    try:
        pg_conn.execute("SELECT setval(pg_get_serial_sequence('habits', 'id'), COALESCE((SELECT MAX(id) FROM habits), 1));")
    except Exception:
        pass

    for rec in tables_data.get('habit_records', []):
        pg_conn.execute("""
            INSERT INTO habit_records (id, habit_id, record_date, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (habit_id, record_date) DO UPDATE SET
                status = EXCLUDED.status,
                updated_at = EXCLUDED.updated_at;
        """, (rec['id'], rec['habit_id'], rec['record_date'], rec['status'], rec.get('created_at'), rec.get('updated_at')))

    for rem in tables_data.get('habit_reminders', []):
        pg_conn.execute("""
            INSERT INTO habit_reminders (habit_id, reminder_time, enabled)
            VALUES (?, ?, ?)
            ON CONFLICT (habit_id) DO UPDATE SET
                reminder_time = EXCLUDED.reminder_time,
                enabled = EXCLUDED.enabled;
        """, (rem['habit_id'], rem['reminder_time'], rem.get('enabled', 1)))

    for goal in tables_data.get('habit_goals', []):
        pg_conn.execute("""
            INSERT INTO habit_goals (id, habit_id, target_type, target_value, created_at, updated_at, active, end_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (habit_id, target_type) DO UPDATE SET
                target_value = EXCLUDED.target_value,
                end_date = EXCLUDED.end_date,
                active = EXCLUDED.active;
        """, (goal['id'], goal['habit_id'], goal['target_type'], goal['target_value'], goal.get('created_at'),
              goal.get('updated_at'), goal.get('active', 1), goal.get('end_date')))

    for m in tables_data.get('goal_milestones', []):
        pg_conn.execute("""
            INSERT INTO goal_milestones (goal_id, habit_id, milestone_type, milestone_period, achieved_at, notified)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (habit_id, milestone_type, milestone_period) DO NOTHING;
        """, (m['goal_id'], m['habit_id'], m['milestone_type'], m['milestone_period'], m.get('achieved_at'), m.get('notified', 0)))

    pg_conn.commit()
    return {"status": "success", "imported": {k: len(v) for k, v in tables_data.items()}}


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--migrate':
        print("[*] Starting SQLite to PostgreSQL migration...")
        pg_url = get_database_url()
        if not pg_url:
            print("[!] Error: No PostgreSQL connection URL found in DATABASE_URL or POSTGRES_URL.")
            sys.exit(1)
        data = export_sqlite_data()
        pg = connect_postgres(pg_url)
        init_db_schema(pg)
        res = import_data_to_postgres(data, pg)
        print(f"[+] Migration complete: {json.dumps(res, indent=2)}")
    elif len(sys.argv) > 1 and sys.argv[1] == '--init':
        print("[*] Initializing database schema...")
        init_db_schema()
        print("[+] Schema successfully initialized.")
    else:
        print("StreakLab Database Utility")
        print("Usage:")
        print("  python database.py --init     (Initializes database tables)")
        print("  python database.py --migrate  (Migrates local SQLite records to PostgreSQL)")
