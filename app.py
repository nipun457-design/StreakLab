"""
=============================================================================
StreakLab — Habit Pattern Detector
Backend Server: app.py (Flask + SQLite)

Phase 2B: SQLite Database Integration & RESTful API
- SQLite database auto-initialization in 'instance/streaklab.db'
- PRAGMA foreign_keys = ON enforcement and parameterized SQL queries
- Complete REST API for Habits (GET, POST, GET/:id, PUT/:id, DELETE/:id)
- Complete REST API for Daily Records (GET, POST, GET /habits/:id/records)
- Database-backed streak calculation & weekly consistency aggregation
=============================================================================
"""

import os
import csv
import io
import re
import logging
import sqlite3
from datetime import datetime, timedelta, date
from flask import Flask, render_template, jsonify, request, g, Response
from pattern_engine import (
    analyze_habit_patterns,
    analyze_single_habit,
    get_habit_analytics,
    get_calendar_heatmap,
    generate_weekly_review,
    calculate_goals_and_milestones,
    generate_progress_report,
    calculate_current_streak,
    calculate_best_streak,
    parse_target_date
)
import ai_explainer

logger = logging.getLogger("streaklab.app")

# Initialize Flask application
# Initialize Flask application
app = Flask(__name__, template_folder='templates', static_folder='static')
application = app  # WSGI compatibility for Vercel / serverless runtimes


def get_database_path():
    """
    Resolves and configures the SQLite database path.
    1. If DATABASE environment variable is set, it takes top precedence.
    2. If running on Vercel or any serverless runtime (VERCEL, AWS_LAMBDA, LAMBDA_TASK_ROOT, or /var/task),
       strictly uses '/tmp/streaklab.db' BEFORE attempting any directory creation or SQLite connection.
    3. In local development, uses Flask's instance directory 'instance/streaklab.db'.
    """
    env_db = os.environ.get('DATABASE')
    if env_db:
        return env_db

    # Serverless runtime detection (Vercel, AWS Lambda, or /var/task deployment root)
    is_serverless = bool(
        os.environ.get('VERCEL')
        or os.environ.get('VERCEL_ENV')
        or os.environ.get('VERCEL_REGION')
        or os.environ.get('AWS_LAMBDA_FUNCTION_NAME')
        or os.environ.get('LAMBDA_TASK_ROOT')
        or os.environ.get('NOW_REGION')
        or (hasattr(app, 'instance_path') and str(app.instance_path).startswith('/var/task'))
        or (hasattr(app, 'root_path') and str(app.root_path).startswith('/var/task'))
    )
    if is_serverless:
        resolved = '/tmp/streaklab.db'
        app.config['DATABASE'] = resolved
        return resolved

    # Local development: use instance/streaklab.db without premature creation
    resolved = os.path.join(app.instance_path, 'streaklab.db')
    app.config['DATABASE'] = resolved
    return resolved


get_default_database_path = get_database_path

# Set database path inside Flask's configuration
app.config.setdefault('DATABASE', get_database_path())


# ---------------------------------------------------------------------------
# DATABASE CONNECTION & INITIALIZATION
# ---------------------------------------------------------------------------

