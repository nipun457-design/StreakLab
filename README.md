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
| **Frontend** | HTML5, Vanilla ES6 JavaScript, Bootstrap 5.3, Bootstrap Icons, Chart.js | 7-section single-page application (SPA), modal forms, Chart.js graphs, floating AI chatbox, XSS-safe DOM rendering |
| **Backend** | Python 3.14+, Flask 3.1+ | RESTful API, request validation, sliding-window rate limiting, contextual database connection management (`g.db`), Vercel WSGI support |
| **Database** | SQLite 3 (`instance/streaklab.db` locally, `/tmp/streaklab.db` on Vercel) | ACID persistence, foreign key enforcement (`PRAGMA foreign_keys = ON`), automatic non-destructive column migrations, UPSERT conflict handling |
| **Statistical Engine** | Python (`pattern_engine.py`) | **Source of Truth**: Best streaks, active completion rates, weekday drop-offs, peak days, consecutive misses, progress reports |
| **AI Habit Coach** | Python (`ai_explainer.py`), Google Gemini / OpenAI APIs | Conversational habit coaching grounded in SQLite data, prompt injection defense, sliding-window IP rate limiter, deterministic offline fallback |
| **Automated Testing**  | Python `unittest`, `unittest.mock` (`test_app.py`) | 107 isolated automated unit and integration tests using temporary SQLite databases (100% mocked AI) |

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
   - Observe the live permission badge: `Not Requested Yet`, `Checking...`, `Notifications Enabled` (Granted), `Blocked in Browser` (Denied), or `Unsupported in Browser`.
   - Click **Enable Notifications** to trigger the browser prompt on explicit user gesture.
   - If browser notifications are disabled or the tab is blurred, prominent in-app alert banners automatically appear at the scheduled minute.
5. **CSV Data Export Center**:
   - Download UTF-8 BOM CSV files for Habits, Check-in Records, Goals & Milestones, and Progress Reports with built-in formula injection defenses.
6. **Conversational AI Habit Coach**:
   - Click the floating robot icon or top navbar **AI Coach** button to chat about your routines, slumps, or upcoming goals.

---

## ⚠️ Browser Realities, Background Push & Serverless Deployment

### 1. Browser Notification Execution Context & Honesty
- Standard browser Web Notifications (`Notification.requestPermission()` and `new Notification()`) run inside the browser tab context.
- **Tab Activity Requirement**: In standard web browsers, client-side JavaScript timers (`setInterval` / `setTimeout`) only fire while the browser has an open or backgrounded tab running the application. Ordinary web page JavaScript cannot execute when the browser application is completely closed.
- StreakLab transparently informs users of this requirement and provides an automatic **in-app banner alert** fallback so users never miss a reminder while actively using the application.

### 2. Reliable Background Notifications via Web Push & VAPID (Optional Production Architecture)
To deliver persistent background reminders when the browser tab or entire web browser is closed, the application requires the W3C Push API, a Service Worker, and a Web Push protocol server:

1. **Service Worker**: A registered background service worker (`sw.js`) that listens for `push` events and displays notifications via `self.registration.showNotification()`.
2. **VAPID Key Pair**: Voluntary Application Server Identification (VAPID) credentials generated using `pywebpush`:
   ```bash
   pip install pywebpush
   python -c "from pywebpush import webpush; import json; print(json.dumps(webpush.generate_vapid_keypair()))"
   ```
3. **Environment-Only Secrets Configuration**:
   ```ini
   VAPID_PUBLIC_KEY=BK...
   VAPID_PRIVATE_KEY=your_vapid_private_key_secret_here
   VAPID_CLAIM_EMAIL=mailto:admin@streaklab.app
   ```
4. **Strict Security Requirement**:
   - `VAPID_PRIVATE_KEY`, API secrets, and server configuration must **never** be exposed in frontend JavaScript, templates, or committed to GitHub repositories.
   - Only `VAPID_PUBLIC_KEY` is shared with client-side `pushManager.subscribe()`.
