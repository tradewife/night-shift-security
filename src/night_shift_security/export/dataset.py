"""Public findings dataset export — severity-ranked JSON feed."""

import json
from datetime import datetime, timezone
from pathlib import Path

from night_shift_security.bridge.tokenomics import generate_tokenomics_risk_feed
from night_shift_security.data.schemas import AttackCandidateResult, Finding


def build_public_feed(findings: list[Finding], run_meta: dict) -> dict:
    """Build severity-ranked public API feed payload."""
    ranked = sorted(findings, key=lambda f: (f.severity_score, f.economic_impact_usd), reverse=True)

    return {
        "schema_version": "1.0",
        "track": "night-shift-security",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run": {
            "run_at": run_meta.get("run_at"),
            "elapsed_seconds": run_meta.get("elapsed_seconds"),
            "candidates_evaluated": run_meta.get("candidates_evaluated", 0),
            "candidates_passed_gates": run_meta.get("candidates_passed_gates", 0),
            "rediscovery_rate": run_meta.get("rediscovery", {}).get("rate", 0),
        },
        "summary": {
            "total_findings": len(ranked),
            "by_severity": _count_by_severity(ranked),
            "total_economic_impact_usd": sum(f.economic_impact_usd for f in ranked),
        },
        "findings": [_public_finding(f, rank) for rank, f in enumerate(ranked, start=1)],
    }


def _count_by_severity(findings: list[Finding]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.severity.value] = counts.get(f.severity.value, 0) + 1
    return counts


def _public_finding(f: Finding, rank: int) -> dict:
    return {
        "rank": rank,
        "finding_id": f.finding_id,
        "template_id": f.template_id,
        "target_id": f.target_id,
        "severity": f.severity.value,
        "severity_score": round(f.severity_score, 4),
        "economic_impact_usd": round(f.economic_impact_usd, 2),
        "capital_required_usd": round(f.capital_required_usd, 2),
        "reproducibility": round(f.reproducibility, 4),
        "confidence": round(f.confidence, 4),
        "parameters": f.parameters,
        "invariant_violations": [
            {"id": v.invariant_id, "description": v.description}
            for v in f.invariant_violations
        ],
        "mitigations": f.mitigations,
        "rediscovered_exploit_id": f.rediscovered_exploit_id or None,
        "reproduction_steps": [
            {"actor": s.actor, "action": s.action, "details": s.details}
            for s in f.reproduction_steps
        ],
    }


def export_dataset(
    findings: list[Finding],
    run_meta: dict,
    output_dir: Path,
    candidates: list[AttackCandidateResult] | None = None,
) -> dict[str, Path]:
    """
    Export public dataset artifacts:

    - dataset/latest.json      — full severity-ranked feed
    - dataset/feed.json        — minimal public API shape
    - dataset/findings.jsonl   — one finding per line
    - bridge/tokenomics_risk_feed.json — cross-track bridge for Tokenomics
    """
    dataset_dir = output_dir / "dataset"
    bridge_dir = output_dir / "bridge"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    bridge_dir.mkdir(parents=True, exist_ok=True)

    feed = build_public_feed(findings, run_meta)
    minimal = {
        "schema_version": feed["schema_version"],
        "generated_at": feed["generated_at"],
        "total": feed["summary"]["total_findings"],
        "findings": [
            {
                "rank": f["rank"],
                "finding_id": f["finding_id"],
                "template_id": f["template_id"],
                "severity": f["severity"],
                "severity_score": f["severity_score"],
                "economic_impact_usd": f["economic_impact_usd"],
            }
            for f in feed["findings"]
        ],
    }

    latest_path = dataset_dir / "latest.json"
    feed_path = dataset_dir / "feed.json"
    jsonl_path = dataset_dir / "findings.jsonl"
    bridge_path = bridge_dir / "tokenomics_risk_feed.json"

    with open(latest_path, "w") as f:
        json.dump(feed, f, indent=2, default=str)

    with open(feed_path, "w") as f:
        json.dump(minimal, f, indent=2)

    with open(jsonl_path, "w") as f:
        for item in feed["findings"]:
            f.write(json.dumps(item, default=str) + "\n")

    risk_feed = generate_tokenomics_risk_feed(findings, candidates or [])
    with open(bridge_path, "w") as f:
        json.dump(risk_feed, f, indent=2, default=str)

    return {
        "latest": latest_path,
        "feed": feed_path,
        "jsonl": jsonl_path,
        "tokenomics_bridge": bridge_path,
    }