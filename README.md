# 🔥 StreakLab — Habit Pattern Detector & Real AI Habit Coach

A smart habit tracking and behavioral analytics platform for students, developers, and habit-builders.

StreakLab pairs real-time daily habit tracking with an intelligent **Rule-Based Statistical Pattern Engine**, a **Hybrid AI Coaching Layer**, an interactive **Floating AI Habit Coach Chatbox**, and comprehensive **Automatic Habit Reminders, 7-Section Product UI, Goals & Milestones, Multi-Period Progress Reports, and Secure CSV Data Export**—delivering conversational habit insights, quantifying consistency trends, and providing evidence-grounded recommendations while remaining 100% functional offline and seamlessly deployable on Vercel.

---

## 📌 Problem Statement & Target Users

* **The Problem**: Conventional habit trackers only record binary completions. They fail to reveal *why* routines break down, *when* willpower drops, or *how* weekends and times of day impact follow-through. Rigid streak systems also penalize legitimate rest days, inducing "streak fatigue" and abandonment.
* **The Solution**: StreakLab introduces:
  1. **Automatic Habit Reminders & Local Scheduling**: Users choose reminder times while creating habits (ON by default), with seamless time editing, toggle controls, and duplicate prevention.
  2. **Organized Product Navigation (7 Views)**: Clear separation into Overview, My Habits, Calendar, Insights, Goals, Reports, and Settings with a unified 4-card metric summary.
  3. **Rest-Preserving Streaks**: Excused pauses (`skipped`) preserve consecutive momentum.
  4. **Deterministic Pattern Engine**: Quantifies weekday drop-offs, peak days, time-of-day biases, and consecutive missed trends.
  5. **Real AI Habit Coach Chatbox**: An interactive floating coach grounded directly in your SQLite check-in history without hallucinations.
  6. **Goals, Deadlines & Milestones**: Measurable targets (weekly frequency, target streaks, total completions) with deadlines, progress tracking, and duplicate-proof milestone badges.
  7. **Multi-Period Progress Reports**: Daily, weekly, and monthly reports with completion statistics, strengths, and areas needing attention computed from stored records.
  8. **Secure CSV Data Export**: UTF-8 BOM exports for Habits, Records, Goals, and Reports protected against spreadsheet formula injection (`=+-@\t\r`).
  9. **Guaranteed Offline Resilience & Serverless Safety**: Runs seamlessly without internet access or API keys using deterministic local fallbacks, with automatic `/tmp` database resolution on Vercel.
* **Target Users**:
  * Students balancing coursework, project deadlines, and personal habits.
  * Developers establishing daily coding, reading, and wellness routines.
  * Anyone seeking actionable behavioural rhythms rather than vanity counters.

---

## 🚀 Technology Stack Roadmap

| Layer | Technologies | Purpose |
| :--- | :--- | :--- |
| **Frontend** | HTML5, Vanilla ES6 JavaScript, Bootstrap 5.3, Bootstrap Icons, Chart.js | 7-section single-page application (SPA), modal forms, Chart.js graphs, floating AI chatbox, XSS-safe DOM rendering, PWA Manifest |
| **Backend** | Python 3.14+, Flask 3.1+ | RESTful API, request validation, sliding-window rate limiting, contextual database connection management (`g.db`), Vercel WSGI support |
| **Database** | PostgreSQL (Production via Neon / Supabase / Vercel Postgres using `pg8000`) & SQLite 3 (Local dev & test fallback) | ACID persistence, unified query parameterization (`?` auto-translated to `%s`), self-healing schema across 7 tables, automated migration utilities |
| **Push Service** | Standards-based W3C Web Push (`pywebpush`, `py-vapid`), Service Worker (`/sw.js`) | Genuine mobile OS push notifications when website is closed, VAPID encryption, duplicate notification suppression, expired endpoint pruning |
| **Statistical Engine** | Python (`pattern_engine.py`) | **Source of Truth**: Best streaks, active completion rates, weekday drop-offs, peak days, consecutive misses, progress reports |
| **AI Habit Coach** | Python (`ai_explainer.py`), Google Gemini / OpenAI APIs | Conversational habit coaching grounded in database evidence, prompt injection defense, sliding-window IP rate limiter, deterministic offline fallback |
| **Automated Testing**  | Python `unittest`, `unittest.mock` (`test_app.py`) | 125 isolated automated unit and regression tests passing with 100% mocked AI and push services |

---

## 📂 Project Structure

