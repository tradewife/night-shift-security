"""Tests for early structural filters."""

import json
from pathlib import Path

from night_shift_security.data.schemas import AttackVector
from night_shift_security.domain.attack_hypotheses.structural_filters import (
    apply_structural_filters,
    auditvault_axes_for_target,
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


def _write_auditvault_index(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def test_auditvault_axes_index_lookup(tmp_path: Path):
    path = tmp_path / "auditvault_patterns.jsonl"
    _write_auditvault_index(
        path,
        [
            {"protocol_slug": "wormhole", "atlas_axes": ["bridge", "oracle"]},
            {"protocol_slug": "uniswap", "atlas_axes": ["amm"]},
        ],
    )

    from night_shift_security.domain.attack_hypotheses.structural_filters import (
        _load_auditvault_axes_by_slug,
    )

    index = _load_auditvault_axes_by_slug(path)
    assert auditvault_axes_for_target("wormhole", index) == ["bridge", "oracle"]
    assert auditvault_axes_for_target("Wormhole", index) == ["bridge", "oracle"]
    assert auditvault_axes_for_target("uniswap", index) == ["amm"]
    assert auditvault_axes_for_target("nonexistent", index) == []


def test_auditvault_axis_penalty_bumps_priority(tmp_path: Path):
    path = tmp_path / "auditvault_patterns.jsonl"
    _write_auditvault_index(
        path,
        [{"protocol_slug": "wormhole", "atlas_axes": ["bridge"]}],
    )
    vector = AttackVector(
        template_id="access_control_escalation",
        parameters={"target_role": "guardian"},
        target_id="wormhole",
        label="worms-aces",
        metadata={"priority_score": 0.5},
    )
    kept, stats = apply_structural_filters(
        [vector],
        {
            "feasibility_checks": False,
            "auditvault_axes": {
                "enabled": True,
                "required_min_count": 1,
                "priority_bump_per_ref": 0.10,
                "path": str(path),
            },
        },
    )
    assert len(kept) == 1
    assert kept[0].metadata["auditvault_priority_bump"] == pytest_approx(0.10)


def test_auditvault_axis_gap_is_visible_as_filter_stat(tmp_path: Path):
    path = tmp_path / "auditvault_patterns.jsonl"
    _write_auditvault_index(path, [])
    vector = AttackVector(
        template_id="access_control_escalation",
        parameters={"target_role": "guardian"},
        target_id="uniswap",
        label="worms-aces",
        metadata={"priority_score": 0.5},
    )
    kept, stats = apply_structural_filters(
        [vector],
        {
            "feasibility_checks": False,
            "min_priority_score": 0.0,
            "auditvault_axes": {
                "enabled": True,
                "required_min_count": 1,
                "path": str(path),
            },
        },
    )
    assert len(kept) == 1  # penalty does not drop
    assert stats.reasons.get("auditvault_axis_gap_kept_with_penalty") == 1
    assert kept[0].metadata["auditvault_atlas_axis_gap"] == 1


# local import-only alias to keep tests light
def pytest_approx(*args, **kwargs):
    import pytest as _pytest

    return _pytest.approx(*args, **kwargs)