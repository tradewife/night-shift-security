"""Export track classification — avoids circular imports with immunefi_submission."""

from __future__ import annotations

from typing import Literal

from night_shift_security.bounty.scoring import compute_bounty_score, resolve_program_for_finding
from night_shift_security.data.schemas import Finding
from night_shift_security.validation.submission_gates import qualifies_for_submission

ExportTrack = Literal["research_surface", "submittable", "hold"]


def _reproduction_tier(finding: Finding) -> str:
    if finding.reproduction_tier and finding.reproduction_tier != "simulation":
        return finding.reproduction_tier
    if finding.fork_reproduced:
        return "fork_reproduced"
    method = (finding.solana_evidence or {}).get("method", "")
    if method:
        return str(method)
    if finding.solana_reproduced:
        return "solana_reproduced"
    return "simulation"


def resolve_export_track(finding: Finding) -> ExportTrack:
    """Classify finding for research_surface vs submittable export paths."""
    program = resolve_program_for_finding(finding)
    score = compute_bounty_score(finding, program)
    if qualifies_for_submission(finding, score):
        return "submittable"
    fork_ev = finding.fork_evidence or {}
    if fork_ev.get("triage_surface_verified"):
        return "research_surface"
    if finding.catalog_analogue:
        return "research_surface"
    tier = _reproduction_tier(finding)
    grade = finding.evidence_grade or 0
    if grade >= 3 and tier in (
        "fork_reproduced",
        "solana_validator",
        "solana_fixture",
        "solana_reproduced",
    ):
        return "research_surface"
    return "hold"