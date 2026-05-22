from __future__ import annotations

import json
import unittest
from pathlib import Path

from evaluator.core import evaluate_dataset, evaluate_item


class EvaluatorTests(unittest.TestCase):
    def test_approved_grounded_output_can_ship(self) -> None:
        item = {
            "id": "ok",
            "name": "Grounded answer",
            "workflow": "qa",
            "model": "test-model",
            "output": "Source S1 says refunds take 5 days.",
            "expected_facts": ["refunds take 5 days"],
            "forbidden_claims": ["refunds are instant"],
            "required_sources": ["S1"],
            "source_terms": ["refunds", "5 days"],
            "sources": [{"id": "S1", "title": "Policy", "text": "Refunds take 5 days."}],
            "tokens": {"input": 500, "output": 80},
            "latency_ms": 900,
            "human_review": {"status": "approved"},
        }
        result = evaluate_item(item)
        self.assertEqual(result["decision"], "ship")
        self.assertGreaterEqual(result["scores"]["accuracy"], 1.0)

    def test_forbidden_claim_blocks_output(self) -> None:
        item = {
            "id": "bad",
            "name": "Bad answer",
            "output": "Refunds are instant.",
            "expected_facts": ["refunds take 5 days"],
            "forbidden_claims": ["refunds are instant"],
            "required_sources": ["S1"],
            "source_terms": ["refunds"],
            "sources": [{"id": "S1", "title": "Policy", "text": "Refunds take 5 days."}],
            "tokens": {"input": 500, "output": 80},
            "latency_ms": 900,
            "human_review": {"status": "approved"},
        }
        result = evaluate_item(item)
        self.assertEqual(result["decision"], "block")
        self.assertTrue(result["evidence"]["forbidden_hits"])

    def test_near_phrase_match_counts_for_accuracy(self) -> None:
        item = {
            "id": "near",
            "name": "Near phrase",
            "output": "Source S1 says the repository turns project schedule files into delivery risk reports.",
            "expected_facts": ["turns project schedule files into delivery-risk reporting"],
            "forbidden_claims": ["deployed SaaS product"],
            "required_sources": ["S1"],
            "source_terms": ["project schedule files"],
            "sources": [{"id": "S1", "title": "README", "text": "Turns project schedule files into delivery-risk reporting."}],
            "tokens": {"input": 500, "output": 80},
            "latency_ms": 900,
            "human_review": {"status": "approved"},
        }
        result = evaluate_item(item)
        self.assertEqual(result["scores"]["accuracy"], 1.0)

    def test_sample_dataset_has_expected_shape(self) -> None:
        payload = json.loads(Path("examples/workflows.json").read_text())
        report = evaluate_dataset(payload)
        self.assertEqual(report["summary"]["total"], 3)
        self.assertEqual(report["generated_at"], "2026-05-22T00:00:00+00:00")
        self.assertEqual(report["calibration"]["labelled"], 3)
        self.assertEqual(report["calibration"]["accuracy"], 1.0)
        self.assertEqual(len(report["results"]), 3)
        self.assertIn(report["results"][0]["decision"], {"ship", "review", "block"})

    def test_portfolio_dataset_catches_overclaim(self) -> None:
        payload = json.loads(Path("examples/portfolio-workflows.json").read_text())
        report = evaluate_dataset(payload)
        decisions = {item["id"]: item["decision"] for item in report["results"]}
        self.assertEqual(report["summary"]["total"], 4)
        self.assertEqual(report["calibration"]["accuracy"], 1.0)
        self.assertEqual(decisions["repo-recommender-overclaim"], "block")


if __name__ == "__main__":
    unittest.main()