def get_db():
    """
    Opens a unique database connection per request if not already open,
    attaching it to Flask's request-scoped 'g' context.
    Enforces SQLite foreign key constraints and enables dict-like row access.
    Uses the exact same resolved database path as init_db().
    """
    if 'db' not in g:
        db_path = app.config.get('DATABASE') or get_database_path()
        app.config['DATABASE'] = db_path

        if db_path != ':memory:':
            db_dir = os.path.dirname(os.path.abspath(db_path))
            if db_dir:
                try:
                    os.makedirs(db_dir, exist_ok=True)
                except (OSError, PermissionError):
                    db_path = '/tmp/streaklab.db'
                    app.config['DATABASE'] = db_path
                    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)

        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
        # Crucial: SQLite turns foreign keys OFF by default per connection
        g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    """Closes the database connection at the end of each request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """
    Creates tables and indices in SQLite if they do not already exist.
    Called automatically on application startup.
    Ensures both init_db() and all runtime queries use the same resolved database path.
    """
    db_path = app.config.get('DATABASE') or get_database_path()
    app.config['DATABASE'] = db_path

    if db_path != ':memory:':
        db_dir = os.path.dirname(os.path.abspath(db_path))
        if db_dir:
            try:
                os.makedirs(db_dir, exist_ok=True)
            except (OSError, PermissionError):
                db_path = '/tmp/streaklab.db'
                app.config['DATABASE'] = db_path
                os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    with conn:
        # Table 1: habits
        conn.execute("""
            CREATE TABLE IF NOT EXISTS habits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                category TEXT,
                time_of_day TEXT DEFAULT 'Morning',
                target_time TEXT DEFAULT '08:00 AM',
                target_frequency TEXT DEFAULT 'daily',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                active INTEGER DEFAULT 1
            );
        """)

        # Table 2: habit_records
        conn.execute("""
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

        # Performance indices for fast queries on habit history and date lookups
        conn.execute("CREATE INDEX IF NOT EXISTS idx_records_habit_date ON habit_records (habit_id, record_date);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_records_date ON habit_records (record_date);")

        # Table 3: habit_goals (Phase 7 & 8: Weekly, Streak, and Total Targets)
        # Safe migration if table previously had target_value <= 7 check constraint
        cur = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='habit_goals'")
        goal_table_row = cur.fetchone()
        if goal_table_row and "target_value <= 7" in goal_table_row[0]:
            conn.execute("PRAGMA foreign_keys = OFF;")
            conn.execute("""
                CREATE TABLE habit_goals_new (
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
            conn.execute("""
                INSERT INTO habit_goals_new (id, habit_id, target_type, target_value, created_at, updated_at, active)
                SELECT id, habit_id, target_type, target_value, created_at, updated_at, active FROM habit_goals;
            """)
            conn.execute("DROP TABLE habit_goals;")
            conn.execute("ALTER TABLE habit_goals_new RENAME TO habit_goals;")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_goals_habit ON habit_goals (habit_id);")
            conn.execute("PRAGMA foreign_keys = ON;")
        else:
            conn.execute("""
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
            # Ensure end_date column exists if table was created previously without it
            cols = [r[1] for r in conn.execute("PRAGMA table_info(habit_goals)").fetchall()]
            if 'end_date' not in cols:
                conn.execute("ALTER TABLE habit_goals ADD COLUMN end_date TEXT DEFAULT NULL;")

        # Table 4: goal_milestones (Phase 7 & 8: Achieved Milestones & Duplicate Prevention)
        conn.execute("""
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

        # Table 5: habit_reminders (Smart Reminders & Notifications)
        conn.execute("""
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

        # Safe migration for existing habits: ensure columns exist without data loss
        habit_cols = [r[1] for r in conn.execute("PRAGMA table_info(habits)").fetchall()]
        if 'reminder_time' not in habit_cols:
            conn.execute("ALTER TABLE habits ADD COLUMN reminder_time TEXT DEFAULT '08:00';")
        if 'reminder_enabled' not in habit_cols:
            conn.execute("ALTER TABLE habits ADD COLUMN reminder_enabled INTEGER DEFAULT 1;")

        # Migrate existing habits: ensure each active habit has a habit_reminders row
        existing_habits = conn.execute("SELECT id, target_time, reminder_time, reminder_enabled FROM habits").fetchall()
        for h_row in existing_habits:
            hid = h_row[0]
            t_time = str(h_row[1] or "08:00")
            # Extract 24-hr time if available
            m24 = re.match(r"^([01]\d|2[0-3]):[0-5]\d", t_time)
            r_time = h_row[2] or (m24.group(0) if m24 else "08:00")
            r_en = 1 if (h_row[3] is None or h_row[3] == 1) else 0

            rem_check = conn.execute("SELECT id, reminder_time, enabled FROM habit_reminders WHERE habit_id = ?", (hid,)).fetchone()
            if not rem_check:
                conn.execute("""
                    INSERT INTO habit_reminders (habit_id, reminder_time, enabled)
                    VALUES (?, ?, ?)
                """, (hid, r_time, r_en))
            else:
                conn.execute("""
                    UPDATE habits SET reminder_time = ?, reminder_enabled = ? WHERE id = ?
                """, (rem_check[1], rem_check[2], hid))

        conn.execute("CREATE INDEX IF NOT EXISTS idx_goals_habit ON habit_goals (habit_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_milestones_lookup ON goal_milestones (habit_id, milestone_period);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_reminders_habit ON habit_reminders (habit_id);")
    conn.close()


# ---------------------------------------------------------------------------
# STREAK & RECORD HELPER FUNCTIONS
# ---------------------------------------------------------------------------

def calculate_streak(habit_id, target_date_str=None):
    """
    Calculates the current streak of completed days for a habit up to target_date.

    Streak Rules:
    1. Count consecutive 'completed' days ending today (or ending yesterday if today has no record yet).
    2. 'skipped' preserves the streak (does not break it, but does not increment count).
    3. 'missed' breaks the streak immediately (resets streak to 0).
    4. An unrecorded day prior to yesterday breaks the streak.
    5. An unrecorded day today is considered 'pending' — it does not break yesterday's active streak.
    """
    if target_date_str is None:
        target_date = date.today()
    else:
        try:
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
        except ValueError:
            target_date = date.today()

    db = get_db()
    cursor = db.execute(
        "SELECT record_date, status FROM habit_records WHERE habit_id = ? AND record_date <= ? ORDER BY record_date DESC",
        (habit_id, target_date.isoformat())
    )
    records = {row["record_date"]: row["status"] for row in cursor.fetchall()}

    streak = 0
    curr_date = target_date
    today_iso = target_date.isoformat()

    # If today has no record, today is pending; start evaluating from yesterday
    if today_iso not in records:
        curr_date = target_date - timedelta(days=1)

    while True:
        d_str = curr_date.isoformat()
        if d_str not in records:
            # Reached a day with no record: streak ends here
            break

        status = records[d_str]
        if status == "completed":
            streak += 1
            curr_date -= timedelta(days=1)
        elif status == "skipped":
            # Skipped day maintains current streak without incrementing
            curr_date -= timedelta(days=1)
        else:
            # Missed status breaks the streak
            break

    return streak


def get_habit_status_for_date(habit_id, target_date_str=None):
    """Returns 'completed', 'missed', 'skipped', or 'pending' for a habit on a given date."""
    if target_date_str is None:
        target_date_str = date.today().isoformat()
    db = get_db()
    row = db.execute(
        "SELECT status FROM habit_records WHERE habit_id = ? AND record_date = ?",
        (habit_id, target_date_str)
    ).fetchone()
    return row["status"] if row else "pending"


def get_habit_weekly_history(habit_id, target_date_str=None):
    """
    Returns a 7-element list of statuses for the 7 days ending at target_date.
    Each item is 'completed', 'missed', 'skipped', or 'pending'.
    """
    if target_date_str is None:
        target_date = date.today()
    else:
        try:
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
        except ValueError:
            target_date = date.today()

    start_date = target_date - timedelta(days=6)
    db = get_db()
    cursor = db.execute(
        "SELECT record_date, status FROM habit_records WHERE habit_id = ? AND record_date BETWEEN ? AND ? ORDER BY record_date ASC",
        (habit_id, start_date.isoformat(), target_date.isoformat())
    )
    records = {row["record_date"]: row["status"] for row in cursor.fetchall()}

    history = []
    for i in range(7):
        day_str = (start_date + timedelta(days=i)).isoformat()
        history.append(records.get(day_str, "pending"))
    return history


def habit_to_dict(row, include_stats=True, target_date=None):
    """
    Serializes a SQLite habits row into a clean JSON-friendly dictionary.
    Includes both snake_case and camelCase aliases for seamless frontend compatibility.
    """
    if row is None:
        return None

    keys = row.keys()
    time_of_day = row["time_of_day"] if "time_of_day" in keys and row["time_of_day"] else "Morning"
    target_time = row["target_time"] if "target_time" in keys and row["target_time"] else "08:00 AM"
    target_frequency = row["target_frequency"] if "target_frequency" in keys and row["target_frequency"] else "daily"
    raw_rem_time = row["reminder_time"] if "reminder_time" in keys and row["reminder_time"] else "08:00"
    raw_rem_enabled = bool(row["reminder_enabled"]) if "reminder_enabled" in keys and row["reminder_enabled"] is not None else True

    habit_dict = {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"] or "",
        "category": row["category"] or "General",
        "time_of_day": time_of_day,
        "timeOfDay": time_of_day,
        "target_time": target_time,
        "targetTime": target_time,
        "target_frequency": target_frequency,
        "frequency": target_frequency,
        "reminder_time": raw_rem_time,
        "reminder_enabled": raw_rem_enabled,
        "reminderEnabled": raw_rem_enabled,
        "created_at": str(row["created_at"]),
        "active": row["active"]
    }

    if include_stats:
        cur_streak = calculate_streak(row["id"], target_date)
        habit_dict["streak"] = cur_streak
        try:
            parsed_d = parse_target_date(target_date) if 'parse_target_date' in globals() else None
            best_streak = calculate_best_streak(row["id"], parsed_d, get_db())
        except Exception:
            best_streak = cur_streak
        habit_dict["best_streak"] = best_streak
        habit_dict["bestStreak"] = best_streak
        habit_dict["status"] = get_habit_status_for_date(row["id"], target_date)
        weekly = get_habit_weekly_history(row["id"], target_date)
        habit_dict["weekly_history"] = weekly
        habit_dict["weeklyHistory"] = weekly

    try:
        rem_row = get_db().execute(
            "SELECT reminder_time, enabled FROM habit_reminders WHERE habit_id = ?",
            (row["id"],)
        ).fetchone()
        if rem_row:
            rem_active = bool(rem_row["enabled"])
            rem_t = rem_row["reminder_time"]
            habit_dict["reminder"] = {
                "reminder_time": rem_t,
                "time": rem_t,
                "enabled": rem_active
            }
            habit_dict["reminder_time"] = rem_t
            habit_dict["reminder_enabled"] = rem_active
            habit_dict["reminderEnabled"] = rem_active
        else:
            habit_dict["reminder"] = {
                "reminder_time": raw_rem_time,
                "time": raw_rem_time,
                "enabled": raw_rem_enabled
            }
    except Exception:
        habit_dict["reminder"] = {
            "reminder_time": raw_rem_time,
            "time": raw_rem_time,
            "enabled": raw_rem_enabled
        }

    return habit_dict


# ---------------------------------------------------------------------------
# CORE APPLICATION ROUTES
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    """Renders the main StreakLab dashboard."""
    return render_template('index.html')


@app.route('/api/health', methods=['GET'])
def health_check():
    """Diagnostic health check verifying Flask and SQLite database connectivity."""
    db_ok = True
    try:
        db = get_db()
        db.execute("SELECT 1").fetchone()
    except Exception:
        db_ok = False

    return jsonify({
        "status": "ok" if db_ok else "error",
        "app": "StreakLab",
        "database": "connected" if db_ok else "disconnected"
    }), 200 if db_ok else 500


# ---------------------------------------------------------------------------
# HABITS REST API ENDPOINTS
# ---------------------------------------------------------------------------

@app.route('/api/habits', methods=['GET'])
def get_habits():
    """
    Retrieves all active habits.
    Pass ?all=true to include deactivated habits.
    Pass ?date=YYYY-MM-DD to evaluate streaks & statuses relative to that date.
    """
    target_date = request.args.get('date', date.today().isoformat())
    include_all = request.args.get('all', 'false').lower() in ('true', '1')

    db = get_db()
    if include_all:
        cursor = db.execute("SELECT * FROM habits ORDER BY id ASC")
    else:
        cursor = db.execute("SELECT * FROM habits WHERE active = 1 ORDER BY id ASC")

    habits_list = [
        habit_to_dict(row, include_stats=True, target_date=target_date)
        for row in cursor.fetchall()
    ]
    return jsonify(habits_list), 200


@app.route('/api/habits', methods=['POST'])
def create_habit():
    """
    Creates a new habit in the SQLite database and automatically configures its reminder.
    Expects JSON: { name, description?, category?, target_frequency?, time_of_day?, target_time?, reminder_time?, reminder_enabled? }
    """
    if not request.is_json:
        return jsonify({"error": "Request body must be JSON"}), 400

    data = request.get_json() or {}
    name = data.get('name')
    if not name or not isinstance(name, str) or not name.strip():
        return jsonify({"error": "Habit name is required"}), 400

    name = name.strip()
    description = (data.get('description') or "").strip()
    category = (data.get('category') or "General").strip()
    target_frequency = (data.get('target_frequency') or data.get('frequency') or "daily").strip()
    time_of_day = (data.get('time_of_day') or data.get('timeOfDay') or "Morning").strip()

    # Time handling: support 24-hr (e.g. "08:30") or 12-hr (e.g. "08:30 AM")
    raw_target_time = data.get('target_time') or data.get('targetTime') or data.get('time') or "08:00"
    raw_target_time = str(raw_target_time).strip()

    # Validation: reject malformed or out-of-range times
    time_to_check = str(data.get('reminder_time') or data.get('reminderTime') or raw_target_time).strip()
    m_check = re.match(r"^(\d{1,2}):(\d{2})(?:\s*(?:AM|PM))?$", time_to_check, re.IGNORECASE)
    if m_check:
        h, m = int(m_check.group(1)), int(m_check.group(2))
        is_ampm = "AM" in time_to_check.upper() or "PM" in time_to_check.upper()
        if is_ampm:
            if h < 1 or h > 12 or m < 0 or m > 59:
                return jsonify({"error": "Invalid time format. Hour must be 1-12 and minute 0-59"}), 400
        else:
            if h < 0 or h > 23 or m < 0 or m > 59:
                return jsonify({"error": "Invalid time format. Hour must be 0-23 and minute 0-59"}), 400
    elif time_to_check not in ("", "08:00 AM", "08:00"):
        return jsonify({"error": "Invalid time format. Expected HH:MM or HH:MM AM/PM"}), 400

    # Determine 24-hr reminder_time
    rem_input = data.get('reminder_time') or data.get('reminderTime')
    if rem_input:
        rem_str = str(rem_input).strip()
        m24 = re.match(r"^([01]\d|2[0-3]):[0-5]\d$", rem_str)
        if m24:
            rem_time_24 = rem_str
        else:
            try:
                dt = datetime.strptime(rem_str.upper(), "%I:%M %p")
                rem_time_24 = dt.strftime("%H:%M")
            except ValueError:
                rem_time_24 = "08:00"
    else:
        m24 = re.match(r"^([01]\d|2[0-3]):[0-5]\d$", raw_target_time)
        if m24:
            rem_time_24 = raw_target_time
        else:
            try:
                dt = datetime.strptime(raw_target_time.upper(), "%I:%M %p")
                rem_time_24 = dt.strftime("%H:%M")
            except ValueError:
                rem_time_24 = "08:00"

    # Default reminder toggle is ON (True)
    raw_en = data.get('reminder_enabled', data.get('reminderEnabled', True))
    rem_enabled_val = 1 if raw_en in (True, 1, '1', 'true', 'True') else 0

    target_time = raw_target_time

    db = get_db()
    cursor = db.execute("""
        INSERT INTO habits (name, description, category, time_of_day, target_time, target_frequency, reminder_time, reminder_enabled, active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
    """, (name, description, category, time_of_day, target_time, target_frequency, rem_time_24, rem_enabled_val))
    new_id = cursor.lastrowid

    # Automatically persist habit reminder in habit_reminders table
    db.execute("""
        INSERT INTO habit_reminders (habit_id, reminder_time, enabled)
        VALUES (?, ?, ?)
    """, (new_id, rem_time_24, rem_enabled_val))

    db.commit()
    ai_explainer.invalidate_explanation_cache()

    row = db.execute("SELECT * FROM habits WHERE id = ?", (new_id,)).fetchone()
    return jsonify(habit_to_dict(row)), 201


@app.route('/api/habits/<int:habit_id>', methods=['GET'])
def get_habit(habit_id):
    """Retrieves a single habit by ID."""
    target_date = request.args.get('date', date.today().isoformat())
    db = get_db()
    row = db.execute("SELECT * FROM habits WHERE id = ?", (habit_id,)).fetchone()
    if not row:
        return jsonify({"error": "Habit not found"}), 404

    return jsonify(habit_to_dict(row, include_stats=True, target_date=target_date)), 200


@app.route('/api/habits/<int:habit_id>', methods=['PUT'])
def update_habit(habit_id):
    """
    Updates an existing habit and synchronizes reminder settings.
    Supports updates for name, description, category, target_frequency,
    time_of_day, target_time, reminder_time, reminder_enabled, and active status.
    """
    if not request.is_json:
        return jsonify({"error": "Request body must be JSON"}), 400

    db = get_db()
    existing = db.execute("SELECT * FROM habits WHERE id = ?", (habit_id,)).fetchone()
    if not existing:
        return jsonify({"error": "Habit not found"}), 404

    data = request.get_json() or {}

    # Validate name if present
    if 'name' in data:
        name = data.get('name')
        if not name or not isinstance(name, str) or not name.strip():
            return jsonify({"error": "Habit name cannot be empty"}), 400
        name = name.strip()
    else:
        name = existing['name']

    description = data.get('description', existing['description'])
    category = data.get('category', existing['category'])
    target_frequency = data.get('target_frequency', data.get('frequency', existing['target_frequency']))
    time_of_day = data.get('time_of_day', data.get('timeOfDay', existing['time_of_day']))
    target_time = data.get('target_time', data.get('targetTime', existing['target_time']))
    active = data.get('active', existing['active'])

    # Reminder fields
    existing_keys = existing.keys()
    curr_rem_time = existing['reminder_time'] if 'reminder_time' in existing_keys and existing['reminder_time'] else "08:00"
    curr_rem_en = existing['reminder_enabled'] if 'reminder_enabled' in existing_keys and existing['reminder_enabled'] is not None else 1

    reminder_time = data.get('reminder_time', data.get('reminderTime', curr_rem_time))
    if reminder_time:
        reminder_time = str(reminder_time).strip()
        m_check = re.match(r"^(\d{1,2}):(\d{2})(?:\s*(?:AM|PM))?$", reminder_time, re.IGNORECASE)
        if m_check:
            h, m = int(m_check.group(1)), int(m_check.group(2))
            is_ampm = "AM" in reminder_time.upper() or "PM" in reminder_time.upper()
            if is_ampm:
                if h < 1 or h > 12 or m < 0 or m > 59:
                    return jsonify({"error": "Invalid reminder_time format. Hour must be 1-12 and minute 0-59"}), 400
                dt = datetime.strptime(reminder_time.upper(), "%I:%M %p")
                reminder_time = dt.strftime("%H:%M")
            else:
                if h < 0 or h > 23 or m < 0 or m > 59:
                    return jsonify({"error": "Invalid reminder_time format. Hour must be 0-23 and minute 0-59"}), 400
                reminder_time = f"{h:02d}:{m:02d}"
        else:
            return jsonify({"error": "Invalid reminder_time format. Expected HH:MM"}), 400

    if 'reminder_enabled' in data or 'reminderEnabled' in data:
        raw_en = data.get('reminder_enabled', data.get('reminderEnabled'))
        rem_enabled_val = 1 if raw_en in (True, 1, '1', 'true', 'True') else 0
    else:
        rem_enabled_val = curr_rem_en

    db.execute("""
        UPDATE habits
        SET name = ?, description = ?, category = ?, time_of_day = ?, target_time = ?,
            target_frequency = ?, reminder_time = ?, reminder_enabled = ?, active = ?
        WHERE id = ?
    """, (name, description, category, time_of_day, target_time, target_frequency, reminder_time, rem_enabled_val, active, habit_id))

    # Synchronize habit_reminders table
    existing_rem = db.execute("SELECT id FROM habit_reminders WHERE habit_id = ?", (habit_id,)).fetchone()
    if existing_rem:
        db.execute("""
            UPDATE habit_reminders
            SET reminder_time = ?, enabled = ?, updated_at = CURRENT_TIMESTAMP
            WHERE habit_id = ?
        """, (reminder_time, rem_enabled_val, habit_id))
    else:
        db.execute("""
            INSERT INTO habit_reminders (habit_id, reminder_time, enabled)
            VALUES (?, ?, ?)
        """, (habit_id, reminder_time, rem_enabled_val))

    db.commit()
    ai_explainer.invalidate_explanation_cache()

    updated = db.execute("SELECT * FROM habits WHERE id = ?", (habit_id,)).fetchone()
    return jsonify(habit_to_dict(updated)), 200


@app.route('/api/habits/<int:habit_id>', methods=['DELETE'])
def deactivate_habit(habit_id):
    """
    Deactivates a habit instead of permanently deleting its history.
    Sets active = 0 to preserve past streak statistics and disables reminders.
    """
    db = get_db()
    existing = db.execute("SELECT * FROM habits WHERE id = ?", (habit_id,)).fetchone()
    if not existing:
        return jsonify({"error": "Habit not found"}), 404

    db.execute("UPDATE habits SET active = 0 WHERE id = ?", (habit_id,))
    db.execute("UPDATE habit_reminders SET enabled = 0 WHERE habit_id = ?", (habit_id,))
    db.commit()
    ai_explainer.invalidate_explanation_cache()

    return jsonify({
        "message": "Habit deactivated successfully",
        "id": habit_id,
        "active": 0
    }), 200


# ---------------------------------------------------------------------------
# DAILY RECORDS REST API ENDPOINTS
# ---------------------------------------------------------------------------

@app.route('/api/records', methods=['GET'])
def get_daily_records():
    """
    Returns daily records for the given date.
    Query parameter: ?date=YYYY-MM-DD (defaults to today).
    """
    record_date = request.args.get('date', date.today().isoformat())
    try:
        datetime.strptime(record_date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Invalid date format. Expected YYYY-MM-DD"}), 400

    db = get_db()
    cursor = db.execute("""
        SELECT r.id, r.habit_id, r.record_date, r.status, r.created_at, r.updated_at,
               h.name as habit_name
        FROM habit_records r
        JOIN habits h ON r.habit_id = h.id
        WHERE r.record_date = ?
        ORDER BY r.id ASC
    """, (record_date,))

    records = []
    for row in cursor.fetchall():
        records.append({
            "id": row["id"],
            "habit_id": row["habit_id"],
            "habit_name": row["habit_name"],
            "record_date": row["record_date"],
            "status": row["status"],
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"])
        })
    return jsonify(records), 200


@app.route('/api/records', methods=['POST'])
def save_daily_record():
    """
    Creates or updates a habit's daily status using SQLite UPSERT logic.
    Allowed status values: 'completed', 'missed', 'skipped', or 'pending'.
    If status is 'pending', removes any existing record for that habit on that date.
    """
    if not request.is_json:
        return jsonify({"error": "Request body must be JSON"}), 400

    data = request.get_json() or {}
    habit_id = data.get('habit_id')
    record_date = data.get('record_date')
    status = data.get('status')

    if habit_id is None:
        return jsonify({"error": "habit_id is required"}), 400
    try:
        habit_id = int(habit_id)
    except (ValueError, TypeError):
        return jsonify({"error": "habit_id must be an integer"}), 400

    if not record_date:
        return jsonify({"error": "record_date is required"}), 400
    try:
        datetime.strptime(record_date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Invalid record_date format. Expected YYYY-MM-DD"}), 400

    allowed_statuses = {'completed', 'missed', 'skipped', 'pending'}
    if not status or status not in allowed_statuses:
        return jsonify({"error": "status must be 'completed', 'missed', 'skipped', or 'pending'"}), 400

    db = get_db()
    # Check that habit exists
    habit = db.execute("SELECT id FROM habits WHERE id = ?", (habit_id,)).fetchone()
    if not habit:
        return jsonify({"error": "Habit not found"}), 404

    # Check whether a record already exists for this habit and date
    existing = db.execute(
        "SELECT id FROM habit_records WHERE habit_id = ? AND record_date = ?",
        (habit_id, record_date)
    ).fetchone()

    if status == 'pending':
        # Resetting back to pending: delete existing record
        db.execute(
            "DELETE FROM habit_records WHERE habit_id = ? AND record_date = ?",
            (habit_id, record_date)
        )
        db.commit()
        ai_explainer.invalidate_explanation_cache()
        streak = calculate_streak(habit_id, record_date)
        return jsonify({
            "message": "Record reset to pending",
            "habit_id": habit_id,
            "record_date": record_date,
            "status": "pending",
            "streak": streak
        }), 200

    # SQLite UPSERT: insert new record or update existing status on (habit_id, record_date) conflict
    db.execute("""
        INSERT INTO habit_records (habit_id, record_date, status, created_at, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT(habit_id, record_date) DO UPDATE SET
            status = excluded.status,
            updated_at = CURRENT_TIMESTAMP
    """, (habit_id, record_date, status))
    db.commit()
    ai_explainer.invalidate_explanation_cache()

    row = db.execute(
        "SELECT id, habit_id, record_date, status, created_at, updated_at FROM habit_records WHERE habit_id = ? AND record_date = ?",
        (habit_id, record_date)
    ).fetchone()

    streak = calculate_streak(habit_id, record_date)
    response_code = 200 if existing else 201

    return jsonify({
        "id": row["id"],
        "habit_id": row["habit_id"],
        "record_date": row["record_date"],
        "status": row["status"],
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
        "streak": streak
    }), response_code


@app.route('/api/habits/<int:habit_id>/records', methods=['GET'])
def get_habit_records_history(habit_id):
    """Returns the full chronological history of daily records for a specific habit."""
    db = get_db()
    habit = db.execute("SELECT id FROM habits WHERE id = ?", (habit_id,)).fetchone()
    if not habit:
        return jsonify({"error": "Habit not found"}), 404

    cursor = db.execute("""
        SELECT id, habit_id, record_date, status, created_at, updated_at
        FROM habit_records
        WHERE habit_id = ?
        ORDER BY record_date ASC
    """, (habit_id,))

    records = []
    for row in cursor.fetchall():
        records.append({
            "id": row["id"],
            "habit_id": row["habit_id"],
            "record_date": row["record_date"],
            "status": row["status"],
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"])
        })
    return jsonify(records), 200


# ---------------------------------------------------------------------------
# PHASE 3: HABIT PATTERN DETECTION & ANALYTICS REST API ENDPOINTS
# ---------------------------------------------------------------------------

def parse_days_param(request_obj, default=30, min_days=1, max_days=365):
    """Validates and parses the 'days' query parameter for statistical windows."""
    raw_days = request_obj.args.get('days')
    if raw_days is None:
        return default, None
    try:
        days = int(raw_days)
        if days < min_days or days > max_days:
            return None, f"days parameter must be an integer between {min_days} and {max_days}"
        return days, None
    except (ValueError, TypeError):
        return None, f"days parameter must be a valid integer between {min_days} and {max_days}"


def parse_date_param(request_obj):
    """Validates and parses the 'date' query parameter."""
    raw_date = request_obj.args.get('date')
    if raw_date is None:
        return date.today().isoformat(), None
    try:
        datetime.strptime(raw_date, "%Y-%m-%d")
        return raw_date, None
    except ValueError:
        return None, "Invalid date format. Expected YYYY-MM-DD"


@app.route('/api/insights', methods=['GET'])
def get_insights():
    """
    Returns an overall summary and a list of rule-based insights detected
    from actual SQLite habit records.
    Query parameters:
      - days: integer window (default 30, min 1, max 365)
      - date: YYYY-MM-DD reference date (defaults to today)
    """
    days, err = parse_days_param(request)
    if err:
        return jsonify({"error": err}), 400
    target_date, err = parse_date_param(request)
    if err:
        return jsonify({"error": err}), 400

    db = get_db()
    insights_data = analyze_habit_patterns(days=days, target_date_str=target_date, db=db)
    
    # Optional explain flag for backward-compatible enriched insights
    if request.args.get('explain', '').lower() in ('true', '1'):
        insights_list = insights_data.get("insights", [])
        insights_data["explanations"] = ai_explainer.explain_patterns(
            insights_list,
            period_days=days,
            target_date=target_date
        )

    return jsonify(insights_data), 200


@app.route('/api/insights/explanations', methods=['GET'])
def get_insight_explanations():
    """
    Phase 4: Hybrid AI Explanations and Recommendations.
    Takes deterministic patterns from pattern_engine and enriches them
    with evidence-grounded AI explanations or offline deterministic fallbacks.

    Query parameters:
      - days: integer window (default 30, min 1, max 365)
      - date: YYYY-MM-DD reference date (defaults to today)
      - habit_id: optional integer to explain a single habit's patterns
      - refresh: optional boolean (true/1) to force bypass of cache
    """
    days, err = parse_days_param(request)
    if err:
        return jsonify({"error": err}), 400
    target_date, err = parse_date_param(request)
    if err:
        return jsonify({"error": err}), 400

    habit_id_raw = request.args.get('habit_id')
    habit_id = None
    if habit_id_raw is not None:
        try:
            habit_id = int(habit_id_raw)
        except (ValueError, TypeError):
            return jsonify({"error": "habit_id must be a valid integer"}), 400

    refresh = request.args.get('refresh', '').lower() in ('true', '1')

    db = get_db()
    ai_cfg = ai_explainer.get_ai_config()

    if habit_id is not None:
        single_data = analyze_single_habit(habit_id=habit_id, days=days, target_date_str=target_date, db=db)
        if single_data is None:
            return jsonify({"error": "Habit not found or inactive"}), 404

        habit_insights = single_data.get("insights", [])
        explanations = ai_explainer.explain_patterns(
            habit_insights,
            period_days=days,
            target_date=target_date,
            force_refresh=refresh
        )
        overall_source = "ai" if any(e.get("source") == "ai" for e in explanations) else "fallback"

        return jsonify({
            "habit": single_data.get("habit"),
            "period": single_data.get("period"),
            "statistics": single_data.get("statistics"),
            "weekday_breakdown": single_data.get("weekday_breakdown"),
            "explanations": explanations,
            "source": overall_source,
            "ai_configured": ai_cfg["is_configured"],
            "provider": ai_cfg["provider"] if ai_cfg["is_configured"] else "local_fallback"
        }), 200

    # Overall system insights with explanations
    insights_data = analyze_habit_patterns(days=days, target_date_str=target_date, db=db)
    insights_list = insights_data.get("insights", [])

    explanations = ai_explainer.explain_patterns(
        insights_list,
        period_days=days,
        target_date=target_date,
        force_refresh=refresh
    )
    overall_source = "ai" if any(e.get("source") == "ai" for e in explanations) else "fallback"

    return jsonify({
        "period": insights_data.get("period"),
        "summary": insights_data.get("summary"),
        "explanations": explanations,
        "source": overall_source,
        "ai_configured": ai_cfg["is_configured"],
        "provider": ai_cfg["provider"] if ai_cfg["is_configured"] else "local_fallback"
    }), 200


@app.route('/api/insights/<int:habit_id>', methods=['GET'])
def get_single_habit_insights(habit_id):
    """
    Returns detailed statistics, weekday breakdown, and targeted patterns
    for a particular active habit.
    Returns 404 if the habit is nonexistent or inactive.
    """
    days, err = parse_days_param(request)
    if err:
        return jsonify({"error": err}), 400
    target_date, err = parse_date_param(request)
    if err:
        return jsonify({"error": err}), 400

    db = get_db()
    result = analyze_single_habit(habit_id=habit_id, days=days, target_date_str=target_date, db=db)
    if result is None:
        return jsonify({"error": "Habit not found or inactive"}), 404
    return jsonify(result), 200


@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    """
    Returns structured data for dashboard visualizations:
      - daily completion rates and counts over the analysis window
      - weekday statistics (Mon - Sun)
      - habit-wise breakdown with completion rates and streaks
      - time-of-day distribution comparison
    """
    days, err = parse_days_param(request)
    if err:
        return jsonify({"error": err}), 400
    target_date, err = parse_date_param(request)
    if err:
        return jsonify({"error": err}), 400

    db = get_db()
    analytics_data = get_habit_analytics(days=days, target_date_str=target_date, db=db)
    return jsonify(analytics_data), 200


# ---------------------------------------------------------------------------
# PHASE 7: HABIT CALENDAR HEATMAP, WEEKLY REVIEW, AND GOALS REST API ENDPOINTS
# ---------------------------------------------------------------------------

@app.route('/api/calendar', methods=['GET'])
def get_calendar_heatmap_api():
    """
    Phase 7: Calendar Heatmap API.
    Returns month calendar grid with day-by-day habit records and dominant status.
    Query parameters:
      - month: YYYY-MM (e.g. 2026-10, defaults to current month)
      - habit_id: optional integer to filter by habit
      - date: reference date YYYY-MM-DD (defaults to today)
    """
    month = request.args.get('month')
    habit_id_raw = request.args.get('habit_id')
    habit_id = None
    if habit_id_raw is not None and habit_id_raw != '':
        try:
            habit_id = int(habit_id_raw)
        except (ValueError, TypeError):
            return jsonify({"error": "habit_id must be a valid integer"}), 400

    target_date, err = parse_date_param(request)
    if err:
        return jsonify({"error": err}), 400

    # Validate month format if provided
    if month:
        parts = month.strip().split("-")
        if len(parts) != 2:
            return jsonify({"error": "Invalid month format. Expected YYYY-MM"}), 400
        try:
            y, m = int(parts[0]), int(parts[1])
            if y < 1900 or y > 2100 or m < 1 or m > 12:
                return jsonify({"error": "Month or year out of range"}), 400
        except ValueError:
            return jsonify({"error": "Invalid month format. Expected YYYY-MM"}), 400

    db = get_db()
    if habit_id is not None:
        habit = db.execute("SELECT id FROM habits WHERE id = ?", (habit_id,)).fetchone()
        if not habit:
            return jsonify({"error": "Habit not found"}), 404

    result = get_calendar_heatmap(month_str=month, habit_id=habit_id, target_date_str=target_date, db=db)
    return jsonify(result), 200


@app.route('/api/reviews/weekly', methods=['GET'])
def get_weekly_review_api():
    """
    Phase 7: Weekly Progress Review API.
    Returns 7-day completion review, comparisons, strongest days, habits needing attention,
    and hybrid AI explanation.
    Query parameters:
      - date: reference date YYYY-MM-DD (defaults to today)
      - explain: boolean (default true)
    """
    target_date, err = parse_date_param(request)
    if err:
        return jsonify({"error": err}), 400

    explain = request.args.get('explain', 'true').lower() in ('true', '1')

    db = get_db()
    review_data = generate_weekly_review(target_date_str=target_date, db=db)

    explanation = None
    if explain:
        explanation = ai_explainer.explain_weekly_review(review_data)

    review_data["explanation"] = explanation
    return jsonify(review_data), 200


@app.route('/api/goals', methods=['GET'])
def get_goals_api():
    """
    Phase 7: Goals & Milestones API.
    Returns weekly targets, current progress, achievement flags, and milestone details.
    Query parameters:
      - date: reference date YYYY-MM-DD (defaults to today)
      - habit_id: optional integer to filter by single habit
    """
    target_date, err = parse_date_param(request)
    if err:
        return jsonify({"error": err}), 400

    habit_id_raw = request.args.get('habit_id')
    habit_id = None
    if habit_id_raw is not None and habit_id_raw != '':
        try:
            habit_id = int(habit_id_raw)
        except (ValueError, TypeError):
            return jsonify({"error": "habit_id must be a valid integer"}), 400

    db = get_db()
    if habit_id is not None:
        habit = db.execute("SELECT id FROM habits WHERE id = ?", (habit_id,)).fetchone()
        if not habit:
            return jsonify({"error": "Habit not found"}), 404

    result = calculate_goals_and_milestones(target_date_str=target_date, habit_id=habit_id, db=db)
    return jsonify(result), 200


@app.route('/api/goals', methods=['POST'])
def save_goal_api():
    """
    Phase 7 & 8: Set or update a habit's target goal.
    Supports weekly completions (1-7), target streak (>=1), and total completions (>=1).
    Expects JSON: { "habit_id": int, "target_value": int, "target_type": str (optional), "end_date": str (optional) }
    """
    if not request.is_json:
        return jsonify({"error": "Request body must be JSON"}), 400

    data = request.get_json() or {}
    habit_id = data.get('habit_id')
    target_value = data.get('target_value')
    target_type = data.get('target_type', 'weekly_completions')
    end_date = data.get('end_date')

    if habit_id is None:
        return jsonify({"error": "habit_id is required"}), 400
    try:
        habit_id = int(habit_id)
    except (ValueError, TypeError):
        return jsonify({"error": "habit_id must be an integer"}), 400

    if target_type not in ('weekly_completions', 'target_streak', 'total_completions'):
        return jsonify({"error": "target_type must be weekly_completions, target_streak, or total_completions"}), 400

    if target_value is None:
        return jsonify({"error": "target_value is required"}), 400
    try:
        target_value = int(target_value)
        if target_type == 'weekly_completions' and (target_value < 1 or target_value > 7):
            return jsonify({"error": "target_value must be an integer between 1 and 7"}), 400
        elif target_value < 1:
            return jsonify({"error": "target_value must be an integer greater than or equal to 1"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "target_value must be a valid integer"}), 400

    if end_date is not None and end_date != "":
        try:
            datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "end_date must be in YYYY-MM-DD format"}), 400
    else:
        end_date = None

    db = get_db()
    habit = db.execute("SELECT id, name FROM habits WHERE id = ?", (habit_id,)).fetchone()
    if not habit:
        return jsonify({"error": "Habit not found"}), 404

    # Check if goal already exists for this habit and target_type
    existing = db.execute(
        "SELECT id FROM habit_goals WHERE habit_id = ? AND target_type = ?",
        (habit_id, target_type)
    ).fetchone()

    cols = [r[1] for r in db.execute("PRAGMA table_info(habit_goals)").fetchall()]
    has_end_date = 'end_date' in cols

    if existing:
        if has_end_date:
            db.execute("""
                UPDATE habit_goals
                SET target_value = ?, active = 1, end_date = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (target_value, end_date, existing["id"]))
        else:
            db.execute("""
                UPDATE habit_goals
                SET target_value = ?, active = 1, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (target_value, existing["id"]))
        db.commit()
        goal_id = existing["id"]
        status_code = 200
    else:
        if has_end_date:
            cursor = db.execute("""
                INSERT INTO habit_goals (habit_id, target_type, target_value, active, end_date)
                VALUES (?, ?, ?, 1, ?)
            """, (habit_id, target_type, target_value, end_date))
        else:
            cursor = db.execute("""
                INSERT INTO habit_goals (habit_id, target_type, target_value, active)
                VALUES (?, ?, ?, 1)
            """, (habit_id, target_type, target_value))
        db.commit()
        goal_id = cursor.lastrowid
        status_code = 201

    # Return calculated progress for this goal
    progress_data = calculate_goals_and_milestones(habit_id=habit_id, db=db)
    matched_goals = [g for g in progress_data.get("goals", []) if g["id"] == goal_id]
    goal_payload = matched_goals[0] if matched_goals else {"id": goal_id, "habit_id": habit_id, "target_value": target_value}

    return jsonify(goal_payload), status_code


@app.route('/api/goals/<int:goal_id>', methods=['PUT'])
def update_goal_api(goal_id):
    """
    Phase 8: Update an existing habit goal.
    Supports editing target_value, target_type, end_date, and active status.
    """
    if not request.is_json:
        return jsonify({"error": "Request body must be JSON"}), 400

    db = get_db()
    existing = db.execute("SELECT * FROM habit_goals WHERE id = ?", (goal_id,)).fetchone()
    if not existing:
        return jsonify({"error": "Goal not found"}), 404

    data = request.get_json() or {}
    target_type = data.get('target_type', existing['target_type'])
    if target_type not in ('weekly_completions', 'target_streak', 'total_completions'):
        return jsonify({"error": "target_type must be weekly_completions, target_streak, or total_completions"}), 400

    target_value = data.get('target_value', existing['target_value'])
    try:
        target_value = int(target_value)
        if target_type == 'weekly_completions' and (target_value < 1 or target_value > 7):
            return jsonify({"error": "target_value must be an integer between 1 and 7"}), 400
        elif target_value < 1:
            return jsonify({"error": "target_value must be an integer greater than or equal to 1"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "target_value must be a valid integer"}), 400

    end_date = data.get('end_date')
    if end_date is not None and end_date != "":
        try:
            datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "end_date must be in YYYY-MM-DD format"}), 400
    else:
        end_date = None

    active = data.get('active', existing['active'])
    active_val = 1 if active in (1, True, '1', 'true') else 0

    cols = [r[1] for r in db.execute("PRAGMA table_info(habit_goals)").fetchall()]
    if 'end_date' in cols:
        db.execute("""
            UPDATE habit_goals
            SET target_value = ?, target_type = ?, end_date = ?, active = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (target_value, target_type, end_date, active_val, goal_id))
    else:
        db.execute("""
            UPDATE habit_goals
            SET target_value = ?, target_type = ?, active = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (target_value, target_type, active_val, goal_id))
    db.commit()

    progress_data = calculate_goals_and_milestones(habit_id=existing['habit_id'], db=db)
    matched_goals = [g for g in progress_data.get("goals", []) if g["id"] == goal_id]
    goal_payload = matched_goals[0] if matched_goals else {"id": goal_id, "target_value": target_value, "active": active_val}
    return jsonify(goal_payload), 200


