const state = {
  currentRun: null,
  history: [],
  accuracy: null,
  geojson: null,
  selectedDistrict: null,
  lastLoadedAt: null,
  mapMode: "actual", // "actual" | "predicted" | "rainfall"
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
  accuracyPanel: document.querySelector("#accuracy-panel"),
  districtList: document.querySelector("#district-list"),
  actionsList: document.querySelector("#actions-list"),
  agentsGrid: document.querySelector("#agents-grid"),
  flagsList: document.querySelector("#flags-list"),
  historyList: document.querySelector("#history-list"),
  mapDistricts: document.querySelector("#hk-map-districts"),
  mapGrid: document.querySelector("#hk-map-grid"),
  mapLabels: document.querySelector("#hk-map-labels"),
  mapCompass: document.querySelector("#hk-map-compass"),
  mapDataTime: document.querySelector("#map-data-time"),
  mapPredWindow: document.querySelector("#map-pred-window"),
  mapInspectorPill: document.querySelector("#map-inspector-pill"),
  mapInspectorName: document.querySelector("#map-inspector-name"),
  mapInspectorCopy: document.querySelector("#map-inspector-copy"),
  mapInspectorDriver: document.querySelector("#map-inspector-driver"),
  mapInspectorConfidence: document.querySelector("#map-inspector-confidence"),
  scoreRingVal: document.querySelector("#score-ring-val"),
  scoreRingText: document.querySelector("#score-ring-text"),
  // New map controls
  mapTabBar: document.querySelector(".map-tab-bar"),
  mapTabHint: document.querySelector("#map-tab-hint"),
  dualBarActual: document.querySelector("#dual-bar-actual"),
  dualBarPred: document.querySelector("#dual-bar-pred"),
  dualValActual: document.querySelector("#dual-val-actual"),
  dualValPred: document.querySelector("#dual-val-pred"),
  inspectorRainfall: document.querySelector("#map-inspector-rainfall"),
  inspectorTide: document.querySelector("#map-inspector-tide"),
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

function buildAccuracyChart(points) {
  const width = 560;
  const height = 220;
  const padding = 22;
  const usableWidth = width - padding * 2;
  const usableHeight = height - padding * 2;
  const series = points.map((point, index) => {
    const x =
      points.length === 1 ? width / 2 : padding + (usableWidth * index) / Math.max(points.length - 1, 1);
    const y = padding + ((100 - point.accuracy_percent) / 100) * usableHeight;
    return { ...point, x: Number(x.toFixed(2)), y: Number(y.toFixed(2)) };
  });
  const polyline = series.map((point) => `${point.x},${point.y}`).join(" ");
  const dots = series
    .map(
      (point) => `
        <circle cx="${point.x}" cy="${point.y}" r="4.5"></circle>
      `
    )
    .join("");
  return `
    <svg class="accuracy-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="Prediction accuracy over time">
      <line class="accuracy-axis" x1="${padding}" y1="${padding}" x2="${padding}" y2="${height - padding}"></line>
      <line class="accuracy-axis" x1="${padding}" y1="${height - padding}" x2="${width - padding}" y2="${height - padding}"></line>
      <line class="accuracy-gridline" x1="${padding}" y1="${padding}" x2="${width - padding}" y2="${padding}"></line>
      <line class="accuracy-gridline" x1="${padding}" y1="${padding + usableHeight / 2}" x2="${width - padding}" y2="${padding + usableHeight / 2}"></line>
      <polyline class="accuracy-line" points="${polyline}"></polyline>
      <g class="accuracy-dots">${dots}</g>
      <text class="accuracy-label" x="${padding}" y="${padding - 6}">100%</text>
      <text class="accuracy-label" x="${padding}" y="${padding + usableHeight / 2 - 6}">50%</text>
      <text class="accuracy-label" x="${padding}" y="${height - 6}">0%</text>
    </svg>
  `;
}

function renderAccuracy() {
  const report = state.accuracy;
  const points = report?.points ?? [];
  if (!points.length) {
    elements.accuracyPanel.className = "stack-list empty-state";
    elements.accuracyPanel.textContent =
      "Accuracy will appear after validated predictions are available.";
    return;
  }

  const latest = points[points.length - 1];
  const chartMarkup = buildAccuracyChart(points);
  const latestTime = formatTimestamp(latest.actual_generated_at);
  elements.accuracyPanel.className = "stack-list";
  elements.accuracyPanel.innerHTML = `
    <article class="action-item accuracy-item">
      <div class="district-top">
        <strong>Rolling prediction accuracy</strong>
        <span class="mini-pill">${escapeHtml(`${report.rolling_accuracy_percent.toFixed(1)}%`)}</span>
      </div>
      <p class="learning-copy">${escapeHtml(report.formula)}</p>
      <div class="learning-metrics">
        <span class="learning-metric"><span class="mini-label">Validated points</span> ${escapeHtml(report.point_count)}</span>
        <span class="learning-metric"><span class="mini-label">Horizon</span> ${escapeHtml(`${latest.target_horizon_minutes} min`)}</span>
        <span class="learning-metric"><span class="mini-label">Latest score</span> ${escapeHtml(`${latest.accuracy_percent.toFixed(1)}%`)}</span>
        <span class="learning-metric"><span class="mini-label">Latest validated</span> ${escapeHtml(latestTime)}</span>
      </div>
      ${chartMarkup}
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

/**
 * Interpolate a continuous colour for a risk score 0–10.
 * Palette: deep-blue(0) → teal-green(3) → amber(5) → orange(7) → crimson(10)
 */
function riskColour(score, alpha = 1) {
  const stops = [
    { s: 0,  r: 30,  g: 74,  b: 107 }, // deep navy
    { s: 3,  r: 38,  g: 138, b: 78  }, // teal-green
    { s: 5,  r: 217, g: 184, b: 58  }, // amber-yellow
    { s: 7,  r: 232, g: 114, b: 42  }, // orange
    { s: 10, r: 217, g: 43,  b: 28  }, // crimson
  ];
  const clamped = Math.max(0, Math.min(10, score));
  let lo = stops[0];
  let hi = stops[stops.length - 1];
  for (let i = 0; i < stops.length - 1; i++) {
    if (clamped >= stops[i].s && clamped <= stops[i + 1].s) {
      lo = stops[i];
      hi = stops[i + 1];
      break;
    }
  }
  const t = lo.s === hi.s ? 0 : (clamped - lo.s) / (hi.s - lo.s);
  const r = Math.round(lo.r + t * (hi.r - lo.r));
  const g = Math.round(lo.g + t * (hi.g - lo.g));
  const b = Math.round(lo.b + t * (hi.b - lo.b));
  return alpha < 1 ? `rgba(${r},${g},${b},${alpha})` : `rgb(${r},${g},${b})`;
}

/** Rain colour: 0 mm → slate-blue, >30 mm → vivid cyan-green */
function rainfallColour(mmPerHour) {
  const mm = Math.max(0, mmPerHour || 0);
  if (mm === 0) return "rgb(22,44,68)";
  if (mm < 10) return `rgb(${Math.round(22 + mm * 3)},${Math.round(44 + mm * 8)},${Math.round(68 + mm * 4)})`;
  if (mm < 30) return `rgb(${Math.round(52 + (mm - 10) * 2)},${Math.round(124 + (mm - 10) * 4)},${Math.round(108)})`;
  if (mm < 50) return `rgb(57,211,140)`;
  return `rgb(255,230,50)`; // extreme flash yellow
}

/** Ring stroke colour matching risk */
function ringColour(score) {
  return riskColour(score);
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

function renderCompass() {
  const cx = 910;
  const cy = 670;
  const r = 36;
  elements.mapCompass.innerHTML = `
    <circle cx="${cx}" cy="${cy}" r="${r}" class="compass-ring-outer" />
    <circle cx="${cx}" cy="${cy}" r="${r - 4}" class="compass-ring-inner" />
    <polygon class="compass-needle-n" points="${cx},${cy - r + 6} ${cx - 5},${cy + 4} ${cx + 5},${cy + 4}" />
    <polygon class="compass-needle-s" points="${cx},${cy + r - 6} ${cx - 5},${cy - 4} ${cx + 5},${cy - 4}" />
    <polygon class="compass-needle-e" points="${cx + r - 6},${cy} ${cx - 4},${cy - 5} ${cx - 4},${cy + 5}" />
    <polygon class="compass-needle-w" points="${cx - r + 6},${cy} ${cx + 4},${cy - 5} ${cx + 4},${cy + 5}" />
    <text x="${cx}" y="${cy - r + 6}" class="compass-label-n" text-anchor="middle" dy="-2">N</text>
    <text x="${cx}" y="${cy + r - 4}" class="compass-label-s" text-anchor="middle" dy="5">S</text>
    <text x="${cx + r - 6}" y="${cy + 4}" class="compass-label-e" text-anchor="middle">E</text>
    <text x="${cx - r + 6}" y="${cy + 4}" class="compass-label-w" text-anchor="middle">W</text>
  `;
}

function updateMapInspector(run, districtName = null) {
  const activeDistrict = districtName || state.selectedDistrict || run?.top_risk_districts?.[0] || null;
  const details = activeDistrict ? run?.district_scores?.[activeDistrict] : null;
  state.selectedDistrict = activeDistrict;

  const scoreRing = elements.scoreRingVal;
  const scoreText = elements.scoreRingText;
  const total = 182.21;

  if (!run) {
    elements.mapInspectorPill.className = "alert-pill neutral";
    elements.mapInspectorPill.textContent = "No run";
    elements.mapInspectorName.textContent = "Hong Kong";
    elements.mapInspectorCopy.textContent =
      "Load a live assessment to color the real district boundaries and inspect each district.";
    elements.mapInspectorDriver.textContent = "--";
    elements.mapInspectorConfidence.textContent = "--";
    scoreRing.setAttribute("stroke-dasharray", "0 " + total);
    scoreRing.setAttribute("stroke", "#93abc0");
    scoreText.textContent = "--";
    elements.mapDataTime.textContent = "Real-time data";
    elements.mapPredWindow.textContent = "";
    // Dual bars
    elements.dualBarActual.style.width = "0%";
    elements.dualBarPred.style.width = "0%";
    elements.dualValActual.textContent = "--";
    elements.dualValPred.textContent = "--";
    if (elements.inspectorRainfall) elements.inspectorRainfall.textContent = "--";
    if (elements.inspectorTide) elements.inspectorTide.textContent = "--";
    return;
  }

  const alertClass = details ? alertClassMap[run.alert_level] ?? "neutral" : "neutral";
  elements.mapInspectorPill.className = `alert-pill ${alertClass}`;
  elements.mapInspectorPill.textContent = details ? `${run.alert_level} alert` : run.alert_level;
  elements.mapInspectorName.textContent = activeDistrict || "Hong Kong";
  elements.mapInspectorCopy.textContent = details
    ? `${activeDistrict}: scored ${details.score.toFixed(1)}/10. ${details.primary_driver?.split(" ").slice(0, 10).join(" ") ?? ""}…`
    : "No district-level data for the selected district.";
  elements.mapInspectorDriver.textContent = details?.primary_driver?.split(" ").slice(0, 4).join(" ") ?? "--";
  elements.mapInspectorConfidence.textContent = details?.confidence ?? "--";

  // Score ring — reflects current map mode
  const actualScore = details?.score ?? 0;
  const predScore = run?.prediction_window?.predicted_overall_risk_score ?? actualScore;
  const displayScore = state.mapMode === "predicted" ? predScore : actualScore;
  const pct = Math.min(displayScore / 10, 1);
  const filled = total * pct;
  scoreRing.setAttribute("stroke-dasharray", filled.toFixed(2) + " " + total);
  scoreRing.setAttribute("stroke", ringColour(displayScore));
  scoreText.textContent = details ? displayScore.toFixed(1) : "--";

  // Dual bars
  elements.dualBarActual.style.width = `${(actualScore / 10) * 100}%`;
  elements.dualValActual.textContent = details ? actualScore.toFixed(1) : "--";
  elements.dualBarPred.style.width = `${(predScore / 10) * 100}%`;
  elements.dualValPred.textContent = run.prediction_window ? predScore.toFixed(1) : "n/a";

  // Agent signal readouts
  const rainfallAgent = run.agent_signals?.find(s => s.agent_id === "RainfallAgent");
  const tideAgent = run.agent_signals?.find(s => s.agent_id === "TideAgent");
  const rainfallScore = activeDistrict && rainfallAgent?.district_scores?.[activeDistrict];
  const tideScore = activeDistrict && tideAgent?.district_scores?.[activeDistrict];
  if (elements.inspectorRainfall) {
    elements.inspectorRainfall.textContent =
      typeof rainfallScore === "number" ? rainfallScore.toFixed(1) : "--";
  }
  if (elements.inspectorTide) {
    elements.inspectorTide.textContent =
      typeof tideScore === "number" ? tideScore.toFixed(1) : "--";
  }

  // Timestamps
  const genAt = formatTimestamp(run?.generated_at);
  elements.mapDataTime.textContent = `Data: ${genAt}`;
  const pw = run?.prediction_window;
  if (pw) {
    elements.mapPredWindow.textContent =
      `Pred: +${pw.target_horizon_minutes ?? "?"}min · ${pw.predicted_alert_level} · ${pw.predicted_overall_risk_score?.toFixed(1)}`;
  } else {
    elements.mapPredWindow.textContent = "No prediction window";
  }

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
  renderCompass();
  const features = state.geojson.features.filter((feature) => feature?.properties?.District);
  const project = projectFactory(features);
  const districtsFrag = document.createDocumentFragment();
  const labelsFrag = document.createDocumentFragment();

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
      text.dataset.district = district;
      text.textContent = district;
      labelsFrag.appendChild(text);
    }

    districtsFrag.appendChild(group);
  }

  elements.mapDistricts.innerHTML = "";
  elements.mapDistricts.appendChild(districtsFrag);
  elements.mapLabels.innerHTML = "";
  elements.mapLabels.appendChild(labelsFrag);

  const handleFocus = (event) => {
    const group = event.target.closest(".district-shape");
    if (!group) {
      return;
    }
    const district = group.dataset.district;
    updateMapInspector(state.currentRun, district);

    elements.mapLabels.querySelectorAll(".district-label").forEach((lbl) => {
      lbl.classList.toggle("label-active", lbl.dataset.district === district);
    });
  };

  elements.mapDistricts.addEventListener("pointerover", handleFocus);
  elements.mapDistricts.addEventListener("focusin", handleFocus);
  elements.mapDistricts.addEventListener("click", handleFocus);
}

/**
 * Apply fill colours to all district shapes based on the current map mode:
 *  - "actual"    : district_scores[d].score (continuous colour scale)
 *  - "predicted" : prediction_window.predicted_overall_risk_score (uniform tint)
 *                  + per-district actual as base when no per-district prediction
 *  - "rainfall"  : RainfallAgent district_scores (blue-green scale)
 */
function renderMap(run) {
  const districtScores = run?.district_scores ?? {};
  const predScore = run?.prediction_window?.predicted_overall_risk_score ?? null;
  const rainfallAgent = run?.agent_signals?.find(s => s.agent_id === "RainfallAgent");
  const rainfallScores = rainfallAgent?.district_scores ?? {};

  Array.from(elements.mapDistricts.querySelectorAll(".district-shape")).forEach((node) => {
    const district = node.dataset.district;
    const path = node.querySelector("path");
    if (!path) return;

    // Remove old mode classes
    node.classList.remove("top-risk", "mode-predicted", "mode-rainfall");

    let fillColour;
    if (state.mapMode === "rainfall") {
      const mm = rainfallScores[district] ?? 0;
      fillColour = rainfallColour(mm * 30); // scale agent score 0-10 → 0-300mm equiv
      node.classList.add("mode-rainfall");
    } else if (state.mapMode === "predicted") {
      // Use per-district actual score blended toward the run-level prediction
      const actualScore = districtScores[district]?.score ?? 0;
      const blended = predScore !== null ? (actualScore * 0.4 + predScore * 0.6) : actualScore;
      fillColour = riskColour(blended, 0.88);
      node.classList.add("mode-predicted");
    } else {
      // Actual mode
      const score = districtScores[district]?.score ?? 0;
      fillColour = riskColour(score);
      if (run?.top_risk_districts?.includes(district)) {
        node.classList.add("top-risk");
      }
    }

    path.style.fill = fillColour;
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

async function loadAccuracy() {
  const payload = await fetchJson("/api/learning/accuracy");
  state.accuracy = payload;
  renderAccuracy();
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
    await loadAccuracy();
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

  // Map tab bar switching
  if (elements.mapTabBar) {
    elements.mapTabBar.addEventListener("click", (event) => {
      const tab = event.target.closest(".map-tab[data-mode]");
      if (!tab) return;
      const mode = tab.dataset.mode;
      if (mode === state.mapMode) return;
      state.mapMode = mode;
      elements.mapTabBar.querySelectorAll(".map-tab").forEach((t) => {
        t.classList.toggle("active", t.dataset.mode === mode);
        t.setAttribute("aria-selected", t.dataset.mode === mode ? "true" : "false");
      });
      renderMap(state.currentRun);
    });
  }
}


async function bootstrap() {
  bindEvents();
  try {
    await loadGeojson();
    await loadHistory();
    await loadAccuracy();
    await loadLatestRun();
  } catch (error) {
    setStatus(`Dashboard loaded, but data is unavailable. ${error.message}`, true);
  }
}

bootstrap();
