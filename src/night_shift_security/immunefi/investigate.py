"""Deep investigation queue driven by Immunefi scan rankings."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from night_shift_security.config.loader import load_config
from night_shift_security.core.pipeline import run_security_pipeline
from night_shift_security.data.immunefi_registry import (
    IMMUNEFI_PROGRAMS,
    ImmunefiProgram,
    program_to_live_target,
)


def _program_by_slug(slug: str) -> ImmunefiProgram | None:
    for program in IMMUNEFI_PROGRAMS:
        if program.slug == slug:
            return program
    return None


def pick_investigation_targets(
    scan_report: dict[str, Any],
    *,
    top_n: int = 2,
    min_evidence_grade: int = 2,
    ecosystem: str | None = "solana",
    require_engine_ready: bool = False,
) -> list[dict[str, Any]]:
    """
    Rank scan results and return programs worth a full investigation run.

    Sort key matches scan.py: submission_ready, best_evidence_grade, solana_reproduced, etc.
    """
    programs = list(scan_report.get("programs") or [])
    if ecosystem:
        programs = [p for p in programs if str(p.get("ecosystem", "")).lower() == ecosystem.lower()]

    filtered: list[dict[str, Any]] = []
    for row in programs:
        grade = int(row.get("best_evidence_grade") or 0)
        if grade < min_evidence_grade:
            continue
        if require_engine_ready and not row.get("engine_ready"):
            continue
        filtered.append(row)

    filtered.sort(
        key=lambda r: (
            r.get("submission_ready", False),
            int(r.get("best_evidence_grade") or 0),
            int(r.get("solana_reproduced") or 0),
            int(r.get("candidates_passed") or 0),
            int(r.get("max_bounty_usd") or 0),
        ),
        reverse=True,
    )
    return filtered[: max(top_n, 0)]


_DEFAULT_BASE = (
    Path(__file__).resolve().parents[1] / "config" / "kamino_shoestring.json"
)


def build_investigation_config(
    program: ImmunefiProgram,
    *,
    base_config_path: Path | None = None,
    campaign_prefix: str = "immunefi",
) -> dict[str, Any]:
    """Build a shoestring-style full pipeline config for one Immunefi program."""
    base = load_config(base_config_path or _DEFAULT_BASE)
    cfg = deepcopy(base)
    target = program_to_live_target(program)
    today = datetime.now(timezone.utc).strftime("%Y-%m")

    cfg["campaign"] = {
        "id": f"{campaign_prefix}-{program.slug}-{today}",
        "name": f"Immunefi deep dive: {program.name}",
    }
    cfg["templates"] = list(program.templates)
    cfg["target"] = {
        "enabled": True,
        "target_id": target.target_id,
        "protocol_name": target.protocol_name,
        "chain": target.chain,
        "templates": list(target.templates),
        "rpc_env_var": target.rpc_env_var,
        "exploit_id": target.exploit_id,
        "immunefi_program": target.immunefi_program,
    }
    cfg.setdefault("llm_expansion", {})
    cfg["llm_expansion"].setdefault("provider", "external")
    cfg["llm_expansion"].setdefault("fallback", "parametric")
    cfg["llm_expansion"].setdefault("max_seeds", 5)
    cfg["llm_expansion"].setdefault("variants_per_seed", 2)
    return cfg


def write_investigation_config(
    program: ImmunefiProgram,
    output_dir: Path,
    *,
    base_config_path: Path | None = None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    cfg = build_investigation_config(program, base_config_path=base_config_path)
    path = output_dir / f"{program.slug}-investigate.json"
    path.write_text(json.dumps(cfg, indent=2))
    return path


def run_investigation_queue(
    scan_report: dict[str, Any],
    *,
    top_n: int = 2,
    min_evidence_grade: int = 2,
    ecosystem: str | None = "solana",
    base_config_path: Path | None = None,
    proposals_path: Path | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    """Run full pipeline for top-ranked scan targets."""
    targets = pick_investigation_targets(
        scan_report,
        top_n=top_n,
        min_evidence_grade=min_evidence_grade,
        ecosystem=ecosystem,
    )
    config_dir = output_dir or Path("data/security_results/investigations")
    config_dir.mkdir(parents=True, exist_ok=True)

    runs: list[dict[str, Any]] = []
    for row in targets:
        slug = str(row.get("slug") or "")
        program = _program_by_slug(slug)
        if program is None:
            runs.append({"slug": slug, "skipped": True, "reason": "unknown_program"})
            continue

        config_path = write_investigation_config(
            program,
            config_dir,
            base_config_path=base_config_path,
        )
        result = run_security_pipeline(
            config_path=config_path,
            proposals_path=proposals_path,
        )
        runs.append(
            {
                "slug": slug,
                "name": program.name,
                "scan_grade": row.get("best_evidence_grade"),
                "config_path": str(config_path),
                "findings": result.get("findings", 0),
                "output_dir": result.get("output_dir"),
            }
        )

    return {
        "investigated_at": datetime.now(timezone.utc).isoformat(),
        "top_n": top_n,
        "min_evidence_grade": min_evidence_grade,
        "ecosystem": ecosystem,
        "targets_selected": [t.get("slug") for t in targets],
        "runs": runs,
    }


def load_scan_report(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Scan report not found: {path}")
    return json.loads(path.read_text())