@app.route('/api/goals/<int:goal_id>', methods=['DELETE'])
def delete_goal_api(goal_id):
    """
    Phase 7: Deactivates or removes a habit goal.
    """
    db = get_db()
    existing = db.execute("SELECT id FROM habit_goals WHERE id = ?", (goal_id,)).fetchone()
    if not existing:
        return jsonify({"error": "Goal not found"}), 404

    db.execute("UPDATE habit_goals SET active = 0 WHERE id = ?", (goal_id,))
    db.commit()
    return jsonify({"message": "Goal removed successfully", "id": goal_id}), 200


# ---------------------------------------------------------------------------
# PHASE 8: SMART REMINDERS & NOTIFICATIONS REST API ENDPOINTS
# ---------------------------------------------------------------------------

@app.route('/api/reminders', methods=['GET'])
def get_reminders_api():
    """
    Phase 8: Retrieve all configured habit reminders with habit metadata.
    Includes today's completion status so reminders do not trigger for completed habits.
    """
    target_date, err = parse_date_param(request)
    if err:
        return jsonify({"error": err}), 400
    ref_date_str = target_date or date.today().isoformat()

    db = get_db()
    cursor = db.execute("""
        SELECT r.id, r.habit_id, r.reminder_time, r.enabled, r.created_at, r.updated_at,
               h.name as habit_name, h.category, h.time_of_day, h.active as habit_active
        FROM habit_reminders r
        JOIN habits h ON r.habit_id = h.id
        WHERE h.active = 1
        ORDER BY r.reminder_time ASC
    """)
    reminders = []
    for row in cursor.fetchall():
        hid = row["habit_id"]
        # Check today's completion status
        rec = db.execute(
            "SELECT status FROM habit_records WHERE habit_id = ? AND record_date = ?",
            (hid, ref_date_str)
        ).fetchone()
        is_completed = (rec is not None and rec["status"] == "completed")
        today_status = rec["status"] if rec else "pending"

        reminders.append({
            "id": row["id"],
            "habit_id": hid,
            "habit_name": row["habit_name"],
            "category": row["category"] or "General",
            "time_of_day": row["time_of_day"] or "Morning",
            "reminder_time": row["reminder_time"],
            "enabled": bool(row["enabled"]),
            "is_completed_today": is_completed,
            "today_status": today_status,
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"])
        })

    return jsonify(reminders), 200


