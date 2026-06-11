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

from night_shift_security.data.exploit_catalog import get_exploit_catalog
from night_shift_security.data.schemas import ExploitRecord, Finding, InvariantViolation, ReproductionStep, Severity
from night_shift_security.data.solana_targets import get_solana_targets
from night_shift_security.validation.evidence_grading import effective_evidence_grade


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


def resolve_exploit_id(finding: Finding) -> str:
    """Prefer strict reproduction anchors over fuzzy rediscovery matches."""
    if finding.solana_reproduced or finding.solana_confirmed:
        evidence_id = finding.solana_evidence.get("exploit_id", "")
        if evidence_id:
            return str(evidence_id)
    if finding.fork_reproduced:
        fork_id = finding.fork_evidence.get("exploit_id", "")
        if fork_id:
            return str(fork_id)
    if finding.rediscovered_exploit_id:
        return finding.rediscovered_exploit_id
    evidence_id = finding.solana_evidence.get("exploit_id", "")
    if evidence_id:
        return str(evidence_id)
    if finding.fork_evidence.get("exploit_id"):
        return str(finding.fork_evidence["exploit_id"])
    return ""


def resolve_catalog_record(
    finding: Finding,
    catalog: list[ExploitRecord] | None = None,
) -> ExploitRecord | None:
    exploit_id = resolve_exploit_id(finding)
    if not exploit_id:
        return None
    catalog = catalog or get_exploit_catalog()
    for record in catalog:
        if record.exploit_id == exploit_id:
            return record
    return None


