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
        self.assertEqual(report["dataset"]["id"], "workflow-quality-fixtures")
        self.assertEqual(report["scorers"]["version"], "deterministic-v1")
        self.assertIn("baseline", report)
        self.assertEqual(len(report["results"]), 3)
        self.assertIn(report["results"][0]["decision"], {"ship", "review", "block"})
        self.assertIn("trace", report["results"][0])
        self.assertEqual(len(report["results"][0]["agent_reviews"]), 8)
        self.assertIn("source_grounding_agent", report["scorers"]["agents"])
        self.assertIn("model_router_agent", report["scorers"]["agents"])

    def test_portfolio_dataset_catches_overclaim(self) -> None:
        payload = json.loads(Path("examples/portfolio-workflows.json").read_text())
        report = evaluate_dataset(payload)
        decisions = {item["id"]: item["decision"] for item in report["results"]}
        overclaim = next(item for item in report["results"] if item["id"] == "repo-recommender-overclaim")
        self.assertEqual(report["summary"]["total"], 4)
        self.assertEqual(report["calibration"]["accuracy"], 1.0)
        self.assertEqual(decisions["repo-recommender-overclaim"], "block")
        self.assertEqual(report["dataset"]["id"], "portfolio-copy-grounding")
        self.assertTrue(any(item["type"] == "forbidden_claim" for item in overclaim["trace"]["explanations"]))
        self.assertTrue(any(item["agent"] == "policy_agent" for item in overclaim["agent_reviews"]))

    def test_ai_ops_dataset_tracks_multimodal_cost_and_routing(self) -> None:
        payload = json.loads(Path("examples/ai-ops-workflows.json").read_text())
        report = evaluate_dataset(payload)
        decisions = {item["id"]: item["decision"] for item in report["results"]}
        screenshot_item = next(item for item in report["results"] if item["id"] == "screen-support-001")
        blocked_item = next(item for item in report["results"] if item["id"] == "product-image-004")

        self.assertEqual(report["summary"]["total"], 4)
        self.assertEqual(report["dataset"]["id"], "ai-ops-multimodal-cost-quality")
        self.assertEqual(report["ai_ops"]["multimodal_items"], 4)
        self.assertGreater(report["ai_ops"]["projected_monthly_cost_usd"], 0)
        self.assertEqual(decisions["product-image-004"], "block")
        self.assertIn("screenshots", " ".join(screenshot_item["observability"]["modalities"]))
        self.assertGreater(screenshot_item["observability"]["multimodal_cost_usd"], 0)
        self.assertEqual(blocked_item["observability"]["route"], "block_or_rewrite")
        self.assertTrue(any(item["agent"] == "multimodal_cost_agent" for item in screenshot_item["agent_reviews"]))


if __name__ == "__main__":
    unittest.main()
