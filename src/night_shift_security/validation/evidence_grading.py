"""Evidence grading (Levels 0–4) — architecture v2."""

from __future__ import annotations

from typing import Any

from night_shift_security.data.schemas import AttackCandidateResult

EVIDENCE_GRADE_LABELS = {
    0: "none",
    1: "monte_carlo_survivor",
    2: "cpcv_survivor",
    3: "reproduced",
    4: "root_cause_artifacts",
}

EVIDENCE_GRADE_MULTIPLIERS = {
    0: 0.0,
    1: 1.0,
    2: 1.05,
    3: 1.15,
    4: 1.25,
}


def evidence_grade_label(grade: int) -> str:
    return EVIDENCE_GRADE_LABELS.get(grade, "unknown")


def _passed_monte_carlo(candidate: AttackCandidateResult, min_mc: float) -> bool:
    if candidate.mc_simulations <= 0:
        return True
    return candidate.mc_reproducibility >= min_mc


def _passed_cpcv(candidate: AttackCandidateResult, max_pbo: float) -> bool:
    if not candidate.cpcv_verdict:
        return False
    if candidate.pbo > max_pbo:
        return False
    return candidate.cpcv_verdict in {"SAFE", "ELEVATED"}


def _has_reproduction(candidate: AttackCandidateResult) -> bool:
    return candidate.fork_reproduced or candidate.solana_reproduced


def _has_root_cause_artifacts(candidate: AttackCandidateResult) -> bool:
    if candidate.invariant_violation_count <= 0:
        return False
    has_steps = any(
        r.success and r.reproduction_steps for r in candidate.results
    )
    if not has_steps:
        return False
    has_impact = (
        candidate.mean_economic_impact_usd > 0
        or bool(candidate.fork_evidence)
        or bool(candidate.solana_evidence)
    )
    return has_impact


def compute_evidence_grade(
    candidate: AttackCandidateResult,
    config: dict[str, Any] | None = None,
) -> int:
    """
    Assign cumulative evidence grade (0–4).

    Level 1: Survives structural gates + Monte Carlo (when run).
    Level 2: Survives CPCV/PBO overfitting detection.
    Level 3: Achieves reproduction (fork_reproduced / solana_reproduced).
    Level 4: Clear root cause + reproducible impact artifacts.
    """
    cfg = config or {}
    min_mc = float(cfg.get("level_1_mc_min", 0.70))
    max_pbo = float(cfg.get("max_pbo", 0.30))

    if candidate.rejected:
        return 0
    if not _passed_monte_carlo(candidate, min_mc):
        return 0

    grade = 1

    if _passed_cpcv(candidate, max_pbo):
        grade = 2

    if grade >= 2 and _has_reproduction(candidate):
        grade = 3

    if grade >= 3 and _has_root_cause_artifacts(candidate):
        grade = 4

    return grade


def apply_evidence_grade_scoring(
    candidate: AttackCandidateResult,
    *,
    axis_survival_rate: float,
) -> None:
    """
    Adjust severity_score using evidence grade and multi-axis survival.

    Preserves severity_score_base for audit; stacks with fork/solana bonuses.
    """
    if candidate.severity_score_base == 0.0:
        candidate.severity_score_base = candidate.severity_score

    base = candidate.severity_score_base
    grade_mult = EVIDENCE_GRADE_MULTIPLIERS.get(candidate.evidence_grade, 1.0)
    survival_blend = 0.85 + 0.15 * max(0.0, min(1.0, axis_survival_rate))
    candidate.severity_score = min(base * survival_blend * grade_mult, 1.0)