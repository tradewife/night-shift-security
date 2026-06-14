"""Immunefi report sections + IVSS v2.3 category mapping."""

from __future__ import annotations

from typing import Any

from night_shift_security.data.schemas import Finding
from night_shift_security.export.finding_resolve import resolve_catalog_record, resolve_exploit_id
from night_shift_security.export.immunefi_submission import severity_justification

# IVSS v2.3 attack vector categories (simplified mapping from NSS template_id).
_TEMPLATE_IVSS: dict[str, dict[str, str]] = {
    "access_control_escalation": {
        "attack_vector": "Network",
        "attack_complexity": "Low",
        "privileges_required": "None",
        "user_interaction": "None",
        "scope": "Changed",
        "confidentiality": "None",
        "integrity": "High",
        "availability": "None",
    },
    "reentrancy": {
        "attack_vector": "Network",
        "attack_complexity": "Low",
        "privileges_required": "None",
        "user_interaction": "None",
        "scope": "Unchanged",
        "confidentiality": "None",
        "integrity": "High",
        "availability": "None",
    },
    "flash_loan_oracle": {
        "attack_vector": "Network",
        "attack_complexity": "Medium",
        "privileges_required": "None",
        "user_interaction": "None",
        "scope": "Unchanged",
        "confidentiality": "None",
        "integrity": "High",
        "availability": "None",
    },
    "governance_capture": {
        "attack_vector": "Network",
        "attack_complexity": "High",
        "privileges_required": "Low",
        "user_interaction": "None",
        "scope": "Changed",
        "confidentiality": "None",
        "integrity": "High",
        "availability": "Low",
    },
    "treasury_drain": {
        "attack_vector": "Network",
        "attack_complexity": "Medium",
        "privileges_required": "None",
        "user_interaction": "None",
        "scope": "Unchanged",
        "confidentiality": "None",
        "integrity": "High",
        "availability": "None",
    },
    "composability_risk": {
        "attack_vector": "Network",
        "attack_complexity": "Medium",
        "privileges_required": "None",
        "user_interaction": "None",
        "scope": "Changed",
        "confidentiality": "None",
        "integrity": "High",
        "availability": "Low",
    },
}

_DEFAULT_IVSS = {
    "attack_vector": "Network",
    "attack_complexity": "Medium",
    "privileges_required": "None",
    "user_interaction": "None",
    "scope": "Unchanged",
    "confidentiality": "None",
    "integrity": "High",
    "availability": "None",
}


def ivss_vector_for_template(template_id: str) -> dict[str, str]:
    return dict(_TEMPLATE_IVSS.get(template_id, _DEFAULT_IVSS))


def format_ivss_section(finding: Finding) -> list[str]:
    ivss = ivss_vector_for_template(finding.template_id)
    lines = [
        "## IVSS Risk Breakdown",
        "",
        "| Metric | Value |",
        "|--------|-------|",
    ]
    for key, value in ivss.items():
        label = key.replace("_", " ").title()
        lines.append(f"| {label} | {value} |")
    lines.append("")
    return lines


def format_immunefi_submittable_sections(
    finding: Finding,
    *,
    run_meta: dict[str, Any] | None = None,
    scope_impact_id: str = "",
) -> list[str]:
    """Immunefi template: Brief, Details, Impact, Risk, Recommendation, References."""
    run_meta = run_meta or {}
    live_target = run_meta.get("live_target") if isinstance(run_meta.get("live_target"), dict) else {}
    record = resolve_catalog_record(finding)
    protocol = str(
        live_target.get("protocol_name")
        or finding.target_id
        or (record.protocol if record else "Protocol")
    )
    exploit_id = resolve_exploit_id(finding)

    lines = [
        "## Brief",
        "",
        f"A {finding.template_id} vulnerability in **{protocol}** was validated with "
        f"evidence grade {finding.evidence_grade} ({finding.evidence_grade_label}). "
        f"Estimated impact: ${finding.economic_impact_usd:,.0f} USD.",
        "",
        "## Details",
        "",
        f"- Template: `{finding.template_id}`",
        f"- Finding ID: `{finding.finding_id}`",
        f"- Reproduction tier: `{finding.reproduction_tier or 'fork_reproduced'}`",
    ]
    if exploit_id:
        lines.append(f"- Exploit anchor: `{exploit_id}`")
    if scope_impact_id:
        lines.append(f"- In-scope impact ID: `{scope_impact_id}`")
    lines.extend([
        "",
        "## Impact",
        "",
        f"- Economic impact: ${finding.economic_impact_usd:,.0f}",
        f"- Capital required: ${finding.capital_required_usd:,.0f}",
        f"- Severity score: {finding.severity_score:.2f}",
        "",
        "## Risk",
        "",
        severity_justification(finding),
        "",
    ])
    lines.extend(format_ivss_section(finding))
    lines.extend([
        "## Recommendation",
        "",
        "; ".join(finding.mitigations)
        if finding.mitigations
        else "Review access control, oracle assumptions, and economic invariants.",
        "",
        "## References",
        "",
        "- Night Shift Security validation pipeline",
        f"- Finding lineage: `{finding.hypothesis_id or finding.finding_id}`",
    ])
    if record:
        lines.append(f"- Historical catalogue anchor: `{record.exploit_id}` ({record.name})")
    if live_target:
        lines.append(f"- Live target program: `{live_target.get('immunefi_program', live_target.get('target_id', ''))}`")
    lines.append("")
    return lines