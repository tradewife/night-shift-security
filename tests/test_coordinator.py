"""Tests for deterministic mission coordinator."""

import json
from pathlib import Path

from night_shift_security.core.evaluation import evaluate_attack_vector
from night_shift_security.data.exploit_catalog import catalog_states
from night_shift_security.data.schemas import AttackVector
from night_shift_security.knowledge.findings_store import (
    FindingsStore,
    StoredRecord,
    load_store,
    record_run,
)
from night_shift_security.orchestration.coordinator import (
    AttackSurfaceCoverage,
    CoordinatorState,
    Mission,
    MissionDebrief,
    build_coverage,
    debrief_mission,
    init_state,
    load_state,
    plan_missions,
    prioritize_missions,
    refine_promotions,
    save_state,
    update_state,
)


def _kamino_config_path() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "src/night_shift_security/config/kamino_shoestring.json"
    )


def _sample_candidate(
    template_id: str,
    hypothesis_id: str,
    *,
    lineage: list[str] | None = None,
    evidence_grade: int = 1,
    novelty_score: float = 0.5,
    axis_survival_rate: float = 0.6,
    catalog_analogue: bool = False,
    campaign_id: str = "kamino-immunefi-2026-06",
):
    vector = AttackVector(
        template_id=template_id,
        parameters={
            "loan_amount_usd": 25_000_000.0,
            "price_manipulation_pct": 50.0,
            "use_single_oracle": True,
        }
        if template_id == "flash_loan_oracle"
        else {
            "protocol_hops": 3,
            "leverage_multiplier": 6.0,
            "use_callback_chain": True,
        },
        label=hypothesis_id,
        metadata={
            "hypothesis_id": hypothesis_id,
            "parent_ids": lineage[-1:] if lineage else [],
            "lineage": lineage or [],
            "generation_method": "sample",
            "priority_score": 0.8,
            "novelty_score": novelty_score,
        },
    )
    candidate = evaluate_attack_vector(vector, catalog_states())
    candidate.evidence_grade = evidence_grade
    candidate.axis_survival_rate = axis_survival_rate
    candidate.catalog_analogue = catalog_analogue
    return candidate


def test_init_state_creates_pending_missions(tmp_path: Path):
    state_path = tmp_path / "coordinator_state.json"
    state = init_state(_kamino_config_path(), state_path=state_path)

    assert state.campaign_id == "kamino-immunefi-2026-06"
    assert state.target_id == "kamino"
    assert len(state.pending_missions) == 3
    templates = {m.template_id for m in state.pending_missions}
    assert templates == {"flash_loan_oracle", "composability_risk", "reentrancy"}
    assert state_path.exists()


def test_state_roundtrip(tmp_path: Path):
    state_path = tmp_path / "coordinator_state.json"
    original = init_state(_kamino_config_path(), state_path=state_path)
    loaded = load_state(state_path)

    assert loaded.campaign_id == original.campaign_id
    assert loaded.target_id == original.target_id
    assert len(loaded.pending_missions) == len(original.pending_missions)


def test_prioritize_uncovered_template_first(tmp_path: Path):
    state_path = tmp_path / "coordinator_state.json"
    store_path = tmp_path / "findings_store.jsonl"
    state = init_state(_kamino_config_path(), state_path=state_path)

    covered = _sample_candidate("flash_loan_oracle", "flash-root")
    record_run(
        [covered],
        [],
        {"run_at": "2026-06-10T12:00:00+00:00", "campaign_id": state.campaign_id},
        {"path": str(store_path)},
    )
    store = load_store(store_path)
    state.coverage = build_coverage(store, state.campaign_id, state.target_id)

    ordered = prioritize_missions(state, store)
    assert ordered[0].template_id != "flash_loan_oracle"
    assert ordered[0].priority_reason in ("uncovered_surface", "refinement_candidate", "novelty_gap")


