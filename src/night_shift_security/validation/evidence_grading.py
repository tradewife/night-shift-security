"""Evidence grading (Levels 0–4) — architecture v2."""

from __future__ import annotations

from typing import Any

from night_shift_security.data.schemas import AttackCandidateResult, Finding
from night_shift_security.validation.task_verifier import candidate_balance_verified

# Grading tracks (see SPEC v2.0.2):
# - pipeline: strict cumulative grader (CPCV required for Level 3+)
# - shoestring / scan: credits fixture reproduction without CPCV pass
GRADING_TRACKS = frozenset({"pipeline", "shoestring", "scan"})

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

    operator_cfg = cfg.get("operator") or {}
    verifier_cfg = operator_cfg.get("task_verifier") or {}
    if (
        grade >= 3
        and verifier_cfg.get("enabled", True)
        and verifier_cfg.get("required_for_novel", True)
        and not candidate_balance_verified(candidate)
    ):
        grade = 2

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


def _shoestring_grade_from_signals(
    *,
    rejected: bool,
    solana_reproduced: bool,
    fork_reproduced: bool,
    invariant_violation_count: int,
    has_reproduction_steps: bool,
    mean_economic_impact_usd: float,
    solana_evidence: dict[str, Any] | None,
    fork_evidence: dict[str, Any] | None,
    pipeline_grade: int,
) -> int:
    """Shoestring/scan grading — fixture reproduction can reach Level 4 without CPCV."""
    if rejected:
        return 0
    has_impact = (
        mean_economic_impact_usd > 0
        or bool(solana_evidence)
        or bool(fork_evidence)
    )
    if solana_reproduced or fork_reproduced:
        if invariant_violation_count > 0 and has_reproduction_steps and has_impact:
            return 4
        return 3
    return max(pipeline_grade, 1)


def shoestring_evidence_grade_candidate(candidate: AttackCandidateResult) -> int:
    has_steps = any(r.success and r.reproduction_steps for r in candidate.results)
    return _shoestring_grade_from_signals(
        rejected=candidate.rejected,
        solana_reproduced=candidate.solana_reproduced,
        fork_reproduced=candidate.fork_reproduced,
        invariant_violation_count=candidate.invariant_violation_count,
        has_reproduction_steps=has_steps,
        mean_economic_impact_usd=candidate.mean_economic_impact_usd,
        solana_evidence=candidate.solana_evidence,
        fork_evidence=candidate.fork_evidence,
        pipeline_grade=candidate.evidence_grade,
    )


def shoestring_evidence_grade_finding(finding: Finding) -> int:
    return _shoestring_grade_from_signals(
        rejected=False,
        solana_reproduced=finding.solana_reproduced,
        fork_reproduced=finding.fork_reproduced,
        invariant_violation_count=len(finding.invariant_violations),
        has_reproduction_steps=bool(finding.reproduction_steps),
        mean_economic_impact_usd=finding.economic_impact_usd,
        solana_evidence=finding.solana_evidence,
        fork_evidence=finding.fork_evidence,
        pipeline_grade=finding.evidence_grade,
    )


def effective_evidence_grade(
    finding: Finding,
    *,
    track: str = "pipeline",
) -> int:
    """Resolve evidence grade for export/triage under the chosen grading track."""
    if track in {"shoestring", "scan"}:
        return shoestring_evidence_grade_finding(finding)
    return finding.evidence_grade