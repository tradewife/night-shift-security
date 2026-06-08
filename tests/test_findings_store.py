"""Tests for the lightweight findings store."""

import json
from pathlib import Path

from night_shift_security.core.evaluation import evaluate_attack_vector
from night_shift_security.core.results import findings_from_candidates
from night_shift_security.data.exploit_catalog import catalog_states
from night_shift_security.data.schemas import AttackVector, Finding, Severity
from night_shift_security.knowledge.findings_store import (
    ancestors,
    best_evidence_per_lineage_root,
    descendants,
    lineage_survival_stats,
    load_store,
    record_run,
)


def _sample_candidate(label: str, hypothesis_id: str, lineage: list[str]):
    vector = AttackVector(
        template_id="governance_capture",
        parameters={
            "voting_power_pct": 67.0,
            "use_flash_loan": True,
            "bypass_timelock": True,
        },
        label=label,
        metadata={
            "hypothesis_id": hypothesis_id,
            "parent_ids": lineage[-1:] if lineage else [],
            "lineage": lineage,
            "generation_method": "sample",
            "priority_score": 0.8,
            "novelty_score": 0.6,
        },
    )
    return evaluate_attack_vector(vector, catalog_states())


def test_record_run_appends_lineage_records(tmp_path: Path):
    store_path = tmp_path / "findings_store.jsonl"
    root_id = "root-hypothesis"
    child_id = "child-hypothesis"
    root = _sample_candidate("root", root_id, [])
    child = _sample_candidate("child", child_id, [root_id])

    passed = [c for c in (root, child) if not c.rejected]
    findings = findings_from_candidates(passed)
    stats = record_run(
        [root, child],
        findings,
        {"run_at": "2026-06-08T12:00:00+00:00"},
        {"path": str(store_path)},
    )

    assert stats.added == 2
    assert store_path.exists()
    lines = store_path.read_text().strip().splitlines()
    assert len(lines) == 2

    payload = json.loads(lines[0])
    assert payload["hypothesis_id"] == root_id
    assert payload["lineage"] == []


def test_lineage_analytics(tmp_path: Path):
    store_path = tmp_path / "findings_store.jsonl"
    root_id = "root-a"
    child_id = "child-a"
    record_run(
        [_sample_candidate("root", root_id, []), _sample_candidate("child", child_id, [root_id])],
        [],
        {"run_at": "2026-06-08T12:00:00+00:00"},
        {"path": str(store_path)},
    )
    store = load_store(store_path)

    assert ancestors(store, child_id) == [root_id]
    assert child_id in descendants(store, root_id)
    stats = lineage_survival_stats(store)
    assert stats["total_records"] == 2
    assert "sample" in stats["by_generation_method"]
    assert root_id in best_evidence_per_lineage_root(store)


def test_promoted_findings_marked_in_store(tmp_path: Path):
    store_path = tmp_path / "findings_store.jsonl"
    candidate = _sample_candidate("promoted", "promoted-id", [])
    if candidate.rejected:
        return

    findings = findings_from_candidates([candidate])
    record_run(
        [candidate],
        findings,
        {"run_at": "2026-06-08T12:00:00+00:00"},
        {"path": str(store_path)},
    )
    store = load_store(store_path)
    assert any(record.promoted for record in store.records)
    promoted = [record for record in store.records if record.promoted][0]
    assert promoted.finding_id.startswith("NSS-")