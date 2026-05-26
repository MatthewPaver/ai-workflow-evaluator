from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core import evaluate_dataset


def quality_gate_failures(
    report: dict,
    *,
    min_score: float | None = None,
    fail_on_review: bool = False,
    fail_on_block: bool = False,
    max_monthly_cost: float | None = None,
) -> list[str]:
    summary = report["summary"]
    measured = report["measurable_results"]
    failures: list[str] = []

    if min_score is not None and float(summary["average_score"]) < min_score:
        failures.append(f"average score {summary['average_score']:.2f} is below {min_score:.2f}")
    if fail_on_review and int(summary["review"]) > 0:
        failures.append(f"{summary['review']} output(s) need review")
    if fail_on_block and int(summary["block"]) > 0:
        failures.append(f"{summary['block']} output(s) are blocked")
    if max_monthly_cost is not None and float(measured["projected_monthly_cost_usd"]) > max_monthly_cost:
        failures.append(
            f"monthly cost ${measured['projected_monthly_cost_usd']:.2f} is above ${max_monthly_cost:.2f}"
        )

    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate logged LLM workflow outputs.")
    parser.add_argument("input", type=Path, help="Path to workflow JSON input")
    parser.add_argument("--out", type=Path, default=Path("reports/sample-report.json"), help="Output report path")
    parser.add_argument("--min-score", type=float, help="Fail if the average score is below this value, for example 0.80")
    parser.add_argument("--fail-on-review", action="store_true", help="Fail if any output needs review")
    parser.add_argument("--fail-on-block", action="store_true", help="Fail if any output is blocked")
    parser.add_argument("--max-monthly-cost", type=float, help="Fail if projected monthly cost is above this amount")
    args = parser.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    report = evaluate_dataset(payload)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    summary = report["summary"]
    measured = report["measurable_results"]
    print(
        f"{report['suite']}: {summary['total']} outputs, "
        f"average={summary['average_score']:.2f}, "
        f"ship={summary['ship']}, review={summary['review']}, block={summary['block']}, "
        f"calibration={report['calibration']['accuracy']:.2f}, "
        f"score_delta={measured['score_delta_points']:+.1f}pts, "
        f"calibration_delta={measured['calibration_delta_points']:+.1f}pts, "
        f"monthly_cost=${measured['projected_monthly_cost_usd']:.2f}"
    )

    failures = quality_gate_failures(
        report,
        min_score=args.min_score,
        fail_on_review=args.fail_on_review,
        fail_on_block=args.fail_on_block,
        max_monthly_cost=args.max_monthly_cost,
    )
    if failures:
        print("Quality gate failed:")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(2)


if __name__ == "__main__":
    main()
