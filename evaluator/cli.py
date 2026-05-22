from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core import evaluate_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate logged LLM workflow outputs.")
    parser.add_argument("input", type=Path, help="Path to workflow JSON input")
    parser.add_argument("--out", type=Path, default=Path("reports/sample-report.json"), help="Output report path")
    args = parser.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    report = evaluate_dataset(payload)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    summary = report["summary"]
    print(
        f"{report['suite']}: {summary['total']} outputs, "
        f"average={summary['average_score']:.2f}, "
        f"ship={summary['ship']}, review={summary['review']}, block={summary['block']}, "
        f"calibration={report['calibration']['accuracy']:.2f}"
    )


if __name__ == "__main__":
    main()
