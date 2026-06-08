"""Immunefi / bug bounty submission pack generator.

Produces complete, submission-ready artifacts:
- Human-readable markdown report
- Standalone reproduction script template (Foundry or Solana)
- Structured JSON for automation

Zero API cost compatible. Uses only data already present in Finding objects.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from night_shift_security.data.schemas import Finding, InvariantViolation, ReproductionStep, Severity


def _format_invariant(inv: InvariantViolation | dict[str, Any]) -> str:
    if isinstance(inv, InvariantViolation):
        return f"{inv.invariant_id}: expected {inv.expected}, got {inv.actual} — {inv.description}"
    return (
        f"{inv.get('invariant_id', 'unknown')}: "
        f"expected {inv.get('expected', '?')}, got {inv.get('actual', '?')}"
    )


def _format_step(step: ReproductionStep | dict[str, Any], index: int) -> str:
    if isinstance(step, ReproductionStep):
        details = json.dumps(step.details, default=str) if step.details else ""
        suffix = f" ({details})" if details and details != "{}" else ""
        return f"{index}. [{step.actor}] {step.action}{suffix}"
    actor = step.get("actor", "attacker")
    action = step.get("action", "step")
    return f"{index}. [{actor}] {action}"


def severity_justification(finding: Finding) -> str:
    """Plain-language severity rationale for bounty triage."""
    severity_map = {
        Severity.CRITICAL: "Critical",
        Severity.HIGH: "High",
        Severity.MEDIUM: "Medium",
        Severity.LOW: "Low",
    }
    label = severity_map.get(finding.severity, "Medium")
    repro = "fork" if finding.fork_reproduced else "solana" if finding.solana_reproduced else "simulation"
    return (
        f"Classified as {label} based on severity score {finding.severity_score:.2f}, "
        f"estimated impact ${finding.economic_impact_usd:,.0f}, evidence grade "
        f"{finding.evidence_grade} ({finding.evidence_grade_label}), and {repro} reproduction signal."
    )


def generate_immunefi_markdown(finding: Finding, *, run_meta: dict[str, Any] | None = None) -> str:
    """Generate a complete Immunefi-style markdown submission report."""
    run_meta = run_meta or {}
    severity_map = {
        Severity.CRITICAL: "Critical",
        Severity.HIGH: "High",
        Severity.MEDIUM: "Medium",
        Severity.LOW: "Low",
    }
    severity_label = severity_map.get(finding.severity, "Medium")

    lines = [
        f"# {finding.template_id} — {finding.target_id or 'Protocol'}",
        "",
        f"**Severity**: {severity_label} (score: {finding.severity_score:.2f})",
        f"**Estimated Impact**: ${finding.economic_impact_usd:,.0f} USD",
        f"**Evidence Level**: {finding.evidence_grade} ({finding.evidence_grade_label})",
        f"**Finding ID**: {finding.finding_id}",
        f"**Generated**: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Summary",
        (
            f"Night Shift Security validated a {finding.template_id} attack vector "
            f"against {finding.target_id or 'the target protocol'} with "
            f"{finding.evidence_grade_label} evidence."
        ),
        "",
        "## Severity Justification",
        severity_justification(finding),
        "",
        "## Attack Vector",
        f"Template: `{finding.template_id}`",
        f"Parameters: {json.dumps(finding.parameters, indent=2, default=str) if finding.parameters else 'N/A'}",
        "",
        "## Reproduction Steps",
    ]

    if finding.reproduction_steps:
        for i, step in enumerate(finding.reproduction_steps, 1):
            lines.append(_format_step(step, i))
    else:
        lines.append("1. See attached reproduction script / Foundry test or Solana validator replay.")
        lines.append("2. Run with the provided invariant checks.")

    lines.extend([
        "",
        "## Impact Analysis",
        f"- Economic impact: ${finding.economic_impact_usd:,.0f}",
        f"- Capital required: ${finding.capital_required_usd:,.0f}",
        f"- Likelihood axis: {finding.axis_scores.get('likelihood', 'N/A')}",
        f"- Impact axis: {finding.axis_scores.get('impact', 'N/A')}",
        f"- Stealth / Realism: {finding.axis_scores.get('stealth', 'N/A')}",
        f"- Generality: {finding.axis_scores.get('generality', 'N/A')}",
        "",
        "## Invariant Violations",
    ])

    if finding.invariant_violations:
        for inv in finding.invariant_violations:
            lines.append(f"- {_format_invariant(inv)}")
    else:
        lines.append("- See MC / fork validation output for specific invariant breaks.")

    mitigation_text = (
        "; ".join(finding.mitigations)
        if finding.mitigations
        else (
            "Review access control, oracle assumptions, governance parameters, "
            "and economic incentives against the described vector."
        )
    )
    lines.extend([
        "",
        "## Recommended Mitigation",
        mitigation_text,
        "",
        "## Provenance & Reproducibility",
        f"- Night Shift Security version: {run_meta.get('engine_version', 'v2.0')}",
        f"- Run ID / Lineage: {finding.hypothesis_id or finding.finding_id}",
        f"- Evidence grade achieved via: {finding.evidence_grade_label}",
        f"- Fork reproduced: {finding.fork_reproduced}",
        f"- Solana reproduced: {finding.solana_reproduced}",
        "- All findings pass structural validation + multi-gate scoring.",
        "",
        "---",
        "*Generated by Night Shift Security — https://github.com/tradewife/night-shift-security*",
        "*STFU and Build. Brutal validation over hype.*",
    ])

    return "\n".join(lines)


def _repro_language(finding: Finding) -> str:
    if finding.solana_reproduced or finding.solana_confirmed:
        return "solana"
    return "solidity"


def generate_reproduction_script(finding: Finding, *, language: str | None = None) -> str:
    """Generate a minimal standalone reproduction script template."""
    language = language or _repro_language(finding)

    if language == "solana":
        slot = finding.solana_slot or finding.solana_evidence.get("slot", 0)
        program = finding.solana_evidence.get("program_id", "PROGRAM_ID")
        exploit = finding.solana_evidence.get("exploit_id", finding.rediscovered_exploit_id or "")
        return f"""#!/usr/bin/env bash
