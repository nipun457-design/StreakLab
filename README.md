# 🔥 StreakLab — Habit Pattern Detector

A college project for the **First-Year Applied AI Tools & Prompt Engineering** course.

StreakLab is a smart habit tracking web application designed to help students and developers build consistent daily routines, visualize streak momentum, and detect hidden behavioral patterns (such as completion drop-offs on specific weekdays or times of day).

---

## 🚀 Technology Stack Roadmap

- **Frontend (Phase 1 — Complete)**: HTML5, CSS3, JavaScript (Vanilla ES6), Bootstrap 5.3, Bootstrap Icons, Chart.js
- **Backend (Phase 2A — Complete)**: Python Flask
- **Database & RESTful APIs (Phase 2B — Complete)**: SQLite (`instance/streaklab.db`), parameterized SQL, foreign-key enforcement, and full CRUD RESTful API endpoints
- **AI Pattern Detection (Phase 4)**: Python, Pandas, and statistical routine analysis

---

## 📂 Project Structure

```text
StreakLab/
│
├── app.py                  # Python Flask server + SQLite database initialization & REST API
├── test_app.py             # Automated unit & integration test suite (17 tests)
├── requirements.txt        # Python dependency manifest (Flask>=3.0.0,<4.0.0)
├── instance/
│   └── streaklab.db        # SQLite database file (auto-generated, git-ignored)
├── templates/
│   └── index.html          # Main dashboard HTML template (Flask Jinja2)
├── static/
│   ├── style.css           # Custom modern responsive styling
│   └── script.js           # Frontend client: API fetch calls, Chart.js logic, metrics
├── README.md               # Beginner-friendly guide and documentation
└── .gitignore              # Git ignore rules (venv, instance/, __pycache__)
```

---

## 🗄️ Database Architecture (Phase 2B)

### 1. Database Location & Auto-Initialization
- The SQLite database is automatically created upon starting the application at:
  ```text
  instance/streaklab.db
  ```
- The `instance/` folder is listed in `.gitignore` so local user databases are never committed to git.
- SQLite foreign key constraints are strictly enforced per connection via `PRAGMA foreign_keys = ON;`.
- Parameterized SQL queries (`?`) are used everywhere to eliminate SQL injection vulnerabilities.

### 2. Schema Specification

#### Table 1: `habits`
Tracks habit definitions and configuration:
- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `name`: TEXT NOT NULL
- `description`: TEXT (optional notes)
- `category`: TEXT (e.g. `Coding`, `Fitness`, `Learning`, `Mindfulness`, `Health`, `Productivity`)
- `time_of_day`: TEXT (default `'Morning'`)
- `target_time`: TEXT (default `'08:00 AM'`)
- `target_frequency`: TEXT (default `'daily'`)
- `created_at`: TIMESTAMP (default current timestamp)
- `active`: INTEGER (default `1`, set to `0` upon deactivation to preserve past streak statistics)

#### Table 2: `habit_records`
Tracks daily execution status per habit:
- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `habit_id`: INTEGER NOT NULL (foreign key referencing `habits(id)` ON DELETE CASCADE)
- `record_date`: TEXT NOT NULL (stored in `YYYY-MM-DD` format)
- `status`: TEXT NOT NULL (`completed`, `missed`, `skipped`, or `pending`)
- `created_at`: TIMESTAMP (default current timestamp)
- `updated_at`: TIMESTAMP (default current timestamp)
- **Constraint**: `UNIQUE(habit_id, record_date)` — ensures at most one record per habit per day.

---

## 📡 RESTful API Endpoints

### 1. Health Diagnostic
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Diagnostic check confirming Flask and SQLite connectivity |

**Example Response**:
```json
{
  "app": "StreakLab",
  "database": "connected",
  "status": "ok"
}
```

---

