"""Bounty readiness scoring — economic prioritization on top of evidence gates."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from night_shift_security.data.bounty_program import BountyProgram
from night_shift_security.data.cantina_registry import CANTINA_PROGRAMS
from night_shift_security.data.immunefi_registry import IMMUNEFI_PROGRAMS, immunefi_to_bounty
from night_shift_security.data.schemas import Finding, Severity
from night_shift_security.validation.evidence_grading import (
    EVIDENCE_GRADE_MULTIPLIERS,
    effective_evidence_grade,
)

DEFAULT_HISTORICAL_PAYOUT_RATE = 0.15
DEPOSIT_REQUIRED_PENALTY = 0.90
CATALOG_ANALOGUE_PENALTY = 0.70
DEPLOYED_VIABLE_BONUS = 1.15

REPRODUCTION_MULTIPLIERS: dict[str, float] = {
    "solana_validator": 1.0,
    "fork_reproduced": 1.0,
    "solana_fixture": 0.65,
    "solana_reproduced": 0.65,
    "simulation": 0.25,
}

_ALL_PROGRAMS: list[BountyProgram] | None = None


@dataclass(frozen=True)
class BountyScoreResult:
    bounty_readiness: float
    expected_payout_proxy_usd: float
    confidence_band: str
    submission_recommendation: str
    score_components: dict[str, float] = field(default_factory=dict)
    platform: str = ""
    program_slug: str = ""
    max_bounty_usd: int = 0


def _all_programs() -> list[BountyProgram]:
    global _ALL_PROGRAMS
    if _ALL_PROGRAMS is None:
        _ALL_PROGRAMS = [
            *[immunefi_to_bounty(p) for p in IMMUNEFI_PROGRAMS],
            *CANTINA_PROGRAMS,
        ]
    return _ALL_PROGRAMS


def _reproduction_tier(finding: Finding) -> str:
    if finding.reproduction_tier and finding.reproduction_tier != "simulation":
        return finding.reproduction_tier
    method = finding.solana_evidence.get("method", "")
    if method:
        return str(method)
    if finding.fork_reproduced:
        return "fork_reproduced"
    if finding.solana_reproduced:
        return "solana_reproduced"
    return "simulation"


def _is_validator_tier(tier: str) -> bool:
    return tier in ("solana_validator", "fork_reproduced")


def resolve_program_for_finding(finding: Finding) -> BountyProgram | None:
    """Map finding target / catalogue anchor to a curated bounty program."""
    candidates: list[str] = []
    if finding.target_id:
        candidates.append(finding.target_id)
        candidates.append(finding.target_id.replace("_", "-"))
    exploit_id = (
        finding.rediscovered_exploit_id
        or finding.solana_evidence.get("exploit_id", "")
        or finding.fork_evidence.get("exploit_id", "")
    )
    if exploit_id:
        candidates.append(str(exploit_id))

    slug_aliases = {
        "mango_markets": "kamino",
        "mango-markets": "kamino",
        "solend": "marinade",
        "cashio": "cashio-2022",
        "euler_finance": "euler",
        "euler-finance-2023": "euler",
        "kamino": "kamino",
        "solend-whale-2022": "marinade",
    }

    for raw in candidates:
        slug = slug_aliases.get(raw, raw)
        for program in _all_programs():
            if program.slug == slug:
                return program

    analogue_matches = [
        p for p in _all_programs()
        if p.catalog_analogue and p.catalog_analogue in candidates
    ]
    if analogue_matches:
        return max(analogue_matches, key=lambda p: p.max_bounty_usd)

    for raw in candidates:
        for program in _all_programs():
            if program.catalog_analogue == raw:
                return program
    return None


def _confidence_band(readiness: float, grade: int, tier: str) -> str:
    if readiness >= 0.75 and grade >= 4 and _is_validator_tier(tier):
        return "high"
    if readiness >= 0.50 and grade >= 3:
        return "medium"
    return "low"


def _submission_recommendation(
    readiness: float,
    grade: int,
    tier: str,
    *,
    catalog_analogue: bool,
) -> str:
    if grade < 3:
        return "hold"
    if readiness >= 0.75 and grade >= 4 and _is_validator_tier(tier) and not catalog_analogue:
        return "submit_now"
    if grade >= 4 and _is_validator_tier(tier) and readiness >= 0.30:
        return "polish_validator"
    if readiness >= 0.55 and grade >= 3 and not _is_validator_tier(tier):
        return "polish_validator"
    if readiness >= 0.40 and grade >= 3 and catalog_analogue:
        return "shoestring_only"
    if readiness >= 0.55 and grade >= 3:
        return "polish_validator"
    return "hold"


def compute_bounty_score(
    finding: Finding,
    program: BountyProgram | None = None,
    *,
    historical_payout_rate: float = DEFAULT_HISTORICAL_PAYOUT_RATE,
) -> BountyScoreResult:
    """Rank a finding by expected bounty ROI. Grade < 3 is blocked."""
    program = program or resolve_program_for_finding(finding)
    tier = _reproduction_tier(finding)
    grade_track = "shoestring" if tier in ("solana_fixture", "catalog_solana") else "pipeline"
    grade = effective_evidence_grade(finding, track=grade_track)

    if grade < 3:
        return BountyScoreResult(
            bounty_readiness=0.0,
            expected_payout_proxy_usd=0.0,
            confidence_band="low",
            submission_recommendation="hold",
            score_components={"evidence_grade": float(grade), "gate_blocked": 1.0},
            platform=program.platform if program else "",
            program_slug=program.slug if program else "",
            max_bounty_usd=program.max_bounty_usd if program else 0,
        )

    axis = min(max(finding.axis_survival_rate, 0.01), 1.0)
    priority = finding.priority_score if finding.priority_score > 0 else min(max(finding.severity_score, 0.35), 1.0)
    novelty = finding.novelty_score if finding.novelty_score > 0 else 0.35
    priority = min(max(priority, 0.01), 1.0)
    novelty = min(max(novelty, 0.01), 1.0)
    grade_mult = EVIDENCE_GRADE_MULTIPLIERS.get(grade, 0.0) / 1.25

    quality_core = min(
        1.0,
        0.40 * axis + 0.20 * priority + 0.20 * novelty + 0.20 * grade_mult,
    )
    repro_mult = REPRODUCTION_MULTIPLIERS.get(tier, 0.25)

    readiness = quality_core * repro_mult
    if _is_validator_tier(tier) and grade >= 4:
        readiness *= 1.35
    if finding.deployed_viable:
        readiness *= DEPLOYED_VIABLE_BONUS
    if finding.catalog_analogue:
        readiness *= CATALOG_ANALOGUE_PENALTY
    if program and program.deposit_required:
        readiness *= DEPOSIT_REQUIRED_PENALTY

    readiness = round(min(readiness, 1.0), 4)

    max_bounty = program.max_bounty_usd if program else int(finding.economic_impact_usd)
    capped_impact = min(finding.economic_impact_usd, float(max_bounty))
    payout_proxy = round(capped_impact * historical_payout_rate * readiness, 2)

    recommendation = _submission_recommendation(
        readiness,
        grade,
        tier,
        catalog_analogue=finding.catalog_analogue,
    )

    return BountyScoreResult(
        bounty_readiness=readiness,
        expected_payout_proxy_usd=payout_proxy,
        confidence_band=_confidence_band(readiness, grade, tier),
        submission_recommendation=recommendation,
        score_components={
            "evidence_grade": float(grade),
            "axis_survival_rate": axis,
            "priority_score": priority,
            "novelty_score": novelty,
            "grade_multiplier": grade_mult,
            "quality_core": round(quality_core, 4),
            "reproduction_multiplier": repro_mult,
            "reproduction_tier": tier,
            "catalog_analogue_penalty": CATALOG_ANALOGUE_PENALTY if finding.catalog_analogue else 1.0,
            "deposit_penalty": DEPOSIT_REQUIRED_PENALTY if program and program.deposit_required else 1.0,
        },
        platform=program.platform if program else "",
        program_slug=program.slug if program else "",
        max_bounty_usd=max_bounty,
    )


def score_result_to_dict(score: BountyScoreResult) -> dict[str, Any]:
    return {
        "bounty_readiness": score.bounty_readiness,
        "expected_payout_proxy_usd": score.expected_payout_proxy_usd,
        "confidence_band": score.confidence_band,
        "submission_recommendation": score.submission_recommendation,
        "score_components": score.score_components,
        "platform": score.platform,
        "program_slug": score.program_slug,
        "max_bounty_usd": score.max_bounty_usd,
    }