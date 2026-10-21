# 🔥 StreakLab — Habit Pattern Detector

A college project for the **First-Year Applied AI Tools & Prompt Engineering** course.

StreakLab is a smart habit tracking web application designed to help students and developers build consistent daily routines, visualize streak momentum, and detect hidden behavioral patterns (such as completion drop-offs on specific weekdays or times of day).

---

## 🚀 Technology Stack Roadmap

- **Frontend (Phase 1 — Complete)**: HTML5, CSS3, JavaScript (Vanilla ES6), Bootstrap 5.3, Bootstrap Icons, Chart.js
- **Backend (Phase 2A — Complete)**: Python Flask
- **Database & RESTful APIs (Phase 2B — Complete)**: SQLite (`instance/streaklab.db`), parameterized SQL, foreign-key enforcement, and full CRUD RESTful API endpoints
- **Habit Pattern Detection Engine (Phase 3 — Complete)**: Rule-based statistical pattern detection (`pattern_engine.py`), dynamic insights generation, analysis window customization, and `/api/insights` + `/api/analytics` endpoints
- **AI Pattern Detection (Phase 4)**: Python, Pandas, and machine-learning routines

---

## 📂 Project Structure

```text
StreakLab/
│
├── app.py                  # Python Flask server + SQLite database initialization & REST API
├── pattern_engine.py       # Rule-based statistical pattern detection & analytics engine (Phase 3)
├── test_app.py             # Automated unit & integration test suite (30 tests)
├── requirements.txt        # Python dependency manifest (Flask>=3.0.0,<4.0.0)
├── instance/
│   └── streaklab.db        # SQLite database file (auto-generated, git-ignored)
├── templates/
│   └── index.html          # Main dashboard HTML template (Flask Jinja2)
├── static/
│   ├── style.css           # Custom modern responsive styling
│   └── script.js           # Frontend client: API fetch calls, pattern insights rendering, Chart.js
├── README.md               # Beginner-friendly guide and documentation
└── .gitignore              # Git ignore rules (venv, instance/, __pycache__)
```

---

## 🧠 Habit Pattern Detection Engine (Phase 3)

The pattern detection engine (`pattern_engine.py`) analyzes actual SQLite records to uncover actionable behavioral patterns without relying on hardcoded sample data or external paid APIs.

### 1. Analysis Window
- **Configurable Window**: Accepts a `days` query parameter (default: `30` days, valid range: `1` to `365` days).
- **Date Filtering**: Evaluates records between `start_date` (`end_date - (days - 1)`) and `end_date` (defaults to today).
- **Future Exclusion**: Records with dates in the future are strictly excluded from historical calculations.

### 2. Completion Rate Definition
- **Active Execution Rate (Primary Metric)**:
  $$\text{Completion Rate} = \frac{\text{completed}}{\text{completed} + \text{missed}} \times 100$$
- **Treatment of Skipped Days**: Skipped check-ins represent excused rest days or planned pauses (e.g., travel, illness, rest schedule). They do **not** penalize the habit completion rate.
- **Division-by-Zero Guard**: If a habit has only skipped records or zero evaluated check-ins, the rate evaluates safely to `0.0%`.

### 3. Detection Rules & Thresholds

| Pattern Identifier | Name | Detection Rule / Threshold | Practical Recommendation |
| :--- | :--- | :--- | :--- |
| `strong_routine` | Strong Routine | Completion rate $\ge 80.0\%$ with $\ge 5$ evaluated check-ins in the window. | Keep as an anchor habit or stack new habits on top of it. |
| `at_risk_habit` | At-Risk Habit | Completion rate $< 50.0\%$ with $\ge 5$ evaluated check-ins in the window. | Reduce friction: lower target duration or shift time of day. |
| `weekday_dropoff` | Weekday Drop-off | A weekday with $\ge 3$ records where rate drops $\ge 25\%$ below overall average. | Set reminders or prepare materials the evening before. |
| `peak_performance_day` | Peak Performance Day | A weekday with $\ge 3$ records where rate is $\ge 20\%$ above average (or $100\%$). | Capitalize on this energy for demanding or high-focus goals. |
| `time_of_day_preference` | Time-of-Day Window | Compares Morning vs Afternoon vs Evening habits when $\ge 2$ categories have $\ge 5$ records each and rate difference is $\ge 20\%$. | Shift struggling habits into your optimal routine window. |
| `repeated_misses` | Recent Missed Trend | 3 or more consecutive missed check-ins from the most recent record. | Commit to a 2-minute micro-habit to restart momentum. |
| `streak_milestone` | Streak Milestone | Active continuous streak $\ge 7$ consecutive days. | Celebrate continuous streak progress and habit loop formation. |
| `insufficient_data` | Insufficient Data | Fewer than 3 total records across all active habits in the window. | Guidance message encouraging daily check-ins to unlock insights. |

