"""Tests for Solana reproduction scoring bonus."""

from night_shift_security.core.solana_scoring import (
    apply_solana_scoring_bonus,
    reproduction_multiplier,
    solana_score_multiplier,
)
from night_shift_security.data.schemas import AttackCandidateResult, AttackVector


def _cand(
    label: str,
    score: float,
    *,
    solana_reproduced: bool = False,
    fork_reproduced: bool = False,
) -> AttackCandidateResult:
    return AttackCandidateResult(
        vector=AttackVector(
            template_id="flash_loan_oracle",
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
        solana_reproduced=solana_reproduced,
        fork_reproduced=fork_reproduced,
        catalog_exploit_id="mango-markets-2022" if solana_reproduced else "",
    )


def test_solana_score_multiplier_default():
    assert solana_score_multiplier(False, {}) == 1.0
    assert solana_score_multiplier(True, {}) == 1.10


def test_apply_solana_bonus_increases_score():
    candidates = [_cand("mango", 0.70, solana_reproduced=True)]
    result = apply_solana_scoring_bonus(candidates, {"enabled": True, "score_multiplier": 1.10})
    assert result["adjusted"] == 1
    assert candidates[0].severity_score_base == 0.70
    assert candidates[0].severity_score == 0.77


def test_no_multiplier_stacking_with_fork():
    candidates = [_cand("both", 0.70, solana_reproduced=True, fork_reproduced=True)]
    candidates[0].severity_score_base = 0.70
    candidates[0].severity_score = 0.84  # fork 1.20 already applied

    apply_solana_scoring_bonus(
        candidates,
        {"score_multiplier": 1.10},
        {"score_multiplier": 1.20},
    )
    assert candidates[0].severity_score == 0.84


def test_solana_overrides_when_stronger_than_fork():
    candidates = [_cand("both", 0.70, solana_reproduced=True, fork_reproduced=True)]
    apply_solana_scoring_bonus(
        candidates,
        {"score_multiplier": 1.30},
        {"score_multiplier": 1.20},
    )
    assert candidates[0].severity_score == min(0.70 * 1.30, 1.0)


def test_reproduction_multiplier_picks_max():
    cand = _cand("x", 0.5, solana_reproduced=True, fork_reproduced=True)
    mult = reproduction_multiplier(cand, {"score_multiplier": 1.10}, {"score_multiplier": 1.20})
    assert mult == 1.20