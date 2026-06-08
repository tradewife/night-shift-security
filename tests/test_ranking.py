"""Tests for hypothesis ranking signals."""

from night_shift_security.data.schemas import AttackVector
from night_shift_security.domain.attack_hypotheses.ranking import (
    attach_ranking_signals,
    compute_priority_score,
    ranking_signals_for_vector,
)


def test_ranking_signals_are_bounded():
    vector = AttackVector(
        template_id="governance_capture",
        parameters={
            "voting_power_pct": 51.0,
            "use_flash_loan": True,
            "bypass_timelock": True,
        },
        label="gov_test",
    )
    signals = ranking_signals_for_vector(vector)
    for key in (
        "impact_proxy",
        "novelty_score",
        "testability_score",
        "evidence_potential",
        "priority_score",
    ):
        assert 0.0 <= signals[key] <= 1.0


def test_priority_score_blend():
    score = compute_priority_score(impact=1.0, novelty=0.0, testability=0.0)
    assert score == 0.4


def test_attach_ranking_signals_is_idempotent():
    vector = AttackVector(
        template_id="treasury_drain",
        parameters={
            "withdrawal_pct": 75.0,
            "use_compromised_admin": True,
            "bypass_multisig": False,
        },
        label="treasury_test",
    )
    first = attach_ranking_signals(vector)
    second = attach_ranking_signals(first)
    assert first.metadata["priority_score"] == second.metadata["priority_score"]


def test_grid_vectors_receive_ranking_metadata():
    from night_shift_security.core.hypothesis import generate_attack_vectors
    from night_shift_security.domain.attack_templates.reentrancy import ReentrancyTemplate

    vectors = generate_attack_vectors(ReentrancyTemplate())
    assert vectors
    assert "priority_score" in vectors[0].metadata
    assert "novelty_score" in vectors[0].metadata