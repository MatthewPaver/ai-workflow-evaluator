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

let activeFilter = "all";
let report = fallbackReport;

function percent(value) {
  return Math.round(Number(value || 0) * 100);
}

function titleCase(value) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (match) => match.toUpperCase());
}

function formatCost(value) {
  return `$${Number(value || 0).toFixed(4)}`;
}

function setText(id, value) {
  const element = document.getElementById(id);
  if (element) element.textContent = value;
}

function renderSummary() {
  const { summary } = report;
  const average = percent(summary.average_score);
  setText("suite-name", report.suite);
  setText("average-score", `${average}%`);
  setText("total-count", summary.total);
  setText("ship-count", summary.ship);
  setText("review-count", summary.review);
  setText("block-count", summary.block);
  document.getElementById("score-ring")?.style.setProperty("--score", average);
}

function renderIssues(item) {
  if (!item.issues.length) {
    return '<p class="issue">No scoring issues found in this run.</p>';
  }

  return item.issues
    .map((issue) => {
      const content = issue.items.slice(0, 2).join("; ");
      return `<p class="issue"><strong>${titleCase(issue.type)}:</strong> ${content}</p>`;
    })
    .join("");
}

function renderCard(item) {
  const scores = Object.entries(item.scores)
    .map(([key, value]) => {
      const pct = percent(value);
      return `
        <div class="score-row">
          <span>${scoreLabels[key] || titleCase(key)}</span>
          <div class="bar" aria-hidden="true"><span style="--value: ${pct}"></span></div>
          <strong>${pct}%</strong>
        </div>
      `;
    })
    .join("");

  return `
    <article class="card" data-decision="${item.decision}">
      <div class="card-head">
        <div>
          <h3>${item.name}</h3>
          <p class="subtle">${item.workflow} · ${item.model}</p>
        </div>
        <span class="pill ${item.decision}">${item.decision}</span>
      </div>
      <div class="score-list">${scores}</div>
      <div class="meta" aria-label="Observability">
        <div><span>Latency</span><strong>${item.observability.latency_ms}ms</strong></div>
        <div><span>Cost</span><strong>${formatCost(item.observability.cost_usd)}</strong></div>
        <div><span>Review</span><strong>${titleCase(item.observability.review_status)}</strong></div>
      </div>
      <div class="issues">
        <span class="issue-label">Evidence notes</span>
        ${renderIssues(item)}
      </div>
    </article>
  `;
}

function renderResults() {
  const grid = document.getElementById("result-grid");
  if (!grid) return;

  const visible = report.results.filter((item) => activeFilter === "all" || item.decision === activeFilter);
  grid.innerHTML = visible.map(renderCard).join("");
}

function bindFilters() {
  document.querySelectorAll(".filter").forEach((button) => {
    button.addEventListener("click", () => {
      activeFilter = button.dataset.filter;
      document.querySelectorAll(".filter").forEach((item) => item.classList.remove("is-active"));
      button.classList.add("is-active");
      renderResults();
    });
  });
}

async function loadReport() {
  try {
    const response = await fetch("../reports/sample-report.json");
    if (!response.ok) throw new Error(`Report returned ${response.status}`);
    report = await response.json();
  } catch (error) {
    console.warn("Using fallback report", error);
  }

  renderSummary();
  renderResults();
}

bindFilters();
loadReport();