5. **Persistent Background Scheduler**: A persistent background task runner (e.g., Celery with Redis, APScheduler worker, or cron-triggered webhook) queries scheduled reminders each minute and transmits encrypted Web Push payloads to the browser vendor's push service (e.g. Mozilla autopush, Google FCM).

### 3. Vercel Serverless Deployment Safety
- **Read-Only Filesystem**: Serverless runtimes on Vercel mount the application directory (`/var/task`) as read-only. Attempting to create folders or write SQLite databases in `/var/task/instance/` produces an immediate `OSError: [Errno 30] Read-only file system` error.
- **Configurable Database Path**: In `app.py`, `get_database_path()` dynamically checks `os.environ.get('VERCEL')`. When running in Vercel serverless mode, it automatically resolves to `/tmp/streaklab.db` before any directory creation or database connection:
  ```python
  if os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
      return '/tmp/streaklab.db'
  ```
- **Local Consistency**: In local development, StreakLab continues using the project directory `instance/streaklab.db`.

---

## 📚 Supplementary Documentation

* **[Architecture Document](file:///c:/Users/nipun/OneDrive/Desktop/StreakLab/docs/ARCHITECTURE.md)**: System flow diagrams, component boundaries, schema tables (`habits`, `habit_records`, `habit_reminders`, `habit_goals`, `goal_milestones`), security model, and formula injection defense.
* **[Testing Guide](file:///c:/Users/nipun/OneDrive/Desktop/StreakLab/docs/TESTING.md)**: Full test matrix (107 test cases), isolation details, mock specifications, and manual verification checklist.
* **[Demo Presentation Guide](file:///c:/Users/nipun/OneDrive/Desktop/StreakLab/docs/DEMO_GUIDE.md)**: Step-by-step live demonstration script covering Reminders, Goals, Progress Reports, CSV Export, AI Chatbox, and Calendar Heatmap.

---

## 📅 Development Roadmap Status

- [x] **Foundation & Diagnostics**: Flask backend foundation, SQLite database integration (`instance/streaklab.db`), RESTful API endpoints, streak calculation, and `/api/health` diagnostic endpoint.
- [x] **Behavioral Pattern Engine**: Rule-based habit pattern detection engine (`pattern_engine.py`), `/api/insights`, `/api/analytics`, configurable window selector, and statistical metrics.
- [x] **Hybrid AI Explanations**: Evidence-grounded explanations and recommendations (`ai_explainer.py`), Gemini and OpenAI integrations, local deterministic fallback, and `/api/insights/explanations`.
- [x] **Real AI Habit Coach Chatbox**: Conversational AI Coach (`/api/chat`), floating frontend chatbox with suggestion chips, DOM-safe rendering, evidence grounding, and sliding-window rate limiting.
- [x] **Progress & Goal Tracking**: Habit Calendar Heatmap (`/api/calendar`), Weekly Progress Review (`/api/reviews/weekly`), Goals & Milestones (`/api/goals`), and duplicate-prevented badge celebrations.
- [x] **Automatic Habit Reminders**: Reminder time selection and default-ON toggle during habit creation, 1-to-1 persistence in `habits` and `habit_reminders`, edit time & toggle controls, local time scheduling, and automatic silence on habit completion/deletion.
- [x] **Organized 7-Section Product UI**: Dedicated views (Overview, My Habits, Calendar, Insights, Goals, Reports, Settings), unified 4-card metric summary, prominent Add Habit trigger, and elimination of development-phase jargon.
- [x] **Multi-Period Reports & CSV Export**: Daily, weekly, and monthly reports (`/api/reports`), UTF-8 BOM CSV exports (`/api/export`) protected against formula injection (`=+-@\t\r`).
- [x] **Vercel Serverless Safety**: Dynamic `/tmp/streaklab.db` path resolution, eliminating read-only filesystem errors.
- [x] **Automated Test Suite**: 107 isolated automated unit and integration tests passing with 100% mocked AI and temporary database fixtures.

