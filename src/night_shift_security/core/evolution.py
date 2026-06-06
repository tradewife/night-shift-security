"""Darwinian evolution of attack strategies — ported from RTP night_shift.py."""

import random
from typing import Any

from night_shift_security.core.evaluation import evaluate_attack_vector
from night_shift_security.core.gates import SecurityGate
from night_shift_security.data.schemas import AttackCandidateResult, AttackVector, ContractState

DARWINIAN_DEFAULTS = {
    "generations": 3,
    "population": 10,
    "perturbation_range": (0.05, 0.15),
    "offspring_per_parent": 3,
}


def _perturb_params(params: dict[str, Any], perturb_range: tuple[float, float]) -> dict[str, Any]:
    """Mutate one numeric parameter by a random delta."""
    mutated = dict(params)
    numeric_keys = [k for k, v in mutated.items() if isinstance(v, (int, float))]
    if not numeric_keys:
        return mutated

    key = random.choice(numeric_keys)
    delta = random.uniform(*perturb_range) * random.choice([-1, 1])
    original = mutated[key]

    if isinstance(original, int):
        mutated[key] = max(1, int(original * (1 + delta)))
    else:
        floor = 0.01 if key != "loan_amount_usd" else 100_000.0
        mutated[key] = max(floor, round(original * (1 + delta), 4))

    return mutated


def _crossover(parent_a: dict[str, Any], parent_b: dict[str, Any]) -> dict[str, Any]:
    """Single-point crossover between two parameter sets."""
    keys = list(parent_a.keys())
    if len(keys) < 2:
        return dict(parent_a)
    split = random.randint(1, len(keys) - 1)
    child = {}
    for i, key in enumerate(keys):
        child[key] = parent_a[key] if i < split else parent_b.get(key, parent_a[key])
    return child


def darwinian_evolution(
    population: list[AttackCandidateResult],
    states: list[ContractState],
    gates: SecurityGate | None = None,
    config: dict | None = None,
) -> list[AttackCandidateResult]:
    """
    Stage 3: evolve attack parameter sets via mutation and crossover.

    Selection pressure = severity_score (higher = more dangerous).
    """
    cfg = {**DARWINIAN_DEFAULTS, **(config or {})}
    generations = cfg["generations"]
    pop_size = cfg["population"]
    perturb_range = cfg["perturbation_range"]
    offspring_per_parent = cfg["offspring_per_parent"]

    current_gen = sorted(
        [c for c in population if not c.rejected],
        key=lambda c: c.severity_score,
        reverse=True,
    )[:pop_size]

    if not current_gen:
        return []

    all_survivors = list(current_gen)

    for gen in range(generations):
        offspring: list[AttackCandidateResult] = []

        for parent in current_gen:
            for _ in range(offspring_per_parent):
                if random.random() < 0.3 and len(current_gen) > 1:
                    other = random.choice(current_gen)
                    params = _crossover(parent.vector.parameters, other.vector.parameters)
                    label = f"{parent.vector.template_id}_cross_g{gen}"
                else:
                    params = _perturb_params(parent.vector.parameters, perturb_range)
                    label = f"{parent.vector.template_id}_mut_g{gen}"

                vector = AttackVector(
                    template_id=parent.vector.template_id,
                    parameters=params,
                    target_id=parent.vector.target_id,
                    label=label,
                )
                offspring.append(evaluate_attack_vector(vector, states, gate=gates))

        combined = current_gen + offspring
        combined.sort(key=lambda c: c.severity_score, reverse=True)
        current_gen = combined[:pop_size]
        all_survivors.extend(current_gen)

    seen: set[tuple] = set()
    unique: list[AttackCandidateResult] = []
    for cand in sorted(all_survivors, key=lambda c: c.severity_score, reverse=True):
        key = cand.vector.key()
        if key not in seen:
            seen.add(key)
            unique.append(cand)

    return unique[: pop_size * 2]