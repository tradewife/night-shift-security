"""Bounty candidate ledger — ranked findings + yield-engine signals."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from night_shift_security.bridge.tokenomics import _TEMPLATE_TRIGGERS
from night_shift_security.bounty.scoring import (
    BountyScoreResult,
    compute_bounty_score,
    resolve_program_for_finding,
    score_result_to_dict,
)
from night_shift_security.data.bounty_program import BountyProgram
from night_shift_security.data.schemas import Finding, Severity
from night_shift_security.validation.evidence_grading import effective_evidence_grade


@dataclass(frozen=True)
class ScoredFinding:
    finding: Finding
    score: BountyScoreResult
    program: BountyProgram | None


def _monitoring_hint(finding: Finding) -> str:
    template = finding.template_id
    params = finding.parameters or {}
    if template == "access_control_escalation":
        role = params.get("target_role", "admin")
        return f"{role}_role_escalation"
    if template == "governance_capture":
        return "governance_flash_loan" if params.get("use_flash_loan") else "governance_timelock_bypass"
    if template == "flash_loan_oracle":
        return "oracle_price_manipulation"
    if template == "reentrancy":
        return f"reentrancy_{params.get('target_function', 'withdraw')}"
    if template == "composability_risk":
        return "cross_protocol_composability"
    return template


def _yield_signals(finding: Finding) -> dict[str, Any]:
    triggers = _TEMPLATE_TRIGGERS.get(finding.template_id, {})
    return {
        "attack_surface": triggers.get("attack_surface", finding.template_id),
        "monitoring_hint": _monitoring_hint(finding),
        "severity": finding.severity.value if isinstance(finding.severity, Severity) else str(finding.severity),
    }


def rank_findings_by_bounty_score(
    findings: list[Finding],
    *,
    min_readiness: float = 0.0,
    min_evidence_grade: int = 3,
) -> list[ScoredFinding]:
    scored: list[ScoredFinding] = []
    for finding in findings:
        tier = finding.reproduction_tier or finding.solana_evidence.get("method", "")
        track = "shoestring" if tier in ("solana_fixture", "catalog_solana") else "pipeline"
        if effective_evidence_grade(finding, track=track) < min_evidence_grade:
            continue
        program = resolve_program_for_finding(finding)
        score = compute_bounty_score(finding, program)
        if score.bounty_readiness < min_readiness:
            continue
        scored.append(ScoredFinding(finding=finding, score=score, program=program))

    scored.sort(
        key=lambda s: (s.score.bounty_readiness, s.score.expected_payout_proxy_usd),
        reverse=True,
    )
    return scored


def candidate_record(scored: ScoredFinding, *, run_at: str | None = None) -> dict[str, Any]:
    finding = scored.finding
    program = scored.program
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_at": run_at,
        "finding_id": finding.finding_id,
        "target_id": finding.target_id,
        "template_id": finding.template_id,
        "catalog_exploit_id": finding.rediscovered_exploit_id or finding.solana_evidence.get("exploit_id"),
        "platform": scored.score.platform or (program.platform if program else ""),
        "immunefi_program": program.slug if program else "",
        "bounty_readiness": scored.score.bounty_readiness,
        "expected_payout_proxy_usd": scored.score.expected_payout_proxy_usd,
        "confidence_band": scored.score.confidence_band,
        "submission_recommendation": scored.score.submission_recommendation,
        "evidence_grade": finding.evidence_grade,
        "reproduction_tier": finding.reproduction_tier or finding.solana_evidence.get("method", "simulation"),
        "catalog_analogue": finding.catalog_analogue,
        "economic_impact_usd": finding.economic_impact_usd,
        "score_components": scored.score.score_components,
        "yield_signals": _yield_signals(finding),
        "bounty_score": score_result_to_dict(scored.score),
    }


def write_bounty_candidates_jsonl(
    scored: list[ScoredFinding],
    path: Path,
    *,
    run_at: str | None = None,
    append: bool = False,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with path.open(mode, encoding="utf-8") as handle:
        for item in scored:
            record = candidate_record(item, run_at=run_at)
            handle.write(json.dumps(record, default=str) + "\n")
    return path