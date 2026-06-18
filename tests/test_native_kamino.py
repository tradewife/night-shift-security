"""Tests for the Kamino KLend native harness (Phase 7)."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from unittest.mock import patch

import pytest

from night_shift_security.native import kamino
from night_shift_security.semantic.selectors import anchor_discriminator


def test_harness_metadata_constants() -> None:
    assert kamino.HARNESS_TARGET == "kamino"
    assert kamino.HARNESS_PLATFORM == "immunefi"
    assert kamino.HARNESS_CHAIN == "solana"
    assert kamino.HARNESS_NAME == "Kamino"


def test_program_ids_returns_klend_stack() -> None:
    ids = kamino.program_ids()
    assert ids["klend"] == "KLend2g3cP87fffoy8q1mQqGKjrxjC8boSyAYavgmjD"
    assert ids["kvault"] == "KvauGMspG5k6rtzrqqn7WNn3oZdyKqLKwK2XWQ8FLjd"
    assert ids["oracle"] == "HFn8GnPADiny6XqUoWE8uRPPxb29ikn4yTuPa9MF2fWJ"


def test_discriminators_top_ten_present() -> None:
    discs = kamino.discriminators()
    assert len(discs) == 10
    regex = re.compile(r"^0x[0-9a-f]{16}$")
    for name, value in discs.items():
        assert regex.match(value), f"bad discriminator for {name}: {value}"


def test_discriminators_deterministic() -> None:
    assert kamino.discriminators() == kamino.discriminators()


def test_discriminators_match_anchor_helper() -> None:
    for name in kamino.TOP_KLEND_INSTRUCTIONS:
        assert kamino.discriminators()[name] == anchor_discriminator(name)


def test_instruction_names_round_trip() -> None:
    assert kamino.instruction_names() == list(kamino.TOP_KLEND_INSTRUCTIONS)


def test_load_idl_inline_fallback() -> None:
    idl = kamino.load_idl(Path("/nonexistent"))
    assert idl["address"] == kamino.KLEND_PROGRAM
    assert len(idl["instructions"]) == 10


def test_load_idl_from_artifact(tmp_path: Path) -> None:
    idl_dir = tmp_path / "target" / "idl"
    idl_dir.mkdir(parents=True)
    payload = {"address": kamino.KLEND_PROGRAM, "instructions": [{"name": "swap"}]}
    (idl_dir / "klend.json").write_text(json.dumps(payload))
    result = kamino.load_idl(tmp_path)
    assert result["instructions"][0]["name"] == "swap"


def test_load_accounts_default_path() -> None:
    accounts = kamino.load_accounts()
    assert accounts["market_pubkey"] == "7u3HeHxYDLhnCoErrtycNokbQYbWGzLs6JSDqGAv5PfF"
    assert "USDC" in accounts["reserves"]


def test_load_accounts_missing_file(tmp_path: Path) -> None:
    accounts = kamino.load_accounts(tmp_path / "missing.json")
    assert accounts["market_pubkey"] == kamino.DEFAULT_MARKET_PUBKEY


def test_account_resolution_to_dict() -> None:
    res = kamino.AccountResolution(
        market_pubkey=kamino.DEFAULT_MARKET_PUBKEY,
        reserve_pubkey=kamino.DEFAULT_USDC_RESERVE,
        program_id=kamino.KLEND_PROGRAM,
        slot=100,
        lamports=5000,
        data_len=8616,
        executable=True,
        owner=kamino.KLEND_PROGRAM,
    )
    d = res.to_dict()
    assert d["slot"] == 100
    assert d["data_len"] == 8616


def test_resolve_market_requires_rpc() -> None:
    with pytest.raises(RuntimeError, match="rpc_url_required"):
        kamino.resolve_market(None, "")


def test_resolve_market_rpc_error() -> None:
    with patch(
        "night_shift_security.native.kamino.get_account_info",
        side_effect=RuntimeError("rpc_url_unreachable"),
    ):
        with pytest.raises(RuntimeError, match="rpc_url_unreachable"):
            kamino.resolve_market(None, "https://rpc.example.com")


def test_resolve_market_success_mocked() -> None:
    program_value = {"executable": True, "lamports": 1}
    market_value = {"lamports": 100, "owner": kamino.KLEND_PROGRAM, "data": ["", "base64"]}
    reserve_value = {
        "lamports": 200,
        "owner": kamino.KLEND_PROGRAM,
        "data": ["AAAA", "base64"],
    }

    def fake_info(pubkey: str, rpc_url: str) -> dict:
        if pubkey == kamino.KLEND_PROGRAM:
            return {"value": program_value}
        if pubkey == kamino.DEFAULT_MARKET_PUBKEY:
            return {"value": market_value}
        return {"value": reserve_value}

    with (
        patch("night_shift_security.native.kamino.get_account_info", side_effect=fake_info),
        patch("night_shift_security.native.kamino.get_slot", return_value=999),
    ):
        result = kamino.resolve_market(None, "https://rpc.example.com")
        assert result.slot == 999
        assert result.executable is True


def test_no_fixture_markers_in_module() -> None:
    source = Path(kamino.__file__).read_text()
    assert "HARNESS_MODE:fixture" not in source
    assert "0x00CAFE" not in source


def test_discriminators_align_with_klend_v2_names() -> None:
    assert "borrow_obligation_liquidity_v2" in kamino.discriminators()
    assert "refresh_reserve" in kamino.discriminators()


@pytest.mark.skipif(
    not os.environ.get("SOLANA_MAINNET_RPC_URL"),
    reason="SOLANA_MAINNET_RPC_URL not set",
)
def test_resolve_market_live_smoke() -> None:
    rpc = os.environ["SOLANA_MAINNET_RPC_URL"]
    result = kamino.resolve_market(None, rpc)
    assert result.executable is True
    assert result.data_len > 0


def test_program_id_matches_lib_rs_declare_id() -> None:
    lib = kamino.DEFAULT_KLEND_REPO / "programs" / "klend" / "src" / "lib.rs"
    if lib.is_file():
        text = lib.read_text()
        assert kamino.KLEND_PROGRAM in text
    else:
        assert kamino.KLEND_PROGRAM.startswith("KLend")