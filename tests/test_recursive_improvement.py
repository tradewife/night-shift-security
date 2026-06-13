"""Tests for deterministic recursive self-improvement."""

from __future__ import annotations

import json
from pathlib import Path

from night_shift_security.knowledge.findings_store import FindingsStore, StoredRecord
from night_shift_security.orchestration.recursive_improvement import (
    ImprovementAction,
    analyze_loop_state,
    apply_improvement_actions,
    compute_improvement_actions,
    refinement_seeds_from_store,
    run_fingerprint,
    run_improvement_cycle,
    template_plateaued,
)


def _record(
    *,
    hypothesis_id: str = "h1",
    template_id: str = "flash_loan_oracle",
    target_id: str = "pendle",
    campaign_id: str = "loop-pendle-2026-06",
    evidence_grade: int = 2,
    axis_survival_rate: float = 0.55,
    catalog_analogue: bool = False,
    lineage: list[str] | None = None,
) -> StoredRecord:
    return StoredRecord(
        record_id="r1",
        run_at="2026-06-13T00:00:00+00:00",
        record_type="candidate",
        hypothesis_id=hypothesis_id,
        lineage=lineage or [hypothesis_id],
        template_id=template_id,
        target_id=target_id,
        campaign_id=campaign_id,
        evidence_grade=evidence_grade,
        axis_survival_rate=axis_survival_rate,
        catalog_analogue=catalog_analogue,
    )


def _store(*records: StoredRecord) -> FindingsStore:
    store = FindingsStore(path=Path("/tmp/test-store.jsonl"))
    store.records = list(records)
    for r in records:
        store._index_record(r)
    return store


def test_refinement_seeds_grade_band():
    store = _store(_record(hypothesis_id="seed-a", evidence_grade=2))
    seeds = refinement_seeds_from_store(store, target_id="pendle")
    assert "flash_loan_oracle" in seeds
    assert "seed-a" in seeds["flash_loan_oracle"]


def test_template_plateaued_catalogue_only():
    records = [
        _record(evidence_grade=4, catalog_analogue=True),
        _record(hypothesis_id="h2", evidence_grade=4, catalog_analogue=True),
    ]
    assert template_plateaued(records, "flash_loan_oracle") is True
    assert template_plateaued(records, "reentrancy") is False


def test_run_fingerprint_stable():
    evaluation = {
        "scored": [
            {"finding_id": "NSS-0001", "submission_recommendation": "hold", "catalog_analogue": True, "bounty_readiness": 0.2},
            {"finding_id": "NSS-0002", "submission_recommendation": "shoestring_only", "catalog_analogue": True, "bounty_readiness": 0.1},
        ]
    }
    assert run_fingerprint(evaluation) == run_fingerprint(evaluation)


def test_repeat_fingerprint_extends_cooldown():
    state = {
        "run_fingerprints": {"aave": []},
        "cooldown_overrides": {"aave": 12.0},
    }
    # Force repeat by matching fingerprint
    fp = run_fingerprint(
        {
            "scored": [
                {
                    "finding_id": "NSS-0001",
                    "submission_recommendation": "hold",
                    "catalog_analogue": True,
                    "reproduction_tier": "fork_reproduced",
                    "bounty_readiness": 0.5,
                }
            ]
        }
    )
    state["run_fingerprints"] = {"aave": [fp]}
    evaluation2 = {
        "scored": [
            {
                "finding_id": "NSS-0001",
                "submission_recommendation": "hold",
                "catalog_analogue": True,
                "reproduction_tier": "fork_reproduced",
                "bounty_readiness": 0.5,
            }
        ]
    }
    actions2 = compute_improvement_actions(
        state,
        slug="aave",
        evaluation=evaluation2,
        store=_store(),
        run_record={"fork_reproduced": 5},
    )
    assert any(a.action_type == "extend_cooldown" for a in actions2)
    summary = apply_improvement_actions(state, actions2, evaluation=evaluation2, slug="aave")
    assert state["cooldown_overrides"]["aave"] > 12.0
    assert summary["action_count"] >= 1


def test_queue_refinement_writes_hints(tmp_path: Path):
    store = _store(_record(hypothesis_id="seed-x", evidence_grade=2))
    state = {"refinement_queue": [], "run_fingerprints": {}}
    evaluation = {"scored": [{"finding_id": "NSS-0001", "submission_recommendation": "hold", "catalog_analogue": True, "bounty_readiness": 0.1}]}
    hints_path = tmp_path / "hints.json"
    ledger_path = tmp_path / "ledger.jsonl"
    out = run_improvement_cycle(
        state,
        slug="pendle",
        evaluation=evaluation,
        store=store,
        run_record={"fork_reproduced": 0},
        ledger_path=ledger_path,
        hints_path=hints_path,
    )
    assert out["refinement_hints"] == str(hints_path)
    assert hints_path.is_file()
    assert ledger_path.is_file()
    assert state["refinement_queue"]


def test_analyze_loop_state_from_last_run():
    state = {
        "runs": [
            {"slug": "pendle", "best_recommendation": "hold", "fork_reproduced": 0, "at": "2026-06-13T00:00:00+00:00"}
        ],
        "refinement_queue": [],
    }
    store = _store(_record(target_id="pendle", evidence_grade=2))
    report = analyze_loop_state(state, store)
    assert report["status"] == "analyzed"
    assert report["slug"] == "pendle"