def test_debrief_parses_pipeline_result(tmp_path: Path):
    mission = Mission(
        mission_id="mission-1",
        campaign_id="kamino-immunefi-2026-06",
        target_id="kamino",
        template_id="flash_loan_oracle",
        objective="Probe oracle surface",
    )
    report_path = tmp_path / "findings.json"
    report_path.write_text(
        json.dumps(
            {
                "findings": [
                    {
                        "evidence_grade": 4,
                        "catalog_analogue": True,
                        "submission_readiness": "shoestring",
                        "hypothesis_id": "hyp-1",
                        "lineage": ["hyp-root"],
                    }
                ]
            }
        )
    )
    run_result = {
        "candidates_evaluated": 10,
        "candidates_passed": 3,
        "findings": 1,
        "fork_reproduced": 0,
        "solana_reproduced": 1,
        "report_json": str(report_path),
    }

    debrief = debrief_mission(mission, run_result, report_json_path=report_path)

    assert debrief.mission_id == "mission-1"
    assert debrief.max_evidence_grade == 4
    assert debrief.solana_reproduced == 1
    assert debrief.catalog_analogue is True
    assert debrief.submission_readiness == "shoestring"
    assert "hyp-root" in debrief.lineage_roots_touched


def test_refine_promotions_escalate_to_validator(tmp_path: Path):
    store = FindingsStore(path=tmp_path / "store.jsonl")
    store.records.append(
        StoredRecord(
            record_id="r1",
            run_at="2026-06-10T12:00:00+00:00",
            record_type="candidate",
            hypothesis_id="hyp-1",
            template_id="flash_loan_oracle",
            campaign_id="kamino-immunefi-2026-06",
            evidence_grade=3,
            deployed_viable=False,
            catalog_analogue=True,
        )
    )
    debrief = MissionDebrief(
        mission_id="m1",
        run_at="2026-06-10T12:00:00+00:00",
        candidates_evaluated=5,
        candidates_passed=2,
        findings_promoted=1,
        max_evidence_grade=3,
        fork_reproduced=0,
        solana_reproduced=1,
        catalog_analogue=True,
        submission_readiness="shoestring",
        lineage_roots_touched=["hyp-1"],
        promotion_recommendations=[],
        report_json="",
    )

    recs = refine_promotions(debrief, store, "kamino-immunefi-2026-06")
    actions = {r["action"] for r in recs}
    assert "escalate_to_validator" in actions


def test_mission_retired_after_update(tmp_path: Path):
    state_path = tmp_path / "coordinator_state.json"
    store_path = tmp_path / "findings_store.jsonl"
    state = init_state(_kamino_config_path(), state_path=state_path)
    mission = state.pending_missions[0]
    mission.status = "completed"

    store = FindingsStore(path=store_path)
    debrief = MissionDebrief(
        mission_id=mission.mission_id,
        run_at="2026-06-10T12:00:00+00:00",
        candidates_evaluated=8,
        candidates_passed=2,
        findings_promoted=1,
        max_evidence_grade=2,
        fork_reproduced=0,
        solana_reproduced=0,
        catalog_analogue=True,
        submission_readiness="draft",
        lineage_roots_touched=[],
        promotion_recommendations=[],
        report_json="",
    )

    updated = update_state(state, mission, debrief, store)

    assert len(updated.mission_history) == 1
    assert updated.mission_history[0].status == "retired"
    assert mission.mission_id not in {m.mission_id for m in updated.pending_missions}
    assert updated.coverage.missions_completed == 1


def test_plan_missions_returns_top_n(tmp_path: Path):
    state_path = tmp_path / "coordinator_state.json"
    store_path = tmp_path / "findings_store.jsonl"
    state = init_state(_kamino_config_path(), state_path=state_path)
    store = load_store(store_path)

    missions = plan_missions(state, store, top_n=2)
    assert len(missions) == 2


def test_build_coverage_from_store(tmp_path: Path):
    store_path = tmp_path / "findings_store.jsonl"
    candidate = _sample_candidate("composability_risk", "comp-1")
    record_run(
        [candidate],
        [],
        {"run_at": "2026-06-10T12:00:00+00:00", "campaign_id": "kamino-immunefi-2026-06"},
        {"path": str(store_path)},
    )
    store = load_store(store_path)
    coverage = build_coverage(store, "kamino-immunefi-2026-06", "kamino")

    assert "composability_risk" in coverage.covered_templates
    assert len(coverage.attempted_fingerprints) >= 1


def test_save_state_updates_timestamp(tmp_path: Path):
    state_path = tmp_path / "coordinator_state.json"
    state = CoordinatorState(
        campaign_id="test",
        target_id="kamino",
        config_path=str(_kamino_config_path()),
        coverage=AttackSurfaceCoverage(target_id="kamino"),
        last_updated="",
    )
    save_state(state, state_path)
    loaded = load_state(state_path)
    assert loaded.last_updated