```text
StreakLab/
│
├── app.py                  # Flask server + SQLite initialization & RESTful API endpoints
├── pattern_engine.py       # Rule-based statistical pattern detection & analytics engine
├── ai_explainer.py         # Hybrid AI explanation & recommendation engine + local fallback
├── test_app.py             # Automated unit & integration test suite (46 isolated tests)
├── requirements.txt        # Python dependency manifest (Flask>=3.0.0,<4.0.0)
├── .env.example            # Environment configuration template for AI providers
├── .gitignore              # Git ignore rules (.env, .venv, instance/, __pycache__, *.db)
│
├── docs/                   # Submission & architectural documentation
│   ├── ARCHITECTURE.md     # System flow diagrams, component breakdown, and security model
│   ├── TESTING.md          # Comprehensive test cases, coverage metrics, and execution logs
│   └── DEMO_GUIDE.md       # Step-by-step 5-minute live demonstration script
│
├── templates/
│   └── index.html          # Main dashboard HTML template (Flask Jinja2)
│
├── static/
│   ├── style.css           # Custom modern responsive styling & tokens
│   └── script.js           # Client application: Fetch calls, dynamic cards, Chart.js graphs
│
└── instance/
    └── streaklab.db        # SQLite database file (auto-generated, git-ignored)
```

---

## 🧠 System Architecture (Hybrid AI)

```text
┌──────────────────────┐
│   SQLite Database    │  (instance/streaklab.db)
└──────────┬───────────┘
           │ Parameterized SQL queries
           ▼
┌──────────────────────┐
│    Pattern Engine    │  (pattern_engine.py)
│  (Source of Truth)   │  • Deterministic statistical calculations
└──────────┬───────────┘  • Execution rates, streak records, drop-offs
           │ Structured Evidence & Detected Patterns
           ▼
┌──────────────────────┐
│ Hybrid AI Explainer  │  (ai_explainer.py)
│  (Evidence-Grounded) │  • Optional AI Provider (Gemini / OpenAI)
└──────────┬───────────┘  • Deterministic Local Fallback (offline)
           │              • In-memory cache with auto-invalidation
           │ Enriched Explanations + Recommendations
           ▼
┌──────────────────────┐
│  Frontend Dashboard  │  (templates/index.html & static/script.js)
│                      │  • Pattern Cards, Source Badges (AI vs Rule)
└──────────────────────┘  • XSS-safe rendering, dynamic window filter
```

### Two Distinct Responsibilities

1. **Pattern Detection (`pattern_engine.py`)**:
   - The statistical engine is the **sole source of truth** for all numbers, counts, completion rates, streaks, and detected patterns.
   - AI is never allowed to invent statistics, fabricate habit records, or replace deterministic calculations with guesses.

2. **AI Explanation (`ai_explainer.py`)**:
   - The explainer module translates detected patterns into supportive, student-friendly coaching explanations and practical next steps.
   - Every claim is grounded **strictly in the numerical evidence** supplied by `pattern_engine.py`.
   - If an AI provider is unconfigured, unreachable, or returns malformed output, the system **automatically and instantly falls back** to deterministic local explanations.

---

## 🗄️ Database Schema

### Table: `habits`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique habit identifier |
| `name` | TEXT | NOT NULL | Habit title (e.g., "Morning 30-Min Coding") |
| `description` | TEXT | NULLABLE | Detailed goal description |
| `category` | TEXT | DEFAULT 'General' | Category (Coding, Fitness, Study, Mindfulness, Health) |
| `time_of_day` | TEXT | DEFAULT 'Morning' | Time slot ('Morning', 'Afternoon', 'Evening') |
| `target_time` | TEXT | DEFAULT '08:00 AM' | Scheduled reminder time |
| `target_frequency` | TEXT | DEFAULT 'daily' | Frequency ('Daily', 'Weekdays', 'Weekends') |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |
| `active` | INTEGER | DEFAULT 1 | Active flag (0 = archived, preserves history) |

### Table: `habit_records`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique check-in record ID |
| `habit_id` | INTEGER | NOT NULL, FK -> habits(id) ON DELETE CASCADE | Associated habit |
| `record_date` | TEXT | NOT NULL | Date in `YYYY-MM-DD` format |
| `status` | TEXT | NOT NULL, CHECK IN ('completed', 'missed', 'skipped') | Daily check-in status |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | First recorded timestamp |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last updated timestamp |
| *Constraint* | UNIQUE | `(habit_id, record_date)` | Enforces exactly one record per habit per day |

