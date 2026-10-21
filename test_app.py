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
from app import app, init_db, get_db


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


if __name__ == '__main__':
    unittest.main()
