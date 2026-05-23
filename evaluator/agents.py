from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AgentReview:
    agent: str
    status: str
    message: str
    evidence: list[str]


def reviewer_agent(item: dict[str, Any], result: dict[str, Any]) -> AgentReview:
    review_status = result["observability"]["review_status"]
    decision = result["decision"]
    status = "pass" if decision == "ship" and review_status == "approved" else "review"
    return AgentReview(
        "reviewer_agent",
        status,
        "Human review state supports shipping" if status == "pass" else "Human review or decision state needs attention",
        [f"decision={decision}", f"human_review={review_status}", f"workflow={item.get('workflow', 'unknown')}"],
    )


def source_grounding_agent(result: dict[str, Any]) -> AgentReview:
    score = result["scores"]["source_grounding"]
    missing_sources = [
        source for source in result["trace"]["required_sources"] if source not in result["evidence"]["source_hits"]
    ]
    return AgentReview(
        "source_grounding_agent",
        "pass" if score >= 0.75 and not missing_sources else "review",
        "Source grounding is strong" if score >= 0.75 and not missing_sources else "Source grounding is weak",
        [f"grounding={score:.2f}", f"missing_sources={', '.join(missing_sources) or 'none'}"],
    )


def hallucination_agent(result: dict[str, Any]) -> AgentReview:
    hits = result["evidence"]["forbidden_hits"]
    return AgentReview(
        "hallucination_agent",
        "pass" if not hits else "block",
        "No blocked claims found" if not hits else "Blocked claims found in output",
        hits or ["forbidden_claims=0"],
    )


def cost_agent(result: dict[str, Any]) -> AgentReview:
    score = result["scores"]["cost"]
    cost = result["observability"]["cost_usd"]
    return AgentReview(
        "cost_agent",
        "pass" if score >= 0.5 else "review",
        "Cost is within workflow threshold" if score >= 0.5 else "Cost is outside workflow threshold",
        [f"cost_usd={cost:.6f}", f"score={score:.2f}"],
    )


def latency_agent(result: dict[str, Any]) -> AgentReview:
    score = result["scores"]["latency"]
    latency = result["observability"]["latency_ms"]
    return AgentReview(
        "latency_agent",
        "pass" if score >= 0.5 else "review",
        "Latency is within workflow threshold" if score >= 0.5 else "Latency is outside workflow threshold",
        [f"latency_ms={latency}", f"score={score:.2f}"],
    )


def policy_agent(result: dict[str, Any]) -> AgentReview:
    high_issues = [issue for issue in result["issues"] if issue["severity"] == "high"]
    return AgentReview(
        "policy_agent",
        "pass" if not high_issues else "block",
        "No high-severity policy issues" if not high_issues else "High-severity issue requires block",
        [issue["type"] for issue in high_issues] or ["high_severity_issues=0"],
    )


def run_agent_reviews(item: dict[str, Any], result: dict[str, Any]) -> list[dict[str, Any]]:
    reviews = [
        reviewer_agent(item, result),
        source_grounding_agent(result),
        hallucination_agent(result),
        cost_agent(result),
        latency_agent(result),
        policy_agent(result),
    ]
    return [review.__dict__ for review in reviews]
