"""Tests for Solana validation layer."""

import os
from unittest.mock import MagicMock, patch

from night_shift_security.core.evaluation import evaluate_attack_vector
from night_shift_security.core.gates import SecurityGate
from night_shift_security.data.exploit_catalog import get_exploit_catalog
from night_shift_security.data.solana_targets import (
    get_solana_targets,
    solana_catalog_targets,
    validator_backed_targets,
)
from night_shift_security.data.schemas import AttackVector
from night_shift_security.validation.catalog_seeds import evaluate_catalog_seeds
from night_shift_security.validation.solana_validation import (
    is_solana_eligible,
    run_solana_validation_phase,
)


def _permissive_gates() -> SecurityGate:
    return SecurityGate(
        MIN_REPRODUCIBILITY=0.0,
        MIN_SEVERITY_SCORE=0.0,
        MIN_ECONOMIC_IMPACT_USD=0.0,
        MIN_INVARIANT_VIOLATIONS=0,
        MIN_REALISM_SCORE=0.0,
        MIN_GENERALITY=0.0,
    )


def test_solana_targets_include_slice1_incidents():
    ids = {t.target_id for t in get_solana_targets()}
    assert "mango-markets-2022" in ids
    assert "solend-whale-2022" in ids
    assert "cashio-2022" in ids
    assert "crema-finance-2022" in ids
    assert len(solana_catalog_targets()) == 4


def test_validator_backed_targets_slice2():
    backed = {t.exploit_id for t in validator_backed_targets()}
    assert backed == {"solend-whale-2022", "cashio-2022"}
    solend = next(t for t in get_solana_targets() if t.exploit_id == "solend-whale-2022")
    cashio = next(t for t in get_solana_targets() if t.exploit_id == "cashio-2022")
    assert solend.slot == 139_896_000
    assert cashio.slot == 128_587_000
    assert solend.program_id == "So1endDq2YkqhipRh3WViPa8hdiSpxWy6z3Z6tMCpAo"
    assert cashio.program_id == "BRRRot6ig147TBU6EGp7TMesmQrwu729CbG6qu2ZUHWm"


def test_catalog_has_19_exploits_including_solana():
    catalog = get_exploit_catalog()
    assert len(catalog) == 19
    solana_ids = {
        "mango-markets-2022",
        "solend-whale-2022",
        "cashio-2022",
        "crema-finance-2022",
    }
    assert solana_ids.issubset({e.exploit_id for e in catalog})


def test_new_solana_catalog_entries_pass_gates():
    catalog = get_exploit_catalog()
    for exploit_id in ("solend-whale-2022", "cashio-2022", "crema-finance-2022"):
        exploit = next(e for e in catalog if e.exploit_id == exploit_id)
        vector = AttackVector(
            template_id=exploit.template_id,
            parameters=exploit.known_parameters,
            target_id=exploit.state.protocol_id,
        )
        cand = evaluate_attack_vector(vector, [exploit.state])
        assert not cand.rejected, exploit_id


def test_is_solana_eligible_requires_catalog_exploit_id():
    catalog = get_exploit_catalog()
    targets = get_solana_targets()
    mango = next(e for e in catalog if e.exploit_id == "mango-markets-2022")
    vector = AttackVector(
        template_id=mango.template_id,
        parameters=mango.known_parameters,
        label="mango_no_id",
    )
    cand = evaluate_attack_vector(vector, [mango.state])
    assert is_solana_eligible(cand, targets) is None

    cand.catalog_exploit_id = "mango-markets-2022"
    target = is_solana_eligible(cand, targets)
    assert target is not None
    assert target.slot == 152_000_000


