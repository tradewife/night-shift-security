"""Optional live Solana validator tests — skipped without tooling."""

import os

import pytest

from night_shift_security.core.gates import SecurityGate
from night_shift_security.data.exploit_catalog import get_exploit_catalog
from night_shift_security.validation.catalog_seeds import evaluate_catalog_seeds
from night_shift_security.validation.solana_rpc import solana_validator_ready
from night_shift_security.validation.solana_validation import run_solana_validation_phase

pytestmark = pytest.mark.skipif(
    os.environ.get("SOLANA_USE_VALIDATOR", "").lower() not in ("1", "true", "yes")
    or not solana_validator_ready(),
    reason="SOLANA_USE_VALIDATOR=1, solana-test-validator, and SOLANA_MAINNET_RPC_URL required",
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


@pytest.mark.parametrize("exploit_id", ["solend-whale-2022", "cashio-2022"])
def test_live_validator_backed_reproduced(exploit_id: str):
    catalog = get_exploit_catalog()
    seeds = evaluate_catalog_seeds(catalog, _permissive_gates())
    seed = next(s for s in seeds if s.catalog_exploit_id == exploit_id)
    results = run_solana_validation_phase(
        [seed],
        catalog,
        {"top_n": 0, "always_test_catalog_solana_anchors": True},
    )
    entry = next(iter(results.values()))
    assert entry["method"] == "solana_validator"
    assert entry["solana_reproduced"] is True
    assert seed.solana_evidence["method"] == "solana_validator"