# 🔥 StreakLab — Habit Pattern Detector & Real AI Habit Coach

A smart habit tracking and behavioral analytics platform for students, developers, and habit-builders.

StreakLab pairs real-time daily habit tracking with an intelligent **Rule-Based Statistical Pattern Engine**, a **Hybrid AI Coaching Layer**, an interactive **Floating AI Habit Coach Chatbox**, and comprehensive **Phase 8 Smart Reminders, Goals & Milestones, Multi-Period Progress Reports, and Secure CSV Data Export**—delivering conversational habit insights, quantifying consistency trends, and providing evidence-grounded recommendations while remaining 100% functional offline.

---

## 📌 Problem Statement & Target Users

* **The Problem**: Conventional habit trackers only record binary completions. They fail to reveal *why* routines break down, *when* willpower drops, or *how* weekends and times of day impact follow-through. Rigid streak systems also penalize legitimate rest days, inducing "streak fatigue" and abandonment.
* **The Solution**: StreakLab introduces:
  1. **Rest-Preserving Streaks**: Excused pauses (`skipped`) preserve consecutive momentum.
  2. **Deterministic Pattern Engine**: Quantifies weekday drop-offs, peak days, time-of-day biases, and consecutive missed trends.
  3. **Real AI Habit Coach Chatbox (Phase 6)**: An interactive floating coach grounded directly in your SQLite check-in history. Ask questions naturally and receive conversational coaching without hallucinations.
  4. **Smart Reminders & Browser Notifications (Phase 8)**: Per-habit reminder schedules, user-gesture permission model, in-app banner fallback, and local time handling without duplicate alerts.
  5. **Goals, Deadlines & Milestones (Phase 7 & 8)**: Measurable targets (weekly frequency, target streaks, total completions) with deadlines, progress tracking, and duplicate-proof milestone badges.
  6. **Multi-Period Progress Reports (Phase 8)**: Daily, weekly, and monthly reports with completion statistics, strengths, and areas needing attention computed from stored records.
  7. **Secure CSV Data Export (Phase 8)**: UTF-8 BOM exports for Habits, Records, Goals, and Reports protected against spreadsheet formula injection (`=+-@\t\r`).
  8. **Guaranteed Offline Resilience**: Runs seamlessly without internet access or API keys using deterministic local fallbacks.
* **Target Users**:
  * Students balancing coursework, project deadlines, and personal habits.
  * Developers establishing daily coding, reading, and wellness routines.
  * Anyone seeking actionable behavioural rhythms rather than vanity counters.

---

## 🚀 Technology Stack Roadmap

| Layer | Technologies | Purpose |
| :--- | :--- | :--- |
| **Frontend** | HTML5, Vanilla ES6 JavaScript, Bootstrap 5.3, Bootstrap Icons, Chart.js | Responsive SPA dashboard, modal forms, Chart.js graphs, floating AI chatbox with chips and bubbles, XSS-safe DOM rendering |
| **Backend** | Python 3.14+, Flask 3.1+ | RESTful API, request validation, sliding-window rate limiting, contextual database connection management (`g.db`) |
| **Database** | SQLite 3 (`instance/streaklab.db`) | ACID persistence, foreign key enforcement (`PRAGMA foreign_keys = ON`), UPSERT conflict handling, indices |
| **Statistical Engine** | Python (`pattern_engine.py`) | **Source of Truth**: Best streaks, active completion rates, weekday drop-offs, peak days, consecutive misses, progress reports |
| **AI Habit Coach** | Python (`ai_explainer.py`), Google Gemini / OpenAI APIs | Conversational habit coaching grounded in SQLite data, prompt injection defense, sliding-window IP rate limiter, deterministic offline fallback |
| **Automated Testing**  | Python `unittest`, `unittest.mock` (`test_app.py`) | 94 isolated automated unit and integration tests using temporary SQLite databases (100% mocked AI) |

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
cd c:\Users\nipun\OneDrive\Desktop\StreakLab
```

### Step 2: Configure Optional AI Provider (Securely in PowerShell)
The application works 100% offline with zero configuration. To connect a real AI provider:

```powershell
# Copy the template to .env (git-ignored)
Copy-Item .env.example .env

