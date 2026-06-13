"""Tests for synthetic KLend harness rejection at submission gate."""

from night_shift_security.bounty.scoring import compute_bounty_score
from night_shift_security.data.schemas import Finding, InvariantViolation, ReproductionStep, Severity
from night_shift_security.orchestration import bounty_loop as bl
from night_shift_security.orchestration.novel_gate import _human_gate_status
from night_shift_security.validation.task_verifier import (
    finding_balance_verified,
    is_credible_klend_harness_evidence,
)


def _klend_finding(**overrides) -> Finding:
    base = Finding(
        finding_id="NSS-0099",
        template_id="flash_loan_oracle",
        target_id="kamino",
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
        reproduction_tier="solana_validator",
        solana_reproduced=True,
        deployed_viable=True,
        catalog_analogue=False,
        solana_evidence={
            "method": "solana_klend_harness",
            "harness_mode": "fixture",
            "balance_verified": True,
            "balance_delta_lamports": 33_333_333_333,
        },
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


def test_fixture_klend_harness_not_credible():
    ev = {"method": "solana_klend_harness", "harness_mode": "fixture", "balance_verified": True}
    assert is_credible_klend_harness_evidence(ev) is False


def test_live_deploy_klend_harness_not_credible():
    ev = {"method": "solana_klend_harness", "harness_mode": "live_deploy_verified"}
    assert is_credible_klend_harness_evidence(ev) is False


def test_live_executed_klend_harness_is_credible():
    ev = {
        "method": "solana_klend_harness",
        "harness_mode": "live_executed",
        "probe_executed": True,
        "balance_verified": True,
    }
    assert is_credible_klend_harness_evidence(ev) is True


def test_fixture_klend_blocked_from_submit_ready():
    finding = _klend_finding()
    score = compute_bounty_score(finding)
    assert score.submission_recommendation == "submit_now"
    assert finding_balance_verified(finding) is False
    assert bl.qualifies_for_submission(finding, score) is False
    assert _human_gate_status(finding, score, balance_ok=False) == "hold_synthetic_harness"