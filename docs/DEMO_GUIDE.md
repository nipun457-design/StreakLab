# StreakLab — 5-Minute Live Demonstration Guide

This guide provides a structured, step-by-step demonstration sequence for presenting **StreakLab — Habit Pattern Detector** in class or during an evaluation.

---

## ⏱️ Live Demonstration Timeline (5 Minutes)

```text
[0:00 - 1:00]  Minute 1: Introduction & Problem Statement
[1:00 - 2:00]  Minute 2: Real-Time Tracking & Streak Logic
[2:00 - 3:00]  Minute 3: Statistical Pattern Detection Engine
[3:00 - 4:00]  Minute 4: Hybrid AI Explanations & Offline Fallback
[4:00 - 5:00]  Minute 5: Architecture, Tests & Production Readiness
```

---

### Minute 1: Introduction & Problem Statement (60 seconds)

* **Hook**:
  > *"Most habit trackers simply tell you whether you did a habit today. But they fail to tell you **why** you're struggling, or **when** your willpower naturally drops. StreakLab was built to solve this problem: it pairs real-time habit tracking with an intelligent pattern detection engine that uncovers behavioral rhythms."*
* **Open the Dashboard**:
  * Open `http://127.0.0.1:5000` in the browser.
  * Point out the clean, modern aesthetic: Top navigation with the **Phase 5 • Hybrid AI & Analytics** badge, today's date chip, and quick KPI metrics.
  * Point out the four summary cards: **Today's Completion Rate**, **Active Habits**, **Current Streaks**, and the **Top Consistent Habit**.

---

### Minute 2: Real-Time Tracking & Streak Logic (60 seconds)

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

### Minute 3: Statistical Pattern Detection Engine (60 seconds)

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

### Minute 4: Hybrid AI Explanations & Offline Fallback (60 seconds)

* **Explain the Hybrid Philosophy**:
  > *"A critical requirement in applied AI is avoiding hallucination. In StreakLab, the AI never calculates numbers or invents streaks. The Python statistical engine is the sole source of truth. The AI's only job is to translate that evidence into supportive coaching advice."*
* **Show the Source Badge**:
  * Point to the small badge on each pattern card:
    * If running offline: shows `<Rule>` (Rule-based engine).
    * If configured with Gemini/OpenAI: shows `<AI>` (AI Coach).
* **Show Evidence Grounding**:
  * Point out the **Evidence box** on each card: e.g., `9 completed out of 10 evaluated check-ins (90.0% consistency)`.
  * Point out the **Practical Recommendation**: e.g., *"Prepare your cues the evening before Friday to maintain momentum."*
* **Demonstrate Offline Resilience**:
  * Explain that if the Wi-Fi drops, the API key expires, or the external provider times out, the app continues functioning seamlessly using the built-in deterministic Python explainer.

---

### Minute 5: Architecture, Tests & Production Readiness (60 seconds)

* **Open Terminal / PowerShell**:
* **Run the Automated Test Suite**:
  ```powershell
  .\.venv\Scripts\python.exe test_app.py
  ```
* **Walk Through the Results**:
  > *"Here you can see our comprehensive test suite: 46 automated tests running across isolated SQLite databases, validating everything from foreign key cascades to division-by-zero protection, prompt injection sanitization, and AI provider mocking."*
* **Conclude**:
  > *"StreakLab provides a complete, robust, full-stack demonstration of applied AI: deterministic data integrity at the core, paired with grounded, helpful language coaching at the surface."*

---

## 🛠️ Demo Preparation Checklist

Before presenting, make sure:
1. Virtual environment is ready: `.\.venv\Scripts\Activate.ps1`
2. Test database is clean or seeded: run `.\.venv\Scripts\python.exe test_app.py`
3. Flask server is running: `.\.venv\Scripts\python.exe app.py`
4. Browser is open to `http://127.0.0.1:5000` with console open (`F12`) to verify zero JavaScript errors.
