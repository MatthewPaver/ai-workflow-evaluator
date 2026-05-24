from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
import re
from difflib import SequenceMatcher
from evaluator.agents import run_agent_reviews


DEFAULT_WEIGHTS = {
    "accuracy": 0.28,
    "grounding": 0.24,
    "hallucination": 0.22,
    "latency": 0.12,
    "cost": 0.08,
    "review": 0.06,
}

DEFAULT_SCORER_VERSION = "deterministic-v1"


@dataclass(frozen=True)
class Pricing:
    input_per_1k: float
    output_per_1k: float
    image_usd: float = 0.002
    screenshot_usd: float = 0.002
    pdf_page_usd: float = 0.0004
    audio_minute_usd: float = 0.006


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


def estimate_multimodal_cost(modalities: dict[str, Any], pricing: Pricing) -> float:
    images = int(modalities.get("images", 0))
    screenshots = int(modalities.get("screenshots", 0))
    pdf_pages = int(modalities.get("pdf_pages", 0))
    audio_minutes = float(modalities.get("audio_minutes", 0))
    cost = (
        images * pricing.image_usd
        + screenshots * pricing.screenshot_usd
        + pdf_pages * pricing.pdf_page_usd
        + audio_minutes * pricing.audio_minute_usd
    )
    return round(cost, 6)


def estimate_monthly_cost(per_run_cost: float, volume: dict[str, Any]) -> float:
    monthly_runs = int(volume.get("monthly_runs", 0))
    return round(per_run_cost * monthly_runs, 4)


def modality_summary(modalities: dict[str, Any]) -> list[str]:
    summary = []
    if modalities.get("text", True):
        summary.append("text")
    for key, label in [
        ("images", "images"),
        ("screenshots", "screenshots"),
        ("pdf_pages", "PDF pages"),
        ("audio_minutes", "audio minutes"),
    ]:
        value = modalities.get(key, 0)
        if value:
            summary.append(f"{value} {label}")
    return summary or ["text"]


def recommend_route(
    *,
    decision: str,
    risk_level: str,
    grounding: float,
    cost: float,
    latency: float,
    review_status: str,
    has_multimodal_input: bool,
) -> dict[str, str]:
    if decision == "block":
        return {
            "route": "block_or_rewrite",
            "reason": "Blocked claim, weak score, or policy issue means this should not reach users.",
        }
    if risk_level == "high" or review_status != "approved":
        return {
            "route": "strong_model_plus_human_review",
            "reason": "High-risk or unapproved workflow needs stronger reasoning and explicit sign-off.",
        }
    if grounding < 0.75:
        return {
            "route": "retrieve_more_context",
            "reason": "Evidence coverage is too weak for a confident answer.",
        }
    if has_multimodal_input and cost < 0.5:
        return {
            "route": "compress_inputs_or_use_cheaper_model",
            "reason": "Multimodal inputs are driving spend above the workflow threshold.",
        }
    if latency < 0.5:
        return {
            "route": "async_queue_or_faster_model",
            "reason": "Latency is too high for an interactive workflow.",
        }
    if risk_level == "low" and cost >= 0.75 and latency >= 0.75:
        return {
            "route": "small_model_auto_gate",
            "reason": "Low-risk workflow is grounded, cheap, and fast enough for automated gating.",
        }
    return {
        "route": "standard_model_review_gate",
        "reason": "Workflow can run through the normal quality gate before shipping.",
    }


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


def issue_explanations(
    *,
    output: str,
    missing_facts: list[str],
    forbidden_hits: list[str],
    required_sources: list[str],
    source_hits: list[str],
    sources: list[dict[str, str]],
) -> list[dict[str, Any]]:
    source_lookup = {source.get("id", ""): source for source in sources}
    explanations: list[dict[str, Any]] = []

    for fact in missing_facts:
        explanations.append(
            {
                "type": "missing_fact",
                "expected": fact,
                "actual": "Not found in the output.",
                "source": next((source.get("title", "Source evidence") for source in sources if contains_phrase(source.get("text", ""), fact)), "Source evidence"),
            }
        )

    for claim in forbidden_hits:
        explanations.append(
            {
                "type": "forbidden_claim",
                "expected": f"Output must not claim: {claim}",
                "actual": claim,
                "source": "Blocked claim list",
            }
        )

    missing_sources = [source_id for source_id in required_sources if source_id not in source_hits]
    for source_id in missing_sources:
        source = source_lookup.get(source_id, {})
        explanations.append(
            {
                "type": "missing_source",
                "expected": f"Reference source {source_id}",
                "actual": "Source ID was not cited in the output.",
                "source": source.get("title", source_id),
            }
        )

    if not explanations:
        explanations.append(
            {
                "type": "passed",
                "expected": "Required facts, sources, blocked claims, thresholds, and review status aligned.",
                "actual": output[:220],
                "source": "Evaluator checks",
            }
        )

    return explanations


