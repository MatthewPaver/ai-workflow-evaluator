from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SOURCE_CANDIDATES = [
    "README.md",
    "docs/README.md",
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "Makefile",
    "LICENSE",
]

FORBIDDEN_DEFAULTS = [
    "production-grade SaaS",
    "enterprise deployment",
    "guaranteed accuracy",
    "fully autonomous",
]


def normalise_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "project"


def compact_text(text: str, limit: int = 1400) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit].rstrip()


def first_heading(readme: str, fallback: str) -> str:
    match = re.search(r"^#\s+(.+)$", readme, flags=re.MULTILINE)
    return match.group(1).strip() if match else fallback


def first_paragraph(readme: str) -> str:
    blocks = [block.strip() for block in re.split(r"\n\s*\n", readme) if block.strip()]
    for block in blocks:
        if block.startswith("#") or block.startswith("[!") or block.startswith("<"):
            continue
        cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", block)
        cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
        return compact_text(cleaned, 360)
    return ""


def sentence_facts(text: str, limit: int = 3) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    facts = []
    for sentence in sentences:
        cleaned = sentence.strip(" -\n\t")
        if 24 <= len(cleaned) <= 180:
            facts.append(cleaned.rstrip("."))
        if len(facts) >= limit:
            break
    return facts


def source_terms_from_text(text: str, project_name: str) -> list[str]:
    terms = [project_name]
    keyword_patterns = [
        r"\bPython\b",
        r"\bTypeScript\b",
        r"\bFastAPI\b",
        r"\bNext\.js\b",
        r"\bDuckDB\b",
        r"\bStreamlit\b",
        r"\bFlask\b",
        r"\bPower BI\b",
        r"\bpytest\b",
        r"\bGitHub Actions\b",
        r"\bDocker\b",
        r"\bPostgreSQL\b",
        r"\bRedis\b",
    ]
    for pattern in keyword_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            terms.append(match.group(0))
    seen = set()
    return [term for term in terms if not (term.lower() in seen or seen.add(term.lower()))][:8]


def read_sources(project_path: Path) -> list[dict[str, str]]:
    sources = []
    for index, relative in enumerate(SOURCE_CANDIDATES, start=1):
        path = project_path / relative
        if not path.exists() or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if not text.strip():
            continue
        sources.append(
            {
                "id": f"S{index}",
                "title": relative,
                "text": compact_text(text),
            }
        )
    return sources


def build_project_suite(project_path: Path, *, output: str | None = None, model: str = "project-summary-draft") -> dict[str, Any]:
    project_path = project_path.resolve()
    sources = read_sources(project_path)
    if not sources:
        raise FileNotFoundError(f"No supported project files found in {project_path}")

    readme_source = next((source for source in sources if source["title"] == "README.md"), sources[0])
    readme_path = project_path / readme_source["title"]
    readme_text = readme_path.read_text(encoding="utf-8", errors="ignore") if readme_path.exists() else readme_source["text"]
    project_name = first_heading(readme_text, project_path.name)
    paragraph = first_paragraph(readme_text)
    expected_facts = sentence_facts(paragraph) or [project_name]
    required_sources = [readme_source["id"]]

    source_terms = source_terms_from_text(" ".join(source["text"] for source in sources), project_name)
    output_text = output or f"Source {readme_source['id']} describes {project_name}. {paragraph or project_name}"
    approx_tokens = max(200, round(len(output_text.split()) * 1.4))

    return {
        "suite": f"{project_name} project summary gate",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "config": {
            "dataset_id": f"{normalise_slug(project_name)}-project-summary-gate",
            "dataset_version": "v1",
            "scorer_version": "deterministic-v2-project-ingest",
            "thresholds": {
                "target_latency_ms": 2000,
                "max_latency_ms": 6500,
                "target_cost_usd": 0.012,
                "max_cost_usd": 0.07,
                "pass_score": 0.78,
                "block_score": 0.45,
            },
        },
        "items": [
            {
                "id": f"{normalise_slug(project_name)}-summary-001",
                "name": "Project summary grounding",
                "workflow": "project_summary_review",
                "model": model,
                "risk_level": "low",
                "output": output_text,
                "expected_facts": expected_facts,
                "forbidden_claims": FORBIDDEN_DEFAULTS,
                "required_sources": required_sources,
                "source_terms": source_terms,
                "sources": sources,
                "modalities": {"text": True},
                "tokens": {
                    "input": sum(max(1, len(source["text"].split())) for source in sources),
                    "output": approx_tokens,
                },
                "volume": {"monthly_runs": 100},
                "latency_ms": 1200,
                "expected_decision": "ship",
                "human_review": {"status": "approved"},
            }
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a starter evaluator suite from a project folder.")
    parser.add_argument("project", type=Path, help="Path to the project to inspect")
    parser.add_argument("--out", type=Path, required=True, help="Path to write the generated workflow suite")
    parser.add_argument("--output", help="Optional AI-generated output to test against the project evidence")
    parser.add_argument("--model", default="project-summary-draft", help="Model or workflow label to store in the suite")
    args = parser.parse_args()

    suite = build_project_suite(args.project, output=args.output, model=args.model)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(suite, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.out} with {len(suite['items'])} item(s) and {len(suite['items'][0]['sources'])} source(s)")


if __name__ == "__main__":
    main()
