/**
 * ============================================================================
 * StreakLab — Habit Pattern Detector
 * Frontend Logic: static/script.js
 * 
 * Phase 2B: SQLite Database & Flask REST API Integration
 * - Asynchronously loads and persists habits via Flask REST API endpoints
 * - Tracks daily records (completed, missed, skipped) via /api/records
 * - Calculates streaks and 7-day consistency directly from database records
 * - Updates KPI metrics, Chart.js graphs, and time-of-day distributions
 * - Prevents duplicate submissions and displays friendly error notifications
 * - Offers safe, optional one-time migration from Phase 1 browser localStorage
 * ============================================================================
 */

// ----------------------------------------------------------------------------
// 1. GLOBAL STATE & CONFIGURATION
// ----------------------------------------------------------------------------
let habits = [];
let currentFilter = "all";
let weeklyChartInstance = null;
let timeOfDayChartInstance = null;

// Submission & concurrency locks to prevent duplicate requests
let isSubmittingHabit = false;
const activeRecordRequests = new Set();
const activeDeleteRequests = new Set();
let currentInsightsDays = 30;

// Phase 7 Global State
let currentCalendarYear = null;
let currentCalendarMonth = null;
let currentCalendarHabitId = "";
let currentCalendarData = null;
let currentWeeklyReviewData = null;
let currentGoals = [];
const acknowledgedMilestones = new Set();

// Category visual styling configuration
const CATEGORY_CONFIG = {
  "Coding": { icon: "bi-code-slash", color: "bg-indigo-subtle text-indigo" },
  "Fitness": { icon: "bi-activity", color: "bg-emerald-subtle text-emerald" },
  "Learning": { icon: "bi-book", color: "bg-purple-subtle text-purple" },
  "Mindfulness": { icon: "bi-heart-pulse", color: "bg-orange-subtle text-orange" },
  "Health": { icon: "bi-droplet-fill", color: "bg-primary-subtle text-primary" },
  "Productivity": { icon: "bi-check2-square", color: "bg-indigo-subtle text-indigo" },
  "General": { icon: "bi-star-fill", color: "bg-primary-subtle text-primary" }
};

// ----------------------------------------------------------------------------
// 2. INITIALIZATION ON DOM READY
// ----------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  // Step A: Display formatted local date in top navigation
  displayCurrentDate();

  // Step B: Set up user event listeners (form submissions, filter tabs, period selector)
  setupEventListeners();

  // Step C: Initialize Chart.js interactive graphs with empty/initial state
  initCharts();

  // Step D: Load habits from the SQLite database via Flask REST API
  loadHabitsFromApi();

  // Step E: Load rule-based habit pattern insights (Phase 3)
  loadInsightsFromApi(currentInsightsDays);

  // Step F: Initialize AI Habit Coach Chatbox (Phase 6)
  initChatCoach();

  // Step G: Initialize Smart Progress & Goals (Phase 7)
  initPhase7();
});

/**
 * Returns today's date formatted as YYYY-MM-DD in local time.
 */
function getTodayDateString() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

/**
 * Formats and injects today's date into the top navbar (e.g. "Wed, Oct 21, 2026").
 */
function displayCurrentDate() {
  const dateEl = document.getElementById("currentDateDisplay");
  if (!dateEl) return;
  const now = new Date();
  const options = { weekday: "short", month: "short", day: "numeric", year: "numeric" };
  dateEl.textContent = now.toLocaleDateString("en-US", options);
}

// ----------------------------------------------------------------------------
// 3. API COMMUNICATION (HABITS & RECORDS)
// ----------------------------------------------------------------------------

/**
 * Loads all active habits from the Flask API (GET /api/habits).
 * Does not fall back silently to sample data if the server fails.
 */
async function loadHabitsFromApi() {
  const today = getTodayDateString();
  const alertContainer = document.getElementById("dashboardAlertContainer");

  try {
    const response = await fetch(`/api/habits?date=${encodeURIComponent(today)}`);

    if (!response.ok) {
      throw new Error(`Server returned HTTP ${response.status}`);
    }

    const data = await response.json();
    habits = Array.isArray(data) ? data : [];

    // Clear any previous error alerts
    if (alertContainer) {
      alertContainer.innerHTML = "";
    }

    // Check for optional one-time localStorage migration if SQLite database is empty
    checkLocalStorageMigration();

    // Re-render UI with database-backed data
    renderHabits();
    updateSummaryMetrics();
    updateCharts();
    loadInsightsFromApi(currentInsightsDays);
    populateCalendarHabitSelect();
    populateGoalHabitSelect();
    loadCalendarHeatmap();
    loadWeeklyReview();
    loadGoalsAndMilestones();

  } catch (error) {
    console.error("StreakLab: Could not load habits from API:", error);
    habits = [];

    // Friendly error alert in dashboard
    if (alertContainer) {
      alertContainer.innerHTML = `
        <div class="alert alert-warning d-flex flex-column flex-sm-row align-items-sm-center justify-content-between p-3 rounded-4 shadow-sm border-warning-subtle mb-0 gap-2">
          <div class="d-flex align-items-center gap-2">
            <i class="bi bi-exclamation-triangle-fill text-warning fs-5"></i>
            <div>
              <strong class="d-block text-dark">Backend Connection Warning</strong>
              <span class="small text-muted">Unable to reach the StreakLab API. Ensure the Flask server is running at <code>http://127.0.0.1:5000</code>.</span>
            </div>
          </div>
          <button type="button" class="btn btn-sm btn-outline-dark rounded-pill px-3 align-self-start align-self-sm-center" onclick="loadHabitsFromApi()">
            <i class="bi bi-arrow-clockwise me-1"></i>Retry
          </button>
        </div>
      `;
    }

    renderHabits();
    updateSummaryMetrics();
    updateCharts();
    showToast("Unable to connect to Flask server. Please verify backend is running.", "warning");
  }
}

/**
 * Checks if browser localStorage has Phase 1 habits that can be safely imported
 * into the SQLite database. Does not overwrite or delete any existing data.
 */
function checkLocalStorageMigration() {
  const alertContainer = document.getElementById("dashboardAlertContainer");
  if (!alertContainer) return;

  const dismissed = localStorage.getItem("streaklab_migration_dismissed");
  const saved = localStorage.getItem("streaklab_habits_v1");

  if (dismissed || !saved) return;

  try {
    const legacy = JSON.parse(saved);
    if (!Array.isArray(legacy) || legacy.length === 0) return;

    // Only offer migration if SQLite database currently has 0 habits
    if (habits.length === 0) {
      alertContainer.innerHTML = `
        <div class="alert alert-info d-flex flex-column flex-md-row align-items-md-center justify-content-between p-3 rounded-4 shadow-sm border-info-subtle gap-2">
          <div class="d-flex align-items-center gap-2">
            <i class="bi bi-cloud-arrow-up-fill text-primary fs-4"></i>
            <div>
              <strong class="text-dark">Phase 1 Habits Detected</strong>
              <div class="small text-muted">Found ${legacy.length} habits in your browser storage. Would you like to import them into your SQLite database?</div>
            </div>
          </div>
          <div class="d-flex align-items-center gap-2 align-self-end align-self-md-center">
            <button type="button" class="btn btn-sm btn-light rounded-pill px-3" onclick="dismissMigration()">Dismiss</button>
            <button type="button" class="btn btn-sm btn-primary rounded-pill px-3 d-flex align-items-center gap-1" id="btnMigrateHabits" onclick="migrateLegacyHabits()">
              <i class="bi bi-box-arrow-in-down"></i> Import to Database
            </button>
          </div>
        </div>
      `;
    }
  } catch (e) {
    console.warn("Could not inspect localStorage for legacy habits:", e);
  }
}

/**
 * Dismisses the migration banner without deleting any stored data.
 */
function dismissMigration() {
  localStorage.setItem("streaklab_migration_dismissed", "true");
  const alertContainer = document.getElementById("dashboardAlertContainer");
  if (alertContainer) alertContainer.innerHTML = "";
}

/**
 * Safely migrates habits from browser localStorage into SQLite via the REST API.
 */
async function migrateLegacyHabits() {
  const btn = document.getElementById("btnMigrateHabits");
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner-border spinner-border-sm me-1" role="status"></span>Importing...`;
  }

  const saved = localStorage.getItem("streaklab_habits_v1");
  if (!saved) return;

  try {
    const legacyHabits = JSON.parse(saved);
    const today = getTodayDateString();

    for (const item of legacyHabits) {
      // 1. Create habit in SQLite
      const res = await fetch("/api/habits", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: item.name,
          category: item.category || "General",
          target_frequency: item.frequency || "daily",
          time_of_day: item.timeOfDay || "Morning",
          target_time: item.targetTime || "08:00 AM",
          description: "Imported from Phase 1 browser storage"
        })
      });

      if (res.ok) {
        const created = await res.json();
        // 2. If habit had a completed/missed/skipped status today, save record
        if (item.status && item.status !== "pending") {
          await fetch("/api/records", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              habit_id: created.id,
              record_date: today,
              status: item.status
            })
          });
        }
      }
    }

    // Mark migration complete, archive localStorage
    localStorage.setItem("streaklab_habits_v1_imported", saved);
    localStorage.removeItem("streaklab_habits_v1");
    dismissMigration();

    showToast("Habits successfully imported into SQLite database!", "success");
    await loadHabitsFromApi();

  } catch (error) {
    console.error("Migration error:", error);
    showToast("Could not complete migration: " + error.message, "danger");
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = "Import to Database";
    }
  }
}

// ----------------------------------------------------------------------------
// 4. RENDERING HABIT CARDS
// ----------------------------------------------------------------------------

/**
 * Renders the habit items matching the active filter into #habitsListContainer.
 */
