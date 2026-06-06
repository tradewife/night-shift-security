"""Security gate thresholds — mirrors RTP promotion_criteria.py pattern."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SecurityGate:
    """Thresholds an attack finding must clear before reporting."""

    MIN_REPRODUCIBILITY: float = 0.80
    MIN_SEVERITY_SCORE: float = 0.50
    MIN_ECONOMIC_IMPACT_USD: float = 100_000.0
    MIN_INVARIANT_VIOLATIONS: int = 1
    MIN_REALISM_SCORE: float = 0.40
    MIN_GENERALITY: float = 0.30
    MAX_CAPITAL_REQUIRED_USD: float = 50_000_000.0


@dataclass
class GateResult:
    passed: bool
    value: Any
    threshold: Any
    name: str


def check_security_gates(
    success_rate: float,
    severity_score: float,
    economic_impact_usd: float,
    invariant_violation_count: int,
    realism_score: float,
    generality: float,
    capital_required_usd: float,
    gates: SecurityGate | None = None,
) -> tuple[bool, str, list[GateResult]]:
    """Evaluate a candidate against all security gates. Returns (passed, reason, details)."""
    g = gates or SecurityGate()
    results = [
        GateResult(
            "reproducibility",
            success_rate >= g.MIN_REPRODUCIBILITY,
            success_rate,
            g.MIN_REPRODUCIBILITY,
        ),
        GateResult(
            "severity_score",
            severity_score >= g.MIN_SEVERITY_SCORE,
            severity_score,
            g.MIN_SEVERITY_SCORE,
        ),
        GateResult(
            "economic_impact",
            economic_impact_usd >= g.MIN_ECONOMIC_IMPACT_USD,
            economic_impact_usd,
            g.MIN_ECONOMIC_IMPACT_USD,
        ),
        GateResult(
            "invariant_violations",
            invariant_violation_count >= g.MIN_INVARIANT_VIOLATIONS,
            invariant_violation_count,
            g.MIN_INVARIANT_VIOLATIONS,
        ),
        GateResult(
            "realism",
            realism_score >= g.MIN_REALISM_SCORE,
            realism_score,
            g.MIN_REALISM_SCORE,
        ),
        GateResult(
            "generality",
            generality >= g.MIN_GENERALITY,
            generality,
            g.MIN_GENERALITY,
        ),
        GateResult(
            "capital_feasibility",
            capital_required_usd <= g.MAX_CAPITAL_REQUIRED_USD,
            capital_required_usd,
            g.MAX_CAPITAL_REQUIRED_USD,
        ),
    ]

    failed = [r for r in results if not r.passed]
    if failed:
        reasons = ", ".join(f"{r.name}={r.value} (need {r.threshold})" for r in failed)
        return False, reasons, results

    return True, "", results