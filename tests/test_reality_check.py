"""Tests for lab vs deployed reality tier inference."""

from night_shift_security.validation.reality_check import infer_reproduction_method


def test_klend_harness_maps_to_solana_validator_when_balance_verified():
    tier = infer_reproduction_method(
        solana_evidence={
            "method": "solana_klend_harness",
            "balance_verified": True,
            "balance_delta_lamports": 50_000_000_000,
        },
        solana_reproduced=True,
    )
    assert tier == "solana_validator"


def test_kamino_klend_exploit_id_not_catalogue_analogue():
    from night_shift_security.validation.reality_check import _is_catalog_analogue

    assert not _is_catalog_analogue(
        target_id="kamino",
        solana_evidence={"exploit_id": "kamino-klend"},
    )


def test_klend_harness_without_verifier_falls_back():
    tier = infer_reproduction_method(
        solana_evidence={"method": "solana_klend_harness"},
        solana_reproduced=True,
    )
    assert tier == "solana_reproduced"