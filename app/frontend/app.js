const state = {
  currentRun: null,
  history: [],
  geojson: null,
  selectedDistrict: null,
  lastLoadedAt: null,
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
  loadedAt: document.querySelector("#loaded-at"),
  narrativeEn: document.querySelector("#narrative-en"),
  narrativeTc: document.querySelector("#narrative-tc"),
  learningPanel: document.querySelector("#learning-panel"),
  districtList: document.querySelector("#district-list"),
  actionsList: document.querySelector("#actions-list"),
  agentsGrid: document.querySelector("#agents-grid"),
  flagsList: document.querySelector("#flags-list"),
  historyList: document.querySelector("#history-list"),
  mapDistricts: document.querySelector("#hk-map-districts"),
  mapGrid: document.querySelector("#hk-map-grid"),
  mapInspectorPill: document.querySelector("#map-inspector-pill"),
  mapInspectorName: document.querySelector("#map-inspector-name"),
  mapInspectorCopy: document.querySelector("#map-inspector-copy"),
  mapInspectorScore: document.querySelector("#map-inspector-score"),
  mapInspectorDriver: document.querySelector("#map-inspector-driver"),
  mapInspectorConfidence: document.querySelector("#map-inspector-confidence"),
};

const alertClassMap = {
  GREEN: "green",
  YELLOW: "yellow",
  AMBER: "amber",
  RED: "red",
  BLACK: "black",
};

const SVG_NS = "http://www.w3.org/2000/svg";
const MAP_VIEWBOX = { width: 1000, height: 740, padding: 44 };

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

