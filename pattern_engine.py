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

from datetime import datetime, timedelta, date


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
