const state = {
  currentRun: null,
  history: [],
};

const elements = {
  runLiveBtn: document.querySelector("#run-live-btn"),
  loadLatestBtn: document.querySelector("#load-latest-btn"),
  statusLine: document.querySelector("#status-line"),
  heroAlertPill: document.querySelector("#hero-alert-pill"),
  heroRiskScore: document.querySelector("#hero-risk-score"),
  heroConfidence: document.querySelector("#hero-confidence"),
  heroPriority: document.querySelector("#hero-priority"),
  topDistrictChips: document.querySelector("#top-district-chips"),
  generatedAt: document.querySelector("#generated-at"),
  narrativeEn: document.querySelector("#narrative-en"),
  narrativeTc: document.querySelector("#narrative-tc"),
  districtList: document.querySelector("#district-list"),
  actionsList: document.querySelector("#actions-list"),
  agentsGrid: document.querySelector("#agents-grid"),
  flagsList: document.querySelector("#flags-list"),
  historyList: document.querySelector("#history-list"),
};

const alertClassMap = {
  GREEN: "green",
  YELLOW: "yellow",
  AMBER: "amber",
  RED: "red",
  BLACK: "black",
};

function setStatus(message, isError = false) {
  elements.statusLine.textContent = message;
  elements.statusLine.style.color = isError ? "#ffb39f" : "";
}

function formatPercent(value) {
  return typeof value === "number" ? `${Math.round(value * 100)}%` : "--";
}

