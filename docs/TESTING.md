# StreakLab Test Strategy & Verification Results

This document describes the testing strategy, test cases, and actual test outcomes for **StreakLab — Habit Pattern Detector & Real AI Habit Coach**.

---

## 1. Testing Philosophy & Isolation

StreakLab employs **100% isolated, deterministic automated testing**:
* **Temporary Databases**: Every test case creates a separate temporary SQLite database via `tempfile.mkstemp(suffix='.db')`, runs schema initialization, executes tests, and cleans up the file on teardown. The user's actual database (`instance/streaklab.db`) is **never touched or modified during test runs**.
* **Zero External AI Calls**: Tests never make live network calls to external LLM providers. Provider interactions are thoroughly tested using `unittest.mock` (simulating successful AI output, network timeouts, provider 500 errors, rate limits, and malformed provider responses).
* **Deterministic Fixtures**: All streaks and date ranges use relative date calculations (`date.today() - timedelta(days=n)`) so tests remain evergreen regardless of execution date.

---

## 2. Test Suite Breakdown (63 Automated Tests)

| Category | Count | Focus Areas |
| :--- | :---: | :--- |
| **Health & Core Routes** | 2 | `/api/health` status, database connection, index dashboard HTML rendering |
| **Habits CRUD** | 6 | Creation validation, partial updates, single retrieval, soft deactivation, active filtering |
| **Daily Records & Streaks** | 10 | Upsert logic, consecutive streaks, skipped preservation, missed break, pending reset |
| **Statistical Pattern Engine** | 12 | Strong routine, at-risk habit, weekday drop-off, peak day, time-of-day, repeated misses, milestones |
| **Analytics & Visualizations** | 3 | Daily trends, weekday distributions, habit breakdowns, division-by-zero guards |
| **Hybrid AI Explanations** | 7 | Endpoint structure, empty DB fallback, validation, provider mocking, error resilience |
| **Cache & Performance** | 3 | In-memory cache hit, mutation-triggered invalidation, `refresh=true` query flag |
| **Security & Safety** | 3 | Prompt injection sanitization, zero external calls offline, secrets containment |
| **Phase 6: Real AI Habit Coach Chat** | 17 | Valid chat mock, empty/missing message, malformed JSON, non-string types, length bounds, history validation, no-key fallback, timeout fallback, 30 req/min rate limit, provider error fallback, invalid provider response, intent coverage, source labeling (`ai` vs `fallback`), evidence grounding, zero habits handling, injection defense, secrets leakage containment |
| **Total** | **63** | **All 63 tests passing with 0 failures** |

---

## 3. Actual Automated Test Run

### Command:
```powershell
.\.venv\Scripts\python.exe test_app.py
```

### Actual Output:
```text
...........................AI provider returned invalid non-list response; using local fallback.
..AI provider failed (gemini): Connection timed out. Gracefully falling back to local engine.
.............AI provider returned empty chat response; using local fallback.
....AI Coach provider failed (gemini): URLError: Failed connecting with key AI_KEY_VERY_SECRET_DO_NOT_REVEAL_XYZ123. Falling back to local coach.
....AI Coach provider failed (gemini): Connection timed out. Falling back to local coach.
.AI Coach provider failed (gemini): Gemini API returned HTTP 500. Falling back to local coach.
............
----------------------------------------------------------------------
Ran 63 tests in 2.227s

OK
```

> **Note on Console Warnings during Test Runs:**
> The two log messages printed during testing (`AI provider returned invalid non-list response` and `AI provider failed: Connection timed out`) are **deliberately induced** by the test suite to verify that provider errors are handled gracefully without crashing the app or surfacing HTTP 500 errors.

---

## 4. Key Test Cases Detailed

### A. Health & Diagnostics
* `test_health_check`: Asserts `/api/health` returns `200 OK` with `{"status": "ok", "app": "StreakLab", "database": "connected"}`.
* `test_index_dashboard_route`: Confirms root `/` renders valid HTML containing navigation, metric cards, and chart containers.