def test_always_test_catalog_solana_anchors_includes_mango():
    catalog = get_exploit_catalog()
    seeds = evaluate_catalog_seeds(catalog, _permissive_gates())
    mango = next(s for s in seeds if s.catalog_exploit_id == "mango-markets-2022")
    euler = next(s for s in seeds if s.catalog_exploit_id == "euler-finance-2023")

    results = run_solana_validation_phase(
        [euler, mango],
        catalog,
        {"top_n": 0, "always_test_catalog_solana_anchors": True},
    )
    assert str(mango.vector.key()) in results
    assert str(euler.vector.key()) not in results


def test_solana_reproduced_strict_on_fixture_success():
    catalog = get_exploit_catalog()
    seeds = evaluate_catalog_seeds(catalog, _permissive_gates())
    mango = next(s for s in seeds if s.catalog_exploit_id == "mango-markets-2022")

    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = "IMPACT_USD:110000000\nIMPACT_LAMPORTS:733333333333\n"
    mock_proc.stderr = ""

    with patch("night_shift_security.validation.solana_validation.subprocess.run", return_value=mock_proc):
        results = run_solana_validation_phase(
            [mango],
            catalog,
            {"top_n": 0, "always_test_catalog_solana_anchors": True},
        )

    entry = next(iter(results.values()))
    assert entry["method"] == "solana_fixture"
    assert entry["solana_confirmed"] is True
    assert entry["solana_reproduced"] is True
    assert mango.solana_reproduced is True
    assert mango.solana_slot == 152_000_000
    assert mango.solana_evidence["exploit_id"] == "mango-markets-2022"


def test_mango_fixture_end_to_end_without_mock():
    catalog = get_exploit_catalog()
    seeds = evaluate_catalog_seeds(catalog, _permissive_gates())
    mango = next(s for s in seeds if s.catalog_exploit_id == "mango-markets-2022")

    results = run_solana_validation_phase(
        [mango],
        catalog,
        {"top_n": 0, "always_test_catalog_solana_anchors": True},
    )
    entry = next(iter(results.values()))
    assert entry["method"] == "solana_fixture"
    assert entry["solana_reproduced"] is True
    assert mango.solana_evidence["impact_usd"] == 110_000_000


def test_fixture_mode_never_uses_validator_method():
    """Without validator readiness, SOLANA_USE_VALIDATOR does not emit solana_validator."""
    catalog = get_exploit_catalog()
    seeds = evaluate_catalog_seeds(catalog, _permissive_gates())
    solend = next(s for s in seeds if s.catalog_exploit_id == "solend-whale-2022")

    env = {k: v for k, v in os.environ.items() if k != "SOLANA_USE_VALIDATOR"}
    with patch.dict(os.environ, env, clear=True):
        results = run_solana_validation_phase(
            [solend],
            catalog,
            {"top_n": 0, "always_test_catalog_solana_anchors": True},
        )

    entry = next(iter(results.values()))
    assert entry["method"] == "solana_fixture"
    assert entry["solana_reproduced"] is True
    assert entry["method"] != "solana_validator"


def test_validator_env_uses_fixture_for_non_backed_mango():
    catalog = get_exploit_catalog()
    seeds = evaluate_catalog_seeds(catalog, _permissive_gates())
    mango = next(s for s in seeds if s.catalog_exploit_id == "mango-markets-2022")

    with patch.dict(os.environ, {"SOLANA_USE_VALIDATOR": "1", "SOLANA_MAINNET_RPC_URL": "http://rpc.test"}):
        with patch("night_shift_security.validation.solana_validation.solana_validator_ready", return_value=True):
            results = run_solana_validation_phase(
                [mango],
                catalog,
                {"top_n": 0, "always_test_catalog_solana_anchors": True},
            )

    entry = next(iter(results.values()))
    assert entry["method"] == "solana_fixture"
    assert "solana_validator" not in entry["method"]


