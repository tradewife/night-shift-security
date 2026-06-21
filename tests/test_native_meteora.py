"""Tests for the Meteora DLMM NativeHarness (v6.6 onboarding)."""

from __future__ import annotations

import re

import pytest

from night_shift_security.native import meteora
from night_shift_security.semantic.selectors import anchor_discriminator


def test_harness_metadata_constants() -> None:
    assert meteora.HARNESS_TARGET == "meteora"
    assert meteora.HARNESS_PLATFORM == "immunefi"
    assert meteora.HARNESS_CHAIN == "solana"
    assert "Meteora" in meteora.HARNESS_NAME
    assert meteora.HARNESS_VERSION.startswith("v6.6")


def test_meteora_program_address_shape() -> None:
    """Canonical Solana base58 program pubkey shape (Meteora DLMM)."""
    assert meteora.METEORA_DLMM_PROGRAM == "LbVRzDTvBDEcrthxfZ4RL6yiq3uZw8bS6MwtdY6UhFQ"
    assert re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]{32,44}", meteora.METEORA_DLMM_PROGRAM)


def test_program_ids_returns_meteora_stack() -> None:
    ids = meteora.program_ids()
    assert ids["meteora_dlmm"] == meteora.METEORA_DLMM_PROGRAM
    assert ids["system"] == meteora.SYSTEM_PROGRAM


def test_discriminators_produced_for_all_instructions() -> None:
    disc = meteora.discriminators()
    for name in meteora.TOP_METEORA_INSTRUCTIONS:
        assert name in disc
        assert disc[name].startswith("0x")


def test_discriminators_are_unique() -> None:
    disc = meteora.discriminators()
    values = list(disc.values())
    assert len(values) == len(set(values))


def test_instruction_names_match_top_instructions() -> None:
    names = meteora.instruction_names()
    assert names == list(meteora.TOP_METEORA_INSTRUCTIONS)


def test_instruction_names_include_core_operations() -> None:
    names = meteora.instruction_names()
    assert "swap" in names
    assert "add_liquidity" in names
    assert "remove_liquidity" in names


def test_harness_differs_from_other_harnesses() -> None:
    """Ensure Meteora does not collide with existing harnesses."""
    from night_shift_security.native import kamino, marginfi, drift
    assert meteora.HARNESS_TARGET != kamino.HARNESS_TARGET
    assert meteora.HARNESS_TARGET != marginfi.HARNESS_TARGET
    assert meteora.HARNESS_TARGET != drift.HARNESS_TARGET
    ids = meteora.program_ids()
    assert ids["meteora_dlmm"] != kamino.KLEND_PROGRAM
    assert ids["meteora_dlmm"] != marginfi.MARGINFI_PROGRAM
    assert ids["meteora_dlmm"] != drift.DRIFT_PROGRAM


def test_resolve_market_with_hint() -> None:
    resolution = meteora.resolve_market("SomePubkey123", "")
    assert resolution.pool_pubkey == "SomePubkey123"
    assert resolution.accounts_path_defaulted is True


def test_resolve_market_empty() -> None:
    resolution = meteora.resolve_market("", "")
    assert resolution.accounts_path_defaulted is True


def test_load_accounts_missing_file() -> None:
    result = meteora.load_accounts("/nonexistent/path.json")
    assert result == {}


def test_load_idl_missing_repo() -> None:
    result = meteora.load_idl("/nonexistent/repo")
    assert result == {}


def test_get_slot_returns_int() -> None:
    """Should not crash even if RPC is unavailable."""
    result = meteora.get_slot("https://api.mainnet-beta.solana.com")
    assert isinstance(result, int)


def test_get_account_info_returns_dict() -> None:
    """Should not crash even if RPC is unavailable."""
    result = meteora.get_account_info(
        "11111111111111111111111111111111",
        "https://api.mainnet-beta.solana.com",
    )
    assert isinstance(result, dict)


def test_dynamic_fee_fsm_constants_referenced() -> None:
    """Verify DLMM-specific instruction names that differentiate from CLMM."""
    names = meteora.instruction_names()
    # Dynamic fee management is unique to Meteora DLMM
    assert "set_dynamic_fee" in names
    assert "claim_protocol_fee" in names
    assert "claim_host_fee" in names
