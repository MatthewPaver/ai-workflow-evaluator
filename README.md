# AI Workflow Evaluator

Quality gate for deciding whether AI work is accurate, grounded, affordable, fast enough, and ready for review.

[![Validate](https://github.com/MatthewPaver/ai-workflow-evaluator/actions/workflows/validate.yml/badge.svg)](https://github.com/MatthewPaver/ai-workflow-evaluator/actions/workflows/validate.yml)
[![Demo](https://github.com/MatthewPaver/ai-workflow-evaluator/actions/workflows/pages.yml/badge.svg)](https://github.com/MatthewPaver/ai-workflow-evaluator/actions/workflows/pages.yml)

![AI Workflow Evaluator preview](docs/assets/evaluator-preview.png)

**Live demo:** [matthewpaver.github.io/ai-workflow-evaluator/app/](https://matthewpaver.github.io/ai-workflow-evaluator/app/)

## What It Solves

This is not a model leaderboard. It tests one logged AI workflow at a time.

The practical question is simple: the model produced an answer, summary, recommendation, ticket note, listing draft, or repo description. Can that output ship, does a human need to review it, should it be blocked, or should the workflow route through a cheaper/faster/stronger model path?

This project checks whether an AI-generated summary, answer, recommendation, repo description, screenshot summary, PDF answer, product-listing draft, or audio-transcript action list is accurate, grounded in supplied sources, cheap enough to run, fast enough for the workflow, and ready for human approval.

It is intentionally deterministic. No paid API key is required to run the evaluator.

## Practical Test

Use it when you already know what “good enough to ship” means for a workflow.

Example:

- **Workflow:** turn a support-ticket screenshot into a triage note.
- **Required facts:** ticket ID, customer issue, affected product.
- **Evidence:** screenshot source `S1`, policy source `P1`.
- **Blocked claims:** refund approved, customer at fault, policy exception granted.
- **Limits:** max latency, max cost, required review status.
- **Decision:** ship if grounded, review if evidence is thin, block if it invents a claim.

That is the point of the app: it converts an AI output into an auditable decision instead of leaving someone to skim the answer and hope it is fine.

## Does It Meet The Brief?

Yes for a portfolio-grade public demo, with one clear boundary.

It meets the brief because it:

- accepts logged AI outputs instead of asking for live API keys
- checks accuracy, grounding, blocked claims, cost, latency, review state, and routing
- returns a decision a person can act on: ship, review, block, or reroute
- writes measurable reports with labelled accuracy, decision mix, baseline deltas, cost exposure, and route counts
- includes public examples for support replies, product listings, meeting actions, agency briefs, portfolio copy, and multimodal AI Ops
- runs locally with deterministic tests

The boundary: this is a workflow gate, not a full observability platform. It does not replace trace storage, prompt versioning, live monitoring, or LLM-as-judge experiments. Its strength is the smaller job: take one workflow output and make the release decision repeatable.

## General Public Use

The app is useful outside a developer portfolio when someone has a repeatable AI task and a known standard for acceptable output.

| User | Workflow | What they check |
|:---|:---|:---|
| Support lead | Screenshot or ticket to customer reply | policy claims, refund wording, source evidence, review state |
| Ecommerce operator | Product image or data row to listing copy | approved claims, missing attributes, cost per run |
| Agency owner | Notes and analytics to client update | overclaims, weak evidence, account-lead sign-off |
| Operations team | Meeting transcript to action list | owner, deadline, source note, handoff status |
| Builder | Repo README to portfolio card | inflated claims, missing evidence, public wording |

That gives the product a simple public wedge: upload or define one AI workflow, add the facts it must include and the claims it must avoid, then run the gate before the output reaches someone else.

## How It Can Beat Heavier Web Apps

Most evaluation platforms are stronger once a team already has traces, datasets, prompt versions, and production traffic. This project can win earlier in the workflow:

- **Lower setup:** one JSON file and a static dashboard.
- **Clear verdict:** every output lands in ship, review, block, or reroute.
- **Evidence-first:** each decision shows required facts, sources, blocked claims, and route reason.
- **Cost-aware:** multimodal inputs and monthly run volume are visible before scale-up.
- **Portable:** teams can run it locally, in CI, or as a small hosted demo.

The next step for a public product would be a “paste an output” screen that generates the JSON behind the scenes. That would move it from developer-friendly to non-technical-user-friendly.

Good fits:

- AI-written portfolio cards checked against repo READMEs.
- Support or operations summaries checked against source notes.
- Product copy drafts checked against approved claims.
- Internal assistant answers checked before a human signs them off.
- Multimodal workflows where screenshots, PDFs, images, or audio change the cost and review path.

Poor fits:

- Proving a model is universally accurate.
- Evaluating open-ended creative writing.
- Replacing semantic evals, trace stores, or human judgement in production.

## Quick Start

```bash
make report
make serve
```

Then open `http://localhost:8017/app/`.

## Run Locally

```bash
python3 -m evaluator.cli examples/workflows.json --out reports/sample-report.json
```

## Use In Another Project

Yes: copy the template, log the output from your AI workflow, and run the evaluator as a local or CI quality gate.

Start with:

```bash
cp examples/minimal-workflow-suite.json my-workflow-suite.json
python3 -m evaluator.cli my-workflow-suite.json --out reports/my-workflow-report.json
```

For CI:

```bash
python3 -m evaluator.cli my-workflow-suite.json \
  --out reports/my-workflow-report.json \
  --min-score 0.80 \
  --fail-on-block \
  --max-monthly-cost 50
```

See [Use This In Your Project](docs/use-in-your-project.md) and the sample GitHub Actions workflow at [.github/example-workflows/ai-output-gate.yml](.github/example-workflows/ai-output-gate.yml).

You can also ingest a project folder and generate a starter suite from its README, package files, Makefile, requirements, and licence:

```bash
python3 -m evaluator.ingest_project /path/to/project --out examples/project-ingest-demo.json
python3 -m evaluator.cli examples/project-ingest-demo.json --out reports/project-ingest-demo-report.json
```

That is useful for checking AI-written project summaries, README sections, release notes, and portfolio cards against the actual repo evidence.

## Add Your Own Workflow

Create a JSON file with a suite name, evaluator config, and one or more logged outputs:

```json
{
  "suite": "Product copy grounding suite",
  "config": {
    "dataset_id": "product-copy-grounding",
    "dataset_version": "v1",
    "scorer_version": "deterministic-v1",
    "baseline": {
      "label": "Previous accepted run",
      "average_score": 0.82,
      "ship": 3,
      "review": 1,
      "block": 0,
      "calibration": 0.75
    }
  },
  "items": [
    {
      "id": "copy-001",
      "name": "Launch page summary",
      "workflow": "marketing_copy_review",
      "model": "copy-model-v1",
      "output": "Source S1 says the feature is in private beta.",
      "expected_facts": ["feature is in private beta"],
      "forbidden_claims": ["available to every customer"],
      "required_sources": ["S1"],
      "source_terms": ["private beta"],
      "sources": [
        { "id": "S1", "title": "Release note", "text": "The feature is in private beta." }
      ],
      "tokens": { "input": 900, "output": 120 },
      "latency_ms": 1100,
      "expected_decision": "ship",
      "human_review": { "status": "approved" }
    }
  ]
}
```

Then run:

```bash
python3 -m evaluator.cli path/to/workflows.json --out reports/my-report.json
```

Reports include dataset/scorer versions, baseline deltas, calibration, trace evidence, and the final `ship`, `review`, or `block` decision.

## Measurable Results

The evaluator now writes a `measurable_results` block into every report. That gives you numbers to inspect or quote instead of relying on a dashboard impression.

Current checked suites:

| Suite | Labelled accuracy | Score delta | Calibration delta | Decisions | Cost exposure |
|:---|---:|---:|---:|:---|---:|
| Workflow Quality | 100% (3/3) | +5.9 pts | +33.0 pts | 2 ship · 0 review · 1 block | $0.00/month |
| Portfolio Grounding | 100% (4/4) | +14.0 pts | +25.0 pts | 3 ship · 0 review · 1 block | $0.00/month |
| AI Ops Multimodal | 100% (4/4) | +7.8 pts | +25.0 pts | 2 ship · 1 review · 1 block | $75.87/month |

The portfolio suite catches the deliberate recommender overclaim and blocks it. The AI Ops suite routes four multimodal workflows across standard review, human review, input compression, and block/rewrite paths.

## AI Ops Controls

Each workflow can now declare:

- input modalities: text, screenshots, images, PDF pages, and audio minutes
- token usage and per-modality pricing
- monthly run volume for spend projection
- risk level for routing decisions
- latency and cost thresholds

The evaluator reports:

- token cost and multimodal cost per run
- projected monthly cost
- model-routing recommendation
- route reason
- deterministic review-agent findings

The included prices are configurable demonstration rates, not a live provider billing feed. Replace them with the current rates from your chosen model provider before using the numbers for planning.

Example routes include:

| Route | Meaning |
|:---|:---|
| `small_model_auto_gate` | Low-risk, grounded, cheap, and fast enough for automated gating. |
| `standard_model_review_gate` | Normal quality gate before shipping. |
| `strong_model_plus_human_review` | High-risk or unapproved workflow needs stronger reasoning and sign-off. |
| `retrieve_more_context` | Evidence coverage is too weak. |
| `compress_inputs_or_use_cheaper_model` | Multimodal spend is too high for the threshold. |
| `async_queue_or_faster_model` | Latency is too high for an interactive workflow. |
| `block_or_rewrite` | Policy, overclaim, or quality issue means the output should not ship. |

## Tests

```bash
make test
```

## Demo Data

The sample file at `examples/workflows.json` contains three realistic workflow checks:

- a grounded AI-news summary
- a partially unsupported HR policy answer
- a high-risk analytics recommendation that needs review

The portfolio grounding file at `examples/portfolio-workflows.json` applies the same evaluator to public repo summary copy for:

- Marketing ML Lakehouse
- ProjectLens
- Dating App Recommendation System
- Sentence Similarity Analysis

That suite is designed to catch inflated portfolio claims, for example describing an offline recommender exercise as a deployed production recommender.

The AI Ops file at `examples/ai-ops-workflows.json` adds four multimodal workflow checks:

- screenshot to support-ticket summary
- PDF policy answer
- audio transcript to action list
- product image listing draft

The public-use file at `examples/public-use-cases.json` adds four copyable checks:

- support refund reply
- ecommerce product listing
- meeting action list
- client delivery brief

## Accuracy Model

This is not an LLM-as-judge benchmark. It is a deterministic quality gate for workflows where the expected evidence is known.

The evaluator is accurate when the question is: did the output include required facts, cite or mention required sources, avoid known-bad claims, stay within latency/cost thresholds, and match the expected review decision?

Each item can include an `expected_decision`. Reports include calibration metrics so you can see whether the evaluator's `ship`, `review`, and `block` outcomes match labelled expectations. The included suites currently calibrate against 11 labelled cases across workflow quality, portfolio grounding, and multimodal AI Ops checks.

## Architecture

![Architecture](docs/assets/architecture.svg)

```mermaid
flowchart LR
    A["Workflow output logs"] --> B["Deterministic evaluator"]
    C["Expected facts"] --> B
    D["Source snippets"] --> B
    E["Cost and latency config"] --> B
    B --> F["Risk scores"]
    B --> G["Human review decision"]
    B --> H["Static dashboard report"]
```

## Evaluation Criteria

| Criterion | What it checks |
|:---|:---|
| Accuracy | Required facts present in the output |
| Hallucination risk | Forbidden or unsupported claims |
| Source grounding | Required source citations and source terms |
| Latency | Whether response time meets workflow limits |
| Cost | Estimated token and multimodal cost |
| Human review | Whether the output can ship, needs review, or should be blocked |
| Routing | Whether to use a small model, stronger model, human review, context retrieval, compression, async queueing, or block/rewrite |

## Specialist Review Stages

Every evaluated item includes 14 deterministic checks and 8 named review stages:

- `reviewer_agent` checks the human-review state against the final decision.
- `source_grounding_agent` checks citations and required source coverage.
- `hallucination_agent` checks blocked claims.
- `cost_agent` checks token-cost thresholds.
- `latency_agent` checks workflow timing.
- `policy_agent` escalates high-severity issues.
- `model_router_agent` recommends the operating path for the workflow.
- `multimodal_cost_agent` checks whether multimodal spend needs review before scale-up.

These are named review stages rather than autonomous chat agents, so the quality gate stays reproducible and easy to inspect.

## Limitations

- This is a deterministic evaluation harness, not a replacement for expert review.
- Semantic correctness is approximated through required facts, forbidden claims, source references, and reviewer thresholds.
- It is designed to package evaluation thinking for product workflows; production systems should add trace storage, auth, observability, and model-provider-specific telemetry.

## License

MIT. See `LICENSE`.