@app.route('/api/reminders', methods=['POST'])
def save_reminder_api():
    """
    Phase 8: Configure, create, or update a reminder time for a habit.
    Expects JSON: { "habit_id": int, "reminder_time": "HH:MM", "enabled": bool (optional) }
    """
    if not request.is_json:
        return jsonify({"error": "Request body must be JSON"}), 400

    data = request.get_json() or {}
    habit_id = data.get('habit_id')
    reminder_time = data.get('reminder_time')
    enabled = data.get('enabled', True)

    if habit_id is None:
        return jsonify({"error": "habit_id is required"}), 400
    try:
        habit_id = int(habit_id)
    except (ValueError, TypeError):
        return jsonify({"error": "habit_id must be an integer"}), 400

    if not reminder_time or not isinstance(reminder_time, str):
        return jsonify({"error": "reminder_time is required and must be a string (HH:MM)"}), 400

    reminder_time = reminder_time.strip()
    if not re.match(r"^([01]\d|2[0-3]):[0-5]\d$", reminder_time):
        return jsonify({"error": "reminder_time must be in 24-hour HH:MM format (e.g. 08:30 or 19:45)"}), 400

    enabled_val = 1 if enabled in (True, 1, '1', 'true', 'True') else 0

    db = get_db()
    habit = db.execute("SELECT id, name FROM habits WHERE id = ? AND active = 1", (habit_id,)).fetchone()
    if not habit:
        return jsonify({"error": "Habit not found"}), 404

    existing = db.execute("SELECT id FROM habit_reminders WHERE habit_id = ?", (habit_id,)).fetchone()
    if existing:
        db.execute("""
            UPDATE habit_reminders
            SET reminder_time = ?, enabled = ?, updated_at = CURRENT_TIMESTAMP
            WHERE habit_id = ?
        """, (reminder_time, enabled_val, habit_id))
        db.commit()
        status_code = 200
        rem_id = existing["id"]
    else:
        cursor = db.execute("""
            INSERT INTO habit_reminders (habit_id, reminder_time, enabled)
            VALUES (?, ?, ?)
        """, (habit_id, reminder_time, enabled_val))
        db.commit()
        status_code = 201
        rem_id = cursor.lastrowid

    return jsonify({
        "id": rem_id,
        "habit_id": habit_id,
        "habit_name": habit["name"],
        "reminder_time": reminder_time,
        "enabled": bool(enabled_val)
    }), status_code


