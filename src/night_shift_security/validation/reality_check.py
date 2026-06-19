"""Lab vs deployed reality classification — architecture v2.1 / METHODOLOGY."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from night_shift_security.data.schemas import AttackCandidateResult, Finding


REPRODUCTION_TIERS = frozenset({
    "simulation",
    "solana_fixture",
    "solana_validator",
    "fork_reproduced",
})

KLEND_HARNESS_METHOD = "solana_klend_harness"

DEPLOYED_TIERS = frozenset({"solana_validator", "fork_reproduced"})


@dataclass(frozen=True)
class RealityCheck:
    reproduction_tier: str
    deployed_viable: bool
    catalog_analogue: bool
    submission_readiness: str


def infer_reproduction_method(
    *,
    solana_evidence: dict[str, Any] | None = None,
    fork_reproduced: bool = False,
    solana_reproduced: bool = False,
) -> str:
    evidence = solana_evidence or {}
    method = str(evidence.get("method", "") or "")
    if method == "solana_measured_oracle" and evidence.get("evidence_kind") == "solana_measured_oracle.v1":
        return "solana_validator"
    if method == KLEND_HARNESS_METHOD and evidence.get("balance_verified"):
        return "solana_validator"
    if method in REPRODUCTION_TIERS:
        return method
    if fork_reproduced:
        return "fork_reproduced"
    if solana_reproduced:
        return "solana_reproduced"
    return "simulation"


def _is_catalog_analogue(
    *,
    target_id: str,
    solana_evidence: dict[str, Any] | None = None,
    fork_evidence: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> bool:
    meta = metadata or {}
    if meta.get("catalog_analogue"):
        return True
    evidence = solana_evidence or fork_evidence or {}
    anchor = str(evidence.get("exploit_id", "") or evidence.get("target_id", "") or "")
    novel_native = {
        "kamino-klend",
        "wormhole-live-core",
        "wormhole-live-token-bridge",
    }
    if anchor in novel_native or anchor.startswith("wormhole-live-"):
        return False
    if anchor and target_id and anchor != target_id:
        return True
    return False


def _submission_readiness(
    reproduction_tier: str,
    *,
    catalog_analogue: bool,
    evidence_grade: int,
) -> str:
    if reproduction_tier in DEPLOYED_TIERS and not catalog_analogue and evidence_grade >= 3:
        return "strict"
    if reproduction_tier in ("solana_fixture", "fork_reproduced", "solana_validator"):
        return "shoestring"
    return "draft"


def compute_reality_check_candidate(candidate: AttackCandidateResult) -> RealityCheck:
    tier = infer_reproduction_method(
        solana_evidence=candidate.solana_evidence,
        fork_reproduced=candidate.fork_reproduced,
        solana_reproduced=candidate.solana_reproduced,
    )
    meta = dict(candidate.vector.metadata or {})
    analogue = _is_catalog_analogue(
        target_id=candidate.vector.target_id,
        solana_evidence=candidate.solana_evidence,
        fork_evidence=candidate.fork_evidence,
        metadata=meta,
    )
    return RealityCheck(
        reproduction_tier=tier,
        deployed_viable=tier in DEPLOYED_TIERS,
        catalog_analogue=analogue,
        submission_readiness=_submission_readiness(
            tier,
            catalog_analogue=analogue,
            evidence_grade=candidate.evidence_grade,
        ),
    )


def compute_reality_check_finding(finding: Finding) -> RealityCheck:
    tier = infer_reproduction_method(
        solana_evidence=finding.solana_evidence,
        fork_reproduced=finding.fork_reproduced,
        solana_reproduced=finding.solana_reproduced,
    )
    analogue = _is_catalog_analogue(
        target_id=finding.target_id,
        solana_evidence=finding.solana_evidence,
        fork_evidence=finding.fork_evidence,
    )
    return RealityCheck(
        reproduction_tier=tier,
        deployed_viable=tier in DEPLOYED_TIERS,
        catalog_analogue=analogue,
        submission_readiness=_submission_readiness(
            tier,
            catalog_analogue=analogue,
            evidence_grade=finding.evidence_grade,
        ),
    )


def apply_reality_check_candidate(candidate: AttackCandidateResult) -> AttackCandidateResult:
    rc = compute_reality_check_candidate(candidate)
    candidate.reproduction_tier = rc.reproduction_tier
    candidate.deployed_viable = rc.deployed_viable
    candidate.catalog_analogue = rc.catalog_analogue
    candidate.submission_readiness = rc.submission_readiness
    meta = dict(candidate.vector.metadata or {})
    meta["reproduction_tier"] = rc.reproduction_tier
    meta["deployed_viable"] = rc.deployed_viable
    meta["catalog_analogue"] = rc.catalog_analogue
    meta["submission_readiness"] = rc.submission_readiness
    candidate.vector.metadata = meta
    return candidate


def apply_reality_check_finding(finding: Finding) -> Finding:
    rc = compute_reality_check_finding(finding)
    finding.reproduction_tier = rc.reproduction_tier
    finding.deployed_viable = rc.deployed_viable
    finding.catalog_analogue = rc.catalog_analogue
    finding.submission_readiness = rc.submission_readiness
    return finding