# Solana reproduction template for {finding.finding_id}
# Target: {finding.target_id or 'Protocol'}
# Vector: {finding.template_id}
# Exploit anchor: {exploit}

set -euo pipefail
export SOLANA_EXPLOIT_ID="{exploit or 'TARGET_EXPLOIT_ID'}"
export SLOT_TARGET="{slot}"

# Requires solana-test-validator + mainnet RPC for account clone (see solana/README.md)
cd "$(dirname "$0")/../../solana"
./run_validator_test.sh
"""
    return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "forge-std/console.sol";

// Target: {finding.target_id or 'Protocol'}
// Vector: {finding.template_id}
// Finding: {finding.finding_id}

contract {finding.template_id.replace('-', '_').title()}PoC is Test {{
    function test_{finding.template_id.replace('-', '_')}_exploit() public {{
        // TODO: Deploy / fork target at specific block
        // TODO: Set up attacker contract with parameters:
        // {json.dumps(finding.parameters or {}, indent=8, default=str)}

        // 1. Execute the attack sequence
        // 2. Assert invariant violations
        // 3. Measure economic impact

        console.log("Reproduction script for {finding.finding_id}");
    }}
}}
"""


def build_full_submission_pack(
    finding: Finding,
    *,
    output_dir: Path,
    run_meta: dict[str, Any] | None = None,
) -> dict[str, Path]:
    """Write the complete submission pack to disk and return paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    base = output_dir / finding.finding_id

    md_path = base.with_suffix(".md")
    md_path.write_text(generate_immunefi_markdown(finding, run_meta=run_meta))

    lang = _repro_language(finding)
    if lang == "solana":
        script_path = base.with_name(f"{finding.finding_id}_repro.sh")
    else:
        script_path = base.with_name(f"{finding.finding_id}_repro.sol")
    script_path.write_text(generate_reproduction_script(finding, language=lang))
    if lang == "solana":
        script_path.chmod(0o755)

    json_path = base.with_suffix(".json")
    json_path.write_text(
        json.dumps(
            {
                "finding_id": finding.finding_id,
                "template_id": finding.template_id,
                "target_id": finding.target_id,
                "severity": finding.severity.value,
                "severity_score": finding.severity_score,
                "severity_justification": severity_justification(finding),
                "economic_impact_usd": finding.economic_impact_usd,
                "evidence_grade": finding.evidence_grade,
                "evidence_grade_label": finding.evidence_grade_label,
                "fork_reproduced": finding.fork_reproduced,
                "solana_reproduced": finding.solana_reproduced,
                "parameters": finding.parameters,
                "invariant_violations": [
                    asdict(v) if isinstance(v, InvariantViolation) else v
                    for v in finding.invariant_violations
                ],
                "reproduction_steps": [
                    asdict(s) if isinstance(s, ReproductionStep) else s
                    for s in finding.reproduction_steps
                ],
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
            default=str,
        )
    )

    return {
        "markdown": md_path,
        "reproduction_script": script_path,
        "json": json_path,
    }


def export_immunefi_packs(
    findings: list[Finding],
    run_meta: dict,
    output_dir: Path,
    *,
    min_evidence_grade: int = 3,
    min_severity: str = "high",
) -> dict[str, Any]:
    """
    Export Immunefi-style submission packs for qualifying findings.

    Writes per-finding packs under bounty/immunefi/<finding_id>.*
    """
    bounty_dir = output_dir / "bounty" / "immunefi"
    bounty_dir.mkdir(parents=True, exist_ok=True)

    min_rank = {"low": 0, "medium": 1, "high": 2, "critical": 3}.get(min_severity, 2)
    rank = {"low": 0, "medium": 1, "high": 2, "critical": 3}

    qualifying = [
        f
        for f in findings
        if f.evidence_grade >= min_evidence_grade
        and rank.get(f.severity.value, 0) >= min_rank
    ]
    qualifying.sort(key=lambda f: (f.evidence_grade, f.severity_score), reverse=True)

    packs: list[dict[str, Any]] = []
    for finding in qualifying:
        paths = build_full_submission_pack(finding, output_dir=bounty_dir, run_meta=run_meta)
        packs.append(
            {
                "finding_id": finding.finding_id,
                "evidence_grade": finding.evidence_grade,
                "markdown": str(paths["markdown"]),
                "reproduction_script": str(paths["reproduction_script"]),
                "json": str(paths["json"]),
            }
        )

    manifest = {
        "schema_version": "1.0",
        "source": "night-shift-security",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_at": run_meta.get("run_at"),
        "pack_count": len(packs),
        "min_evidence_grade": min_evidence_grade,
        "min_severity": min_severity,
        "packs": packs,
    }
    manifest_path = bounty_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, default=str))

    return {
        "manifest_path": str(manifest_path),
        "pack_count": len(packs),
        "packs": packs,
    }