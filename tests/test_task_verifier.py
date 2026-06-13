"""Tests for operator task verifier."""

from night_shift_security.validation.task_verifier import (
    apply_verifier_to_fork_entry,
    finding_balance_verified,
    parse_threshold_wei,
    verify_from_forge_output,
    verify_from_solana_output,
)


def test_parse_threshold_wei_default():
    assert parse_threshold_wei({}) == 100_000_000_000_000_000


def test_verify_passes_on_delta_wei():
    output = "DELTA_WEI:200000000000000000\nBALANCE_BEFORE:0\nBALANCE_AFTER:200000000000000000"
    result = verify_from_forge_output(output, {"enabled": True})
    assert result.passed is True
    assert result.delta_wei == 200_000_000_000_000_000


def test_verify_fails_below_threshold():
    output = "DELTA_WEI:10000000000000000"
    result = verify_from_forge_output(output, {"enabled": True})
    assert result.passed is False


def test_catalog_exempt_skips_balance_requirement():
    result = verify_from_forge_output("IMPACT_USD:1000", {"required_for_novel": True}, catalog_exempt=True)
    assert result.passed is True
    assert result.method == "catalog_exempt"


def test_apply_verifier_downgrades_novel_fork_without_delta():
    entry = {"fork_reproduced": True, "fork_confirmed": True, "method": "evm_fork"}
    verifier = verify_from_forge_output("IMPACT_USD:1", {"enabled": True, "required_for_novel": True})
    apply_verifier_to_fork_entry(
        entry,
        verifier,
        required_for_novel=True,
        is_catalog_anchor=False,
    )
    assert entry["balance_verified"] is False
    assert entry["fork_reproduced"] is False


def test_verify_from_solana_output_passes_delta_lamports():
    output = "DELTA_LAMPORTS:500000000\nBALANCE_BEFORE:0\nBALANCE_AFTER:500000000"
    result = verify_from_solana_output(output, {"enabled": True, "threshold_lamports": "100000000"})
    assert result.passed is True
    assert result.method == "solana_output"


def test_finding_balance_verified_catalog_analogue():
    class _Finding:
        catalog_analogue = True
        fork_evidence = {}
        solana_evidence = {}

    assert finding_balance_verified(_Finding()) is True