function formatTimestamp(value) {
  if (!value) {
    return "Awaiting data";
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderTopDistrictChips(run) {
  if (!run?.top_risk_districts?.length) {
    elements.topDistrictChips.innerHTML = '<span class="district-chip">No exposed districts</span>';
    return;
  }
  elements.topDistrictChips.innerHTML = run.top_risk_districts
    .slice(0, 6)
    .map((district) => `<span class="district-chip">${escapeHtml(district)}</span>`)
    .join("");
}

function renderDistricts(run) {
  const entries = Object.entries(run?.district_scores ?? {})
    .sort(([, left], [, right]) => right.score - left.score)
    .slice(0, 8);
  if (!entries.length) {
    elements.districtList.className = "district-list empty-state";
    elements.districtList.textContent = "District scores will appear here.";
    return;
  }
  elements.districtList.className = "district-list";
  elements.districtList.innerHTML = entries
    .map(([district, details]) => {
      const width = Math.max(6, Math.min(100, details.score * 10));
      return `
        <article class="district-item">
          <div class="district-top">
            <strong class="district-name">${escapeHtml(district)}</strong>
            <span class="mini-pill">${details.score.toFixed(1)} / 10</span>
          </div>
          <div class="score-bar"><span style="width: ${width}%"></span></div>
          <p class="district-meta">${escapeHtml(details.primary_driver)} · ${escapeHtml(details.confidence)} confidence</p>
        </article>
      `;
    })
    .join("");
}

function renderActions(run) {
  const actions = run?.recommended_actions ?? [];
  if (!actions.length) {
    elements.actionsList.className = "stack-list empty-state";
    elements.actionsList.textContent = "Recommended actions will appear here.";
    return;
  }
  elements.actionsList.className = "stack-list";
  elements.actionsList.innerHTML = actions
    .map(
      (action) => `
        <article class="action-item">
          <span class="mini-label">${escapeHtml(action.code)}</span>
          <strong>${escapeHtml(action.description)}</strong>
        </article>
      `
    )
    .join("");
}

function renderFlags(run) {
  const flags = run?.compound_flags ?? [];
  if (!flags.length) {
    elements.flagsList.className = "stack-list empty-state";
    elements.flagsList.textContent = "Compound flags will appear here.";
    return;
  }
  elements.flagsList.className = "stack-list";
  elements.flagsList.innerHTML = flags
    .map(
      (flag) => `
        <article class="flag-item">
          <div class="district-top">
            <strong>${escapeHtml(flag.flag)}</strong>
            <span class="mini-pill">Severity ${escapeHtml(flag.severity)}</span>
          </div>
          <p>${escapeHtml(flag.reasoning)}</p>
        </article>
      `
    )
    .join("");
}

function renderAgents(run) {
  const agents = run?.agent_signals ?? [];
  if (!agents.length) {
    elements.agentsGrid.className = "agents-grid empty-state";
    elements.agentsGrid.textContent = "Agent diagnostics will appear here.";
    return;
  }
  elements.agentsGrid.className = "agents-grid";
  elements.agentsGrid.innerHTML = agents
    .map(
      (agent) => `
        <article class="agent-card">
          <div class="agent-top">
            <strong>${escapeHtml(agent.agent_id)}</strong>
            <span class="mini-pill">${agent.is_stale ? "Stale" : "Fresh"}</span>
          </div>
          <p>${escapeHtml(agent.primary_driver)}</p>
          <div class="agent-metrics">
            <span class="agent-metric"><span class="mini-label">Risk</span> ${agent.risk_score.toFixed(1)}</span>
            <span class="agent-metric"><span class="mini-label">Confidence</span> ${formatPercent(agent.confidence)}</span>
            <span class="agent-metric"><span class="mini-label">Latency</span> ${escapeHtml(agent.latency_ms)} ms</span>
          </div>
        </article>
      `
    )
    .join("");
}

function renderHistory() {
  if (!state.history.length) {
    elements.historyList.className = "history-list empty-state";
    elements.historyList.textContent = "No recent runs available yet.";
    return;
  }
  elements.historyList.className = "history-list";
  elements.historyList.innerHTML = state.history
    .map(
      (item) => `
        <article class="history-item">
          <button type="button" data-run-id="${escapeHtml(item.run_id)}">
            <div class="history-top">
              <strong>${escapeHtml(item.alert_level ?? "UNKNOWN")} alert</strong>
              <span class="mini-pill">${typeof item.overall_risk_score === "number" ? item.overall_risk_score.toFixed(1) : "--"}</span>
            </div>
            <p>${escapeHtml((item.top_risk_districts ?? []).slice(0, 3).join(", ") || "No districts listed")}</p>
            <p class="history-meta">${escapeHtml(formatTimestamp(item.generated_at))}</p>
          </button>
        </article>
      `
    )
    .join("");
}

function renderRun(run) {
  state.currentRun = run;
  const alertLevel = run?.alert_level ?? "UNKNOWN";
  const alertClass = alertClassMap[alertLevel] ?? "neutral";
  elements.heroAlertPill.className = `alert-pill ${alertClass}`;
  elements.heroAlertPill.textContent = alertLevel;
  elements.heroRiskScore.textContent =
    typeof run?.overall_risk_score === "number" ? run.overall_risk_score.toFixed(1) : "--";
  elements.heroConfidence.textContent = formatPercent(run?.confidence_overall);
  elements.heroPriority.textContent = run?.next_update_priority ?? "--";
  elements.generatedAt.textContent = formatTimestamp(run?.generated_at);
  elements.narrativeEn.textContent =
    run?.narrative_en ?? "Run an assessment or open a recent snapshot to populate the briefing.";
  elements.narrativeTc.textContent =
    run?.narrative_tc ?? "執行評估或載入最近快照後，這裡會顯示警報摘要。";
  renderTopDistrictChips(run);
  renderDistricts(run);
  renderActions(run);
  renderAgents(run);
  renderFlags(run);
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return response.json();
}

async function loadHistory() {
  const payload = await fetchJson("/api/runs/recent");
  state.history = payload.runs ?? [];
  renderHistory();
}

async function loadRun(runId) {
  const run = await fetchJson(`/api/runs/${encodeURIComponent(runId)}`);
  renderRun(run);
  setStatus(`Loaded snapshot ${runId}.`);
}

async function loadLatestRun() {
  if (!state.history.length) {
    await loadHistory();
  }
  const latest = state.history[0];
  if (!latest) {
    setStatus("No recent snapshots available yet.", true);
    return;
  }
  await loadRun(latest.run_id);
}

async function triggerLiveRun() {
  elements.runLiveBtn.disabled = true;
  setStatus("Running live flood assessment...");
  try {
    const run = await fetchJson("/runs/flood-alert", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ mode: "live" }),
    });
    renderRun(run);
    await loadHistory();
    setStatus(`Live assessment completed with ${run.alert_level} alert.`);
  } catch (error) {
    setStatus(`Unable to complete live assessment. ${error.message}`, true);
  } finally {
    elements.runLiveBtn.disabled = false;
  }
}

function bindEvents() {
  elements.runLiveBtn.addEventListener("click", triggerLiveRun);
  elements.loadLatestBtn.addEventListener("click", () => {
    loadLatestRun().catch((error) => setStatus(`Unable to load latest snapshot. ${error.message}`, true));
  });
  elements.historyList.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-run-id]");
    if (!button) {
      return;
    }
    loadRun(button.dataset.runId).catch((error) =>
      setStatus(`Unable to load snapshot. ${error.message}`, true)
    );
  });
}

async function bootstrap() {
  bindEvents();
  try {
    await loadHistory();
    await loadLatestRun();
  } catch (error) {
    setStatus(`Dashboard loaded, but data is unavailable. ${error.message}`, true);
  }
}

bootstrap();
