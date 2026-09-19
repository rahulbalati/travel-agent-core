/**
 * Voyager AI — Consumer Travel Planner Client
 * Handles real-time SSE stream ingestion, UI rendering, day tab switching,
 * and conversational human-in-the-loop revisions.
 */

// Automatically adapt API_BASE to localhost:8000 when served from :5000, or relative in production
const API_BASE = window.VOYAGER_API_BASE || (
    window.location.port === "5000"
        ? "http://localhost:8000/api"
        : `${window.location.origin}/api`
);

// Active session state
let currentItinerary = null;
let activeDayIndex = 0;

document.addEventListener("DOMContentLoaded", () => {
    initHealthCheck();
    initTagSelectors();
    initScenarioChips();
    initPlannerForm();
    initRevisionForm();
});

/**
 * Checks backend health and updates the header badge.
 */
async function initHealthCheck() {
    const statusLabel = document.getElementById("backendStatus");
    const indicator = document.querySelector(".status-indicator");

    try {
        const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(3000) });
        if (res.ok) {
            const data = await res.json();
            statusLabel.textContent = `Online • ${data.llm_provider.toUpperCase()}`;
            indicator.style.backgroundColor = "var(--success)";
        } else {
            throw new Error("Bad response");
        }
    } catch (err) {
        statusLabel.textContent = "Offline (Start Backend)";
        indicator.style.backgroundColor = "var(--warning)";
    }
}

/**
 * Initializes preference tag pills.
 */
function initTagSelectors() {
    const pills = document.querySelectorAll(".tag-pill");
    pills.forEach((pill) => {
        pill.addEventListener("click", () => {
            pill.classList.toggle("active");
        });
    });
}

/**
 * Initializes quick scenario buttons for one-click testing.
 */
function initScenarioChips() {
    const chips = document.querySelectorAll(".scenario-chip");
    chips.forEach((chip) => {
        chip.addEventListener("click", () => {
            document.getElementById("destination").value = chip.dataset.dest;
            document.getElementById("duration").value = chip.dataset.days;
            document.getElementById("budget").value = chip.dataset.budget;
            document.getElementById("planForm").dispatchEvent(new Event("submit"));
        });
    });
}

/**
 * Initializes trip generation form with SSE stream ingestion.
 */
function initPlannerForm() {
    const form = document.getElementById("planForm");
    const submitBtn = document.getElementById("submitBtn");
    const progressBanner = document.getElementById("progressBanner");
    const progressTitle = document.getElementById("progressTitle");
    const progressDetail = document.getElementById("progressDetail");
    const itinerarySection = document.getElementById("itinerarySection");

    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        // Extract form values
        const destination = document.getElementById("destination").value.trim();
        const duration_days = parseInt(document.getElementById("duration").value, 10);
        const max_budget = parseFloat(document.getElementById("budget").value);
        const notes = document.getElementById("notes").value.trim() || null;

        const selectedTags = Array.from(
            document.querySelectorAll(".tag-pill.active")
        ).map((p) => p.dataset.tag);

        const payload = {
            destination,
            duration_days,
            max_budget,
            currency: "USD",
            travel_style: selectedTags.length ? selectedTags : ["culture", "sightseeing"],
            notes,
        };

        // UI Loading state
        submitBtn.disabled = true;
        progressBanner.classList.remove("hidden");
        progressTitle.textContent = "Connecting to Voyager Agent...";
        progressDetail.textContent = "Initializing state machine and geocoding destination...";

        try {
            // Use streaming endpoint
            const response = await fetch(`${API_BASE}/trips/plan/stream`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                throw new Error(`Server returned HTTP ${response.status}`);
            }

            // Stream SSE chunks
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = "";
            let receivedItinerary = null;
            let streamError = null;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n\n");
                buffer = lines.pop(); // keep remainder

                for (const block of lines) {
                    if (block.startsWith("data: ")) {
                        try {
                            const data = JSON.parse(block.slice(6));
                            if (data.error) {
                                streamError = data.error;
                                break;
                            }
                            if (data.status) {
                                progressTitle.textContent = formatNodeTitle(data.node || "Agent");
                                progressDetail.textContent = data.status;
                            }
                            if (data.itinerary) {
                                receivedItinerary = data.itinerary;
                            }
                        } catch (err) {
                            console.warn("Could not parse SSE chunk:", err);
                        }
                    }
                }
                if (streamError) break;
            }

            if (streamError) {
                throw new Error(streamError);
            }

            if (receivedItinerary) {
                currentItinerary = receivedItinerary;
                activeDayIndex = 0;
                renderItinerary(currentItinerary);
                itinerarySection.classList.remove("hidden");
                itinerarySection.scrollIntoView({ behavior: "smooth" });
            } else {
                throw new Error("No itinerary was generated. Please verify your connection or model quota.");
            }

        } catch (err) {
            alert(`Trip planning error: ${err.message}`);
        } finally {
            submitBtn.disabled = false;
            progressBanner.classList.add("hidden");
        }
    });
}

