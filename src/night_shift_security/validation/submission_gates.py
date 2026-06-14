"""Submission qualification gates — shared by loop, scan, and export."""

from __future__ import annotations

from night_shift_security.validation.task_verifier import (
    finding_balance_verified,
    finding_has_credible_reproduction,
)


def qualifies_for_submission(finding, score) -> bool:
    """Engine + scoring gate for autonomous loop stop (human still posts externally)."""
    tier = finding.reproduction_tier or (
        "fork_reproduced" if finding.fork_reproduced else "simulation"
    )
    grade = finding.evidence_grade or 0
    return (
        score.submission_recommendation == "submit_now"
        and grade >= 4
        and tier in ("fork_reproduced", "solana_validator")
        and not finding.catalog_analogue
        and finding.deployed_viable
        and finding_has_credible_reproduction(finding)
        and finding_balance_verified(finding)
    )