# Configure your provider and API key in .env (or in PowerShell session):
$env:AI_PROVIDER="gemini"
$env:AI_API_KEY="your_actual_google_gemini_api_key_here"
$env:AI_MODEL="gemini-1.5-flash"
```

> **Security Note**: Never commit `.env` or paste your API key in Git-tracked files. `.env` is permanently excluded via `.gitignore`.

### Step 3: Run the Complete Automated Test Suite (94 Tests)
```powershell
.\.venv\Scripts\python.exe -m unittest test_app.py
```
**Actual Output**:
```text
...........................AI provider returned invalid non-list response; using local fallback.
..AI provider failed (gemini): Connection timed out. Gracefully falling back to local engine.
.............AI provider returned empty chat response; using local fallback.
....AI Coach provider failed (gemini): URLError: Failed connecting with key AI_KEY_VERY_SECRET_DO_NOT_REVEAL_XYZ123. Falling back to local coach.
....AI Coach provider failed (gemini): Connection timed out. Falling back to local coach.
.AI Coach provider failed (gemini): Gemini API returned HTTP 500. Falling back to local coach.
...........................................
----------------------------------------------------------------------
Ran 94 tests in 9.080s

OK
```

### Step 4: Start the Flask Application
```powershell
.\.venv\Scripts\python.exe app.py
```
**Console Output**:
```text
============================================================
[*] Starting StreakLab Flask Backend with SQLite (Phase 8)...
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

### Step 5: Explore Phase 8 Features in the Browser
1. Open **`http://127.0.0.1:5000`** in your browser.
2. **Smart Reminders & Browser Notifications**:
   - In each habit card, click the **Set Reminder** / **Bell** chip to configure a daily time (e.g. `08:30`) and toggle reminders on/off.
   - Click the top navigation **Bell icon** to open the **Notification Settings Modal**:
     - Review your browser notification permission status (`default`, `granted`, or `denied`).
     - Click **"Enable Browser Notifications"** to trigger the browser prompt (strictly requested on user gesture).
     - Read the transparent explanation about background limitations: standard browser notifications require the tab to be open or active.
     - If notifications are denied or unsupported, a visible **In-App Reminder Banner** automatically alerts you when scheduled times arrive.
     - Reminders are suppressed if the habit is already marked **Completed** today or if already notified in the current minute window.
3. **Enhanced Goals, Deadlines & Milestones**:
   - Click **+ Set Habit Goal** to select among:
     - **Weekly Frequency**: Target 1–7 completions per week.
     - **Target Streak**: Reach a consecutive day streak (e.g. 14, 21, 30 days).
     - **Total Completions**: Total lifetime completions (e.g. 50, 100 sessions).
   - Set an optional **Target Deadline** (`YYYY-MM-DD`).
   - Goals are dynamically categorized as **Active** (in progress), **Completed** (target achieved), or **Overdue** (past deadline without completion).
   - Edit any goal anytime using the pencil button on the goal card.
4. **Progress Reports (Daily, Weekly, Monthly)**:
   - Navigate to the **Progress Reports & Analytics** section.
   - Switch between **Daily**, **Weekly**, and **Monthly** tabs.
   - Pick any reference date and click **Generate Report**.
   - Review high-level KPI cards (Total Habits, Completion Rate, Completed/Missed/Skipped counts, Active Goals).
   - Inspect **Top Performing Habits** and **Habits Needing Attention** calculated from evidence.
   - Browse the detailed habit breakdown table with current and best streaks.
5. **CSV Data Export Center**:
   - In the **CSV Data Export Center**, click any of the 4 dedicated download buttons:
     - **Habits List**: Active habits, categories, schedules, reminders, current streaks, and best streaks.
     - **Check-in History**: Chronological log of check-in records (`completed`, `missed`, `skipped`).
     - **Goals & Milestones**: Active and achieved goals, target types, progress, deadlines, and milestone badges.
     - **Current Progress Report**: Filtered snapshot of the currently selected progress report.
   - All CSV downloads include UTF-8 BOM (`utf-8-sig`) for Microsoft Excel compatibility and defuse spreadsheet formula injection by sanitizing fields starting with `=`, `+`, `-`, `@`, `\t`, or `\r`.