function renderHabits() {
  const container = document.getElementById("habitsListContainer");
  const emptyState = document.getElementById("emptyHabitsState");
  if (!container) return;

  // Filter habits according to current selection (all, Morning, Afternoon, Evening)
  const filtered = habits.filter(habit => {
    if (currentFilter === "all") return true;
    const timeOfDay = habit.timeOfDay || habit.time_of_day || "Morning";
    return timeOfDay.toLowerCase() === currentFilter.toLowerCase();
  });

  // Toggle empty state if no habits match
  if (filtered.length === 0) {
    container.innerHTML = "";
    if (emptyState) emptyState.classList.remove("d-none");
    return;
  }

  if (emptyState) emptyState.classList.add("d-none");

  // Build HTML cards for each habit
  container.innerHTML = filtered.map(habit => {
    const habitStatus = habit.status || "pending";
    const statusClass = habitStatus !== "pending" ? `status-${habitStatus}` : "";
    
    // Status text & badge styling
    let statusLabel = "Pending";
    let statusBadgeClass = "bg-secondary-subtle text-secondary";
    if (habitStatus === "completed") {
      statusLabel = "Completed";
      statusBadgeClass = "bg-success text-white";
    } else if (habitStatus === "missed") {
      statusLabel = "Missed";
      statusBadgeClass = "bg-danger text-white";
    } else if (habitStatus === "skipped") {
      statusLabel = "Skipped";
      statusBadgeClass = "bg-warning text-dark";
    }

    // Category visual config
    const catName = habit.category || "General";
    const catConfig = CATEGORY_CONFIG[catName] || CATEGORY_CONFIG["General"];
    const timeOfDay = habit.timeOfDay || habit.time_of_day || "Morning";
    const targetTime = habit.targetTime || habit.target_time || "08:00 AM";
    const frequency = habit.frequency || habit.target_frequency || "daily";
    const streakCount = typeof habit.streak === "number" ? habit.streak : 0;

    // Mini 7-day dot history HTML
    const dayLetters = ["M", "T", "W", "T", "F", "S", "S"];
    const historyList = Array.isArray(habit.weeklyHistory)
      ? habit.weeklyHistory
      : (Array.isArray(habit.weekly_history) ? habit.weekly_history : ["pending", "pending", "pending", "pending", "pending", "pending", "pending"]);

    const historyDotsHtml = historyList.map((st, i) => {
      let dotClass = "dot-pending";
      if (st === "done" || st === "completed") dotClass = "dot-done";
      else if (st === "missed") dotClass = "dot-missed";
      else if (st === "skipped") dotClass = "dot-skipped";
      return `<span class="history-dot ${dotClass}" title="Day ${i + 1} (${dayLetters[i % 7]}): ${st}"></span>`;
    }).join("");

    // Concurrency disable state
    const isBusy = activeRecordRequests.has(habit.id) || activeDeleteRequests.has(habit.id);
    const disabledAttr = isBusy ? "disabled" : "";

    return `
      <div class="habit-card ${statusClass}" data-id="${habit.id}">
        <div class="d-flex flex-column flex-md-row align-items-md-center justify-content-between gap-3">
          
          <!-- Habit Info (Left) -->
          <div class="d-flex align-items-center gap-3">
            <div class="habit-cat-icon ${catConfig.color}">
              <i class="bi ${catConfig.icon}"></i>
            </div>
            <div>
              <div class="d-flex align-items-center gap-2 flex-wrap mb-1">
                <span class="habit-name">${escapeHtml(habit.name)}</span>
                <span class="badge ${statusBadgeClass} rounded-pill small">${statusLabel}</span>
              </div>
              <div class="d-flex align-items-center gap-3 text-muted small flex-wrap">
                <span><i class="bi bi-clock me-1"></i>${escapeHtml(targetTime)}</span>
                <span><i class="bi bi-tag me-1"></i>${escapeHtml(catName)}</span>
                <span><i class="bi bi-sun me-1"></i>${escapeHtml(timeOfDay)}</span>
                <span><i class="bi bi-repeat me-1"></i>${escapeHtml(frequency)}</span>
              </div>
              ${habit.description ? `<p class="text-muted small mb-0 mt-1 fst-italic">${escapeHtml(habit.description)}</p>` : ""}
            </div>
          </div>

          <!-- Habit Controls & Stats (Right) -->
          <div class="d-flex align-items-center justify-content-between justify-content-md-end gap-3 flex-wrap">
            
            <!-- Streak & 7-Day History Mini Indicator -->
            <div class="d-flex flex-column align-items-end me-1">
              <span class="streak-badge bg-orange-subtle text-orange mb-1">
                <i class="bi bi-fire"></i> ${streakCount} ${streakCount === 1 ? "day" : "days"}
              </span>
              <div class="mini-history-dots" title="Last 7 days consistency">
                ${historyDotsHtml}
              </div>
            </div>

            <!-- 3 Status Buttons (Done, Missed, Skipped) -->
            <div class="action-btn-group" role="group" aria-label="Habit completion status actions">
              <!-- Mark Done Button -->
              <button 
                type="button" 
                class="btn-status btn-status-done ${habitStatus === 'completed' ? 'active' : ''}" 
                title="Mark Completed" 
                onclick="handleStatusChange(${habit.id}, 'completed')"
                ${disabledAttr}
                aria-label="Mark ${escapeHtml(habit.name)} as completed">
                <i class="bi bi-check-lg"></i>
              </button>

              <!-- Mark Missed Button -->
              <button 
                type="button" 
                class="btn-status btn-status-missed ${habitStatus === 'missed' ? 'active' : ''}" 
                title="Mark Missed" 
                onclick="handleStatusChange(${habit.id}, 'missed')"
                ${disabledAttr}
                aria-label="Mark ${escapeHtml(habit.name)} as missed">
                <i class="bi bi-x-lg"></i>
              </button>

              <!-- Mark Skipped Button -->
              <button 
                type="button" 
                class="btn-status btn-status-skipped ${habitStatus === 'skipped' ? 'active' : ''}" 
                title="Mark Skipped" 
                onclick="handleStatusChange(${habit.id}, 'skipped')"
                ${disabledAttr}
                aria-label="Mark ${escapeHtml(habit.name)} as skipped">
                <i class="bi bi-pause-fill"></i>
              </button>

              <!-- Deactivate Habit Button -->
              <button 
                type="button" 
                class="btn-delete-habit ms-1" 
                title="Deactivate Habit" 
                onclick="deleteHabit(${habit.id})"
                ${disabledAttr}
                aria-label="Deactivate ${escapeHtml(habit.name)}">
                <i class="bi bi-trash3"></i>
              </button>
            </div>

          </div>
        </div>
      </div>
    `;
  }).join("");
}

// ----------------------------------------------------------------------------
// 5. STATUS CHANGE & HABIT ACTIONS VIA API
// ----------------------------------------------------------------------------

/**
 * Handles status clicks (completed, missed, skipped) and sends POST /api/records.
 * If user clicks the currently active status, resets the status to 'pending'.
 * Prevents duplicate submissions while a request is in progress.
 */
async function handleStatusChange(habitId, targetStatus) {
  // Prevent duplicate concurrent clicks on the same habit
  if (activeRecordRequests.has(habitId)) return;

  const habit = habits.find(h => h.id === habitId);
  if (!habit) return;

  const currentStatus = habit.status || "pending";
  // Toggle: clicking the active status resets it to pending
  const newStatus = (currentStatus === targetStatus) ? "pending" : targetStatus;
  const today = getTodayDateString();

  activeRecordRequests.add(habitId);
  renderHabits(); // Reflect busy state on buttons

  try {
    const response = await fetch("/api/records", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        habit_id: habitId,
        record_date: today,
        status: newStatus
      })
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.error || `Server error (${response.status})`);
    }

    const result = await response.json();

    // Update local habit state from verified database response
    habit.status = result.status || newStatus;
    if (typeof result.streak === "number") {
      habit.streak = result.streak;
    }

    // Update today's slot in 7-day mini history
    if (Array.isArray(habit.weeklyHistory) && habit.weeklyHistory.length > 0) {
      habit.weeklyHistory[habit.weeklyHistory.length - 1] = habit.status;
    } else if (Array.isArray(habit.weekly_history) && habit.weekly_history.length > 0) {
      habit.weekly_history[habit.weekly_history.length - 1] = habit.status;
    }

    // Friendly feedback toasts
    if (newStatus === "completed") {
      showToast(`Awesome! "${habit.name}" completed! 🔥`, "success");
    } else if (newStatus === "missed") {
      showToast(`Marked "${habit.name}" as missed for today.`, "warning");
    } else if (newStatus === "skipped") {
      showToast(`Skipped "${habit.name}" for today.`, "info");
    } else {
      showToast(`"${habit.name}" set back to Pending`, "info");
    }

    updateSummaryMetrics();
    updateCharts();
    loadInsightsFromApi(currentInsightsDays);
    loadCalendarHeatmap();
    loadWeeklyReview();
    loadGoalsAndMilestones();

  } catch (error) {
    console.error("Failed to update habit record:", error);
    showToast(`Could not update record: ${error.message}`, "danger");
  } finally {
    activeRecordRequests.delete(habitId);
    renderHabits();
  }
}

/**
 * Deactivates a habit using DELETE /api/habits/<id>.
 * Preserves past streak records in SQLite while removing it from active dashboard views.
 */
async function deleteHabit(habitId) {
  if (activeDeleteRequests.has(habitId)) return;

  const habit = habits.find(h => h.id === habitId);
  if (!habit) return;

  const confirmed = window.confirm(`Archive "${habit.name}"? Historical streaks will be preserved in SQLite.`);
  if (!confirmed) return;

  activeDeleteRequests.add(habitId);
  renderHabits();

  try {
    const response = await fetch(`/api/habits/${habitId}`, {
      method: "DELETE"
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.error || `Server error (${response.status})`);
    }

    // Remove from in-memory active habits list
    habits = habits.filter(h => h.id !== habitId);

    showToast(`Habit "${habit.name}" archived successfully.`, "secondary");
    updateSummaryMetrics();
    updateCharts();
    loadInsightsFromApi(currentInsightsDays);
    populateCalendarHabitSelect();
    populateGoalHabitSelect();
    loadCalendarHeatmap();
    loadWeeklyReview();
    loadGoalsAndMilestones();

  } catch (error) {
    console.error("Failed to deactivate habit:", error);
    showToast(`Could not archive habit: ${error.message}`, "danger");
  } finally {
    activeDeleteRequests.delete(habitId);
    renderHabits();
  }
}

