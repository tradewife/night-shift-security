"""Foundry validation phase — confirm top findings in Solidity harness."""

from night_shift_security.data.schemas import AttackCandidateResult, ContractState
from night_shift_security.domain.simulators.foundry_simulator import FoundrySimulator, get_simulator


def run_foundry_phase(
    candidates: list[AttackCandidateResult],
    states: list[ContractState],
    config: dict,
) -> dict[str, bool]:
    """
    Re-validate top candidates via Foundry when available.

    Sets foundry_confirmed on candidates that pass forge tests.
    """
    if not config.get("enabled", True):
        return {}

    top_n = config.get("top_n", 5)
    fork_url = config.get("fork_url") or None
    simulator = get_simulator(prefer_foundry=True, fork_url=fork_url)

    passing = [c for c in candidates if not c.rejected]
    top = sorted(passing, key=lambda c: c.severity_score, reverse=True)[:top_n]

    confirmations: dict[str, bool] = {}

    for cand in top:
        state = _best_state_for_candidate(cand, states)
        result = simulator.execute(cand.vector, state)
        confirmed = result.success and "foundry" in (result.notes or "").lower()
        if isinstance(simulator, FoundrySimulator) and simulator.is_available():
            confirmed = result.success and result.notes == "foundry_confirmed"

        cand.foundry_confirmed = confirmed
        cand.simulator_backend = simulator.backend.value
        confirmations[str(cand.vector.key())] = confirmed

    return confirmations


def _best_state_for_candidate(
    cand: AttackCandidateResult,
    states: list[ContractState],
) -> ContractState:
    """Pick the state where this candidate had the highest impact."""
    if not cand.results:
        return states[0]
    best = max(cand.results, key=lambda r: r.economic_impact_usd)
    for state in states:
        if state.protocol_id == best.vector.target_id or state.protocol_id in str(best.vector.target_id):
            return state
    for state in states:
        for r in cand.results:
            if r.success and r.economic_impact_usd > 0:
                return state
    return states[0]