/**
 * Maps LangGraph node identifiers to human-readable consumer status messages.
 */
function formatNodeTitle(node) {
    switch (node) {
        case "plan_and_resolve":
            return "Resolving Destination & Coordinates...";
        case "fetch_tools":
            return "Checking Live Meteorological Forecasts & Places...";
        case "synthesize":
            return "Synthesizing Optimized Itinerary...";
        case "validate":
            return "Verifying Budget & Weather Feasibility...";
        case "self_correct":
            return "Adjusting Constraints & Refining Plan...";
        default:
            return "Orchestrating Plan...";
    }
}

/**
 * Renders the full itinerary view.
 */
function renderItinerary(itinerary) {
    // 1. Header Banner
    document.getElementById("tripDaysBadge").textContent = `${itinerary.duration_days} Days`;
    document.getElementById("tripDestBadge").textContent = itinerary.currency;
    document.getElementById("tripDestinationTitle").textContent = itinerary.destination;
    document.getElementById("tripWeatherOverview").textContent = itinerary.weather_overview || "Detailed forecast evaluated by agent.";

    // 2. Budget Meter
    const totalCost = itinerary.total_cost ?? (itinerary.cost_breakdown?.total_cost || 0);
    const budgetLimit = itinerary.budget ?? (itinerary.cost_breakdown?.budget_limit || 1000);
    const isWithinBudget = itinerary.is_within_budget ?? (totalCost <= budgetLimit);
    const remaining = Math.max(0, budgetLimit - totalCost);
    const utilPct = budgetLimit > 0 ? Math.round((totalCost / budgetLimit) * 100) : 100;

    document.getElementById("totalSpentText").textContent = `$${totalCost.toFixed(2)}`;
    document.getElementById("budgetLimitText").textContent = `$${budgetLimit.toFixed(2)}`;

    const fillBar = document.getElementById("budgetBarFill");
    fillBar.style.width = `${Math.min(100, Math.max(0, utilPct))}%`;

    const statusTag = document.getElementById("budgetStatusTag");
    const utilText = document.getElementById("budgetUtilizationText");
    utilText.textContent = `${utilPct}% utilized`;

    if (isWithinBudget) {
        statusTag.textContent = "✓ Within Budget";
        statusTag.style.color = "var(--success)";
        fillBar.style.backgroundColor = "var(--success)";
    } else {
        statusTag.textContent = "⚠️ Over Budget";
        statusTag.style.color = "var(--danger)";
        fillBar.style.backgroundColor = "var(--danger)";
    }

    // 3. Day Tabs
    renderDayTabs(itinerary.days);

    // 4. Timeline Cards
    renderTimeline(itinerary.days[activeDayIndex]);

    // 5. Cost Breakdown
    const cb = itinerary.cost_breakdown || {};
    document.getElementById("costAttractions").textContent = `$${(cb.attractions_cost ?? (totalCost * 0.4)).toFixed(2)}`;
    document.getElementById("costDining").textContent = `$${(cb.dining_cost ?? (totalCost * 0.4)).toFixed(2)}`;
    document.getElementById("costTransit").textContent = `$${(cb.transit_cost ?? (totalCost * 0.2)).toFixed(2)}`;
    document.getElementById("costRemaining").textContent = `$${remaining.toFixed(2)}`;
}

