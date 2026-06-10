"""Deterministic coordinator — global attack-surface state and mission lifecycle."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from night_shift_security.config.loader import load_config
from night_shift_security.core.pipeline import run_security_pipeline
from night_shift_security.data.recon import load_recon
from night_shift_security.knowledge.findings_store import (
    FindingsStore,
    StoredRecord,
    best_evidence_per_lineage_root,
    campaign_stats,
    load_store,
)

MissionStatus = Literal["planned", "spawned", "completed", "retired"]

_DEFAULT_STATE_PATH = Path("data/security_results/knowledge/coordinator_state.json")
_DEFAULT_DEBRIEF_DIR = Path("data/security_results/knowledge/debriefs")
_REFINEMENT_GRADE_MIN = 1
_REFINEMENT_GRADE_MAX = 2
_SURVIVAL_RATE_FLOOR = 0.4
_PLATEAU_GRADE = 4


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_state_path() -> Path:
    return _DEFAULT_STATE_PATH


def _params_fingerprint(template_id: str, parameters: dict[str, Any]) -> str:
    normalized: list[tuple[str, Any]] = []
    for key, value in sorted(parameters.items()):
        if isinstance(value, float):
            normalized.append((key, round(value, 4)))
        else:
            normalized.append((key, value))
    payload = json.dumps([template_id, normalized], sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


@dataclass
class AttackSurfaceCoverage:
    target_id: str
    covered_templates: list[str] = field(default_factory=list)
    covered_invariants: list[str] = field(default_factory=list)
    attempted_fingerprints: list[str] = field(default_factory=list)
    missions_completed: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AttackSurfaceCoverage:
        return cls(
            target_id=str(data.get("target_id", "")),
            covered_templates=list(data.get("covered_templates", [])),
            covered_invariants=list(data.get("covered_invariants", [])),
            attempted_fingerprints=list(data.get("attempted_fingerprints", [])),
            missions_completed=int(data.get("missions_completed", 0)),
        )


@dataclass
class Mission:
    mission_id: str
    campaign_id: str
    target_id: str
    template_id: str
    objective: str
    seed_hypothesis_ids: list[str] = field(default_factory=list)
    status: MissionStatus = "planned"
    generation_method: str = "coordinator"
    priority_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Mission:
        return cls(
            mission_id=str(data["mission_id"]),
            campaign_id=str(data.get("campaign_id", "")),
            target_id=str(data.get("target_id", "")),
            template_id=str(data.get("template_id", "")),
            objective=str(data.get("objective", "")),
            seed_hypothesis_ids=list(data.get("seed_hypothesis_ids", [])),
            status=data.get("status", "planned"),  # type: ignore[arg-type]
            generation_method=str(data.get("generation_method", "coordinator")),
            priority_reason=str(data.get("priority_reason", "")),
        )


@dataclass
class MissionDebrief:
    mission_id: str
    run_at: str
    candidates_evaluated: int
    candidates_passed: int
    findings_promoted: int
    max_evidence_grade: int
    fork_reproduced: int
    solana_reproduced: int
    catalog_analogue: bool
    submission_readiness: str
    lineage_roots_touched: list[str]
    promotion_recommendations: list[dict[str, Any]]
    report_json: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MissionDebrief:
        return cls(
            mission_id=str(data["mission_id"]),
            run_at=str(data.get("run_at", "")),
            candidates_evaluated=int(data.get("candidates_evaluated", 0)),
            candidates_passed=int(data.get("candidates_passed", 0)),
            findings_promoted=int(data.get("findings_promoted", 0)),
            max_evidence_grade=int(data.get("max_evidence_grade", 0)),
            fork_reproduced=int(data.get("fork_reproduced", 0)),
            solana_reproduced=int(data.get("solana_reproduced", 0)),
            catalog_analogue=bool(data.get("catalog_analogue", False)),
            submission_readiness=str(data.get("submission_readiness", "draft")),
            lineage_roots_touched=list(data.get("lineage_roots_touched", [])),
            promotion_recommendations=list(data.get("promotion_recommendations", [])),
            report_json=str(data.get("report_json", "")),
        )


@dataclass
class CoordinatorState:
    campaign_id: str
    target_id: str
    config_path: str
    coverage: AttackSurfaceCoverage
    mission_history: list[Mission] = field(default_factory=list)
    pending_missions: list[Mission] = field(default_factory=list)
    last_updated: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "target_id": self.target_id,
            "config_path": self.config_path,
            "coverage": self.coverage.to_dict(),
            "mission_history": [m.to_dict() for m in self.mission_history],
            "pending_missions": [m.to_dict() for m in self.pending_missions],
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CoordinatorState:
        return cls(
            campaign_id=str(data.get("campaign_id", "")),
            target_id=str(data.get("target_id", "")),
            config_path=str(data.get("config_path", "")),
            coverage=AttackSurfaceCoverage.from_dict(data.get("coverage", {})),
            mission_history=[
                Mission.from_dict(item) for item in data.get("mission_history", [])
            ],
            pending_missions=[
                Mission.from_dict(item) for item in data.get("pending_missions", [])
            ],
            last_updated=str(data.get("last_updated", "")),
        )


def _resolve_target_config_path(config_path: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute():
        return path
    # Match data/target_config.py: targets live under config/targets/
    return config_path.parent / "targets" / path.name


def _target_id_from_config(config: dict[str, Any], config_path: Path | None = None) -> str:
    target = config.get("target", {})
    if target.get("target_id"):
        return str(target["target_id"])
    if target.get("config_path") and config_path is not None:
        target_path = _resolve_target_config_path(config_path, str(target["config_path"]))
        target_cfg = load_config(target_path)
        return str(target_cfg.get("target_id", "unknown"))
    return "unknown"


def _primary_surfaces(recon: dict[str, Any] | None, config: dict[str, Any]) -> list[str]:
    if recon:
        threat = recon.get("threat_model", {})
        surfaces = threat.get("primary_surfaces")
        if surfaces:
            return list(surfaces)
    return list(config.get("templates", []))


def _invariant_ids(recon: dict[str, Any] | None) -> list[str]:
    if not recon:
        return []
    return [str(inv.get("id", "")) for inv in recon.get("invariants", []) if inv.get("id")]


def _mission_objective(template_id: str, recon: dict[str, Any] | None) -> str:
    if recon:
        invariants = recon.get("invariants", [])
        related = [
            inv.get("description", inv.get("id", ""))
            for inv in invariants
            if template_id in str(inv.get("id", ""))
            or template_id.replace("_", " ") in str(inv.get("description", "")).lower()
        ]
        if related:
            return f"Probe {template_id}: {related[0]}"
    return f"Systematic probe of {template_id} attack surface"


def init_state(
    config_path: Path,
    *,
    state_path: Path | None = None,
    recon: dict[str, Any] | None = None,
) -> CoordinatorState:
    """Bootstrap coordinator state from campaign config and recon slice."""
    config = load_config(config_path)
    campaign = config.get("campaign", {})
    campaign_id = str(campaign.get("id", "default"))
    target_id = _target_id_from_config(config, config_path)
    recon_data = recon if recon is not None else load_recon(target_id)

    coverage = AttackSurfaceCoverage(target_id=target_id)
    surfaces = _primary_surfaces(recon_data, config)
    invariants = _invariant_ids(recon_data)
    if invariants:
        coverage.covered_invariants = []

    pending: list[Mission] = []
    for template_id in surfaces:
        pending.append(
            Mission(
                mission_id=str(uuid.uuid4()),
                campaign_id=campaign_id,
                target_id=target_id,
                template_id=template_id,
                objective=_mission_objective(template_id, recon_data),
                status="planned",
                priority_reason="initial_surface_probe",
            )
        )

    state = CoordinatorState(
        campaign_id=campaign_id,
        target_id=target_id,
        config_path=str(config_path),
        coverage=coverage,
        pending_missions=pending,
        last_updated=_utc_now_iso(),
    )
    save_state(state, state_path or default_state_path())
    return state


def load_state(path: Path) -> CoordinatorState:
    if not path.is_file():
        raise FileNotFoundError(f"Coordinator state not found: {path}")
    data = json.loads(path.read_text())
    return CoordinatorState.from_dict(data)


def save_state(state: CoordinatorState, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    state.last_updated = _utc_now_iso()
    path.write_text(json.dumps(state.to_dict(), indent=2, default=str) + "\n")


def build_coverage(store: FindingsStore, campaign_id: str, target_id: str) -> AttackSurfaceCoverage:
    """Derive attack-surface coverage from findings store records."""
    records = (
        [r for r in store.records if r.campaign_id == campaign_id]
        if campaign_id
        else list(store.records)
    )

    covered_templates: set[str] = set()
    fingerprints: set[str] = set()
    covered_invariants: set[str] = set()
    missions_completed = 0

    for record in records:
        if record.target_id and record.target_id != target_id:
            continue
        if record.template_id:
            covered_templates.add(record.template_id)
        if record.parameters:
            fingerprints.add(_params_fingerprint(record.template_id, record.parameters))
        if record.promoted or record.evidence_grade >= 1:
            root = record.lineage[0] if record.lineage else record.hypothesis_id
            if root:
                covered_invariants.add(root)

    return AttackSurfaceCoverage(
        target_id=target_id,
        covered_templates=sorted(covered_templates),
        covered_invariants=sorted(covered_invariants),
        attempted_fingerprints=sorted(fingerprints),
        missions_completed=missions_completed,
    )


def _template_plateaued(records: list[StoredRecord], template_id: str) -> bool:
    template_records = [r for r in records if r.template_id == template_id]
    if not template_records:
        return False
    return all(
        r.catalog_analogue and r.evidence_grade >= _PLATEAU_GRADE
        for r in template_records
    )


def _refinement_seeds(store: FindingsStore, campaign_id: str) -> dict[str, list[str]]:
    """Map template_id → lineage root hypothesis IDs worth refining."""
    records = [r for r in store.records if r.campaign_id == campaign_id]
    best = best_evidence_per_lineage_root(store)
    seeds: dict[str, list[str]] = {}

    for record in records:
        if record.evidence_grade < _REFINEMENT_GRADE_MIN or record.evidence_grade > _REFINEMENT_GRADE_MAX:
            continue
        if record.axis_survival_rate < _SURVIVAL_RATE_FLOOR:
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


def _novelty_by_template(store: FindingsStore, campaign_id: str) -> dict[str, float]:
    buckets: dict[str, list[float]] = {}
    for record in store.records:
        if record.campaign_id != campaign_id:
            continue
        if record.novelty_score <= 0:
            continue
        buckets.setdefault(record.template_id, []).append(record.novelty_score)
    return {
        template: sum(scores) / len(scores)
        for template, scores in buckets.items()
    }


def _mission_priority_key(
    template_id: str,
    *,
    surfaces: list[str],
    coverage: AttackSurfaceCoverage,
    refinement_seeds: dict[str, list[str]],
    novelty_by_template: dict[str, float],
    plateaued: bool,
) -> tuple:
    uncovered = 1 if template_id not in coverage.covered_templates else 0
    has_refinement = 1 if refinement_seeds.get(template_id) else 0
    novelty_gap = 1.0 - novelty_by_template.get(template_id, 0.5)
    surface_order = -(surfaces.index(template_id)) if template_id in surfaces else 0
    plateau_penalty = -1 if plateaued else 0
    return (uncovered, has_refinement, novelty_gap, surface_order, plateau_penalty, template_id)


def prioritize_missions(
    state: CoordinatorState,
    store: FindingsStore,
    recon: dict[str, Any] | None = None,
) -> list[Mission]:
    """Deterministically rank pending missions by coverage and store signals."""
    config = load_config(Path(state.config_path))
    recon_data = recon if recon is not None else load_recon(state.target_id)
    surfaces = _primary_surfaces(recon_data, config)
    campaign_records = [r for r in store.records if r.campaign_id == state.campaign_id]
    refinement_seeds = _refinement_seeds(store, state.campaign_id)
    novelty_by_template = _novelty_by_template(store, state.campaign_id)

    ranked: list[tuple[tuple, Mission]] = []
    for mission in state.pending_missions:
        if mission.status not in ("planned", "spawned"):
            continue
        plateaued = _template_plateaued(campaign_records, mission.template_id)
        key = _mission_priority_key(
            mission.template_id,
            surfaces=surfaces,
            coverage=state.coverage,
            refinement_seeds=refinement_seeds,
            novelty_by_template=novelty_by_template,
            plateaued=plateaued,
        )
        seeds = refinement_seeds.get(mission.template_id, [])
        if seeds:
            mission.seed_hypothesis_ids = seeds[:3]
            mission.priority_reason = "refinement_candidate"
        elif mission.template_id not in state.coverage.covered_templates:
            mission.priority_reason = "uncovered_surface"
        elif plateaued:
            mission.priority_reason = "plateau_deprioritized"
        else:
            mission.priority_reason = "novelty_gap"
        ranked.append((key, mission))

    ranked.sort(key=lambda item: item[0], reverse=True)
    return [mission for _, mission in ranked]


def plan_missions(
    state: CoordinatorState,
    store: FindingsStore,
    *,
    top_n: int = 3,
    recon: dict[str, Any] | None = None,
) -> list[Mission]:
    """Return top-N missions for Hermes delegate expansion."""
    ordered = prioritize_missions(state, store, recon=recon)
    return ordered[: max(top_n, 0)]


def refine_promotions(
    debrief: MissionDebrief,
    store: FindingsStore,
    campaign_id: str,
) -> list[dict[str, Any]]:
    """Deterministic escalation flags for the next planning cycle."""
    recommendations: list[dict[str, Any]] = []
    campaign_records = [r for r in store.records if r.campaign_id == campaign_id]

    if debrief.solana_reproduced > 0 and not any(r.deployed_viable for r in campaign_records):
        recommendations.append({
            "action": "escalate_to_validator",
            "reason": "fixture_reproduced_without_deployed_viable",
            "mission_id": debrief.mission_id,
        })

    for root in debrief.lineage_roots_touched:
        children = [
            r for r in campaign_records
            if root in r.lineage and r.hypothesis_id != root
        ]
        for child in children:
            parent = next((r for r in campaign_records if r.hypothesis_id == root), None)
            if parent and child.novelty_score > parent.novelty_score and child.evidence_grade < 3:
                recommendations.append({
                    "action": "expand_lineage",
                    "hypothesis_id": child.hypothesis_id,
                    "parent_id": root,
                    "reason": "child_novelty_exceeds_parent",
                })

        rejections = [r for r in campaign_records if (r.lineage[0] if r.lineage else r.hypothesis_id) == root and r.rejected]
        if len(rejections) >= 2 and all(r.evidence_grade == 0 for r in rejections):
            recommendations.append({
                "action": "discard_lineage",
                "lineage_root": root,
                "reason": "repeated_grade_zero_rejections",
            })

    if debrief.max_evidence_grade >= 3 and debrief.submission_readiness == "strict":
        recommendations.append({
            "action": "hold_for_human",
            "reason": "strict_submission_readiness_level_3_plus",
            "mission_id": debrief.mission_id,
        })

    return recommendations


def debrief_mission(
    mission: Mission,
    run_result: dict[str, Any],
    *,
    report_json_path: Path | None = None,
) -> MissionDebrief:
    """Build structured post-run summary from pipeline return dict."""
    report_json = str(run_result.get("report_json", ""))
    lineage_roots: list[str] = []
    max_grade = 0
    catalog_analogue = False
    submission_readiness = "draft"

    if report_json_path and report_json_path.is_file():
        payload = json.loads(report_json_path.read_text())
        for finding in payload.get("findings", []):
            grade = int(finding.get("evidence_grade", 0))
            max_grade = max(max_grade, grade)
            if finding.get("catalog_analogue"):
                catalog_analogue = True
            readiness = finding.get("submission_readiness", "draft")
            if readiness in ("strict", "shoestring"):
                submission_readiness = readiness
            meta = finding.get("metadata", {}) or {}
            lineage = meta.get("lineage") or finding.get("lineage") or []
            if lineage:
                lineage_roots.append(str(lineage[0]))
            elif finding.get("hypothesis_id"):
                lineage_roots.append(str(finding["hypothesis_id"]))

    store_stats = run_result.get("findings_store", {})
    if isinstance(store_stats, dict) and store_stats.get("lineage_roots"):
        pass

    debrief = MissionDebrief(
        mission_id=mission.mission_id,
        run_at=str(run_result.get("run_at") or _utc_now_iso()),
        candidates_evaluated=int(run_result.get("candidates_evaluated", 0)),
        candidates_passed=int(run_result.get("candidates_passed", 0)),
        findings_promoted=int(run_result.get("findings", 0)),
        max_evidence_grade=max_grade,
        fork_reproduced=int(run_result.get("fork_reproduced", 0)),
        solana_reproduced=int(run_result.get("solana_reproduced", 0)),
        catalog_analogue=catalog_analogue,
        submission_readiness=submission_readiness,
        lineage_roots_touched=sorted(set(lineage_roots)),
        promotion_recommendations=[],
        report_json=report_json,
    )
    return debrief


def _write_debrief(debrief: MissionDebrief, debrief_dir: Path | None = None) -> Path:
    out_dir = debrief_dir or _DEFAULT_DEBRIEF_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{debrief.mission_id}.json"
    path.write_text(json.dumps(debrief.to_dict(), indent=2, default=str) + "\n")
    return path


def update_state(
    state: CoordinatorState,
    mission: Mission,
    debrief: MissionDebrief,
    store: FindingsStore,
) -> CoordinatorState:
    """Retire completed mission and merge coverage from store."""
    mission.status = "retired"
    state.mission_history.append(mission)
    state.pending_missions = [m for m in state.pending_missions if m.mission_id != mission.mission_id]
    state.coverage = build_coverage(store, state.campaign_id, state.target_id)
    state.coverage.missions_completed = len(state.mission_history)

    if mission.template_id not in state.coverage.covered_templates:
        state.coverage.covered_templates.append(mission.template_id)
        state.coverage.covered_templates.sort()

    for rec in debrief.promotion_recommendations:
        if rec.get("action") == "expand_lineage":
            template_id = mission.template_id
            hypothesis_id = str(rec.get("hypothesis_id", ""))
            if hypothesis_id and not any(
                m.template_id == template_id and hypothesis_id in m.seed_hypothesis_ids
                for m in state.pending_missions
            ):
                state.pending_missions.append(
                    Mission(
                        mission_id=str(uuid.uuid4()),
                        campaign_id=state.campaign_id,
                        target_id=state.target_id,
                        template_id=template_id,
                        objective=f"Refine lineage from {hypothesis_id}",
                        seed_hypothesis_ids=[hypothesis_id],
                        status="planned",
                        priority_reason="lineage_expansion",
                    )
                )

    state.last_updated = _utc_now_iso()
    return state


def run_mission_cycle(
    state: CoordinatorState,
    *,
    proposals_path: Path | None = None,
    state_path: Path | None = None,
    store_path: Path | None = None,
    debrief_dir: Path | None = None,
) -> dict[str, Any]:
    """Execute top pending mission: pipeline → debrief → state update."""
    store_cfg = load_config(Path(state.config_path))
    findings_path = Path(
        store_cfg.get("findings_store", {}).get(
            "path", "data/security_results/knowledge/findings_store.jsonl"
        )
    )
    store = load_store(store_path or findings_path)

    ordered = prioritize_missions(state, store)
    if not ordered:
        return {"status": "idle", "message": "No pending missions", "state": state.to_dict()}

    mission = ordered[0]
    mission.status = "spawned"

    config_path = Path(state.config_path)
    run_result = run_security_pipeline(config_path=config_path, proposals_path=proposals_path)

    report_json_path = Path(run_result.get("report_json", ""))
    debrief = debrief_mission(mission, run_result, report_json_path=report_json_path)
    debrief.promotion_recommendations = refine_promotions(debrief, store, state.campaign_id)

    store = load_store(store_path or findings_path)
    mission.status = "completed"
    state = update_state(state, mission, debrief, store)

    debrief_path = _write_debrief(debrief, debrief_dir)
    save_state(state, state_path or default_state_path())

    return {
        "status": "completed",
        "mission": mission.to_dict(),
        "debrief": debrief.to_dict(),
        "debrief_path": str(debrief_path),
        "pipeline": run_result,
        "state": state.to_dict(),
    }


def coordinator_status(state: CoordinatorState, store: FindingsStore) -> dict[str, Any]:
    """Aggregate status for CLI display."""
    stats = campaign_stats(store, state.campaign_id)
    next_missions = plan_missions(state, store, top_n=3)
    return {
        "campaign_id": state.campaign_id,
        "target_id": state.target_id,
        "config_path": state.config_path,
        "coverage": state.coverage.to_dict(),
        "missions_completed": len(state.mission_history),
        "pending_count": len(state.pending_missions),
        "next_missions": [m.to_dict() for m in next_missions],
        "campaign_stats": stats,
        "last_updated": state.last_updated,
    }