### 4. Qualitative Confidence Levels
- **`high`**: Substantial sample size ($\ge 14$ observations for habits, $\ge 8$ for weekdays).
- **`medium`**: Moderate sample size ($7\text{--}13$ observations for habits, $4\text{--}5$ for weekdays).
- **`low`**: Initial observations ($5\text{--}6$ observations for habits, $3$ for weekdays).
*Note*: Confidence levels are qualitative sample-size indicators, not probabilistic p-values.

---

## 📡 RESTful API Endpoints

### 1. Health Diagnostic
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Diagnostic check confirming Flask and SQLite connectivity |

---

### 2. Habits Management
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/habits` | Return all active habits with current streak and today's status |
| `POST` | `/api/habits` | Create a new habit (`201 Created`) |
| `GET` | `/api/habits/<id>` | Retrieve a single habit by ID |
| `PUT` | `/api/habits/<id>` | Update habit fields (name, description, category, target time, etc.) |
| `DELETE` | `/api/habits/<id>` | Deactivate habit (`active = 0`) preserving historical records |

---

### 3. Daily Records Management
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/records?date=YYYY-MM-DD` | Return all habit records for a specific date (defaults to today) |
| `POST` | `/api/records` | Upsert daily status (`completed`, `missed`, `skipped`, or `pending`) |
| `GET` | `/api/habits/<id>/records` | Return full chronological record history for a habit |

---

### 4. Habit Pattern Detection & Analytics (Phase 3)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/insights?days=30` | Return overall summary and all detected pattern insights |
| `GET` | `/api/insights/<id>?days=30` | Return deep-dive stats, weekday breakdown, and patterns for a single habit |
| `GET` | `/api/analytics?days=30` | Return structured time-series and weekday data for dashboard charts |

#### Example: `GET /api/insights?days=30`
**Response (`200 OK`)**:
```json
{
  "period": {
    "days": 30,
    "start_date": "2026-09-22",
    "end_date": "2026-10-21"
  },
  "summary": {
    "total_active_habits": 3,
    "total_records": 24,
    "total_completed": 19,
    "total_missed": 3,
    "total_skipped": 2,
    "overall_completion_rate": 86.4,
    "best_overall_streak": 8
  },
  "insights": [
    {
      "type": "strong_routine",
      "habit_id": 1,
      "habit_name": "30-Min Coding Practice",
      "title": "Strong Routine: 30-Min Coding Practice",
      "message": "'30-Min Coding Practice' has an exceptional 90.0% completion rate across 10 evaluated check-ins in the past 30 days.",
      "evidence": {
        "completed": 9,
        "missed": 1,
        "skipped": 1,
        "completion_rate": 90.0,
        "sample_size": 10,
        "period_days": 30
      },
      "confidence": "medium",
      "recommendation": "This habit is well-established. Consider keeping it as an anchor routine or stacking a new habit onto it."
    }
  ]
}
```

