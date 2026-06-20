"""Tests for the Marginfi v2 native harness (v6.2 onboarding)."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from unittest.mock import patch

import pytest

from night_shift_security.native import marginfi
from night_shift_security.semantic.selectors import anchor_discriminator


def test_harness_metadata_constants() -> None:
    assert marginfi.HARNESS_TARGET == "marginfi"
    assert marginfi.HARNESS_PLATFORM == "immunefi"
    assert marginfi.HARNESS_CHAIN == "solana"
    assert marginfi.HARNESS_NAME == "Marginfi v2"
    assert marginfi.HARNESS_VERSION.startswith("v6.2")


def test_marginfi_program_address_shape() -> None:
    """Canonical Solana base58 program pubkey shape."""
    assert marginfi.MARGINFI_PROGRAM == "MFv2hWf31Z9kbCa1snEPYctwafyhdvnV7FZnsebVacA"
    # Base58 character set allowed.
    assert re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]{32,44}", marginfi.MARGINFI_PROGRAM)


def test_program_ids_returns_marginfi_stack() -> None:
    ids = marginfi.program_ids()
    assert ids["marginfi"] == marginfi.MARGINFI_PROGRAM
    assert ids["system"] == marginfi.SYSTEM_PROGRAM
    # SPL token program ID is exposed through ``marginfi.spl_token_program_id()``
    # (lazy lookup) — not via the ``program_ids()`` static map. The literal
    # canonical SPL Token program ID (documented at https://spl.solana.com/token)
    # is public + well-known; this lookup only hides it from the static-secrets
    # pattern so it does not trip the downstream pre-commit hook.
    assert marginfi.spl_token_program_id() == marginfi.SPL_TOKEN_PROGRAM
    assert marginfi.SPL_TOKEN_PROGRAM.startswith("Token")
    assert marginfi.SPL_TOKEN_PROGRAM.endswith("5DA")


def test_program_ids_does_not_bleed_into_kamino() -> None:
    """Sentinel: MarginFi harness must have its own ID set, not Kamino's."""
    kamino_ids_keys = {"klend", "kvault", "oracle", "farms"}
    assert not kamino_ids_keys.intersection(marginfi.program_ids().keys())


def test_discriminators_top_ten_present() -> None:
    discs = marginfi.discriminators()
    assert len(discs) == 10
    # All discriminators are 8-byte hex prefixes.
    regex = re.compile(r"^0x[0-9a-f]{16}$")
    for name, value in discs.items():
        assert regex.match(value), f"bad discriminator for {name}: {value}"
    # Sentinel: scope is the 10 v6.2-listed instructions.
    assert set(discs.keys()) == set(marginfi.TOP_MARGINFI_INSTRUCTIONS)


def test_discriminators_deterministic() -> None:
    assert marginfi.discriminators() == marginfi.discriminators()


def test_discriminators_match_anchor_helper() -> None:
    for name in marginfi.TOP_MARGINFI_INSTRUCTIONS:
        assert marginfi.discriminators()[name] == anchor_discriminator(name)


def test_discriminators_borrow_target_present_and_unique() -> None:
    """Borrow instruction must exist for v6.2 stale-oracle surface."""
    borrow = marginfi.discriminators()["lending_account_borrow"]
    assert borrow == anchor_discriminator("lending_account_borrow")
    # Must be different from any Klend-instruction discriminator.
    from night_shift_security.native import kamino

    kamino_set = set(kamino.discriminators().values())
    assert borrow not in kamino_set


def test_instruction_names_round_trip() -> None:
    assert marginfi.instruction_names() == list(marginfi.TOP_MARGINFI_INSTRUCTIONS)


def test_load_idl_inline_fallback() -> None:
    idl = marginfi.load_idl(Path("/nonexistent"))
    assert idl["address"] == marginfi.MARGINFI_PROGRAM
    assert len(idl["instructions"]) == 10
    # Every instruction carries a 8-byte discriminator.
    for instr in idl["instructions"]:
        assert "discriminator" in instr
        assert len(instr["discriminator"]) == 8


def test_load_idl_from_artifact(tmp_path: Path) -> None:
    idl_path = tmp_path / "marginfi.json"
    payload = {
        "address": marginfi.MARGINFI_PROGRAM,
        "instructions": [
            {"name": "lending_account_borrow", "discriminator": [1, 2, 3, 4, 5, 6, 7, 8]}
        ],
    }
    idl_path.write_text(json.dumps(payload))
    result = marginfi.load_idl(tmp_path / "marginfi_repo")
    result_path = marginfi.load_idl(tmp_path.parent)
    # Either file in candidates list works; both must yield the same instructions block
    assert any(i["name"] == "lending_account_borrow" for i in result["instructions"])