### Table: `habit_goals` (Phase 7 & 8)
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique goal ID |
| `habit_id` | INTEGER | NOT NULL, FK -> habits(id) ON DELETE CASCADE | Associated habit |
| `target_type` | TEXT | NOT NULL DEFAULT 'weekly_completions' | Metric type: `'weekly_completions'`, `'target_streak'`, `'total_completions'` |
| `target_value` | INTEGER | NOT NULL, CHECK(target_value >= 1) | Target threshold (e.g. 5 days/wk, 14-day streak, 30 completions) |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Goal creation timestamp |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last update timestamp |
| `active` | INTEGER | DEFAULT 1 | Active state (1 = active, 0 = archived) |
| `end_date` | TEXT | DEFAULT NULL | Optional target deadline (`YYYY-MM-DD`) |
| *Constraint* | UNIQUE | `(habit_id, target_type)` | Prevents duplicate active goal types per habit |

### Table: `goal_milestones` (Phase 7 & 8)
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique milestone award ID |
| `goal_id` | INTEGER | NOT NULL, FK -> habit_goals(id) ON DELETE CASCADE | Associated goal |
| `habit_id` | INTEGER | NOT NULL, FK -> habits(id) ON DELETE CASCADE | Associated habit |
| `milestone_type` | TEXT | NOT NULL | Type: `'target_reached'`, `'streak_3'`, `'streak_7'`, `'streak_14'`, `'streak_30'` |
| `milestone_period` | TEXT | NOT NULL | Scope tag (e.g. `'2026-W43'`, `'streak_7'`, `'total_30'`) |
| `achieved_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Achievement timestamp |
| `notified` | INTEGER | DEFAULT 0 | 0 = unacknowledged banner, 1 = acknowledged |
| *Constraint* | UNIQUE | `(habit_id, milestone_type, milestone_period)` | **Duplicate Prevention**: Physical DB guarantee against repeat badges |

### Table: `habit_reminders` (Phase 8)
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique reminder schedule ID |
| `habit_id` | INTEGER | NOT NULL UNIQUE, FK -> habits(id) ON DELETE CASCADE | 1-to-1 association with habit |
| `reminder_time` | TEXT | NOT NULL | 24-hour daily reminder schedule in `HH:MM` format |
| `enabled` | INTEGER | NOT NULL DEFAULT 1 | Reminder toggle (1 = enabled, 0 = muted) |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Schedule creation timestamp |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last update timestamp |

---

## 📊 Rule-Based Detection Engine & Formulas

### 1. Active Completion Rate Formula
$$\text{Completion Rate} = \frac{\text{completed}}{\text{completed} + \text{missed}} \times 100$$
*Skipped check-ins represent excused rest days or planned pauses and do not penalize the completion rate.*

### 2. Supported Behavioral Patterns

| Pattern Type | Identifier | Detection Trigger | Practical Recommendation |
| :--- | :--- | :--- | :--- |
| **No Habits** | `no_habits` | 0 active habits in database. | Guidance to create initial daily routines. |
| **Insufficient Data** | `insufficient_data` | $< 3$ total records in evaluation window. | Advice to check in for 3-5 days to unlock trends. |
| **Strong Routine** | `strong_routine` | Rate $\ge 80\%$ across $\ge 5$ evaluated check-ins. | Keep as anchor routine; practice habit stacking. |
| **At-Risk Habit** | `at_risk_habit` | Rate $< 50\%$ across $\ge 5$ evaluated check-ins. | Lower initial friction: reduce duration or shift time. |
| **Weekday Drop-Off** | `weekday_dropoff` | Weekday rate drops $\ge 25\%$ below overall average. | Prepare materials/cues the evening before. |
| **Peak Performance** | `peak_performance_day`| Weekday rate $\ge 20\%$ above overall average (or 100%).| Tackle demanding or high-focus goals on peak days. |
| **Time-of-Day Bias** | `time_of_day_preference` | $\ge 20\%$ gap between Morning, Afternoon, Evening.| Schedule difficult habits into optimal energy window. |
| **Repeated Misses** | `repeated_misses` | $\ge 3$ consecutive missed check-ins. | Restart with a 2-minute micro-habit to rebuild momentum. |
| **Streak Milestone** | `streak_milestone` | Active continuous streak $\ge 7$ days. | Acknowledge milestone to reinforce habit identity. |

---

## ⚙️ AI Provider Configuration

StreakLab supports Google Gemini, OpenAI-compatible providers, or completely offline local fallback without external dependencies.

Configuration is handled through environment variables (or a local `.env` file):

| Variable | Description | Example |
| :--- | :--- | :--- |
| `AI_PROVIDER` | Active AI provider (`gemini`, `openai`, or empty for local fallback) | `gemini` |
| `AI_API_KEY` | Provider API key (keep private; never commit) | `AIzaSy...` |
| `AI_MODEL` | Model identifier (defaults: `gemini-1.5-flash`, `gpt-4o-mini`) | `gemini-1.5-flash` |
| `AI_ENDPOINT` | Optional custom base URL or proxy | `https://custom-proxy.com/v1` |
| `AI_TIMEOUT` | Request timeout in seconds (default: 6, min: 2, max: 30) | `6` |