@app.route('/api/reminders/<int:habit_id>', methods=['PUT'])
def update_reminder_api(habit_id):
    """
    Phase 8: Edit reminder settings (time and enabled status) for a habit.
    """
    if not request.is_json:
        return jsonify({"error": "Request body must be JSON"}), 400

    db = get_db()
    existing = db.execute("SELECT * FROM habit_reminders WHERE habit_id = ?", (habit_id,)).fetchone()
    if not existing:
        return jsonify({"error": "Reminder not found for this habit"}), 404

    data = request.get_json() or {}
    reminder_time = data.get('reminder_time', existing['reminder_time'])
    if reminder_time:
        reminder_time = str(reminder_time).strip()
        if not re.match(r"^([01]\d|2[0-3]):[0-5]\d$", reminder_time):
            return jsonify({"error": "reminder_time must be in 24-hour HH:MM format"}), 400

    enabled = data.get('enabled', existing['enabled'])
    enabled_val = 1 if enabled in (True, 1, '1', 'true', 'True') else 0

    db.execute("""
        UPDATE habit_reminders
        SET reminder_time = ?, enabled = ?, updated_at = CURRENT_TIMESTAMP
        WHERE habit_id = ?
    """, (reminder_time, enabled_val, habit_id))
    db.commit()

    habit = db.execute("SELECT name FROM habits WHERE id = ?", (habit_id,)).fetchone()
    return jsonify({
        "id": existing["id"],
        "habit_id": habit_id,
        "habit_name": habit["name"] if habit else "Habit",
        "reminder_time": reminder_time,
        "enabled": bool(enabled_val)
    }), 200


