# Use This In Your Project

This evaluator can be used by other projects when you have a repeatable AI workflow and a known standard for acceptable output.

It works best as a quality gate for outputs such as:

- support replies
- product copy
- meeting action lists
- portfolio or documentation summaries
- policy answers
- screenshot, PDF, image, or audio summaries

## 1. Copy the template

Start with:

```bash
cp examples/minimal-workflow-suite.json my-workflow-suite.json
```

Edit the item fields:

| Field | What to put there |
|:---|:---|
| `output` | The AI output your workflow produced. |
| `expected_facts` | Facts that must appear in the output. |
| `forbidden_claims` | Claims that must block or fail review. |
| `required_sources` | Source IDs that must be cited or mentioned. |
| `source_terms` | Evidence terms that should appear in both source and output. |
| `sources` | The notes, policy snippets, OCR text, repo README excerpts, or data rows the model was allowed to use. |
| `tokens` | Input and output token counts from the model call. |
| `modalities` | Text, screenshot, image, PDF, or audio counts. |
| `volume` | Expected monthly run count for cost projection. |
| `human_review.status` | `approved`, `review_required`, `blocked`, or `not_reviewed`. |

## 2. Or ingest an existing project

If you want to check whether AI-written project copy is grounded in the repo, generate a starter suite from the project folder:

```bash
python3 -m evaluator.ingest_project /path/to/project --out examples/project-ingest-demo.json
python3 -m evaluator.cli examples/project-ingest-demo.json --out reports/project-ingest-demo-report.json
```

The ingester reads common project files:

- `README.md`
- `docs/README.md`
- `package.json`
- `pyproject.toml`
- `requirements.txt`
- `Makefile`
- `LICENSE`

It turns those files into evidence sources and creates one starter check called `Project summary grounding`. Replace the generated `output` field with the AI-written summary, README section, portfolio card, or release note you want to test.

You can also pass the output directly:

```bash
python3 -m evaluator.ingest_project /path/to/project \
  --out examples/project-summary-gate.json \
  --output "Source S1 describes the project as a local analytics app with DuckDB and Streamlit."
```

## 3. Generate a report

```bash
python3 -m evaluator.cli my-workflow-suite.json --out reports/my-workflow-report.json
```

The report includes:

- ship, review, or block decision
- score by criterion
- evidence trace
- route recommendation
- run cost and projected monthly cost
- labelled accuracy when `expected_decision` is present

## 4. Use it as a CI gate

For a soft reporting step:

```bash
python3 -m evaluator.cli my-workflow-suite.json --out reports/my-workflow-report.json
```

For a strict release gate:

```bash
python3 -m evaluator.cli my-workflow-suite.json \
  --out reports/my-workflow-report.json \
  --min-score 0.80 \
  --fail-on-block \
  --max-monthly-cost 50
```

Use `--fail-on-review` only when every output must be fully approved before merging. Many teams will allow review items in staging but block them in production.

## 5. Add GitHub Actions

Copy `.github/example-workflows/ai-output-gate.yml` into your project as `.github/workflows/ai-output-gate.yml`.

The example assumes:

- your workflow suite lives at `examples/minimal-workflow-suite.json`
- the evaluator code is available in the repo
- reports should be uploaded as CI artifacts

## 6. When not to use it

Do not use this to prove a model is generally good. Use it when you can name the facts, sources, blocked claims, budget, and review rule for one workflow.

If your output is open-ended creative writing, a deterministic gate like this will be too rigid. If you need production traces, prompt versioning, and live monitoring, use a full observability platform.
