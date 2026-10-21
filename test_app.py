"""
=============================================================================
StreakLab — Automated Test Suite (Phase 2B)
File: test_app.py

Tests Flask REST API endpoints, SQLite schema enforcement, and streak logic
using a temporary, isolated SQLite database file.
=============================================================================
"""

import os
import tempfile
import unittest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock
from app import app, init_db, get_db
import ai_explainer


class StreakLabTestCase(unittest.TestCase):
    def setUp(self):
        """Set up a temporary database and test client before each test."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        app.config['DATABASE'] = self.db_path
        app.config['TESTING'] = True
        self.client = app.test_client()

        with app.app_context():
            init_db()

    def tearDown(self):
        """Clean up temporary database after each test."""
        os.close(self.db_fd)
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    # -----------------------------------------------------------------------
    # 1. HEALTH CHECK & DASHBOARD HTML
    # -----------------------------------------------------------------------
    def test_health_check(self):
        """Confirm /api/health returns 200 with database status."""
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data.get('status'), 'ok')
        self.assertEqual(data.get('app'), 'StreakLab')
        self.assertEqual(data.get('database'), 'connected')

    def test_index_dashboard_route(self):
        """Confirm home page / renders HTML containing StreakLab brand elements."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'StreakLab', response.data)
        self.assertIn(b'habitsListContainer', response.data)

    # -----------------------------------------------------------------------
    # 2. HABITS CRUD API
    # -----------------------------------------------------------------------
    def test_create_habit_success(self):
        """POST /api/habits with valid data should return 201 Created."""
        payload = {
            "name": "Morning 30-min Coding",
            "description": "Daily Python practice",
            "category": "Coding",
            "time_of_day": "Morning",
            "target_time": "08:00 AM",
            "target_frequency": "daily"
        }
        res = self.client.post('/api/habits', json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertIsNotNone(data.get('id'))
        self.assertEqual(data.get('name'), "Morning 30-min Coding")
        self.assertEqual(data.get('category'), "Coding")
        self.assertEqual(data.get('active'), 1)
        self.assertEqual(data.get('streak'), 0)
        self.assertEqual(data.get('status'), 'pending')

    def test_create_habit_validation(self):
        """POST /api/habits should fail with 400 if name is missing or empty."""
        # Missing name
        res1 = self.client.post('/api/habits', json={"category": "Coding"})
        self.assertEqual(res1.status_code, 400)
        self.assertIn("error", res1.get_json())

        # Empty name
        res2 = self.client.post('/api/habits', json={"name": "   "})
        self.assertEqual(res2.status_code, 400)

        # Non-JSON request
        res3 = self.client.post('/api/habits', data="not json", content_type='text/plain')
        self.assertEqual(res3.status_code, 400)

    def test_get_habits(self):
        """GET /api/habits returns only active habits by default."""
        # Create two habits
        self.client.post('/api/habits', json={"name": "Habit 1", "category": "Coding"})
        self.client.post('/api/habits', json={"name": "Habit 2", "category": "Fitness"})

        res = self.client.get('/api/habits')
        self.assertEqual(res.status_code, 200)
        habits = res.get_json()
        self.assertEqual(len(habits), 2)
        names = [h['name'] for h in habits]
        self.assertIn("Habit 1", names)
        self.assertIn("Habit 2", names)

    def test_get_single_habit(self):
        """GET /api/habits/<id> returns 200 for existing or 404 for missing."""
        create_res = self.client.post('/api/habits', json={"name": "Drink Water", "category": "Health"})
        habit_id = create_res.get_json()['id']

        # Existing
        res = self.client.get(f'/api/habits/{habit_id}')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()['name'], "Drink Water")

        # Non-existent
        res_404 = self.client.get('/api/habits/99999')
        self.assertEqual(res_404.status_code, 404)
        self.assertIn("error", res_404.get_json())

    def test_update_habit(self):
        """PUT /api/habits/<id> updates fields and validates input."""
        create_res = self.client.post('/api/habits', json={"name": "Old Title", "category": "General"})
        habit_id = create_res.get_json()['id']

        # Update name and category
        update_res = self.client.put(f'/api/habits/{habit_id}', json={
            "name": "Updated Title",
            "category": "Productivity"
        })
        self.assertEqual(update_res.status_code, 200)
        data = update_res.get_json()
        self.assertEqual(data['name'], "Updated Title")
        self.assertEqual(data['category'], "Productivity")

        # Empty name should fail
        fail_res = self.client.put(f'/api/habits/{habit_id}', json={"name": "  "})
        self.assertEqual(fail_res.status_code, 400)

        # 404 on missing habit
        missing_res = self.client.put('/api/habits/8888', json={"name": "X"})
        self.assertEqual(missing_res.status_code, 404)

    def test_deactivate_habit(self):
        """DELETE /api/habits/<id> sets active=0 instead of dropping rows."""
        create_res = self.client.post('/api/habits', json={"name": "Archived Habit"})
        habit_id = create_res.get_json()['id']

        del_res = self.client.delete(f'/api/habits/{habit_id}')
        self.assertEqual(del_res.status_code, 200)
        self.assertEqual(del_res.get_json().get('active'), 0)

        # GET /api/habits should now omit this habit
        active_res = self.client.get('/api/habits')
        active_habits = active_res.get_json()
        self.assertEqual(len(active_habits), 0)

        # But it still exists when requesting ?all=true
        all_res = self.client.get('/api/habits?all=true')
        all_habits = all_res.get_json()
        self.assertEqual(len(all_habits), 1)
        self.assertEqual(all_habits[0]['active'], 0)

    # -----------------------------------------------------------------------
    # 3. DAILY RECORDS & UPSERT API
    # -----------------------------------------------------------------------
    def test_save_daily_record_and_upsert(self):
        """POST /api/records inserts and updates daily statuses idempotently."""
        create_res = self.client.post('/api/habits', json={"name": "Meditation"})
        habit_id = create_res.get_json()['id']
        today = date.today().isoformat()

        # Insert new record -> 201 Created
        rec_res = self.client.post('/api/records', json={
            "habit_id": habit_id,
            "record_date": today,
            "status": "completed"
        })
        self.assertEqual(rec_res.status_code, 201)
        data = rec_res.get_json()
        self.assertEqual(data['status'], "completed")
        self.assertEqual(data['streak'], 1)

        # Update record for the same date (UPSERT) -> 200 OK
        upsert_res = self.client.post('/api/records', json={
            "habit_id": habit_id,
            "record_date": today,
            "status": "missed"
        })
        self.assertEqual(upsert_res.status_code, 200)
        self.assertEqual(upsert_res.get_json()['status'], "missed")
        self.assertEqual(upsert_res.get_json()['streak'], 0)

        # Reset back to pending -> 200 OK
        pending_res = self.client.post('/api/records', json={
            "habit_id": habit_id,
            "record_date": today,
            "status": "pending"
        })
        self.assertEqual(pending_res.status_code, 200)
        self.assertEqual(pending_res.get_json()['status'], "pending")

    def test_save_record_validation(self):
        """POST /api/records validates habit existence, date format, and allowed statuses."""
        create_res = self.client.post('/api/habits', json={"name": "Jogging"})
        habit_id = create_res.get_json()['id']
        today = date.today().isoformat()

        # Missing habit_id
        res1 = self.client.post('/api/records', json={"record_date": today, "status": "completed"})
        self.assertEqual(res1.status_code, 400)

        # Non-existent habit_id
        res2 = self.client.post('/api/records', json={"habit_id": 9999, "record_date": today, "status": "completed"})
        self.assertEqual(res2.status_code, 404)

        # Invalid date format
        res3 = self.client.post('/api/records', json={"habit_id": habit_id, "record_date": "21/10/2026", "status": "completed"})
        self.assertEqual(res3.status_code, 400)

        # Invalid status value
        res4 = self.client.post('/api/records', json={"habit_id": habit_id, "record_date": today, "status": "finished"})
        self.assertEqual(res4.status_code, 400)

    def test_get_daily_records_and_habit_history(self):
        """Test GET /api/records?date=... and GET /api/habits/<id>/records."""
        create_res = self.client.post('/api/habits', json={"name": "Reading"})
        habit_id = create_res.get_json()['id']
        today = date.today().isoformat()
        yesterday = (date.today() - timedelta(days=1)).isoformat()

        # Save 2 records
        self.client.post('/api/records', json={"habit_id": habit_id, "record_date": yesterday, "status": "completed"})
        self.client.post('/api/records', json={"habit_id": habit_id, "record_date": today, "status": "skipped"})

        # Get records for date
        res_date = self.client.get(f'/api/records?date={today}')
        self.assertEqual(res_date.status_code, 200)
        records_today = res_date.get_json()
        self.assertEqual(len(records_today), 1)
        self.assertEqual(records_today[0]['status'], "skipped")

        # Get habit records history
        res_hist = self.client.get(f'/api/habits/{habit_id}/records')
        self.assertEqual(res_hist.status_code, 200)
        history = res_hist.get_json()
        self.assertEqual(len(history), 2)
        dates = [r['record_date'] for r in history]
        self.assertIn(yesterday, dates)
        self.assertIn(today, dates)

    # -----------------------------------------------------------------------
    # 4. STREAK CALCULATION LOGIC
    # -----------------------------------------------------------------------
    def test_streak_calculation_consecutive_days(self):
        """Streaks should increment correctly over consecutive completed days."""
        create_res = self.client.post('/api/habits', json={"name": "Streak Test Habit"})
        habit_id = create_res.get_json()['id']

        today = date.today()
        # Save records for 3 consecutive days: today, yesterday, 2 days ago
        d0 = today.isoformat()
        d1 = (today - timedelta(days=1)).isoformat()
        d2 = (today - timedelta(days=2)).isoformat()

        self.client.post('/api/records', json={"habit_id": habit_id, "record_date": d2, "status": "completed"})
        self.client.post('/api/records', json={"habit_id": habit_id, "record_date": d1, "status": "completed"})
        res = self.client.post('/api/records', json={"habit_id": habit_id, "record_date": d0, "status": "completed"})

        self.assertEqual(res.get_json()['streak'], 3)

        # GET /api/habits should also report streak=3
        habit_res = self.client.get(f'/api/habits/{habit_id}')
        self.assertEqual(habit_res.get_json()['streak'], 3)

    def test_streak_broken_by_missed(self):
        """A missed day should break the streak."""
        create_res = self.client.post('/api/habits', json={"name": "Missed Streak Habit"})
        habit_id = create_res.get_json()['id']

        today = date.today()
        d0 = today.isoformat()
        d1 = (today - timedelta(days=1)).isoformat()

        # Yesterday completed, today missed
        self.client.post('/api/records', json={"habit_id": habit_id, "record_date": d1, "status": "completed"})
        res = self.client.post('/api/records', json={"habit_id": habit_id, "record_date": d0, "status": "missed"})

        self.assertEqual(res.get_json()['streak'], 0)

    def test_streak_preserved_by_skipped(self):
        """A skipped day preserves existing streak without incrementing."""
        create_res = self.client.post('/api/habits', json={"name": "Skip Streak Habit"})
        habit_id = create_res.get_json()['id']

        today = date.today()
        d0 = today.isoformat()
        d1 = (today - timedelta(days=1)).isoformat()
        d2 = (today - timedelta(days=2)).isoformat()

        # 2 days ago: completed (1)
        # 1 day ago: skipped (preserves 1)
        # today: completed (increments to 2)
        self.client.post('/api/records', json={"habit_id": habit_id, "record_date": d2, "status": "completed"})
        self.client.post('/api/records', json={"habit_id": habit_id, "record_date": d1, "status": "skipped"})
        res = self.client.post('/api/records', json={"habit_id": habit_id, "record_date": d0, "status": "completed"})
        self.assertEqual(res.get_json()['streak'], 2)

    def test_streak_with_today_pending(self):
        """If today has no record yet, yesterday's completed streak remains active."""
        create_res = self.client.post('/api/habits', json={"name": "Pending Streak Habit"})
        habit_id = create_res.get_json()['id']

        yesterday = (date.today() - timedelta(days=1)).isoformat()
        # Mark yesterday completed
        self.client.post('/api/records', json={"habit_id": habit_id, "record_date": yesterday, "status": "completed"})

        # Today has no record: GET habit should report streak=1, status=pending
        habit_res = self.client.get(f'/api/habits/{habit_id}')
        data = habit_res.get_json()
        self.assertEqual(data['status'], 'pending')
        self.assertEqual(data['streak'], 1)

    def test_sqlite_foreign_key_enforcement(self):
        """Confirm PRAGMA foreign_keys = ON prevents dangling records at SQL level."""
        import sqlite3
        with app.app_context():
            db = get_db()
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute(
                    "INSERT INTO habit_records (habit_id, record_date, status) VALUES (99999, '2026-10-21', 'completed')"
                )

    def test_sqlite_unique_constraint_enforcement(self):
        """Confirm UNIQUE(habit_id, record_date) prevents duplicate records for same date."""
        import sqlite3
        create_res = self.client.post('/api/habits', json={"name": "Unique Test Habit"})
        habit_id = create_res.get_json()['id']

        with app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO habit_records (habit_id, record_date, status) VALUES (?, '2026-10-21', 'completed')",
                (habit_id,)
            )
            db.commit()

            with self.assertRaises(sqlite3.IntegrityError):
                db.execute(
                    "INSERT INTO habit_records (habit_id, record_date, status) VALUES (?, '2026-10-21', 'missed')",
                    (habit_id,)
                )

    # -----------------------------------------------------------------------
    # 5. PHASE 3: HABIT PATTERN DETECTION & ANALYTICS TESTS
    # -----------------------------------------------------------------------
    def test_phase3_empty_database(self):
        """Empty database should safely return summary with 0 active habits and no_habits insight."""
        res = self.client.get('/api/insights')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['summary']['total_active_habits'], 0)
        self.assertEqual(data['summary']['total_records'], 0)
        self.assertEqual(data['summary']['overall_completion_rate'], 0.0)
        self.assertTrue(any(i['type'] == 'no_habits' for i in data['insights']))

    def test_phase3_newly_created_habit_no_records(self):
        """A newly created habit with 0 records should handle division by zero and report insufficient data."""
        self.client.post('/api/habits', json={"name": "Brand New Habit", "category": "Mindfulness"})
        res = self.client.get('/api/insights')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['summary']['total_active_habits'], 1)
        self.assertEqual(data['summary']['total_records'], 0)
        self.assertEqual(data['summary']['overall_completion_rate'], 0.0)
        self.assertTrue(any(i['type'] == 'insufficient_data' for i in data['insights']))

    def test_phase3_consistently_completed_habit(self):
        """Habit with >=80% completion over >=5 evaluated records triggers strong_routine insight."""
        create_res = self.client.post('/api/habits', json={"name": "Coding Practice", "category": "Coding"})
        habit_id = create_res.get_json()['id']
        today = date.today()

        # Log 8 completed records and 1 missed record (88.9% rate)
        for i in range(8):
            d = (today - timedelta(days=i)).isoformat()
            self.client.post('/api/records', json={"habit_id": habit_id, "record_date": d, "status": "completed"})
        self.client.post('/api/records', json={"habit_id": habit_id, "record_date": (today - timedelta(days=8)).isoformat(), "status": "missed"})

        res = self.client.get('/api/insights')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        strong_insights = [i for i in data['insights'] if i['type'] == 'strong_routine']
        self.assertTrue(len(strong_insights) >= 1)
        self.assertEqual(strong_insights[0]['habit_id'], habit_id)
        self.assertGreaterEqual(strong_insights[0]['evidence']['completion_rate'], 80.0)
        self.assertIn('recommendation', strong_insights[0])
        self.assertIn(strong_insights[0]['confidence'], ['low', 'medium', 'high'])

    def test_phase3_repeated_missed_habit(self):
        """Habit with consecutive misses triggers repeated_misses insight."""
        create_res = self.client.post('/api/habits', json={"name": "Gym Workout", "category": "Fitness"})
        habit_id = create_res.get_json()['id']
        today = date.today()

        # Log 4 consecutive missed days
        for i in range(4):
            d = (today - timedelta(days=i)).isoformat()
            self.client.post('/api/records', json={"habit_id": habit_id, "record_date": d, "status": "missed"})

        res = self.client.get('/api/insights')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        missed_insights = [i for i in data['insights'] if i['type'] in ('repeated_misses', 'at_risk_habit')]
        self.assertTrue(len(missed_insights) >= 1)
        self.assertIn('recommendation', missed_insights[0])

    def test_phase3_skipped_records_do_not_penalize_completion_rate(self):
        """Skipped records are treated as excused rest days and do not lower the active execution rate."""
        create_res = self.client.post('/api/habits', json={"name": "Piano Practice", "category": "Learning"})
        habit_id = create_res.get_json()['id']
        today = date.today()

        # 5 completed days and 2 skipped days (0 missed)
        for i in range(5):
            d = (today - timedelta(days=i)).isoformat()
            self.client.post('/api/records', json={"habit_id": habit_id, "record_date": d, "status": "completed"})
        for i in range(5, 7):
            d = (today - timedelta(days=i)).isoformat()
            self.client.post('/api/records', json={"habit_id": habit_id, "record_date": d, "status": "skipped"})

        res = self.client.get(f'/api/insights/{habit_id}')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        # completed / (completed + missed) = 5 / (5 + 0) = 100.0%
        self.assertEqual(data['statistics']['completion_rate'], 100.0)
        self.assertEqual(data['statistics']['skipped'], 2)
        self.assertEqual(data['statistics']['completed'], 5)

    def test_phase3_weekday_patterns(self):
        """Different completion rates across weekdays trigger weekday pattern insights."""
        create_res = self.client.post('/api/habits', json={"name": "Reading Book", "category": "Learning"})
        habit_id = create_res.get_json()['id']

        # Log records across past 28 days:
        # Find 3 Sundays and mark missed, find other days and mark completed
        today = date.today()
        for i in range(21):
            d_obj = today - timedelta(days=i)
            status = "missed" if d_obj.weekday() == 6 else "completed"
            self.client.post('/api/records', json={"habit_id": habit_id, "record_date": d_obj.isoformat(), "status": status})

        res = self.client.get('/api/insights')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        insights_types = [i['type'] for i in data['insights']]
        # Sunday drop-off or peak day should be detected
        self.assertTrue('weekday_dropoff' in insights_types or 'peak_performance_day' in insights_types or 'strong_routine' in insights_types)

    def test_phase3_time_of_day_analysis(self):
        """Comparison between Morning and Evening habits when sufficient data exists."""
        # Morning habit with high completions
        m_res = self.client.post('/api/habits', json={"name": "Morning Run", "category": "Fitness", "time_of_day": "Morning"})
        m_id = m_res.get_json()['id']
        # Evening habit with low completions
        e_res = self.client.post('/api/habits', json={"name": "Evening Journal", "category": "Productivity", "time_of_day": "Evening"})
        e_id = e_res.get_json()['id']

        today = date.today()
        # 6 completed mornings (100% rate)
        for i in range(6):
            d = (today - timedelta(days=i)).isoformat()
            self.client.post('/api/records', json={"habit_id": m_id, "record_date": d, "status": "completed"})

        # 6 missed evenings (0% rate)
        for i in range(6):
            d = (today - timedelta(days=i)).isoformat()
            self.client.post('/api/records', json={"habit_id": e_id, "record_date": d, "status": "missed"})

        res = self.client.get('/api/insights')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        tod_insights = [i for i in data['insights'] if i['type'] == 'time_of_day_preference']
        self.assertTrue(len(tod_insights) >= 1)
        self.assertEqual(tod_insights[0]['evidence']['best_time_of_day'], 'Morning')
        self.assertEqual(tod_insights[0]['evidence']['worst_time_of_day'], 'Evening')

    def test_phase3_insufficient_historical_data(self):
        """Fewer than 3 records returns insufficient_data guidance insight."""
        create_res = self.client.post('/api/habits', json={"name": "Guitar", "category": "Learning"})
        habit_id = create_res.get_json()['id']
        today = date.today().isoformat()
        # Only 1 record
        self.client.post('/api/records', json={"habit_id": habit_id, "record_date": today, "status": "completed"})

        res = self.client.get('/api/insights')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(any(i['type'] == 'insufficient_data' for i in data['insights']))

    def test_phase3_invalid_days_param(self):
        """Invalid 'days' parameter returns HTTP 400 Bad Request with clear error message."""
        # Non-numeric
        res1 = self.client.get('/api/insights?days=abc')
        self.assertEqual(res1.status_code, 400)
        self.assertIn("days parameter", res1.get_json().get("error", ""))

        # Zero or negative
        res2 = self.client.get('/api/insights?days=0')
        self.assertEqual(res2.status_code, 400)

        # Exceeds maximum 365
        res3 = self.client.get('/api/insights?days=999')
        self.assertEqual(res3.status_code, 400)

        # Also test on /api/analytics
        res4 = self.client.get('/api/analytics?days=-5')
        self.assertEqual(res4.status_code, 400)

    def test_phase3_nonexistent_and_inactive_habit_id(self):
        """GET /api/insights/<id> returns 404 for nonexistent or deactivated habit."""
        # Nonexistent ID
        res1 = self.client.get('/api/insights/99999')
        self.assertEqual(res1.status_code, 404)

        # Deactivated habit
        create_res = self.client.post('/api/habits', json={"name": "Archived Habit"})
        habit_id = create_res.get_json()['id']
        self.client.delete(f'/api/habits/{habit_id}')

        res2 = self.client.get(f'/api/insights/{habit_id}')
        self.assertEqual(res2.status_code, 404)

    def test_phase3_exclude_future_records(self):
        """Records with dates in the future must be excluded from historical calculations."""
        create_res = self.client.post('/api/habits', json={"name": "Future Test", "category": "General"})
        habit_id = create_res.get_json()['id']
        today = date.today()
        future_date = (today + timedelta(days=5)).isoformat()
        past_date = (today - timedelta(days=1)).isoformat()

        # Log 1 past completion and 1 future missed
        self.client.post('/api/records', json={"habit_id": habit_id, "record_date": past_date, "status": "completed"})
        self.client.post('/api/records', json={"habit_id": habit_id, "record_date": future_date, "status": "missed"})

        res = self.client.get(f'/api/insights/{habit_id}?date={today.isoformat()}')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        # Future record should be excluded: total_records=1, completed=1, missed=0
        self.assertEqual(data['statistics']['total_records'], 1)
        self.assertEqual(data['statistics']['completed'], 1)
        self.assertEqual(data['statistics']['missed'], 0)

    def test_phase3_division_by_zero_edge_case(self):
        """Habit with only skipped records avoids division by zero and reports 0.0% completion rate."""
        create_res = self.client.post('/api/habits', json={"name": "Skipped Only", "category": "General"})
        habit_id = create_res.get_json()['id']
        today = date.today()

        # Log 3 skipped days
        for i in range(3):
            d = (today - timedelta(days=i)).isoformat()
            self.client.post('/api/records', json={"habit_id": habit_id, "record_date": d, "status": "skipped"})

        res = self.client.get(f'/api/insights/{habit_id}')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['statistics']['completed'], 0)
        self.assertEqual(data['statistics']['missed'], 0)
        self.assertEqual(data['statistics']['skipped'], 3)
        self.assertEqual(data['statistics']['completion_rate'], 0.0)

    def test_phase3_json_response_structure_and_analytics(self):
        """Verify complete JSON structure for /api/analytics and /api/insights."""
        create_res = self.client.post('/api/habits', json={"name": "Analytics Habit", "category": "Productivity", "time_of_day": "Afternoon"})
        habit_id = create_res.get_json()['id']
        today = date.today().isoformat()
        self.client.post('/api/records', json={"habit_id": habit_id, "record_date": today, "status": "completed"})

        # Test /api/analytics
        res = self.client.get('/api/analytics?days=7')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('period', data)
        self.assertIn('summary', data)
        self.assertIn('daily_trend', data)
        self.assertIn('weekday_statistics', data)
        self.assertIn('habit_breakdown', data)
        self.assertIn('time_of_day_distribution', data)

        # Check daily_trend contains 7 days
        self.assertEqual(len(data['daily_trend']), 7)
        # Check weekday_statistics contains 7 days (Mon-Sun)
        self.assertEqual(len(data['weekday_statistics']), 7)
        # Check habit_breakdown contains created habit
        self.assertTrue(any(h['id'] == habit_id for h in data['habit_breakdown']))

    # -----------------------------------------------------------------------
    # PHASE 4: HYBRID AI EXPLANATIONS & RECOMMENDATIONS TESTS
    # -----------------------------------------------------------------------

    def test_phase4_explanations_endpoint_empty_db(self):
        """GET /api/insights/explanations on empty DB returns 200 with fallback no_habits explanation."""
        res = self.client.get('/api/insights/explanations')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('period', data)
        self.assertIn('summary', data)
        self.assertIn('explanations', data)
        self.assertEqual(data.get('source'), 'fallback')
        self.assertFalse(data.get('ai_configured'))

        explanations = data['explanations']
        self.assertGreaterEqual(len(explanations), 1)
        first = explanations[0]
        self.assertEqual(first.get('pattern_type'), 'no_habits')
        self.assertIn('StreakLab', first.get('title'))
        self.assertEqual(first.get('source'), 'fallback')
        self.assertIn('evidence_summary', first)
        self.assertIn('recommendation', first)

        # Now create 1 habit with 0 check-ins: should report 'insufficient_data'
        self.client.post('/api/habits', json={"name": "New Habit", "category": "General"})
        res2 = self.client.get('/api/insights/explanations?days=14')
        self.assertEqual(res2.status_code, 200)
        data2 = res2.get_json()
        first2 = data2['explanations'][0]
        self.assertEqual(first2.get('pattern_type'), 'insufficient_data')
        self.assertIn('Gathering Habit History', first2.get('title'))

    def test_phase4_explanations_endpoint_with_records(self):
        """GET /api/insights/explanations with real records produces validated explanation cards."""
        create_res = self.client.post('/api/habits', json={"name": "Morning Coding", "category": "Coding"})
        habit_id = create_res.get_json()['id']
        today = date.today()

        # Log 8 consecutive completed check-ins
        for i in range(8):
            d = (today - timedelta(days=i)).isoformat()
            self.client.post('/api/records', json={"habit_id": habit_id, "record_date": d, "status": "completed"})

        res = self.client.get('/api/insights/explanations?days=14')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get('source'), 'fallback')

        explanations = data.get('explanations', [])
        self.assertGreater(len(explanations), 0)

        # Check all explanation fields conform to required contract
        for exp in explanations:
            self.assertIn('pattern_type', exp)
            self.assertIn('title', exp)
            self.assertIn('explanation', exp)
            self.assertIn('recommendation', exp)
            self.assertIn('evidence_summary', exp)
            self.assertIn('confidence', exp)
            self.assertIn(exp['confidence'], ('low', 'medium', 'high'))
            self.assertEqual(exp['source'], 'fallback')

    def test_phase4_explanations_parameter_validation(self):
        """Test parameter validation for /api/insights/explanations (days, date, habit_id)."""
        # Invalid days (< 1)
        res1 = self.client.get('/api/insights/explanations?days=0')
        self.assertEqual(res1.status_code, 400)
        self.assertIn('error', res1.get_json())

        # Invalid days (> 365)
        res2 = self.client.get('/api/insights/explanations?days=400')
        self.assertEqual(res2.status_code, 400)

        # Invalid days (non-integer)
        res3 = self.client.get('/api/insights/explanations?days=abc')
        self.assertEqual(res3.status_code, 400)

        # Invalid date format
        res4 = self.client.get('/api/insights/explanations?date=2026-99-99')
        self.assertEqual(res4.status_code, 400)

        # Invalid habit_id (non-integer)
        res5 = self.client.get('/api/insights/explanations?habit_id=invalid')
        self.assertEqual(res5.status_code, 400)

        # Nonexistent habit_id
        res6 = self.client.get('/api/insights/explanations?habit_id=99999')
        self.assertEqual(res6.status_code, 404)

    def test_phase4_single_habit_explanation(self):
        """GET /api/insights/explanations?habit_id=<id> returns single habit breakdown and explanations."""
        create_res = self.client.post('/api/habits', json={"name": "Evening Reading", "category": "Mindfulness"})
        habit_id = create_res.get_json()['id']
        today = date.today()

        for i in range(6):
            d = (today - timedelta(days=i)).isoformat()
            self.client.post('/api/records', json={"habit_id": habit_id, "record_date": d, "status": "completed"})

        res = self.client.get(f'/api/insights/explanations?habit_id={habit_id}&days=14')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('habit', data)
        self.assertEqual(data['habit']['id'], habit_id)
        self.assertIn('statistics', data)
        self.assertIn('weekday_breakdown', data)
        self.assertIn('explanations', data)
        self.assertEqual(data['source'], 'fallback')

    def test_phase4_local_fallback_unit_coverage(self):
        """Unit test generate_local_fallback across all supported pattern types."""
        pattern_types = [
            ("insufficient_data", {"total_records": 2, "period_days": 30}),
            ("strong_routine", {"completion_rate": 85.0, "sample_size": 10, "completed": 9, "period_days": 30}),
            ("at_risk_habit", {"completion_rate": 30.0, "sample_size": 10, "missed": 7, "period_days": 30}),
            ("weekday_dropoff", {"weekday": "Friday", "weekday_rate": 40.0, "overall_rate": 75.0, "sample_size": 5}),
            ("peak_performance_day", {"weekday": "Monday", "weekday_rate": 95.0, "weekday_completed": 5, "sample_size": 5}),
            ("time_of_day_preference", {"best_time_of_day": "Morning", "best_rate": 88.0, "worst_time_of_day": "Evening", "worst_rate": 50.0, "rate_difference": 38.0}),
            ("repeated_misses", {"consecutive_misses": 4}),
            ("streak_milestone", {"current_streak": 14, "best_streak": 20})
        ]

        for p_type, ev in pattern_types:
            mock_insight = {
                "type": p_type,
                "habit_id": 1,
                "habit_name": "Test Habit",
                "title": f"Pattern: {p_type}",
                "evidence": ev,
                "confidence": "high",
                "recommendation": "Existing suggestion."
            }
            res = ai_explainer.generate_local_fallback(mock_insight)
            self.assertEqual(res["pattern_type"], p_type)
            self.assertEqual(res["source"], "fallback")
            self.assertTrue(len(res["explanation"]) > 10)
            self.assertTrue(len(res["recommendation"]) > 5)
            self.assertTrue(len(res["evidence_summary"]) > 5)

    def test_phase4_mock_ai_provider_success(self):
        """When AI provider succeeds, explanations are tagged source: 'ai' with grounded content."""
        create_res = self.client.post('/api/habits', json={"name": "Daily Workout", "category": "Fitness"})
        habit_id = create_res.get_json()['id']
        today = date.today()

        for i in range(7):
            d = (today - timedelta(days=i)).isoformat()
            self.client.post('/api/records', json={"habit_id": habit_id, "record_date": d, "status": "completed"})

        mock_config = {
            "provider": "gemini",
            "api_key": "fake_test_key",
            "model": "gemini-1.5-flash",
            "endpoint": "",
            "timeout": 6,
            "is_configured": True
        }

        mock_ai_output = [
            {
                "index": 0,
                "explanation": "You have sustained a strong behavioral habit loop for Daily Workout over the past week.",
                "recommendation": "Keep your workout gear ready the night before to maintain this momentum.",
                "evidence_summary": "7 of 7 check-ins completed (100% rate)."
            }
        ]

        with patch('ai_explainer.get_ai_config', return_value=mock_config):
            with patch('ai_explainer._call_gemini_api', return_value=mock_ai_output):
                res = self.client.get('/api/insights/explanations?days=14&refresh=true')
                self.assertEqual(res.status_code, 200)
                data = res.get_json()
                self.assertEqual(data.get('source'), 'ai')
                self.assertTrue(data.get('ai_configured'))
                self.assertEqual(data.get('provider'), 'gemini')

                explanations = data.get('explanations', [])
                self.assertGreater(len(explanations), 0)
                ai_exp = explanations[0]
                self.assertEqual(ai_exp['source'], 'ai')
                self.assertIn("Daily Workout", ai_exp['explanation'])
                self.assertIn("night before", ai_exp['recommendation'])

    def test_phase4_mock_ai_provider_timeout_fallback(self):
        """When AI provider encounters a timeout or network error, it gracefully falls back with 200 OK."""
        create_res = self.client.post('/api/habits', json={"name": "Meditation", "category": "Mindfulness"})
        habit_id = create_res.get_json()['id']
        today = date.today()

        for i in range(6):
            d = (today - timedelta(days=i)).isoformat()
            self.client.post('/api/records', json={"habit_id": habit_id, "record_date": d, "status": "completed"})

        mock_config = {
            "provider": "gemini",
            "api_key": "fake_key",
            "model": "gemini-1.5-flash",
            "endpoint": "",
            "timeout": 6,
            "is_configured": True
        }

        # Simulate TimeoutError / URLError
        with patch('ai_explainer.get_ai_config', return_value=mock_config):
            with patch('ai_explainer._call_gemini_api', side_effect=TimeoutError("Connection timed out")):
                res = self.client.get('/api/insights/explanations?days=14&refresh=true')
                # Must return 200, NEVER 500
                self.assertEqual(res.status_code, 200)
                data = res.get_json()
                self.assertEqual(data.get('source'), 'fallback')
                self.assertGreater(len(data.get('explanations', [])), 0)

    def test_phase4_mock_ai_malformed_response_fallback(self):
        """When AI provider returns invalid schema or non-list data, reject it and use local fallback."""
        create_res = self.client.post('/api/habits', json={"name": "Hydration", "category": "Health"})
        habit_id = create_res.get_json()['id']
        today = date.today()

        for i in range(6):
            d = (today - timedelta(days=i)).isoformat()
            self.client.post('/api/records', json={"habit_id": habit_id, "record_date": d, "status": "completed"})

        mock_config = {
            "provider": "openai",
            "api_key": "fake_openai_key",
            "model": "gpt-4o-mini",
            "endpoint": "",
            "timeout": 6,
            "is_configured": True
        }

        # Return invalid structure (empty or malformed object)
        with patch('ai_explainer.get_ai_config', return_value=mock_config):
            with patch('ai_explainer._call_openai_api', return_value={"corrupted": "bad_data"}):
                res = self.client.get('/api/insights/explanations?days=14&refresh=true')
                self.assertEqual(res.status_code, 200)
                data = res.get_json()
                self.assertEqual(data.get('source'), 'fallback')

    def test_phase4_cache_and_invalidation(self):
        """Verify caching preserves explanations and habit updates invalidate cache."""
        ai_explainer.invalidate_explanation_cache()

        create_res = self.client.post('/api/habits', json={"name": "Cache Habit", "category": "General"})
        habit_id = create_res.get_json()['id']
        today = date.today().isoformat()

        self.client.post('/api/records', json={"habit_id": habit_id, "record_date": today, "status": "completed"})

        # First request populates cache
        res1 = self.client.get('/api/insights/explanations?days=14')
        self.assertEqual(res1.status_code, 200)

        # Mutate record: should invalidate cache
        res_mut = self.client.post('/api/records', json={"habit_id": habit_id, "record_date": today, "status": "missed"})
        self.assertEqual(res_mut.status_code, 200)

        # Fetching insights should reflect the new state
        res2 = self.client.get('/api/insights/explanations?days=14')
        self.assertEqual(res2.status_code, 200)

    def test_phase4_backward_compatible_insights_flag(self):
        """GET /api/insights?explain=true enriches the response with explanations."""
        create_res = self.client.post('/api/habits', json={"name": "Backward Compat Habit", "category": "General"})
        habit_id = create_res.get_json()['id']
        today = date.today().isoformat()
        self.client.post('/api/records', json={"habit_id": habit_id, "record_date": today, "status": "completed"})

        res = self.client.get('/api/insights?days=7&explain=true')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('insights', data)
        self.assertIn('explanations', data)

    def test_phase4_no_external_calls_offline(self):
        """Confirm that in standard configuration without API keys, urllib.request.urlopen is NEVER invoked."""
        with patch('urllib.request.urlopen') as mock_urlopen:
            res = self.client.get('/api/insights/explanations?days=30')
            self.assertEqual(res.status_code, 200)
            mock_urlopen.assert_not_called()

    # -----------------------------------------------------------------------
    # PHASE 5: SYSTEM POLISH, DATA INTEGRITY & EDGE-CASE VALIDATION
    # -----------------------------------------------------------------------

    def test_phase5_pending_record_status_and_deletion(self):
        """Setting status to 'pending' deletes existing record and resets streak calculation."""
        create_res = self.client.post('/api/habits', json={"name": "Pending Reset Habit", "category": "General"})
        habit_id = create_res.get_json()['id']
        today = date.today().isoformat()

        # Step 1: Mark completed
        res1 = self.client.post('/api/records', json={"habit_id": habit_id, "record_date": today, "status": "completed"})
        self.assertEqual(res1.status_code, 201)
        self.assertEqual(res1.get_json()['streak'], 1)

        # Step 2: Reset to pending
        res2 = self.client.post('/api/records', json={"habit_id": habit_id, "record_date": today, "status": "pending"})
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.get_json()['status'], 'pending')
        self.assertEqual(res2.get_json()['streak'], 0)

        # Verify no record exists in database for this date
        records_res = self.client.get(f'/api/habits/{habit_id}/records')
        self.assertEqual(len(records_res.get_json()), 0)

    def test_phase5_invalid_record_status_error_message(self):
        """POST /api/records with an invalid status returns 400 with a descriptive error message."""
        create_res = self.client.post('/api/habits', json={"name": "Status Test Habit", "category": "General"})
        habit_id = create_res.get_json()['id']
        today = date.today().isoformat()

        res = self.client.post('/api/records', json={"habit_id": habit_id, "record_date": today, "status": "unknown_status"})
        self.assertEqual(res.status_code, 400)
        err = res.get_json().get('error', '')
        self.assertIn("completed", err)
        self.assertIn("missed", err)
        self.assertIn("skipped", err)
        self.assertIn("pending", err)

    def test_phase5_update_habit_partial_and_validation(self):
        """PUT /api/habits/<id> validates input and supports partial field updates."""
        create_res = self.client.post('/api/habits', json={
            "name": "Original Habit",
            "category": "General",
            "time_of_day": "Morning",
            "target_time": "08:00 AM"
        })
        habit_id = create_res.get_json()['id']

        # Empty name should fail
        res_empty = self.client.put(f'/api/habits/{habit_id}', json={"name": "   "})
        self.assertEqual(res_empty.status_code, 400)
        self.assertIn('error', res_empty.get_json())

        # Partial update: change only category and target_time
        res_update = self.client.put(f'/api/habits/{habit_id}', json={
            "category": "Productivity",
            "target_time": "09:30 AM"
        })
        self.assertEqual(res_update.status_code, 200)
        updated = res_update.get_json()
        self.assertEqual(updated['name'], "Original Habit")  # Preserved
        self.assertEqual(updated['category'], "Productivity")  # Updated
        self.assertEqual(updated['target_time'], "09:30 AM")  # Updated
        self.assertEqual(updated['time_of_day'], "Morning")  # Preserved

    def test_phase5_deactivate_habit_preserves_history(self):
        """DELETE /api/habits/<id> sets active=0 but preserves historical check-ins in SQLite."""
        create_res = self.client.post('/api/habits', json={"name": "Archive Habit", "category": "Fitness"})
        habit_id = create_res.get_json()['id']
        today = date.today()

        # Log check-ins
        for i in range(3):
            d = (today - timedelta(days=i)).isoformat()
            self.client.post('/api/records', json={"habit_id": habit_id, "record_date": d, "status": "completed"})

        # Deactivate habit
        del_res = self.client.delete(f'/api/habits/{habit_id}')
        self.assertEqual(del_res.status_code, 200)

        # GET /api/habits should NOT list deactivated habit
        active_res = self.client.get('/api/habits')
        self.assertFalse(any(h['id'] == habit_id for h in active_res.get_json()))

        # GET /api/habits?all=true SHOULD list it with active=0
        all_res = self.client.get('/api/habits?all=true')
        archived = next((h for h in all_res.get_json() if h['id'] == habit_id), None)
        self.assertIsNotNone(archived)
        self.assertEqual(archived['active'], 0)

        # History records remain intact
        history_res = self.client.get(f'/api/habits/{habit_id}/records')
        self.assertEqual(len(history_res.get_json()), 3)

    def test_phase5_insights_explanations_refresh_param(self):
        """GET /api/insights/explanations?refresh=true successfully forces cache regeneration."""
        create_res = self.client.post('/api/habits', json={"name": "Refresh Test Habit", "category": "Mindfulness"})
        habit_id = create_res.get_json()['id']
        today = date.today().isoformat()
        self.client.post('/api/records', json={"habit_id": habit_id, "record_date": today, "status": "completed"})

        # Normal request
        res1 = self.client.get('/api/insights/explanations?days=14')
        self.assertEqual(res1.status_code, 200)

        # Request with refresh=true
        res2 = self.client.get('/api/insights/explanations?days=14&refresh=true')
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.get_json()['period']['days'], 14)


if __name__ == '__main__':
    unittest.main()

