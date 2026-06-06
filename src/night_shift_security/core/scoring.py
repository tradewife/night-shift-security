"""Severity scoring — inverted survivor_score from RTP.

Higher score = more dangerous / higher-confidence finding.
"""

from night_shift_security.data.schemas import AttackResult, Severity


_SEVERITY_WEIGHT = {
    Severity.LOW: 0.25,
    Severity.MEDIUM: 0.50,
    Severity.HIGH: 0.75,
    Severity.CRITICAL: 1.0,
}


def severity_weight(severity: Severity) -> float:
    return _SEVERITY_WEIGHT[severity]


def compute_severity_score(
    success_rate: float,
    mean_severity_weight: float,
    reproducibility: float,
    generality: float,
    realism_score: float,
    invariant_violation_count: int,
) -> float:
    """
    Composite danger score for an attack candidate.

    Mirrors RTP survivor_score structure:
      score = success × severity × reproducibility × generality × realism × invariant_factor
    """
    invariant_factor = min(invariant_violation_count / 2.0, 1.0) if invariant_violation_count else 0.0
    if invariant_factor == 0:
        return 0.0

    return (
        success_rate
        * mean_severity_weight
        * reproducibility
        * generality
        * realism_score
        * invariant_factor
    )


def aggregate_attack_results(results: list[AttackResult]) -> dict:
    """Aggregate a list of AttackResults into scoring inputs."""
    if not results:
        return {
            "success_rate": 0.0,
            "mean_severity_weight": 0.0,
            "mean_economic_impact_usd": 0.0,
            "reproducibility": 0.0,
            "invariant_violation_count": 0,
        }

    successes = [r for r in results if r.success]
    success_rate = len(successes) / len(results)
    mean_severity = sum(severity_weight(r.severity) for r in successes) / max(len(successes), 1) if successes else 0.0
    mean_impact = sum(r.economic_impact_usd for r in successes) / max(len(successes), 1)

    return {
        "success_rate": success_rate,
        "mean_severity_weight": mean_severity,
        "mean_economic_impact_usd": mean_impact if successes else 0.0,
        # MVP: reproducible if attack succeeds on at least one target state
        "reproducibility": 1.0 if successes else 0.0,
        "invariant_violation_count": sum(len(r.invariant_violations) for r in successes),
    }