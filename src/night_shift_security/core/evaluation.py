"""Attack vector evaluation — mirrors RTP evaluate_candidate() pattern."""

from night_shift_security.core.gates import SecurityGate, check_security_gates
from night_shift_security.core.scoring import aggregate_attack_results, compute_severity_score, severity_weight
from night_shift_security.data.schemas import AttackCandidateResult, AttackResult, AttackVector, ContractState
from night_shift_security.domain.attack_templates.base import AttackTemplate, get_template
from night_shift_security.validation.validation_layer import refresh_validation_layer


def evaluate_attack_vector(
    vector: AttackVector,
    states: list[ContractState],
    gate: SecurityGate | None = None,
) -> AttackCandidateResult:
    """Execute one attack vector against multiple contract states and aggregate."""
    template = get_template(vector.template_id)
    results: list[AttackResult] = []

    for state in states:
        result = template.execute(state, vector.parameters)
        result.vector = vector
        results.append(result)

    agg = aggregate_attack_results(results)
    successes = [r for r in results if r.success]

    success_protocols = {state.protocol_id for r, state in zip(results, states) if r.success}
    generality = len(success_protocols) / max(len(states), 1)
    realism_scores = [template.realism_score(vector.parameters, state) for state in states]
    realism_score = sum(realism_scores) / len(realism_scores) if realism_scores else 0.0

    capital_required = max((r.capital_required_usd for r in successes), default=0.0)

    severity_score = compute_severity_score(
        success_rate=agg["success_rate"],
        mean_severity_weight=agg["mean_severity_weight"],
        reproducibility=agg["reproducibility"],
        generality=generality,
        realism_score=realism_score,
        invariant_violation_count=agg["invariant_violation_count"],
    )

    passed, rejection_reason, _ = check_security_gates(
        success_rate=agg["success_rate"],
        severity_score=severity_score,
        economic_impact_usd=agg["mean_economic_impact_usd"],
        invariant_violation_count=agg["invariant_violation_count"],
        realism_score=realism_score,
        generality=generality,
        capital_required_usd=capital_required,
        gates=gate,
    )

    candidate = AttackCandidateResult(
        vector=vector,
        success_rate=agg["success_rate"],
        mean_severity_score=agg["mean_severity_weight"],
        mean_economic_impact_usd=agg["mean_economic_impact_usd"],
        reproducibility=agg["reproducibility"],
        generality=generality,
        realism_score=realism_score,
        invariant_violation_count=agg["invariant_violation_count"],
        severity_score=severity_score,
        rejected=not passed,
        rejection_reason=rejection_reason,
        results=results,
    )
    return refresh_validation_layer(candidate)


def rank_candidates(candidates: list[AttackCandidateResult]) -> list[AttackCandidateResult]:
    """Rank by severity_score descending; rejected candidates sink."""
    return sorted(
        candidates,
        key=lambda c: (not c.rejected, c.severity_score),
        reverse=True,
    )