6. Chat with the **AI Habit Coach**:
   - Ask *"What are my habit reminders?"* or *"How are my habit goals this week?"* to see your active targets and schedules.

---

## ⚠️ Known Limitations & Browser Realities

1. **Browser Notification Background Limitations**:
   - Standard browser `Notification.requestPermission()` and `new Notification()` operate within the browser execution context.
   - In accordance with web platform standards, notifications require the page to be open in a browser tab or window. If the browser is completely closed, ordinary web page JavaScript does not run without a dedicated Service Worker and Push Server infrastructure (Web Push API). StreakLab clearly communicates this limitation in the Notification Settings modal.
   - When browser notifications are unsupported or permissions are denied, StreakLab provides a persistent in-app alert banner (`#inAppReminderAlertContainer`) so users never miss a reminder while using the dashboard.
2. **Cold-Start Window**:
   - Pattern detection and multi-day trend analysis require at least 3 daily check-in records to prevent premature generalization from tiny samples. Single-day reports and daily checklists remain fully operational immediately.
3. **Discrete Time-of-Day Slots**:
   - Habit organization uses discrete categories (`Morning`, `Afternoon`, `Evening`) and user-configured `HH:MM` reminder schedules.

---

## 📚 Supplementary Documentation

* **[Architecture Document](file:///c:/Users/nipun/OneDrive/Desktop/StreakLab/docs/ARCHITECTURE.md)**: System flow diagrams, component boundaries, schema tables (`habit_reminders`, `habit_goals`, `goal_milestones`), security model, and formula injection defense.
* **[Testing Guide](file:///c:/Users/nipun/OneDrive/Desktop/StreakLab/docs/TESTING.md)**: Full test matrix (94 test cases), isolation details, mock specifications, and manual verification checklist.
* **[Demo Presentation Guide](file:///c:/Users/nipun/OneDrive/Desktop/StreakLab/docs/DEMO_GUIDE.md)**: Step-by-step live demonstration script covering Reminders, Goals, Progress Reports, CSV Export, AI Chatbox, and Phase 7 Heatmap.

---

## 📅 Development Roadmap Status

- [x] **Phase 1**: Interactive HTML5, CSS3, JavaScript dashboard with Chart.js and filters.
- [x] **Phase 2A**: Flask backend foundation and `/api/health` diagnostic endpoint.
- [x] **Phase 2B**: SQLite database integration (`instance/streaklab.db`), RESTful API endpoints, streak calculation, and frontend API wiring.
- [x] **Phase 3**: Rule-based habit pattern detection engine (`pattern_engine.py`), `/api/insights`, `/api/analytics`, configurable window selector, and statistical metrics.
- [x] **Phase 4**: Hybrid AI explanation and recommendation engine (`ai_explainer.py`), Gemini and OpenAI integrations, local deterministic fallback, in-memory cache with mutation invalidation, and `/api/insights/explanations`.
- [x] **Phase 5**: Final Polish, Edge-Case Verification, Expanded Test Suite, Comprehensive Documentation (`docs/`), and Submission Preparation.
- [x] **Phase 6**: Real AI Habit Coach Chatbox (`/api/chat`), floating frontend chatbox with suggestion chips, DOM-safe rendering, evidence grounding, sliding-window rate limiting, and 17 automated mock-isolated test scenarios.
- [x] **Phase 7**: Smart Progress and Goal Tracking (`/api/calendar`, `/api/reviews/weekly`, `/api/goals`, `/api/milestones/acknowledge`), Habit Calendar Heatmap with date inspection modal, Weekly Progress Review with grounded AI explanations, and Weekly Target Goals with duplicate-prevented milestone notifications.
- [x] **Phase 8**: Smart Reminders & Notifications (`/api/reminders`), Goals & Milestones enhancements (`PUT /api/goals`, streak/total targets, deadlines, active/overdue/completed states), Multi-Period Progress Reports (`/api/reports` daily/weekly/monthly), and Secure CSV Data Export (`/api/export` with UTF-8 BOM and spreadsheet formula injection defense).
