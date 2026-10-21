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

  // Step B: Set up user event listeners (form submissions, filter tabs)
  setupEventListeners();

  // Step C: Initialize Chart.js interactive graphs with empty/initial state
  initCharts();

  // Step D: Load habits from the SQLite database via Flask REST API
  loadHabitsFromApi();
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
        if (modalEl) {
          const modalInstance = bootstrap.Modal.getInstance(modalEl);
          if (modalInstance) modalInstance.hide();
        }

        showToast(`New habit "${newHabit.name}" created!`, "success");
        renderHabits();
        updateSummaryMetrics();
        updateCharts();

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
 */
function updateCharts() {
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