### Setting Up a `.env` File (Optional)

Copy `.env.example` to `.env`:
```powershell
cp .env.example .env
```

Edit `.env` with your preferred provider:
```ini
AI_PROVIDER=gemini
AI_API_KEY=your_gemini_api_key_here
AI_MODEL=gemini-1.5-flash
AI_TIMEOUT=6
```

> **Security Note:** `.env` is listed in `.gitignore` and is never committed. If `.env` is omitted or `AI_API_KEY` is blank, StreakLab runs 100% offline using its built-in rule-based fallback.

---

## 🛡️ Guardrails & Safety Controls

1. **Prompt Injection Defense**: User-supplied habit names and descriptions are treated strictly as passive alphanumeric data and are never interpreted as model instructions.
2. **Zero External Calls on Startup & Tests**: No network requests to AI providers occur during application boot or automated testing.
3. **No Hallucinated Statistics**: Explanations cite only the provided counts, rates, and sample sizes.
4. **Constructive & Safe Tone**: The explainer avoids medical or psychological diagnoses, shame, blame, or forceful language.
5. **Length Limits & XSS Protection**: Explanation and recommendation strings are capped in length and always escaped via `escapeHtml()` before DOM insertion.
6. **Fault-Tolerant Resilience**: Network drops, timeouts, non-200 responses, or invalid JSON from an AI provider never crash the app or yield a `500 Internal Server Error`; the local fallback returns immediately with HTTP `200 OK`.

---

## 📡 RESTful API Endpoints

### 1. Hybrid AI Explanations & Patterns

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/insights/explanations` | Returns detected patterns with evidence-grounded explanations, recommendations, and source badges |
| `GET` | `/api/insights/explanations?days=30` | Configurable evaluation window (1 to 365 days) |
| `GET` | `/api/insights/explanations?habit_id=<id>` | Deep-dive explanations for a specific habit |
| `GET` | `/api/insights?explain=true` | Backward-compatible endpoint returning raw insights plus explanations |

#### Example: `GET /api/insights/explanations?days=14`
**Response (`200 OK`)**:
```json
{
  "period": {
    "days": 14,
    "start_date": "2026-10-08",
    "end_date": "2026-10-21"
  },
  "summary": {
    "total_active_habits": 3,
    "total_records": 21,
    "total_completed": 18,
    "total_missed": 2,
    "total_skipped": 1,
    "overall_completion_rate": 90.0,
    "best_overall_streak": 8
  },
  "explanations": [
    {
      "pattern_type": "strong_routine",
      "habit_id": 1,
      "habit_name": "Morning Coding",
      "title": "Strong Routine: Morning Coding",
      "explanation": "'Morning Coding' shows consistent execution with a 90.0% completion rate across 10 evaluated days in the past 14 days.",
      "recommendation": "Maintain this strong routine as an anchor habit. You can stack a newer or harder routine immediately after it.",
      "evidence_summary": "9 completed out of 10 evaluated check-ins (90.0% consistency).",
      "confidence": "medium",
      "source": "fallback"
    }
  ],
  "source": "fallback",
  "ai_configured": false,
  "provider": "local_fallback"
}
```

---

### 2. Conversational AI Habit Coach Chatbox (Phase 6)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/chat` | Send a natural-language query to the StreakLab AI Habit Coach grounded strictly in SQLite habit records |

#### Request Schema:
```json
{
  "message": "How are my habits going this week?",
  "history": [
    {"role": "user", "content": "Hello coach!"},
    {"role": "assistant", "content": "Hello! I am StreakLab AI Habit Coach..."}
  ]
}
```

#### Response Schema (`200 OK`):
```json
{
  "success": true,
  "reply": "Here is how your habits are tracking this week:\n\n• Today you have completed 1 of 2 scheduled habits.\n• Over the past 7 days, your overall completion rate is 71.4% (5 completed, 2 missed).\n\n🔥 **Top Performer:** 'Morning 30-min Coding' with a 100% rate and an active 4-day streak.",
  "source": "ai",
  "evidence": [
    {"label": "7-Day Rate", "value": "71.4%"},
    {"label": "Active Habits", "value": "2"}
  ],
  "provider": "gemini"
}
```

#### Validation & Guardrails:
* Content-Type must be `application/json` (returns `400` on malformed or non-JSON payloads).
* `message`: Required non-empty string, max 1,000 characters.
* `history`: Array bounded to max 20 items, max 1,000 chars per message.
* Abuse protection: Sliding-window in-memory IP rate limiter (30 requests/minute, returns `429 Too Many Requests`).
* Prompt-injection defense: Database fields and user queries are treated as passive data. Attempts to override instructions or dump secrets are ignored.
* Offline fallback: Returns `source: "fallback"` and `provider: "local_fallback"` with deterministic responses when unconfigured or offline.