function renderLearning(run) {
  const summary = run?.learning_summary;
  const validation = run?.validation;
  const prediction = run?.prediction_window;

  if (!summary && !validation && !prediction) {
    elements.learningPanel.className = "stack-list empty-state";
    elements.learningPanel.textContent =
      "Learning feedback will appear here after a prediction is validated.";
    return;
  }

  const sourceLabel = summary?.source ? `Source: ${summary.source}` : "Source: local run data";
  const summaryText =
    summary?.summary_text ??
    "This run recorded a prediction window, but no validated lesson is available yet.";

  const metrics = validation
    ? `
      <div class="learning-metrics">
        <span class="learning-metric"><span class="mini-label">Matched run</span> ${escapeHtml(validation.matched_run_id)}</span>
        <span class="learning-metric"><span class="mini-label">Score error</span> ${escapeHtml(validation.risk_score_error.toFixed(2))}</span>
        <span class="learning-metric"><span class="mini-label">Abs error</span> ${escapeHtml(validation.abs_risk_score_error.toFixed(2))}</span>
        <span class="learning-metric"><span class="mini-label">Alert match</span> ${validation.alert_level_match ? "Yes" : "No"}</span>
      </div>
    `
    : `
      <div class="learning-metrics">
        <span class="learning-metric"><span class="mini-label">Prediction target</span> ${escapeHtml(formatTimestamp(prediction?.target_time))}</span>
        <span class="learning-metric"><span class="mini-label">Status</span> Awaiting future validation</span>
      </div>
    `;

  elements.learningPanel.className = "stack-list";
  elements.learningPanel.innerHTML = `
    <article class="action-item learning-item">
      <div class="district-top">
        <strong>What the system has learned</strong>
        <span class="mini-pill">${escapeHtml(sourceLabel)}</span>
      </div>
      <p class="learning-copy">${escapeHtml(summaryText)}</p>
      ${metrics}
    </article>
  `;
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

function riskBand(score) {
  if (score >= 8) {
    return "risk-extreme";
  }
  if (score >= 6) {
    return "risk-high";
  }
  if (score >= 3) {
    return "risk-medium";
  }
  return "risk-low";
}

function projectFactory(features) {
  let minLon = Infinity;
  let minLat = Infinity;
  let maxLon = -Infinity;
  let maxLat = -Infinity;

  const visit = (coordinates) => {
    if (typeof coordinates?.[0] === "number") {
      const [lon, lat] = coordinates;
      minLon = Math.min(minLon, lon);
      maxLon = Math.max(maxLon, lon);
      minLat = Math.min(minLat, lat);
      maxLat = Math.max(maxLat, lat);
      return;
    }
    coordinates?.forEach?.(visit);
  };

  features.forEach((feature) => visit(feature.geometry?.coordinates));

  const width = maxLon - minLon || 1;
  const height = maxLat - minLat || 1;
  const scale = Math.min(
    (MAP_VIEWBOX.width - MAP_VIEWBOX.padding * 2) / width,
    (MAP_VIEWBOX.height - MAP_VIEWBOX.padding * 2) / height
  );
  const offsetX = (MAP_VIEWBOX.width - width * scale) / 2;
  const offsetY = (MAP_VIEWBOX.height - height * scale) / 2;

  return ([lon, lat]) => {
    const x = offsetX + (lon - minLon) * scale;
    const y = MAP_VIEWBOX.height - (offsetY + (lat - minLat) * scale);
    return [Number(x.toFixed(2)), Number(y.toFixed(2))];
  };
}

function polygonToPath(rings, project) {
  return rings
    .map((ring) =>
      ring
        .map((coordinate, index) => {
          const [x, y] = project(coordinate);
          return `${index === 0 ? "M" : "L"}${x} ${y}`;
        })
        .join(" ") + " Z"
    )
    .join(" ");
}

function geometryToPath(geometry, project) {
  if (!geometry) {
    return "";
  }
  if (geometry.type === "Polygon") {
    return polygonToPath(geometry.coordinates, project);
  }
  if (geometry.type === "MultiPolygon") {
    return geometry.coordinates.map((polygon) => polygonToPath(polygon, project)).join(" ");
  }
  return "";
}

function centroidFromGeometry(geometry) {
  const points = [];
  const visit = (coordinates) => {
    if (typeof coordinates?.[0] === "number") {
      points.push(coordinates);
      return;
    }
    coordinates?.forEach?.(visit);
  };
  visit(geometry?.coordinates);
  if (!points.length) {
    return null;
  }
  const [sumLon, sumLat] = points.reduce(
    (accumulator, [lon, lat]) => [accumulator[0] + lon, accumulator[1] + lat],
    [0, 0]
  );
  return [sumLon / points.length, sumLat / points.length];
}

function renderMapGrid() {
  const verticals = 6;
  const horizontals = 5;
  let markup = "";
  for (let index = 1; index < verticals; index += 1) {
    const x = (MAP_VIEWBOX.width / verticals) * index;
    markup += `<line x1="${x}" y1="0" x2="${x}" y2="${MAP_VIEWBOX.height}"></line>`;
  }
  for (let index = 1; index < horizontals; index += 1) {
    const y = (MAP_VIEWBOX.height / horizontals) * index;
    markup += `<line x1="0" y1="${y}" x2="${MAP_VIEWBOX.width}" y2="${y}"></line>`;
  }
  elements.mapGrid.innerHTML = markup;
}

function updateMapInspector(run, districtName = null) {
  const activeDistrict = districtName || state.selectedDistrict || run?.top_risk_districts?.[0] || null;
  const details = activeDistrict ? run?.district_scores?.[activeDistrict] : null;
  state.selectedDistrict = activeDistrict;

  if (!run) {
    elements.mapInspectorPill.className = "alert-pill neutral";
    elements.mapInspectorPill.textContent = "No run";
    elements.mapInspectorName.textContent = "Hong Kong";
    elements.mapInspectorCopy.textContent =
      "Load a live assessment to color the real district boundaries and inspect each district.";
    elements.mapInspectorScore.textContent = "--";
    elements.mapInspectorDriver.textContent = "--";
    elements.mapInspectorConfidence.textContent = "--";
    return;
  }

  const alertClass = details ? alertClassMap[run.alert_level] ?? "neutral" : "neutral";
  elements.mapInspectorPill.className = `alert-pill ${alertClass}`;
  elements.mapInspectorPill.textContent = details ? `${run.alert_level} focus` : run.alert_level;
  elements.mapInspectorName.textContent = activeDistrict || "Hong Kong";
  elements.mapInspectorCopy.textContent = details
    ? `${activeDistrict} is scored ${details.score.toFixed(1)} out of 10. ${details.primary_driver} is the dominant flood driver with ${details.confidence} confidence.`
    : "The map is loaded, but no district-level run data is currently active.";
  elements.mapInspectorScore.textContent = details ? `${details.score.toFixed(1)} / 10` : "--";
  elements.mapInspectorDriver.textContent = details?.primary_driver ?? "--";
  elements.mapInspectorConfidence.textContent = details?.confidence ?? "--";

  Array.from(elements.mapDistricts.querySelectorAll(".district-shape")).forEach((node) => {
    node.classList.toggle("selected", node.dataset.district === activeDistrict);
  });
}

function renderGeoDistrictMap() {
  if (!state.geojson?.features?.length) {
    elements.mapDistricts.innerHTML = "";
    return;
  }

  renderMapGrid();
  const features = state.geojson.features.filter((feature) => feature?.properties?.District);
  const project = projectFactory(features);
  const fragment = document.createDocumentFragment();

  for (const feature of features) {
    const district = feature.properties.District;
    const group = document.createElementNS(SVG_NS, "g");
    group.setAttribute("class", "district-shape risk-low");
    group.dataset.district = district;
    group.setAttribute("tabindex", "0");

    const path = document.createElementNS(SVG_NS, "path");
    path.setAttribute("d", geometryToPath(feature.geometry, project));
    group.appendChild(path);

    const centroid = centroidFromGeometry(feature.geometry);
    if (centroid) {
      const [x, y] = project(centroid);
      const text = document.createElementNS(SVG_NS, "text");
      text.setAttribute("x", String(x));
      text.setAttribute("y", String(y));
      text.setAttribute("class", "district-label");
      text.textContent = district;
      group.appendChild(text);
    }

    fragment.appendChild(group);
  }

  elements.mapDistricts.innerHTML = "";
  elements.mapDistricts.appendChild(fragment);

  const handleFocus = (event) => {
    const group = event.target.closest(".district-shape");
    if (!group) {
      return;
    }
    updateMapInspector(state.currentRun, group.dataset.district);
  };

  elements.mapDistricts.addEventListener("pointerover", handleFocus);
  elements.mapDistricts.addEventListener("focusin", handleFocus);
  elements.mapDistricts.addEventListener("click", handleFocus);
}

function renderMap(run) {
  const districtScores = run?.district_scores ?? {};
  Array.from(elements.mapDistricts.querySelectorAll(".district-shape")).forEach((node) => {
    const district = node.dataset.district;
    const score = districtScores[district]?.score ?? 0;
    node.classList.remove("risk-low", "risk-medium", "risk-high", "risk-extreme", "top-risk");
    node.classList.add(riskBand(score));
    if (run?.top_risk_districts?.includes(district)) {
      node.classList.add("top-risk");
    }
  });
  updateMapInspector(run);
}

function renderRun(run) {
  state.currentRun = run;
  state.lastLoadedAt = new Date().toISOString();
  const alertLevel = run?.alert_level ?? "UNKNOWN";
  const alertClass = alertClassMap[alertLevel] ?? "neutral";
  elements.heroAlertPill.className = `alert-pill ${alertClass}`;
  elements.heroAlertPill.textContent = alertLevel;
  elements.heroRiskScore.textContent =
    typeof run?.overall_risk_score === "number" ? run.overall_risk_score.toFixed(1) : "--";
  elements.heroConfidence.textContent = formatPercent(run?.confidence_overall);
  elements.heroPriority.textContent = run?.next_update_priority ?? "--";
  elements.generatedAt.textContent = `Run time ${formatTimestamp(run?.generated_at)}`;
  elements.loadedAt.textContent = `Loaded ${formatTimestamp(state.lastLoadedAt)}`;
  elements.narrativeEn.textContent =
    run?.narrative_en ?? "Run an assessment or open a recent snapshot to populate the briefing.";
  elements.narrativeTc.textContent =
    run?.narrative_tc ?? "執行評估或載入最近快照後，這裡會顯示警報摘要。";
  renderTopDistrictChips(run);
  renderLearning(run);
  renderDistricts(run);
  renderActions(run);
  renderAgents(run);
  renderFlags(run);
  renderMap(run);
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return response.json();
}

async function loadGeojson() {
  const payload = await fetchJson("/data/hksar_18_district_boundary.json");
  state.geojson = payload;
  renderGeoDistrictMap();
  renderMap(state.currentRun);
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
    const horizonMinutes = run?.prediction_window?.target_horizon_minutes;
    const scheduleText =
      typeof horizonMinutes === "number"
        ? ` Auto-runs are now armed every ${horizonMinutes} minutes while the server stays online.`
        : "";
    setStatus(`Live assessment completed with ${run.alert_level} alert.${scheduleText}`);
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
    await loadGeojson();
    await loadHistory();
    await loadLatestRun();
  } catch (error) {
    setStatus(`Dashboard loaded, but data is unavailable. ${error.message}`, true);
  }
}

bootstrap();