// ----------------------------------------------------------------------------
// 6. ADD NEW HABIT FORM SUBMISSION
// ----------------------------------------------------------------------------
function setupEventListeners() {
  const addHabitForm = document.getElementById("addHabitForm");
  if (addHabitForm) {
    addHabitForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      if (isSubmittingHabit) return;

      const nameInput = document.getElementById("habitNameInput");
      const descInput = document.getElementById("habitDescriptionInput");
      const categorySelect = document.getElementById("habitCategorySelect");
      const timeOfDaySelect = document.getElementById("habitTimeOfDaySelect");
      const frequencySelect = document.getElementById("habitFrequencySelect");
      const targetTimeInput = document.getElementById("habitTargetTimeInput");
      const submitBtn = addHabitForm.querySelector("button[type='submit']");

      const name = nameInput ? nameInput.value.trim() : "";
      if (!name) {
        if (nameInput) nameInput.classList.add("is-invalid");
        return;
      }
      if (nameInput) nameInput.classList.remove("is-invalid");

      const rawTime = (targetTimeInput && targetTimeInput.value) ? targetTimeInput.value : "08:00";
      const formattedTime = formatTime12h(rawTime);

      const payload = {
        name: name,
        description: descInput ? descInput.value.trim() : "",
        category: categorySelect ? categorySelect.value : "Coding",
        time_of_day: timeOfDaySelect ? timeOfDaySelect.value : "Morning",
        target_frequency: frequencySelect ? frequencySelect.value : "Daily",
        target_time: formattedTime
      };

      // Set submission lock & loading UI state
      isSubmittingHabit = true;
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status"></span>Saving...`;
      }

      try {
        const response = await fetch("/api/habits", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });

        if (!response.ok) {
          const errData = await response.json().catch(() => ({}));
          throw new Error(errData.error || `Server error (${response.status})`);
        }

        const newHabit = await response.json();

        // Add newly created habit to local state
        habits.unshift(newHabit);

        // Reset form & close modal
        addHabitForm.reset();
        const modalEl = document.getElementById("addHabitModal");
        if (modalEl && typeof bootstrap !== "undefined" && bootstrap.Modal) {
          const modalInstance = bootstrap.Modal.getInstance(modalEl) || bootstrap.Modal.getOrCreateInstance(modalEl);
          if (modalInstance) modalInstance.hide();
        }

        showToast(`New habit "${newHabit.name}" created!`, "success");
        renderHabits();
        updateSummaryMetrics();
        updateCharts();
        loadInsightsFromApi(currentInsightsDays);
        populateCalendarHabitSelect();
        populateGoalHabitSelect();
        loadCalendarHeatmap();
        loadWeeklyReview();
        loadGoalsAndMilestones();

      } catch (error) {
        console.error("Failed to create habit:", error);
        showToast(`Could not create habit: ${error.message}`, "danger");
      } finally {
        isSubmittingHabit = false;
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.innerHTML = `<i class="bi bi-check-lg"></i> Save Habit`;
        }
      }
    });
  }

  // Configurable Insights Analysis Window Selector (Phase 3)
  const periodSelect = document.getElementById("insightsPeriodSelect");
  if (periodSelect) {
    periodSelect.addEventListener("change", (e) => {
      const val = parseInt(e.target.value, 10) || 30;
      currentInsightsDays = val;
      loadInsightsFromApi(val);
    });
  }

  // Filter Pill Buttons (All, Morning, Afternoon, Evening)
  const filterButtons = document.querySelectorAll(".filter-btn");
  filterButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      filterButtons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentFilter = btn.getAttribute("data-filter") || "all";
      renderHabits();
    });
  });
}

// ----------------------------------------------------------------------------
// 7. SUMMARY KPI METRIC CALCULATIONS
// ----------------------------------------------------------------------------
function updateSummaryMetrics() {
  const total = habits.length;
  const completed = habits.filter(h => h.status === "completed").length;
  const completionRate = total > 0 ? Math.round((completed / total) * 100) : 0;

  // Best streak calculation from database-backed streaks
  let maxStreak = 0;
  let topHabitName = "--";
  habits.forEach(h => {
    const s = typeof h.streak === "number" ? h.streak : 0;
    if (s > maxStreak) {
      maxStreak = s;
      topHabitName = h.name;
    }
  });

  // Top metric card DOM elements
  const statBestStreak = document.getElementById("statBestStreak");
  const statCompletionRate = document.getElementById("statCompletionRate");
  const statActiveHabits = document.getElementById("statActiveHabits");
  const statStrongestHabit = document.getElementById("statStrongestHabit");
  const statStrongestStreak = document.getElementById("statStrongestStreak");

  if (statBestStreak) statBestStreak.textContent = `${maxStreak} ${maxStreak === 1 ? "Day" : "Days"}`;
  if (statCompletionRate) statCompletionRate.textContent = `${completionRate}%`;
  if (statActiveHabits) statActiveHabits.textContent = total;
  if (statStrongestHabit) statStrongestHabit.textContent = topHabitName;
  if (statStrongestStreak) {
    statStrongestStreak.innerHTML = `<i class="bi bi-trophy-fill me-1"></i>${maxStreak} Day Record`;
  }

  // Hero Banner Progress Bar
  const bannerProgressLabel = document.getElementById("bannerProgressLabel");
  const bannerProgressBar = document.getElementById("bannerProgressBar");
  const bannerMotivationText = document.getElementById("bannerMotivationText");

  if (bannerProgressLabel) {
    bannerProgressLabel.textContent = `${completed} of ${total} Completed (${completionRate}%)`;
  }
  if (bannerProgressBar) {
    bannerProgressBar.style.width = `${completionRate}%`;
    bannerProgressBar.setAttribute("aria-valuenow", completionRate);
  }
  if (bannerMotivationText) {
    if (total === 0) {
      bannerMotivationText.textContent = "Click 'Add Habit' above to start tracking your daily patterns!";
    } else if (completionRate === 100) {
      bannerMotivationText.textContent = "All habits completed today! Outstanding streak! 🎉";
    } else if (completionRate >= 50) {
      bannerMotivationText.textContent = "More than halfway done! Keep the momentum flowing.";
    } else {
      bannerMotivationText.textContent = "Complete your next habit to boost today's consistency score!";
    }
  }

  // Update time of day distribution badges
  const morningCount = habits.filter(h => (h.timeOfDay || h.time_of_day || "").toLowerCase() === "morning").length;
  const afternoonCount = habits.filter(h => (h.timeOfDay || h.time_of_day || "").toLowerCase() === "afternoon").length;
  const eveningCount = habits.filter(h => (h.timeOfDay || h.time_of_day || "").toLowerCase() === "evening").length;

  const mEl = document.getElementById("morningCountBadge");
  const aEl = document.getElementById("afternoonCountBadge");
  const eEl = document.getElementById("eveningCountBadge");
  if (mEl) mEl.textContent = morningCount;
  if (aEl) aEl.textContent = afternoonCount;
  if (eEl) eEl.textContent = eveningCount;
}

// ----------------------------------------------------------------------------
// 8. INTERACTIVE PROGRESS CHARTS (CHART.JS)
// ----------------------------------------------------------------------------
function initCharts() {
  if (typeof Chart === "undefined") {
    console.warn("Chart.js is not loaded yet.");
    return;
  }

  // Generate dynamic day-name labels for the past 7 days ending with 'Today'
  const past7Labels = getPast7DaysLabels();

  // 1. Weekly Consistency Bar Chart
  const weeklyCtx = document.getElementById("weeklyChart");
  if (weeklyCtx) {
    const weeklyData = calculateWeeklyConsistency();
    weeklyChartInstance = new Chart(weeklyCtx, {
      type: "bar",
      data: {
        labels: past7Labels,
        datasets: [{
          label: "Habits Completed",
          data: weeklyData,
          backgroundColor: "#4f46e5",
          borderRadius: 6,
          barPercentage: 0.55
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: "#0f172a",
            padding: 10,
            cornerRadius: 8
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: { stepSize: 1, precision: 0, color: "#94a3b8" },
            grid: { color: "#f1f5f9" }
          },
          x: {
            grid: { display: false },
            ticks: { color: "#64748b", font: { weight: 500 } }
          }
        }
      }
    });
  }

  // 2. Time-of-Day Distribution Doughnut Chart
  const timeCtx = document.getElementById("timeOfDayChart");
  if (timeCtx) {
    const timeData = getTimeDistributionData();
    timeOfDayChartInstance = new Chart(timeCtx, {
      type: "doughnut",
      data: {
        labels: ["Morning", "Afternoon", "Evening"],
        datasets: [{
          data: timeData,
          backgroundColor: ["#f59e0b", "#3b82f6", "#8b5cf6"],
          borderWidth: 0,
          hoverOffset: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "70%",
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: "#0f172a",
            padding: 8,
            cornerRadius: 8
          }
        }
      }
    });
  }
}

/**
 * Returns dynamic day abbreviations for the last 7 days ending with 'Today'.
 */
function getPast7DaysLabels() {
  const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  const labels = [];
  const now = new Date();
  for (let i = 6; i >= 1; i--) {
    const past = new Date(now);
    past.setDate(now.getDate() - i);
    labels.push(days[past.getDay()]);
  }
  labels.push("Today");
  return labels;
}

/**
 * Recalculates chart datasets and updates active Chart.js instances.
 * Fetches real SQLite analytics over 7 days, falling back to local calculation if offline.
 */
async function updateCharts() {
  try {
    const today = getTodayDateString();
    const res = await fetch(`/api/analytics?days=7&date=${encodeURIComponent(today)}`);
    if (res.ok) {
      const data = await res.json();
      if (weeklyChartInstance && Array.isArray(data.daily_trend)) {
        weeklyChartInstance.data.datasets[0].data = data.daily_trend.map(d => d.completed);
        weeklyChartInstance.update();
      }
      if (timeOfDayChartInstance && data.time_of_day_distribution) {
        const tod = data.time_of_day_distribution;
        timeOfDayChartInstance.data.datasets[0].data = [
          tod.Morning ? tod.Morning.total : 0,
          tod.Afternoon ? tod.Afternoon.total : 0,
          tod.Evening ? tod.Evening.total : 0
        ];
        timeOfDayChartInstance.update();
      }
      return;
    }
  } catch (err) {
    console.warn("Analytics fetch fallback to local calculation:", err);
  }

  // Fallback to in-memory calculation if analytics endpoint is unreachable
  if (weeklyChartInstance) {
    weeklyChartInstance.data.datasets[0].data = calculateWeeklyConsistency();
    weeklyChartInstance.update();
  }

  if (timeOfDayChartInstance) {
    timeOfDayChartInstance.data.datasets[0].data = getTimeDistributionData();
    timeOfDayChartInstance.update();
  }
}

