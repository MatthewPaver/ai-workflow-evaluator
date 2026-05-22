const fallbackReport = {
  suite: "AI Workflow Evaluator sample suite",
  generated_at: "2026-05-22T00:00:00+00:00",
  summary: { total: 0, average_score: 0, ship: 0, review: 0, block: 0 },
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
  portfolio: "../reports/portfolio-report.json"
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

function renderSummary() {
  const { summary } = report;
  const average = percent(summary.average_score);
  const labelled = Number(report.calibration?.labelled || 0);
  const matches = Number(report.calibration?.matches || 0);
  const avgLatency = report.results.reduce((total, item) => total + item.observability.latency_ms, 0) / Math.max(report.results.length, 1);
  const avgCost = report.results.reduce((total, item) => total + item.observability.cost_usd, 0) / Math.max(report.results.length, 1);
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
  setText("run-note-title", note.title);
  setText("run-note", note.body);
  document.getElementById("health-meter")?.style.setProperty("--score", average);
}

function renderIssues(item) {
  if (!item.issues.length) {
    return '<p class="issue">No exceptions found. Facts, sources, thresholds, and review status are aligned.</p>';
  }

  return item.issues
    .map((issue) => {
      const content = issue.items.slice(0, 2).join("; ");
      return `<p class="issue"><strong>${titleCase(issue.type)}:</strong> ${content}</p>`;
    })
    .join("");
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
  return `
    <article class="run-card" data-decision="${item.decision}">
      <div class="run-index">${String(index + 1).padStart(2, "0")}</div>
      <div class="run-title">
        <h3>${item.name}</h3>
        <p class="run-subtitle">${item.workflow} · ${item.model}</p>
        <span class="decision-pill ${item.decision}">${decisionCopy[item.decision] || item.decision}</span>
      </div>
      <div class="score-matrix">${renderScores(item)}</div>
      <div class="run-side">
        <div class="observability" aria-label="Observability">
          <div><span>Latency</span><strong>${item.observability.latency_ms}ms</strong></div>
          <div><span>Cost</span><strong>${formatCost(item.observability.cost_usd)}</strong></div>
          <div><span>Review</span><strong>${titleCase(item.observability.review_status)}</strong></div>
        </div>
        <div class="evidence">
          <span class="evidence-title">Evidence Notes</span>
          ${renderIssues(item)}
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
}

function bindFilters() {
  document.querySelectorAll(".filter").forEach((button) => {
    const isActive = button.dataset.filter === activeFilter;
    button.classList.toggle("is-active", isActive);

    button.addEventListener("click", () => {
      activeFilter = button.dataset.filter;
      document.querySelectorAll(".filter").forEach((item) => item.classList.remove("is-active"));
      button.classList.add("is-active");
      updateUrlFilter();
      renderResults();
    });
  });
}

function bindSuites() {
  document.querySelectorAll(".suite-button").forEach((button) => {
    const isActive = button.dataset.suite === activeSuite;
    button.classList.toggle("is-active", isActive);

    button.addEventListener("click", () => {
      activeSuite = button.dataset.suite;
      document.querySelectorAll(".suite-button").forEach((item) => item.classList.remove("is-active"));
      button.classList.add("is-active");
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
