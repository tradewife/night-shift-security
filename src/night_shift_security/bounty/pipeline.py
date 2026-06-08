"""Bug bounty pipeline — format findings for responsible disclosure workflows."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from night_shift_security.data.schemas import Finding, Severity
from night_shift_security.export.disclosure import apply_disclosure_policy, redact_finding_for_public
from night_shift_security.export.immunefi_submission import export_immunefi_packs
from night_shift_security.export.shoestring_submission import export_shoestring_pack

_SEVERITY_BOUNTY_TIER = {
    Severity.CRITICAL: "critical",
    Severity.HIGH: "high",
    Severity.MEDIUM: "medium",
    Severity.LOW: "low",
}


def build_bounty_submission(finding: Finding) -> dict:
    """Format a single finding for bug-bounty / Immunefi-style submission."""
    public = redact_finding_for_public(finding)
    return {
        "submission_id": finding.finding_id,
        "title": f"{finding.template_id} on {finding.target_id or 'protocol'}",
        "severity": _SEVERITY_BOUNTY_TIER.get(finding.severity, "medium"),
        "severity_score": round(finding.severity_score, 4),
        "estimated_impact_usd": round(finding.economic_impact_usd, 2),
        "attack_surface": finding.template_id,
        "description": _bounty_description(finding),
        "reproduction": {
            "steps": public.get("reproduction_steps", []),
            "parameters": public.get("parameters", {}),
            "capital_required_usd": round(finding.capital_required_usd, 2),
        },
        "mitigations": finding.mitigations,
        "disclosure_status": finding.disclosure_status,
        "confidence": round(finding.confidence, 4),
        "rediscovered_exploit_id": finding.rediscovered_exploit_id or None,
        "invariant_violations": public.get("invariant_violations", []),
        "evidence_grade": finding.evidence_grade,
        "evidence_grade_label": finding.evidence_grade_label,
        "fork_reproduced": finding.fork_reproduced,
        "solana_reproduced": finding.solana_reproduced,
    }


def _bounty_description(finding: Finding) -> str:
    violations = ", ".join(v.invariant_id for v in finding.invariant_violations[:3])
    return (
        f"Night Shift Security discovered a {finding.severity.value} severity "
        f"{finding.template_id} vector with estimated impact "
        f"${finding.economic_impact_usd:,.0f}. "
        f"Invariants violated: {violations or 'see report'}."
    )


def export_bounty_pack(
    findings: list[Finding],
    run_meta: dict,
    output_dir: Path,
    *,
    min_severity: str = "high",
) -> Path:
    """
    Export bug-bounty submission pack:

    - bounty/submissions.json — all qualifying findings
    - bounty/submissions.jsonl — one per line
    """
    bounty_dir = output_dir / "bounty"
    bounty_dir.mkdir(parents=True, exist_ok=True)

    findings = apply_disclosure_policy(findings)
    min_rank = {"low": 0, "medium": 1, "high": 2, "critical": 3}.get(min_severity, 2)
    rank = {"low": 0, "medium": 1, "high": 2, "critical": 3}

    qualifying = [
        f for f in findings
        if rank.get(f.severity.value, 0) >= min_rank
        and f.disclosure_status in ("draft", "disclosed", "embargoed")
    ]
    qualifying.sort(key=lambda f: (f.severity_score, f.economic_impact_usd), reverse=True)

    pack = {
        "schema_version": "1.0",
        "source": "night-shift-security",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_at": run_meta.get("run_at"),
        "submission_count": len(qualifying),
        "min_severity": min_severity,
        "submissions": [build_bounty_submission(f) for f in qualifying],
    }

    json_path = bounty_dir / "submissions.json"
    jsonl_path = bounty_dir / "submissions.jsonl"

    with open(json_path, "w") as f:
        json.dump(pack, f, indent=2, default=str)

    with open(jsonl_path, "w") as f:
        for item in pack["submissions"]:
            f.write(json.dumps(item, default=str) + "\n")

    return json_path


def export_bounty_artifacts(
    findings: list[Finding],
    run_meta: dict,
    output_dir: Path,
    bounty_cfg: dict[str, Any],
) -> dict[str, Any]:
    """Export standard bounty pack and optional Immunefi submission packs."""
    min_severity = bounty_cfg.get("min_severity", "high")
    submissions_path = export_bounty_pack(
        findings,
        run_meta,
        output_dir,
        min_severity=min_severity,
    )
    result: dict[str, Any] = {"submissions_path": str(submissions_path)}

    if bounty_cfg.get("immunefi_packs", True):
        immunefi = export_immunefi_packs(
            findings,
            run_meta,
            output_dir,
            min_evidence_grade=int(bounty_cfg.get("min_evidence_grade", 3)),
            min_severity=min_severity,
        )
        result["immunefi"] = immunefi

    if bounty_cfg.get("shoestring_pack", False):
        shoestring_meta = {**run_meta, "shoestring_mode": True, "zero_rpc": True}
        shoestring = export_shoestring_pack(
            findings,
            shoestring_meta,
            output_dir,
            min_evidence_grade=int(bounty_cfg.get("min_evidence_grade", 4)),
        )
        result["shoestring"] = shoestring

    return result