@app.route('/api/reminders/<int:habit_id>', methods=['DELETE'])
def delete_reminder_api(habit_id):
    """
    Phase 8: Delete a habit reminder.
    """
    db = get_db()
    existing = db.execute("SELECT id FROM habit_reminders WHERE habit_id = ?", (habit_id,)).fetchone()
    if not existing:
        return jsonify({"error": "Reminder not found for this habit"}), 404

    db.execute("DELETE FROM habit_reminders WHERE habit_id = ?", (habit_id,))
    db.commit()
    return jsonify({"message": "Reminder deleted successfully", "habit_id": habit_id}), 200


# ---------------------------------------------------------------------------
# PHASE 8: PROGRESS REPORTS & CSV EXPORT REST API ENDPOINTS
# ---------------------------------------------------------------------------

@app.route('/api/reports', methods=['GET'])
def get_progress_report_api():
    """
    Phase 8: Daily, Weekly, and Monthly Progress Report API.
    Query parameters:
      - type: daily | weekly | monthly (default: weekly)
      - date: YYYY-MM-DD reference date (defaults to today)
    """
    report_type = request.args.get('type', 'weekly').lower().strip()
    if report_type not in ["daily", "weekly", "monthly"]:
        return jsonify({"error": f"Invalid report type '{report_type}'. Supported: daily, weekly, monthly"}), 400

    target_date, err = parse_date_param(request)
    if err:
        return jsonify({"error": err}), 400

    db = get_db()
    report = generate_progress_report(report_type=report_type, target_date_str=target_date, db=db)
    return jsonify(report), 200


