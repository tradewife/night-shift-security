"""Tests for adversarial self-interrogation candidate triage."""

from night_shift_security.data.schemas import (
    AttackCandidateResult,
    AttackVector,
)
from night_shift_security.validation.self_interrogation import (
    apply_self_interrogation,
    interrogate_candidate,
)


def _candidate(**overrides) -> AttackCandidateResult:
    vector = overrides.pop(
        "vector",
        AttackVector(
            template_id="access_control_escalation",
            target_id="wormhole",
            label="self_interrogation_good",
            parameters={"target_role": "guardian"},
            metadata={
                "priority_score": 0.9,
                "novelty_score": 0.7,
                "source_commit": "abc123",
                "selector_or_discriminator": "0xdeadbeef",
            },
        ),
    )
    base = AttackCandidateResult(
        vector=vector,
        success_rate=0.9,
        mean_severity_score=0.8,
        mean_economic_impact_usd=5_000_000.0,
        reproducibility=0.9,
        generality=0.4,
        realism_score=0.75,
        invariant_violation_count=1,
        severity_score=0.7,
        rejected=False,
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


def test_interrogation_proceeds_for_target_bound_value_candidate():
    report = interrogate_candidate(_candidate())
    assert report.recommended_action == "proceed"
    assert report.conviction_score >= 0.68
    assert "has a target binding" in report.surviving_arguments


def test_interrogation_flags_missing_target_and_impact():
    weak = _candidate(
        vector=AttackVector(
            template_id="governance_capture",
            parameters={"voting_power_pct": 11.0},
            label="weak_generic",
            metadata={"priority_score": 0.1},
        ),
        mean_economic_impact_usd=1_000.0,
        invariant_violation_count=0,
        severity_score=0.1,
        realism_score=0.1,
    )
    report = interrogate_candidate(weak)
    assert report.recommended_action in {"revise", "discard"}
    assert "target binding is missing" in report.adversarial_challenges
    assert "economic impact is below configured floor" in report.adversarial_challenges


def test_apply_self_interrogation_stamps_metadata_without_filtering_by_default():
    weak = _candidate(
        vector=AttackVector(
            template_id="governance_capture",
            parameters={"voting_power_pct": 11.0},
            label="weak_advisory",
            metadata={"priority_score": 0.1},
        ),
        mean_economic_impact_usd=1_000.0,
        invariant_violation_count=0,
        severity_score=0.1,
    )
    candidates, stats = apply_self_interrogation([weak])
    assert candidates[0].rejected is False
    assert stats.analyzed == 1
    assert candidates[0].vector.metadata["self_interrogation"]["recommended_action"] in {
        "revise",
        "discard",
    }


def test_filter_mode_rejects_low_conviction_non_catalogue_candidate():
    weak = _candidate(
        vector=AttackVector(
            template_id="governance_capture",
            parameters={"voting_power_pct": 11.0},
            label="weak_filter",
            metadata={"priority_score": 0.1},
        ),
        mean_economic_impact_usd=1_000.0,
        invariant_violation_count=0,
        severity_score=0.1,
    )
    candidates, stats = apply_self_interrogation([weak], {"mode": "filter"})
    assert candidates[0].rejected is True
    assert candidates[0].rejection_reason.startswith("self_interrogation_")
    assert stats.filtered == 1


def test_rank_adjustment_changes_surviving_candidate_score():
    strong = _candidate()
    before = strong.severity_score
    candidates, stats = apply_self_interrogation(
        [strong],
        {"rank_adjustment": True, "max_rank_adjustment": 0.05},
    )
    assert stats.rank_adjusted == 1
    assert candidates[0].severity_score > before
    assert "self_interrogation_rank_adjustment" in candidates[0].vector.metadata
