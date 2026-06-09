"""Scan Immunefi programs with the Night Shift engine (shoestring / zero-RPC)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from night_shift_security.config.loader import gates_from_config, load_config
from night_shift_security.core.evaluation import rank_candidates
from night_shift_security.core.results import findings_from_candidates
from night_shift_security.core.target_harness import evaluate_target_vectors, generate_target_vectors
from night_shift_security.data.exploit_catalog import get_exploit_catalog
from night_shift_security.data.immunefi_registry import (
    ImmunefiProgram,
    list_programs,
    program_summary,
    program_to_live_target,
)
from night_shift_security.data.schemas import AttackCandidateResult
from night_shift_security.data.target_config import resolve_target_exploit
from night_shift_security.validation.solana_validation import run_solana_validation_phase
from night_shift_security.validation.validation_layer import refresh_validation_batch

# Register attack templates (same as pipeline)
import night_shift_security.domain.attack_templates.governance_capture  # noqa: F401
import night_shift_security.domain.attack_templates.treasury_drain  # noqa: F401
import night_shift_security.domain.attack_templates.flash_loan_oracle  # noqa: F401
import night_shift_security.domain.attack_templates.reentrancy  # noqa: F401
import night_shift_security.domain.attack_templates.composability_risk  # noqa: F401
import night_shift_security.domain.attack_templates.upgradeability_risk  # noqa: F401
import night_shift_security.domain.attack_templates.access_control_escalation  # noqa: F401


from night_shift_security.validation.evidence_grading import shoestring_evidence_grade_candidate


def _scan_evidence_grade(candidate: AttackCandidateResult) -> int:
    """Shoestring scan grading — uses shared shoestring track (see evidence_grading.py)."""
    return shoestring_evidence_grade_candidate(candidate)


def _scan_config(base: dict[str, Any]) -> dict[str, Any]:
    """Lightweight scan overrides — fast, zero-RPC."""
    cfg = json.loads(json.dumps(base))
    cfg.setdefault("hypothesis_generation", {})
    cfg["hypothesis_generation"]["samples_per_template"] = 4
    cfg["hypothesis_generation"]["grid_enabled"] = True
    cfg.setdefault("darwinian", {})["enabled"] = False
    cfg.setdefault("monte_carlo", {})["enabled"] = False
    cfg.setdefault("cpcv", {})["enabled"] = False
    cfg.setdefault("foundry", {})["enabled"] = False
    cfg.setdefault("fork_validation", {})["enabled"] = False
    cfg.setdefault("solana_validation", {})["enabled"] = True
    cfg.setdefault("llm_expansion", {})["enabled"] = False
    cfg.setdefault("monitoring", {})["enabled"] = False
    cfg.setdefault("bounty", {})["enabled"] = False
    cfg.setdefault("findings_store", {})["enabled"] = False
    return cfg


def scan_program(
    program: ImmunefiProgram,
    config: dict[str, Any],
    catalog: list,
    gates,
) -> dict[str, Any]:
    """Run a lightweight engine probe against one Immunefi program."""
    target = program_to_live_target(program)
    vectors = generate_target_vectors(target, config)
    candidates = evaluate_target_vectors(target, vectors, gates, catalog)

    analogue = resolve_target_exploit(target, catalog)
    solana_results: dict = {}
    if program.ecosystem == "solana" and config.get("solana_validation", {}).get("enabled", True):
        passing = [c for c in candidates if not c.rejected]
        if analogue:
            for cand in passing:
                cand.catalog_exploit_id = analogue.exploit_id
        solana_results = run_solana_validation_phase(
            candidates,
            catalog,
            config.get("solana_validation", {"enabled": True, "top_n": 3}),
        )

    validation_cfg = config.get("validation_layer", {})
    refresh_validation_batch(
        candidates,
        {
            **validation_cfg,
            "level_1_mc_min": 0.70,
            "max_pbo": config.get("cpcv", {}).get("max_pbo", 0.30),
        },
        apply_scoring=False,
    )

    ranked = rank_candidates(candidates)
    passed = [c for c in ranked if not c.rejected]
    top = passed[0] if passed else None
    findings = findings_from_candidates(passed[:5], {})

    scan_grades = [_scan_evidence_grade(c) for c in passed]
    best_grade = max(scan_grades, default=0)
    top_scan_grade = _scan_evidence_grade(top) if top else 0
    solana_repro = sum(1 for c in candidates if c.solana_reproduced)

    return {
        **program_summary(program),
        "vectors_generated": len(vectors),
        "candidates_evaluated": len(candidates),
        "candidates_passed": len(passed),
        "solana_reproduced": solana_repro,
        "best_evidence_grade": best_grade,
        "top_finding": {
            "severity_score": top.severity_score if top else 0.0,
            "template_id": top.vector.template_id if top else "",
            "impact_usd": top.mean_economic_impact_usd if top else 0.0,
            "evidence_grade": top_scan_grade,
            "solana_reproduced": top.solana_reproduced if top else False,
        },
        "catalog_analogue_name": analogue.name if analogue else "",
        "solana_validation_runs": len(solana_results),
        "engine_ready": len(passed) > 0,
        "submission_ready": best_grade >= 3,
        "notes": program.notes,
    }


def run_immunefi_scan(
    *,
    config_path: Path | None = None,
    ecosystem: str | None = None,
    min_max_bounty_usd: int = 0,
    limit: int | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    """Scan curated Immunefi programs and write a ranked report."""
    base_config = load_config(config_path)
    config = _scan_config(base_config)
    gates = gates_from_config(config)
    catalog = get_exploit_catalog()
    programs = list_programs(ecosystem=ecosystem, min_max_bounty_usd=min_max_bounty_usd)
    if limit is not None:
        programs = programs[:limit]

    results: list[dict[str, Any]] = []
    for program in programs:
        results.append(scan_program(program, config, catalog, gates))

    results.sort(
        key=lambda r: (
            r["submission_ready"],
            r["best_evidence_grade"],
            r["solana_reproduced"],
            r["candidates_passed"],
            r["max_bounty_usd"],
        ),
        reverse=True,
    )

    report = {
        "schema_version": "1.0",
        "source": "night-shift-security",
        "mode": "shoestring",
        "zero_rpc": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "platform_total_programs": 213,
        "curated_programs_scanned": len(results),
        "ecosystem_filter": ecosystem,
        "min_max_bounty_usd": min_max_bounty_usd,
        "programs": results,
        "summary": {
            "engine_ready_count": sum(1 for r in results if r["engine_ready"]),
            "submission_ready_count": sum(1 for r in results if r["submission_ready"]),
            "solana_reproduced_total": sum(r["solana_reproduced"] for r in results),
            "top_programs": [r["slug"] for r in results[:5]],
        },
    }

    out = output_dir or Path(config.get("output_dir", "data/security_results"))
    scan_dir = out / "immunefi_scan"
    scan_dir.mkdir(parents=True, exist_ok=True)
    json_path = scan_dir / "latest.json"
    json_path.write_text(json.dumps(report, indent=2, default=str))

    md_lines = [
        "# Immunefi Engine Scan (Shoestring)",
        "",
        f"**Scanned**: {len(results)} curated programs (of 213 on Immunefi)",
        f"**Mode**: zero-RPC simulation + Solana fixture where analogue exists",
        f"**Generated**: {report['generated_at']}",
        "",
        "## Summary",
        f"- Engine-ready (passed gates): **{report['summary']['engine_ready_count']}**",
        f"- Submission-ready (grade ≥3): **{report['summary']['submission_ready_count']}**",
        f"- Solana fixture reproduced: **{report['summary']['solana_reproduced_total']}**",
        "",
        "## Ranked Results",
        "",
        "| Program | Max Bounty | Passed | Grade | Solana Repro | Analogue |",
        "|---------|------------|--------|-------|--------------|----------|",
    ]
    for r in results:
        md_lines.append(
            f"| [{r['name']}]({r['url']}) | ${r['max_bounty_usd']:,} | "
            f"{r['candidates_passed']} | {r['best_evidence_grade']} | "
            f"{r['solana_reproduced']} | `{r['catalog_analogue'] or '—'}` |"
        )
    md_lines.extend([
        "",
        "## Notes",
        "",
        "This scan uses **catalog analogues** and **simulation** — not live mainnet probing. ",
        "Immunefi prohibits mainnet testing; validator/fork upgrade requires grant-funded RPC.",
        "",
    ])
    md_path = scan_dir / "latest.md"
    md_path.write_text("\n".join(md_lines))

    report["paths"] = {"json": str(json_path), "markdown": str(md_path)}
    return report