#### Example: `GET /api/analytics?days=7`
**Response (`200 OK`)**:
```json
{
  "period": { "days": 7, "start_date": "2026-10-15", "end_date": "2026-10-21" },
  "summary": {
    "total_active_habits": 3,
    "total_completed": 15,
    "total_missed": 2,
    "total_skipped": 1,
    "overall_completion_rate": 88.2
  },
  "daily_trend": [
    { "date": "2026-10-15", "completed": 2, "missed": 0, "skipped": 0, "total": 2, "completion_rate": 100.0 },
    { "date": "2026-10-16", "completed": 3, "missed": 0, "skipped": 0, "total": 3, "completion_rate": 100.0 }
  ],
  "weekday_statistics": [
    { "day_index": 0, "day_name": "Monday", "completed": 3, "missed": 0, "skipped": 0, "total": 3, "completion_rate": 100.0 }
  ],
  "habit_breakdown": [
    { "id": 1, "name": "30-Min Coding Practice", "category": "Coding", "completed": 6, "missed": 0, "skipped": 1, "completion_rate": 100.0, "best_streak": 6 }
  ],
  "time_of_day_distribution": {
    "Morning": { "completed": 10, "missed": 1, "skipped": 0, "rate": 90.9, "total": 11 },
    "Afternoon": { "completed": 3, "missed": 1, "skipped": 1, "rate": 75.0, "total": 5 },
    "Evening": { "completed": 2, "missed": 0, "skipped": 0, "rate": 100.0, "total": 2 }
  }
}
```

---

## 🖥️ How to Run and Test Locally (Windows PowerShell)

### Step 1: Open PowerShell in Project Folder
```powershell
cd c:\Users\nipun\OneDrive\Desktop\StreakLab
```

---

### Step 2: Activate the Virtual Environment
```powershell
.\.venv\Scripts\Activate.ps1
```

---

### Step 3: Run the Complete Automated Test Suite
Run the 30-test automated verification suite:
```powershell
.\.venv\Scripts\python.exe test_app.py
```
**Expected Output**:
```text
..............................
----------------------------------------------------------------------
Ran 30 tests in 2.829s

OK
```

---

### Step 4: Start the Flask Web Application
```powershell
.\.venv\Scripts\python.exe app.py
```
**Expected Console Output**:
```text
============================================================
[*] Starting StreakLab Flask Backend with SQLite (Phase 2B)...
[*] Database Path : C:\Users\nipun\OneDrive\Desktop\StreakLab\instance\streaklab.db
[*] Dashboard URL  : http://127.0.0.1:5000
[*] Health API    : http://127.0.0.1:5000/api/health
[*] Habits API    : http://127.0.0.1:5000/api/habits
============================================================
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
```

---

### Step 5: Verify the Dashboard in Your Browser
1. Open **`http://127.0.0.1:5000`** in Chrome, Edge, or Firefox.
2. Check that the top navbar shows the **Phase 3 • Pattern Engine** badge.
3. In the right column under **Habit Pattern Detector**:
   - Use the window selector to toggle between **Last 7 Days**, **Last 14 Days**, **Last 30 Days**, **Last 60 Days**, and **Last 90 Days**.
   - Notice the dynamic pattern cards showing detected routines, evidence metrics, confidence pills, and practical recommendations.
4. Mark a habit as completed or missed; observe the insights and charts dynamically refreshing.

---

## ⚠️ Known Limitations of the Rule-Based Approach

1. **Cold Start Period**: The engine requires at least 3 check-ins before generating insights to prevent false-positive conclusions from tiny sample sizes.
2. **Correlation vs Causation**: Weekday and time-of-day patterns indicate observed correlations, not causal relationships (e.g., lower Sunday completion might stem from travel or different wake-up times).
3. **Discrete Categorization**: Time-of-day analysis groups habits by their scheduled category (`Morning`, `Afternoon`, `Evening`) rather than precise execution timestamps.
4. **Binary Daily Status**: Statuses are modeled as `completed`, `missed`, or `skipped`; partial completions (e.g., 15 mins of a 30-min goal) are not yet represented.

---

## 📅 Development Roadmap

- [x] **Phase 1**: Frontend dashboard with interactive UI, filters, and Chart.js.
- [x] **Phase 2A**: Flask backend foundation, static asset serving via `url_for`, and `/api/health` endpoint.
- [x] **Phase 2B**: SQLite database integration (`instance/streaklab.db`), RESTful API endpoints for habits and daily records, database-backed streaks, and frontend API connection.
- [x] **Phase 3**: Rule-based habit pattern detection engine (`pattern_engine.py`), `/api/insights`, `/api/insights/<id>`, `/api/analytics`, configurable analysis window, and dynamic dashboard integration.
- [ ] **Phase 4**: Advanced machine-learning habit pattern detection and routine optimization.