---

### 3. Analytics & Visualizations

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/analytics?days=7` | Daily completion trend, weekday stats, habit breakdown, and time-of-day distribution |
| `GET` | `/api/insights?days=30` | Statistical pattern detection engine raw insights |
| `GET` | `/api/insights/<id>?days=30` | Single-habit statistical breakdown |

---

### 4. Habits & Records CRUD

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/habits` | Retrieve all active habits with streaks and today's status |
| `POST` | `/api/habits` | Create a new habit (`201 Created`) |
| `GET` | `/api/habits/<id>` | Retrieve a single habit by ID |
| `PUT` | `/api/habits/<id>` | Update habit fields |
| `DELETE` | `/api/habits/<id>` | Soft-deactivate habit (`active = 0`) preserving streak history |
| `GET` | `/api/records?date=YYYY-MM-DD` | Get all records for a date |
| `POST` | `/api/records` | Upsert daily status (`completed`, `missed`, `skipped`, or `pending`) |
| `GET` | `/api/habits/<id>/records` | Retrieve full chronological check-in history |
| `GET` | `/api/health` | Diagnostic check confirming Flask and SQLite status |

---

### 5. Smart Progress & Goal Tracking (Phase 7 & 8)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/calendar` | Habit Calendar Heatmap with day-by-day status (`completed`, `partial`, `missed`, `skipped`, `unrecorded`, `future`, `today`). Supports `?month=YYYY-MM` and `?habit_id=<id>`. |
| `GET` | `/api/reviews/weekly` | Structured weekly progress review: completion stats, comparison to previous week, trend, top recorded days, habits needing attention, and AI Coach explanation. Supports `?date=YYYY-MM-DD`. |
| `GET` | `/api/goals` | Retrieve all active habit goals, target types, deadlines, and live progress. |
| `POST` | `/api/goals` | Create or upsert a habit goal (`target_type`: `'weekly_completions'`, `'target_streak'`, `'total_completions'`, `target_value`: $\ge 1$, optional `end_date`: `'YYYY-MM-DD'`). |
| `PUT` | `/api/goals/<id>` | Update an existing goal target, target type, deadline, or active status. |
| `DELETE` | `/api/goals/<id>` | Deactivate a habit goal target. |
| `POST` | `/api/milestones/acknowledge` | Acknowledge and dismiss an achieved milestone banner (`{"milestone_id": 1}`). |

---

### 6. Smart Reminders, Reports & CSV Export (Phase 8)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/reminders` | Retrieve all configured habit reminders with current day completion status. |
| `POST` | `/api/reminders` | Set or update daily reminder schedule (`{"habit_id": 1, "reminder_time": "08:30", "enabled": 1}`). |
| `PUT` | `/api/reminders/<habit_id>` | Edit reminder schedule time or toggle enabled state (`{"reminder_time": "09:00", "enabled": 1}`). |
| `DELETE` | `/api/reminders/<habit_id>` | Remove reminder schedule for habit. |
| `GET` | `/api/reports` | Multi-period progress report: `?type=daily|weekly|monthly&date=YYYY-MM-DD`. Calculates completion rates, streaks, best habits, and habits needing attention. |
| `GET` | `/api/export` | Downloadable CSV export: `?type=habits|records|goals|report[&report_type=...][&date=...]`. Features UTF-8 BOM encoding and formula injection sanitization. |

---

## 🖥️ How to Run and Test Locally (Windows PowerShell)

### Step 1: Open PowerShell in Project Folder
```powershell
cd c:### Step 3: Run the Complete Automated Test Suite (107 Tests)
```powershell
.\.venv\Scripts\python.exe -m unittest test_app.py
```
**Actual Output**:
```text
....................................AI provider returned invalid non-list response; using local fallback.
..AI provider failed (gemini): Connection timed out. Gracefully falling back to local engine.
.............AI provider returned empty chat response; using local fallback.
....AI Coach provider failed (gemini): URLError: Failed connecting with key AI_KEY_VERY_SECRET_DO_NOT_REVEAL_XYZ123. Falling back to local coach.
....AI Coach provider failed (gemini): Connection timed out. Falling back to local coach.
.AI Coach provider failed (gemini): Gemini API returned HTTP 500. Falling back to local coach.
...............................................
----------------------------------------------------------------------
Ran 107 tests in 16.008s

