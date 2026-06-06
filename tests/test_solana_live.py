"""Optional live Solana validator tests — skipped without tooling."""

import os

import pytest

from night_shift_security.core.gates import SecurityGate
from night_shift_security.data.exploit_catalog import get_exploit_catalog
from night_shift_security.validation.catalog_seeds import evaluate_catalog_seeds
from night_shift_security.validation.solana_rpc import solana_validator_available
from night_shift_security.validation.solana_validation import run_solana_validation_phase

pytestmark = pytest.mark.skipif(
    os.environ.get("SOLANA_USE_VALIDATOR", "").lower() not in ("1", "true", "yes")
    or not solana_validator_available(),
    reason="SOLANA_USE_VALIDATOR=1 and solana-test-validator required",
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


def test_live_mango_solana_reproduced():
    catalog = get_exploit_catalog()
    seeds = evaluate_catalog_seeds(catalog, _permissive_gates())
    mango = next(s for s in seeds if s.catalog_exploit_id == "mango-markets-2022")
    results = run_solana_validation_phase(
        [mango],
        catalog,
        {"top_n": 0, "always_test_catalog_solana_anchors": True},
    )
    entry = next(iter(results.values()))
    assert entry["method"] in ("solana_validator", "solana_fixture")
    assert mango.solana_reproduced is True