### B. Habits Management
* `test_create_habit_success`: Verifies `POST /api/habits` creates a record with default streak 0 and status pending.
* `test_create_habit_validation`: Confirms empty names, whitespace-only names, or non-JSON payloads return `400 Bad Request`.
* `test_get_habits`: Validates active filtering (`active=1`) and `?all=true` parameter.
* `test_phase5_update_habit_partial_and_validation`: Confirms partial updates (`category`, `target_time`) preserve existing fields.
* `test_phase5_deactivate_habit_preserves_history`: Verifies soft deletion (`DELETE /api/habits/<id>`) sets `active=0` while retaining past check-in rows in `habit_records`.

### C. Streak Calculations & Integrity
* `test_streak_consecutive_completed`: Verifies 5 consecutive completed days yields a streak of 5.
* `test_streak_skipped_preserves`: Verifies skipped rest days preserve streak momentum without penalizing or resetting.
* `test_streak_missed_resets`: Confirms a missed day immediately resets the streak to 0.
* `test_streak_unrecorded_day_breaks`: Confirms a gap in check-in history breaks the streak.
* `test_streak_today_pending_preserves_yesterday`: Asserts that if today is not yet checked in, yesterday's active streak is preserved.
* `test_phase5_pending_record_status_and_deletion`: Verifies setting a record back to `pending` removes the record and recalculates streak.

### D. Pattern Detection Engine
* `test_phase3_strong_routine_detection`: Verifies $\ge 80\%$ completion with $\ge 5$ records triggers `strong_routine`.
* `test_phase3_at_risk_habit_detection`: Verifies $< 50\%$ completion with $\ge 5$ records triggers `at_risk_habit`.
* `test_phase3_weekday_dropoff_pattern`: Verifies a weekday with $\ge 25\%$ drop below average triggers `weekday_dropoff`.
* `test_phase3_peak_performance_day_pattern`: Verifies a weekday with $\ge 20\%$ boost triggers `peak_performance_day`.
* `test_phase3_time_of_day_preference_pattern`: Verifies a $\ge 20\%$ gap between Morning and Evening triggers `time_of_day_preference`.
* `test_phase3_repeated_missed_habit_pattern`: Verifies 3 consecutive missed check-ins triggers `repeated_misses`.
* `test_phase3_streak_milestone_pattern`: Verifies a continuous streak $\ge 7$ days triggers `streak_milestone`.
* `test_phase3_insufficient_data_empty_db`: Verifies fewer than 3 total records safely triggers `insufficient_data`.
* `test_phase3_division_by_zero_edge_case`: Verifies a habit with only skipped records evaluates to `0.0%` without runtime error.
* `test_phase3_future_records_excluded`: Confirms records with future dates do not influence historical stats.

### E. Hybrid AI Explanations & Fallback
* `test_phase4_local_fallback_unit_coverage`: Tests `generate_local_fallback()` across all 8 pattern types.
* `test_phase4_mock_ai_provider_success`: Confirms that when Gemini/OpenAI returns valid JSON, cards are tagged `source: "ai"`.
* `test_phase4_mock_ai_provider_timeout_fallback`: Simulates network timeouts; confirms app returns `200 OK` with `source: "fallback"`.
* `test_phase4_mock_ai_malformed_response_fallback`: Simulates corrupted provider JSON; confirms clean fallback.
* `test_phase4_cache_and_invalidation`: Verifies in-memory cache hit on repeat queries and automatic invalidation on record mutations.
* `test_phase4_no_external_calls_offline`: Asserts that `urllib.request.urlopen` is **never called** when AI credentials are unset.