/**
 * Calculates completed habits count across each of the past 7 days from habit weekly histories.
 */
function calculateWeeklyConsistency() {
  const dayCounts = [0, 0, 0, 0, 0, 0, 0];

  habits.forEach(h => {
    const history = Array.isArray(h.weeklyHistory)
      ? h.weeklyHistory
      : (Array.isArray(h.weekly_history) ? h.weekly_history : []);

    history.forEach((status, i) => {
      if (i < 7 && (status === "done" || status === "completed")) {
        dayCounts[i] += 1;
      }
    });
  });

  // Ensure index 6 (Today) reflects real-time today status
  const todayCompleted = habits.filter(h => h.status === "completed").length;
  dayCounts[6] = todayCompleted;

  return dayCounts;
}

/**
 * Returns array of habit counts for [Morning, Afternoon, Evening].
 */
function getTimeDistributionData() {
  const m = habits.filter(h => (h.timeOfDay || h.time_of_day || "").toLowerCase() === "morning").length;
  const a = habits.filter(h => (h.timeOfDay || h.time_of_day || "").toLowerCase() === "afternoon").length;
  const e = habits.filter(h => (h.timeOfDay || h.time_of_day || "").toLowerCase() === "evening").length;
  // If all are zero, return [0, 0, 0]
  return [m, a, e];
}

// ----------------------------------------------------------------------------
// 9. HELPER UTILITIES
// ----------------------------------------------------------------------------

/**
 * Shows a toast message at the bottom right.
 */
function showToast(message, type = "success") {
  const toastEl = document.getElementById("actionToast");
  const toastMsg = document.getElementById("toastMessage");
  const toastIcon = document.getElementById("toastIcon");

  if (!toastEl || !toastMsg) return;

  toastMsg.textContent = message;

  // Set appropriate icon & color
  if (toastIcon) {
    toastIcon.className = "bi fs-5 ";
    if (type === "success") {
      toastIcon.className += "bi-check-circle-fill text-success";
    } else if (type === "warning") {
      toastIcon.className += "bi-exclamation-circle-fill text-warning";
    } else if (type === "info") {
      toastIcon.className += "bi-info-circle-fill text-info";
    } else if (type === "danger") {
      toastIcon.className += "bi-x-circle-fill text-danger";
    } else {
      toastIcon.className += "bi-trash-fill text-secondary";
    }
  }

  const toastInstance = new bootstrap.Toast(toastEl, { delay: 3500 });
  toastInstance.show();
}

/**
 * Converts 24h string "14:30" to 12h string "02:30 PM".
 */
function formatTime12h(timeStr) {
  if (!timeStr) return "08:00 AM";
  const parts = timeStr.split(":");
  if (parts.length < 2) return timeStr;
  let hour = parseInt(parts[0], 10);
  const minutes = parts[1];
  const ampm = hour >= 12 ? "PM" : "AM";
  hour = hour % 12;
  hour = hour ? hour : 12; // 0 hour should be 12
  const formattedHour = hour < 10 ? `0${hour}` : hour;
  return `${formattedHour}:${minutes} ${ampm}`;
}

/**
 * Escapes HTML to prevent XSS.
 */
function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// ----------------------------------------------------------------------------
// 10. HABIT PATTERN DETECTOR & AI EXPLANATIONS (PHASE 4: HYBRID AI)
// ----------------------------------------------------------------------------

/**
 * Loads pattern explanations from the Flask API (GET /api/insights/explanations).
 * Fallbacks cleanly to /api/insights if the explanations endpoint is unreachable.
 */
async function loadInsightsFromApi(days = 30) {
  const container = document.getElementById("insightsContainer");
  const periodSpan = document.getElementById("insightsPeriodSpan");
  const metaSpan = document.getElementById("insightsMetaSpan");
  const sourceBadge = document.getElementById("insightsSourceBadge");

  if (periodSpan) {
    periodSpan.textContent = `Window: ${days} Days`;
  }

  if (container) {
    container.innerHTML = `
      <div class="text-center py-4 text-muted small">
        <span class="spinner-border spinner-border-sm text-primary me-2" role="status"></span>
        <span>Analyzing habit patterns with AI explainer...</span>
      </div>
    `;
  }

  try {
    const today = getTodayDateString();
    let response = await fetch(`/api/insights/explanations?days=${encodeURIComponent(days)}&date=${encodeURIComponent(today)}`);

    // Graceful backward compatibility fallback
    if (!response.ok && response.status === 404) {
      response = await fetch(`/api/insights?days=${encodeURIComponent(days)}&date=${encodeURIComponent(today)}`);
    }

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.error || `Server returned HTTP ${response.status}`);
    }

    const data = await response.json();

    // Update statistical summary in card footer
    if (metaSpan && data.summary) {
      const s = data.summary;
      metaSpan.innerHTML = `
        <i class="bi bi-shield-check text-success me-1"></i>${s.total_completed || 0} done / ${s.total_missed || 0} missed (${s.overall_completion_rate || 0}%)
      `;
    }

    // Update source badge in card footer
    if (sourceBadge) {
      if (data.source === "ai") {
        const prov = escapeHtml(data.provider || "AI");
        sourceBadge.className = "badge bg-purple-subtle text-purple border border-purple-subtle rounded-pill";
        sourceBadge.innerHTML = `<i class="bi bi-stars me-1"></i>AI (${prov})`;
      } else {
        sourceBadge.className = "badge bg-light text-muted border rounded-pill";
        sourceBadge.innerHTML = `<i class="bi bi-shield-check text-success me-1"></i>Rule Engine`;
      }
    }

    // Prioritize explanations array, fallback to insights array
    const items = data.explanations || data.insights || [];
    renderInsights(items, days);

  } catch (error) {
    console.error("StreakLab: Could not load pattern explanations:", error);
    if (container) {
      container.innerHTML = `
        <div class="alert alert-warning p-3 rounded-3 small mb-0 d-flex flex-column flex-sm-row justify-content-between align-items-sm-center gap-2">
          <div>
            <i class="bi bi-exclamation-triangle-fill text-warning me-1"></i>
            <span>Unable to load habit patterns.</span>
          </div>
          <button class="btn btn-sm btn-outline-dark rounded-pill px-3 py-1" onclick="loadInsightsFromApi(${days})">
            <i class="bi bi-arrow-clockwise me-1"></i>Retry
          </button>
        </div>
      `;
    }
  }
}

/**
 * Renders detected patterns and evidence-grounded explanations.
 * Escapes all untrusted text to prevent XSS. Displays source badges,
 * confidence levels, evidence summaries, and practical recommendations.
 */
function renderInsights(itemsList, periodDays = 30) {
  const container = document.getElementById("insightsContainer");
  if (!container) return;

  if (!Array.isArray(itemsList) || itemsList.length === 0) {
    container.innerHTML = `
      <div class="text-center py-4 text-muted small">
        <i class="bi bi-clipboard-data fs-3 d-block mb-2 text-primary opacity-50"></i>
        <div class="fw-semibold text-dark">No Patterns Detected Yet</div>
        <div class="text-muted">Keep checking in daily to discover your routine rhythms.</div>
      </div>
    `;
    return;
  }

  // Visual type styling map
  const typeIcons = {
    "strong_routine": { icon: "bi-graph-up-arrow text-success", border: "border-success-subtle" },
    "at_risk_habit": { icon: "bi-exclamation-triangle text-danger", border: "border-danger-subtle" },
    "weekday_dropoff": { icon: "bi-calendar-x text-warning", border: "border-warning-subtle" },
    "peak_performance_day": { icon: "bi-award-fill text-primary", border: "border-primary-subtle" },
    "time_of_day_preference": { icon: "bi-clock-history text-indigo", border: "border-indigo-subtle" },
    "repeated_misses": { icon: "bi-arrow-repeat text-danger", border: "border-danger-subtle" },
    "streak_milestone": { icon: "bi-fire text-orange", border: "border-warning-subtle" },
    "insufficient_data": { icon: "bi-hourglass-split text-primary", border: "border-primary-subtle" },
    "no_habits": { icon: "bi-plus-circle text-primary", border: "border-primary-subtle" }
  };

  const confidenceBadges = {
    "high": `<span class="badge bg-success-subtle text-success border border-success-subtle rounded-pill small" title="Substantial sample size">High Confidence</span>`,
    "medium": `<span class="badge bg-warning-subtle text-warning-emphasis border border-warning-subtle rounded-pill small" title="Moderate sample size">Medium Confidence</span>`,
    "low": `<span class="badge bg-secondary-subtle text-secondary border border-secondary-subtle rounded-pill small" title="Initial observations">Low Confidence</span>`
  };

  container.innerHTML = itemsList.map(item => {
    const pType = item.pattern_type || item.type || "unknown";
    const config = typeIcons[pType] || { icon: "bi-lightbulb-fill text-primary", border: "border" };
    const confBadge = confidenceBadges[item.confidence] || confidenceBadges["low"];

    // Source badge: AI vs Rule-based
    const isAi = (item.source === "ai");
    const sourceBadge = isAi
      ? `<span class="badge bg-purple-subtle text-purple border border-purple-subtle rounded-pill small" title="Explained by AI using SQLite evidence"><i class="bi bi-stars me-1"></i>AI</span>`
      : `<span class="badge bg-light text-muted border rounded-pill small" title="Rule-based deterministic engine"><i class="bi bi-shield-check text-success me-1"></i>Rule</span>`;

    // Supporting Evidence string
    let evidenceHtml = "";
    if (item.evidence_summary) {
      evidenceHtml = `
        <div class="d-flex flex-wrap align-items-center gap-2 mt-2 pt-1 small text-muted">
          <span class="badge bg-light text-dark border"><i class="bi bi-bar-chart me-1"></i>Evidence:</span>
          <span>${escapeHtml(item.evidence_summary)}</span>
        </div>
      `;
    } else if (item.evidence) {
      const ev = item.evidence;
      const bits = [];
      if (typeof ev.completion_rate === "number") bits.push(`Rate: <strong>${ev.completion_rate}%</strong>`);
      if (typeof ev.completed === "number" && typeof ev.missed === "number") bits.push(`${ev.completed} done / ${ev.missed} missed`);
      if (typeof ev.consecutive_misses === "number") bits.push(`<strong>${ev.consecutive_misses} misses in a row</strong>`);
      if (typeof ev.sample_size === "number") bits.push(`Sample: ${ev.sample_size} check-ins`);
      if (typeof ev.rate_difference === "number") bits.push(`Gap: +${ev.rate_difference}%`);

      if (bits.length > 0) {
        evidenceHtml = `
          <div class="d-flex flex-wrap align-items-center gap-2 mt-2 pt-1 small text-muted">
            <span class="badge bg-light text-dark border"><i class="bi bi-bar-chart me-1"></i>Evidence:</span>
            <span>${bits.join(" &bull; ")}</span>
          </div>
        `;
      }
    }

    const mainText = item.explanation || item.message || "";
    const recText = item.recommendation || "";

    return `
      <div class="insight-item p-3 rounded-3 bg-white border ${config.border} shadow-sm">
        <div class="d-flex align-items-start justify-content-between gap-2 mb-1 flex-wrap">
          <div class="d-flex align-items-center gap-2">
            <i class="bi ${config.icon} fs-5"></i>
            <h6 class="fw-bold mb-0 text-dark small">${escapeHtml(item.title || "Habit Pattern")}</h6>
          </div>
          <div class="d-flex align-items-center gap-1">
            ${sourceBadge}
            ${confBadge}
          </div>
        </div>
        <p class="text-muted small mb-0 mt-1">${escapeHtml(mainText)}</p>
        ${evidenceHtml}
        ${recText ? `
          <div class="mt-2 pt-2 border-top small text-muted">
            <strong class="text-dark"><i class="bi bi-lightbulb text-warning me-1"></i>Recommendation:</strong>
            ${escapeHtml(recText)}
          </div>
        ` : ""}
      </div>
    `;
  }).join("");
}

