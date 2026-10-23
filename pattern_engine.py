"""
=============================================================================
StreakLab — Habit Pattern Detection Engine
Module: pattern_engine.py

Phase 3: Rule-Based Statistical Pattern Detection
- Analyzes actual SQLite records over a configurable time window (default 30 days)
- Computes habit consistency, active completion rates, and streak records
- Analyzes weekday drop-offs, peak consistency days, and time-of-day variations
- Detects repeated missed habits vs isolated misses (preserving skipped rest days)
- Excludes future records, guards against division-by-zero, and handles empty datasets
- Generates structured, deterministic insights with evidence, confidence, and advice
=============================================================================
"""

import calendar
from datetime import datetime, timedelta, date, timezone


# ---------------------------------------------------------------------------
# DATE & STREAK ANALYSIS HELPERS
# ---------------------------------------------------------------------------

def parse_target_date(target_date_str=None):
    """Parses a YYYY-MM-DD date string or defaults to local today."""
    if not target_date_str:
        return date.today()
    try:
        return datetime.strptime(target_date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return date.today()


def calculate_best_streak(habit_id, target_date=None, db=None):
    """
    Calculates the all-time best (longest) streak of consecutive completed days
    for a habit up to target_date.

    Streak rules:
    - Only 'completed' days increment the streak counter.
    - 'skipped' days act as excused pauses: they preserve the current streak without incrementing it.
    - 'missed' days or unrecorded calendar days break the streak and reset the counter.
    - Excludes records with dates greater than target_date.
    """
    if target_date is None:
        target_date = date.today()
    elif isinstance(target_date, str):
        target_date = parse_target_date(target_date)

    cursor = db.execute(
        """
        SELECT record_date, status
        FROM habit_records
        WHERE habit_id = ? AND record_date <= ?
        ORDER BY record_date ASC
        """,
        (habit_id, target_date.isoformat())
    )
    records = cursor.fetchall()
    if not records:
        return 0

    record_dict = {row["record_date"]: row["status"] for row in records}
    # Sort distinct dates
    sorted_dates = sorted([datetime.strptime(d, "%Y-%m-%d").date() for d in record_dict.keys()])
    if not sorted_dates:
        return 0

    best_streak = 0
    current_streak = 0
    last_date = None

    for curr_date in sorted_dates:
        status = record_dict[curr_date.isoformat()]

        if last_date is None:
            if status == "completed":
                current_streak = 1
                best_streak = max(best_streak, current_streak)
                last_date = curr_date
            elif status == "skipped":
                current_streak = 0
                last_date = curr_date
            else:  # missed
                current_streak = 0
                last_date = curr_date
            continue

        day_diff = (curr_date - last_date).days

        if day_diff == 1:
            # Consecutive day
            if status == "completed":
                current_streak += 1
                best_streak = max(best_streak, current_streak)
            elif status == "skipped":
                # Preserves current streak without adding
                pass
            else:  # missed
                current_streak = 0
            last_date = curr_date
        elif day_diff > 1:
            # Calendar gap: unrecorded days break the continuous streak
            if status == "completed":
                current_streak = 1
                best_streak = max(best_streak, current_streak)
            else:
                current_streak = 0
            last_date = curr_date

    return best_streak


# ---------------------------------------------------------------------------
# STATISTICAL CALCULATIONS FOR A SINGLE HABIT
# ---------------------------------------------------------------------------

def calculate_habit_statistics(habit_id, start_date, end_date, db):
    """
    Computes completion stats for a specific habit within [start_date, end_date].
    Defines:
      - completed: count of 'completed' records
      - missed: count of 'missed' records
      - skipped: count of 'skipped' records (excused rest days)
      - total_evaluated: completed + missed (actionable execution days)
      - completion_rate: (completed / total_evaluated) * 100 if total_evaluated > 0 else 0.0
      - total_records: completed + missed + skipped
    """
    cursor = db.execute(
        """
        SELECT record_date, status
        FROM habit_records
        WHERE habit_id = ? AND record_date BETWEEN ? AND ?
        ORDER BY record_date ASC
        """,
        (habit_id, start_date.isoformat(), end_date.isoformat())
    )
    records = cursor.fetchall()

    completed = sum(1 for r in records if r["status"] == "completed")
    missed = sum(1 for r in records if r["status"] == "missed")
    skipped = sum(1 for r in records if r["status"] == "skipped")
    total_evaluated = completed + missed
    total_records = len(records)

    completion_rate = round((completed / total_evaluated * 100.0), 1) if total_evaluated > 0 else 0.0

    return {
        "completed": completed,
        "missed": missed,
        "skipped": skipped,
        "total_evaluated": total_evaluated,
        "total_records": total_records,
        "completion_rate": completion_rate,
        "records": records
    }


# ---------------------------------------------------------------------------
# QUALITATIVE CONFIDENCE RATER
# ---------------------------------------------------------------------------

def evaluate_confidence(sample_size, high_threshold=14, medium_threshold=6):
    """
    Returns qualitative confidence level ('low', 'medium', 'high') based on sample size.
    Transparently documented as observation count rather than a statistical p-value.
    """
    if sample_size >= high_threshold:
        return "high"
    elif sample_size >= medium_threshold:
        return "medium"
    return "low"


# ---------------------------------------------------------------------------
# CORE PATTERN DETECTION ENGINE
# ---------------------------------------------------------------------------

def analyze_habit_patterns(days=30, target_date_str=None, db=None):
    """
    Analyzes all active habits over the specified window and generates structured insights.

    Parameters:
      - days: integer number of days to analyze (default 30)
      - target_date_str: end date of window (default today)
      - db: SQLite database connection

    Returns dictionary with:
      - period: analysis window details
      - summary: overall progress stats
      - insights: list of detected insight objects
    """
    end_date = parse_target_date(target_date_str)
    start_date = end_date - timedelta(days=days - 1)

    # 1. Fetch active habits
    cursor = db.execute("SELECT * FROM habits WHERE active = 1 ORDER BY id ASC")
    active_habits = cursor.fetchall()

    # Empty database / no active habits handling
    if not active_habits:
        return {
            "period": {
                "days": days,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "summary": {
                "total_active_habits": 0,
                "total_records": 0,
                "total_completed": 0,
                "total_missed": 0,
                "total_skipped": 0,
                "overall_completion_rate": 0.0,
                "best_overall_streak": 0
            },
            "insights": [
                {
                    "type": "no_habits",
                    "title": "Welcome to StreakLab",
                    "message": "No active habits found. Create your first habit to begin tracking daily routines.",
                    "evidence": {
                        "active_habits": 0,
                        "sample_size": 0,
                        "period_days": days
                    },
                    "confidence": "low",
                    "recommendation": "Click 'Add Habit' above to define your daily routine and start building momentum."
                }
            ]
        }

    # 2. Compute statistics for all active habits
    overall_completed = 0
    overall_missed = 0
    overall_skipped = 0
    overall_total_records = 0
    best_overall_streak = 0

    habit_stats_list = []
    for h in active_habits:
        stats = calculate_habit_statistics(h["id"], start_date, end_date, db)
        best_strk = calculate_best_streak(h["id"], end_date, db)
        best_overall_streak = max(best_overall_streak, best_strk)

        overall_completed += stats["completed"]
        overall_missed += stats["missed"]
        overall_skipped += stats["skipped"]
        overall_total_records += stats["total_records"]

        habit_stats_list.append({
            "habit": h,
            "stats": stats,
            "best_streak": best_strk
        })

    overall_evaluated = overall_completed + overall_missed
    overall_rate = round((overall_completed / overall_evaluated * 100.0), 1) if overall_evaluated > 0 else 0.0

    insights = []

    # Safe handling of insufficient total records across the entire system
    if overall_total_records < 3:
        insights.append({
            "type": "insufficient_data",
            "title": "Gathering Habit History",
            "message": f"StreakLab has recorded {overall_total_records} habit entries so far. The pattern engine requires at least 3-5 daily check-ins to detect trends.",
            "evidence": {
                "total_records": overall_total_records,
                "sample_size": overall_total_records,
                "period_days": days,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "confidence": "low",
            "recommendation": "Mark your habits as completed, missed, or skipped for a few consecutive days to unlock pattern detection."
        })
        return {
            "period": {
                "days": days,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "summary": {
                "total_active_habits": len(active_habits),
                "total_records": overall_total_records,
                "total_completed": overall_completed,
                "total_missed": overall_missed,
                "total_skipped": overall_skipped,
                "overall_completion_rate": overall_rate,
                "best_overall_streak": best_overall_streak
            },
            "insights": insights
        }

    # -----------------------------------------------------------------------
    # PATTERN A: HABIT CONSISTENCY (HIGH & LOW PERFORMERS)
    # -----------------------------------------------------------------------
    for item in habit_stats_list:
        h = item["habit"]
        st = item["stats"]
        name = h["name"]

        # Minimum 5 evaluated days required to report strong consistency
        if st["total_evaluated"] >= 5 and st["completion_rate"] >= 80.0:
            conf = evaluate_confidence(st["total_evaluated"], high_threshold=14, medium_threshold=7)
            insights.append({
                "type": "strong_routine",
                "habit_id": h["id"],
                "habit_name": name,
                "title": f"Strong Routine: {name}",
                "message": f"'{name}' has an exceptional {st['completion_rate']}% completion rate across {st['total_evaluated']} evaluated check-ins in the past {days} days.",
                "evidence": {
                    "completed": st["completed"],
                    "missed": st["missed"],
                    "skipped": st["skipped"],
                    "completion_rate": st["completion_rate"],
                    "sample_size": st["total_evaluated"],
                    "period_days": days
                },
                "confidence": conf,
                "recommendation": "This habit is well-established. Consider keeping it as an anchor routine or stacking a new habit onto it."
            })
        elif st["total_evaluated"] >= 5 and st["completion_rate"] < 50.0:
            conf = evaluate_confidence(st["total_evaluated"], high_threshold=14, medium_threshold=7)
            insights.append({
                "type": "at_risk_habit",
                "habit_id": h["id"],
                "habit_name": name,
                "title": f"At-Risk Habit: {name}",
                "message": f"'{name}' has a low completion rate of {st['completion_rate']}% ({st['missed']} missed out of {st['total_evaluated']} active days).",
                "evidence": {
                    "completed": st["completed"],
                    "missed": st["missed"],
                    "skipped": st["skipped"],
                    "completion_rate": st["completion_rate"],
                    "sample_size": st["total_evaluated"],
                    "period_days": days
                },
                "confidence": conf,
                "recommendation": "Lower the friction: try reducing the target duration or shifting the scheduled time to make execution easier."
            })

    # -----------------------------------------------------------------------
    # PATTERN B: DAY-OF-WEEK PATTERNS (WEEKDAY DROP-OFF & PEAK DAYS)
    # -----------------------------------------------------------------------
    weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekday_data = {i: {"completed": 0, "missed": 0, "skipped": 0} for i in range(7)}

    # Fetch all records across all active habits in the window
    all_records_cursor = db.execute(
        """
        SELECT r.record_date, r.status
        FROM habit_records r
        JOIN habits h ON r.habit_id = h.id
        WHERE h.active = 1 AND r.record_date BETWEEN ? AND ?
        """,
        (start_date.isoformat(), end_date.isoformat())
    )
    for row in all_records_cursor.fetchall():
        try:
            d_obj = datetime.strptime(row["record_date"], "%Y-%m-%d").date()
            w_idx = d_obj.weekday()  # 0=Monday, 6=Sunday
            st = row["status"]
            if st in weekday_data[w_idx]:
                weekday_data[w_idx][st] += 1
        except Exception:
            continue

    # Evaluate weekdays that meet minimum threshold (at least 3 evaluated records)
    for w_idx, counts in weekday_data.items():
        w_eval = counts["completed"] + counts["missed"]
        if w_eval >= 3 and overall_evaluated >= 5:
            w_rate = round((counts["completed"] / w_eval * 100.0), 1)
            day_name = weekday_names[w_idx]

            # Detect notable drop-off (25 percentage points below overall average)
            if overall_rate >= 50.0 and (overall_rate - w_rate) >= 25.0:
                conf = evaluate_confidence(w_eval, high_threshold=8, medium_threshold=4)
                insights.append({
                    "type": "weekday_dropoff",
                    "weekday": day_name,
                    "title": f"Noticeable Drop-off on {day_name}s",
                    "message": f"Completion rate drops to {w_rate}% on {day_name}s, which is {round(overall_rate - w_rate, 1)}% lower than your {overall_rate}% overall average.",
                    "evidence": {
                        "weekday": day_name,
                        "weekday_completed": counts["completed"],
                        "weekday_missed": counts["missed"],
                        "weekday_rate": w_rate,
                        "overall_rate": overall_rate,
                        "sample_size": w_eval
                    },
                    "confidence": conf,
                    "recommendation": f"Set a gentle notification or prepare your materials the evening before {day_name} to maintain consistency."
                })
            # Detect peak consistency day (at least 20 percentage points above average or 100% with >= 4 records)
            elif (w_rate - overall_rate >= 20.0) or (w_rate == 100.0 and w_eval >= 4):
                conf = evaluate_confidence(w_eval, high_threshold=8, medium_threshold=4)
                insights.append({
                    "type": "peak_performance_day",
                    "weekday": day_name,
                    "title": f"Peak Consistency on {day_name}s",
                    "message": f"{day_name}s are your highest performing day with a {w_rate}% completion rate ({counts['completed']} of {w_eval} completed).",
                    "evidence": {
                        "weekday": day_name,
                        "weekday_completed": counts["completed"],
                        "weekday_missed": counts["missed"],
                        "weekday_rate": w_rate,
                        "overall_rate": overall_rate,
                        "sample_size": w_eval
                    },
                    "confidence": conf,
                    "recommendation": f"Use your strong momentum on {day_name}s to make progress on key developmental goals."
                })

    # -----------------------------------------------------------------------
    # PATTERN C: TIME-OF-DAY COMPARISON
    # -----------------------------------------------------------------------
    time_groups = {"Morning": {"c": 0, "m": 0, "s": 0},
                   "Afternoon": {"c": 0, "m": 0, "s": 0},
                   "Evening": {"c": 0, "m": 0, "s": 0}}

    tod_cursor = db.execute(
        """
        SELECT h.time_of_day, r.status
        FROM habit_records r
        JOIN habits h ON r.habit_id = h.id
        WHERE h.active = 1 AND r.record_date BETWEEN ? AND ?
        """,
        (start_date.isoformat(), end_date.isoformat())
    )
    for row in tod_cursor.fetchall():
        tod = (row["time_of_day"] or "Morning").capitalize()
        if tod in time_groups:
            if row["status"] == "completed":
                time_groups[tod]["c"] += 1
            elif row["status"] == "missed":
                time_groups[tod]["m"] += 1
            elif row["status"] == "skipped":
                time_groups[tod]["s"] += 1

    valid_times = {}
    for tod, counts in time_groups.items():
        evaluated = counts["c"] + counts["m"]
        if evaluated >= 5:  # Require at least 5 evaluated records per category for meaningful comparison
            valid_times[tod] = {
                "rate": round((counts["c"] / evaluated * 100.0), 1),
                "evaluated": evaluated,
                "completed": counts["c"],
                "missed": counts["m"]
            }

    if len(valid_times) >= 2:
        sorted_times = sorted(valid_times.items(), key=lambda x: x[1]["rate"], reverse=True)
        best_time, best_stats = sorted_times[0]
        worst_time, worst_stats = sorted_times[-1]

        diff = best_stats["rate"] - worst_stats["rate"]
        if diff >= 20.0:
            combined_sample = best_stats["evaluated"] + worst_stats["evaluated"]
            conf = evaluate_confidence(combined_sample, high_threshold=20, medium_threshold=12)
            insights.append({
                "type": "time_of_day_preference",
                "title": f"Optimal Time Window: {best_time}",
                "message": f"Habits scheduled for {best_time} have a {best_stats['rate']}% completion rate, noticeably higher than {worst_time} habits ({worst_stats['rate']}%).",
                "evidence": {
                    "best_time_of_day": best_time,
                    "best_rate": best_stats["rate"],
                    "best_sample": best_stats["evaluated"],
                    "worst_time_of_day": worst_time,
                    "worst_rate": worst_stats["rate"],
                    "worst_sample": worst_stats["evaluated"],
                    "rate_difference": round(diff, 1)
                },
                "confidence": conf,
                "recommendation": f"Schedule demanding or high-priority habits in the {best_time} when your energy and follow-through are strongest."
            })

    # -----------------------------------------------------------------------
    # PATTERN D: REPEATED MISSED HABITS
    # -----------------------------------------------------------------------
    for item in habit_stats_list:
        h = item["habit"]
        records = item["stats"]["records"]
        name = h["name"]

        # Examine recent records chronologically backwards from end_date
        records_desc = sorted(records, key=lambda x: x["record_date"], reverse=True)

        # Count consecutive missed days from the most recent record
        consecutive_misses = 0
        missed_dates = []
        for r in records_desc:
            if r["status"] == "missed":
                consecutive_misses += 1
                missed_dates.append(r["record_date"])
            elif r["status"] == "skipped":
                # Excused skip does not increment missed count and does not mask misses
                continue
            else:
                # Encountered a completed day: streak of misses stops
                break

        # Distinguish a repeated pattern (3+ consecutive misses) from an isolated missed day
        if consecutive_misses >= 3:
            conf = "high" if consecutive_misses >= 5 else "medium"
            date_range_str = f"{missed_dates[-1]} to {missed_dates[0]}"
            insights.append({
                "type": "repeated_misses",
                "habit_id": h["id"],
                "habit_name": name,
                "title": f"Recent Missed Trend: {name}",
                "message": f"'{name}' was marked missed for {consecutive_misses} consecutive scheduled check-ins ({date_range_str}).",
                "evidence": {
                    "consecutive_misses": consecutive_misses,
                    "missed_dates": missed_dates,
                    "sample_size": consecutive_misses
                },
                "confidence": conf,
                "recommendation": "Lower the initial barrier: commit to a 2-minute micro-habit today to restart your momentum effortlessly."
            })

    # -----------------------------------------------------------------------
    # PATTERN E: STREAK MILESTONES
    # -----------------------------------------------------------------------
    for item in habit_stats_list:
        h = item["habit"]
        # Fetch current streak using Phase 2B logic
        curr_streak = h["streak"] if "streak" in h.keys() else 0
        best_strk = item["best_streak"]

        if curr_streak >= 7:
            conf = "high" if curr_streak >= 14 else "medium"
            insights.append({
                "type": "streak_milestone",
                "habit_id": h["id"],
                "habit_name": h["name"],
                "title": f"Streak Milestone: {curr_streak} Days!",
                "message": f"'{h['name']}' has maintained an active {curr_streak}-day continuous streak. (All-time best: {best_strk} days).",
                "evidence": {
                    "current_streak": curr_streak,
                    "best_streak": best_strk,
                    "sample_size": curr_streak
                },
                "confidence": conf,
                "recommendation": "Outstanding momentum! You have locked in a consistent behavioral habit loop."
            })

    return {
        "period": {
            "days": days,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        },
        "summary": {
            "total_active_habits": len(active_habits),
            "total_records": overall_total_records,
            "total_completed": overall_completed,
            "total_missed": overall_missed,
            "total_skipped": overall_skipped,
            "overall_completion_rate": overall_rate,
            "best_overall_streak": best_overall_streak
        },
        "insights": insights
    }


# ---------------------------------------------------------------------------
# SINGLE HABIT DEEP-DIVE ANALYSIS
# ---------------------------------------------------------------------------

def analyze_single_habit(habit_id, days=30, target_date_str=None, db=None):
    """
    Returns detailed statistics, weekday breakdown, and targeted patterns
    for a specific active habit.
    Returns None if the habit does not exist or is deactivated.
    """
    cursor = db.execute("SELECT * FROM habits WHERE id = ? AND active = 1", (habit_id,))
    habit = cursor.fetchone()
    if not habit:
        return None

    end_date = parse_target_date(target_date_str)
    start_date = end_date - timedelta(days=days - 1)

    stats = calculate_habit_statistics(habit_id, start_date, end_date, db)
    best_streak = calculate_best_streak(habit_id, end_date, db)

    # Weekday breakdown specifically for this habit
    weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekday_stats = {name: {"completed": 0, "missed": 0, "skipped": 0, "rate": 0.0, "total": 0} for name in weekday_names}

    for r in stats["records"]:
        try:
            d_obj = datetime.strptime(r["record_date"], "%Y-%m-%d").date()
            day_name = weekday_names[d_obj.weekday()]
            st = r["status"]
            if st in weekday_stats[day_name]:
                weekday_stats[day_name][st] += 1
            weekday_stats[day_name]["total"] += 1
        except Exception:
            continue

    for d_name, d_counts in weekday_stats.items():
        evaluated = d_counts["completed"] + d_counts["missed"]
        d_counts["rate"] = round((d_counts["completed"] / evaluated * 100.0), 1) if evaluated > 0 else 0.0

    # Targeted insights for this habit
    habit_insights = []
    if stats["total_evaluated"] >= 5:
        if stats["completion_rate"] >= 80.0:
            habit_insights.append({
                "type": "strong_routine",
                "title": "Consistent Performer",
                "message": f"{stats['completion_rate']}% of scheduled check-ins completed in the last {days} days.",
                "confidence": evaluate_confidence(stats["total_evaluated"]),
                "recommendation": "Protect this routine and reward yourself for consistency."
            })
        elif stats["completion_rate"] < 50.0:
            habit_insights.append({
                "type": "at_risk_habit",
                "title": "Needs Attention",
                "message": f"Completion rate is {stats['completion_rate']}% ({stats['missed']} missed days).",
                "confidence": evaluate_confidence(stats["total_evaluated"]),
                "recommendation": "Adjust difficulty or change target time to rebuild momentum."
            })

    return {
        "habit": {
            "id": habit["id"],
            "name": habit["name"],
            "category": habit["category"] or "General",
            "time_of_day": habit["time_of_day"] if "time_of_day" in habit.keys() else "Morning",
            "target_time": habit["target_time"] if "target_time" in habit.keys() else "08:00 AM",
            "target_frequency": habit["target_frequency"] if "target_frequency" in habit.keys() else "daily",
            "active": habit["active"]
        },
        "period": {
            "days": days,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        },
        "statistics": {
            "total_records": stats["total_records"],
            "completed": stats["completed"],
            "missed": stats["missed"],
            "skipped": stats["skipped"],
            "completion_rate": stats["completion_rate"],
            "best_streak": best_streak
        },
        "weekday_breakdown": weekday_stats,
        "insights": habit_insights
    }


# ---------------------------------------------------------------------------
# DASHBOARD ANALYTICS DATA BUILDER
# ---------------------------------------------------------------------------

def get_habit_analytics(days=30, target_date_str=None, db=None):
    """
    Returns structured data for dashboard visualizations:
      - daily_trend: day-by-day completed, missed, skipped counts over the window
      - weekday_statistics: aggregates for Mon - Sun
      - habit_breakdown: per-habit rates, counts, and streaks
      - time_of_day_distribution: Morning vs Afternoon vs Evening metrics
    """
    end_date = parse_target_date(target_date_str)
    start_date = end_date - timedelta(days=days - 1)

    cursor = db.execute("SELECT * FROM habits WHERE active = 1 ORDER BY id ASC")
    active_habits = cursor.fetchall()

    # Pre-populate all dates in window to ensure complete time series
    daily_map = {}
    curr = start_date
    while curr <= end_date:
        d_str = curr.isoformat()
        daily_map[d_str] = {"date": d_str, "completed": 0, "missed": 0, "skipped": 0, "total": 0, "completion_rate": 0.0}
        curr += timedelta(days=1)

    weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekday_map = {i: {"day_index": i, "day_name": weekday_names[i], "completed": 0, "missed": 0, "skipped": 0, "total": 0, "completion_rate": 0.0} for i in range(7)}

    time_groups = {
        "Morning": {"completed": 0, "missed": 0, "skipped": 0, "rate": 0.0, "total": 0},
        "Afternoon": {"completed": 0, "missed": 0, "skipped": 0, "rate": 0.0, "total": 0},
        "Evening": {"completed": 0, "missed": 0, "skipped": 0, "rate": 0.0, "total": 0}
    }

    tot_completed = 0
    tot_missed = 0
    tot_skipped = 0

    records_cursor = db.execute(
        """
        SELECT r.record_date, r.status, h.time_of_day
        FROM habit_records r
        JOIN habits h ON r.habit_id = h.id
        WHERE h.active = 1 AND r.record_date BETWEEN ? AND ?
        """,
        (start_date.isoformat(), end_date.isoformat())
    )
    for row in records_cursor.fetchall():
        d_str = row["record_date"]
        st = row["status"]
        tod = (row["time_of_day"] or "Morning").capitalize()

        if d_str in daily_map:
            if st in daily_map[d_str]:
                daily_map[d_str][st] += 1
            daily_map[d_str]["total"] += 1

        try:
            d_obj = datetime.strptime(d_str, "%Y-%m-%d").date()
            w_idx = d_obj.weekday()
            if st in weekday_map[w_idx]:
                weekday_map[w_idx][st] += 1
            weekday_map[w_idx]["total"] += 1
        except Exception:
            pass

        if tod in time_groups:
            if st in time_groups[tod]:
                time_groups[tod][st] += 1
            time_groups[tod]["total"] += 1

        if st == "completed":
            tot_completed += 1
        elif st == "missed":
            tot_missed += 1
        elif st == "skipped":
            tot_skipped += 1

    # Calculate rates for daily series
    for d_data in daily_map.values():
        evaluated = d_data["completed"] + d_data["missed"]
        d_data["completion_rate"] = round((d_data["completed"] / evaluated * 100.0), 1) if evaluated > 0 else 0.0

    # Calculate rates for weekdays
    for w_data in weekday_map.values():
        evaluated = w_data["completed"] + w_data["missed"]
        w_data["completion_rate"] = round((w_data["completed"] / evaluated * 100.0), 1) if evaluated > 0 else 0.0

    # Calculate rates for time of day
    for t_data in time_groups.values():
        evaluated = t_data["completed"] + t_data["missed"]
        t_data["rate"] = round((t_data["completed"] / evaluated * 100.0), 1) if evaluated > 0 else 0.0

    # Habit-wise breakdown
    habit_breakdown = []
    for h in active_habits:
        stats = calculate_habit_statistics(h["id"], start_date, end_date, db)
        best_strk = calculate_best_streak(h["id"], end_date, db)
        habit_breakdown.append({
            "id": h["id"],
            "name": h["name"],
            "category": h["category"] or "General",
            "time_of_day": h["time_of_day"] if "time_of_day" in h.keys() else "Morning",
            "completed": stats["completed"],
            "missed": stats["missed"],
            "skipped": stats["skipped"],
            "completion_rate": stats["completion_rate"],
            "best_streak": best_strk
        })

    tot_eval = tot_completed + tot_missed
    overall_rate = round((tot_completed / tot_eval * 100.0), 1) if tot_eval > 0 else 0.0

    return {
        "period": {
            "days": days,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        },
        "summary": {
            "total_active_habits": len(active_habits),
            "total_completed": tot_completed,
            "total_missed": tot_missed,
            "total_skipped": tot_skipped,
            "overall_completion_rate": overall_rate
        },
        "daily_trend": list(daily_map.values()),
        "weekday_statistics": list(weekday_map.values()),
        "habit_breakdown": habit_breakdown,
        "time_of_day_distribution": time_groups
    }


# ---------------------------------------------------------------------------
# PHASE 7: HABIT CALENDAR HEATMAP, WEEKLY REVIEW, AND GOALS
# ---------------------------------------------------------------------------

def calculate_current_streak(habit_id, target_date=None, db=None):
    """
    Calculates active consecutive completed days for a habit ending at target_date.
    Skipped preserves the streak without incrementing; missed breaks the streak.
    Pending/unrecorded today does not break yesterday's streak.
    """
    if target_date is None:
        target_date = date.today()
    elif isinstance(target_date, str):
        target_date = parse_target_date(target_date)

    cursor = db.execute(
        "SELECT record_date, status FROM habit_records WHERE habit_id = ? AND record_date <= ? ORDER BY record_date DESC",
        (habit_id, target_date.isoformat())
    )
    records = {row["record_date"]: row["status"] for row in cursor.fetchall()}

    streak = 0
    curr_date = target_date
    today_iso = target_date.isoformat()

    if today_iso not in records:
        curr_date = target_date - timedelta(days=1)

    while True:
        d_str = curr_date.isoformat()
        if d_str not in records:
            break

        status = records[d_str]
        if status == "completed":
            streak += 1
            curr_date -= timedelta(days=1)
        elif status == "skipped":
            curr_date -= timedelta(days=1)
        else:
            break

    return streak


def get_calendar_heatmap(month_str=None, habit_id=None, target_date_str=None, db=None):
    """
    Phase 7: Calendar Heatmap Builder.
    Returns month calendar grid with day-by-day records and status for all active habits
    or for a single habit.
    
    Parameters:
      - month_str: 'YYYY-MM' (default: current month)
      - habit_id: optional integer to filter by single habit
      - target_date_str: optional reference date
      - db: SQLite database connection
    """
    ref_date = parse_target_date(target_date_str)
    
    if month_str:
        try:
            parts = month_str.strip().split("-")
            year = int(parts[0])
            month = int(parts[1])
            if month < 1 or month > 12:
                raise ValueError("Month out of range")
        except Exception:
            year = ref_date.year
            month = ref_date.month
    else:
        year = ref_date.year
        month = ref_date.month

    # Number of days in this month
    first_weekday, num_days = calendar.monthrange(year, month)
    first_date = date(year, month, 1)
    last_date = date(year, month, num_days)

    # Get habits
    if habit_id is not None:
        cursor = db.execute("SELECT * FROM habits WHERE id = ?", (habit_id,))
        habits = cursor.fetchall()
        selected_habit_name = habits[0]["name"] if habits else None
    else:
        cursor = db.execute("SELECT * FROM habits WHERE active = 1 ORDER BY id ASC")
        habits = cursor.fetchall()
        selected_habit_name = None

    # Fetch all records for the target habit(s) in this month window
    if habit_id is not None:
        rec_cursor = db.execute(
            """
            SELECT habit_id, record_date, status
            FROM habit_records
            WHERE habit_id = ? AND record_date BETWEEN ? AND ?
            """,
            (habit_id, first_date.isoformat(), last_date.isoformat())
        )
    else:
        rec_cursor = db.execute(
            """
            SELECT r.habit_id, r.record_date, r.status
            FROM habit_records r
            JOIN habits h ON r.habit_id = h.id
            WHERE h.active = 1 AND r.record_date BETWEEN ? AND ?
            """,
            (first_date.isoformat(), last_date.isoformat())
        )

    records_map = {}
    for r in rec_cursor.fetchall():
        records_map[(r["record_date"], r["habit_id"])] = r["status"]

    days = []
    month_completed = 0
    month_missed = 0
    month_skipped = 0
    recorded_days_set = set()

    weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    for d in range(1, num_days + 1):
        curr_d = date(year, month, d)
        d_str = curr_d.isoformat()
        is_today = (curr_d == ref_date)
        is_future = (curr_d > ref_date)

        day_habits = []
        c_count = 0
        m_count = 0
        s_count = 0
        u_count = 0

        for h in habits:
            h_id = h["id"]
            st = records_map.get((d_str, h_id), "unrecorded")
            if st == "completed":
                c_count += 1
                month_completed += 1
                recorded_days_set.add(d_str)
            elif st == "missed":
                m_count += 1
                month_missed += 1
                recorded_days_set.add(d_str)
            elif st == "skipped":
                s_count += 1
                month_skipped += 1
                recorded_days_set.add(d_str)
            else:
                u_count += 1

            day_habits.append({
                "habit_id": h_id,
                "habit_name": h["name"],
                "category": h["category"] or "General",
                "time_of_day": h["time_of_day"] if "time_of_day" in h.keys() and h["time_of_day"] else "Morning",
                "status": st
            })

        total_habits = len(habits)

        # Dominant status classification
        if is_future:
            dominant_status = "future"
        elif total_habits == 0:
            dominant_status = "unrecorded"
        elif habit_id is not None:
            # Single habit mode
            dominant_status = day_habits[0]["status"] if day_habits else "unrecorded"
        else:
            # Multi habit mode
            if c_count == total_habits and total_habits > 0:
                dominant_status = "completed"
            elif c_count > 0:
                dominant_status = "mixed"
            elif m_count > 0:
                dominant_status = "missed"
            elif s_count > 0:
                dominant_status = "skipped"
            else:
                dominant_status = "unrecorded"

        w_idx = curr_d.weekday()
        days.append({
            "date": d_str,
            "day": d,
            "weekday": w_idx,
            "weekday_name": weekday_names[w_idx],
            "is_today": is_today,
            "is_future": is_future,
            "total_habits": total_habits,
            "completed_count": c_count,
            "missed_count": m_count,
            "skipped_count": s_count,
            "unrecorded_count": u_count,
            "dominant_status": dominant_status,
            "records": day_habits
        })

    month_eval = month_completed + month_missed
    month_rate = round((month_completed / month_eval * 100.0), 1) if month_eval > 0 else 0.0

    return {
        "month": f"{year:04d}-{month:02d}",
        "month_name": first_date.strftime("%B %Y"),
        "year": year,
        "month_number": month,
        "first_weekday": first_weekday,  # 0=Mon, 6=Sun
        "total_days": num_days,
        "habit_id": habit_id,
        "habit_name": selected_habit_name,
        "active_habits_count": len(habits),
        "days": days,
        "summary": {
            "total_active_habits": len(habits),
            "recorded_days_count": len(recorded_days_set),
            "completed": month_completed,
            "missed": month_missed,
            "skipped": month_skipped,
            "completion_rate": month_rate
        }
    }


def generate_weekly_review(target_date_str=None, db=None):
    """
    Phase 7: Weekly Progress Review Generator.
    Analyzes actual records for the past 7 days ending at target_date,
    comparing against the preceding 7-day period.
    Identifies completion statistics, trends, strongest recorded days,
    habits needing attention, and habits showing improvement.
    Guards strictly against fabricating statistics when data is insufficient.
    """
    end_date = parse_target_date(target_date_str)
    start_date = end_date - timedelta(days=6)
    prev_end_date = start_date - timedelta(days=1)
    prev_start_date = prev_end_date - timedelta(days=6)

    cursor = db.execute("SELECT * FROM habits WHERE active = 1 ORDER BY id ASC")
    active_habits = cursor.fetchall()

    if not active_habits:
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": 7,
                "prev_start_date": prev_start_date.isoformat(),
                "prev_end_date": prev_end_date.isoformat()
            },
            "data_status": "no_data",
            "message": "No active habits found. Create a habit to begin tracking.",
            "statistics": {
                "total_active_habits": 0,
                "total_records": 0,
                "completed": 0,
                "missed": 0,
                "skipped": 0,
                "completion_rate": 0.0,
                "previous_completion_rate": 0.0,
                "rate_diff": 0.0,
                "trend": "no_data"
            },
            "strongest_recorded_days": [],
            "weakest_recorded_days": [],
            "habits_needing_attention": [],
            "habits_improving": [],
            "strongest_habits": [],
            "all_habits_review": []
        }

    # Query records for current week and previous week
    curr_cursor = db.execute(
        """
        SELECT r.habit_id, r.record_date, r.status, h.name, h.category
        FROM habit_records r
        JOIN habits h ON r.habit_id = h.id
        WHERE h.active = 1 AND r.record_date BETWEEN ? AND ?
        ORDER BY r.record_date ASC
        """,
        (start_date.isoformat(), end_date.isoformat())
    )
    curr_records = curr_cursor.fetchall()

    prev_cursor = db.execute(
        """
        SELECT r.habit_id, r.record_date, r.status
        FROM habit_records r
        JOIN habits h ON r.habit_id = h.id
        WHERE h.active = 1 AND r.record_date BETWEEN ? AND ?
        """,
        (prev_start_date.isoformat(), prev_end_date.isoformat())
    )
    prev_records = prev_cursor.fetchall()

    total_records = len(curr_records)
    c_count = sum(1 for r in curr_records if r["status"] == "completed")
    m_count = sum(1 for r in curr_records if r["status"] == "missed")
    s_count = sum(1 for r in curr_records if r["status"] == "skipped")
    eval_count = c_count + m_count
    rate = round((c_count / eval_count * 100.0), 1) if eval_count > 0 else 0.0

    prev_c_count = sum(1 for r in prev_records if r["status"] == "completed")
    prev_m_count = sum(1 for r in prev_records if r["status"] == "missed")
    prev_eval_count = prev_c_count + prev_m_count
    prev_rate = round((prev_c_count / prev_eval_count * 100.0), 1) if prev_eval_count > 0 else 0.0

    if prev_eval_count > 0:
        rate_diff = round(rate - prev_rate, 1)
        if rate_diff > 0:
            trend = "improved"
        elif rate_diff < 0:
            trend = "declined"
        else:
            trend = "steady"
    else:
        rate_diff = 0.0
        trend = "baseline"

    # Assess data sufficiency
    if total_records == 0:
        data_status = "no_data"
        message = "No habit check-ins recorded for this 7-day period."
    elif total_records < 3:
        data_status = "insufficient_data"
        message = f"Insufficient data: only {total_records} record{'s' if total_records > 1 else ''} logged this week. At least 3 daily check-ins are recommended for a reliable weekly review."
    else:
        data_status = "sufficient_data"
        message = f"Weekly summary calculated from {total_records} verified records across {len(active_habits)} active habit{'s' if len(active_habits) > 1 else ''}."

    # Group by date for strongest/weakest recorded days
    days_map = {}
    curr = start_date
    while curr <= end_date:
        d_str = curr.isoformat()
        days_map[d_str] = {
            "date": d_str,
            "day_name": curr.strftime("%A"),
            "completed": 0,
            "missed": 0,
            "skipped": 0,
            "total": 0
        }
        curr += timedelta(days=1)

    for r in curr_records:
        d_str = r["record_date"]
        st = r["status"]
        if d_str in days_map:
            if st in days_map[d_str]:
                days_map[d_str][st] += 1
            days_map[d_str]["total"] += 1

    for d_data in days_map.values():
        e = d_data["completed"] + d_data["missed"]
        d_data["rate"] = round((d_data["completed"] / e * 100.0), 1) if e > 0 else 0.0

    # Strongest recorded days (at least 1 completion, sorted by rate then completed)
    recorded_days_list = [d for d in days_map.values() if d["total"] > 0]
    strongest_recorded_days = sorted(
        [d for d in recorded_days_list if d["completed"] > 0],
        key=lambda x: (x["rate"], x["completed"]),
        reverse=True
    )
    weakest_recorded_days = sorted(
        [d for d in recorded_days_list if d["missed"] > 0],
        key=lambda x: (x["missed"], -x["rate"]),
        reverse=True
    )

    # Per-habit analysis
    habits_needing_attention = []
    habits_improving = []
    strongest_habits = []
    all_habits_review = []

    for h in active_habits:
        hid = h["id"]
        h_curr = [r for r in curr_records if r["habit_id"] == hid]
        h_prev = [r for r in prev_records if r["habit_id"] == hid]

        hc = sum(1 for r in h_curr if r["status"] == "completed")
        hm = sum(1 for r in h_curr if r["status"] == "missed")
        hs = sum(1 for r in h_curr if r["status"] == "skipped")
        he = hc + hm
        hrate = round((hc / he * 100.0), 1) if he > 0 else 0.0

        hpc = sum(1 for r in h_prev if r["status"] == "completed")
        hpm = sum(1 for r in h_prev if r["status"] == "missed")
        hpe = hpc + hpm
        hprate = round((hpc / hpe * 100.0), 1) if hpe > 0 else 0.0

        current_streak = calculate_current_streak(hid, end_date, db)
        best_streak = calculate_best_streak(hid, end_date, db)

        h_info = {
            "id": hid,
            "name": h["name"],
            "category": h["category"] or "General",
            "completed": hc,
            "missed": hm,
            "skipped": hs,
            "evaluated": he,
            "completion_rate": hrate,
            "prev_completion_rate": hprate,
            "streak": current_streak,
            "best_streak": best_streak
        }
        all_habits_review.append(h_info)

        # Improvement detection
        if hpe > 0 and he > 0 and hrate > hprate:
            diff = round(hrate - hprate, 1)
            habits_improving.append({
                "id": hid,
                "name": h["name"],
                "category": h["category"] or "General",
                "current_rate": hrate,
                "prev_rate": hprate,
                "diff": diff
            })

        # Needs attention detection
        if hm >= 2 or (he >= 3 and hrate < 60.0):
            reason = f"{hm} missed days" if hm >= 2 else f"Low completion rate ({hrate}%)"
            habits_needing_attention.append({
                "id": hid,
                "name": h["name"],
                "category": h["category"] or "General",
                "missed": hm,
                "rate": hrate,
                "reason": reason
            })

        # Strongest habit detection
        if (hrate >= 80.0 and hc >= 2) or current_streak >= 3:
            strongest_habits.append({
                "id": hid,
                "name": h["name"],
                "category": h["category"] or "General",
                "rate": hrate,
                "completed": hc,
                "streak": current_streak
            })

    # Sort strongest habits by completion_rate, then streak, then completed
    strongest_habits = sorted(strongest_habits, key=lambda x: (x["rate"], x["streak"], x["completed"]), reverse=True)

    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days": 7,
            "prev_start_date": prev_start_date.isoformat(),
            "prev_end_date": prev_end_date.isoformat()
        },
        "data_status": data_status,
        "message": message,
        "statistics": {
            "total_active_habits": len(active_habits),
            "total_records": total_records,
            "completed": c_count,
            "missed": m_count,
            "skipped": s_count,
            "completion_rate": rate,
            "previous_completion_rate": prev_rate,
            "rate_diff": rate_diff,
            "trend": trend
        },
        "strongest_recorded_days": strongest_recorded_days[:3],
        "weakest_recorded_days": weakest_recorded_days[:3],
        "habits_needing_attention": habits_needing_attention,
        "habits_improving": habits_improving,
        "strongest_habits": strongest_habits[:3],
        "all_habits_review": all_habits_review
    }


