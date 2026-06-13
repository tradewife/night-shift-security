"""Deterministic recursive self-improvement — store signals → loop state mutations.

No LLM in this layer. Reads findings store + loop run outcomes; emits
append-only improvement ledger entries and bounded state updates.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from night_shift_security.knowledge.findings_store import (
    FindingsStore,
    StoredRecord,
    best_evidence_per_lineage_root,
)

ActionType = Literal[
    "saturate_slug",
    "extend_cooldown",
    "queue_refinement",
    "plateau_template",
    "boost_scan_priority",
    "config_fallback",
    "repeat_fingerprint",
]

REFINEMENT_GRADE_MIN = 1
REFINEMENT_GRADE_MAX = 2
SURVIVAL_RATE_FLOOR = 0.4
PLATEAU_GRADE = 4
_COOLDOWN_BUMP_HOURS = 12.0
_COOLDOWN_MAX_HOURS = 72.0
_FINGERPRINT_HISTORY = 3

_DEFAULT_LEDGER = Path("data/security_results/knowledge/improvement_ledger.jsonl")
_DEFAULT_HINTS = Path("data/security_results/loop/refinement_hints.json")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ImprovementAction:
    action_type: ActionType
    slug: str
    reason: str
    template_id: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    at: str = field(default_factory=_utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def refinement_seeds_from_store(
    store: FindingsStore,
    *,
    campaign_id: str | None = None,
    target_id: str | None = None,
) -> dict[str, list[str]]:
    """Map template_id → lineage root hypothesis IDs worth refining."""
    records = list(store.records)
    if campaign_id:
        records = [r for r in records if r.campaign_id == campaign_id]
    if target_id:
        records = [r for r in records if r.target_id == target_id]

    best = best_evidence_per_lineage_root(store)
    seeds: dict[str, list[str]] = {}

    for record in records:
        if record.evidence_grade < REFINEMENT_GRADE_MIN or record.evidence_grade > REFINEMENT_GRADE_MAX:
            continue
        if record.axis_survival_rate < SURVIVAL_RATE_FLOOR:
            continue
        root = record.lineage[0] if record.lineage else record.hypothesis_id
        if not root:
            continue
        best_root = best.get(root, {})
        if best_root.get("evidence_grade", 0) >= 3:
            continue
        seeds.setdefault(record.template_id, [])
        if root not in seeds[record.template_id]:
            seeds[record.template_id].append(root)
    return seeds


def template_plateaued(records: list[StoredRecord], template_id: str) -> bool:
    template_records = [r for r in records if r.template_id == template_id]
    if not template_records:
        return False
    return all(
        r.catalog_analogue and r.evidence_grade >= PLATEAU_GRADE
        for r in template_records
    )


def template_plateaus_for_target(store: FindingsStore, target_id: str) -> list[str]:
    records = [r for r in store.records if r.target_id == target_id]
    templates = sorted({r.template_id for r in records if r.template_id})
    return [t for t in templates if template_plateaued(records, t)]


def run_fingerprint(evaluation: dict[str, Any]) -> str:
    scored = list(evaluation.get("scored") or [])
    scored.sort(key=lambda x: float(x.get("bounty_readiness") or 0), reverse=True)
    top = scored[:3]
    payload = [
        (
            s.get("finding_id"),
            s.get("submission_recommendation"),
            s.get("catalog_analogue"),
            s.get("reproduction_tier"),
        )
        for s in top
    ]
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
    return digest[:12]


def compute_improvement_actions(
    state: dict[str, Any],
    *,
    slug: str,
    evaluation: dict[str, Any],
    store: FindingsStore,
    run_record: dict[str, Any],
) -> list[ImprovementAction]:
    """Derive deterministic improvement actions from one loop tick."""
    actions: list[ImprovementAction] = []
    fingerprint = run_fingerprint(evaluation)
    prior_fps: list[str] = list((state.get("run_fingerprints") or {}).get(slug) or [])

    if prior_fps and fingerprint == prior_fps[-1]:
        actions.append(
            ImprovementAction(
                action_type="repeat_fingerprint",
                slug=slug,
                reason="identical_top_findings_fingerprint",
                payload={"fingerprint": fingerprint},
            )
        )
        actions.append(
            ImprovementAction(
                action_type="extend_cooldown",
                slug=slug,
                reason="repeat_run_no_delta",
                payload={"bump_hours": _COOLDOWN_BUMP_HOURS},
            )
        )

    saturated = set(state.get("saturated_slugs") or [])
    if slug in saturated:
        actions.append(
            ImprovementAction(
                action_type="saturate_slug",
                slug=slug,
                reason="catalogue_only_no_submit_candidates",
            )
        )

    seeds = refinement_seeds_from_store(store, target_id=slug)
    for template_id, hypothesis_ids in sorted(seeds.items()):
        actions.append(
            ImprovementAction(
                action_type="queue_refinement",
                slug=slug,
                template_id=template_id,
                reason="grade_1_2_survivors_below_lineage_cap",
                payload={"seed_hypothesis_ids": hypothesis_ids[:3]},
            )
        )

    plateaus = template_plateaus_for_target(store, slug)
    for template_id in plateaus:
        actions.append(
            ImprovementAction(
                action_type="plateau_template",
                slug=slug,
                template_id=template_id,
                reason="catalogue_analogue_grade_4_plus",
            )
        )

    target_records = [r for r in store.records if r.target_id == slug]
    if any(
        REFINEMENT_GRADE_MIN <= r.evidence_grade <= REFINEMENT_GRADE_MAX
        and r.axis_survival_rate >= SURVIVAL_RATE_FLOOR
        for r in target_records
    ):
        actions.append(
            ImprovementAction(
                action_type="boost_scan_priority",
                slug=slug,
                reason="refinement_candidates_in_store",
            )
        )

    scored = evaluation.get("scored") or []
    if scored and all(s.get("catalog_analogue") for s in scored):
        fork_hits = int(run_record.get("fork_reproduced") or 0)
        if fork_hits > 0 and evaluation.get("best_recommendation") in (
            "hold",
            "shoestring_only",
            "polish_validator",
        ):
            actions.append(
                ImprovementAction(
                    action_type="config_fallback",
                    slug=slug,
                    reason="fork_catalogue_only",
                    payload={"hint": "novel_or_shoestring"},
                )
            )

    return actions


def apply_improvement_actions(
    state: dict[str, Any],
    actions: list[ImprovementAction],
    *,
    evaluation: dict[str, Any] | None = None,
    slug: str | None = None,
) -> dict[str, Any]:
    """Mutate loop state from improvement actions; return summary."""
    applied: list[str] = []
    cooldown_overrides: dict[str, float] = dict(state.get("cooldown_overrides") or {})
    refinement_queue: list[dict[str, Any]] = list(state.get("refinement_queue") or [])
    template_plateaus: dict[str, list[str]] = dict(state.get("template_plateaus") or {})
    scan_boost: set[str] = set(state.get("scan_boost_slugs") or [])
    config_hints: dict[str, str] = dict(state.get("config_hints") or {})
    fingerprints: dict[str, list[str]] = dict(state.get("run_fingerprints") or {})

    target_slug = slug or (actions[0].slug if actions else "")
    if evaluation and target_slug:
        fp = run_fingerprint(evaluation)
        history = list(fingerprints.get(target_slug) or [])
        history.append(fp)
        fingerprints[target_slug] = history[-_FINGERPRINT_HISTORY:]

    for action in actions:
        if action.action_type == "extend_cooldown":
            current = float(cooldown_overrides.get(action.slug, 12.0))
            bump = float(action.payload.get("bump_hours", _COOLDOWN_BUMP_HOURS))
            cooldown_overrides[action.slug] = min(current + bump, _COOLDOWN_MAX_HOURS)
            applied.append(f"extend_cooldown:{action.slug}")

        elif action.action_type == "queue_refinement":
            entry = {
                "slug": action.slug,
                "template_id": action.template_id,
                "seed_hypothesis_ids": action.payload.get("seed_hypothesis_ids", []),
                "reason": action.reason,
                "at": action.at,
            }
            refinement_queue = [e for e in refinement_queue if e.get("slug") != action.slug]
            refinement_queue.insert(0, entry)
            applied.append(f"queue_refinement:{action.slug}/{action.template_id}")

        elif action.action_type == "plateau_template":
            existing = set(template_plateaus.get(action.slug) or [])
            existing.add(action.template_id)
            template_plateaus[action.slug] = sorted(existing)
            applied.append(f"plateau_template:{action.slug}/{action.template_id}")

        elif action.action_type == "boost_scan_priority":
            scan_boost.add(action.slug)
            applied.append(f"boost_scan_priority:{action.slug}")

        elif action.action_type == "config_fallback":
            config_hints[action.slug] = str(action.payload.get("hint", "novel_or_shoestring"))
            applied.append(f"config_fallback:{action.slug}")

        elif action.action_type in ("saturate_slug", "repeat_fingerprint"):
            applied.append(f"{action.action_type}:{action.slug}")

    state["cooldown_overrides"] = cooldown_overrides
    state["refinement_queue"] = refinement_queue[:20]
    state["template_plateaus"] = template_plateaus
    state["scan_boost_slugs"] = sorted(scan_boost)
    state["config_hints"] = config_hints
    state["run_fingerprints"] = fingerprints
    state["improvement_ledger_at"] = _utc_now()

    return {"applied": applied, "action_count": len(actions)}


def append_improvement_ledger(
    actions: list[ImprovementAction],
    path: Path | None = None,
) -> Path:
    p = path or _DEFAULT_LEDGER
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as fh:
        for action in actions:
            fh.write(json.dumps(action.to_dict(), default=str) + "\n")
    return p


def write_refinement_hints(state: dict[str, Any], path: Path | None = None) -> Path | None:
    """Write top refinement queue entry for Hermes parametric pass."""
    queue = state.get("refinement_queue") or []
    if not queue:
        return None
    p = path or _DEFAULT_HINTS
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"generated_at": _utc_now(), "top": queue[0], "queue_len": len(queue)}, indent=2) + "\n")
    return p


def run_improvement_cycle(
    state: dict[str, Any],
    *,
    slug: str,
    evaluation: dict[str, Any],
    store: FindingsStore,
    run_record: dict[str, Any],
    ledger_path: Path | None = None,
    hints_path: Path | None = None,
) -> dict[str, Any]:
    """Full RSI tick: compute → apply → ledger → hints."""
    actions = compute_improvement_actions(
        state,
        slug=slug,
        evaluation=evaluation,
        store=store,
        run_record=run_record,
    )
    summary = apply_improvement_actions(state, actions, evaluation=evaluation, slug=slug)
    if actions:
        append_improvement_ledger(actions, ledger_path)
    hints = write_refinement_hints(state, hints_path)
    return {
        "actions": [a.to_dict() for a in actions],
        "summary": summary,
        "refinement_hints": str(hints) if hints else None,
    }


def analyze_loop_state(
    state: dict[str, Any],
    store: FindingsStore,
) -> dict[str, Any]:
    """Replay RSI analysis from last loop run without re-running pipeline."""
    runs = state.get("runs") or []
    if not runs:
        return {"status": "no_runs", "actions": []}
    last = runs[-1]
    slug = str(last.get("slug") or "")
    evaluation = {
        "scored": [],
        "best_recommendation": last.get("best_recommendation", "hold"),
        "submit_candidates": [],
    }
    actions = compute_improvement_actions(
        state,
        slug=slug,
        evaluation=evaluation,
        store=store,
        run_record=last,
    )
    return {
        "status": "analyzed",
        "slug": slug,
        "actions": [a.to_dict() for a in actions],
        "refinement_queue": state.get("refinement_queue"),
        "cooldown_overrides": state.get("cooldown_overrides"),
        "scan_boost_slugs": state.get("scan_boost_slugs"),
    }