// ============================================================================
// PHASE 6: STREAKLAB AI HABIT COACH CHATBOX CLIENT LOGIC
// ============================================================================

let chatHistory = [];
let isChatOpen = false;
let isChatSending = false;
let lastUserMessage = "";

/**
 * Initializes the AI Habit Coach chat panel, event listeners, and chips.
 */
function initChatCoach() {
  const launcherBtn = document.getElementById("chatLauncherBtn");
  const closeBtn = document.getElementById("chatCloseBtn");
  const clearBtn = document.getElementById("chatClearBtn");
  const chatForm = document.getElementById("chatForm");
  const chatInput = document.getElementById("chatInput");
  const chipsContainer = document.getElementById("chatChipsContainer");

  if (!launcherBtn) return;

  // Toggle chat panel visibility
  launcherBtn.addEventListener("click", () => {
    toggleChatPanel();
  });

  // Close chat panel button
  if (closeBtn) {
    closeBtn.addEventListener("click", () => {
      closeChatPanel();
    });
  }

  // Clear chat history
  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      clearChatHistory();
    });
  }

  // Handle form submission
  if (chatForm) {
    chatForm.addEventListener("submit", (e) => {
      e.preventDefault();
      submitChatMessage();
    });
  }

  // Textarea: Enter to send, Shift+Enter for new line
  if (chatInput) {
    chatInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        submitChatMessage();
      }
    });

    // Auto-expand textarea height slightly as user types
    chatInput.addEventListener("input", () => {
      chatInput.style.height = "auto";
      chatInput.style.height = Math.min(chatInput.scrollHeight, 100) + "px";
    });
  }

  // Quick question chips
  if (chipsContainer) {
    chipsContainer.addEventListener("click", (e) => {
      const chip = e.target.closest(".chat-chip-btn");
      if (!chip) return;
      const query = chip.getAttribute("data-query");
      if (query && !isChatSending) {
        sendChatMessage(query);
      }
    });
  }
}

/**
 * Opens or closes the floating chat panel.
 */
function toggleChatPanel() {
  const panel = document.getElementById("chatPanel");
  const launcher = document.getElementById("chatLauncherBtn");
  const openIcon = launcher ? launcher.querySelector(".chat-icon-open") : null;
  const closeIcon = launcher ? launcher.querySelector(".chat-icon-close") : null;
  const chatInput = document.getElementById("chatInput");

  if (!panel) return;

  isChatOpen = !isChatOpen;
  if (isChatOpen) {
    panel.classList.remove("d-none");
    if (openIcon) openIcon.classList.add("d-none");
    if (closeIcon) closeIcon.classList.remove("d-none");
    scrollChatToBottom();
    setTimeout(() => {
      if (chatInput && window.innerWidth > 576) chatInput.focus();
    }, 150);
  } else {
    panel.classList.add("d-none");
    if (openIcon) openIcon.classList.remove("d-none");
    if (closeIcon) closeIcon.classList.add("d-none");
  }
}

/**
 * Closes the floating chat panel.
 */
function closeChatPanel() {
  const panel = document.getElementById("chatPanel");
  const launcher = document.getElementById("chatLauncherBtn");
  const openIcon = launcher ? launcher.querySelector(".chat-icon-open") : null;
  const closeIcon = launcher ? launcher.querySelector(".chat-icon-close") : null;

  if (!panel) return;
  isChatOpen = false;
  panel.classList.add("d-none");
  if (openIcon) openIcon.classList.remove("d-none");
  if (closeIcon) closeIcon.classList.add("d-none");
}

/**
 * Clears the chat conversation history and resets to initial welcome message.
 */
function clearChatHistory() {
  chatHistory = [];
  lastUserMessage = "";
  const messagesContainer = document.getElementById("chatMessages");
  if (!messagesContainer) return;

  // Retain only welcome message and suggestions
  messagesContainer.innerHTML = `
    <div class="chat-msg coach">
      <div class="chat-msg-avatar">
        <i class="bi bi-robot"></i>
      </div>
      <div class="chat-msg-content">
        <div class="chat-bubble coach-bubble">
          <div class="chat-bubble-text">
            👋 <strong>Conversation reset!</strong><br><br>
            I'm ready with your latest habit records. Ask me anything about your current progress or routine!
          </div>
          <div class="chat-bubble-meta mt-2">
            <span class="badge bg-light text-muted border rounded-pill small"><i class="bi bi-shield-check text-success me-1"></i>StreakLab Coach</span>
          </div>
        </div>
      </div>
    </div>
    <div id="chatChipsContainer" class="chat-chips-container my-2">
      <small class="text-muted d-block mb-1 px-1 fw-semibold fs-xs">SUGGESTED QUESTIONS</small>
      <div class="d-flex flex-wrap gap-1">
        <button type="button" class="chat-chip-btn" data-query="How are my habits going this week?">
          📊 How are my habits going this week?
        </button>
        <button type="button" class="chat-chip-btn" data-query="Which habit needs the most attention?">
          ⚠️ Which habit needs attention?
        </button>
        <button type="button" class="chat-chip-btn" data-query="What patterns have you detected in my routine?">
          🔍 What patterns have you detected?
        </button>
        <button type="button" class="chat-chip-btn" data-query="Suggest a realistic plan to improve my consistency.">
          🎯 Suggest a plan to improve
        </button>
        <button type="button" class="chat-chip-btn" data-query="Compare my recent performance with my earlier records.">
          📈 Compare recent vs earlier
        </button>
      </div>
    </div>
  `;
}

/**
 * Handles sending chat messages from input field.
 */
function submitChatMessage() {
  const input = document.getElementById("chatInput");
  if (!input || isChatSending) return;

  const text = input.value.trim();
  if (!text) return;

  input.value = "";
  input.style.height = "auto";
  sendChatMessage(text);
}

/**
 * Formats untrusted message text into safe DOM nodes.
 * Avoids innerHTML for XSS safety while supporting paragraph breaks,
 * bullet points, and **bold** markdown formatting.
 */
function appendSafeFormattedText(container, rawText) {
  if (!rawText) return;

  const lines = String(rawText).split("\n");
  lines.forEach((line, lineIndex) => {
    if (lineIndex > 0) {
      container.appendChild(document.createElement("br"));
    }

    // Split line by bold delimiters (**text**)
    const parts = line.split(/(\*\*[^*]+\*\*)/g);
    parts.forEach(part => {
      if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
        const strong = document.createElement("strong");
        strong.textContent = part.slice(2, -2);
        container.appendChild(strong);
      } else if (part) {
        container.appendChild(document.createTextNode(part));
      }
    });
  });
}

/**
 * Appends a safe message bubble to the chat message container.
 */
