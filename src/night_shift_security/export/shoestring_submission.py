"""Shoestring submission export — zero-RPC, fixture-first bounty pack."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from night_shift_security.data.exploit_catalog import get_exploit_catalog
from night_shift_security.data.schemas import ExploitRecord, Finding
from night_shift_security.export.immunefi_submission import (
    build_full_submission_pack,
    resolve_exploit_id,
)


def resolve_catalog_record(finding: Finding, catalog: list[ExploitRecord] | None = None) -> ExploitRecord | None:
    exploit_id = resolve_exploit_id(finding)
    if not exploit_id:
        return None
    catalog = catalog or get_exploit_catalog()
    for record in catalog:
        if record.exploit_id == exploit_id:
            return record
    return None


def score_submission_candidate(finding: Finding) -> tuple:
    """Rank findings for shoestring submission (higher is better)."""
    exploit_id = resolve_exploit_id(finding)
    repro_method = finding.solana_evidence.get("method", "")
    fixture_bonus = 1 if repro_method == "solana_fixture" else 0
    catalog_bonus = 1 if exploit_id else 0
    return (
        finding.evidence_grade,
        fixture_bonus,
        catalog_bonus,
        finding.severity_score,
        finding.economic_impact_usd,
    )


def select_best_submission(
    findings: list[Finding],
    *,
    min_evidence_grade: int = 4,
    prefer_exploit_id: str = "",
) -> Finding | None:
    """Pick the best shoestring submission candidate."""
    eligible = [f for f in findings if f.evidence_grade >= min_evidence_grade]
    if not eligible:
        return None
    if prefer_exploit_id:
        anchored = [f for f in eligible if resolve_exploit_id(f) == prefer_exploit_id]
        if anchored:
            eligible = anchored
    return max(eligible, key=score_submission_candidate)


def _shoestring_readme(
    finding: Finding,
    record: ExploitRecord | None,
    *,
    repro_method: str,
) -> str:
    protocol = record.protocol if record else (finding.target_id or "protocol")
    exploit_id = resolve_exploit_id(finding) or "unknown"
    historical_loss = record.loss_usd if record else finding.economic_impact_usd
    lines = [
        f"# Shoestring Submission — {protocol}",
        "",
        f"**Finding**: `{finding.finding_id}`",
        f"**Catalog anchor**: `{exploit_id}`",
        f"**Evidence grade**: {finding.evidence_grade} ({finding.evidence_grade_label})",
        f"**Reproduction method**: `{repro_method}` (zero RPC cost)",
        "",
        "## What this pack is",
        "",
        "A grant-pending, zero-budget submission draft. Reproduction uses the Solana "
        "**fixture harness** — no mainnet RPC, no paid endpoints. Validator clone replay "
        "is documented as the upgrade path once RPC budget is available.",
        "",
        "## Files",
        "",
        f"- `{finding.finding_id}.md` — Immunefi-style report",
        f"- `{finding.finding_id}_repro.sh` — runnable fixture reproduction (free)",
        f"- `{finding.finding_id}.json` — structured metadata",
        "",
        "## Run reproduction (zero cost)",
        "",
        "```bash",
        f"./{finding.finding_id}_repro.sh",
        "```",
        "",
        "## Historical reference",
        "",
        f"- Documented loss: ${historical_loss:,.0f} USD",
        f"- Simulated impact (engine): ${finding.economic_impact_usd:,.0f} USD",
        "",
        "## Upgrade path (when grants land)",
        "",
        "```bash",
        "export SOLANA_MAINNET_RPC_URL=<grant-funded-rpc>",
        "export SOLANA_USE_VALIDATOR=1",
        f"SOLANA_EXPLOIT_ID={exploit_id} ./solana/run_validator_test.sh",
        "```",
        "",
        "---",
        "*Night Shift Security — shoestring mode. Brutal validation over hype.*",
    ]
    return "\n".join(lines)


def export_shoestring_pack(
    findings: list[Finding],
    run_meta: dict[str, Any],
    output_dir: Path,
    *,
    min_evidence_grade: int = 4,
) -> dict[str, Any]:
    """
    Export a single polished submission pack under bounty/shoestring/.

    Picks the best Level 4+ finding with fixture reproduction when available.
    """
    prefer_exploit = ""
    live_target = run_meta.get("live_target") or {}
    if isinstance(live_target, dict):
        prefer_exploit = str(live_target.get("exploit_id", "") or live_target.get("target_id", ""))

    finding = select_best_submission(
        findings,
        min_evidence_grade=min_evidence_grade,
        prefer_exploit_id=prefer_exploit,
    )
    if finding is None:
        return {"selected": None, "reason": "no_eligible_findings"}

    record = resolve_catalog_record(finding)
    exploit_id = resolve_exploit_id(finding) or finding.finding_id
    repro_method = (
        finding.solana_evidence.get("method")
        or ("fork_reproduced" if finding.fork_reproduced else "simulation")
    )

    pack_dir = output_dir / "bounty" / "shoestring" / exploit_id
    if pack_dir.exists():
        shutil.rmtree(pack_dir)
    pack_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        **run_meta,
        "shoestring_mode": True,
        "reproduction_method": repro_method,
        "catalog_exploit_id": exploit_id,
        "zero_rpc": True,
    }
    if record:
        meta["catalog_protocol"] = record.protocol
        meta["historical_loss_usd"] = record.loss_usd

    paths = build_full_submission_pack(finding, output_dir=pack_dir, run_meta=meta)

    readme_path = pack_dir / "README.md"
    readme_path.write_text(
        _shoestring_readme(finding, record, repro_method=str(repro_method))
    )

    manifest = {
        "schema_version": "1.0",
        "mode": "shoestring",
        "zero_rpc": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_at": run_meta.get("run_at"),
        "selected_finding_id": finding.finding_id,
        "catalog_exploit_id": exploit_id,
        "evidence_grade": finding.evidence_grade,
        "reproduction_method": repro_method,
        "paths": {k: str(v) for k, v in paths.items()},
        "readme": str(readme_path),
    }
    manifest_path = output_dir / "bounty" / "shoestring" / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, default=str))

    return {
        "selected_finding_id": finding.finding_id,
        "catalog_exploit_id": exploit_id,
        "evidence_grade": finding.evidence_grade,
        "reproduction_method": repro_method,
        "pack_dir": str(pack_dir),
        "manifest_path": str(manifest_path),
        "paths": {k: str(v) for k, v in paths.items()},
    }