"""Tests for Validation Layer — multi-axis scores and evidence grading."""

import pytest

from night_shift_security.core.evaluation import evaluate_attack_vector
from night_shift_security.core.hypothesis import generate_llm_expanded_attack_vectors, generate_sampled_attack_vectors
from night_shift_security.data.exploit_catalog import get_exploit_catalog
from night_shift_security.data.schemas import (
    AttackCandidateResult,
    AttackResult,
    AttackVector,
    InvariantViolation,
    ReproductionStep,
    Severity,
)
from night_shift_security.domain.attack_hypotheses import (
    MockLLMProvider,
    attack_vector_to_hypothesis,
    hypothesis_to_attack_vector,
)
from night_shift_security.validation.evidence_grading import (
    EVIDENCE_GRADE_MULTIPLIERS,
    apply_evidence_grade_scoring,
    compute_evidence_grade,
)
from night_shift_security.validation.multi_axis import MultiAxisScores, compute_multi_axis_scores
from night_shift_security.validation.validation_layer import refresh_validation_layer


def _passing_candidate(**overrides) -> AttackCandidateResult:
    base = AttackCandidateResult(
        vector=AttackVector(template_id="governance_capture", parameters={"voting_power_pct": 35}),
        success_rate=0.9,
        mean_severity_score=0.75,
        mean_economic_impact_usd=5_000_000.0,
        reproducibility=1.0,
        generality=0.5,
        realism_score=0.7,
        invariant_violation_count=2,
        severity_score=0.65,
        results=[
            AttackResult(
                vector=AttackVector(template_id="governance_capture", parameters={}),
                success=True,
                severity=Severity.HIGH,
                economic_impact_usd=5_000_000.0,
                invariant_violations=[
                    InvariantViolation("gov_quorum", "quorum", "40%", "20%"),
                ],
                reproduction_steps=[
                    ReproductionStep("flash_loan_vote", "attacker"),
                ],
            )
        ],
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


def test_multi_axis_scores_geometric_mean():
    scores = MultiAxisScores(likelihood=0.8, impact=0.5, stealth=0.6, generality=0.4)
    survival = scores.survival_rate()
    assert 0.0 < survival < 1.0
    assert survival == pytest.approx((0.8 * 0.5 * 0.6 * 0.4) ** 0.25)


def test_compute_multi_axis_uses_mc_likelihood_when_available():
    cand = _passing_candidate(mc_simulations=100, mc_reproducibility=0.82, success_rate=0.5)
    axis = compute_multi_axis_scores(cand)
    assert axis.likelihood == pytest.approx(0.82)
    assert axis.stealth == pytest.approx(0.7)
    assert axis.generality == pytest.approx(0.5)


def test_evidence_grade_level_1_for_gate_pass():
    cand = _passing_candidate()
    assert compute_evidence_grade(cand) == 1


def test_evidence_grade_level_2_after_cpcv():
    cand = _passing_candidate(cpcv_verdict="SAFE", pbo=0.12)
    assert compute_evidence_grade(cand) == 2


def test_evidence_grade_level_3_requires_reproduction():
    cand = _passing_candidate(
        cpcv_verdict="SAFE",
        pbo=0.12,
        fork_reproduced=True,
        fork_evidence={"target_id": "euler-finance-2023"},
        results=[
            AttackResult(
                vector=AttackVector(template_id="governance_capture", parameters={}),
                success=True,
                severity=Severity.HIGH,
                economic_impact_usd=5_000_000.0,
                invariant_violations=[],
                reproduction_steps=[],
            )
        ],
        invariant_violation_count=0,
    )
    assert compute_evidence_grade(cand) == 3


def test_evidence_grade_level_4_requires_artifacts():
    cand = _passing_candidate(
        cpcv_verdict="SAFE",
        pbo=0.10,
        fork_reproduced=True,
        fork_evidence={"impact_usd": 1_000_000},
    )
    assert compute_evidence_grade(cand) == 4


def test_evidence_grade_zero_when_rejected():
    cand = _passing_candidate(rejected=True)
    assert compute_evidence_grade(cand) == 0


def test_evidence_grade_scoring_increases_with_grade():
    low = _passing_candidate(evidence_grade=1, axis_survival_rate=0.5)
    high = _passing_candidate(evidence_grade=4, axis_survival_rate=0.5)
    apply_evidence_grade_scoring(low, axis_survival_rate=0.5)
    apply_evidence_grade_scoring(high, axis_survival_rate=0.5)
    assert high.severity_score > low.severity_score
    assert EVIDENCE_GRADE_MULTIPLIERS[4] > EVIDENCE_GRADE_MULTIPLIERS[1]


def test_refresh_validation_layer_stamps_vector_metadata():
    cand = _passing_candidate()
    refresh_validation_layer(cand)
    assert cand.axis_scores
    assert cand.evidence_grade == 1
    assert cand.vector.metadata["evidence_grade"] == 1
    assert "likelihood" in cand.vector.metadata["axis_scores"]


def test_evaluation_populates_validation_fields():
    catalog = get_exploit_catalog()
    states = [e.state for e in catalog if e.template_id == "governance_capture"]
    vectors = generate_sampled_attack_vectors("governance_capture", n=1)
    result = evaluate_attack_vector(vectors[0], states)
    assert result.axis_scores
    assert result.evidence_grade >= 0
    assert result.axis_survival_rate >= 0.0


def test_hypothesis_round_trip_carries_validation_metadata():
    cand = _passing_candidate()
    refresh_validation_layer(cand)
    vector = cand.vector
    hypothesis = attack_vector_to_hypothesis(vector)
    assert hypothesis.metadata.get("evidence_grade") == cand.evidence_grade
    restored = hypothesis_to_attack_vector(hypothesis)
    assert restored.metadata.get("axis_scores") == cand.axis_scores


def test_llm_vectors_receive_validation_on_evaluation():
    catalog = get_exploit_catalog()
    states = [e.state for e in catalog if e.template_id == "governance_capture"]
    seeds = generate_sampled_attack_vectors("governance_capture", n=1)
    json_variants = """[
      {"quorum_threshold": 0.12, "participation_rate": 0.45,
       "whale_concentration": 0.55, "proposal_timing_window_blocks": 1200,
       "flash_loan_boost": 0.15}
    ]"""
    provider = MockLLMProvider(responses=[json_variants])
    expanded = generate_llm_expanded_attack_vectors(
        "governance_capture",
        seeds,
        variants_per_seed=1,
        enabled=True,
        provider=provider,
    )
    assert expanded
    result = evaluate_attack_vector(expanded[0], states)
    assert result.vector.metadata.get("trusted") is False
    assert result.axis_scores