def sanitize_csv_field(val):
    """
    Phase 8: Defuses spreadsheet formula injection in untrusted CSV fields.
    If a string starts with '=', '+', '-', '@', '\t', or '\r', prepends a single quote "'".
    """
    if val is None:
        return ""
    s = str(val)
    if s and s[0] in ('=', '+', '-', '@', '\t', '\r'):
        return f"'{s}"
    return s


@app.route('/api/export', methods=['GET'])
def export_csv_api():
    """
    Phase 8: Secure CSV Data Export.
    Exports habit records, completion history, goals, milestones, or structured progress reports.
    Uses UTF-8 encoding with BOM (utf-8-sig) for Excel compatibility.
    Guarantees spreadsheet formula injection defense.
    Query parameters:
      - type: habits | records | goals | report (default: habits)
      - report_type: daily | weekly | monthly (when type == 'report', default: weekly)
      - date: YYYY-MM-DD reference date (defaults to today)
    """
    export_type = request.args.get('type', 'habits').lower().strip()
    if export_type not in ["habits", "records", "goals", "report"]:
        return jsonify({"error": f"Invalid export type '{export_type}'. Supported: habits, records, goals, report"}), 400

    target_date, err = parse_date_param(request)
    if err:
        return jsonify({"error": err}), 400
    ref_date_str = target_date or date.today().isoformat()

    db = get_db()
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    if export_type == "records":
        filename = f"streaklab_records_{ref_date_str}.csv"
        headers = ["Record ID", "Habit ID", "Habit Name", "Category", "Record Date", "Status", "Created At", "Updated At"]
        writer.writerow(headers)

        cursor = db.execute("""
            SELECT r.id, r.habit_id, r.record_date, r.status, r.created_at, r.updated_at,
                   h.name as habit_name, h.category
            FROM habit_records r
            JOIN habits h ON r.habit_id = h.id
            ORDER BY r.record_date DESC, r.habit_id ASC
        """)
        for row in cursor.fetchall():
            writer.writerow([
                sanitize_csv_field(row["id"]),
                sanitize_csv_field(row["habit_id"]),
                sanitize_csv_field(row["habit_name"]),
                sanitize_csv_field(row["category"] or "General"),
                sanitize_csv_field(row["record_date"]),
                sanitize_csv_field(row["status"]),
                sanitize_csv_field(row["created_at"]),
                sanitize_csv_field(row["updated_at"])
            ])

    elif export_type == "goals":
        filename = f"streaklab_goals_milestones_{ref_date_str}.csv"
        headers = [
            "Goal ID", "Habit ID", "Habit Name", "Category", "Target Type", "Target Value",
            "Current Progress", "Progress %", "Status", "Target Deadline", "Milestone Type", "Achieved Period"
        ]
        writer.writerow(headers)

        goals_data = calculate_goals_and_milestones(target_date_str=ref_date_str, db=db)
        for g in goals_data.get("goals", []):
            ms = g.get("milestone") or {}
            writer.writerow([
                sanitize_csv_field(g.get("id")),
                sanitize_csv_field(g.get("habit_id")),
                sanitize_csv_field(g.get("habit_name")),
                sanitize_csv_field(g.get("category")),
                sanitize_csv_field(g.get("target_type")),
                sanitize_csv_field(g.get("target_value")),
                sanitize_csv_field(g.get("current_progress")),
                sanitize_csv_field(f"{g.get('progress_percentage', 0.0)}%"),
                sanitize_csv_field(g.get("status")),
                sanitize_csv_field(g.get("end_date") or "Ongoing"),
                sanitize_csv_field(ms.get("type") or "None"),
                sanitize_csv_field(ms.get("period") or "None")
            ])

    elif export_type == "report":
        rep_type = request.args.get('report_type', 'weekly').lower().strip()
        if rep_type not in ["daily", "weekly", "monthly"]:
            return jsonify({"error": f"Invalid report_type '{rep_type}'. Supported: daily, weekly, monthly"}), 400
        report = generate_progress_report(report_type=rep_type, target_date_str=ref_date_str, db=db)
        rep_name = report.get("report_type", "weekly")
        filename = f"streaklab_report_{rep_name}_{ref_date_str}.csv"
        headers = [
            "Report Type", "Start Date", "End Date", "Generated At",
            "Habit ID", "Habit Name", "Category", "Time of Day",
            "Completed", "Missed", "Skipped", "Completion Rate",
            "Current Streak", "Best Streak", "Status"
        ]
        writer.writerow(headers)

        period = report.get("period", {})
        gen_at = report.get("generated_at", "")
        for h in report.get("habits", []):
            writer.writerow([
                sanitize_csv_field(report.get("report_type")),
                sanitize_csv_field(period.get("start_date")),
                sanitize_csv_field(period.get("end_date")),
                sanitize_csv_field(gen_at),
                sanitize_csv_field(h.get("id")),
                sanitize_csv_field(h.get("name")),
                sanitize_csv_field(h.get("category")),
                sanitize_csv_field(h.get("time_of_day")),
                sanitize_csv_field(h.get("completed")),
                sanitize_csv_field(h.get("missed")),
                sanitize_csv_field(h.get("skipped")),
                sanitize_csv_field(f"{h.get('completion_rate', 0.0)}%"),
                sanitize_csv_field(h.get("current_streak")),
                sanitize_csv_field(h.get("best_streak")),
                sanitize_csv_field(h.get("status"))
            ])

    elif export_type == "habits":
        filename = f"streaklab_habits_{ref_date_str}.csv"
        headers = [
            "Habit ID", "Name", "Description", "Category", "Time of Day", "Target Time",
            "Target Frequency", "Current Streak", "Best Streak", "Reminder", "Status", "Created At"
        ]
        writer.writerow(headers)

        cursor = db.execute("""
            SELECT h.*, r.reminder_time, r.enabled as reminder_enabled
            FROM habits h
            LEFT JOIN habit_reminders r ON h.id = r.habit_id
            ORDER BY h.id ASC
        """)
        for row in cursor.fetchall():
            hid = row["id"]
            cur_s = calculate_current_streak(hid, parse_target_date(ref_date_str), db)
            best_s = calculate_best_streak(hid, parse_target_date(ref_date_str), db)
            rem_str = f"{row['reminder_time']} (Active)" if row['reminder_enabled'] else ("Off" if row['reminder_time'] else "None")

            writer.writerow([
                sanitize_csv_field(row["id"]),
                sanitize_csv_field(row["name"]),
                sanitize_csv_field(row["description"] or ""),
                sanitize_csv_field(row["category"] or "General"),
                sanitize_csv_field(row["time_of_day"] or "Morning"),
                sanitize_csv_field(row["target_time"] or ""),
                sanitize_csv_field(row["target_frequency"] or "daily"),
                sanitize_csv_field(cur_s),
                sanitize_csv_field(best_s),
                sanitize_csv_field(rem_str),
                sanitize_csv_field("Active" if row["active"] == 1 else "Archived"),
                sanitize_csv_field(row["created_at"])
            ])

    csv_data = output.getvalue().encode('utf-8-sig')
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=\"{filename}\"",
            "Cache-Control": "no-cache"
        }
    )


