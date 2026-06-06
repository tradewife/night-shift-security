"""Tests for mainnet fork validation layer."""

from night_shift_security.core.evaluation import evaluate_attack_vector
from night_shift_security.data.exploit_catalog import get_exploit_catalog
from night_shift_security.data.fork_targets import evm_fork_targets, get_fork_targets
from night_shift_security.data.schemas import AttackVector
from night_shift_security.validation.fork_validation import run_fork_validation_phase

import night_shift_security.domain.attack_templates.reentrancy  # noqa: F401
import night_shift_security.domain.attack_templates.flash_loan_oracle  # noqa: F401


def test_fork_targets_include_euler_and_mango():
    targets = get_fork_targets()
    ids = {t.target_id for t in targets}
    assert "euler-finance-2023" in ids
    assert "mango-markets-2022" in ids
    assert "nomad-bridge-2022" in ids


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