function appendChatBubble(role, text, source, evidence = [], isError = false) {
  const container = document.getElementById("chatMessages");
  if (!container) return;

  const msgDiv = document.createElement("div");
  msgDiv.className = `chat-msg ${role === "user" ? "user" : "coach"}`;

  // Avatar for coach
  if (role !== "user") {
    const avatar = document.createElement("div");
    avatar.className = "chat-msg-avatar";
    const icon = document.createElement("i");
    icon.className = isError ? "bi bi-exclamation-triangle-fill text-danger" : "bi bi-robot";
    avatar.appendChild(icon);
    msgDiv.appendChild(avatar);
  }

  const contentDiv = document.createElement("div");
  contentDiv.className = "chat-msg-content";

  const bubbleDiv = document.createElement("div");
  bubbleDiv.className = `chat-bubble ${role === "user" ? "user-bubble" : "coach-bubble"}`;
  if (isError) {
    bubbleDiv.classList.add("border-danger-subtle", "bg-danger-subtle", "text-danger");
  }

  const textDiv = document.createElement("div");
  textDiv.className = "chat-bubble-text";
  appendSafeFormattedText(textDiv, text);
  bubbleDiv.appendChild(textDiv);

  // Evidence chips if provided
  if (Array.isArray(evidence) && evidence.length > 0) {
    const evDiv = document.createElement("div");
    evDiv.className = "chat-evidence-tags";
    evidence.forEach(item => {
      if (item && item.label && item.value !== undefined) {
        const badge = document.createElement("span");
        badge.className = "badge";
        badge.textContent = `${item.label}: ${item.value}`;
        evDiv.appendChild(badge);
      }
    });
    bubbleDiv.appendChild(evDiv);
  }

  // Meta label (source indicator)
  if (role !== "user") {
    const metaDiv = document.createElement("div");
    metaDiv.className = "chat-bubble-meta";

    const badge = document.createElement("span");
    badge.className = "badge border rounded-pill small";

    if (isError) {
      badge.className += " bg-danger text-white";
      badge.textContent = "Error";
    } else if (source === "ai") {
      badge.className += " bg-purple-subtle text-purple border-purple-subtle";
      const icon = document.createElement("i");
      icon.className = "bi bi-stars me-1";
      badge.appendChild(icon);
      badge.appendChild(document.createTextNode("AI Powered"));
    } else {
      badge.className += " bg-light text-muted";
      const icon = document.createElement("i");
      icon.className = "bi bi-shield-check text-success me-1";
      badge.appendChild(icon);
      badge.appendChild(document.createTextNode("Fallback Coach"));
    }
    metaDiv.appendChild(badge);

    // If error, add a retry button
    if (isError && lastUserMessage) {
      const retryBtn = document.createElement("button");
      retryBtn.className = "btn btn-xs btn-outline-danger rounded-pill px-2 py-0 ms-1";
      retryBtn.style.fontSize = "0.7rem";
      retryBtn.textContent = "Retry";
      retryBtn.onclick = () => {
        sendChatMessage(lastUserMessage);
      };
      metaDiv.appendChild(retryBtn);
    }

    bubbleDiv.appendChild(metaDiv);
  }

  contentDiv.appendChild(bubbleDiv);
  msgDiv.appendChild(contentDiv);
  container.appendChild(msgDiv);

  scrollChatToBottom();
}

/**
 * Scrolls the chat messages container to the bottom.
 */
function scrollChatToBottom() {
  const container = document.getElementById("chatMessages");
  if (container) {
    container.scrollTop = container.scrollHeight;
  }
}

/**
 * Sends a message to the backend /api/chat endpoint.
 */
async function sendChatMessage(message) {
  if (isChatSending || !message.trim()) return;

  const trimmed = message.trim();
  lastUserMessage = trimmed;
  isChatSending = true;

  const input = document.getElementById("chatInput");
  const sendBtn = document.getElementById("chatSendBtn");
  const typingIndicator = document.getElementById("chatTypingIndicator");
  const providerIndicator = document.getElementById("chatProviderIndicator");

  if (sendBtn) sendBtn.disabled = true;
  if (input) input.disabled = true;
  if (typingIndicator) typingIndicator.classList.remove("d-none");

  // Render user bubble
  appendChatBubble("user", trimmed);

  // Add to bounded in-memory session history
  chatHistory.push({ role: "user", content: trimmed });
  if (chatHistory.length > 16) {
    chatHistory = chatHistory.slice(-16);
  }

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        message: trimmed,
        history: chatHistory.slice(-10)
      })
    });

    const data = await response.json();

    if (!response.ok) {
      const errMsg = (data && data.error) ? data.error : `Server returned HTTP ${response.status}`;
      appendChatBubble("coach", errMsg, "fallback", [], true);
      return;
    }

    const reply = data.reply || "I couldn't generate a response for that query.";
    const source = data.source || "fallback";
    const evidence = data.evidence || [];
    const provider = data.provider || "local_fallback";

    // Add assistant reply to bounded history
    chatHistory.push({ role: "assistant", content: reply });

    // Render coach bubble safely
    appendChatBubble("coach", reply, source, evidence, false);

    // Update status badge
    if (providerIndicator) {
      if (source === "ai") {
        providerIndicator.textContent = provider.toUpperCase() + " AI";
        providerIndicator.className = "badge bg-purple-subtle text-purple border border-purple-subtle fs-xxs";
      } else {
        providerIndicator.textContent = "Offline Coach";
        providerIndicator.className = "badge bg-light text-muted border fs-xxs";
      }
    }

  } catch (err) {
    console.error("Chat request failed:", err);
    appendChatBubble("coach", "Connection error. Unable to reach StreakLab server. Please check your connection and try again.", "fallback", [], true);
  } finally {
    isChatSending = false;
    if (sendBtn) sendBtn.disabled = false;
    if (input) {
      input.disabled = false;
      if (window.innerWidth > 576) input.focus();
    }
    if (typingIndicator) typingIndicator.classList.add("d-none");
    scrollChatToBottom();
  }
}

// ----------------------------------------------------------------------------
// 12. PHASE 7: HABIT CALENDAR HEATMAP, WEEKLY REVIEW & GOALS
// ----------------------------------------------------------------------------

/**
 * Initializes Phase 7 modules (Calendar, Weekly Review, Goals).
 */
function initPhase7() {
  const now = new Date();
  currentCalendarYear = now.getFullYear();
  currentCalendarMonth = now.getMonth() + 1;

  setupPhase7EventListeners();
}

/**
 * Sets up user event listeners for Phase 7 controls.
 */
