"""Tests for mainnet fork validation layer."""

from unittest.mock import MagicMock, patch

from night_shift_security.core.evaluation import evaluate_attack_vector
from night_shift_security.core.gates import SecurityGate
from night_shift_security.data.exploit_catalog import get_exploit_catalog
from night_shift_security.data.fork_targets import evm_fork_targets, get_fork_targets
from night_shift_security.data.schemas import AttackVector
from night_shift_security.validation.catalog_seeds import evaluate_catalog_seeds
from night_shift_security.validation.fork_validation import (
    is_fork_eligible,
    run_fork_validation_phase,
)

import night_shift_security.domain.attack_templates.reentrancy  # noqa: F401
import night_shift_security.domain.attack_templates.flash_loan_oracle  # noqa: F401
import night_shift_security.domain.attack_templates.access_control_escalation  # noqa: F401
import night_shift_security.domain.attack_templates.governance_capture  # noqa: F401
import night_shift_security.domain.attack_templates.treasury_drain  # noqa: F401


def test_fork_targets_include_euler_and_mango():
    targets = get_fork_targets()
    ids = {t.target_id for t in targets}
    assert "euler-finance-2023" in ids
    assert "mango-markets-2022" in ids
    assert "nomad-bridge-2022" in ids
    assert "wormhole-core-ethereum" in ids
    assert "wormhole-token-bridge-ethereum" in ids
    assert "wormhole-token-bridge-pauser-ethereum" in ids


def test_evm_fork_targets_exclude_solana():
    evm = evm_fork_targets()
    assert all(not t.solana for t in evm)
    assert any(t.target_id == "euler-finance-2023" for t in evm)


def test_euler_block_number():
    euler = next(t for t in get_fork_targets() if t.target_id == "euler-finance-2023")
    assert euler.block_number == 16_825_925
    assert euler.chain == "ethereum"


def test_fork_validation_catalog_fallback():
    catalog = get_exploit_catalog()
    euler = next(e for e in catalog if e.exploit_id == "euler-finance-2023")
    vector = AttackVector(
        template_id="reentrancy",
        parameters=euler.known_parameters,
        label="euler_fork",
    )
    cand = evaluate_attack_vector(vector, [euler.state])
    results = run_fork_validation_phase([cand], catalog, {"top_n": 1})
    assert len(results) == 1
    entry = next(iter(results.values()))
    assert entry["method"] in ("evm_fork", "catalog_fallback", "catalog_solana", "no_target")


def test_mango_fork_validation_via_catalog():
    catalog = get_exploit_catalog()
    mango = next(e for e in catalog if e.exploit_id == "mango-markets-2022")
    vector = AttackVector(
        template_id="flash_loan_oracle",
        parameters=mango.known_parameters,
        label="mango_fork",
    )
    cand = evaluate_attack_vector(vector, [mango.state])
    results = run_fork_validation_phase([cand], catalog, {"top_n": 1})
    entry = next(iter(results.values()))
    assert entry.get("fork_confirmed") is True
    assert entry.get("method") == "catalog_solana"
    assert entry.get("fork_reproduced") is False
    assert cand.fork_reproduced is False


def test_is_fork_eligible_requires_catalog_exploit_id():
    catalog = get_exploit_catalog()
    targets = get_fork_targets()
    euler = next(e for e in catalog if e.exploit_id == "euler-finance-2023")
    vector = AttackVector(
        template_id=euler.template_id,
        parameters=euler.known_parameters,
        label="euler_no_id",
    )
    cand = evaluate_attack_vector(vector, [euler.state])
    assert is_fork_eligible(cand, targets) is None

    cand.catalog_exploit_id = "euler-finance-2023"
    target = is_fork_eligible(cand, targets)
    assert target is not None
    assert target.target_id == "euler-finance-2023"


def _permissive_gates() -> SecurityGate:
    return SecurityGate(
        MIN_REPRODUCIBILITY=0.0,
        MIN_SEVERITY_SCORE=0.0,
        MIN_ECONOMIC_IMPACT_USD=0.0,
        MIN_INVARIANT_VIOLATIONS=0,
        MIN_REALISM_SCORE=0.0,
        MIN_GENERALITY=0.0,
    )


def test_always_test_catalog_evm_anchors_includes_low_rank_seed():
    catalog = get_exploit_catalog()
    seeds = evaluate_catalog_seeds(catalog, _permissive_gates())
    euler = next(s for s in seeds if s.catalog_exploit_id == "euler-finance-2023")
    low_rank = next(s for s in seeds if s.catalog_exploit_id == "cream-finance-2021")

    results = run_fork_validation_phase(
        [low_rank, euler],
        catalog,
        {"top_n": 0, "always_test_catalog_evm_anchors": True},
    )
    keys = set(results.keys())
    assert str(euler.vector.key()) in keys
    assert str(low_rank.vector.key()) not in keys


