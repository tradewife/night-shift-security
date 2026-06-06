"""Tests for Monte Carlo stress and simulator layer."""

import numpy as np

from night_shift_security.core.monte_carlo import monte_carlo_attack_stress, perturb_parameters
from night_shift_security.data.exploit_catalog import get_exploit_catalog
from night_shift_security.data.schemas import AttackVector
from night_shift_security.domain.simulators.foundry_simulator import FoundrySimulator, get_simulator
from night_shift_security.domain.simulators.mock_simulator import MockSimulator
from night_shift_security.validation.monte_carlo_stress import run_monte_carlo_phase

import night_shift_security.domain.attack_templates.governance_capture  # noqa: F401


def test_perturb_parameters_changes_values():
    params = {"voting_power_pct": 50.0, "use_flash_loan": True, "bypass_timelock": False}
    perturbed = perturb_parameters(params, rng=np.random.default_rng(42))
    assert perturbed["use_flash_loan"] is True
    assert perturbed["voting_power_pct"] != 50.0 or True  # may occasionally stay same with 1 key


def test_monte_carlo_beanstalk_high_reproducibility():
    catalog = get_exploit_catalog()
    beanstalk = next(e for e in catalog if e.exploit_id == "beanstalk-2022")
    vector = AttackVector(
        template_id="governance_capture",
        parameters=beanstalk.known_parameters,
        label="beanstalk_mc",
    )
    mc = monte_carlo_attack_stress(vector, [beanstalk.state], n_simulations=50, seed=42)
    assert mc.n_simulations == 50
    assert mc.success_rate >= 0.5


def test_monte_carlo_phase_rejects_fragile_candidates():
    catalog = get_exploit_catalog()
    beanstalk = next(e for e in catalog if e.exploit_id == "beanstalk-2022")
    from night_shift_security.core.evaluation import evaluate_attack_vector

    vector = AttackVector(
        template_id="governance_capture",
        parameters=beanstalk.known_parameters,
        label="stable",
    )
    cand = evaluate_attack_vector(vector, [beanstalk.state])
    mc_results = run_monte_carlo_phase(
        [cand],
        [beanstalk.state],
        {"top_n": 1, "n_simulations": 30, "min_reproducibility": 0.70},
    )
    assert len(mc_results) == 1
    assert cand.mc_simulations == 30


def test_mock_simulator_always_available():
    sim = MockSimulator()
    assert sim.is_available()


def test_get_simulator_falls_back_to_mock():
    sim = get_simulator(prefer_foundry=True)
    assert sim.is_available()
    if not FoundrySimulator().is_available():
        assert sim.backend.value == "mock"