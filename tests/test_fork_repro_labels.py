"""Audit correction C7 — fork_reproduced label split in run summary (additive)."""

from __future__ import annotations

import json
from pathlib import Path

from night_shift_security.orchestration import bounty_loop as bl


def _scope_with(path: Path, entries: dict[str, dict[str, object]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "schema_version": "1.0",
        "entry_count": len(entries),
        "curated_count": 0,
        "entries": entries,
    }))
    return path


def test_record_run_labels_sum_to_legacy_counter_for_mixed_findings(tmp_path: Path):
    """The four sub-labels sum to the legacy fork_reproduced count."""
    _scope_with(
        tmp_path / "scope_registry.json",
        {
            "uniswap_v4": {"slug": "uniswap_v4", "max_bounty_usd": 15_500_000,
                            "curated": True},
            "kamino": {"slug": "kamino", "max_bounty_usd": 1_500_000,
                       "curated": True},
        },
    )
    evaluation = {
        "scored": [
            # Fork repro 1 — non-catalogue + v4 schema + measured_impact_oracle.v1
            {
                "fork_reproduced": True,
                "catalog_analogue": False,
                "fork_evidence": {"evidence_kind": "measured_impact_oracle.v1"},
                "target_id": "uniswap_v4",
                "parameters": {
                    "candidate": {"candidate_schema_version": 4},
                },
            },
            # Fork repro 2 — catalog analogue + no oracle evidence + plain fork
            {
                "fork_reproduced": True,
                "catalog_analogue": True,
                "target_id": "kamino",
            },
            # Below — must not count: fork_reproduced False
            {"fork_reproduced": False, "catalog_analogue": True,
             "target_id": "uniswap_v4"},
        ],
        "submit_candidates": [],
        "best_recommendation": "shoestring_only",
    }
    labels = bl._record_run_labels(
        evaluation, scope_registry_path=tmp_path / "scope_registry.json",
    )
    # Legacy counter = 2 (only first two entries).
    assert labels["fork_reproduced"] == 2
    # Catalog-anchor: only the second finding (catalogue analogue=True).
    assert labels["fork_reproduced_catalog_anchor"] == 1
    # Live-program: both target_ids resolve to entries in scope registry.
    assert labels["fork_reproduced_live_program"] == 2
    # Value-moving: only the first finding has measured_impact_oracle.v1.
    assert labels["fork_reproduced_value_moving"] == 1
    # Novel: only the first finding is non-catalogue AND v4 schema.
    assert labels["fork_reproduced_novel"] == 1


def test_record_run_labels_independent_of_counter_when_empty(tmp_path: Path):
    labels = bl._record_run_labels(
        {"scored": [], "best_recommendation": "hold"},
        scope_registry_path=tmp_path / "scope_registry.json",
    )
    assert labels == {
        "fork_reproduced": 0,
        "fork_reproduced_catalog_anchor": 0,
        "fork_reproduced_live_program": 0,
        "fork_reproduced_value_moving": 0,
        "fork_reproduced_novel": 0,
    }


def test_record_run_labels_value_moving_locked_to_measured_oracle(tmp_path: Path):
    """Generic fork_reproduced:true findings without the oracle evidence
    kind must NOT count as value-moving (audit D8)."""
    evaluation = {
        "scored": [
            {
                "fork_reproduced": True,
                "catalog_analogue": True,
                "fork_evidence": {"method": "evm_fork", "evidence_kind": "evm_fork"},
                "target_id": "wormhole",
            },
        ],
        "submit_candidates": [],
        "best_recommendation": "hold",
    }
    labels = bl._record_run_labels(evaluation)
    assert labels["fork_reproduced"] == 1
    assert labels["fork_reproduced_catalog_anchor"] == 1
    assert labels["fork_reproduced_value_moving"] == 0


def test_record_run_labels_novel_requires_v4_schema_and_non_catalog(tmp_path: Path):
    evaluation = {
        "scored": [
            {
                "fork_reproduced": True,
                "catalog_analogue": True,  # catalogue analogue -> not novel
                "fork_evidence": {"evidence_kind": "measured_impact_oracle.v1"},
                "target_id": "x",
                "parameters": {"candidate": {"candidate_schema_version": 4}},
            },
            {
                "fork_reproduced": True,
                "catalog_analogue": False,
                "fork_evidence": {"method": "evm_fork"},  # not value-moving
                "target_id": "x",
                "parameters": {"candidate": {"candidate_schema_version": 4}},
            },
            {
                "fork_reproduced": True,
                "catalog_analogue": False,
                "target_id": "x",
                "parameters": {"candidate": {"candidate_schema_version": 3}},  # not v4
            },
        ],
        "submit_candidates": [],
        "best_recommendation": "hold",
    }
    labels = bl._record_run_labels(evaluation)
    assert labels["fork_reproduced"] == 3
    assert labels["fork_reproduced_novel"] == 1  # only the second entry


def test_run_record_includes_label_fields(tmp_path: Path, monkeypatch):
    """``run_record`` (built inside ``run_loop_iteration``) carries the new
    label fields when at least one finding fork_reproduced."""
    state_path = tmp_path / "state.json"
    scan_path = tmp_path / "scan.json"
    scan_path.write_text(json.dumps({
        "programs": [
            {
                "slug": "pendle",
                "platform": "cantina",
                "ecosystem": "evm",
                "best_evidence_grade": 3,
                "submission_ready": False,
                "solana_reproduced": 0,
                "candidates_passed": 4,
                "max_bounty_usd": 2_000_000,
            },
        ],
    }))
    bl.save_loop_state(bl._default_state(), state_path)
    findings_path = tmp_path / "findings.json"
    findings_path.write_text("{}")

    def fake_pipeline(**kwargs):
        return {
            "findings": 1,
            "fork_reproduced": 1,
            "solana_reproduced": 0,
            "report_json": str(findings_path),
        }

    monkeypatch.setattr(bl, "run_security_pipeline", fake_pipeline)

    # Force the synthetic evaluation to include findings so labels flow into the run record.
    def fake_evaluate(_path):
        return {
            "scored": [
                {
                    "fork_reproduced": True,
                    "catalog_analogue": True,
                    "submission_recommendation": "shoestring_only",
                    "target_id": "pendle",
                    "fork_evidence": {"evidence_kind": "measured_impact_oracle.v1"},
                    "parameters": {"candidate": {"candidate_schema_version": 4}},
                },
            ],
            "submit_candidates": [],
            "best_recommendation": "shoestring_only",
        }

    monkeypatch.setattr(bl, "evaluate_findings_json", fake_evaluate)

    # ``run_loop_iteration`` defaults to the production manifest which
    # does not contain ``pendle``. Pin the target directly via the
    # ``pinned_target`` kwarg to bypass the picker for this integration
    # test of the run-record label plumbing.
    pinned = {"slug": "pendle", "platform": "cantina"}
    result = bl.run_loop_iteration(
        state_path=state_path,
        scan_path=scan_path,
        refresh_scan=False,
        pinned_target=pinned,
    )
    assert result["status"] in {"submit_ready", "continue"}, result
    last_run = json.loads(state_path.read_text())["runs"][-1]
    assert "fork_reproduced_catalog_anchor" in last_run
    assert "fork_reproduced_live_program" in last_run
    assert "fork_reproduced_value_moving" in last_run
    assert "fork_reproduced_novel" in last_run
    # Legacy field must remain compatible with existing dashboards.
    assert "fork_reproduced" in last_run
    # At least one of the new labels is non-zero because the synthetic
    # entry carries measured_impact_oracle.v1 evidence.
    assert last_run["fork_reproduced_value_moving"] >= 1
