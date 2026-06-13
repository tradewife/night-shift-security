"""Tests for autonomous bounty hunt loop."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from night_shift_security.bounty.scoring import compute_bounty_score
from night_shift_security.data.program_registry import get_program_by_slug
from night_shift_security.data.schemas import Finding, InvariantViolation, ReproductionStep, Severity
from night_shift_security.orchestration import bounty_loop as bl


def _finding(**overrides) -> Finding:
    base = Finding(
        finding_id="NSS-0001",
        template_id="flash_loan_oracle",
        target_id="pendle",
        severity=Severity.CRITICAL,
        severity_score=0.55,
        economic_impact_usd=15_000_000.0,
        capital_required_usd=500_000.0,
        reproducibility=1.0,
        parameters={"loan_amount_usd": 50_000_000},
        invariant_violations=[
            InvariantViolation("oracle_price_integrity", "Oracle integrity", "~$0.10", "$0.20")
        ],
        reproduction_steps=[ReproductionStep("flash_loan", "attacker", {"amount_usd": 50_000_000})],
        evidence_grade=4,
        evidence_grade_label="root_cause_artifacts",
        axis_survival_rate=0.62,
        priority_score=0.7,
        novelty_score=0.5,
        reproduction_tier="fork_reproduced",
        fork_reproduced=True,
        deployed_viable=True,
        catalog_analogue=False,
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


_SAMPLE_SCAN = {
    "programs": [
        {
            "slug": "pendle",
            "platform": "cantina",
            "name": "Pendle",
            "ecosystem": "evm",
            "max_bounty_usd": 2_000_000,
            "best_evidence_grade": 3,
            "submission_ready": False,
            "solana_reproduced": 0,
            "candidates_passed": 4,
        },
        {
            "slug": "raydium",
            "platform": "immunefi",
            "name": "Raydium",
            "ecosystem": "solana",
            "max_bounty_usd": 505_000,
            "best_evidence_grade": 4,
            "submission_ready": True,
            "solana_reproduced": 2,
            "candidates_passed": 5,
        },
        {
            "slug": "kamino",
            "platform": "immunefi",
            "name": "Kamino",
            "ecosystem": "solana",
            "max_bounty_usd": 1_500_000,
            "best_evidence_grade": 4,
            "submission_ready": True,
            "solana_reproduced": 2,
            "candidates_passed": 5,
        },
    ]
}


def test_get_program_by_slug_cross_platform():
    euler = get_program_by_slug("euler", platform="cantina")
    assert euler is not None
    assert euler.platform == "cantina"
    kamino = get_program_by_slug("kamino")
    assert kamino is not None
    assert kamino.platform == "immunefi"


def test_load_save_loop_state(tmp_path: Path):
    path = tmp_path / "state.json"
    state = bl.load_loop_state(path)
    assert state["version"] == 1
    assert "kamino" in state["saturated_slugs"]
    state["iteration_count"] = 5
    bl.save_loop_state(state, path)
    reloaded = bl.load_loop_state(path)
    assert reloaded["iteration_count"] == 5


def test_pick_next_target_excludes_saturated(tmp_path: Path):
    state = bl._default_state()
    target = bl.pick_next_target(_SAMPLE_SCAN, state)
    assert target is not None
    assert target["slug"] not in state["saturated_slugs"]


def test_pick_next_target_respects_cooldown():
    recent = datetime.now(timezone.utc) - timedelta(hours=1)
    state = {
        "saturated_slugs": ["kamino"],
        "runs": [{"slug": "pendle", "at": recent.isoformat()}],
    }
    target = bl.pick_next_target(_SAMPLE_SCAN, state, cooldown_hours=12.0)
    assert target is not None
    assert target["slug"] == "raydium"


def test_qualifies_for_submission_novel_validator():
    finding = _finding()
    score = compute_bounty_score(finding)
    assert score.submission_recommendation == "submit_now"
    assert bl.qualifies_for_submission(finding, score) is True


def test_qualifies_for_submission_blocks_unverified_evm_fork():
    finding = _finding(
        fork_evidence={"method": "evm_fork", "balance_verified": False, "balance_delta_wei": 0},
    )
    score = compute_bounty_score(finding)
    assert bl.qualifies_for_submission(finding, score) is False


def test_qualifies_for_submission_blocks_catalogue():
    finding = _finding(
        catalog_analogue=True,
        reproduction_tier="fork_reproduced",
        rediscovered_exploit_id="nomad-bridge-2022",
    )
    score = compute_bounty_score(finding)
    assert bl.qualifies_for_submission(finding, score) is False


def test_maybe_mark_saturated_catalogue_only():
    state = {"saturated_slugs": ["kamino"]}
    evaluation = {
        "scored": [
            {
                "catalog_analogue": True,
                "submission_recommendation": "shoestring_only",
            }
        ],
        "submit_candidates": [],
        "best_recommendation": "shoestring_only",
    }
    bl._maybe_mark_saturated(state, "raydium", evaluation)
    assert "raydium" in state["saturated_slugs"]


def test_run_loop_iteration_submit_ready(tmp_path: Path, monkeypatch):
    state_path = tmp_path / "state.json"
    scan_path = tmp_path / "scan.json"
    scan_path.write_text(json.dumps(_SAMPLE_SCAN))
    alert_path = Path("data/security_results/loop/submission_alert.json")
    if alert_path.is_file():
        alert_path.unlink()

    findings_path = tmp_path / "findings.json"
    findings_path.write_text("{}")

    def fake_pipeline(**kwargs):
        return {
            "findings": 1,
            "fork_reproduced": 1,
            "solana_reproduced": 0,
            "report_json": str(findings_path),
        }

    def fake_evaluate(_path):
        return {
            "scored": [{"submission_recommendation": "submit_now", "qualifies": True}],
            "submit_candidates": [{"finding_id": "NSS-0001", "qualifies": True}],
            "best_recommendation": "submit_now",
        }

    monkeypatch.setattr(bl, "run_security_pipeline", fake_pipeline)
    monkeypatch.setattr(bl, "evaluate_findings_json", fake_evaluate)
    monkeypatch.setattr(
        bl,
        "pick_next_target",
        lambda scan, state, **kw: _SAMPLE_SCAN["programs"][0],
    )

    result = bl.run_loop_iteration(
        state_path=state_path,
        scan_path=scan_path,
        refresh_scan=False,
    )
    assert result["status"] == "submit_ready"
    assert alert_path.is_file()
    alert_path.unlink()
    saved = json.loads(state_path.read_text())
    assert saved["human_gate_pending"] is True


def test_build_loop_config_kamino_sets_klend_require_live():
    program = get_program_by_slug("kamino")
    assert program is not None
    cfg = bl.build_loop_config(
        program,
        base_config_path=bl._CONFIG_DIR / "kamino_klend.json",
    )
    assert cfg["solana_validation"]["klend_require_live"] is True
    assert cfg["solana_validation"]["enabled"] is True


def test_build_loop_config_wormhole_triage_enables_live_fork():
    program = get_program_by_slug("wormhole")
    assert program is not None
    cfg = bl.build_loop_config(
        program,
        base_config_path=bl._CONFIG_DIR / "wormhole_triage.json",
    )
    assert cfg["fork_validation"]["enabled"] is True
    assert cfg["fork_validation"]["prefer_live_programs"] is True
    assert cfg["fork_validation"]["always_test_catalog_evm_anchors"] is False
    assert cfg["solana_validation"]["enabled"] is False


def test_resolve_pipeline_config_wormhole_uses_triage():
    program = get_program_by_slug("wormhole")
    assert program is not None
    path = bl.resolve_pipeline_config_path(program)
    assert path.name == "wormhole_triage.json"


def test_fixture_klend_finding_not_submit_candidate():
    finding = _finding(
        target_id="kamino-klend",
        reproduction_tier="solana_validator",
        solana_reproduced=True,
        fork_reproduced=False,
        solana_evidence={
            "method": "solana_klend_harness",
            "harness_mode": "fixture",
            "balance_verified": True,
            "balance_delta_lamports": 33_333_333_333,
        },
    )
    score = compute_bounty_score(finding)
    assert score.submission_recommendation == "submit_now"
    assert bl.qualifies_for_submission(finding, score) is False


def test_run_bounty_loop_stops_on_submit(monkeypatch, tmp_path: Path):
    calls = {"n": 0}

    def fake_iteration(**kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return {"status": "submit_ready"}
        return {"status": "continue"}

    monkeypatch.setattr(bl, "run_loop_iteration", fake_iteration)
    out = bl.run_bounty_loop(iterations=3, stop_on_submit=True, state_path=tmp_path / "s.json")
    assert out["iterations_run"] == 1
    assert out["final_status"] == "submit_ready"