function setupPhase7EventListeners() {
  // Calendar month buttons
  const prevBtn = document.getElementById("calendarPrevMonthBtn");
  if (prevBtn) {
    prevBtn.addEventListener("click", () => {
      currentCalendarMonth -= 1;
      if (currentCalendarMonth < 1) {
        currentCalendarMonth = 12;
        currentCalendarYear -= 1;
      }
      loadCalendarHeatmap();
    });
  }

  const nextBtn = document.getElementById("calendarNextMonthBtn");
  if (nextBtn) {
    nextBtn.addEventListener("click", () => {
      currentCalendarMonth += 1;
      if (currentCalendarMonth > 12) {
        currentCalendarMonth = 1;
        currentCalendarYear += 1;
      }
      loadCalendarHeatmap();
    });
  }

  const monthLabel = document.getElementById("calendarMonthLabel");
  if (monthLabel) {
    monthLabel.addEventListener("click", () => {
      const now = new Date();
      currentCalendarYear = now.getFullYear();
      currentCalendarMonth = now.getMonth() + 1;
      loadCalendarHeatmap();
    });
  }

  // Calendar habit filter select
  const calHabitSelect = document.getElementById("calendarHabitSelect");
  if (calHabitSelect) {
    calHabitSelect.addEventListener("change", (e) => {
      currentCalendarHabitId = e.target.value;
      loadCalendarHeatmap();
    });
  }

  // Weekly review refresh
  const refreshReviewBtn = document.getElementById("btnRefreshWeeklyReview");
  if (refreshReviewBtn) {
    refreshReviewBtn.addEventListener("click", () => {
      loadWeeklyReview();
    });
  }

  // Goal range slider
  const rangeInput = document.getElementById("goalTargetValueRange");
  const displaySpan = document.getElementById("goalTargetValueDisplay");
  if (rangeInput && displaySpan) {
    rangeInput.addEventListener("input", (e) => {
      const val = e.target.value;
      displaySpan.textContent = `${val} ${val == 1 ? "day" : "days"}`;
    });
  }

  // Populate habits when Set Goal modal opens
  const setGoalModal = document.getElementById("setGoalModal");
  if (setGoalModal) {
    setGoalModal.addEventListener("show.bs.modal", () => {
      populateGoalHabitSelect();
    });
  }

  // Set goal form submission
  const setGoalForm = document.getElementById("setGoalForm");
  if (setGoalForm) {
    setGoalForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const habitSelect = document.getElementById("goalHabitSelect");
      const rangeVal = rangeInput ? parseInt(rangeInput.value, 10) : 5;
      const submitBtn = document.getElementById("btnSaveGoal");

      const habitId = habitSelect ? parseInt(habitSelect.value, 10) : null;
      if (!habitId) {
        if (habitSelect) habitSelect.classList.add("is-invalid");
        return;
      }
      if (habitSelect) habitSelect.classList.remove("is-invalid");

      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>Saving...`;
      }

      try {
        const res = await fetch("/api/goals", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ habit_id: habitId, target_value: rangeVal })
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.error || `Server error (${res.status})`);
        }

        const saved = await res.json();
        showToast(`Target set: ${saved.target_value} days/week for "${saved.habit_name}"! 🎯`, "success");

        // Close modal
        if (typeof bootstrap !== "undefined" && bootstrap.Modal) {
          const inst = bootstrap.Modal.getInstance(setGoalModal) || bootstrap.Modal.getOrCreateInstance(setGoalModal);
          if (inst) inst.hide();
        }

        loadGoalsAndMilestones();
      } catch (err) {
        console.error("Failed to save goal:", err);
        showToast(`Could not save goal: ${err.message}`, "danger");
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.innerHTML = `<i class="bi bi-check-lg"></i> Save Target`;
        }
      }
    });
  }
}

/**
 * Populates dropdown options for the calendar and goal modals.
 */
function populateCalendarHabitSelect() {
  const select = document.getElementById("calendarHabitSelect");
  if (!select) return;

  const currentVal = select.value;
  let html = `<option value="">All Active Habits</option>`;
  habits.forEach(h => {
    html += `<option value="${h.id}">${escapeHtml(h.name)}</option>`;
  });
  select.innerHTML = html;
  if (currentVal) select.value = currentVal;
}

function populateGoalHabitSelect() {
  const select = document.getElementById("goalHabitSelect");
  if (!select) return;

  if (habits.length === 0) {
    select.innerHTML = `<option value="">No active habits available</option>`;
    return;
  }

  let html = `<option value="">-- Choose a habit --</option>`;
  habits.forEach(h => {
    html += `<option value="${h.id}">${escapeHtml(h.name)} (${escapeHtml(h.category || "General")})</option>`;
  });
  select.innerHTML = html;
}

/**
 * Loads calendar heatmap records for the specified month.
 */
async function loadCalendarHeatmap() {
  const container = document.getElementById("calendarGrid");
  const monthLabel = document.getElementById("calendarMonthLabel");

  if (!currentCalendarYear || !currentCalendarMonth) {
    const now = new Date();
    currentCalendarYear = now.getFullYear();
    currentCalendarMonth = now.getMonth() + 1;
  }

  const monthParam = `${currentCalendarYear}-${String(currentCalendarMonth).padStart(2, "0")}`;
  const habitParam = currentCalendarHabitId ? `&habit_id=${encodeURIComponent(currentCalendarHabitId)}` : "";

  try {
    const res = await fetch(`/api/calendar?month=${monthParam}${habitParam}`);
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }
    const data = await res.json();
    currentCalendarData = data;

    if (monthLabel) {
      monthLabel.textContent = data.month_name || monthParam;
    }

    renderCalendarHeatmap(data);
  } catch (err) {
    console.error("Failed to load calendar heatmap:", err);
    if (container) {
      container.innerHTML = `
        <div class="col-12 text-center py-4 text-muted small">
          <i class="bi bi-exclamation-triangle text-warning me-1"></i>
          Unable to load calendar heatmap. <button class="btn btn-sm btn-link p-0" onclick="loadCalendarHeatmap()">Retry</button>
        </div>
      `;
    }
  }
}

/**
 * Renders calendar heatmap grid days.
 */
function renderCalendarHeatmap(data) {
  const container = document.getElementById("calendarGrid");
  if (!container || !data || !Array.isArray(data.days)) return;

  const firstWeekday = typeof data.first_weekday === "number" ? data.first_weekday : 0; // 0 = Mon
  const days = data.days;

  let html = "";

  // 1. Leading empty cells for days before the 1st
  for (let i = 0; i < firstWeekday; i++) {
    html += `<div class="calendar-cell cell-future" aria-hidden="true" style="opacity: 0.15;"></div>`;
  }

  // 2. Day cells
  days.forEach(d => {
    const status = d.dominant_status || "unrecorded";
    const statusClass = `cell-${status}`;
    const todayClass = d.is_today ? "cell-today" : "";
    const futureClass = d.is_future ? "cell-future" : "";

    let statusText = status.charAt(0).toUpperCase() + status.slice(1);
    let accessibleLabel = `${d.weekday_name}, ${d.date}: ${statusText}. ${d.completed_count} completed, ${d.missed_count} missed, ${d.skipped_count} skipped out of ${d.total_habits} habits.`;

    let subIndicator = "";
    if (data.habit_id) {
      // Single habit mode
      if (status === "completed") subIndicator = `<i class="bi bi-check-lg text-white"></i>`;
      else if (status === "missed") subIndicator = `<i class="bi bi-x-lg text-white"></i>`;
      else if (status === "skipped") subIndicator = `<i class="bi bi-pause-fill text-white"></i>`;
      else subIndicator = `&bull;`;
    } else {
      // Multi-habit summary indicator
      if (!d.is_future && d.total_habits > 0) {
        subIndicator = `${d.completed_count}/${d.total_habits}`;
      }
    }

    const tabIndex = d.is_future ? "-1" : "0";

    html += `
      <div 
        class="calendar-cell ${statusClass} ${todayClass} ${futureClass}"
        role="gridcell"
        tabindex="${tabIndex}"
        aria-label="${escapeHtml(accessibleLabel)}"
        title="${escapeHtml(accessibleLabel)}"
        data-date="${d.date}"
        onclick="inspectCalendarDate('${d.date}')"
        onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();inspectCalendarDate('${d.date}');}">
        <span class="cell-day-num">${d.day}</span>
        <span class="cell-sub-indicator">${subIndicator}</span>
      </div>
    `;
  });

  // 3. Trailing cells to fill the row (optional neatness)
  const totalRendered = firstWeekday + days.length;
  const remainder = totalRendered % 7;
  if (remainder !== 0) {
    const trailingCount = 7 - remainder;
    for (let i = 0; i < trailingCount; i++) {
      html += `<div class="calendar-cell cell-future" aria-hidden="true" style="opacity: 0.15;"></div>`;
    }
  }

  container.innerHTML = html;
}

/**
 * Opens date inspection modal showing all habit records for that date.
 */
function inspectCalendarDate(dateStr) {
  if (!currentCalendarData || !Array.isArray(currentCalendarData.days)) return;

  const day = currentCalendarData.days.find(d => d.date === dateStr);
  if (!day) return;

  const modalEl = document.getElementById("dateInspectionModal");
  const modalLabel = document.getElementById("dateInspectionModalLabel");
  const subLabel = document.getElementById("dateInspectionSubLabel");
  const container = document.getElementById("dateInspectionRecordsContainer");

  if (!modalEl || !container) return;

  if (modalLabel) {
    modalLabel.textContent = `${day.weekday_name}, ${day.date}`;
  }
  if (subLabel) {
    subLabel.textContent = `${day.completed_count} of ${day.total_habits} habits completed (${day.dominant_status})`;
  }

  if (day.records.length === 0) {
    container.innerHTML = `
      <div class="text-center py-4 text-muted small">
        <i class="bi bi-calendar-x fs-4 d-block mb-1"></i>
        No active habits recorded on this date.
      </div>
    `;
  } else {
    container.innerHTML = day.records.map(r => {
      let badgeClass = "bg-secondary-subtle text-secondary";
      let icon = "bi-dash-circle";
      let label = "Unrecorded";

      if (r.status === "completed") {
        badgeClass = "bg-success text-white";
        icon = "bi-check-circle-fill";
        label = "Completed";
      } else if (r.status === "missed") {
        badgeClass = "bg-danger text-white";
        icon = "bi-x-circle-fill";
        label = "Missed";
      } else if (r.status === "skipped") {
        badgeClass = "bg-warning text-dark";
        icon = "bi-pause-circle-fill";
        label = "Skipped";
      }

      return `
        <div class="d-flex align-items-center justify-content-between p-2 px-3 rounded-3 bg-light border">
          <div class="d-flex align-items-center gap-2">
            <span class="badge bg-primary-subtle text-primary rounded-pill small">${escapeHtml(r.category || "General")}</span>
            <strong class="small text-dark">${escapeHtml(r.habit_name)}</strong>
          </div>
          <span class="badge ${badgeClass} rounded-pill d-flex align-items-center gap-1 small">
            <i class="bi ${icon}"></i>
            ${label}
          </span>
        </div>
      `;
    }).join("");
  }

  if (typeof bootstrap !== "undefined" && bootstrap.Modal) {
    const modalInst = bootstrap.Modal.getOrCreateInstance(modalEl);
    modalInst.show();
  }
}

/**
 * Loads weekly progress review from /api/reviews/weekly.
 */
async function loadWeeklyReview(targetDateStr = null) {
  const container = document.getElementById("weeklyReviewContent");
  const periodLabel = document.getElementById("weeklyReviewPeriodLabel");

  const dateParam = targetDateStr ? `?date=${encodeURIComponent(targetDateStr)}` : "";

  try {
    const res = await fetch(`/api/reviews/weekly${dateParam}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();
    currentWeeklyReviewData = data;

    if (periodLabel && data.period) {
      periodLabel.textContent = `${data.period.start_date} – ${data.period.end_date}`;
    }

    renderWeeklyReview(data);
  } catch (err) {
    console.error("Failed to load weekly review:", err);
    if (container) {
      container.innerHTML = `
        <div class="text-center py-4 text-muted small">
          <i class="bi bi-exclamation-triangle text-warning me-1"></i>
          Unable to load weekly review. <button class="btn btn-sm btn-link p-0" onclick="loadWeeklyReview()">Retry</button>
        </div>
      `;
    }
  }
}

/**
 * Renders weekly progress review content.
 */
