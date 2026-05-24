const fallbackReport = {
  suite: "AI Workflow Evaluator sample suite",
  generated_at: "2026-05-22T00:00:00+00:00",
  summary: { total: 0, average_score: 0, ship: 0, review: 0, block: 0 },
  dataset: { id: "pending", version: "v1", items: 0 },
  scorers: {
    version: "pending",
    type: "deterministic",
    count: 14,
    agents: [
      "reviewer_agent",
      "source_grounding_agent",
      "hallucination_agent",
      "cost_agent",
      "latency_agent",
      "policy_agent",
      "model_router_agent",
      "multimodal_cost_agent"
    ]
  },
  ai_ops: { total_run_cost_usd: 0, projected_monthly_cost_usd: 0, multimodal_items: 0, routes: {} },
  baseline: { label: "Previous accepted run", average_score: 0, ship: 0, review: 0, block: 0, calibration: 0 },
  results: []
};

const scoreLabels = {
  accuracy: "Accuracy",
  source_grounding: "Grounding",
  hallucination_control: "Hallucination",
  latency: "Latency",
  cost: "Cost",
  human_review: "Review"
};

const decisionCopy = {
  ship: "Approved to ship",
  review: "Needs review",
  block: "Blocked"
};

const reportSources = {
  sample: "../reports/sample-report.json",
  portfolio: "../reports/portfolio-report.json",
  aiops: "../reports/ai-ops-report.json"
};

const suiteNotes = {
  sample: {
    title: "Workflow quality gate",
    body:
      "This suite checks live-style LLM outputs against facts, citations, hallucination traps, latency, token cost, and reviewer status."
  },
  portfolio: {
    title: "Portfolio claim grounding",
    body:
      "This suite tests whether generated repo summaries stay faithful to the README evidence and blocks inflated claims such as describing an offline recommender as production software."
  },
  aiops: {
    title: "AI Ops control layer",
    body:
      "This suite models the company problem: text, screenshots, PDFs, images, and audio need quality checks, cost controls, latency thresholds, routing rules, and human sign-off before scale."
  }
};

let activeFilter = new URLSearchParams(window.location.search).get("decision") || "all";
let activeSuite = new URLSearchParams(window.location.search).get("suite") || "sample";
let report = fallbackReport;

function percent(value) {
  return Math.round(Number(value || 0) * 100);
}

function titleCase(value) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (match) => match.toUpperCase());
}

function formatCost(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 4,
    maximumFractionDigits: 4
  }).format(Number(value || 0));
}

function formatMonthlyCost(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(Number(value || 0));
}

function formatDate(value) {
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZoneName: "short"
  }).format(new Date(value));
}

function setText(id, value) {
  const element = document.getElementById(id);
  if (element) element.textContent = value;
}

