"""Tests for CPCV + PBO overfitting detection."""

from night_shift_security.core.cpcv import (
    cpcv_attack_params,
    create_temporal_folds,
    generate_param_variants,
    pbo_verdict,
)
from night_shift_security.data.exploit_catalog import get_exploit_catalog
from night_shift_security.core.evaluation import evaluate_attack_vector
from night_shift_security.data.schemas import AttackVector
from night_shift_security.validation.cpcv_stress import run_cpcv_phase

import night_shift_security.domain.attack_templates.governance_capture  # noqa: F401


def test_temporal_folds_created():
    catalog = get_exploit_catalog()
    folds = create_temporal_folds(catalog)
    assert len(folds) >= 1
    assert folds[0].train_exploit_ids
    assert folds[0].test_exploit_ids


def test_cpcv_governance_low_pbo_on_ground_truth():
    catalog = get_exploit_catalog()
    gov_exploits = [e for e in catalog if e.template_id == "governance_capture"]
    beanstalk = next(e for e in gov_exploits if e.exploit_id == "beanstalk-2022")
    params_grid = generate_param_variants(beanstalk.known_parameters, n_variants=10)
    result = cpcv_attack_params(gov_exploits, params_grid, "governance_capture", n_test_folds=2)
    assert result.n_paths > 0
    assert result.pbo <= 0.50


def test_pbo_verdict_labels():
    assert pbo_verdict(0.10) == "SAFE"
    assert pbo_verdict(0.20) == "ELEVATED"
    assert pbo_verdict(0.40) == "DANGER"


def test_cpcv_phase_runs_on_candidates():
    catalog = get_exploit_catalog()
    beanstalk = next(e for e in catalog if e.exploit_id == "beanstalk-2022")
    vector = AttackVector(
        template_id="governance_capture",
        parameters=beanstalk.known_parameters,
        label="beanstalk_cpcv",
    )
    cand = evaluate_attack_vector(vector, [beanstalk.state])
    results = run_cpcv_phase([cand], catalog, {"top_n": 1, "max_pbo": 0.50})
    assert len(results) >= 1
    assert cand.pbo >= 0