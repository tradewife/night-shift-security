"""Autonomous bounty hunt loop — scan → investigate → qualify for submission."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from night_shift_security.bounty.discovery_scan import run_bounty_scan
from night_shift_security.bounty.native_picker import (
    EmptyManifest,
    NativeStatusIncomplete,
    PickRefused,
    filter_native_ready,
    has_measured_delta as _nss_has_measured_delta,
    list_pickable_slugs,
    phase4_rotation_enabled,
    pick_native_ready_or_raise,
    pick_next_target_v6_phase4,
    rank_pickable_slugs,
    rotate_target,
)
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
from night_shift_security.validation.submission_gates import qualifies_for_submission  # noqa: F401 — re-export

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
    "coinbase": "coinbase_cantina.json",
    "polymarket": "polymarket_cantina.json",
    "pendle": "euler_cantina.json",
    "uniswap": "euler_cantina.json",
    "reserve-protocol": "reserve_protocol_cantina.json",
    "jito": "kamino_shoestring.json",
}

_EVM_FORK_BASE = "euler_cantina.json"
_SOLANA_BASE = "kamino_shoestring.json"

# Slugs with live fork harness or proposal-backed depth (skip catalogue-only hunts).
FORK_READY_HUNT_SLUGS: tuple[str, ...] = (
    "wormhole",
    "morpho",
    "euler",
    "ethena",
    "kamino",
    "jito",
)


@dataclass(frozen=True)
class ProposalTargetMetadata:
    target_slug: str = ""
    campaign_id: str = ""
    required_config: str = ""
    allowed_templates: tuple[str, ...] = ()
    source_artifacts: tuple[str, ...] = ()
    force_target: bool = False
    source_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_slug": self.target_slug,
            "campaign_id": self.campaign_id,
            "required_config": self.required_config,
            "allowed_templates": list(self.allowed_templates),
            "source_artifacts": list(self.source_artifacts),
            "force_target": self.force_target,
            "source_path": self.source_path,
        }


def _as_str_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def load_proposal_target_metadata(path: Path | None) -> ProposalTargetMetadata | None:
    """Read target-pinning metadata from a Hermes proposals document."""
    if path is None:
        return None
    if not path.is_file():
        raise FileNotFoundError(f"Proposal file not found: {path}")
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError("Proposal document must be a JSON object")

    proposals = payload.get("proposals")
    proposal_slugs: set[str] = set()
    proposal_campaigns: set[str] = set()
    proposal_templates: set[str] = set()
    if isinstance(proposals, list):
        for proposal in proposals:
            if not isinstance(proposal, dict):
                continue
            slug = str(proposal.get("target_slug") or "").strip()
            campaign = str(proposal.get("campaign_id") or "").strip()
            template = str(proposal.get("template") or "").strip()
            if slug:
                proposal_slugs.add(slug)
            if campaign:
                proposal_campaigns.add(campaign)
            if template:
                proposal_templates.add(template)

    target_slug = str(payload.get("target_slug") or "").strip()
    if not target_slug and len(proposal_slugs) == 1:
        target_slug = next(iter(proposal_slugs))

    campaign_id = str(payload.get("campaign_id") or "").strip()
    if not campaign_id and len(proposal_campaigns) == 1:
        campaign_id = next(iter(proposal_campaigns))

    allowed_templates = _as_str_tuple(payload.get("allowed_templates"))
    if not allowed_templates and proposal_templates:
        allowed_templates = tuple(sorted(proposal_templates))

    return ProposalTargetMetadata(
        target_slug=target_slug,
        campaign_id=campaign_id,
        required_config=str(payload.get("required_config") or "").strip(),
        allowed_templates=allowed_templates,
        source_artifacts=_as_str_tuple(payload.get("source_artifacts")),
        force_target=bool(payload.get("force_target")),
        source_path=str(path),
    )


def _repo_path(path: str | Path) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    return _REPO_ROOT / p


def _same_path(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return left.absolute() == right.absolute()


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

    interrogation = cfg.setdefault("self_interrogation", {})
    interrogation["enabled"] = True
    interrogation.setdefault("mode", "advisory")
    interrogation["top_n"] = max(int(interrogation.get("top_n") or 0), 50)
    interrogation["rank_adjustment"] = True
    interrogation["max_rank_adjustment"] = max(
        float(interrogation.get("max_rank_adjustment") or 0.0),
        0.035,
    )

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
        "auditvault_boosted_slugs": [],
        "config_hints": {},
        "improvement_ledger_at": "",
    }


def load_loop_state(path: Path | None = None) -> dict[str, Any]:
    p = path or _DEFAULT_STATE_PATH
    if not p.is_file():
        state = _default_state()
        save_loop_state(state, p)
        return state
    state = json.loads(p.read_text())
    if not isinstance(state, dict):
        return _default_state()
    defaults = _default_state()
    for key, value in defaults.items():
        state.setdefault(key, value)
    return state


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


def _forced_target_row(target_slug: str, platform: str | None = None) -> dict[str, Any] | None:
    program = get_program_by_slug(target_slug, platform=platform) or get_program_by_slug(target_slug)
    if program is None:
        return None
    return {
        "slug": program.slug,
        "platform": program.platform,
        "name": program.name,
        "forced_target": True,
    }


def _target_mismatch_result(
    *,
    target_slug: str,
    selected_slug: str,
    proposals_path: Path | None,
    reason: str,
) -> dict[str, Any]:
    return {
        "status": "failed",
        "reason": reason,
        "proposal_target_match": False,
        "proposal_target_slug": target_slug,
        "selected_target_slug": selected_slug,
        "proposals_path": str(proposals_path) if proposals_path else "",
    }


def pick_next_target(
    scan_report: dict[str, Any],
    state: dict[str, Any],
    *,
    min_grade: int = 1,
    cooldown_hours: float = 12.0,
    prefer_full_registry: bool = False,
    manifest_path: Path | str | None = None,
    scope_registry_path: Path | str | None = None,
    raise_on_empty: bool = False,
) -> dict[str, Any] | None:
    """Select the highest-ranked program not saturated and outside cooldown.

    Audit correction C3 — the picker honours the native-harness manifest:

    * ``ready`` is preferred (so the cron focuses on programs with real substrate).
    * ``harness_built`` / ``paused`` are accepted as fallback.
    * ``missing`` / ``mapped`` slugs are filtered out.

    Audit correction C5 — ``prefer_full_registry=True`` extends the candidate
    pool beyond the curated ``scan_report.programs`` set into the full live
    ``scope_registry.json`` (audit D1 — 28-of-249 scope was structural).

    Set ``raise_on_empty=True`` to escalate a no-candidate situation to a
    typed ``PickRefused`` exception instead of returning ``None``. This is
    the cron path; the existing 28-curated callers keep the silent ``None``
    behavior so ``test_pick_next_target_excludes_saturated`` stays green.
    """
    # Phase 4 rotation — opt-in wrapper.  When enabled, cold programs float
    # to the top of the queue via a time-decayed bounty-priority score.
    if phase4_rotation_enabled():
        result = pick_next_target_v6_phase4(
            scan_report,
            state,
            cooldown_hours=cooldown_hours,
            prefer_full_registry=prefer_full_registry,
            manifest_path=manifest_path,
            scope_registry_path=scope_registry_path,
            raise_on_empty=raise_on_empty,
        )
        if result is not None:
            rotate_target(state, result["slug"])
        return result

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
    auditvault_boost = list(state.get("auditvault_boosted_slugs") or [])
    targets = pick_investigation_targets(
        scan_report,
        top_n=50,
        min_evidence_grade=min_grade,
        ecosystem=None,
        exclude_slugs=list(exclude),
        boost_slugs=boost + auditvault_boost,
    )
    if not targets:
        targets = pick_investigation_targets(
            scan_report,
            top_n=1,
            min_evidence_grade=0,
            ecosystem=None,
            exclude_slugs=list(saturated),
            boost_slugs=boost + auditvault_boost,
        )
    candidates = list(targets)
    if prefer_full_registry:
        # Extend with the full live registry + canonical state. ``scan_report``
        # only carries the curated subset (audit D1).
        curated_slugs = [str(t.get("slug") or "") for t in candidates if t.get("slug")]
        extra = list_pickable_slugs(
            curated=curated_slugs,
            scope_registry_path=scope_registry_path,
        )
        ranked_extra = rank_pickable_slugs(
            extra, scope_registry_path=scope_registry_path, manifest_path=manifest_path,
        )
        seen = {str(t.get("slug") or "") for t in candidates}
        for slug in ranked_extra:
            if slug in seen:
                continue
            candidates.append({
                "slug": slug,
                "platform": "live_registry",
                "name": slug,
                "best_evidence_grade": 0,
            })
            seen.add(slug)
    elif candidates:
        # When the scan's curated subset is the only source, re-rank by
        # bounty-priority score so a ``ready`` slug with larger bounty wins
        # even when its ``best_evidence_grade`` is low.
        pre_ranked = [
            str(t.get("slug") or "") for t in candidates if t.get("slug")
        ]
        ranked_pre = rank_pickable_slugs(
            pre_ranked,
            scope_registry_path=scope_registry_path,
            manifest_path=manifest_path,
        )
        if ranked_pre:
            by_slug = {str(t.get("slug") or ""): t for t in candidates}
            candidates = [by_slug[slug] for slug in ranked_pre if slug in by_slug]

    if not candidates:
        if raise_on_empty:
            raise EmptyManifest("pick_next_target: empty candidate pool after scan")
        return None

    # Apply the native-harness precondition gate. Fall back to the legacy
    # first-candidate behavior when the manifest is empty (count == 0) — we
    # refuse silently rather than blocking the existing test surface.
    slugs = [str(c.get("slug") or "") for c in candidates if c.get("slug")]
    try:
        slug = pick_native_ready_or_raise(slugs, manifest_path=manifest_path)
    except PickRefused:
        if raise_on_empty:
            raise
        return None

    for row in candidates:
        if str(row.get("slug") or "") == slug:
            return row
    return candidates[0] if candidates else None


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
    """Catalogue-only saturation: all findings analogue + no submit candidates.

    Audit correction C4 — the saturation rule carries an escape valve: a
    slug keeps candidates disabled from saturation if it has at least one
    on-record measured-delta evidence (``measured_impact_oracle.v1`` with
    a non-zero token-unit *or* slot0 delta). This keeps the native harness
    flywheel spinning while analogue-only slugs are correctly retired.
    """
    scored = evaluation.get("scored") or []
    if not scored:
        return
    if evaluation.get("submit_candidates"):
        return
    all_analogue = all(s.get("catalog_analogue") for s in scored)
    best = evaluation.get("best_recommendation") or "hold"
    if all_analogue and best in ("hold", "shoestring_only", "polish_validator"):
        if _nss_has_measured_delta(slug):
            return
        saturated = set(state.get("saturated_slugs") or [])
        saturated.add(slug)
        state["saturated_slugs"] = sorted(saturated)


def _is_catalog_anchor_finding(scored_entry: dict[str, Any]) -> bool:
    """Audit C7 — fork repro that landed only via catalogue analogue.

    A finding is a "catalog-anchor" fork repro when either ``catalog_analogue``
    is True or the entry surfaces a ``catalog_fallback`` hint (the
    finding-store path uses ``parameters.method = "catalog_fallback"``).
    """
    if scored_entry.get("catalog_analogue"):
        return True
    params = scored_entry.get("parameters") or {}
    if isinstance(params, dict) and str(params.get("method") or "") == "catalog_fallback":
        return True
    return False


def _is_live_program_target(
    scored_entry: dict[str, Any],
    *,
    scope_registry_path: Path | str | None = None,
) -> bool:
    """Audit C7 — finding whose target_id derives from the live scope registry.

    Finds whose target_id lacks an entry in the live registry are not
    counted as live-program repros (curated analogues or templated
    fallback). ``catalog_anchor`` + ``live_program`` may overlap; the
    consumer of these labels is expected to reason over them.
    """
    target_id = str(scored_entry.get("target_id") or scored_entry.get("slug") or "").strip()
    if not target_id:
        return False
    path = Path(scope_registry_path) if scope_registry_path is not None else None
    if path is None or not path.is_file():
        return False
    try:
        payload = json.loads(path.read_text())
    except (OSError, ValueError):
        return False
    if not isinstance(payload, dict):
        return False
    entries = payload.get("entries") or {}
    if not isinstance(entries, dict):
        return False
    return target_id in entries


def _is_value_moving_finding(scored_entry: dict[str, Any]) -> bool:
    """Audit C7 — finding has fork evidence of kind ``measured_impact_oracle.v1``."""
    fe = scored_entry.get("fork_evidence") or scored_entry.get("forkEvidence") or {}
    if not isinstance(fe, dict):
        return False
    return str(fe.get("evidence_kind") or "") == "measured_impact_oracle.v1"


def _is_novel_finding(scored_entry: dict[str, Any]) -> bool:
    """Audit C7 — finding has candidate_schema_version >= 4 and is non-catalogue."""
    if scored_entry.get("catalog_analogue"):
        return False
    params = scored_entry.get("parameters") or {}
    if not isinstance(params, dict):
        return False
    candidate = params.get("candidate") or {}
    if not isinstance(candidate, dict):
        return False
    try:
        return int(candidate.get("candidate_schema_version") or 0) >= 4
    except (TypeError, ValueError):
        return False


def _record_run_labels(
    evaluation: dict[str, Any],
    *,
    scope_registry_path: Path | str | None = None,
) -> dict[str, int]:
    """Audit correction C7 — fork_reproduced breakdown labels.

    Returns four additive labels whose sum is the legacy ``fork_reproduced``
    count for the run. Existing fields/keys/consumers are unchanged.

    * ``fork_reproduced_catalog_anchor``  — replayed via catalog fallback.
    * ``fork_reproduced_live_program``    — target present in the live scope registry.
    * ``fork_reproduced_value_moving``    — non-zero measured delta via oracle.
    * ``fork_reproduced_novel``           — catalogue-free, schema v4+.

    Aliases: ``fork_reproduced`` (the legacy sum) is also returned when any
    finding carries the truthy ``fork_reproduced`` flag in the entry.
    """
    labels = {
        "fork_reproduced": 0,
        "fork_reproduced_catalog_anchor": 0,
        "fork_reproduced_live_program": 0,
        "fork_reproduced_value_moving": 0,
        "fork_reproduced_novel": 0,
    }
    scored = list(evaluation.get("scored") or [])
    for entry in scored:
        if not entry.get("fork_reproduced"):
            continue
        labels["fork_reproduced"] += 1
        if _is_catalog_anchor_finding(entry):
            labels["fork_reproduced_catalog_anchor"] += 1
        if _is_live_program_target(entry, scope_registry_path=scope_registry_path):
            labels["fork_reproduced_live_program"] += 1
        if _is_value_moving_finding(entry):
            labels["fork_reproduced_value_moving"] += 1
        if _is_novel_finding(entry):
            labels["fork_reproduced_novel"] += 1
    return labels


def run_loop_iteration(
    *,
    state_path: Path | None = None,
    scan_path: Path | None = None,
    refresh_scan: bool = False,
    min_bounty: int = 250_000,
    min_grade: int = 1,
    proposals_path: Path | None = None,
    config_path: Path | None = None,
    target_slug: str | None = None,
    pinned_target: dict[str, Any] | None = None,
    trial_index: int = 0,
    refresh_scan_once: bool = False,
) -> dict[str, Any]:
    """One loop tick: scan (optional) → pick target → pipeline → score → update state."""
    state = load_loop_state(state_path)
    state["iteration_count"] = int(state.get("iteration_count") or 0) + 1
    proposal_meta = load_proposal_target_metadata(proposals_path)
    forced_slug = (target_slug or "").strip().lower()
    if proposal_meta and proposal_meta.force_target:
        proposal_slug = proposal_meta.target_slug.lower()
        if proposal_slug and forced_slug and proposal_slug != forced_slug:
            result = _target_mismatch_result(
                target_slug=proposal_meta.target_slug,
                selected_slug=forced_slug,
                proposals_path=proposals_path,
                reason="proposal_target_mismatch",
            )
            save_loop_state(state, state_path)
            return result
        forced_slug = proposal_slug or forced_slug

    depth_slug = os.environ.get("NSS_LOOP_DEPTH_SLUG", "").strip().lower()
    if forced_slug:
        target_row = _forced_target_row(forced_slug)
        scan_report = {}
        if target_row is None:
            result = {
                "status": "failed",
                "reason": "unknown_forced_target",
                "target_slug": forced_slug,
            }
            save_loop_state(state, state_path)
            return result
        if (scan_path or _DEFAULT_SCAN_PATH).is_file():
            scan_report = json.loads((scan_path or _DEFAULT_SCAN_PATH).read_text())
    elif pinned_target is not None:
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
        prefer_full = os.environ.get("NSS_PREFER_FULL_REGISTRY") == "1"
        target_row = pick_next_target(scan_report, state, min_grade=min_grade, prefer_full_registry=prefer_full)
    else:
        scan_report = json.loads((scan_path or _DEFAULT_SCAN_PATH).read_text())
        prefer_full = os.environ.get("NSS_PREFER_FULL_REGISTRY") == "1"
        target_row = pick_next_target(scan_report, state, min_grade=min_grade, prefer_full_registry=prefer_full)
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
    proposal_target_match = True
    if proposal_meta and proposal_meta.target_slug:
        proposal_target_match = proposal_meta.target_slug.lower() == slug.lower()
        if proposal_meta.force_target and not proposal_target_match:
            result = _target_mismatch_result(
                target_slug=proposal_meta.target_slug,
                selected_slug=slug,
                proposals_path=proposals_path,
                reason="proposal_target_mismatch",
            )
            save_loop_state(state, state_path)
            return result
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
    if proposal_meta and proposal_meta.required_config:
        required = _repo_path(proposal_meta.required_config)
        if config_path is not None and not _same_path(_repo_path(config_path), required):
            result = {
                "status": "failed",
                "reason": "proposal_config_mismatch",
                "proposal_target_match": proposal_target_match,
                "proposal_required_config": proposal_meta.required_config,
                "selected_config": str(config_path),
            }
            save_loop_state(state, state_path)
            return result
        base = required
    elif config_path is not None:
        base = _repo_path(config_path)
    if not base.is_file():
        result = {
            "status": "failed",
            "reason": "missing_pipeline_config",
            "config_path": str(base),
        }
        save_loop_state(state, state_path)
        return result
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
        "proposal_target_match": proposal_target_match,
        "proposal_target_slug": proposal_meta.target_slug if proposal_meta else "",
        "proposal_campaign_id": proposal_meta.campaign_id if proposal_meta else "",
    }
    # Audit C7 — additive fork_reproduced {catalog_anchor, live_program,
    # value_moving, novel} breakdown. The legacy fork_reproduced field is the
    # sum and remains unchanged for downstream dashboards / alerts.
    label_split = _record_run_labels(evaluation)
    if label_split.get("fork_reproduced", 0) > 0:
        run_record["fork_reproduced"] = label_split["fork_reproduced"]
    run_record["fork_reproduced_catalog_anchor"] = label_split[
        "fork_reproduced_catalog_anchor"
    ]
    run_record["fork_reproduced_live_program"] = label_split[
        "fork_reproduced_live_program"
    ]
    run_record["fork_reproduced_value_moving"] = label_split[
        "fork_reproduced_value_moving"
    ]
    run_record["fork_reproduced_novel"] = label_split["fork_reproduced_novel"]
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
    status: Literal["submit_ready", "continue", "exhausted", "skipped", "failed"] = "continue"
    if submit_candidates:
        status = "submit_ready"
        state["human_gate_pending"] = True
        state.setdefault("submission_queue", []).extend(submit_candidates)
        alert_path = Path("data/security_results/loop/submission_alert.json")
        alert_path.parent.mkdir(parents=True, exist_ok=True)
        top = submit_candidates[0] if submit_candidates else {}
        program_meta = get_program_by_slug(slug)
        alert_path.write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "alert_at": _utc_now(),
                    "status": "submit_ready",
                    "finding_id": top.get("finding_id"),
                    "platform": platform,
                    "program_slug": slug,
                    "export_track": "submittable",
                    "scope_check": "pending",
                    "poc_runnable": True,
                    "kyc_required": bool(program_meta.kyc_required) if program_meta else False,
                    "deposit_usd": float(program_meta.deposit_usd) if program_meta else 0.0,
                    "kate_action": "approve_external_post",
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
        "proposal_target_match": proposal_target_match,
        "proposal": proposal_meta.to_dict() if proposal_meta else None,
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
            if result.get("status") in ("exhausted", "skipped", "failed"):
                break
            if trial_idx > 0 and pinned is None:
                break

        if results and results[-1].get("status") in ("submit_ready", "exhausted", "failed"):
            break

    return {
        "iterations_run": len(results),
        "trials_per_target": trial_count,
        "final_status": results[-1].get("status") if results else "none",
        "results": results,
    }