/**
 * Renders the day navigation tab buttons.
 */
function renderDayTabs(days) {
    const container = document.getElementById("dayTabsNav");
    container.innerHTML = "";

    days.forEach((day, idx) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = `day-tab-btn ${idx === activeDayIndex ? "active" : ""}`;
        btn.textContent = `Day ${day.day_number}`;

        btn.addEventListener("click", () => {
            activeDayIndex = idx;
            document.querySelectorAll(".day-tab-btn").forEach((b) => b.classList.remove("active"));
            btn.classList.add("active");
            renderTimeline(days[activeDayIndex]);
        });

        container.appendChild(btn);
    });
}

/**
 * Renders the activity cards for the selected day.
 */
function renderTimeline(day) {
    const container = document.getElementById("timelineContainer");
    container.innerHTML = "";

    if (!day) return;

    const dayTotal = day.activities.reduce((sum, act) => sum + (act.cost ?? act.estimated_cost ?? 0), 0);

    // Day theme header
    const header = document.createElement("div");
    header.style.marginBottom = "14px";
    header.innerHTML = `
    <h3 style="font-size: 18px; font-weight: 700;">${day.theme}</h3>
    <span style="font-size: 13px; color: var(--text-muted);">${day.weather_summary || ""} • Daily Spend: $${dayTotal.toFixed(2)}</span>
  `;
    container.appendChild(header);

    // Activities
    day.activities.forEach((act) => {
        const card = document.createElement("div");
        card.className = "activity-card";

        const costVal = act.cost ?? act.estimated_cost ?? 0;
        const costDisplay = costVal === 0
            ? '<span class="activity-cost free">Free</span>'
            : `<span class="activity-cost">$${costVal.toFixed(2)}</span>`;

        const indoorOutdoor = act.is_indoor ? "🏛️ Indoor" : "☀️ Outdoor";
        const timeSlot = act.time_slot || act.timeslot || "Activity";
        const locName = act.location || act.location_name || "Central";

        card.innerHTML = `
      <div class="activity-time-column">
        <span class="timeslot-label">${timeSlot}</span>
        ${costDisplay}
      </div>
      <div class="activity-body">
        <h4 class="activity-title">${act.title}</h4>
        <div class="activity-meta">
          <span>📍 ${locName}</span>
          <span>•</span>
          <span>${indoorOutdoor}</span>
        </div>
        <p class="activity-desc">${act.description}</p>
      </div>
    `;

        container.appendChild(card);
    });
}

/**
 * Initializes the conversational revision form.
 */
function initRevisionForm() {
    const form = document.getElementById("revisionForm");
    const input = document.getElementById("revisionInput");
    const reviseBtn = document.getElementById("reviseBtn");

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        if (!currentItinerary) return;

        const instruction = input.value.trim();
        if (!instruction) return;

        reviseBtn.disabled = true;
        reviseBtn.textContent = "Updating...";

        try {
            const res = await fetch(`${API_BASE}/trips/revise`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    current_itinerary: currentItinerary,
                    instruction: instruction,
                }),
            });

            if (!res.ok) {
                throw new Error(`Revision failed: ${res.statusText}`);
            }

            currentItinerary = await res.json();
            renderItinerary(currentItinerary);
            input.value = "";
        } catch (err) {
            alert(`Revision error: ${err.message}`);
        } finally {
            reviseBtn.disabled = false;
            reviseBtn.textContent = "Update Plan";
        }
    });
}
