PYTHON ?= python3

.PHONY: report test serve

report:
	$(PYTHON) -m evaluator.cli examples/workflows.json --out reports/sample-report.json
	$(PYTHON) -m evaluator.cli examples/portfolio-workflows.json --out reports/portfolio-report.json
	$(PYTHON) -m evaluator.cli examples/ai-ops-workflows.json --out reports/ai-ops-report.json
	$(PYTHON) -m evaluator.cli examples/public-use-cases.json --out reports/public-use-cases-report.json

test:
	$(PYTHON) -m unittest discover -s tests -v
	$(PYTHON) -m evaluator.cli examples/workflows.json --out reports/sample-report.json
	$(PYTHON) -m evaluator.cli examples/portfolio-workflows.json --out reports/portfolio-report.json
	$(PYTHON) -m evaluator.cli examples/ai-ops-workflows.json --out reports/ai-ops-report.json
	$(PYTHON) -m evaluator.cli examples/public-use-cases.json --out reports/public-use-cases-report.json

serve:
	$(PYTHON) -m http.server 8017