OK
```

### Step 4: Start the Flask Application
```powershell
.\.venv\Scripts\python.exe app.py
```
**Console Output**:
```text
============================================================
[*] Starting StreakLab Flask Backend with SQLite...
[*] Database Path : C:\Users\nipun\OneDrive\Desktop\StreakLab\instance\streaklab.db
[*] Dashboard URL  : http://127.0.0.1:5000
[*] Health API    : http://127.0.0.1:5000/api/health
[*] Habits API    : http://127.0.0.1:5000/api/habits
[*] Insights API  : http://127.0.0.1:5000/api/insights/explanations
[*] Chat API      : http://127.0.0.1:5000/api/chat
[*] Calendar API  : http://127.0.0.1:5000/api/calendar
[*] Weekly Review : http://127.0.0.1:5000/api/reviews/weekly
[*] Goals API     : http://127.0.0.1:5000/api/goals
[*] Reminders API : http://127.0.0.1:5000/api/reminders
[*] Reports API   : http://127.0.0.1:5000/api/reports
[*] Export API    : http://127.0.0.1:5000/api/export
============================================================
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
```

### Step 5: Explore StreakLab Features in the Browser
1. Open **`http://127.0.0.1:5000`** in your browser.
2. **Automatic Habit Reminders & Workflow**:
   - Click **New Habit** or the **+ Add Habit** button on the Today's Habit Checklist header.
   - Choose a scheduled time (e.g. `08:00 AM`). The **Daily Reminder** toggle is switch **ON by default**.
   - Upon creation, the habit and its scheduled reminder are persisted automatically in both `habits` and `habit_reminders` tables.
   - Click the **Pencil (Edit)** button on any habit card to adjust the scheduled time, disable a reminder, or re-enable it without recreating the habit.
   - When a habit is marked **Done** for today or deleted, reminders are automatically silenced.
3. **Organized 7-Section Product Navigation**:
   - **Overview**: Hero summary, 4 unified metric cards (Completion Rate, Current Streak, Longest Streak, Completed Habits), Today's Habit Checklist, and compact charts.
   - **My Habits**: Complete habit catalog management, target frequency, reminders, and edit controls.
   - **Calendar**: Full-width interactive habit activity heatmap and date inspection modal.
   - **Insights**: Evidence-grounded behavioral pattern detection, peak performance days, and weekly review cards.
   - **Goals**: Target milestones (weekly, streak, total), target deadlines, and duplicate-proof badge celebrations.
   - **Reports**: Daily, weekly, and monthly progress reviews computed from stored SQLite records.
   - **Settings**: Browser notification permissions, active reminder schedule management, and CSV data exports.