function renderWeeklyReview(data) {
  const container = document.getElementById("weeklyReviewContent");
  if (!container || !data) return;

  const dataStatus = data.data_status || "no_data";
  const stats = data.statistics || {};
  const exp = data.explanation || {};

  // 1. No Data State
  if (dataStatus === "no_data") {
    container.innerHTML = `
      <div class="text-center py-4 text-muted small">
        <div class="empty-icon-circle mx-auto mb-2" style="width: 48px; height: 48px; border-radius: 50%; background: #f1f5f9; display: flex; align-items: center; justify-content: center;">
          <i class="bi bi-calendar-x text-muted fs-4"></i>
        </div>
        <h6 class="fw-bold mb-1 text-dark">No Check-ins This Week</h6>
        <p class="text-muted small mb-3">Check in on today's habits to start accumulating your weekly progress records.</p>
      </div>
    `;
    return;
  }

  // 2. Insufficient Data Warning (Never fabricate statistics)
  let insufficientWarningHtml = "";
  if (dataStatus === "insufficient_data") {
    insufficientWarningHtml = `
      <div class="alert alert-warning border-warning-subtle rounded-3 p-2 px-3 mb-3 small d-flex align-items-center gap-2">
        <i class="bi bi-info-circle-fill text-warning fs-5 flex-shrink-0"></i>
        <div>
          <strong>Limited Weekly Data:</strong> Only ${stats.total_records} check-in${stats.total_records > 1 ? "s" : ""} logged. Minimum 3 days recommended for complete weekly trends.
        </div>
      </div>
    `;
  }

  // 3. Comparison Trend Badge
  let trendBadge = "";
  if (stats.trend === "improved") {
    trendBadge = `<span class="badge bg-success-subtle text-success border border-success-subtle rounded-pill small"><i class="bi bi-arrow-up-right me-1"></i>+${stats.rate_diff}% vs last week</span>`;
  } else if (stats.trend === "declined") {
    trendBadge = `<span class="badge bg-danger-subtle text-danger border border-danger-subtle rounded-pill small"><i class="bi bi-arrow-down-right me-1"></i>${stats.rate_diff}% vs last week</span>`;
  } else if (stats.trend === "steady") {
    trendBadge = `<span class="badge bg-secondary-subtle text-secondary border rounded-pill small"><i class="bi bi-dash me-1"></i>Steady pace</span>`;
  } else {
    trendBadge = `<span class="badge bg-light text-muted border rounded-pill small"><i class="bi bi-flag me-1"></i>Baseline week</span>`;
  }

  // 4. Strongest Recorded Days Chips
  let strongDaysHtml = "";
  if (Array.isArray(data.strongest_recorded_days) && data.strongest_recorded_days.length > 0) {
    const chips = data.strongest_recorded_days.map(d => `
      <span class="day-badge-chip">
        <i class="bi bi-fire text-warning"></i>
        ${escapeHtml(d.day_name)} (${d.completed} done &bull; ${d.rate}%)
      </span>
    `).join(" ");
    strongDaysHtml = `
      <div class="mb-3">
        <small class="text-muted fw-semibold d-block mb-1">STRONGEST RECORDED DAYS</small>
        <div class="d-flex flex-wrap gap-2">${chips}</div>
      </div>
    `;
  }

  // 5. Habits Needing Attention
  let attentionHtml = "";
  if (Array.isArray(data.habits_needing_attention) && data.habits_needing_attention.length > 0) {
    const items = data.habits_needing_attention.map(h => `
      <div class="d-flex align-items-center justify-content-between py-1 px-2 rounded bg-rose-subtle text-danger small mb-1">
        <span><strong>${escapeHtml(h.name)}:</strong> ${escapeHtml(h.reason)}</span>
        <span class="badge bg-danger text-white rounded-pill">${h.rate}%</span>
      </div>
    `).join("");
    attentionHtml = `
      <div class="mb-3">
        <small class="text-muted fw-semibold d-block mb-1">HABITS NEEDING ATTENTION</small>
        <div>${items}</div>
      </div>
    `;
  }

  // 6. AI Coach Explanation Box
  let aiCoachBoxHtml = "";
  if (exp && exp.summary) {
    const sourceBadgeClass = exp.source === "ai" ? "bg-purple-subtle text-purple border-purple-subtle" : "bg-light text-muted border";
    const providerText = exp.source === "ai" ? `${(exp.provider || "AI").toUpperCase()} AI COACH` : "RULE-BASED COACH";

    let recsHtml = "";
    if (Array.isArray(exp.recommendations) && exp.recommendations.length > 0) {
      recsHtml = `<ul class="mb-0 ps-3 mt-1 text-muted small">` + exp.recommendations.map(r => `<li>${escapeHtml(r)}</li>`).join("") + `</ul>`;
    }

    aiCoachBoxHtml = `
      <div class="coach-review-box mt-3">
        <div class="d-flex align-items-center justify-content-between mb-2 flex-wrap gap-1">
          <div class="d-flex align-items-center gap-2">
            <div class="chat-avatar-wrapper" style="width: 26px; height: 26px; font-size: 0.8rem;">
              <i class="bi bi-robot"></i>
            </div>
            <strong class="small text-dark">AI Habit Coach Review</strong>
          </div>
          <span class="badge ${sourceBadgeClass} rounded-pill small fs-xxs">
            <i class="bi bi-shield-check text-success me-1"></i>${providerText}
          </span>
        </div>
        <p class="text-dark small mb-2">${escapeHtml(exp.summary)}</p>
        ${recsHtml}
        <div class="mt-2 pt-2 border-top d-flex justify-content-end">
          <button type="button" class="btn btn-sm btn-outline-primary rounded-pill px-3 py-1 fs-xs" onclick="askCoachAboutWeeklyReview()">
            <i class="bi bi-chat-dots-fill me-1"></i>Ask Coach in Chat
          </button>
        </div>
      </div>
    `;
  }

  container.innerHTML = `
    ${insufficientWarningHtml}

    <!-- Weekly KPI Card -->
    <div class="weekly-kpi-box mb-3">
      <div class="d-flex justify-content-between align-items-start mb-2">
        <div>
          <span class="text-muted small fw-medium d-block">Weekly Completion Pace</span>
          <h4 class="fw-bold mb-0 text-dark">${stats.completion_rate}%</h4>
        </div>
        ${trendBadge}
      </div>
      <div class="d-flex align-items-center gap-3 pt-2 border-top small text-muted">
        <span><strong class="text-success">${stats.completed}</strong> completed</span>
        <span>&bull;</span>
        <span><strong class="text-danger">${stats.missed}</strong> missed</span>
        <span>&bull;</span>
        <span><strong class="text-warning">${stats.skipped}</strong> skipped</span>
      </div>
    </div>

    ${strongDaysHtml}
    ${attentionHtml}
    ${aiCoachBoxHtml}
  `;
}

/**
 * Pre-fills the chat coach drawer with a weekly review question and opens it.
 */
function askCoachAboutWeeklyReview() {
  const chatLauncherBtn = document.getElementById("chatLauncherBtn");
  const chatPanel = document.getElementById("chatPanel");
  const chatInput = document.getElementById("chatInput");

  if (chatPanel && chatPanel.classList.contains("d-none")) {
    if (chatLauncherBtn) chatLauncherBtn.click();
  }

  if (chatInput) {
    chatInput.value = "Can you analyze my weekly progress review and give me tailored tips?";
    chatInput.focus();
  }
}

/**
 * Loads goals & milestones from /api/goals.
 */
async function loadGoalsAndMilestones(targetDateStr = null) {
  const container = document.getElementById("goalsListContainer");
  const alertContainer = document.getElementById("milestoneAlertContainer");
  const dateParam = targetDateStr ? `?date=${encodeURIComponent(targetDateStr)}` : "";

  try {
    const res = await fetch(`/api/goals${dateParam}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();
    currentGoals = data.goals || [];

    // Check for newly achieved milestones & notify without duplicates
    if (Array.isArray(data.new_milestones) && data.new_milestones.length > 0) {
      const unnotified = data.new_milestones.filter(m => !acknowledgedMilestones.has(m.id));
      if (unnotified.length > 0) {
        unnotified.forEach(m => {
          acknowledgedMilestones.add(m.id);
          showToast(`🎉 ${m.title}! ${m.message}`, "success");
        });

        // Display celebratory banner
        if (alertContainer) {
          const firstM = unnotified[0];
          alertContainer.innerHTML = `
            <div class="milestone-banner d-flex align-items-center justify-content-between gap-2 shadow-sm mb-3">
              <div class="d-flex align-items-center gap-2">
                <i class="bi bi-trophy-fill fs-4 text-warning"></i>
                <div>
                  <strong class="d-block text-dark">${escapeHtml(firstM.title)}</strong>
                  <span class="small">${escapeHtml(firstM.message)}</span>
                </div>
              </div>
              <button type="button" class="btn-close" aria-label="Close" onclick="this.parentElement.remove()"></button>
            </div>
          `;
        }

        // Acknowledge milestones to database to avoid repeat alerts
        const mIds = unnotified.map(m => m.id);
        fetch("/api/milestones/acknowledge", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ milestone_ids: mIds })
        }).catch(e => console.warn("Acknowledge milestone error:", e));
      }
    }

    renderGoals(currentGoals);
  } catch (err) {
    console.error("Failed to load goals:", err);
    if (container) {
      container.innerHTML = `
        <div class="text-center py-3 text-muted small">
          Unable to load goals. <button class="btn btn-sm btn-link p-0" onclick="loadGoalsAndMilestones()">Retry</button>
        </div>
      `;
    }
  }
}

/**
 * Renders weekly goals list with progress bars.
 */
function renderGoals(goals) {
  const container = document.getElementById("goalsListContainer");
  if (!container) return;

  if (!Array.isArray(goals) || goals.length === 0) {
    container.innerHTML = `
      <div class="text-center py-4 text-muted small">
        <div class="empty-icon-circle mx-auto mb-2" style="width: 44px; height: 44px; border-radius: 50%; background: #fff7ed; display: flex; align-items: center; justify-content: center;">
          <i class="bi bi-bullseye text-orange fs-4"></i>
        </div>
        <h6 class="fw-bold mb-1 text-dark">No Weekly Targets Defined</h6>
        <p class="text-muted small mb-3">Set weekly target days (e.g. 5 days/week) to track milestone progress.</p>
        <button class="btn btn-sm btn-outline-primary rounded-pill px-3" data-bs-toggle="modal" data-bs-target="#setGoalModal">
          <i class="bi bi-plus-lg me-1"></i>Set a Goal
        </button>
      </div>
    `;
    return;
  }

  container.innerHTML = goals.map(g => {
    const isAchieved = g.is_achieved;
    const progressPct = g.progress_percentage || 0;
    const barColor = isAchieved ? "bg-success" : "bg-primary";
    const achievedClass = isAchieved ? "goal-achieved" : "";

    let statusBadge = "";
    if (isAchieved) {
      statusBadge = `<span class="badge bg-success text-white rounded-pill small"><i class="bi bi-trophy-fill me-1"></i>Target Hit! 🎉</span>`;
    } else {
      statusBadge = `<span class="badge bg-light text-muted border rounded-pill small">${g.remaining} more day${g.remaining === 1 ? '' : 's'} needed</span>`;
    }

    return `
      <div class="goal-card ${achievedClass}">
        <div class="d-flex justify-content-between align-items-start mb-2">
          <div>
            <div class="d-flex align-items-center gap-2 mb-1">
              <strong class="text-dark small">${escapeHtml(g.habit_name)}</strong>
              <span class="badge bg-primary-subtle text-primary rounded-pill fs-xxs">${escapeHtml(g.category || "General")}</span>
            </div>
            <span class="text-muted small">Target: <strong>${g.target_value} days/week</strong></span>
          </div>
          <div class="d-flex align-items-center gap-2">
            ${statusBadge}
            <button type="button" class="btn btn-sm btn-link text-muted p-0" title="Remove Goal" onclick="deleteGoal(${g.id})">
              <i class="bi bi-x-circle"></i>
            </button>
          </div>
        </div>

        <!-- Progress Bar -->
        <div class="d-flex justify-content-between align-items-center mb-1 small">
          <span class="text-muted">${g.completed_this_week} of ${g.target_value} completed</span>
          <strong class="${isAchieved ? 'text-success' : 'text-primary'}">${progressPct}%</strong>
        </div>
        <div class="progress" style="height: 8px;">
          <div class="progress-bar ${barColor} rounded-pill" role="progressbar" style="width: ${progressPct}%" aria-valuenow="${progressPct}" aria-valuemin="0" aria-valuemax="100"></div>
        </div>
      </div>
    `;
  }).join("");
}

/**
 * Removes a habit target using DELETE /api/goals/<id>.
 */
async function deleteGoal(goalId) {
  const confirmed = window.confirm("Remove this weekly target?");
  if (!confirmed) return;

  try {
    const res = await fetch(`/api/goals/${goalId}`, { method: "DELETE" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    showToast("Goal target removed.", "info");
    loadGoalsAndMilestones();
  } catch (err) {
    console.error("Failed to delete goal:", err);
    showToast(`Could not remove goal: ${err.message}`, "danger");
  }
}


