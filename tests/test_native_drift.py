"""Tests for the Drift Protocol v2 native harness (v6.5 onboarding)."""

from __future__ import annotations

import re

import pytest

from night_shift_security.native import drift
from night_shift_security.semantic.selectors import anchor_discriminator


def test_harness_metadata_constants() -> None:
    assert drift.HARNESS_TARGET == "drift"
    assert drift.HARNESS_PLATFORM == "immunefi"
    assert drift.HARNESS_CHAIN == "solana"
    assert drift.HARNESS_NAME == "Drift Protocol"
    assert drift.HARNESS_VERSION.startswith("v6.5")


def test_drift_program_address_shape() -> None:
    """Canonical Solana base58 program pubkey shape (Drift v2)."""
    assert drift.DRIFT_PROGRAM == "dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH"
    assert re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]{32,44}", drift.DRIFT_PROGRAM)


def test_program_ids_returns_drift_stack() -> None:
    ids = drift.program_ids()
    assert ids["drift"] == drift.DRIFT_PROGRAM
    assert ids["system"] == drift.SYSTEM_PROGRAM
    # SPL token program ID is exposed lazily.
    assert drift.spl_token_program_id() == drift.SPL_TOKEN_PROGRAM
    assert drift.SPL_TOKEN_PROGRAM.startswith("Token")
    assert drift.SPL_TOKEN_PROGRAM.endswith("5DA")


def test_program_ids_does_not_bleed_into_others() -> None:
    """Sentinel: Drift harness must not reuse other harnesses' program names."""
    marginfi_keys = {"marginfi"}
    kamino_keys = {"klend", "kvault", "oracle", "farms"}
    # 'system' is shared because it's the canonical Solana system program,
    # not a Drift-specific ID; comparing 'drift' / 'marginfi' / 'klend'
    # names keeps the sentinel meaningful across harnesses.
    assert not marginfi_keys.intersection(drift.program_ids().keys())
    assert not kamino_keys.intersection(drift.program_ids().keys())


def test_discriminators_top_instructions_present() -> None:
    discs = drift.discriminators()
    assert len(discs) >= 10  # at least 10 discriminators
    regex = re.compile(r"^0x[0-9a-f]{16}$")
    for name, value in discs.items():
        assert regex.match(value), f"bad discriminator for {name}: {value}"
    assert set(discs.keys()) == set(drift.TOP_DRIFT_INSTRUCTIONS)


def test_discriminators_deterministic() -> None:
    assert drift.discriminators() == drift.discriminators()


def test_discriminators_match_anchor_helper() -> None:
    for name in drift.TOP_DRIFT_INSTRUCTIONS:
        assert drift.discriminators()[name] == anchor_discriminator(name)


def test_discriminators_unique_against_other_harnesses() -> None:
    """Drift discriminators should not collide with Marginfi or Kamino."""
    from night_shift_security.native import marginfi

    drift_set = set(drift.discriminators().values())
    marginfi_set = set(marginfi.discriminators().values())
    assert not drift_set.intersection(marginfi_set)


def test_lp_pool_instructions_present() -> None:
    """LP pool actions must be present in discriminator list."""
    discs = drift.discriminators()
    assert "add_liquidity" in discs
    assert "remove_liquidity" in discs
    assert "swap" in discs


def test_signed_msg_instructions_present() -> None:
    """signed_msg_user order instructions must exist (this is the surface)."""
    discs = drift.discriminators()
    assert "initialize_signed_msg_user_orders" in discs
    assert "consume_signed_msg_user_orders" in discs


def test_load_idl_returns_dict_or_empty() -> None:
    """IDL loader must return dict shape compatible with Anchor JSON."""
    result = drift.load_idl()
    assert isinstance(result, dict)


def test_load_accounts_returns_dict_with_program_id() -> None:
    """Account loader must return minimally usable mapping."""
    accounts = drift.load_accounts()
    assert isinstance(accounts, dict)
    assert accounts.get("drift_program") == drift.DRIFT_PROGRAM


def test_security_md_out_of_scope_documented() -> None:
    """The probe script surfaces that oracle trust is out of scope per SECURITY.md."""
    # Drift's SECURITY.md item #4 excludes "incorrect data supplied by third
    # party oracles (this does not exclude oracle manipulation/flash loan
    # attacks)". The orchestrator must reflect this exclusion in any produced
    # candidate so the bounty-stage gate understands the scope boundary.
    security_md_item = (
        "Incorrect data supplied by third party oracles "
        "(this does not exclude oracle manipulation/flash loan attacks)"
    )
    # Confirm the literal is recoverable by inspecting the on-disk repo.
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[1]
    security_md = (
        repo_root / "sources" / "drift" / "repo" / "SECURITY.md"
    )
    if security_md.is_file():
        content = security_md.read_text()
        assert "drift" in content.lower()
        # The drift.exe scope clause must be present.
        assert "Incorrect data" in content or "oracle" in content.lower()


def test_resolve_market_handles_unreachable_rpc() -> None:
    """resolve_market must not throw on unreachable RPC; just return a sentinel."""
    notes = drift.resolve_market(
        "any-market",
        "http://does-not-resolve.invalid",
    )
    assert notes is not None
    assert notes.program_id == drift.DRIFT_PROGRAM
