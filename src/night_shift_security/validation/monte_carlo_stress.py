"""Stage 5: Monte Carlo stress testing on top attack candidates."""

from night_shift_security.core.monte_carlo import MonteCarloResult, monte_carlo_attack_stress
from night_shift_security.data.schemas import AttackCandidateResult, ContractState


def run_monte_carlo_phase(
    candidates: list[AttackCandidateResult],
    states: list[ContractState],
    config: dict,
) -> dict[str, MonteCarloResult]:
    """
    Run Monte Carlo stress on top non-rejected candidates.

    Updates candidates in-place with mc_* fields and may reject fragile findings.
    """
    top_n = config.get("top_n", 10)
    n_simulations = config.get("n_simulations", 100)
    perturb_range = tuple(config.get("perturbation_range", [0.05, 0.20]))
    min_mc_reproducibility = config.get("min_reproducibility", 0.70)

    passing = [c for c in candidates if not c.rejected]
    top = sorted(passing, key=lambda c: c.severity_score, reverse=True)[:top_n]

    results: dict[str, MonteCarloResult] = {}

    for cand in top:
        target_states = _relevant_states(cand, states)
        mc = monte_carlo_attack_stress(
            cand.vector,
            target_states,
            n_simulations=n_simulations,
            perturb_range=perturb_range,
        )
        results[str(cand.vector.key())] = mc

        cand.mc_reproducibility = mc.success_rate
        cand.mc_impact_p50_usd = mc.impact_p50_usd
        cand.mc_impact_p95_usd = mc.impact_p95_usd
        cand.mc_simulations = mc.n_simulations

        if mc.success_rate < min_mc_reproducibility:
            cand.rejected = True
            cand.rejection_reason = (
                f"mc_reproducibility={mc.success_rate:.0%} < {min_mc_reproducibility:.0%}"
            )

    return results


def _relevant_states(
    cand: AttackCandidateResult,
    states: list[ContractState],
) -> list[ContractState]:
    """Limit MC stress to states where the candidate originally succeeded."""
    if not cand.results:
        return states
    success_ids = {
        state.protocol_id
        for result, state in zip(cand.results, states)
        if result.success
    }
    if success_ids:
        filtered = [s for s in states if s.protocol_id in success_ids]
        if filtered:
            return filtered
    return states[:1]