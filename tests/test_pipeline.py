"""Tests for Night Shift Security pipeline."""

from night_shift_security.core.evaluation import evaluate_attack_vector
from night_shift_security.core.evolution import darwinian_evolution
from night_shift_security.core.hypothesis import generate_attack_vectors, grid_combos
from night_shift_security.data.exploit_catalog import get_exploit_catalog
from night_shift_security.data.schemas import AttackVector
from night_shift_security.domain.attack_templates.base import get_template, list_templates
from night_shift_security.domain.attack_templates.flash_loan_oracle import FlashLoanOracleTemplate
from night_shift_security.domain.attack_templates.governance_capture import GovernanceCaptureTemplate
from night_shift_security.domain.attack_templates.reentrancy import ReentrancyTemplate
from night_shift_security.domain.attack_templates.treasury_drain import TreasuryDrainTemplate
from night_shift_security.validation.historical_replay import evaluate_catalog_directly, run_rediscovery_test

# Ensure templates are registered
import night_shift_security.domain.attack_templates.governance_capture  # noqa: F401
import night_shift_security.domain.attack_templates.treasury_drain  # noqa: F401
import night_shift_security.domain.attack_templates.flash_loan_oracle  # noqa: F401
import night_shift_security.domain.attack_templates.reentrancy  # noqa: F401
import night_shift_security.domain.attack_templates.composability_risk  # noqa: F401
import night_shift_security.domain.attack_templates.upgradeability_risk  # noqa: F401
import night_shift_security.domain.attack_templates.access_control_escalation  # noqa: F401


def test_all_templates_registered():
    assert set(list_templates()) == {
        "governance_capture",
        "treasury_drain",
        "flash_loan_oracle",
        "reentrancy",
        "composability_risk",
        "upgradeability_risk",
        "access_control_escalation",
    }


def test_grid_combos_counts():
    assert len(grid_combos(GovernanceCaptureTemplate().param_grid())) == 24
    assert len(grid_combos(TreasuryDrainTemplate().param_grid())) == 16
    assert len(grid_combos(FlashLoanOracleTemplate().param_grid())) == 32
    assert len(grid_combos(ReentrancyTemplate().param_grid())) == 12


def test_ground_truth_exploits_succeed():
    catalog = get_exploit_catalog()
    results = evaluate_catalog_directly(catalog)
    successes = [r for r in results if r.results and r.results[0].success]
    assert len(successes) == len(catalog)


def test_catalog_has_all_categories():
    catalog = get_exploit_catalog()
    categories = {e.category for e in catalog}
    assert categories == {
        "governance_capture",
        "treasury_drain",
        "flash_loan_oracle",
        "reentrancy",
        "composability_risk",
        "upgradeability_risk",
        "access_control_escalation",
    }
    assert len(catalog) == 16


def test_beanstalk_rediscovery():
    catalog = get_exploit_catalog()
    beanstalk = next(e for e in catalog if e.exploit_id == "beanstalk-2022")
    vector = AttackVector(
        template_id="governance_capture",
        parameters=beanstalk.known_parameters,
        target_id=beanstalk.state.protocol_id,
    )
    result = evaluate_attack_vector(vector, [beanstalk.state])
    assert result.results[0].success
    assert result.mean_economic_impact_usd > 100_000_000


def test_mango_flash_loan_oracle():
    catalog = get_exploit_catalog()
    mango = next(e for e in catalog if e.exploit_id == "mango-markets-2022")
    vector = AttackVector(
        template_id="flash_loan_oracle",
        parameters=mango.known_parameters,
    )
    result = evaluate_attack_vector(vector, [mango.state])
    assert result.results[0].success
    assert result.results[0].economic_impact_usd > 1_000_000


def test_euler_reentrancy():
    catalog = get_exploit_catalog()
    euler = next(e for e in catalog if e.exploit_id == "euler-finance-2023")
    vector = AttackVector(
        template_id="reentrancy",
        parameters=euler.known_parameters,
    )
    result = evaluate_attack_vector(vector, [euler.state])
    assert result.results[0].success
    assert result.results[0].economic_impact_usd > 50_000_000


def test_darwinian_evolution_produces_offspring():
    catalog = get_exploit_catalog()
    template = get_template("governance_capture")
    vectors = generate_attack_vectors(template)[:5]
    states = [e.state for e in catalog if e.template_id == "governance_capture"]
    population = [evaluate_attack_vector(v, states) for v in vectors]
    evolved = darwinian_evolution(
        population, states, config={"generations": 1, "population": 3, "offspring_per_parent": 2}
    )
    assert len(evolved) > 0


def test_rediscovery_on_ground_truth():
    catalog = get_exploit_catalog()
    candidates = evaluate_catalog_directly(catalog)
    stats = run_rediscovery_test(candidates, catalog)
    assert stats["raw_rediscovered"] == len(catalog)