# StreakLab — 5-Minute Live Demonstration Guide

This guide provides a structured, step-by-step demonstration sequence for presenting **StreakLab — Habit Pattern Detector** in class or during an evaluation.

---

## ⏱️ Live Demonstration Timeline (5 Minutes)

```text
[0:00 - 0:45]  Segment 1: Introduction & Problem Statement
[0:45 - 1:45]  Segment 2: Real-Time Tracking & Rest-Preserving Streaks
[1:45 - 2:45]  Segment 3: Statistical Pattern Detection Engine
[2:45 - 4:00]  Segment 4: Real AI Habit Coach Chatbox (Phase 6)
[4:00 - 5:00]  Segment 5: Architecture, 63-Test Suite & Security
```

---

### Segment 1: Introduction & Problem Statement (45 seconds)

* **Hook**:
  > *"Most habit trackers simply tell you whether you did a habit today. But they fail to tell you **why** you're struggling, or **when** your willpower naturally drops. StreakLab was built to solve this problem: it pairs real-time habit tracking with an intelligent pattern detection engine and a real AI habit coach."*
* **Open the Dashboard**:
  * Open `http://127.0.0.1:5000` in the browser.
  * Point out the clean, modern aesthetic: Top navigation with the **Phase 6 • AI Habit Coach** badge, today's date chip, and quick KPI metrics.
  * Point out the summary cards: **Today's Completion Rate**, **Active Habits**, **Current Streaks**, and the **Top Consistent Habit**.

---

### Segment 2: Real-Time Tracking & Streak Logic (60 seconds)

* **Interactive Status Check-in**:
  1. Find a habit in the list (e.g., *"30-Min Python Practice"*).
  2. Click **Done** (`completed`): Show the green status badge, fire toast notification, and observe the streak increment.
  3. Click **Skipped**: Explain StreakLab's unique **rest-day preservation**:
     > *"Unlike rigid trackers that punish rest days, StreakLab treats skipped days as planned pauses—preserving streak momentum without resetting your count to zero."*
  4. Click **Missed**: Observe the streak resetting to zero and the completion rate recalculating in real time.
* **Filter Pills**:
  * Click **Morning**, **Afternoon**, and **Evening** pills to demonstrate instant client-side filtering without reloading the page.
* **Adding a New Habit**:
  * Click **+ Add Habit**.
  * Enter name: *"Evening Reading"*, Category: *"Mindfulness"*, Time: *"Evening"*, Target Time: *"09:00 PM"*.
  * Click **Save Habit**. Notice the modal closes cleanly, a success toast appears, and the habit is prepended to the list.

---

### Segment 3: Statistical Pattern Detection Engine (60 seconds)

* **Scroll to the Right Column** (`Habit Pattern Detector` card):
* **Explain the Principle**:
  > *"StreakLab does not use fake or hardcoded insights. Everything you see here is calculated directly from actual SQLite check-in records."*
* **Demonstrate the Configurable Analysis Window**:
  1. Open the window dropdown: toggle between **Last 7 Days**, **Last 14 Days**, and **Last 30 Days**.
  2. Notice how the footer updates immediately: e.g., `Window: 14 Days • 18 done / 2 missed (90.0%)`.
* **Highlight Detected Patterns**:
  * **Strong Routine**: High consistency habits ($\ge 80\%$) highlighted with habit-stacking advice.
  * **Weekday Drop-offs**: Quantified drop in performance (e.g., *"Drops to 40% on Fridays"*).
  * **Peak Performance Days**: Highlights the user's highest momentum day.
  * **Time-of-Day Window**: Compares Morning vs Evening performance.
  * **Recent Missed Trend**: Warns when a habit has 3+ consecutive misses and suggests a 2-minute micro-habit reset.

---

### Segment 4: Real AI Habit Coach Chatbox (Phase 6) (75 seconds)

* **Open the Floating Chatbox**:
  * Point to the bottom-right corner: notice the floating launcher button with a pulsing green indicator.
  * Click the launcher: the sleek chat drawer slides up smoothly.
* **Demonstrate Suggested Question Chips**:
  1. Click the chip: *"📊 How are my habits going this week?"*.
  2. Notice the instant typing indicator, followed by a grounded response with active habit counts and completion rates.
  3. Notice the **evidence chips** beneath the message bubble (e.g., `7-Day Rate: 71.4%`, `Active Habits: 2`).
  4. Notice the source badge: `<AI Powered>` (if Gemini/OpenAI configured) or `<Fallback Coach>` (if offline).
* **Ask Follow-up Questions**:
  * Type: *"Which habit needs the most attention?"* and press **Enter**.
  * Observe the coach identifying the habit with the lowest completion rate and proposing a low-friction start.
  * Type: *"Suggest a plan to improve my consistency."* -> observe the 3-step anchor stacking strategy.
* **Session Management**:
  * Click the **↺** button in the chat header to reset the conversation.
  * Click the **✕** button to collapse the chat panel.

---

### Segment 5: Architecture, 63-Test Suite & Security (60 seconds)

* **Open Terminal / PowerShell**:
* **Run the Automated Test Suite**:
  ```powershell
  .\.venv\Scripts\python.exe test_app.py
  ```
* **Walk Through the Results**:
  > *"Here you can see our comprehensive test suite: 63 automated tests running across isolated SQLite databases, validating everything from foreign key cascades to prompt injection defense, rate limiting, and 100% mocked AI provider resilience."*
* **Conclude**:
  > *"StreakLab provides a complete, robust, full-stack demonstration of applied AI: deterministic data integrity at the core, paired with grounded, helpful language coaching at the surface."*

---

## 🛠️ Demo Preparation Checklist

Before presenting, make sure:
1. Virtual environment is ready: `.\.venv\Scripts\Activate.ps1`
2. Test database is clean or seeded: run `.\.venv\Scripts\python.exe test_app.py`
3. Flask server is running: `.\.venv\Scripts\python.exe app.py`
4. Browser is open to `http://127.0.0.1:5000` with console open (`F12`) to verify zero JavaScript errors.
