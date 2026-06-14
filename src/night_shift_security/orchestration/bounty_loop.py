"""Autonomous bounty hunt loop — scan → investigate → qualify for submission."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from night_shift_security.bounty.discovery_scan import run_bounty_scan
from night_shift_security.bounty.scoring import compute_bounty_score, resolve_program_for_finding
from night_shift_security.config.loader import load_config
from night_shift_security.core.pipeline import run_security_pipeline
from night_shift_security.export.loader import findings_from_run_json
from night_shift_security.knowledge.findings_store import load_store
from night_shift_security.orchestration.recursive_improvement import run_improvement_cycle
from night_shift_security.data.bounty_program import BountyProgram, program_to_live_target
from night_shift_security.data.program_registry import get_program_by_slug
from night_shift_security.immunefi.investigate import pick_investigation_targets
from night_shift_security.validation.rpc import rpc_available
from night_shift_security.validation.task_verifier import (
    finding_balance_verified,
    finding_has_credible_reproduction,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CONFIG_DIR = _REPO_ROOT / "src" / "night_shift_security" / "config"
_DEFAULT_STATE_PATH = Path("data/security_results/loop/state.json")
_DEFAULT_SCAN_PATH = Path("data/security_results/bounty_scan/latest.json")

# Slugs fully probed as catalogue analogue (seed; state file accumulates more).
_DEFAULT_SATURATED: tuple[str, ...] = (
    "kamino",
    "raydium",
    "orca",
    "marinade",
    "wormhole",
    "euler",
)

# Per-slug pipeline config overrides (relative to config/).
_CONFIG_OVERRIDES: dict[str, str] = {
    "euler": "euler_cantina.json",
    "wormhole": "wormhole_triage.json",
    "kamino": "kamino_klend.json",
    "morpho": "euler_cantina.json",
    "coinbase": "wormhole_fork.json",
    "polymarket": "wormhole_fork.json",
    "pendle": "euler_cantina.json",
    "uniswap": "euler_cantina.json",
    "reserve-protocol": "euler_cantina.json",
}

_EVM_FORK_BASE = "euler_cantina.json"
_SOLANA_BASE = "kamino_shoestring.json"

# Slugs with live fork harness or proposal-backed depth (skip catalogue-only hunts).
FORK_READY_HUNT_SLUGS: tuple[str, ...] = ("wormhole", "morpho", "euler", "ethena", "kamino")


def pick_fork_ready_hunt_slugs(
    *,
    max_targets: int,
    exclude_slugs: list[str] | None = None,
    env_override: str | None = None,
    ignore_saturation: bool = False,
) -> list[str]:
    """Return fork-ready slugs for hunt rotation (not scan catalogue smokes).

    When ``ignore_saturation`` is True, fork-ready slugs are not filtered by
    ``exclude_slugs`` (same policy as ``NSS_LOOP_DEPTH_SLUG`` depth passes).
    """
    if env_override and env_override.strip():
        slugs = [s.strip() for s in env_override.split(",") if s.strip()]
    else:
        slugs = list(FORK_READY_HUNT_SLUGS)

    if not ignore_saturation:
        excluded = set(exclude_slugs or [])
        slugs = [s for s in slugs if s not in excluded]

    return slugs[: max(max_targets, 1)]


def klend_live_preflight() -> dict[str, Any]:
    """Fail fast when bounty-depth Kamino cannot run live validator harness."""
    from night_shift_security.validation.solana_rpc import solana_status, solana_validator_ready

    fixture = os.environ.get("NSS_KLEND_FIXTURE", "").strip().lower()
    if fixture in ("1", "true", "yes"):
        raise RuntimeError("NSS_KLEND_FIXTURE must be 0 for bounty-depth Kamino live harness")
    status = solana_status()
    if not solana_validator_ready():
        raise RuntimeError(f"KLend live preflight failed — validator/RPC not ready: {status}")
    return status


def _hipif_bounty_depth_enabled() -> bool:
    return os.environ.get("NSS_HIPIF_BOUNTY_DEPTH", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "full",
        "bounty",
    )


def _apply_hipif_bounty_depth(cfg: dict[str, Any], program: BountyProgram) -> None:
    """Raise hypothesis + validation depth for long-running bounty hunts."""
    if not _hipif_bounty_depth_enabled():
        return

    hyp = cfg.setdefault("hypothesis_generation", {})
    hyp["samples_per_template"] = max(int(hyp.get("samples_per_template") or 0), 12)

    darwin = cfg.setdefault("darwinian", {})
    darwin["enabled"] = True
    darwin["population"] = max(int(darwin.get("population") or 0), 12)
    darwin["generations"] = max(int(darwin.get("generations") or 0), 3)
    darwin["offspring_per_parent"] = max(int(darwin.get("offspring_per_parent") or 0), 2)

    mc = cfg.setdefault("monte_carlo", {})
    mc["enabled"] = True
    mc["top_n"] = max(int(mc.get("top_n") or 0), 8)
    mc["n_simulations"] = max(int(mc.get("n_simulations") or 0), 50)

    cpcv = cfg.setdefault("cpcv", {})
    cpcv["enabled"] = True
    cpcv["top_n"] = max(int(cpcv.get("top_n") or 0), 5)

    fork = cfg.get("fork_validation") or {}
    fork_enabled = bool(fork.get("enabled"))
    if program.ecosystem in ("evm", "multichain") and (fork_enabled or program.slug == "wormhole"):
        fork = cfg.setdefault("fork_validation", {})
        fork["enabled"] = True
        min_fork = 10 if program.slug == "wormhole" else 8
        fork["top_n"] = max(int(fork.get("top_n") or 0), min_fork)
        foundry = cfg.setdefault("foundry", {})
        foundry["enabled"] = True
        foundry["top_n"] = max(int(foundry.get("top_n") or 0), 5)
    elif program.ecosystem == "solana":
        sol = cfg.setdefault("solana_validation", {})
        sol["enabled"] = True
        sol["top_n"] = max(int(sol.get("top_n") or 0), 10)
        if program.slug == "kamino":
            sol["klend_require_live"] = True


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_state() -> dict[str, Any]:
    return {
        "version": 1,
        "created_at": _utc_now(),
        "saturated_slugs": list(_DEFAULT_SATURATED),
        "runs": [],
        "submission_queue": [],
        "human_gate_pending": False,
        "last_scan_at": "",
        "iteration_count": 0,
        "refinement_queue": [],
        "template_plateaus": {},
        "run_fingerprints": {},
        "cooldown_overrides": {},
        "scan_boost_slugs": [],
        "config_hints": {},
        "improvement_ledger_at": "",
    }


def load_loop_state(path: Path | None = None) -> dict[str, Any]:
    p = path or _DEFAULT_STATE_PATH
    if not p.is_file():
        state = _default_state()
        save_loop_state(state, p)
        return state
    return json.loads(p.read_text())


def save_loop_state(state: dict[str, Any], path: Path | None = None) -> Path:
    p = path or _DEFAULT_STATE_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2, default=str) + "\n")
    return p


def _rpc_env_for(program: BountyProgram) -> str:
    return "SOLANA_MAINNET_RPC_URL" if program.ecosystem == "solana" else "ETHEREUM_RPC_URL"


def rpc_ready_for(program: BountyProgram) -> bool:
    env = _rpc_env_for(program)
    return bool(os.environ.get(env, "").strip()) or (
        env == "ETHEREUM_RPC_URL" and bool(os.environ.get("FOUNDRY_FORK_URL", "").strip())
    )


def resolve_pipeline_config_path(program: BountyProgram) -> Path:
    """Pick the best pipeline config for a program given RPC availability."""
    override = _CONFIG_OVERRIDES.get(program.slug)
    if override:
        path = _CONFIG_DIR / override
        if path.is_file():
            if program.ecosystem == "evm" and "fork" in override and not rpc_ready_for(program):
                return _CONFIG_DIR / "kamino_shoestring.json"
            return path
    if program.ecosystem == "evm" and rpc_ready_for(program):
        return _CONFIG_DIR / _EVM_FORK_BASE
    return _CONFIG_DIR / _SOLANA_BASE


def build_loop_config(
    program: BountyProgram,
    *,
    base_config_path: Path,
    campaign_prefix: str = "loop",
) -> dict[str, Any]:
    """Build a run config with live target + fork/solana toggles from base template."""
    cfg = deepcopy(load_config(base_config_path))
    target = program_to_live_target(program)
    month = datetime.now(timezone.utc).strftime("%Y-%m")

    cfg["campaign"] = {
        "id": f"{campaign_prefix}-{program.slug}-{month}",
        "name": f"Bounty loop: {program.name} ({program.platform})",
    }
    cfg["templates"] = list(program.templates)

    targets_dir = _CONFIG_DIR / "targets"
    target_file = targets_dir / f"{program.slug}.json"
    if target_file.is_file():
        cfg["target"] = {"enabled": True, "config_path": f"targets/{program.slug}.json"}
    else:
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

    if program.ecosystem == "evm" and rpc_ready_for(program):
        fork = cfg.setdefault("fork_validation", {})
        fork["enabled"] = True
        fork["always_test_catalog_evm_anchors"] = True
        if int(fork.get("top_n") or 0) < 3:
            fork["top_n"] = 3
        cfg.setdefault("solana_validation", {})["enabled"] = False
    elif program.ecosystem == "solana":
        cfg.setdefault("solana_validation", {})["enabled"] = True
        cfg.setdefault("fork_validation", {})["enabled"] = False
        if base_config_path.name == "kamino_klend.json":
            cfg.setdefault("solana_validation", {})["klend_require_live"] = True

    if base_config_path.name == "wormhole_triage.json":
        cfg.setdefault("fork_validation", {})["enabled"] = True
        cfg.setdefault("fork_validation", {})["prefer_live_programs"] = True
        cfg.setdefault("fork_validation", {})["always_test_catalog_evm_anchors"] = False
        cfg.setdefault("solana_validation", {})["enabled"] = False

    cfg.setdefault("findings_store", {})["enabled"] = True
    cfg.setdefault("findings_store", {})["path"] = "data/security_results/knowledge/findings_store.jsonl"
    _apply_hipif_bounty_depth(cfg, program)
    return cfg


def write_loop_config(program: BountyProgram, base_config_path: Path) -> Path:
    out_dir = Path("data/security_results/loop/configs")
    out_dir.mkdir(parents=True, exist_ok=True)
    cfg = build_loop_config(program, base_config_path=base_config_path)
    path = out_dir / f"{program.slug}-loop.json"
    path.write_text(json.dumps(cfg, indent=2) + "\n")
    return path


def pick_next_target(
    scan_report: dict[str, Any],
    state: dict[str, Any],
    *,
    min_grade: int = 1,
    cooldown_hours: float = 12.0,
) -> dict[str, Any] | None:
    """Select the highest-ranked program not saturated and outside cooldown."""
    saturated = set(state.get("saturated_slugs") or [])
    now = datetime.now(timezone.utc)
    overrides = state.get("cooldown_overrides") or {}
    recent: set[str] = set()
    for run in state.get("runs") or []:
        slug = str(run.get("slug") or "")
        at = run.get("at") or ""
        if not slug or not at:
            continue
        try:
            ts = datetime.fromisoformat(at.replace("Z", "+00:00"))
        except ValueError:
            continue
        slug_cooldown = float(overrides.get(slug, cooldown_hours))
        if (now - ts).total_seconds() < slug_cooldown * 3600:
            recent.add(slug)

    exclude = saturated | recent
    boost = list(state.get("scan_boost_slugs") or [])
    targets = pick_investigation_targets(
        scan_report,
        top_n=50,
        min_evidence_grade=min_grade,
        ecosystem=None,
        exclude_slugs=list(exclude),
        boost_slugs=boost,
    )
    if not targets:
        targets = pick_investigation_targets(
            scan_report,
            top_n=1,
            min_evidence_grade=0,
            ecosystem=None,
            exclude_slugs=list(saturated),
            boost_slugs=boost,
        )
    return targets[0] if targets else None


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
    )


def evaluate_findings_json(findings_path: Path) -> dict[str, Any]:
    """Score findings from a pipeline run; return submission candidates."""
    findings, run_meta = findings_from_run_json(findings_path)
    scored: list[dict[str, Any]] = []
    submit_candidates: list[dict[str, Any]] = []

    for finding in findings:
        program = resolve_program_for_finding(finding)
        score = compute_bounty_score(finding, program)
        entry = {
            "finding_id": finding.finding_id,
            "target_id": finding.target_id,
            "template_id": finding.template_id,
            "catalog_analogue": finding.catalog_analogue,
            "deployed_viable": finding.deployed_viable,
            "reproduction_tier": finding.reproduction_tier,
            "evidence_grade": finding.evidence_grade,
            "submission_recommendation": score.submission_recommendation,
            "bounty_readiness": score.bounty_readiness,
            "qualifies": qualifies_for_submission(finding, score),
        }
        scored.append(entry)
        if entry["qualifies"]:
            submit_candidates.append(entry)

    scored.sort(key=lambda x: x.get("bounty_readiness", 0), reverse=True)
    return {
        "findings_path": str(findings_path),
        "campaign_id": run_meta.get("campaign_id"),
        "scored": scored,
        "submit_candidates": submit_candidates,
        "best_recommendation": scored[0]["submission_recommendation"] if scored else "hold",
    }


def _maybe_mark_saturated(
    state: dict[str, Any],
    slug: str,
    evaluation: dict[str, Any],
) -> None:
    """Catalogue-only saturation: all findings analogue + no submit candidates."""
    scored = evaluation.get("scored") or []
    if not scored:
        return
    if evaluation.get("submit_candidates"):
        return
    all_analogue = all(s.get("catalog_analogue") for s in scored)
    best = evaluation.get("best_recommendation") or "hold"
    if all_analogue and best in ("hold", "shoestring_only", "polish_validator"):
        saturated = set(state.get("saturated_slugs") or [])
        saturated.add(slug)
        state["saturated_slugs"] = sorted(saturated)


def run_loop_iteration(
    *,
    state_path: Path | None = None,
    scan_path: Path | None = None,
    refresh_scan: bool = False,
    min_bounty: int = 250_000,
    min_grade: int = 1,
    proposals_path: Path | None = None,
    config_path: Path | None = None,
    pinned_target: dict[str, Any] | None = None,
    trial_index: int = 0,
    refresh_scan_once: bool = False,
) -> dict[str, Any]:
    """One loop tick: scan (optional) → pick target → pipeline → score → update state."""
    state = load_loop_state(state_path)
    state["iteration_count"] = int(state.get("iteration_count") or 0) + 1

    depth_slug = os.environ.get("NSS_LOOP_DEPTH_SLUG", "").strip().lower()
    if pinned_target is not None:
        target_row = pinned_target
        scan_report = {}
        if (scan_path or _DEFAULT_SCAN_PATH).is_file():
            scan_report = json.loads((scan_path or _DEFAULT_SCAN_PATH).read_text())
    elif depth_slug:
        depth_program = get_program_by_slug(depth_slug)
        if depth_program is None:
            target_row = None
            scan_report = {}
        else:
            scan_report = {}
            if (scan_path or _DEFAULT_SCAN_PATH).is_file():
                scan_report = json.loads((scan_path or _DEFAULT_SCAN_PATH).read_text())
            target_row = {
                "slug": depth_program.slug,
                "platform": depth_program.platform,
                "name": depth_program.name,
                "depth_pass": True,
            }
    elif refresh_scan or refresh_scan_once or not (scan_path or _DEFAULT_SCAN_PATH).is_file():
        scan_report = run_bounty_scan(
            config_path=config_path,
            platform="all",
            min_max_bounty_usd=min_bounty,
        )
        state["last_scan_at"] = scan_report.get("generated_at", _utc_now())
        target_row = pick_next_target(scan_report, state, min_grade=min_grade)
    else:
        scan_report = json.loads((scan_path or _DEFAULT_SCAN_PATH).read_text())
        target_row = pick_next_target(scan_report, state, min_grade=min_grade)
    if target_row is None:
        result = {
            "status": "exhausted",
            "message": "No uninvestigated targets in scan queue",
            "saturated_slugs": state.get("saturated_slugs"),
            "iteration": state["iteration_count"],
        }
        save_loop_state(state, state_path)
        return result

    slug = str(target_row.get("slug") or "")
    platform = str(target_row.get("platform") or "immunefi")
    program = get_program_by_slug(slug, platform=platform)
    if program is None:
        result = {
            "status": "skipped",
            "slug": slug,
            "reason": "unknown_program",
        }
        save_loop_state(state, state_path)
        return result

    base = resolve_pipeline_config_path(program)
    loop_config_path = write_loop_config(program, base)
    pipeline_result = run_security_pipeline(
        config_path=loop_config_path,
        proposals_path=proposals_path,
    )

    findings_json = Path(pipeline_result.get("report_json") or "")
    evaluation = (
        evaluate_findings_json(findings_json)
        if findings_json.is_file()
        else {"scored": [], "submit_candidates": [], "best_recommendation": "hold"}
    )

    run_record = {
        "slug": slug,
        "platform": platform,
        "name": program.name,
        "at": _utc_now(),
        "config_path": str(loop_config_path),
        "findings": pipeline_result.get("findings", 0),
        "fork_reproduced": pipeline_result.get("fork_reproduced", 0),
        "solana_reproduced": pipeline_result.get("solana_reproduced", 0),
        "best_recommendation": evaluation.get("best_recommendation"),
        "report_json": str(findings_json),
        "trial_index": trial_index,
    }
    state.setdefault("runs", []).append(run_record)
    state["runs"] = state["runs"][-100:]

    _maybe_mark_saturated(state, slug, evaluation)

    store = load_store(Path("data/security_results/knowledge/findings_store.jsonl"))
    improvement = run_improvement_cycle(
        state,
        slug=slug,
        evaluation=evaluation,
        store=store,
        run_record=run_record,
    )

    submit_candidates = evaluation.get("submit_candidates") or []
    status: Literal["submit_ready", "continue", "exhausted", "skipped"] = "continue"
    if submit_candidates:
        status = "submit_ready"
        state["human_gate_pending"] = True
        state.setdefault("submission_queue", []).extend(submit_candidates)
        alert_path = Path("data/security_results/loop/submission_alert.json")
        alert_path.parent.mkdir(parents=True, exist_ok=True)
        alert_path.write_text(
            json.dumps(
                {
                    "alert_at": _utc_now(),
                    "status": "submit_ready",
                    "program": slug,
                    "platform": platform,
                    "candidates": submit_candidates,
                    "report_json": str(findings_json),
                    "message": "Novel submission-qualified finding — human gate for external post",
                },
                indent=2,
            )
            + "\n"
        )

    save_loop_state(state, state_path)

    return {
        "status": status,
        "iteration": state["iteration_count"],
        "target": {"slug": slug, "platform": platform, "name": program.name},
        "scan_grade": target_row.get("best_evidence_grade"),
        "pipeline": {
            "findings": pipeline_result.get("findings", 0),
            "fork_reproduced": pipeline_result.get("fork_reproduced", 0),
            "solana_reproduced": pipeline_result.get("solana_reproduced", 0),
            "report_json": str(findings_json),
        },
        "evaluation": evaluation,
        "saturated_slugs": state.get("saturated_slugs"),
        "human_gate_pending": state.get("human_gate_pending", False),
        "rpc_ready": rpc_ready_for(program),
        "improvement": improvement,
    }


def run_bounty_loop(
    *,
    iterations: int = 1,
    trials: int | None = None,
    stop_on_submit: bool = True,
    **kwargs: Any,
) -> dict[str, Any]:
    """Run up to N loop iterations; optional trials pin the same target for M attempts."""
    trial_count = max(trials or 1, 1)
    results: list[dict[str, Any]] = []

    for _ in range(max(iterations, 1)):
        pinned: dict[str, Any] | None = None
        for trial_idx in range(trial_count):
            iter_kwargs = dict(kwargs)
            if trial_idx > 0:
                iter_kwargs["refresh_scan"] = False
            result = run_loop_iteration(
                **iter_kwargs,
                pinned_target=pinned if trial_idx > 0 else None,
                trial_index=trial_idx,
                refresh_scan_once=trial_idx == 0 and bool(iter_kwargs.get("refresh_scan")),
            )
            results.append(result)

            if trial_idx == 0 and result.get("target"):
                pinned = {
                    "slug": result["target"]["slug"],
                    "platform": result["target"]["platform"],
                }
            elif trial_idx == 0:
                pinned = None

            if stop_on_submit and result.get("status") == "submit_ready":
                break
            if result.get("status") in ("exhausted", "skipped"):
                break
            if trial_idx > 0 and pinned is None:
                break

        if results and results[-1].get("status") in ("submit_ready", "exhausted"):
            break

    return {
        "iterations_run": len(results),
        "trials_per_target": trial_count,
        "final_status": results[-1].get("status") if results else "none",
        "results": results,
    }