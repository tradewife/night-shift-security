"""Tests for early structural filters."""

from night_shift_security.data.schemas import AttackVector
from night_shift_security.domain.attack_hypotheses.structural_filters import (
    apply_structural_filters,
    should_bypass_priority_floor,
    vector_fingerprint,
)


def _gov_vector(priority: float = 0.5, **metadata) -> AttackVector:
    return AttackVector(
        template_id="governance_capture",
        parameters={
            "voting_power_pct": 51.0,
            "use_flash_loan": False,
            "bypass_timelock": True,
        },
        label="gov_filter_test",
        metadata={"priority_score": priority, **metadata},
    )


def test_dedupe_removes_duplicate_fingerprints():
    vectors = [_gov_vector(), _gov_vector()]
    kept, stats = apply_structural_filters(vectors, {"dedupe": True})
    assert len(kept) == 1
    assert stats.reasons.get("duplicate") == 1


def test_low_priority_vectors_are_dropped():
    vectors = [_gov_vector(priority=0.01)]
    kept, stats = apply_structural_filters(
        vectors,
        {"min_priority_score": 0.05, "feasibility_checks": False},
    )
    assert kept == []
    assert stats.reasons.get("low_priority") == 1


def test_catalog_seed_bypasses_priority_floor():
    vector = AttackVector(
        template_id="governance_capture",
        parameters={"voting_power_pct": 10.0, "use_flash_loan": False, "bypass_timelock": False},
        label="catalog_seed_euler-finance-2023",
        metadata={"priority_score": 0.01, "generation_method": "catalog_seed"},
    )
    assert should_bypass_priority_floor(vector)
    kept, _ = apply_structural_filters(
        [vector],
        {"min_priority_score": 0.99, "feasibility_checks": False},
    )
    assert len(kept) == 1


def test_infeasible_vectors_are_dropped():
    vector = AttackVector(
        template_id="flash_loan_oracle",
        parameters={
            "loan_amount_usd": 1_000.0,
            "price_manipulation_pct": 10.0,
            "use_single_oracle": True,
        },
        label="flash_infeasible",
        metadata={"priority_score": 0.9},
    )
    kept, stats = apply_structural_filters([vector], {"min_priority_score": 0.0})
    assert kept == []
    assert stats.reasons.get("infeasible") == 1


def test_vectors_sorted_by_priority_descending():
    low = _gov_vector(priority=0.2, hypothesis_id="low")
    high = AttackVector(
        template_id="treasury_drain",
        parameters={
            "withdrawal_pct": 90.0,
            "use_compromised_admin": True,
            "bypass_multisig": True,
        },
        label="treasury_high",
        metadata={"priority_score": 0.9, "hypothesis_id": "high"},
    )
    kept, _ = apply_structural_filters(
        [low, high],
        {"min_priority_score": 0.05, "dedupe": False},
    )
    assert kept[0].label == "treasury_high"


def test_vector_fingerprint_normalizes_floats():
    a = AttackVector(
        template_id="reentrancy",
        parameters={"recursion_depth": 5, "target_function": "withdraw"},
        label="a",
    )
    b = AttackVector(
        template_id="reentrancy",
        parameters={"recursion_depth": 5.00001, "target_function": "withdraw"},
        label="b",
    )
    assert vector_fingerprint(a) == vector_fingerprint(b)