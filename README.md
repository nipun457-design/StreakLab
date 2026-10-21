# 🔥 StreakLab — Habit Pattern Detector

A smart habit tracking and behavioral analytics platform for students and developers.

StreakLab helps you build consistent daily routines, visualize streak momentum, and detect hidden behavioral patterns (such as completion drop-offs on specific weekdays or times of day).

In **Phase 4**, StreakLab introduces a **Hybrid AI Explanation & Recommendation Engine** that pairs deterministic statistical rules with evidence-grounded AI explanations—delivering friendly, personalized coaching while remaining 100% functional offline.

---

## 🚀 Technology Stack Roadmap

- **Frontend (Phase 1 — Complete)**: HTML5, CSS3, JavaScript (Vanilla ES6), Bootstrap 5.3, Bootstrap Icons, Chart.js
- **Backend (Phase 2A — Complete)**: Python Flask
- **Database & RESTful APIs (Phase 2B — Complete)**: SQLite (`instance/streaklab.db`), parameterized SQL, foreign-key enforcement, and full CRUD RESTful API endpoints
- **Habit Pattern Detection Engine (Phase 3 — Complete)**: Rule-based statistical pattern detection (`pattern_engine.py`), dynamic insights generation, analysis window customization, and `/api/insights` + `/api/analytics` endpoints
- **Hybrid AI Explanations & Recommendations (Phase 4 — Complete)**: Grounded AI coaching (`ai_explainer.py`), Gemini and OpenAI-compatible providers, offline deterministic fallback, in-memory caching, and `/api/insights/explanations`

---

## 📂 Project Structure

```text
StreakLab/
│
├── app.py                  # Python Flask server + SQLite database initialization & REST API
├── pattern_engine.py       # Rule-based statistical pattern detection & analytics engine (Phase 3)
├── ai_explainer.py         # Hybrid AI explanation & recommendation engine + local fallback (Phase 4)
├── test_app.py             # Automated unit & integration test suite (41 tests)
├── requirements.txt        # Python dependency manifest (Flask>=3.0.0,<4.0.0)
├── .env.example            # Environment configuration template for AI providers
├── instance/
│   └── streaklab.db        # SQLite database file (auto-generated, git-ignored)
├── templates/
│   └── index.html          # Main dashboard HTML template (Flask Jinja2)
├── static/
│   ├── style.css           # Custom modern responsive styling
│   └── script.js           # Frontend client: API fetch calls, AI explanation rendering, Chart.js
├── README.md               # Beginner-friendly guide and documentation
└── .gitignore              # Git ignore rules (venv, .env, instance/, __pycache__)
```

---

## 🧠 System Architecture (Phase 4: Hybrid AI)

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

## ⚡ Deterministic Local Fallback & In-Memory Cache

### Supported Pattern Types in Local Fallback

| Pattern Type | Local Fallback Behavior |
| :--- | :--- |
| `no_habits` | Welcoming guide to create the first daily habit. |
| `insufficient_data` | Clear explanation that at least 3-5 check-ins are required before trends unlock. |
| `strong_routine` | Factual consistency summary with habit-stacking recommendation. |
| `at_risk_habit` | Factual friction diagnosis with advice on lowering target duration. |
| `weekday_dropoff` | Quantified percentage drop on specific weekday with preparation advice. |
| `peak_performance_day` | Quantified peak completion rate with momentum-capitalizing recommendation. |
| `time_of_day_preference` | Quantified comparison between Morning, Afternoon, and Evening habits. |
| `repeated_misses` | Identifies consecutive missed check-ins and suggests a 2-minute micro-habit restart. |
| `streak_milestone` | Acknowledges continuous multi-day streaks with milestone reinforcement. |

### Caching Strategy

- Explanations are cached in memory using a fingerprint of the evaluation window, target date, and underlying evidence.
- The cache expires after 5 minutes (TTL).
- **Auto-Invalidation**: Whenever a habit is created (`POST /api/habits`), updated (`PUT /api/habits/<id>`), archived (`DELETE /api/habits/<id>`), or checked in (`POST /api/records`), the cache is immediately cleared to ensure the UI displays real-time data.

---

## 📡 RESTful API Endpoints

### 1. Hybrid AI Explanations & Patterns (Phase 4)

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

### Step 2: Run the Complete Automated Test Suite (41 Tests)
```powershell
.\.venv\Scripts\python.exe test_app.py
```
**Expected Output**:
```text
.........................................
----------------------------------------------------------------------
Ran 41 tests in 1.529s

OK
```

### Step 3: Start the Flask Application
```powershell
.\.venv\Scripts\python.exe app.py
```
**Console Output**:
```text
============================================================
[*] Starting StreakLab Flask Backend with SQLite (Phase 4)...
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
1. Open **`http://127.0.0.1:5000`** in any browser.
2. Look at the **Habit Pattern Detector** card on the right:
   - Notice the **Phase 4 • Hybrid AI Explanations** badge.
   - The footer displays whether explanations are sourced from **AI** or the **Rule Engine**.
   - Each card displays the pattern title, explanation, supporting evidence box, confidence pill, and recommendation.
   - Use the window dropdown (**7**, **14**, **30**, **60**, **90** days) to analyze different time horizons.
3. Check in habits (Done, Missed, Skipped) and watch the charts and pattern explanations update in real time.

---

## 📅 Development Roadmap Status

- [x] **Phase 1**: Interactive HTML5, CSS3, JavaScript dashboard with Chart.js and filters.
- [x] **Phase 2A**: Flask backend foundation and `/api/health` endpoint.
- [x] **Phase 2B**: SQLite database integration (`instance/streaklab.db`), RESTful API endpoints, streak calculation, and frontend API wiring.
- [x] **Phase 3**: Rule-based habit pattern detection engine (`pattern_engine.py`), `/api/insights`, `/api/analytics`, configurable window selector, and statistical metrics.
- [x] **Phase 4**: Hybrid AI explanation and recommendation engine (`ai_explainer.py`), Gemini and OpenAI integrations, local deterministic fallback, in-memory cache with mutation invalidation, `/api/insights/explanations`, and automated test suite.