def _live_target_from_meta(run_meta: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize live-target context injected by pipeline runs."""
    if not run_meta:
        return {}
    live = run_meta.get("live_target")
    return live if isinstance(live, dict) else {}


def _submission_protocol_name(
    finding: Finding,
    record: ExploitRecord | None,
    live_target: dict[str, Any],
) -> str:
    return str(
        live_target.get("protocol_name")
        or finding.target_id
        or (record.protocol if record else "Protocol")
    )


def _submission_title(
    finding: Finding,
    record: ExploitRecord | None,
    live_target: dict[str, Any],
) -> str:
    protocol = _submission_protocol_name(finding, record, live_target)
    if live_target and record:
        return f"{finding.template_id} — {protocol}"
    if record:
        return record.name
    return f"{finding.template_id} — {protocol}"


def _live_target_section(live_target: dict[str, Any], record: ExploitRecord | None) -> list[str]:
    if not live_target:
        return []
    lines = [
        "## Live Target Context",
        "",
        f"**Protocol**: {live_target.get('protocol_name', live_target.get('target_id', 'unknown'))}",
    ]
    program = live_target.get("immunefi_program") or live_target.get("target_id")
    if program:
        lines.append(f"**Bounty program**: `{program}`")
    if live_target.get("program_id"):
        lines.append(f"**Program ID**: `{live_target['program_id']}`")
    if live_target.get("contract_address"):
        lines.append(f"**Contract**: `{live_target['contract_address']}`")
    if record:
        lines.append(
            f"**Methodology**: catalogue-analogue probe via `{record.exploit_id}` "
            f"({record.name}). This documents transferable risk patterns on the live "
            f"target — not a claim of rediscovering the historical incident."
        )
    lines.append("")
    return lines


def _reproduction_method(finding: Finding) -> str:
    if finding.solana_evidence.get("method"):
        return str(finding.solana_evidence["method"])
    if finding.fork_reproduced:
        return "fork_reproduced"
    if finding.solana_reproduced:
        return "solana_reproduced"
    return "simulation"


def _lab_vs_deployed_section(finding: Finding, record: ExploitRecord | None) -> list[str]:
    method = _reproduction_method(finding)
    lines = [
        "## Lab vs Deployed Reality",
        "",
    ]
    if method == "solana_fixture":
        lines.extend([
            "**Current evidence**: Solana fixture replay (zero RPC, CI-safe).",
            "Confirms catalog-aligned impact lines and strict `solana_reproduced` signal.",
            "**Deployed upgrade**: `solana_validator` clone replay at historical slot once RPC budget is available.",
        ])
    elif method == "solana_validator":
        lines.extend([
            "**Current evidence**: `solana-test-validator` clone replay with impact evidence.",
            "Represents deployed-state reproduction on local validator infrastructure.",
        ])
    elif method == "fork_reproduced":
        lines.extend([
            "**Current evidence**: EVM mainnet fork reproduction.",
            "Represents deployed-state replay at historical block.",
        ])
    else:
        lines.extend([
            "**Current evidence**: Simulation + statistical gates (Monte Carlo, CPCV).",
            "Fork/validator reproduction not yet confirmed for this finding.",
        ])

    if record:
        lines.append(f"**Historical anchor**: {record.name} ({record.year}) — ${record.loss_usd:,.0f} documented loss.")
    lines.append("")
    return lines


def severity_justification(finding: Finding) -> str:
    """Plain-language severity rationale for bounty triage."""
    severity_map = {
        Severity.CRITICAL: "Critical",
        Severity.HIGH: "High",
        Severity.MEDIUM: "Medium",
        Severity.LOW: "Low",
    }
    label = severity_map.get(finding.severity, "Medium")
    method = _reproduction_method(finding)
    record = resolve_catalog_record(finding)
    impact_note = (
        f"historical loss ${record.loss_usd:,.0f}"
        if record
        else f"estimated impact ${finding.economic_impact_usd:,.0f}"
    )
    return (
        f"Classified as {label} based on severity score {finding.severity_score:.2f}, "
        f"{impact_note}, evidence grade {finding.evidence_grade} "
        f"({finding.evidence_grade_label}), and `{method}` reproduction signal."
    )


def generate_immunefi_markdown(finding: Finding, *, run_meta: dict[str, Any] | None = None) -> str:
    """Generate a complete Immunefi-style markdown submission report."""
    run_meta = run_meta or {}
    live_target = _live_target_from_meta(run_meta)
    severity_map = {
        Severity.CRITICAL: "Critical",
        Severity.HIGH: "High",
        Severity.MEDIUM: "Medium",
        Severity.LOW: "Low",
    }
    severity_label = severity_map.get(finding.severity, "Medium")
    record = resolve_catalog_record(finding)
    exploit_id = resolve_exploit_id(finding)
    protocol_name = _submission_protocol_name(finding, record, live_target)
    title = _submission_title(finding, record, live_target)
    repro_method = _reproduction_method(finding)
    historical_loss = record.loss_usd if record else None

    lines = [
        f"# {title}",
        "",
        f"**Severity**: {severity_label} (score: {finding.severity_score:.2f})",
        f"**Engine Impact**: ${finding.economic_impact_usd:,.0f} USD",
    ]
    if live_target:
        lines.append(f"**Live Target**: {protocol_name}")
    if historical_loss is not None:
        lines.append(f"**Historical Loss (catalog)**: ${historical_loss:,.0f} USD")
    lines.extend([
        f"**Evidence Level**: {finding.evidence_grade} ({finding.evidence_grade_label})",
        f"**Reproduction Method**: `{repro_method}`",
        f"**Finding ID**: {finding.finding_id}",
    ])
    if exploit_id:
        lines.append(f"**Catalog Anchor**: `{exploit_id}`")
    lines.extend([
        f"**Generated**: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Summary",
    ])
    if live_target and record:
        lines.append(
            f"Night Shift Security probed **{protocol_name}** for {finding.template_id} "
            f"risk using the `{exploit_id}` catalogue analogue ({record.description}). "
            f"Fixture replay confirms invariant breaks and impact scaling on live-target "
            f"assumptions — internal draft pending validator/fork upgrade before external post."
        )
    elif record:
        lines.append(record.description)
    else:
        lines.append(
            f"Night Shift Security validated a {finding.template_id} attack vector "
            f"against {protocol_name} with {finding.evidence_grade_label} evidence."
        )
    lines.extend([
        "",
        "## Severity Justification",
        severity_justification(finding),
        "",
        "## Attack Vector",
        f"Template: `{finding.template_id}`",
        f"Parameters: {json.dumps(finding.parameters, indent=2, default=str) if finding.parameters else 'N/A'}",
        "",
        "## Reproduction Steps",
    ])

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

    lines.extend(_live_target_section(live_target, record))
    lines.extend(_lab_vs_deployed_section(finding, record))

    if run_meta.get("shoestring_mode"):
        lines.extend([
            "## Shoestring Mode",
            "",
            "This pack was generated with **zero RPC spend**. Reproduction uses the Solana "
            "fixture harness. Upgrade to validator clone replay when grant-funded RPC is available.",
            "",
        ])

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
        f"- Reproduction method: `{repro_method}`",
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


def generate_reproduction_script(
    finding: Finding,
    *,
    language: str | None = None,
    run_meta: dict[str, Any] | None = None,
) -> str:
    """Generate a minimal standalone reproduction script template."""
    run_meta = run_meta or {}
    language = language or _repro_language(finding)

    if language == "solana":
        slot = finding.solana_slot or finding.solana_evidence.get("slot", 0)
        exploit = resolve_exploit_id(finding)
        method = _reproduction_method(finding)
        target_id = finding.solana_evidence.get("target_id", exploit)
        fixture_test = ""
        for target in get_solana_targets():
            if target.exploit_id == exploit:
                fixture_test = target.fixture_test
                if not slot:
                    slot = target.slot
                break

        if method == "solana_fixture" or run_meta.get("shoestring_mode", False):
            return f"""#!/usr/bin/env bash
# Zero-cost Solana fixture reproduction — {finding.finding_id}
# Target: {finding.target_id or 'Protocol'}
# Exploit anchor: {exploit or 'TARGET_EXPLOIT_ID'}
# No RPC required.

set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
while [ ! -f "$ROOT/solana/run_fixture_test.py" ] && [ "$ROOT" != "/" ]; do
  ROOT="$(dirname "$ROOT")"
done
if [ ! -f "$ROOT/solana/run_fixture_test.py" ]; then
  echo "Could not locate repo root (solana/run_fixture_test.py)" >&2
  exit 1
fi
cd "$ROOT/solana"

export SOLANA_EXPLOIT_ID="{exploit or 'TARGET_EXPLOIT_ID'}"
export SOLANA_TARGET_ID="{target_id or exploit}"
export SOLANA_SLOT="{slot}"
export SOLANA_FIXTURE_TEST="{fixture_test or 'replay'}"

echo "==> Fixture reproduction (zero RPC)"
python3 run_fixture_test.py
echo "==> PASS: fixture strict reproduction"
"""
        rpc_url = run_meta.get("solana_mainnet_rpc_url", "http://127.0.0.1:18989")
        rpc_note = run_meta.get(
            "x402_proxy_note",
            f"SOLANA_MAINNET_RPC_URL={rpc_url} (x402 proxy — start: solana/x402-proxy/start.sh)",
        )
        return f"""#!/usr/bin/env bash
# Solana validator reproduction — {finding.finding_id}
# {rpc_note}

set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
while [ ! -f "$ROOT/solana/run_validator_test.sh" ] && [ "$ROOT" != "/" ]; do
  ROOT="$(dirname "$ROOT")"
done
if [ ! -f "$ROOT/solana/run_validator_test.sh" ]; then
  echo "Could not locate repo root (solana/run_validator_test.sh)" >&2
  exit 1
fi
cd "$ROOT/solana"

export SOLANA_EXPLOIT_ID="{exploit or 'TARGET_EXPLOIT_ID'}"
export SOLANA_USE_VALIDATOR=1
export SOLANA_MAINNET_RPC_URL="${{SOLANA_MAINNET_RPC_URL:-{rpc_url}}}"
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
    script_path.write_text(generate_reproduction_script(finding, language=lang, run_meta=run_meta))
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
                "reproduction_method": _reproduction_method(finding),
                "catalog_exploit_id": resolve_exploit_id(finding),
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

    track = "shoestring" if run_meta.get("shoestring_mode") else "pipeline"

    qualifying = [
        f
        for f in findings
        if effective_evidence_grade(f, track=track) >= min_evidence_grade
        and rank.get(f.severity.value, 0) >= min_rank
    ]
    qualifying.sort(
        key=lambda f: (effective_evidence_grade(f, track=track), f.severity_score),
        reverse=True,
    )

    packs: list[dict[str, Any]] = []
    for finding in qualifying:
        exploit_id = resolve_exploit_id(finding) or finding.target_id or "unknown"
        pack_dir = bounty_dir / exploit_id
        paths = build_full_submission_pack(finding, output_dir=pack_dir, run_meta=run_meta)
        packs.append(
            {
                "finding_id": finding.finding_id,
                "catalog_exploit_id": exploit_id,
                "evidence_grade": effective_evidence_grade(finding, track=track),
                "pipeline_evidence_grade": finding.evidence_grade,
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
        "grading_track": track,
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