### 2. Habits Management
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/habits` | Return all active habits with current streak and today's status |
| `POST` | `/api/habits` | Create a new habit (returns `201 Created`) |
| `GET` | `/api/habits/<id>` | Retrieve a single habit by ID |
| `PUT` | `/api/habits/<id>` | Update habit fields (name, description, category, target time, etc.) |
| `DELETE` | `/api/habits/<id>` | Deactivate habit (`active = 0`) preserving historical records |

#### Example: Create Habit (`POST /api/habits`)
**Request Body**:
```json
{
  "name": "Morning 30-min Coding",
  "description": "Daily Python exercises",
  "category": "Coding",
  "time_of_day": "Morning",
  "target_time": "08:00 AM",
  "target_frequency": "daily"
}
```

**Response (`201 Created`)**:
```json
{
  "id": 1,
  "name": "Morning 30-min Coding",
  "description": "Daily Python exercises",
  "category": "Coding",
  "time_of_day": "Morning",
  "timeOfDay": "Morning",
  "target_time": "08:00 AM",
  "targetTime": "08:00 AM",
  "target_frequency": "daily",
  "frequency": "daily",
  "created_at": "2026-10-21 12:00:00",
  "active": 1,
  "streak": 0,
  "status": "pending",
  "weekly_history": ["pending", "pending", "pending", "pending", "pending", "pending", "pending"]
}
```

---

### 3. Daily Records Management
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/records?date=YYYY-MM-DD` | Return all habit records for a specific date (defaults to today) |
| `POST` | `/api/records` | Upsert daily status (`completed`, `missed`, `skipped`, or `pending`) |
| `GET` | `/api/habits/<id>/records` | Return full chronological record history for a habit |

#### Example: Mark Habit Completed (`POST /api/records`)
**Request Body**:
```json
{
  "habit_id": 1,
  "record_date": "2026-10-21",
  "status": "completed"
}
```

**Response (`200 OK` or `201 Created`)**:
```json
{
  "id": 1,
  "habit_id": 1,
  "record_date": "2026-10-21",
  "status": "completed",
  "created_at": "2026-10-21 12:05:00",
  "updated_at": "2026-10-21 12:05:00",
  "streak": 1
}
```

*Note on Status Toggle*: If `status: "pending"` is sent, any existing record for that habit on that date is deleted, reverting the card back to pending.

---

## 📈 Streak and Date Logic

Streak calculations are dynamically evaluated from database records using these documented rules:
1. **Consecutive Days**: A streak counts the number of uninterrupted consecutive completed days ending today (or ending yesterday if today has no record yet).
2. **Skipped Days**: Marking a habit `skipped` acts as an excused rest day. It preserves the existing streak without incrementing or breaking it.
3. **Missed Days**: Marking a habit `missed` breaks the streak immediately (streak becomes `0`).
4. **Pending (Today Unrecorded)**: An unrecorded day *today* does not break yesterday's streak because the day is still in progress.
5. **Gaps (Past Days Unrecorded)**: An unrecorded day *prior to yesterday* indicates an incomplete habit and ends the streak.

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
*(If PowerShell displays an execution policy error, run `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` once).*

---

### Step 3: Install Dependencies (If needed)
```powershell
pip install -r requirements.txt
```

---

### Step 4: Run the Automated Test Suite
Run the 17-test automated verification suite using Python's built-in `unittest` runner:
```powershell
python test_app.py
```
**Expected Output**:
```text
.................
----------------------------------------------------------------------
Ran 17 tests in 1.136s

OK
```

---

### Step 5: Start the Flask Web Application
```powershell
python app.py
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

### Step 6: Verify Dashboard in Browser
1. Open your web browser and go to:
   ```text
   http://127.0.0.1:5000
   ```
2. Verify:
   - Dashboard loads with the **Phase 2B • SQLite Powered** badge.
   - Click **Add Habit**, fill in the details, and click **Save Habit**.
   - Click the **Done** (green checkmark), **Missed** (red X), or **Skipped** (pause) buttons.
   - Observe real-time updates to **Best Streak**, **Completion Rate**, and the **Weekly Consistency** chart.
   - Refresh the page (`F5`) to confirm that all habits, streaks, and statuses persist from SQLite.
   - Filter habits by clicking **Morning**, **Afternoon**, **Evening**, or **All**.

---

### Step 7: Verify APIs via PowerShell (Optional)
Test the health diagnostic:
```powershell
Invoke-RestMethod -Uri http://127.0.0.1:5000/api/health
```

List active habits:
```powershell
Invoke-RestMethod -Uri http://127.0.0.1:5000/api/habits
```

---

## 📅 Development Roadmap

- [x] **Phase 1**: Frontend dashboard with interactive UI, filters, and Chart.js.
- [x] **Phase 2A**: Flask backend foundation, static asset serving via `url_for`, and `/api/health` endpoint.
- [x] **Phase 2B**: SQLite database integration (`instance/streaklab.db`), RESTful API endpoints for habits and daily records, database-backed streaks, and frontend API connection.
- [ ] **Phase 3**: Statistical aggregation engine and advanced habit analytics.
- [ ] **Phase 4**: AI habit pattern detection engine with Python, Pandas, and machine learning insights.
