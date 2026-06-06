"""Tests for fork reproduction scoring bonus."""

from night_shift_security.core.fork_scoring import (
    apply_fork_scoring_bonus,
    fork_score_multiplier,
)
from night_shift_security.data.schemas import AttackCandidateResult, AttackVector


def _cand(label: str, score: float, *, fork_reproduced: bool = False) -> AttackCandidateResult:
    return AttackCandidateResult(
        vector=AttackVector(
            template_id="reentrancy",
            parameters={"seed": label},
            label=label,
        ),
        success_rate=1.0,
        mean_severity_score=0.8,
        mean_economic_impact_usd=1_000_000,
        reproducibility=0.9,
        generality=0.5,
        realism_score=0.7,
        invariant_violation_count=1,
        severity_score=score,
        fork_reproduced=fork_reproduced,
        catalog_exploit_id="euler-finance-2023" if fork_reproduced else "",
    )


def test_fork_score_multiplier_default():
    assert fork_score_multiplier(False, {}) == 1.0
    assert fork_score_multiplier(True, {}) == 1.20
    assert fork_score_multiplier(True, {"score_multiplier": 1.15}) == 1.15


def test_apply_bonus_increases_reproduced_scores():
    candidates = [
        _cand("low", 0.50),
        _cand("euler", 0.70, fork_reproduced=True),
    ]
    result = apply_fork_scoring_bonus(candidates, {"enabled": True, "score_multiplier": 1.20})

    assert result["adjusted"] == 1
    assert candidates[0].severity_score == 0.50
    assert candidates[1].severity_score_base == 0.70
    assert candidates[1].severity_score == 0.84


def test_apply_bonus_capped_at_one():
    candidates = [_cand("euler", 0.90, fork_reproduced=True)]
    apply_fork_scoring_bonus(candidates, {"score_multiplier": 1.20})
    assert candidates[0].severity_score == 1.0


def test_rank_change_detected():
    candidates = [
        _cand("grid_a", 0.80),
        _cand("euler", 0.72, fork_reproduced=True),
        _cand("grid_b", 0.75),
    ]
    result = apply_fork_scoring_bonus(candidates, {"score_multiplier": 1.20})

    assert len(result["rank_changes"]) == 1
    change = result["rank_changes"][0]
    assert change["label"] == "euler"
    assert change["rank_before"] > change["rank_after"]


def test_disabled_config_no_op():
    candidates = [_cand("euler", 0.70, fork_reproduced=True)]
    result = apply_fork_scoring_bonus(candidates, {"enabled": False})
    assert result["adjusted"] == 0
    assert candidates[0].severity_score == 0.70
    assert candidates[0].severity_score_base == 0.0