4. **Browser Notifications & In-App Alert Fallback**:
   - Click **Reminders** in the top navigation bar to open the Notification Settings modal.
   - Observe the live permission badge: `Not Requested Yet`, `Checking...`, `Notifications Enabled` (Granted), `Blocked in Browser` (## 🛠️ Root Cause Investigations & Architecture Upgrades

### 1. Priority 1 — Habits Disappearing Bug (Data Loss on Vercel)
* **Root Cause**: Vercel Serverless Functions execute inside ephemeral micro-VM containers. In previous deployments, writing to SQLite at `/tmp/streaklab.db` appeared to work during a single request session. However, `/tmp` in serverless is temporary and isolated per execution instance:
  - When the serverless function cold-starts or idles, the container is destroyed along with its `/tmp` filesystem.
  - When multiple requests route to different concurrent container instances, each instance sees a distinct, empty database file.
* **Fix & Architecture**:
  - Implemented a unified database layer (`database.py`) providing automatic abstraction between **PostgreSQL** in production and **SQLite** locally.
  - StreakLab detects `DATABASE_URL`, `POSTGRES_URL`, or `POSTGRES_PRISMA_URL` in the environment.
  - Automatically translates `?` parameter placeholders to PostgreSQL `%s` syntax while enforcing parameterized queries to prevent SQL injection.
  - Self-healing schema: auto-initializes all 7 tables with proper indexes (`idx_records_habit_date`, `idx_reminders_habit`, `idx_push_endpoint`, `idx_notif_habit_date`).
  - Zero-data-loss SQLite-to-PostgreSQL migration utilities (`python database.py --migrate` or `POST /api/admin/migrate-sqlite`).

### 2. Priority 2 — Edit Habit Bug ("Habit Not Found")
* **Root Cause**:
  1. **Strict Type Mismatch in Frontend**: `static/script.js` was comparing `Number(h.id) === Number(habitId)`, but some habit IDs were rendered as strings from form inputs, causing in-memory state lookup or select prefill to fail.
  2. **Frequency Capitalization Desync**: HTML select elements had capitalized values (`Daily`, `Weekdays`, `Weekends`), whereas database defaults stored lowercase (`daily`), causing option selection to fail to bind on modal open.
  3. **Database Connection Isolation**: In serverless instances without self-healing tables, separate routes could query unmigrated tables.
* **Fix**:
  - Synchronized frontend ID casting to `Number(h.id) === Number(habitId) || String(h.id) === String(habitId)`.
  - Added case-insensitive frequency normalizer in both frontend and backend.
  - Unified `PUT /api/habits/<int:habit_id>` endpoint updates habits in-place and synchronizes `habit_reminders` atomically without creating duplicate rows.

### 3. Priority 3 — Real Mobile Web Push Notifications
* **Architecture**:
  - **PWA Installation**: Implemented Web App Manifest (`static/manifest.json`), responsive icons (`static/icons/`), and root service worker (`static/sw.js`).
  - **Explicit User Interaction**: Permission is requested only after clicking "Enable Mobile Push" (never unprompted on page load).
  - **VAPID Security**: Server-side Web Push delivery via `push_service.py` using `pywebpush` and `py-vapid`. Public key is safely exposed via `GET /api/push/status`; private key remains securely in server environment variables.
  - **Background Serverless Scheduler**: Does not rely on Flask background threads (which terminate immediately upon serverless response completion). Reminders are checked via `GET /api/cron/reminders`, securely configured as a Vercel Cron Job (`* * * * *`) and authenticated with `CRON_SECRET`.
  - **Duplicate Prevention**: Every sent notification logs an immutable event in `habit_notification_logs (habit_id, notification_date)`. If a habit is already completed for today or was already notified, delivery is automatically suppressed.
  - **Expired Subscriptions Pruning**: When browser push services return HTTP 404 or 410 (Gone), expired endpoints are automatically deactivated from `push_subscriptions`.

---

## 📱 Mobile Compatibility & Setup Guide

### iPhone & iPad (iOS / iPadOS 16.4+)
* **Requirement**: Apple requires web applications to be added to the iOS Home Screen before Web Push notifications can be granted permission or received in the background.
* **Installation Steps**:
  1. Open StreakLab in **Safari**.
  2. Tap the **Share** button (square with arrow pointing up).
  3. Scroll down and tap **Add to Home Screen**.
  4. Launch StreakLab from your Home Screen icon.
  5. Go to **Settings & Data Management** and tap **Enable Mobile Push**.
  6. Tap **Allow** when iOS prompts for notification permissions.

### Android (Chrome, Edge, Firefox, Brave)
* **Installation Steps**:
  1. Open StreakLab in your browser.
  2. Tap the browser menu `(⋮)` and select **Install App** or **Add to Home screen**.
  3. Go to **Settings** and tap **Enable Mobile Push**.
  4. Tap **Allow** when the system prompt appears.

---

## 🚀 Production Deployment & Manual Configuration Steps

To deploy StreakLab to Vercel with persistent PostgreSQL storage and real Web Push notifications, follow these exact steps:

### Step 1: Provision a Persistent PostgreSQL Database
Create a free PostgreSQL database on any managed cloud provider:
* **Option A: Neon (Recommended)**: Go to [neon.tech](https://neon.tech), create a project, and copy the `postgres://...` connection string.
* **Option B: Supabase**: Go to [supabase.com](https://supabase.com), create a project, and copy the Connection String (URI, pooling port 5432 or 6543).
* **Option C: Vercel Postgres**: In your Vercel Project Dashboard, navigate to the **Storage** tab, create a Postgres database, and link it.

### Step 2: Generate VAPID Push Notification Credentials
Run the following Python one-liner locally to generate your cryptographic VAPID keypair:
```powershell
.\.venv\Scripts\python.exe -c "import push_service, json; print(json.dumps(push_service.generate_vapid_keypair(), indent=2))"
```
Output:
```json
{
  "public_key": "BEl...",
  "private_key": "ABC..."
}
```

### Step 3: Configure Vercel Environment Variables
In your Vercel Project Dashboard, navigate to **Settings** > **Environment Variables** and add:

| Variable Name | Example Value | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `postgresql://user:pass@ep-xyz.neon.tech/neondb?sslmode=require` | Persistent PostgreSQL database connection string |
| `VAPID_PUBLIC_KEY` | `BEl...` (from Step 2) | Application Server Public Key for browser subscription |
| `VAPID_PRIVATE_KEY` | `ABC...` (from Step 2) | Server-side private key (kept secret) |
| `VAPID_CLAIM_EMAIL` | `mailto:your-email@domain.com` | Contact URI for push delivery services |
| `CRON_SECRET` | `generate-any-secure-random-token` | Bearer token to protect scheduled reminder trigger |
| `GEMINI_API_KEY` | *(Optional)* | For AI Habit Coach provider |

### Step 4: Configure the Push Reminder Scheduler
StreakLab includes a preconfigured Vercel Cron trigger in `vercel.json`:
```json
{
  "crons": [
    {
      "path": "/api/cron/reminders",
      "schedule": "* * * * *"
    }
  ]
}
```
* **Vercel Pro Plans**: Vercel Cron automatically runs every minute and supplies `Authorization: Bearer <CRON_SECRET>`.
* **Vercel Hobby / External Schedulers**: Set up a free recurring cron monitor on [cron-job.org](https://cron-job.org) or [updown.io](https://updown.io) targeting:
  - **URL**: `https://your-streaklab.vercel.app/api/cron/reminders`
  - **Interval**: Every 1 minute (or every 5 minutes)
  - **Header**: `Authorization: Bearer <your-CRON_SECRET>` (or `x-cron-secret: <your-CRON_SECRET>`)

### Step 5: (Optional) Migrate Existing Local SQLite Records to PostgreSQL
If you have existing habits in your local SQLite database and wish to transfer them into PostgreSQL without data loss:
```powershell
# Set your production DATABASE_URL in your local shell session
$env:DATABASE_URL="postgresql://user:pass@ep-xyz.neon.tech/neondb?sslmode=require"

# Run the automated migration script
.\.venv\Scripts\python.exe database.py --migrate
```
All habits, check-in history, goals, milestones, reminders, and push subscriptions will be imported with preserved primary keys.

---

## 📚 Supplementary Documentation

* **[Architecture Document](file:///c:/Users/nipun/OneDrive/Desktop/StreakLab/docs/ARCHITECTURE.md)**: System flow diagrams, component boundaries, schema tables (`habits`, `habit_records`, `habit_reminders`, `habit_goals`, `goal_milestones`, `push_subscriptions`, `habit_notification_logs`), security model, and formula injection defense.
* **[Testing Guide](file:///c:/Users/nipun/OneDrive/Desktop/StreakLab/docs/TESTING.md)**: Full test matrix (125 test cases), isolation details, mock specifications, and manual verification checklist.
* **[Demo Presentation Guide](file:///c:/Users/nipun/OneDrive/Desktop/StreakLab/docs/DEMO_GUIDE.md)**: Step-by-step live demonstration script covering Reminders, Goals, Progress Reports, CSV Export, AI Chatbox, and Calendar Heatmap.

---

## 📅 Development Roadmap Status

- [x] **Foundation & Diagnostics**: Flask backend foundation, RESTful API endpoints, streak calculation, and `/api/health` diagnostic endpoint.
- [x] **Persistent Cloud Storage (Priority 1)**: Unified database abstraction layer (`database.py`) supporting PostgreSQL in production and SQLite locally, self-healing schema across 7 tables, automated migration utilities.
- [x] **Habit Edit Bug Fix (Priority 2)**: Record ID type normalization, frequency case insensitivity, atomic in-place updates, and reminder synchronization.
- [x] **Real Mobile Web Push (Priority 3)**: Standards-based Web Push, service worker `/sw.js`, PWA manifest, VAPID encryption, duplicate notification suppression, and iOS/Android instructions.
- [x] **Behavioral Pattern Engine**: Rule-based habit pattern detection engine (`pattern_engine.py`), `/api/insights`, `/api/analytics`, configurable window selector, and statistical metrics.
- [x] **Hybrid AI Explanations & Coach**: Evidence-grounded explanations (`ai_explainer.py`), conversational AI Coach (`/api/chat`), and sliding-window rate limiting.
- [x] **Progress & Goal Tracking**: Habit Calendar Heatmap (`/api/calendar`), Weekly Progress Review (`/api/reviews/weekly`), Goals & Milestones (`/api/goals`).
- [x] **Multi-Period Reports & CSV Export**: Daily, weekly, and monthly reports (`/api/reports`), UTF-8 BOM CSV exports (`/api/export`) protected against formula injection (`=+-@\t\r`).
- [x] **Automated Test Suite (Priority 5)**: 125 isolated automated unit and regression tests passing with 100% mocked AI and push services. views (Overview, My Habits, Calendar, Insights, Goals, Reports, Settings), unified 4-card metric summary, prominent Add Habit trigger, and elimination of development-phase jargon.
- [x] **Multi-Period Reports & CSV Export**: Daily, weekly, and monthly reports (`/api/reports`), UTF-8 BOM CSV exports (`/api/export`) protected against formula injection (`=+-@\t\r`).
- [x] **Vercel Serverless Safety**: Dynamic `/tmp/streaklab.db` path resolution, eliminating read-only filesystem errors.
- [x] **Automated Test Suite**: 107 isolated automated unit and integration tests passing with 100% mocked AI and temporary database fixtures.