@app.route('/api/milestones/acknowledge', methods=['POST'])
def acknowledge_milestone_api():
    """
    Phase 7: Acknowledges milestone notifications to prevent duplicate alerts.
    Expects JSON: { "milestone_id": int } or { "milestone_ids": [int, ...] }
    """
    if not request.is_json:
        return jsonify({"error": "Request body must be JSON"}), 400

    data = request.get_json() or {}
    ids = []
    if 'milestone_id' in data:
        try:
            ids.append(int(data['milestone_id']))
        except (ValueError, TypeError):
            return jsonify({"error": "milestone_id must be an integer"}), 400
    elif 'milestone_ids' in data:
        raw_ids = data.get('milestone_ids')
        if not isinstance(raw_ids, list):
            return jsonify({"error": "milestone_ids must be a list"}), 400
        for m in raw_ids:
            try:
                ids.append(int(m))
            except (ValueError, TypeError):
                continue

    if not ids:
        return jsonify({"error": "No valid milestone IDs provided"}), 400

    db = get_db()
    placeholders = ",".join("?" for _ in ids)
    db.execute(f"UPDATE goal_milestones SET notified = 1 WHERE id IN ({placeholders})", tuple(ids))
    db.commit()

    return jsonify({"message": "Milestones acknowledged", "acknowledged_ids": ids}), 200


# ---------------------------------------------------------------------------
# PHASE 6: AI HABIT COACH CHAT REST API ENDPOINT
# ---------------------------------------------------------------------------

@app.route('/api/chat', methods=['POST'])
def chat_with_coach_api():
    """
    Phase 6: Conversational AI Habit Coach Chatbox endpoint.
    Accepts:
      {
        "message": "How are my habits going this week?",
        "history": [{"role": "user"|"assistant", "content": "..."}]
      }
    Returns:
      {
        "success": true,
        "reply": "...",
        "source": "ai" | "fallback",
        "evidence": [...],
        "provider": "gemini" | "openai" | "local_fallback"
      }
    """
    # 1. Validate JSON Content-Type
    if not request.is_json:
        return jsonify({"error": "Request body must be JSON"}), 400

    # 2. Parse JSON body
    try:
        data = request.get_json(silent=False)
    except Exception:
        return jsonify({"error": "Malformed JSON payload"}), 400

    if data is None or not isinstance(data, dict):
        return jsonify({"error": "Malformed JSON payload"}), 400

    # 3. Validate message field
    if 'message' not in data:
        return jsonify({"error": "Message is required"}), 400

    raw_message = data['message']
    if not isinstance(raw_message, str):
        return jsonify({"error": "Message must be a string"}), 400

    message = raw_message.strip()
    if not message:
        return jsonify({"error": "Message cannot be empty"}), 400

    if len(message) > 1000:
        return jsonify({"error": "Message is too long (maximum 1000 characters)"}), 400

    # 4. Validate history field
    history = data.get('history', [])
    if history is None:
        history = []
    elif not isinstance(history, list):
        return jsonify({"error": "History must be an array"}), 400

    if len(history) > 20:
        return jsonify({"error": "History exceeds maximum allowed limit (20 messages)"}), 400

    cleaned_history = []
    for item in history:
        if not isinstance(item, dict):
            return jsonify({"error": "Malformed history item: must be an object"}), 400
        role = item.get('role', 'user')
        content = item.get('content')
        if content is None or not isinstance(content, str):
            return jsonify({"error": "Malformed history item: content must be a string"}), 400
        if len(content) > 1000:
            return jsonify({"error": "History item content is too long (maximum 1000 characters)"}), 400
        cleaned_history.append({"role": "model" if role in ("model", "assistant") else "user", "content": content})

    # 5. IP-based sliding window rate limiting (abuse protection)
    client_ip = request.remote_addr or "127.0.0.1"
    if not ai_explainer.check_chat_rate_limit(client_ip):
        return jsonify({"error": "Too many requests. Please wait a moment before sending another message."}), 429

    # 6. Execute coach response grounded in SQLite data
    try:
        db = get_db()
        result = ai_explainer.chat_with_coach(message=message, history=cleaned_history, db=db)
        ai_cfg = ai_explainer.get_ai_config()

        provider_name = ai_cfg["provider"] if (ai_cfg["is_configured"] and result.get("source") == "ai") else "local_fallback"

        return jsonify({
            "success": True,
            "reply": result.get("reply", ""),
            "source": result.get("source", "fallback"),
            "evidence": result.get("evidence", []),
            "provider": provider_name
        }), 200
    except Exception as exc:
        logger.error(f"Error handling chat request: {exc}")
        return jsonify({"error": "An error occurred while processing your message."}), 500


# ---------------------------------------------------------------------------
# ERROR HANDLERS (CLEAN JSON RESPONSES WITHOUT LEAKING SENSITIVE DATA)
# ---------------------------------------------------------------------------

@app.errorhandler(400)
def handle_bad_request(e):
    return jsonify({"error": getattr(e, 'description', 'Bad request')}), 400


@app.errorhandler(404)
def handle_not_found(e):
    return jsonify({"error": getattr(e, 'description', 'Resource not found')}), 404


@app.errorhandler(500)
def handle_internal_error(e):
    return jsonify({"error": "An internal server error occurred"}), 500


# Automatically initialize the database schema on module load / startup
with app.app_context():
    init_db()


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("[*] Starting StreakLab Flask Backend with SQLite (Phase 7)...")
    print(f"[*] Database Path : {app.config['DATABASE']}")
    print("[*] Dashboard URL  : http://127.0.0.1:5000")
    print("[*] Health API    : http://127.0.0.1:5000/api/health")
    print("[*] Habits API    : http://127.0.0.1:5000/api/habits")
    print("[*] Insights API  : http://127.0.0.1:5000/api/insights/explanations")
    print("[*] Chat API      : http://127.0.0.1:5000/api/chat")
    print("[*] Calendar API  : http://127.0.0.1:5000/api/calendar")
    print("[*] Weekly Review : http://127.0.0.1:5000/api/reviews/weekly")
    print("[*] Goals API     : http://127.0.0.1:5000/api/goals")
    print("=" * 60 + "\n")
    app.run(debug=True, host='127.0.0.1', port=5000)