def evaluate_item(item: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or {}
    pricing_data = item.get("pricing", config.get("pricing", {}))
    pricing = Pricing(
        input_per_1k=float(pricing_data.get("input_per_1k", 0.005)),
        output_per_1k=float(pricing_data.get("output_per_1k", 0.015)),
        image_usd=float(pricing_data.get("image_usd", 0.002)),
        screenshot_usd=float(pricing_data.get("screenshot_usd", 0.002)),
        pdf_page_usd=float(pricing_data.get("pdf_page_usd", 0.0004)),
        audio_minute_usd=float(pricing_data.get("audio_minute_usd", 0.006)),
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
    modalities = item.get("modalities", {"text": True})
    token_cost_usd = estimate_cost(item.get("tokens", {}), pricing)
    multimodal_cost_usd = estimate_multimodal_cost(modalities, pricing)
    cost_usd = round(token_cost_usd + multimodal_cost_usd, 6)
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

    volume = item.get("volume", {})
    monthly_cost_usd = estimate_monthly_cost(cost_usd, volume)
    has_multimodal_input = any(float(modalities.get(key, 0)) > 0 for key in ["images", "screenshots", "pdf_pages", "audio_minutes"])
    risk_level = item.get("risk_level", "medium")
    route = recommend_route(
        decision=decision,
        risk_level=risk_level,
        grounding=grounding,
        cost=cost,
        latency=latency,
        review_status=review_status,
        has_multimodal_input=has_multimodal_input,
    )

    result = {
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
            "token_cost_usd": token_cost_usd,
            "multimodal_cost_usd": multimodal_cost_usd,
            "monthly_cost_usd": monthly_cost_usd,
            "input_tokens": int(item.get("tokens", {}).get("input", 0)),
            "output_tokens": int(item.get("tokens", {}).get("output", 0)),
            "review_status": review_status,
            "risk_level": risk_level,
            "monthly_runs": int(volume.get("monthly_runs", 0)),
            "modalities": modality_summary(modalities),
            "route": route["route"],
            "route_reason": route["reason"],
        },
        "evidence": {
            "matched_facts": fact_hits,
            "missing_facts": missing_facts,
            "forbidden_hits": forbidden_hits,
            "source_hits": source_hits,
            "source_term_hits": source_term_hits,
        },
        "trace": {
            "output_excerpt": output[:360],
            "expected_facts": expected_facts,
            "forbidden_claims": forbidden_claims,
            "required_sources": required_sources,
            "source_titles": [f"{source.get('id', '')}: {source.get('title', '')}".strip() for source in sources],
            "modalities": modality_summary(modalities),
            "route": route,
            "explanations": issue_explanations(
                output=output,
                missing_facts=missing_facts,
                forbidden_hits=forbidden_hits,
                required_sources=required_sources,
                source_hits=source_hits,
                sources=sources,
            ),
        },
        "issues": issues,
        "expected_decision": item.get("expected_decision"),
        "calibrated": item.get("expected_decision") in {None, decision},
    }
    result["agent_reviews"] = run_agent_reviews(item, result)
    return result


def evaluate_dataset(payload: dict[str, Any]) -> dict[str, Any]:
    config = payload.get("config", {})
    results = [evaluate_item(item, config) for item in payload.get("items", [])]
    decisions = {name: sum(1 for item in results if item["decision"] == name) for name in ["ship", "review", "block"]}
    avg_score = round(sum(item["overall_score"] for item in results) / max(len(results), 1), 4)
    total_cost = round(sum(item["observability"]["cost_usd"] for item in results), 6)
    total_monthly_cost = round(sum(item["observability"]["monthly_cost_usd"] for item in results), 4)
    multimodal_items = sum(
        1
        for item in results
        if any(label != "text" for label in item["observability"].get("modalities", []))
    )
    routes = {
        route: sum(1 for item in results if item["observability"].get("route") == route)
        for route in sorted({item["observability"].get("route") for item in results})
    }
    calibrated_results = [item for item in results if item.get("expected_decision")]
    calibration_matches = sum(1 for item in calibrated_results if item["calibrated"])
    calibration_accuracy = score_ratio(calibration_matches, len(calibrated_results))
    dataset_id = config.get("dataset_id", normalise(payload.get("suite", "ai-workflow-evaluator")).replace(" ", "-"))
    scorer_version = config.get("scorer_version", DEFAULT_SCORER_VERSION)
    baseline = config.get("baseline", {})
    return {
        "generated_at": payload.get("generated_at", datetime.now(timezone.utc).isoformat()),
        "suite": payload.get("suite", "AI Workflow Evaluator"),
        "dataset": {
            "id": dataset_id,
            "version": config.get("dataset_version", "v1"),
            "items": len(results),
        },
        "scorers": {
            "version": scorer_version,
            "type": "deterministic",
            "count": 14,
            "agents": [
                "reviewer_agent",
                "source_grounding_agent",
                "hallucination_agent",
                "cost_agent",
                "latency_agent",
                "policy_agent",
                "model_router_agent",
                "multimodal_cost_agent",
            ],
        },
        "baseline": {
            "label": baseline.get("label", "Previous accepted run"),
            "average_score": float(baseline.get("average_score", avg_score)),
            "ship": int(baseline.get("ship", decisions["ship"])),
            "review": int(baseline.get("review", decisions["review"])),
            "block": int(baseline.get("block", decisions["block"])),
            "calibration": float(baseline.get("calibration", calibration_accuracy)),
        },
        "summary": {
            "total": len(results),
            "average_score": avg_score,
            "ship": decisions["ship"],
            "review": decisions["review"],
            "block": decisions["block"],
        },
        "ai_ops": {
            "total_run_cost_usd": total_cost,
            "projected_monthly_cost_usd": total_monthly_cost,
            "multimodal_items": multimodal_items,
            "routes": routes,
        },
        "calibration": {
            "labelled": len(calibrated_results),
            "matches": calibration_matches,
            "accuracy": calibration_accuracy,
        },
        "results": results,
    }
