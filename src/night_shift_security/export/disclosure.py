"""Responsible disclosure workflow — embargo, redaction, and publication."""

import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from night_shift_security.data.schemas import Finding, Severity

VALID_STATUSES = frozenset({"draft", "embargoed", "disclosed", "redacted"})

# Severity thresholds requiring embargo before public disclosure
_EMBARGO_SEVERITIES = frozenset({Severity.CRITICAL, Severity.HIGH})

# Fields redacted from public feed while embargoed
_REDACTED_STEP_ACTIONS = frozenset({
    "call_withdraw",
    "call_redeem",
    "call_claim",
    "execute_privileged_action",
    "drain_via_new_logic",
    "extract_value",
    "withdraw",
    "execute_proposal",
})


def classify_disclosure_status(finding: Finding) -> str:
    """Assign initial disclosure status based on severity and exploit rediscovery."""
    return classify_severity_disclosure(finding.severity)


def classify_severity_disclosure(severity: Severity) -> str:
    """Assign disclosure status from severity alone."""
    if severity in _EMBARGO_SEVERITIES:
        return "embargoed"
    return "draft"


def apply_disclosure_policy(findings: list[Finding]) -> list[Finding]:
    """Tag findings with disclosure status if not already set."""
    updated: list[Finding] = []
    for f in findings:
        status = f.disclosure_status
        if status not in VALID_STATUSES:
            status = classify_disclosure_status(f)
        updated.append(replace(f, disclosure_status=status))
    return updated


def redact_finding_for_public(finding: Finding) -> dict:
    """Produce public-safe finding payload respecting disclosure status."""
    base = {
        "finding_id": finding.finding_id,
        "template_id": finding.template_id,
        "target_id": finding.target_id,
        "severity": finding.severity.value,
        "severity_score": round(finding.severity_score, 4),
        "economic_impact_usd": round(finding.economic_impact_usd, 2),
        "capital_required_usd": round(finding.capital_required_usd, 2),
        "reproducibility": round(finding.reproducibility, 4),
        "confidence": round(finding.confidence, 4),
        "disclosure_status": finding.disclosure_status,
        "mitigations": finding.mitigations,
        "rediscovered_exploit_id": finding.rediscovered_exploit_id or None,
        "fork_reproduced": finding.fork_reproduced,
    }
    if finding.fork_reproduced:
        base["fork_block_number"] = finding.fork_block_number
        base["fork_evidence"] = {
            k: finding.fork_evidence.get(k)
            for k in ("target_id", "exploit_id", "block_number", "method", "impact_usd")
            if finding.fork_evidence.get(k) is not None
        }
    if finding.severity_score_base and finding.severity_score_base != finding.severity_score:
        base["severity_score_base"] = round(finding.severity_score_base, 4)

    if finding.disclosure_status in ("embargoed", "redacted"):
        base["parameters"] = _redact_parameters(finding.parameters)
        base["invariant_violations"] = [
            {"id": v.invariant_id, "description": v.description}
            for v in finding.invariant_violations
        ]
        base["reproduction_steps"] = [
            {"actor": s.actor, "action": "redacted", "details": {}}
            for s in finding.reproduction_steps
        ]
        base["disclosure_note"] = "Reproduction details embargoed pending responsible disclosure"
        return base

    base["parameters"] = finding.parameters
    base["invariant_violations"] = [
        {"id": v.invariant_id, "description": v.description}
        for v in finding.invariant_violations
    ]
    base["reproduction_steps"] = [
        {"actor": s.actor, "action": s.action, "details": s.details}
        for s in finding.reproduction_steps
    ]
    return base


def _redact_parameters(parameters: dict) -> dict:
    return {k: "[redacted]" for k in parameters}


def update_disclosure_status(
    findings_path: Path,
    finding_id: str,
    new_status: str,
    *,
    disclosed_at: str | None = None,
) -> dict:
    """Update a finding's disclosure status in a run JSON file."""
    if new_status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {new_status}. Must be one of {sorted(VALID_STATUSES)}")

    with open(findings_path) as f:
        payload = json.load(f)

    updated = False
    for item in payload.get("findings", []):
        if item.get("finding_id") == finding_id:
            item["disclosure_status"] = new_status
            if new_status == "disclosed":
                item["disclosed_at"] = disclosed_at or datetime.now(timezone.utc).isoformat()
            updated = True
            break

    if not updated:
        raise KeyError(f"Finding {finding_id} not found in {findings_path}")

    with open(findings_path, "w") as f:
        json.dump(payload, f, indent=2, default=str)

    return {"finding_id": finding_id, "disclosure_status": new_status}


def build_disclosure_report(findings: list[Finding]) -> dict:
    """Summary report for disclosure workflow review."""
    findings = apply_disclosure_policy(findings)
    by_status: dict[str, int] = {}
    for f in findings:
        by_status[f.disclosure_status] = by_status.get(f.disclosure_status, 0) + 1

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_findings": len(findings),
        "by_status": by_status,
        "embargoed_ids": [f.finding_id for f in findings if f.disclosure_status == "embargoed"],
        "ready_to_disclose": [
            f.finding_id for f in findings if f.disclosure_status == "draft" and f.mitigations
        ],
        "policy": {
            "auto_embargo_severities": ["critical", "high"],
            "redacted_fields": ["parameters", "reproduction_steps"],
        },
    }