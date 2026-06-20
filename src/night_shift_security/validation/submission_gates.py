"""Submission qualification gates — shared by loop, scan, and export."""

from __future__ import annotations

from night_shift_security.validation.task_verifier import (
    finding_balance_verified,
    finding_has_credible_reproduction,
)
from night_shift_security.bridge.wormhole_economic import wormhole_economic_impact_verified


def _candidate_payload(finding) -> dict:
    params = getattr(finding, "parameters", {}) or {}
    if isinstance(params.get("candidate"), dict):
        return params["candidate"]
    for evidence_name in ("fork_evidence", "solana_evidence"):
        evidence = getattr(finding, evidence_name, {}) or {}
        if isinstance(evidence.get("candidate"), dict):
            return evidence["candidate"]
    return {}


def _v4_candidate_submission_ok(finding) -> bool:
    candidate = _candidate_payload(finding)
    if not candidate:
        return False
    if int(candidate.get("candidate_schema_version") or 0) < 4:
        return False
    if candidate.get("target_pinned") is not True:
        return False

    source_ref = candidate.get("source_ref") if isinstance(candidate.get("source_ref"), dict) else {}
    if not (source_ref.get("commit") or candidate.get("source_commit")):
        return False

    entrypoint = candidate.get("entrypoint") if isinstance(candidate.get("entrypoint"), dict) else {}
    if entrypoint and not entrypoint.get("selector_or_discriminator"):
        return False

    artifact = str(candidate.get("reproduction_artifact") or "").strip()
    if not artifact:
        return False

    impact = candidate.get("impact_oracle") if isinstance(candidate.get("impact_oracle"), dict) else {}
    measured = impact.get("measured") is True
    fork_ev = getattr(finding, "fork_evidence", {}) or {}
    sol_ev = getattr(finding, "solana_evidence", {}) or {}
    measured = measured or int(fork_ev.get("balance_delta_wei") or 0) > 0
    measured = measured or int(fork_ev.get("token_delta") or fork_ev.get("token_delta_units") or 0) > 0
    measured = measured or int(sol_ev.get("balance_delta_lamports") or sol_ev.get("protocol_delta_lamports") or 0) > 0
    # NOTE: reserve_last_update_slot_delta alone does NOT constitute measured
    # impact -- advancing the slot is routine behavior on every refresh_reserve
    # call and produces no balance changes.  A true exploit must show actual
    # balance/token/lamport deltas (the lines above).  See lab notebook
    # 2026-06-20-false-positive-measurement-fix.md for the NSS-0013 incident.
    if not measured:
        return False

    failure_trace = candidate.get("failure_trace") if isinstance(candidate.get("failure_trace"), dict) else {}
    if failure_trace.get("blocking") is True:
        return False
    return True


def _wormhole_submission_ok(finding) -> bool:
    target = str(getattr(finding, "target_id", "") or "")
    evidence = getattr(finding, "fork_evidence", {}) or {}
    evidence_target = str(evidence.get("target_id") or "")
    if "wormhole" not in target and not evidence_target.startswith("wormhole-"):
        return True
    if evidence.get("triage_surface_verified") and not wormhole_economic_impact_verified(evidence):
        return False
    return True


def qualifies_for_submission(finding, score) -> bool:
    """Engine + scoring gate for autonomous loop stop (human still posts externally)."""
    tier = finding.reproduction_tier or (
        "fork_reproduced" if finding.fork_reproduced else "simulation"
    )
    grade = finding.evidence_grade or 0
    return (
        score.submission_recommendation == "submit_now"
        and grade >= 4
        and tier in ("fork_reproduced", "solana_validator")
        and not finding.catalog_analogue
        and finding.deployed_viable
        and finding_has_credible_reproduction(finding)
        and finding_balance_verified(finding)
        and _wormhole_submission_ok(finding)
        and _v4_candidate_submission_ok(finding)
    )