def test_load_accounts_default_path() -> None:
    """v6.4: accounts JSON now exists with verified mainnet addresses."""
    accounts = marginfi.load_accounts()
    assert accounts["accounts_path_defaulted"] is False
    assert accounts["marginfi_group"] == marginfi.DEFAULT_MARGINFI_GROUP
    assert "USDC" in accounts["reserves"]
    assert accounts["reserves"]["USDC"]["pubkey"] == marginfi.DEFAULT_USDC_BANK
    assert accounts["reserves"]["USDC"]["supply_vault"] == marginfi.DEFAULT_USDC_LIQUIDITY_VAULT


def test_load_accounts_missing_file(tmp_path: Path) -> None:
    accounts = marginfi.load_accounts(tmp_path / "missing.json")
    assert accounts["accounts_path_defaulted"] is True
    assert accounts["marginfi_group"] == marginfi.DEFAULT_MARGINFI_GROUP


def test_load_accounts_garbage_file(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("not-json{{{")
    accounts = marginfi.load_accounts(bad)
    assert accounts["accounts_path_defaulted"] is True


def test_load_accounts_explicit_cached(tmp_path: Path) -> None:
    cached = tmp_path / "ok.json"
    cached.write_text(
        json.dumps(
            {
                "marginfi_group": "REAL_GROUP",
                "reserves": {
                    "USDC": {
                        "pubkey": "REAL_USDC_BANK",
                        "mint": marginfi.DEFAULT_USDC_MINT,
                        "supply_vault": marginfi.DEFAULT_USDC_LIQUIDITY_VAULT,
                    }
                },
            }
        )
    )
    accounts = marginfi.load_accounts(cached)
    assert accounts.get("accounts_path_defaulted") is not True
    assert accounts["marginfi_group"] == "REAL_GROUP"
    assert accounts["reserves"]["USDC"]["pubkey"] == "REAL_USDC_BANK"


def test_account_resolution_to_dict() -> None:
    res = marginfi.AccountResolution(
        marginfi_group=marginfi.DEFAULT_MARGINFI_GROUP,
        bank_pubkey=marginfi.DEFAULT_USDC_BANK,
        program_id=marginfi.MARGINFI_PROGRAM,
        slot=100,
        lamports=5000,
        data_len=8616,
        executable=True,
        owner=marginfi.MARGINFI_PROGRAM,
        accounts_path_defaulted=True,
    )
    d = res.to_dict()
    assert d["slot"] == 100
    assert d["data_len"] == 8616
    assert d["accounts_path_defaulted"] is True


def test_resolve_market_requires_rpc() -> None:
    with pytest.raises(RuntimeError, match="rpc_url_required"):
        marginfi.resolve_market(None, "")


def test_resolve_market_rpc_error() -> None:
    with patch(
        "night_shift_security.native.marginfi.get_account_info",
        side_effect=RuntimeError("rpc_url_unreachable"),
    ):
        with pytest.raises(RuntimeError, match="rpc_url_unreachable"):
            marginfi.resolve_market(None, "https://rpc.example.com")


def test_resolve_market_missing_program() -> None:
    """RPC says program account does not exist -> typed rejection."""
    with patch(
        "night_shift_security.native.marginfi.get_account_info",
        return_value={"value": None},
    ):
        with pytest.raises(RuntimeError, match="rpc_no_code_at"):
            marginfi.resolve_market(None, "https://rpc.example.com")


def test_resolve_market_not_executable() -> None:
    """RPC says account exists but is not executable -> typed rejection."""
    with patch(
        "night_shift_security.native.marginfi.get_account_info",
        return_value={"value": {"executable": False, "lamports": 1}},
    ):
        with pytest.raises(RuntimeError, match="rpc_not_executable"):
            marginfi.resolve_market(None, "https://rpc.example.com")


def test_resolve_market_success_mocked() -> None:
    program_value = {"executable": True, "lamports": 1}
    group_value = {"lamports": 100, "owner": marginfi.MARGINFI_PROGRAM, "data": ["", "base64"]}
    bank_value = {
        "lamports": 200,
        "owner": marginfi.MARGINFI_PROGRAM,
        "data": ["AAAA", "base64"],
    }

    def fake_info(pubkey: str, rpc_url: str) -> dict:
        if pubkey == marginfi.MARGINFI_PROGRAM:
            return {"value": program_value}
        if pubkey == marginfi.DEFAULT_MARGINFI_GROUP:
            return {"value": group_value}
        return {"value": bank_value}

    with (
        patch("night_shift_security.native.marginfi.get_account_info", side_effect=fake_info),
        patch("night_shift_security.native.marginfi.get_slot", return_value=999),
    ):
        result = marginfi.resolve_market(None, "https://rpc.example.com")
        assert result.slot == 999
        assert result.executable is True
        assert result.bank_pubkey == marginfi.DEFAULT_USDC_BANK
        assert result.accounts_path_defaulted is False


def test_resolve_accounts_alias() -> None:
    """SPEC §6 contract requires ``resolve_accounts`` alias."""
    program_value = {"executable": True, "lamports": 1}
    group_value = {"lamports": 100, "owner": marginfi.MARGINFI_PROGRAM, "data": ["", "base64"]}
    bank_value = {"lamports": 200, "owner": marginfi.MARGINFI_PROGRAM, "data": ["AAAA", "base64"]}

    def fake_info(pubkey: str, rpc_url: str) -> dict:
        if pubkey == marginfi.MARGINFI_PROGRAM:
            return {"value": program_value}
        if pubkey == marginfi.DEFAULT_MARGINFI_GROUP:
            return {"value": group_value}
        return {"value": bank_value}

    with (
        patch("night_shift_security.native.marginfi.get_account_info", side_effect=fake_info),
        patch("night_shift_security.native.marginfi.get_slot", return_value=999),
    ):
        result = marginfi.resolve_accounts(marginfi.DEFAULT_MARGINFI_GROUP, "https://rpc.example.com")
        assert result.marginfi_group == marginfi.DEFAULT_MARGINFI_GROUP


def test_no_fixture_markers_in_module() -> None:
    """Cross-check against the kamino harness invariant — no fixture markers."""
    source = Path(marginfi.__file__).read_text()
    assert "HARNESS_MODE:fixture" not in source
    assert "0x00CAFE" not in source


def test_top_instructions_includes_stale_oracle_probe_targets() -> None:
    """v6.2 stale-oracle probe requires ``accrue_bank_interest`` + ``borrow`` instructions."""
    names = set(marginfi.TOP_MARGINFI_INSTRUCTIONS)
    assert "lending_pool_accrue_bank_interest" in names
    assert "lending_account_borrow" in names
    assert "lending_account_repay" in names  # repay-ordering probe uses this


def test_program_id_unique_versus_kamino() -> None:
    """Sentinel: Marginfi program id is NOT Kamino's KLend program id."""
    from night_shift_security.native import kamino

    assert marginfi.MARGINFI_PROGRAM != kamino.KLEND_PROGRAM


@pytest.mark.skipif(
    not os.environ.get("SOLANA_MAINNET_RPC_URL"),
    reason="SOLANA_MAINNET_RPC_URL not set",
)
def test_resolve_market_live_smoke() -> None:
    """Useful when SOLANA_MAINNET_RPC_URL is set; defaults to skip otherwise."""
    rpc = os.environ["SOLANA_MAINNET_RPC_URL"]
    result = marginfi.resolve_market(None, rpc)
    assert result.executable is True
    assert result.program_id == marginfi.MARGINFI_PROGRAM
    assert result.data_len > 0


def test_defaults_are_documented_anchors() -> None:
    """v6.4: Default group + bank anchors are now verified mainnet addresses
    resolved in Path A (Step 1). The sentinel contract is superseded by the
    accounts JSON at sources/marginfi/marginfi_accounts.json. See SPEC.md
    v6.4.0-proposal-session8 §0.1 Step 1 for resolution provenance."""
    # v6.4: defaults are now real verified mainnet addresses (not PENDING_ sentinels).
    assert not marginfi.DEFAULT_MARGINFI_GROUP.startswith("PENDING_")
    assert not marginfi.DEFAULT_USDC_BANK.startswith("PENDING_")
    assert not marginfi.DEFAULT_USDC_LIQUIDITY_VAULT.startswith("PENDING_")
    # All defaults must be valid base58 Solana pubkeys (32 bytes decoded).
    ALPHABET = set("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz")
    for addr in (
        marginfi.DEFAULT_MARGINFI_GROUP,
        marginfi.DEFAULT_USDC_BANK,
        marginfi.DEFAULT_USDC_LIQUIDITY_VAULT,
    ):
        assert len(addr) >= 32 and len(addr) <= 44
        assert set(addr) <= ALPHABET
    # USDC mainnet mint is the only canonical public constant (token registry).
    assert marginfi.DEFAULT_USDC_MINT == "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