def calculate_goals_and_milestones(target_date_str=None, habit_id=None, db=None):
    """
    Phase 7 & 8: Goals and Milestones Tracker.
    Evaluates weekly completion targets, streak targets, and total completion targets for habits.
    Tracks active, completed, and overdue goal statuses based on measurable metrics and target deadlines.
    Guards against duplicate milestone notifications using the goal_milestones table.
    """
    ref_date = parse_target_date(target_date_str)
    
    # Calculate Monday to Sunday of the current week
    week_start = ref_date - timedelta(days=ref_date.weekday())
    week_end = week_start + timedelta(days=6)
    period_str = f"{week_start.year}-W{week_start.isocalendar()[1]:02d}"

    # Check if end_date column exists in habit_goals
    cols = [r[1] for r in db.execute("PRAGMA table_info(habit_goals)").fetchall()]
    has_end_date = 'end_date' in cols

    select_end_date = "g.end_date," if has_end_date else "NULL as end_date,"
    query = f"""
        SELECT g.id as goal_id, g.habit_id, g.target_type, g.target_value, g.active,
               {select_end_date}
               h.name as habit_name, h.category, h.time_of_day, h.active as habit_active
        FROM habit_goals g
        JOIN habits h ON g.habit_id = h.id
        WHERE g.active = 1 AND h.active = 1
    """
    params = []
    if habit_id is not None:
        query += " AND g.habit_id = ?"
        params.append(habit_id)

    query += " ORDER BY g.id ASC"
    goals_rows = db.execute(query, tuple(params)).fetchall()

    goals_result = []
    new_milestones = []

    for g in goals_rows:
        gid = g["goal_id"]
        hid = g["habit_id"]
        t_val = g["target_value"]
        t_type = g["target_type"] or "weekly_completions"
        end_date_val = g["end_date"] if has_end_date else None

        current_progress = 0
        progress_pct = 0.0
        is_achieved = False
        remaining = 0
        milestone_type = "weekly_target_achieved"
        milestone_period = period_str
        milestone_title = f"Goal Achieved: {g['habit_name']}"
        milestone_msg = ""

        # 1. Weekly Completions Target
        if t_type == "weekly_completions":
            rec_cursor = db.execute(
                """
                SELECT COUNT(*) as completed_count
                FROM habit_records
                WHERE habit_id = ? AND status = 'completed' AND record_date BETWEEN ? AND ?
                """,
                (hid, week_start.isoformat(), week_end.isoformat())
            )
            completed_count = rec_cursor.fetchone()["completed_count"]
            current_progress = completed_count
            progress_pct = min(100.0, round((completed_count / t_val * 100.0), 1)) if t_val > 0 else 0.0
            is_achieved = (completed_count >= t_val)
            remaining = max(0, t_val - completed_count)
            milestone_type = "weekly_target_achieved"
            milestone_period = period_str
            milestone_title = f"Weekly Goal Achieved: {g['habit_name']}"
            milestone_msg = f"Hit weekly target of {t_val} completions ({completed_count}/{t_val}) for week {period_str}!"

        # 2. Target Streak (Consecutive days)
        elif t_type == "target_streak":
            cur_streak = calculate_current_streak(hid, ref_date, db)
            current_progress = cur_streak
            progress_pct = min(100.0, round((cur_streak / t_val * 100.0), 1)) if t_val > 0 else 0.0
            is_achieved = (cur_streak >= t_val)
            remaining = max(0, t_val - cur_streak)
            milestone_type = f"streak_target_{t_val}_achieved"
            milestone_period = f"streak_{t_val}_{hid}_{period_str}"
            milestone_title = f"Streak Goal Achieved: {g['habit_name']}"
            milestone_msg = f"Reached target streak of {t_val} consecutive days ({cur_streak}/{t_val})!"

        # 3. Total Completions Target (All-time count)
        elif t_type == "total_completions":
            rec_cursor = db.execute(
                """
                SELECT COUNT(*) as completed_count
                FROM habit_records
                WHERE habit_id = ? AND status = 'completed' AND record_date <= ?
                """,
                (hid, ref_date.isoformat())
            )
            total_completed = rec_cursor.fetchone()["completed_count"]
            current_progress = total_completed
            progress_pct = min(100.0, round((total_completed / t_val * 100.0), 1)) if t_val > 0 else 0.0
            is_achieved = (total_completed >= t_val)
            remaining = max(0, t_val - total_completed)
            milestone_type = f"total_target_{t_val}_achieved"
            milestone_period = f"total_{t_val}_{hid}"
            milestone_title = f"Total Goal Achieved: {g['habit_name']}"
            milestone_msg = f"Completed '{g['habit_name']}' {t_val} times ({total_completed}/{t_val})!"

        else:
            # Fallback for unrecognized target type
            current_progress = 0
            progress_pct = 0.0
            is_achieved = False
            remaining = t_val

        # Determine Goal Status: active, completed, or overdue
        status = "active"
        if is_achieved:
            status = "completed"
        elif end_date_val and ref_date.isoformat() > str(end_date_val):
            status = "overdue"
        else:
            status = "active"

        # Check / Record Milestone
        milestone_info = None
        has_new_milestone = False

        if is_achieved:
            m_row = db.execute(
                """
                SELECT id, notified, achieved_at
                FROM goal_milestones
                WHERE habit_id = ? AND milestone_type = ? AND milestone_period = ?
                """,
                (hid, milestone_type, milestone_period)
            ).fetchone()

            if m_row is None:
                m_cursor = db.execute(
                    """
                    INSERT INTO goal_milestones (goal_id, habit_id, milestone_type, milestone_period, achieved_at, notified)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, 0)
                    """,
                    (gid, hid, milestone_type, milestone_period)
                )
                db.commit()
                mid = m_cursor.lastrowid
                has_new_milestone = True
                milestone_info = {
                    "id": mid,
                    "goal_id": gid,
                    "habit_id": hid,
                    "habit_name": g["habit_name"],
                    "type": milestone_type,
                    "title": milestone_title,
                    "message": milestone_msg,
                    "period": milestone_period,
                    "notified": 0
                }
                new_milestones.append(milestone_info)
            else:
                milestone_info = {
                    "id": m_row["id"],
                    "goal_id": gid,
                    "habit_id": hid,
                    "habit_name": g["habit_name"],
                    "type": milestone_type,
                    "title": milestone_title,
                    "message": milestone_msg,
                    "period": milestone_period,
                    "notified": m_row["notified"]
                }
                if m_row["notified"] == 0:
                    has_new_milestone = True
                    new_milestones.append(milestone_info)

        goals_result.append({
            "id": gid,
            "habit_id": hid,
            "habit_name": g["habit_name"],
            "category": g["category"] or "General",
            "time_of_day": g["time_of_day"] if "time_of_day" in g.keys() and g["time_of_day"] else "Morning",
            "target_value": t_val,
            "target_type": t_type,
            "end_date": str(end_date_val) if end_date_val else None,
            "status": status,
            "current_progress": current_progress,
            "completed_this_week": current_progress if t_type == "weekly_completions" else current_progress,
            "progress_percentage": progress_pct,
            "is_achieved": is_achieved,
            "remaining": remaining,
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "week_period": period_str,
            "has_new_milestone": has_new_milestone,
            "milestone": milestone_info
        })

    return {
        "goals": goals_result,
        "new_milestones": new_milestones,
        "week_period": period_str,
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat()
    }


