"""Validation Layer — multi-axis scores, evidence grading, scoring refresh."""

from __future__ import annotations

from typing import Any

from night_shift_security.data.schemas import AttackCandidateResult
from night_shift_security.validation.evidence_grading import (
    apply_evidence_grade_scoring,
    compute_evidence_grade,
    evidence_grade_label,
)
from night_shift_security.validation.multi_axis import compute_multi_axis_scores


def update_validation_metadata(
    candidate: AttackCandidateResult,
    config: dict[str, Any] | None = None,
) -> AttackCandidateResult:
    """Recompute axis scores and evidence grade without adjusting severity."""
    cfg = config or {}
    axis = compute_multi_axis_scores(
        candidate,
        impact_ceiling_usd=float(cfg.get("impact_ceiling_usd", 100_000_000.0)),
    )
    candidate.axis_scores = axis.to_dict()
    candidate.axis_survival_rate = axis.survival_rate()
    candidate.evidence_grade = compute_evidence_grade(candidate, cfg)
    candidate.evidence_grade_label = evidence_grade_label(candidate.evidence_grade)
    _stamp_vector_metadata(candidate)
    return candidate


def refresh_validation_layer(
    candidate: AttackCandidateResult,
    config: dict[str, Any] | None = None,
    *,
    apply_scoring: bool = True,
) -> AttackCandidateResult:
    """
    Recompute multi-axis scores, evidence grade, and optionally severity score.

    Safe to call after each validation phase (eval, MC, CPCV, reproduction).
    Use apply_scoring=False after fork/solana bonuses to refresh grades only.
    """
    update_validation_metadata(candidate, config)
    if apply_scoring:
        apply_evidence_grade_scoring(
            candidate,
            axis_survival_rate=candidate.axis_survival_rate,
        )
    return candidate


def refresh_validation_batch(
    candidates: list[AttackCandidateResult],
    config: dict[str, Any] | None = None,
    *,
    apply_scoring: bool = True,
) -> list[AttackCandidateResult]:
    for candidate in candidates:
        refresh_validation_layer(candidate, config, apply_scoring=apply_scoring)
    return candidates


def _stamp_vector_metadata(candidate: AttackCandidateResult) -> None:
    """Propagate validation layer fields onto vector metadata for hypothesis round-trip."""
    meta = dict(candidate.vector.metadata or {})
    meta["axis_scores"] = dict(candidate.axis_scores)
    meta["axis_survival_rate"] = candidate.axis_survival_rate
    meta["evidence_grade"] = candidate.evidence_grade
    meta["evidence_grade_label"] = candidate.evidence_grade_label
    candidate.vector.metadata = meta