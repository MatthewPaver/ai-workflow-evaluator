# AI Workflow Evaluator

Deterministic evaluation for LLM outputs before they reach users.

[![Validate](https://github.com/MatthewPaver/ai-workflow-evaluator/actions/workflows/validate.yml/badge.svg)](https://github.com/MatthewPaver/ai-workflow-evaluator/actions/workflows/validate.yml)
[![Demo](https://github.com/MatthewPaver/ai-workflow-evaluator/actions/workflows/pages.yml/badge.svg)](https://github.com/MatthewPaver/ai-workflow-evaluator/actions/workflows/pages.yml)

![AI Workflow Evaluator preview](docs/assets/evaluator-preview.svg)

**Live demo:** [matthewpaver.github.io/ai-workflow-evaluator/app/](https://matthewpaver.github.io/ai-workflow-evaluator/app/)

## What It Solves

LLM demos often stop at a good-looking answer. This project checks whether an output is accurate, grounded in supplied sources, cheap enough to run, fast enough for the workflow, and ready for human approval.

It is intentionally deterministic. No paid API key is required to run the evaluator.

## Quick Start

```bash
make report
make serve
```

Then open `http://localhost:8017/app/`.

## Run Locally

```bash
python -m evaluator.cli examples/workflows.json --out reports/sample-report.json
```

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

## Accuracy Model

This is not an LLM-as-judge benchmark. It is a deterministic quality gate.

The evaluator is accurate when the question is: did the output include required facts, cite or mention required sources, avoid known-bad claims, stay within latency/cost thresholds, and match the expected review decision?

Each item can include an `expected_decision`. Reports include calibration metrics so you can see whether the evaluator's `ship`, `review`, and `block` outcomes match labelled expectations. The included suites currently calibrate against 7 labelled cases: 5 shippable examples and 2 blocked examples, including one deliberate portfolio overclaim.

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
| Cost | Estimated model cost from token counts |
| Human review | Whether the output can ship, needs review, or should be blocked |

## Limitations

- This is a deterministic evaluation harness, not a replacement for expert review.
- Semantic correctness is approximated through required facts, forbidden claims, source references, and reviewer thresholds.
- It is designed to package evaluation thinking for product workflows; production systems should add trace storage, auth, observability, and model-provider-specific telemetry.

## License

MIT. See `LICENSE`.
