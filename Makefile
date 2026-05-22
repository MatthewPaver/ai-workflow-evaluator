PYTHON ?= python3

.PHONY: report test serve

report:
	$(PYTHON) -m evaluator.cli examples/workflows.json --out reports/sample-report.json

test:
	$(PYTHON) -m unittest discover -s tests -v
	$(PYTHON) -m evaluator.cli examples/workflows.json --out reports/sample-report.json

serve:
	$(PYTHON) -m http.server 8017
