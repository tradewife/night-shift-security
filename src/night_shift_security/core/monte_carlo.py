"""Monte Carlo attack stress testing — ported from RTP robustness.py pattern.

Perturbs attack parameters (amounts, timing, thresholds) across N simulation
paths to measure reproducibility under realistic execution variance.
"""

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from night_shift_security.data.schemas import AttackResult, AttackVector, ContractState
from night_shift_security.domain.attack_templates.base import get_template


@dataclass
class MonteCarloResult:
    """Result of Monte Carlo attack stress test."""

    n_simulations: int
    n_successes: int
    success_rate: float
    impact_p50_usd: float
    impact_p95_usd: float
    impact_worst_usd: float
    impact_observed_usd: float
    prob_success_below_half: float
    perturbed_params_samples: list[dict[str, Any]] = field(default_factory=list)


def perturb_parameters(
    params: dict[str, Any],
    perturb_range: tuple[float, float] = (0.05, 0.20),
    rng: np.random.Generator | None = None,
) -> dict[str, Any]:
    """Apply random perturbation to numeric attack parameters."""
    rng = rng or np.random.default_rng()
    perturbed = dict(params)

    numeric_keys = [k for k, v in perturbed.items() if isinstance(v, (int, float)) and not isinstance(v, bool)]
    if not numeric_keys:
        return perturbed

    n_perturb = rng.integers(1, min(4, len(numeric_keys) + 1))
    keys = rng.choice(numeric_keys, size=n_perturb, replace=False)

    for key in keys:
        original = perturbed[key]
        delta = rng.uniform(*perturb_range) * rng.choice([-1, 1])
        if isinstance(original, int):
            perturbed[key] = max(1, int(original * (1 + delta)))
        else:
            floor = 100_000.0 if key == "loan_amount_usd" else 0.01
            perturbed[key] = max(floor, round(original * (1 + delta), 4))

    return perturbed


def _impact_from_results(results: list[AttackResult]) -> float:
    successes = [r for r in results if r.success]
    if not successes:
        return 0.0
    return max(r.economic_impact_usd for r in successes)


def monte_carlo_attack_stress(
    vector: AttackVector,
    states: list[ContractState],
    n_simulations: int = 100,
    perturb_range: tuple[float, float] = (0.05, 0.20),
    seed: int = 42,
) -> MonteCarloResult:
    """
    Run Monte Carlo perturbations on an attack vector.

    For each simulation path:
    1. Perturb numeric parameters
    2. Execute attack against all target states
    3. Record whether attack still succeeds and economic impact
    """
    template = get_template(vector.template_id)
    rng = np.random.default_rng(seed)

    observed = template.execute(states[0], vector.parameters) if states else None
    observed_impact = observed.economic_impact_usd if observed and observed.success else 0.0

    path_successes = 0
    impacts: list[float] = []
    samples: list[dict[str, Any]] = []

    for _ in range(n_simulations):
        perturbed = perturb_parameters(vector.parameters, perturb_range, rng)
        path_results: list[AttackResult] = []
        for state in states:
            result = template.execute(state, perturbed)
            path_results.append(result)

        if any(r.success for r in path_results):
            path_successes += 1
            impacts.append(_impact_from_results(path_results))

        if len(samples) < 5:
            samples.append(perturbed)

    impacts_arr = np.array(impacts) if impacts else np.array([0.0])
    success_rate = path_successes / n_simulations if n_simulations else 0.0

    return MonteCarloResult(
        n_simulations=n_simulations,
        n_successes=path_successes,
        success_rate=success_rate,
        impact_p50_usd=round(float(np.percentile(impacts_arr, 50)), 2),
        impact_p95_usd=round(float(np.percentile(impacts_arr, 95)), 2) if len(impacts) else 0.0,
        impact_worst_usd=round(float(np.max(impacts_arr)), 2),
        impact_observed_usd=round(observed_impact, 2),
        prob_success_below_half=round(float(success_rate < 0.5), 4),
        perturbed_params_samples=samples,
    )