"""Optional live archive-RPC fork tests — skipped without ETHEREUM_RPC_URL."""

import os

import pytest

from night_shift_security.core.evaluation import evaluate_attack_vector
from night_shift_security.data.exploit_catalog import get_exploit_catalog
from night_shift_security.validation.catalog_seeds import evaluate_catalog_seeds
from night_shift_security.validation.fork_validation import run_fork_validation_phase
from night_shift_security.validation.rpc import rpc_available

import night_shift_security.domain.attack_templates.reentrancy  # noqa: F401
import night_shift_security.domain.attack_templates.access_control_escalation  # noqa: F401
import night_shift_security.domain.attack_templates.governance_capture  # noqa: F401

pytestmark = pytest.mark.skipif(
    not os.environ.get("ETHEREUM_RPC_URL") or not rpc_available(),
    reason="ETHEREUM_RPC_URL archive node required",
)


def test_live_euler_fork_reproduced():
    catalog = get_exploit_catalog()
    from night_shift_security.core.gates import SecurityGate

    permissive = SecurityGate(
        MIN_REPRODUCIBILITY=0.0,
        MIN_SEVERITY_SCORE=0.0,
        MIN_ECONOMIC_IMPACT_USD=0.0,
        MIN_INVARIANT_VIOLATIONS=0,
        MIN_REALISM_SCORE=0.0,
        MIN_GENERALITY=0.0,
    )
    seeds = evaluate_catalog_seeds(catalog, permissive)
    euler = next(s for s in seeds if s.catalog_exploit_id == "euler-finance-2023")
    results = run_fork_validation_phase(
        [euler],
        catalog,
        {"top_n": 0, "always_test_catalog_evm_anchors": True},
    )
    entry = next(iter(results.values()))
    assert entry["method"] == "evm_fork"
    assert entry["fork_confirmed"] is True
    assert euler.fork_reproduced is True
    assert euler.fork_evidence.get("impact_usd", 0) > 0


def test_live_nomad_fork_reproduced():
    catalog = get_exploit_catalog()
    nomad = next(e for e in catalog if e.exploit_id == "nomad-bridge-2022")
    from night_shift_security.data.schemas import AttackVector

    vector = AttackVector(
        template_id=nomad.template_id,
        parameters=nomad.known_parameters,
        target_id=nomad.state.protocol_id,
        label="nomad_live",
    )
    cand = evaluate_attack_vector(vector, [nomad.state])
    cand.catalog_exploit_id = nomad.exploit_id
    results = run_fork_validation_phase(
        [cand],
        catalog,
        {"top_n": 0, "always_test_catalog_evm_anchors": True},
    )
    entry = next(iter(results.values()))
    assert entry["method"] == "evm_fork"
    assert cand.fork_reproduced is True