PYTHON ?= python3

.PHONY: report test serve

report:
	$(PYTHON) -m evaluator.cli examples/workflows.json --out reports/sample-report.json
	$(PYTHON) -m evaluator.cli examples/portfolio-workflows.json --out reports/portfolio-report.json
	$(PYTHON) -m evaluator.cli examples/ai-ops-workflows.json --out reports/ai-ops-report.json
	$(PYTHON) -m evaluator.cli examples/public-use-cases.json --out reports/public-use-cases-report.json
	$(PYTHON) -m evaluator.cli examples/minimal-workflow-suite.json --out reports/minimal-workflow-report.json
	$(PYTHON) -m evaluator.ingest_project . --out examples/project-ingest-demo.json
	$(PYTHON) -m evaluator.cli examples/project-ingest-demo.json --out reports/project-ingest-demo-report.json

test:
	$(PYTHON) -m unittest discover -s tests -v
	$(PYTHON) -m evaluator.cli examples/workflows.json --out reports/sample-report.json
	$(PYTHON) -m evaluator.cli examples/portfolio-workflows.json --out reports/portfolio-report.json
	$(PYTHON) -m evaluator.cli examples/ai-ops-workflows.json --out reports/ai-ops-report.json
	$(PYTHON) -m evaluator.cli examples/public-use-cases.json --out reports/public-use-cases-report.json
	$(PYTHON) -m evaluator.cli examples/minimal-workflow-suite.json --out reports/minimal-workflow-report.json --min-score 0.8 --fail-on-block --max-monthly-cost 50
	$(PYTHON) -m evaluator.ingest_project . --out examples/project-ingest-demo.json
	$(PYTHON) -m evaluator.cli examples/project-ingest-demo.json --out reports/project-ingest-demo-report.json --min-score 0.8 --fail-on-block --max-monthly-cost 50

serve:
	$(PYTHON) -m http.server 8017