### F. Phase 6 Real AI Habit Coach Chatbox (17 Scenarios)
* `test_phase6_valid_chat_mocked_ai_response`: Validates `POST /api/chat` with mocked Gemini AI response (`source: "ai"`, `provider: "gemini"`).
* `test_phase6_missing_or_empty_message`: Asserts `400 Bad Request` on missing, empty, or whitespace-only message bodies.
* `test_phase6_malformed_json`: Asserts `400 Bad Request` on non-JSON content types and malformed JSON syntax.
* `test_phase6_non_string_message`: Asserts `400 Bad Request` on integers, booleans, lists, and dicts passed as messages.
* `test_phase6_excessively_long_message`: Asserts `400 Bad Request` on messages exceeding 1,000 characters.
* `test_phase6_oversized_or_malformed_conversation_history`: Enforces array type, max 20 history messages, and content length caps.
* `test_phase6_missing_api_key_deterministic_fallback`: Verifies seamless local coaching fallback when `AI_API_KEY` is unconfigured.
* `test_phase6_provider_timeout_fallback`: Verifies app returns `200 OK` with grounded local fallback upon remote timeout.
* `test_phase6_rate_limit_and_provider_error`: Verifies sliding-window rate limit triggers `429` on 31st request/min; remote 500 error triggers fallback.
* `test_phase6_invalid_provider_response`: Confirms corrupted or empty LLM response safely triggers local fallback.
* `test_phase6_correct_fallback_behavior_intents`: Verifies rule-based responses across 6 core intents (progress, weak habit, patterns, suggestions, comparison, greetings).
* `test_phase6_source_label_ai_and_fallback`: Confirms source badges are accurately labeled as `"ai"` vs `"fallback"`.
* `test_phase6_evidence_grounding_real_habit_records`: Confirms numerical evidence chips match actual SQLite stored records.
* `test_phase6_insufficient_data_handling`: Asserts zero active habits produces helpful prompt to add habits without hallucinating records.
* `test_phase6_prompt_injection_defense`: Verifies malicious queries and SQL injection in habit names cannot breach system instructions or drop tables.
* `test_phase6_no_api_key_or_secrets_leaked_in_responses`: Verifies API keys in mock exceptions are scrubbed and never returned to the client.
* `test_phase6_existing_endpoints_regression_protection`: Verifies habits, records, analytics, insights, and explanations endpoints remain intact.

---

## 5. Manual Verification Checklist

| Scenario | Expected Outcome | Result |
| :--- | :--- | :---: |
| Open `http://127.0.0.1:5000` | Dashboard loads with responsive cards and charts | ✅ Verified |
| Click "Done" on a habit | Button highlights green, streak increments, toast appears | ✅ Verified |
| Click "Missed" on a habit | Button highlights red, streak resets, toast appears | ✅ Verified |
| Click "Skipped" on a habit | Button highlights yellow, streak maintained, toast appears | ✅ Verified |
| Add new habit via modal | Form validates, closes modal automatically, habit appears in list | ✅ Verified |
| Filter by Morning / Afternoon | List filters instantly without page reload | ✅ Verified |
| Change Window selector (7..90) | Insights reload with correct period metrics | ✅ Verified |
| Click Floating Chat Launcher | Chatbox drawer slides up smoothly at bottom-right | ✅ Verified |
| Click Quick Question Chip | Immediately sends question and streams evidence-grounded response | ✅ Verified |
| Press Enter in Chat Textarea | Sends message, disables input while loading, auto-scrolls to bottom | ✅ Verified |
| Shift+Enter in Chat Textarea | Inserts newline without premature sending | ✅ Verified |
| Click "↺" Clear Chat Button | Resets chat session to initial greeting and suggested question chips | ✅ Verified |
| Close Chat via "✕" Button | Chatbox collapses, launcher icon resets | ✅ Verified |
| Inspect without AI key | Footer displays `Offline Ready` / `Fallback Coach` | ✅ Verified |
| Set `AI_PROVIDER=gemini` & key | Displays `GEMINI AI` badge with conversational coaching | ✅ Verified |
