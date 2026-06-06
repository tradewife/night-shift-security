"""Basic tests for Night Shift Security MVP."""

from night_shift_security.core.evaluation import evaluate_attack_vector
from night_shift_security.core.hypothesis import generate_attack_vectors, grid_combos
from night_shift_security.data.exploit_catalog import get_exploit_catalog
from night_shift_security.data.schemas import AttackVector
from night_shift_security.domain.attack_templates.governance_capture import GovernanceCaptureTemplate
from night_shift_security.validation.historical_replay import evaluate_catalog_directly, run_rediscovery_test


def test_grid_combos_count():
    template = GovernanceCaptureTemplate()
    combos = grid_combos(template.param_grid())
    assert len(combos) == 6 * 2 * 2  # 24 vectors


def test_ground_truth_exploits_succeed():
    catalog = get_exploit_catalog()
    results = evaluate_catalog_directly(catalog)
    successes = [r for r in results if r.results and r.results[0].success]
    assert len(successes) == len(catalog)


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


def test_pipeline_generates_vectors():
    template = GovernanceCaptureTemplate()
    vectors = generate_attack_vectors(template)
    assert len(vectors) == 24


def test_rediscovery_on_ground_truth():
    catalog = get_exploit_catalog()
    candidates = evaluate_catalog_directly(catalog)
    stats = run_rediscovery_test(candidates, catalog)
    assert stats["raw_rediscovered"] == len(catalog)