def test_solana_validator_strict_success():
    catalog = get_exploit_catalog()
    seeds = evaluate_catalog_seeds(catalog, _permissive_gates())
    solend = next(s for s in seeds if s.catalog_exploit_id == "solend-whale-2022")

    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = (
        "SOLANA_VALIDATOR_PASS:1\n"
        "SLOT_TARGET:139896000\n"
        "SLOT_CURRENT:42\n"
        "IMPACT_USD:25000000\n"
        "IMPACT_LAMPORTS:166666666667\n"
    )
    mock_proc.stderr = ""

    with patch.dict(os.environ, {"SOLANA_USE_VALIDATOR": "1", "SOLANA_MAINNET_RPC_URL": "http://rpc.test"}):
        with patch("night_shift_security.validation.solana_validation.solana_validator_ready", return_value=True):
            with patch("night_shift_security.validation.solana_validation.subprocess.run", return_value=mock_proc):
                results = run_solana_validation_phase(
                    [solend],
                    catalog,
                    {"top_n": 0, "always_test_catalog_solana_anchors": True},
                )

    entry = next(iter(results.values()))
    assert entry["method"] == "solana_validator"
    assert entry["solana_reproduced"] is True
    assert solend.solana_evidence["method"] == "solana_validator"
    assert solend.solana_evidence["slot_target"] == 139_896_000


def test_validator_failure_not_reproduced():
    catalog = get_exploit_catalog()
    seeds = evaluate_catalog_seeds(catalog, _permissive_gates())
    cashio = next(s for s in seeds if s.catalog_exploit_id == "cashio-2022")

    mock_proc = MagicMock()
    mock_proc.returncode = 1
    mock_proc.stdout = ""
    mock_proc.stderr = "validator replay failed"

    with patch.dict(os.environ, {"SOLANA_USE_VALIDATOR": "1", "SOLANA_MAINNET_RPC_URL": "http://rpc.test"}):
        with patch("night_shift_security.validation.solana_validation.solana_validator_ready", return_value=True):
            with patch("night_shift_security.validation.solana_validation.subprocess.run", return_value=mock_proc):
                results = run_solana_validation_phase(
                    [cashio],
                    catalog,
                    {"top_n": 0, "always_test_catalog_solana_anchors": True},
                )

    entry = next(iter(results.values()))
    assert entry["method"] == "solana_validator"
    assert entry["solana_confirmed"] is False
    assert entry["solana_reproduced"] is False


def test_validator_output_missing_pass_not_reproduced():
    catalog = get_exploit_catalog()
    seeds = evaluate_catalog_seeds(catalog, _permissive_gates())
    cashio = next(s for s in seeds if s.catalog_exploit_id == "cashio-2022")

    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = "IMPACT_USD:52000000\nSLOT_TARGET:128587000\n"
    mock_proc.stderr = ""

    with patch.dict(os.environ, {"SOLANA_USE_VALIDATOR": "1", "SOLANA_MAINNET_RPC_URL": "http://rpc.test"}):
        with patch("night_shift_security.validation.solana_validation.solana_validator_ready", return_value=True):
            with patch("night_shift_security.validation.solana_validation.subprocess.run", return_value=mock_proc):
                results = run_solana_validation_phase(
                    [cashio],
                    catalog,
                    {"top_n": 0, "always_test_catalog_solana_anchors": True},
                )

    entry = next(iter(results.values()))
    assert entry["method"] == "solana_validator"
    assert entry["solana_reproduced"] is False


def test_catalog_fallback_not_solana_reproduced():
    catalog = get_exploit_catalog()
    mango = next(e for e in catalog if e.exploit_id == "mango-markets-2022")
    vector = AttackVector(
        template_id=mango.template_id,
        parameters=mango.known_parameters,
        label="mango_topn_only",
    )
    cand = evaluate_attack_vector(vector, [mango.state])

    with patch(
        "night_shift_security.validation.solana_validation._fixture_runner_available",
        return_value=False,
    ):
        results = run_solana_validation_phase([cand], catalog, {"top_n": 1})

    entry = next(iter(results.values()))
    assert entry["method"] == "catalog_solana"
    assert entry["solana_confirmed"] is True
    assert entry["solana_reproduced"] is False