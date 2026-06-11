"""Shared zero-RPC bounty discovery scan — Immunefi + Cantina."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from night_shift_security.config.loader import gates_from_config, load_config
from night_shift_security.core.evaluation import rank_candidates
from night_shift_security.core.results import findings_from_candidates
from night_shift_security.core.target_harness import evaluate_target_vectors, generate_target_vectors
from night_shift_security.data.bounty_program import BountyProgram, program_summary, program_to_live_target
from night_shift_security.data.cantina_registry import CANTINA_PROGRAMS, list_programs as list_cantina
from night_shift_security.data.exploit_catalog import get_exploit_catalog
from night_shift_security.data.immunefi_registry import IMMUNEFI_PROGRAMS, immunefi_to_bounty, list_programs as list_immunefi
from night_shift_security.data.schemas import AttackCandidateResult
from night_shift_security.data.target_config import resolve_target_exploit
from night_shift_security.validation.evidence_grading import shoestring_evidence_grade_candidate
from night_shift_security.validation.solana_validation import run_solana_validation_phase
from night_shift_security.validation.validation_layer import refresh_validation_batch

import night_shift_security.domain.attack_templates.access_control_escalation  # noqa: F401
import night_shift_security.domain.attack_templates.composability_risk  # noqa: F401
import night_shift_security.domain.attack_templates.flash_loan_oracle  # noqa: F401
import night_shift_security.domain.attack_templates.governance_capture  # noqa: F401
import night_shift_security.domain.attack_templates.reentrancy  # noqa: F401
import night_shift_security.domain.attack_templates.treasury_drain  # noqa: F401
import night_shift_security.domain.attack_templates.upgradeability_risk  # noqa: F401

PlatformFilter = Literal["immunefi", "cantina", "all"]


def _scan_evidence_grade(candidate: AttackCandidateResult) -> int:
    return shoestring_evidence_grade_candidate(candidate)


def scan_config(base: dict[str, Any]) -> dict[str, Any]:
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
    program: BountyProgram,
    config: dict[str, Any],
    catalog: list,
    gates,
) -> dict[str, Any]:
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
    findings_from_candidates(passed[:5], {})

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


def list_programs_for_platform(
    platform: PlatformFilter,
    *,
    ecosystem: str | None = None,
    min_max_bounty_usd: int = 0,
) -> list[BountyProgram]:
    if platform == "immunefi":
        return [immunefi_to_bounty(p) for p in list_immunefi(ecosystem=ecosystem, min_max_bounty_usd=min_max_bounty_usd)]
    if platform == "cantina":
        return list_cantina(ecosystem=ecosystem, min_max_bounty_usd=min_max_bounty_usd)
    immunefi = [immunefi_to_bounty(p) for p in list_immunefi(ecosystem=ecosystem, min_max_bounty_usd=min_max_bounty_usd)]
    cantina = list_cantina(ecosystem=ecosystem, min_max_bounty_usd=min_max_bounty_usd)
    merged = immunefi + cantina
    merged.sort(key=lambda p: p.max_bounty_usd, reverse=True)
    return merged


def _sort_scan_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        results,
        key=lambda r: (
            r["submission_ready"],
            r["best_evidence_grade"],
            r["solana_reproduced"],
            r["candidates_passed"],
            r["max_bounty_usd"],
        ),
        reverse=True,
    )


def _write_scan_markdown(results: list[dict[str, Any]], *, title: str, generated_at: str) -> str:
    platforms = {r.get("platform", "immunefi") for r in results}
    lines = [
        f"# {title}",
        "",
        f"**Scanned**: {len(results)} curated programs",
        f"**Platforms**: {', '.join(sorted(platforms))}",
        f"**Mode**: zero-RPC simulation + Solana fixture where analogue exists",
        f"**Generated**: {generated_at}",
        "",
        "## Ranked Results",
        "",
        "| Platform | Program | Max Bounty | Passed | Grade | Solana Repro | Analogue |",
        "|----------|---------|------------|--------|-------|--------------|----------|",
    ]
    for r in results:
        lines.append(
            f"| {r.get('platform', '—')} | [{r['name']}]({r['url']}) | ${r['max_bounty_usd']:,} | "
            f"{r['candidates_passed']} | {r['best_evidence_grade']} | "
            f"{r['solana_reproduced']} | `{r['catalog_analogue'] or '—'}` |"
        )
    lines.extend([
        "",
        "## Notes",
        "",
        "Catalog analogues + simulation only — not live mainnet probing.",
        "Validator/fork upgrade requires grant-funded RPC.",
        "",
    ])
    return "\n".join(lines)


def run_bounty_scan(
    *,
    config_path: Path | None = None,
    platform: PlatformFilter = "all",
    ecosystem: str | None = None,
    min_max_bounty_usd: int = 0,
    limit: int | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    base_config = load_config(config_path)
    config = scan_config(base_config)
    gates = gates_from_config(config)
    catalog = get_exploit_catalog()
    programs = list_programs_for_platform(platform, ecosystem=ecosystem, min_max_bounty_usd=min_max_bounty_usd)
    if limit is not None:
        programs = programs[:limit]

    results = [scan_program(program, config, catalog, gates) for program in programs]
    results = _sort_scan_results(results)

    immunefi_count = sum(1 for r in results if r.get("platform") == "immunefi")
    cantina_count = sum(1 for r in results if r.get("platform") == "cantina")

    report = {
        "schema_version": "1.1",
        "source": "night-shift-security",
        "mode": "shoestring",
        "zero_rpc": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "platform_filter": platform,
        "curated_programs_scanned": len(results),
        "platform_breakdown": {"immunefi": immunefi_count, "cantina": cantina_count},
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
    bounty_scan_dir = out / "bounty_scan"
    bounty_scan_dir.mkdir(parents=True, exist_ok=True)
    json_path = bounty_scan_dir / "latest.json"
    json_path.write_text(json.dumps(report, indent=2, default=str))

    md_path = bounty_scan_dir / "latest.md"
    md_path.write_text(
        _write_scan_markdown(
            results,
            title="Bounty Discovery Scan (Immunefi + Cantina)",
            generated_at=report["generated_at"],
        )
    )

    if platform in ("immunefi", "all"):
        immunefi_only = [r for r in results if r.get("platform") == "immunefi"]
        legacy_dir = out / "immunefi_scan"
        legacy_dir.mkdir(parents=True, exist_ok=True)
        legacy_report = {
            **report,
            "schema_version": "1.0",
            "platform_total_programs": 213,
            "curated_programs_scanned": len(immunefi_only),
            "programs": immunefi_only,
        }
        legacy_json = legacy_dir / "latest.json"
        legacy_json.write_text(json.dumps(legacy_report, indent=2, default=str))
        legacy_md = legacy_dir / "latest.md"
        legacy_md.write_text(
            _write_scan_markdown(
                immunefi_only,
                title="Immunefi Engine Scan (Shoestring)",
                generated_at=report["generated_at"],
            )
        )
        report["legacy_paths"] = {"immunefi_json": str(legacy_json), "immunefi_md": str(legacy_md)}

    report["paths"] = {"json": str(json_path), "markdown": str(md_path)}
    return report