def test_fork_reproduced_strict_on_evm_fork_success():
    catalog = get_exploit_catalog()
    seeds = evaluate_catalog_seeds(catalog, _permissive_gates())
    euler = next(s for s in seeds if s.catalog_exploit_id == "euler-finance-2023")

    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = "IMPACT_USD:197000000\n"
    mock_proc.stderr = ""

    with (
        patch("night_shift_security.validation.fork_validation.rpc_available", return_value=True),
        patch("night_shift_security.validation.fork_validation.shutil.which", return_value="/usr/bin/forge"),
        patch("night_shift_security.validation.fork_validation.subprocess.run", return_value=mock_proc),
    ):
        results = run_fork_validation_phase(
            [euler],
            catalog,
            {"top_n": 0, "always_test_catalog_evm_anchors": True},
        )

    entry = next(iter(results.values()))
    assert entry["method"] == "evm_fork"
    assert entry["fork_confirmed"] is True
    assert entry["fork_reproduced"] is True
    assert euler.fork_reproduced is True
    assert euler.fork_block_number == 16_825_925
    assert euler.fork_evidence["exploit_id"] == "euler-finance-2023"
    assert euler.fork_evidence["impact_usd"] == 197_000_000


def test_wormhole_live_fork_targets_use_governance_probes():
    core = next(t for t in get_fork_targets() if t.target_id == "wormhole-core-ethereum")
    bridge = next(t for t in get_fork_targets() if t.target_id == "wormhole-token-bridge-ethereum")
    pauser = next(t for t in get_fork_targets() if t.target_id == "wormhole-token-bridge-pauser-ethereum")
    assert core.fork_test == "testForkWormholeCoreGovernanceSurface"
    assert bridge.fork_test == "testForkWormholeBridgeGovernanceSurface"
    assert pauser.fork_test == "testForkWormholeBridgePauserAuthSurface"


def test_wormhole_live_program_fork_preferred_over_nomad():
    catalog = get_exploit_catalog()
    nomad = next(e for e in catalog if e.exploit_id == "nomad-bridge-2022")
    vector = AttackVector(
        template_id="access_control_escalation",
        parameters=nomad.known_parameters,
        label="wormhole_live",
        target_id="wormhole",
    )
    cand = evaluate_attack_vector(vector, [nomad.state])

    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = (
        "DELTA_WEI:100000000000000000\n"
        "WORMHOLE_CORE_CODE_SIZE:12345\n"
        "IMPACT_USD:5000000\n"
    )
    mock_proc.stderr = ""

    with (
        patch("night_shift_security.validation.fork_validation.rpc_available", return_value=True),
        patch("night_shift_security.validation.fork_validation.shutil.which", return_value="/usr/bin/forge"),
        patch("night_shift_security.validation.fork_validation.subprocess.run", return_value=mock_proc),
    ):
        results = run_fork_validation_phase(
            [cand],
            catalog,
            {
                "top_n": 1,
                "always_test_catalog_evm_anchors": False,
                "prefer_live_programs": True,
                "campaign_target_id": "wormhole",
                "live_target_ids": [
                    "wormhole-core-ethereum",
                    "wormhole-token-bridge-ethereum",
                ],
            },
        )

    entry = next(iter(results.values()))
    assert entry["method"] == "evm_fork"
    assert entry["target_id"] == "wormhole-core-ethereum"
    assert entry["fork_reproduced"] is True
    assert cand.fork_evidence["exploit_id"] == "wormhole-live-core"
    assert cand.fork_evidence["contract"] == "0x98f3c9e6E3fAce36bAAd05FE09d375Ef1464288B"


def test_catalog_fallback_not_fork_reproduced():
    catalog = get_exploit_catalog()
    euler = next(e for e in catalog if e.exploit_id == "euler-finance-2023")
    vector = AttackVector(
        template_id=euler.template_id,
        parameters=euler.known_parameters,
        label="euler_fallback",
    )
    cand = evaluate_attack_vector(vector, [euler.state])
    cand.catalog_exploit_id = euler.exploit_id

    with patch("night_shift_security.validation.fork_validation.rpc_available", return_value=False):
        results = run_fork_validation_phase(
            [cand],
            catalog,
            {"top_n": 1, "always_test_catalog_evm_anchors": True},
        )

    entry = next(iter(results.values()))
    assert entry["method"] == "catalog_fallback"
    assert entry.get("fork_confirmed") is True
    assert entry["fork_reproduced"] is False
    assert cand.fork_reproduced is False