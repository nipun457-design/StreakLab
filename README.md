# 🔥 StreakLab — Habit Pattern Detector

A smart habit tracking and behavioral analytics platform for students, developers, and habit-builders.

StreakLab pairs real-time daily habit tracking with an intelligent **Rule-Based Statistical Pattern Engine** and a **Hybrid AI Coaching Layer**—delivering actionable routine insights, quantifying consistency trends, and providing evidence-grounded recommendations while remaining 100% functional offline.

---

## 📌 Problem Statement & Target Users

* **The Problem**: Conventional habit trackers only record binary completions. They fail to reveal *why* routines break down, *when* willpower drops, or *how* weekends and times of day impact follow-through. Rigid streak systems also penalize legitimate rest days, inducing "streak fatigue" and abandonment.
* **The Solution**: StreakLab introduces:
  1. **Rest-Preserving Streaks**: Excused pauses (`skipped`) preserve consecutive momentum.
  2. **Deterministic Pattern Engine**: Quantifies weekday drop-offs, peak days, time-of-day biases, and consecutive missed trends.
  3. **Hybrid AI Explanations**: Grounded exclusively in actual SQLite records; never hallucinates statistics or claims unearned streaks.
  4. **Guaranteed Offline Resilience**: Runs seamlessly without internet access or API keys using deterministic local fallbacks.
* **Target Users**:
  * Students balancing coursework, project deadlines, and personal habits.
  * Developers establishing daily coding, reading, and wellness routines.
  * Anyone seeking actionable behavioural rhythms rather than vanity counters.

---

## 🚀 Technology Stack Roadmap

| Layer | Technologies | Purpose |
| :--- | :--- | :--- |
| **Frontend** | HTML5, Vanilla ES6 JavaScript, Bootstrap 5.3, Bootstrap Icons, Chart.js | Responsive SPA dashboard, modal forms, Chart.js graphs, filter pills, XSS-safe DOM rendering |
| **Backend** | Python 3.14+, Flask 3.1+ | RESTful API, request validation, error handlers, contextual database connection management (`g.db`) |
| **Database** | SQLite 3 (`instance/streaklab.db`) | ACID persistence, foreign key enforcement (`PRAGMA foreign_keys = ON`), UPSERT conflict handling, indices |
| **Statistical Engine** | Python (`pattern_engine.py`) | **Source of Truth**: Best streaks, active completion rates, weekday drop-offs, peak days, consecutive misses |
| **Hybrid AI Explainer**| Python (`ai_explainer.py`), Google Gemini / OpenAI APIs | Evidence-grounded explanations, prompt injection defense, TTL caching, deterministic offline fallback |
| **Automated Testing**  | Python `unittest`, `unittest.mock` (`test_app.py`) | 46 isolated automated unit and integration tests using temporary SQLite databases |

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

### 2. Analytics & Visualizations

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/analytics?days=7` | Daily completion trend, weekday stats, habit breakdown, and time-of-day distribution |
| `GET` | `/api/insights?days=30` | Statistical pattern detection engine raw insights |
| `GET` | `/api/insights/<id>?days=30` | Single-habit statistical breakdown |

---

### 3. Habits & Records CRUD

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

## 🖥️ How to Run and Test Locally (Windows PowerShell)

### Step 1: Open PowerShell in Project Folder
```powershell
cd c:\Users\nipun\OneDrive\Desktop\StreakLab
```

### Step 2: Run the Complete Automated Test Suite (46 Tests)
```powershell
.\.venv\Scripts\python.exe test_app.py
```
**Actual Output**:
```text
...........................AI provider returned invalid non-list response; using local fallback.
..AI provider failed (gemini): Connection timed out. Gracefully falling back to local engine.
.................
----------------------------------------------------------------------
Ran 46 tests in 3.791s

OK
```

### Step 3: Start the Flask Application
```powershell
.\.venv\Scripts\python.exe app.py
```
**Console Output**:
```text
============================================================
[*] Starting StreakLab Flask Backend with SQLite (Phase 5)...
[*] Database Path : C:\Users\nipun\OneDrive\Desktop\StreakLab\instance\streaklab.db
[*] Dashboard URL  : http://127.0.0.1:5000
[*] Health API    : http://127.0.0.1:5000/api/health
[*] Habits API    : http://127.0.0.1:5000/api/habits
[*] Insights API  : http://127.0.0.1:5000/api/insights/explanations
============================================================
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
```

### Step 4: Explore the Dashboard in Your Browser
1. Open **`http://127.0.0.1:5000`** in any modern web browser.
2. Check the top navbar for the **Phase 5 • Hybrid AI & Analytics** badge.
3. In the right column under **Habit Pattern Detector**:
   - Notice the **Source indicator** (`Rule Engine` when offline, `AI (provider)` when configured).
   - Use the window dropdown (**7**, **14**, **30**, **60**, **90** days) to toggle analysis horizons.
   - Observe evidence pills and practical recommendations for each detected pattern.
4. Check in habits (Done, Missed, Skipped) and watch KPI counters, Chart.js graphs, and pattern explanations update in real time.

---

## ⚠️ Known Limitations & Future Roadmap

1. **Cold-Start Window**: Requires at least 3 daily check-ins before computing multi-day trends to avoid conclusions drawn from tiny sample sizes.
2. **Correlation vs Causation**: Weekday and time-of-day biases represent historical correlations, not clinical causal claims.
3. **Discrete Habit Slots**: Habits are assigned to discrete categories (`Morning`, `Afternoon`, `Evening`) rather than variable micro-timestamps.
4. **Binary Check-ins**: Tracks `completed`, `missed`, and `skipped`; future iterations could support numeric increments (e.g. 20 of 30 pages read).

---

## 📚 Supplementary Documentation

* **[Architecture Document](file:///c:/Users/nipun/OneDrive/Desktop/StreakLab/docs/ARCHITECTURE.md)**: System flow diagrams, component boundaries, and security model.
* **[Testing Guide](file:///c:/Users/nipun/OneDrive/Desktop/StreakLab/docs/TESTING.md)**: Full test matrix, isolation details, and manual verification checklist.
* **[Demo Presentation Guide](file:///c:/Users/nipun/OneDrive/Desktop/StreakLab/docs/DEMO_GUIDE.md)**: Step-by-step 5-minute live demonstration script for presentations.

---

## 📅 Development Roadmap Status

- [x] **Phase 1**: Interactive HTML5, CSS3, JavaScript dashboard with Chart.js and filters.
- [x] **Phase 2A**: Flask backend foundation and `/api/health` diagnostic endpoint.
- [x] **Phase 2B**: SQLite database integration (`instance/streaklab.db`), RESTful API endpoints, streak calculation, and frontend API wiring.
- [x] **Phase 3**: Rule-based habit pattern detection engine (`pattern_engine.py`), `/api/insights`, `/api/analytics`, configurable window selector, and statistical metrics.
- [x] **Phase 4**: Hybrid AI explanation and recommendation engine (`ai_explainer.py`), Gemini and OpenAI integrations, local deterministic fallback, in-memory cache with mutation invalidation, and `/api/insights/explanations`.
- [x] **Phase 5**: Final Polish, Edge-Case Verification, Expanded 46-Test Suite, Comprehensive Documentation (`docs/`), and Submission Preparation.
