"""Multi-axis validation scores — architecture v2."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from night_shift_security.data.schemas import AttackCandidateResult

# Reference ceiling for normalizing economic impact to 0–1.
_DEFAULT_IMPACT_CEILING_USD = 100_000_000.0


@dataclass
class MultiAxisScores:
    """Four-axis validation profile for a candidate (all values 0.0–1.0)."""

    likelihood: float
    impact: float
    stealth: float
    generality: float

    def survival_rate(self) -> float:
        """Geometric mean across axes — multi-axis survival rate."""
        values = [
            max(0.0, min(1.0, self.likelihood)),
            max(0.0, min(1.0, self.impact)),
            max(0.0, min(1.0, self.stealth)),
            max(0.0, min(1.0, self.generality)),
        ]
        product = 1.0
        for value in values:
            product *= value
        return product**0.25

    def to_dict(self) -> dict[str, float]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MultiAxisScores:
        return cls(
            likelihood=float(data.get("likelihood", 0.0)),
            impact=float(data.get("impact", 0.0)),
            stealth=float(data.get("stealth", 0.0)),
            generality=float(data.get("generality", 0.0)),
        )


def _normalize_impact(
    economic_impact_usd: float,
    mc_impact_p50_usd: float,
    ceiling_usd: float,
) -> float:
    raw = max(economic_impact_usd, mc_impact_p50_usd)
    if ceiling_usd <= 0:
        return 0.0
    return max(0.0, min(1.0, raw / ceiling_usd))


def compute_multi_axis_scores(
    candidate: AttackCandidateResult,
    *,
    impact_ceiling_usd: float = _DEFAULT_IMPACT_CEILING_USD,
) -> MultiAxisScores:
    """
    Compute four-axis scores from candidate evaluation state.

    Axes (architecture v2):
    - Likelihood: MC reproducibility when available, else success rate.
    - Impact: normalized economic damage.
    - Stealth / Realism: template realism score.
    - Generality: breadth of successful protocol targets.
    """
    likelihood = (
        candidate.mc_reproducibility
        if candidate.mc_simulations > 0
        else candidate.success_rate
    )
    impact = _normalize_impact(
        candidate.mean_economic_impact_usd,
        candidate.mc_impact_p50_usd,
        impact_ceiling_usd,
    )
    return MultiAxisScores(
        likelihood=max(0.0, min(1.0, likelihood)),
        impact=impact,
        stealth=max(0.0, min(1.0, candidate.realism_score)),
        generality=max(0.0, min(1.0, candidate.generality)),
    )