function reviewStageCount() {
  const agents = report.scorers?.agents;
  return Array.isArray(agents) ? agents.length : 8;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function signedNumber(value, suffix = "") {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value}${suffix}`;
}

function setDelta(id, value, suffix = "", invert = false) {
  const element = document.getElementById(id);
  if (!element) return;
  element.textContent = signedNumber(value, suffix);
  const positive = invert ? value < 0 : value > 0;
  const negative = invert ? value > 0 : value < 0;
  element.classList.toggle("positive", positive);
  element.classList.toggle("negative", negative);
}

function renderSummary() {
  const { summary } = report;
  const average = percent(summary.average_score);
  const labelled = Number(report.calibration?.labelled || 0);
  const matches = Number(report.calibration?.matches || 0);
  const baseline = report.baseline || fallbackReport.baseline;
  const avgLatency = report.results.reduce((total, item) => total + item.observability.latency_ms, 0) / Math.max(report.results.length, 1);
  const avgCost = report.results.reduce((total, item) => total + item.observability.cost_usd, 0) / Math.max(report.results.length, 1);
  const monthlyCost = report.ai_ops?.projected_monthly_cost_usd || 0;
  const note = suiteNotes[activeSuite] || suiteNotes.sample;

  setText("suite-name", report.suite);
  setText("generated-at", formatDate(report.generated_at));
  setText("labelled-count", `${labelled} labelled`);
  setText("average-score", `${average}%`);
  setText("total-count", summary.total);
  setText("ship-count", summary.ship);
  setText("review-count", summary.review);
  setText("block-count", summary.block);
  setText("calibration-score", `${percent(report.calibration?.accuracy)}%`);
  setText("calibration-detail", `${matches} / ${labelled} expected decisions`);
  setText("avg-latency", `${Math.round(avgLatency)}ms`);
  setText("avg-cost", formatCost(avgCost));
  setText("monthly-cost", formatMonthlyCost(monthlyCost));
  setText("run-note-title", note.title);
  setText("run-note", note.body);
  setText("baseline-label", baseline.label || "Previous accepted run");
  setText("dataset-version", `${report.dataset?.id || "dataset"} · ${report.dataset?.version || "v1"} · ${report.dataset?.items || summary.total} cases`);
  setText(
    "scorer-version",
    `${report.scorers?.version || "deterministic-v1"} · ${report.scorers?.count || 14} checks · ${reviewStageCount()} review stages`
  );
  setDelta("score-delta", average - percent(baseline.average_score), " pts");
  setDelta("ship-delta", Number(summary.ship || 0) - Number(baseline.ship || 0));
  setDelta("block-delta", Number(summary.block || 0) - Number(baseline.block || 0), "", true);
  setDelta("calibration-delta", percent(report.calibration?.accuracy) - percent(baseline.calibration), " pts");
  document.getElementById("health-meter")?.style.setProperty("--score", average);
}

function renderIssues(item) {
  if (!item.issues.length) {
    return '<p class="issue">No exceptions found. Facts, sources, thresholds, and review status are aligned.</p>';
  }

  return item.issues
    .map((issue) => {
      const content = issue.items.slice(0, 2).join("; ");
      return `<p class="issue"><strong>${escapeHtml(titleCase(issue.type))}:</strong> ${escapeHtml(content)}</p>`;
    })
    .join("");
}

function renderTrace(item) {
  const explanations = item.trace?.explanations || [];
  const rows = explanations
    .slice(0, 4)
    .map((entry) => {
      const type = entry.type || "trace";
      return `
        <div class="trace-row ${escapeHtml(type)}">
          <span>${escapeHtml(titleCase(type))}</span>
          <p><strong>Expected:</strong> ${escapeHtml(entry.expected)}</p>
          <p><strong>Actual:</strong> ${escapeHtml(entry.actual)}</p>
          <p><strong>Evidence:</strong> ${escapeHtml(entry.source)}</p>
        </div>
      `;
    })
    .join("");

  return `
    <details class="trace-detail">
      <summary>Why This Decision</summary>
      <div class="trace-table">${rows}</div>
    </details>
  `;
}

function renderScores(item) {
  return Object.entries(item.scores)
    .map(([key, value]) => {
      const pct = percent(value);
      return `
        <div class="score-cell">
          <div class="score-top">
            <span class="score-label">${scoreLabels[key] || titleCase(key)}</span>
            <strong class="score-value">${pct}%</strong>
          </div>
          <div class="score-bar" aria-hidden="true"><span style="--value: ${pct}"></span></div>
        </div>
      `;
    })
    .join("");
}

function renderCard(item, index) {
  const route = item.observability.route || "standard_model_review_gate";
  const modalities = item.observability.modalities || ["text"];
  return `
    <article class="run-card" data-decision="${item.decision}">
      <div class="run-index">${String(index + 1).padStart(2, "0")}</div>
      <div class="run-title">
        <h3>${escapeHtml(item.name)}</h3>
        <p class="run-subtitle">${escapeHtml(item.workflow)} · ${escapeHtml(item.model)}</p>
        <span class="decision-pill ${item.decision}">${decisionCopy[item.decision] || item.decision}</span>
      </div>
      <div class="score-matrix">${renderScores(item)}</div>
      <div class="run-side">
        <div class="observability" aria-label="Observability">
          <div><span>Latency</span><strong>${item.observability.latency_ms}ms</strong></div>
          <div><span>Cost</span><strong>${formatCost(item.observability.cost_usd)}</strong></div>
          <div><span>Monthly</span><strong>${formatMonthlyCost(item.observability.monthly_cost_usd)}</strong></div>
          <div><span>Review</span><strong>${titleCase(item.observability.review_status)}</strong></div>
          <div><span>Inputs</span><strong>${escapeHtml(modalities.join(", "))}</strong></div>
          <div><span>Route</span><strong>${escapeHtml(titleCase(route))}</strong></div>
        </div>
        <div class="evidence">
          <span class="evidence-title">Evidence Notes</span>
          ${renderIssues(item)}
          ${renderTrace(item)}
        </div>
      </div>
    </article>
  `;
}

function updateUrlFilter() {
  const url = new URL(window.location.href);
  if (activeFilter === "all") {
    url.searchParams.delete("decision");
  } else {
    url.searchParams.set("decision", activeFilter);
  }
  if (activeSuite === "sample") {
    url.searchParams.delete("suite");
  } else {
    url.searchParams.set("suite", activeSuite);
  }
  window.history.replaceState({}, "", url);
}

function renderResults() {
  const grid = document.getElementById("result-grid");
  if (!grid) return;

  const visible = report.results.filter((item) => activeFilter === "all" || item.decision === activeFilter);
  grid.innerHTML = visible.map(renderCard).join("");
  const emptyState = document.getElementById("empty-state");
  if (emptyState) emptyState.hidden = visible.length > 0;
}

function bindFilters() {
  document.querySelectorAll(".filter").forEach((button) => {
    const isActive = button.dataset.filter === activeFilter;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-pressed", String(isActive));

    button.addEventListener("click", () => {
      activeFilter = button.dataset.filter;
      document.querySelectorAll(".filter").forEach((item) => item.classList.remove("is-active"));
      document.querySelectorAll(".filter").forEach((item) => item.setAttribute("aria-pressed", "false"));
      button.classList.add("is-active");
      button.setAttribute("aria-pressed", "true");
      updateUrlFilter();
      renderResults();
    });
  });
}

function bindSuites() {
  document.querySelectorAll(".suite-button").forEach((button) => {
    const isActive = button.dataset.suite === activeSuite;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-pressed", String(isActive));

    button.addEventListener("click", () => {
      activeSuite = button.dataset.suite;
      document.querySelectorAll(".suite-button").forEach((item) => item.classList.remove("is-active"));
      document.querySelectorAll(".suite-button").forEach((item) => item.setAttribute("aria-pressed", "false"));
      button.classList.add("is-active");
      button.setAttribute("aria-pressed", "true");
      updateUrlFilter();
      loadReport();
    });
  });
}

async function loadReport() {
  try {
    const response = await fetch(reportSources[activeSuite] || reportSources.sample);
    if (!response.ok) throw new Error(`Report returned ${response.status}`);
    report = await response.json();
  } catch (error) {
    console.warn("Using fallback report", error);
  }

  renderSummary();
  renderResults();
}

bindFilters();
bindSuites();
loadReport();