def generate_progress_report(report_type="weekly", target_date_str=None, db=None):
    """
    Phase 8: Daily, Weekly, and Monthly Progress Report Generator.
    Aggregates verified SQLite habit records, completion rates, streaks, and goal statuses.
    Reuses deterministic analytics and transparent rule-based categorization.
    Never invents statistics or fabricates trends on empty datasets.
    """
    ref_date = parse_target_date(target_date_str)
    report_type_clean = (report_type or "weekly").lower().strip()

    if report_type_clean == "daily":
        start_date = ref_date
        end_date = ref_date
        period_label = f"Daily Report ({ref_date.isoformat()})"
    elif report_type_clean == "monthly":
        start_date = date(ref_date.year, ref_date.month, 1)
        last_day = calendar.monthrange(ref_date.year, ref_date.month)[1]
        end_date = date(ref_date.year, ref_date.month, last_day)
        period_label = f"Monthly Report: {ref_date.strftime('%B %Y')}"
    else:
        # Default to 7-day weekly period
        report_type_clean = "weekly"
        start_date = ref_date - timedelta(days=6)
        end_date = ref_date
        period_label = f"Weekly Report ({start_date.isoformat()} to {end_date.isoformat()})"

    days_count = (end_date - start_date).days + 1

    # Fetch active habits
    cursor = db.execute("SELECT * FROM habits WHERE active = 1 ORDER BY id ASC")
    active_habits = cursor.fetchall()

    if not active_habits:
        return {
            "report_type": report_type_clean,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "label": period_label,
                "days_count": days_count
            },
            "data_status": "no_data",
            "message": "No active habits found. Create a habit to start tracking.",
            "summary": {
                "total_active_habits": 0,
                "total_records": 0,
                "completed": 0,
                "missed": 0,
                "skipped": 0,
                "completion_rate": 0.0
            },
            "habits": [],
            "successful_habits": [],
            "habits_needing_attention": [],
            "goals_summary": {
                "total_goals": 0,
                "completed_goals": 0,
                "active_goals": 0,
                "overdue_goals": 0
            }
        }

    # Fetch all records in date range
    r_cursor = db.execute(
        """
        SELECT habit_id, record_date, status
        FROM habit_records
        WHERE record_date BETWEEN ? AND ?
        ORDER BY record_date ASC
        """,
        (start_date.isoformat(), end_date.isoformat())
    )
    records = r_cursor.fetchall()
    total_records = len(records)

    records_by_habit = {}
    total_completed = 0
    total_missed = 0
    total_skipped = 0

    for r in records:
        hid = r["habit_id"]
        st = r["status"]
        if hid not in records_by_habit:
            records_by_habit[hid] = {"completed": 0, "missed": 0, "skipped": 0}
        if st == "completed":
            records_by_habit[hid]["completed"] += 1
            total_completed += 1
        elif st == "missed":
            records_by_habit[hid]["missed"] += 1
            total_missed += 1
        elif st == "skipped":
            records_by_habit[hid]["skipped"] += 1
            total_skipped += 1

    total_eval = total_completed + total_missed
    overall_rate = round(total_completed / total_eval * 100.0, 1) if total_eval > 0 else 0.0

    habit_breakdown = []
    successful_habits = []
    habits_needing_attention = []

    for h in active_habits:
        hid = h["id"]
        h_recs = records_by_habit.get(hid, {"completed": 0, "missed": 0, "skipped": 0})
        c_count = h_recs["completed"]
        m_count = h_recs["missed"]
        s_count = h_recs["skipped"]

        eval_count = c_count + m_count
        hrate = round(c_count / eval_count * 100.0, 1) if eval_count > 0 else 0.0
        cur_streak = calculate_current_streak(hid, ref_date, db)
        best_streak = calculate_best_streak(hid, ref_date, db)

        # Categorize performance
        if (hrate >= 80.0 and c_count >= 1) or cur_streak >= 3:
            h_status = "successful"
            successful_habits.append({
                "id": hid,
                "name": h["name"],
                "category": h["category"] or "General",
                "completion_rate": hrate,
                "completed": c_count,
                "current_streak": cur_streak,
                "reason": f"Strong {hrate}% completion with {cur_streak}-day active streak."
            })
        elif m_count >= 2 or (eval_count >= 2 and hrate < 60.0):
            h_status = "needs_attention"
            habits_needing_attention.append({
                "id": hid,
                "name": h["name"],
                "category": h["category"] or "General",
                "completion_rate": hrate,
                "missed": m_count,
                "current_streak": cur_streak,
                "reason": f"{m_count} missed check-ins ({hrate}% completion)."
            })
        else:
            h_status = "steady"

        habit_breakdown.append({
            "id": hid,
            "name": h["name"],
            "category": h["category"] or "General",
            "time_of_day": h["time_of_day"] or "Morning",
            "completed": c_count,
            "missed": m_count,
            "skipped": s_count,
            "completion_rate": hrate,
            "current_streak": cur_streak,
            "best_streak": best_streak,
            "status": h_status
        })

    # Sort habits by completion rate descending
    habit_breakdown.sort(key=lambda x: (x["completion_rate"], x["current_streak"]), reverse=True)

    # Goals summary
    goals_data = calculate_goals_and_milestones(target_date_str=ref_date.isoformat(), db=db)
    all_goals = goals_data.get("goals", [])
    goals_summary = {
        "total_goals": len(all_goals),
        "completed_goals": len([g for g in all_goals if g.get("status") == "completed"]),
        "active_goals": len([g for g in all_goals if g.get("status") == "active"]),
        "overdue_goals": len([g for g in all_goals if g.get("status") == "overdue"])
    }

    data_status = "no_data" if total_records == 0 else "sufficient_data"
    message = (
        f"Report generated from {total_records} verified records across {len(active_habits)} active habits."
        if total_records > 0 else
        f"No check-ins recorded for this {report_type_clean} period."
    )

    return {
        "report_type": report_type_clean,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "label": period_label,
            "days_count": days_count
        },
        "data_status": data_status,
        "message": message,
        "summary": {
            "total_active_habits": len(active_habits),
            "total_records": total_records,
            "completed": total_completed,
            "missed": total_missed,
            "skipped": total_skipped,
            "completion_rate": overall_rate
        },
        "habits": habit_breakdown,
        "successful_habits": successful_habits,
        "habits_needing_attention": habits_needing_attention,
        "goals_summary": goals_summary
    }

