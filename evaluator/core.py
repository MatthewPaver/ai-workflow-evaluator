from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
import re
from difflib import SequenceMatcher


DEFAULT_WEIGHTS = {
    "accuracy": 0.28,
    "grounding": 0.24,
    "hallucination": 0.22,
    "latency": 0.12,
    "cost": 0.08,
    "review": 0.06,
}


@dataclass(frozen=True)
class Pricing:
    input_per_1k: float
    output_per_1k: float


def normalise(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[-–—/]", " ", text.casefold())).strip()


def contains_phrase(text: str, phrase: str) -> bool:
    return normalise(phrase) in normalise(text)


def phrase_similarity(text: str, phrase: str) -> float:
    text_normalised = normalise(text)
    phrase_normalised = normalise(phrase)
    if not phrase_normalised:
        return 1.0
    if phrase_normalised in text_normalised:
        return 1.0

    phrase_words = phrase_normalised.split()
    if len(phrase_words) <= 1:
        return 0.0

    text_words = text_normalised.split()
    if len(text_words) < len(phrase_words):
        return SequenceMatcher(None, text_normalised, phrase_normalised).ratio()

    window_scores = []
    for index in range(0, len(text_words) - len(phrase_words) + 1):
        window = " ".join(text_words[index : index + len(phrase_words)])
        window_scores.append(SequenceMatcher(None, window, phrase_normalised).ratio())
    return max(window_scores, default=0.0)


def phrase_matches(text: str, phrase: str, threshold: float) -> bool:
    return phrase_similarity(text, phrase) >= threshold


def score_ratio(matches: int, total: int) -> float:
    if total == 0:
        return 1.0
    return round(matches / total, 4)


def estimate_cost(tokens: dict[str, int], pricing: Pricing) -> float:
    input_tokens = int(tokens.get("input", 0))
    output_tokens = int(tokens.get("output", 0))
    cost = (input_tokens / 1000) * pricing.input_per_1k + (output_tokens / 1000) * pricing.output_per_1k
    return round(cost, 6)


def score_latency(latency_ms: int, target_ms: int, max_ms: int) -> float:
    if latency_ms <= target_ms:
        return 1.0
    if latency_ms >= max_ms:
        return 0.0
    return round(1 - ((latency_ms - target_ms) / (max_ms - target_ms)), 4)


def score_cost(cost: float, target_cost: float, max_cost: float) -> float:
    if cost <= target_cost:
        return 1.0
    if cost >= max_cost:
        return 0.0
    return round(1 - ((cost - target_cost) / (max_cost - target_cost)), 4)


def source_blob(sources: list[dict[str, str]]) -> str:
    return " ".join(f"{source.get('id', '')} {source.get('title', '')} {source.get('text', '')}" for source in sources)


def evaluate_item(item: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or {}
    pricing_data = item.get("pricing", config.get("pricing", {}))
    pricing = Pricing(
        input_per_1k=float(pricing_data.get("input_per_1k", 0.005)),
        output_per_1k=float(pricing_data.get("output_per_1k", 0.015)),
    )
    thresholds = item.get("thresholds", config.get("thresholds", {}))
    target_latency = int(thresholds.get("target_latency_ms", 1800))
    max_latency = int(thresholds.get("max_latency_ms", 6000))
    target_cost = float(thresholds.get("target_cost_usd", 0.01))
    max_cost = float(thresholds.get("max_cost_usd", 0.05))
    pass_score = float(thresholds.get("pass_score", 0.78))
    block_score = float(thresholds.get("block_score", 0.45))
    fact_match_threshold = float(thresholds.get("fact_match_threshold", 0.82))
    source_match_threshold = float(thresholds.get("source_match_threshold", 0.9))

    output = item.get("output", "")
    expected_facts = item.get("expected_facts", [])
    forbidden_claims = item.get("forbidden_claims", [])
    required_sources = item.get("required_sources", [])
    sources = item.get("sources", [])
    source_text = source_blob(sources)

    fact_hits = [fact for fact in expected_facts if phrase_matches(output, fact, fact_match_threshold)]
    missing_facts = [fact for fact in expected_facts if fact not in fact_hits]
    forbidden_hits = [claim for claim in forbidden_claims if contains_phrase(output, claim)]
    source_hits = [source_id for source_id in required_sources if contains_phrase(output, source_id)]

    source_terms = item.get("source_terms", [])
    source_term_hits = [
        term
        for term in source_terms
        if phrase_matches(output, term, source_match_threshold) and contains_phrase(source_text, term)
    ]

    accuracy = score_ratio(len(fact_hits), len(expected_facts))
    citation_score = score_ratio(len(source_hits), len(required_sources))
    source_term_score = score_ratio(len(source_term_hits), len(source_terms))
    grounding = round((citation_score * 0.6) + (source_term_score * 0.4), 4)
    hallucination = max(0.0, round(1 - (len(forbidden_hits) / max(len(forbidden_claims), 1)), 4))

    latency_ms = int(item.get("latency_ms", 0))
    latency = score_latency(latency_ms, target_latency, max_latency)
    cost_usd = estimate_cost(item.get("tokens", {}), pricing)
    cost = score_cost(cost_usd, target_cost, max_cost)

    review_status = item.get("human_review", {}).get("status", "not_reviewed")
    review = {"approved": 1.0, "review_required": 0.55, "blocked": 0.0, "not_reviewed": 0.35}.get(review_status, 0.35)

    weights = {**DEFAULT_WEIGHTS, **config.get("weights", {}), **item.get("weights", {})}
    overall = round(
        accuracy * weights["accuracy"]
        + grounding * weights["grounding"]
        + hallucination * weights["hallucination"]
        + latency * weights["latency"]
        + cost * weights["cost"]
        + review * weights["review"],
        4,
    )

    issues = []
    if missing_facts:
        issues.append({"severity": "medium", "type": "missing_facts", "items": missing_facts})
    if forbidden_hits:
        issues.append({"severity": "high", "type": "forbidden_claims", "items": forbidden_hits})
    if grounding < 0.75:
        issues.append({"severity": "medium", "type": "weak_grounding", "items": required_sources})
    if latency < 0.5:
        issues.append({"severity": "medium", "type": "latency", "items": [f"{latency_ms}ms"]})
    if cost < 0.5:
        issues.append({"severity": "low", "type": "cost", "items": [f"${cost_usd:.4f}"]})

    if forbidden_hits or overall < block_score:
        decision = "block"
    elif overall < pass_score or review_status != "approved":
        decision = "review"
    else:
        decision = "ship"

    return {
        "id": item["id"],
        "name": item["name"],
        "model": item.get("model", "unknown"),
        "workflow": item.get("workflow", "unknown"),
        "decision": decision,
        "overall_score": overall,
        "scores": {
            "accuracy": accuracy,
            "source_grounding": grounding,
            "hallucination_control": hallucination,
            "latency": latency,
            "cost": cost,
            "human_review": review,
        },
        "observability": {
            "latency_ms": latency_ms,
            "cost_usd": cost_usd,
            "input_tokens": int(item.get("tokens", {}).get("input", 0)),
            "output_tokens": int(item.get("tokens", {}).get("output", 0)),
            "review_status": review_status,
        },
        "evidence": {
            "matched_facts": fact_hits,
            "missing_facts": missing_facts,
            "forbidden_hits": forbidden_hits,
            "source_hits": source_hits,
            "source_term_hits": source_term_hits,
        },
        "issues": issues,
        "expected_decision": item.get("expected_decision"),
        "calibrated": item.get("expected_decision") in {None, decision},
    }


def evaluate_dataset(payload: dict[str, Any]) -> dict[str, Any]:
    config = payload.get("config", {})
    results = [evaluate_item(item, config) for item in payload.get("items", [])]
    decisions = {name: sum(1 for item in results if item["decision"] == name) for name in ["ship", "review", "block"]}
    avg_score = round(sum(item["overall_score"] for item in results) / max(len(results), 1), 4)
    calibrated_results = [item for item in results if item.get("expected_decision")]
    calibration_matches = sum(1 for item in calibrated_results if item["calibrated"])
    calibration_accuracy = score_ratio(calibration_matches, len(calibrated_results))
    return {
        "generated_at": payload.get("generated_at", datetime.now(timezone.utc).isoformat()),
        "suite": payload.get("suite", "AI Workflow Evaluator"),
        "summary": {
            "total": len(results),
            "average_score": avg_score,
            "ship": decisions["ship"],
            "review": decisions["review"],
            "block": decisions["block"],
        },
        "calibration": {
            "labelled": len(calibrated_results),
            "matches": calibration_matches,
            "accuracy": calibration_accuracy,
        },
        "results": results,
    }
