"""Smoke tests for the Ethena NativeHarness.

Mirrors `tests/test_native_reserve.py`. Includes:
- Selector testing vs the project's pure-Python keccak.
- Default-address validation against verified mainnet deployment.
- Inline-ABI sanity checks (no fabrication).
- Mocked RPC reads via monkeypatch (no live calls).

Run with: .venv/bin/python -m pytest tests/test_native_ethena.py -q
"""

from __future__ import annotations

from typing import Any

import pytest

from night_shift_security.crypto import evm_function_selector
import night_shift_security.native.ethena as ethena
from night_shift_security.native.ethena import (
    DEFAULT_MINTING_MAINNET,
    DEFAULT_USDE_MAINNET,
    selectors,
)


def _sel(sig: str) -> str:
    return evm_function_selector(sig)


def test_addresses_lowercase_42_chars() -> None:
    assert DEFAULT_USDE_MAINNET.lower() == DEFAULT_USDE_MAINNET
    assert DEFAULT_MINTING_MAINNET.lower() == DEFAULT_MINTING_MAINNET
    assert len(DEFAULT_USDE_MAINNET) == 42
    assert len(DEFAULT_MINTING_MAINNET) == 42


def test_addresses_match_docs_verified_canonical() -> None:
    # Verified on 2026-06-20 via public mainnet RPC (code >1KB at both).
    assert DEFAULT_USDE_MAINNET == "0x4c9edd5852cd905f086c759e8383e09bff1e68b3"
    assert DEFAULT_MINTING_MAINNET == "0x2cc440b721d2cafd6d64908d6d8c4acc57f8afc3"
    # Distinct contracts.
    assert DEFAULT_USDE_MAINNET != DEFAULT_MINTING_MAINNET


def test_selectors_returns_both_groups() -> None:
    sel = selectors()
    assert "ethena" in sel
    assert "ethena_view" in sel
    assert "mint" in sel["ethena"]
    assert "redeem" in sel["ethena"]
    assert "disableMintRedeem" in sel["ethena"]
    assert "totalSupply" in sel["ethena_view"]
    assert "maxMintPerBlock" in sel["ethena_view"]


def test_mint_selector_matches_keccak() -> None:
    # Real canonical mint signature from EthenaMinting.sol:179
    expected = _sel("mint((uint8,address,address,address,uint256,uint256,uint256),(address[],uint256[]),(uint8,bytes32,bytes32))")
    assert selectors()["ethena"]["mint"] == expected


def test_redeem_selector_matches_keccak() -> None:
    expected = _sel("redeem((uint8,address,address,address,uint256,uint256,uint256),(uint8,bytes32,bytes32))")
    assert selectors()["ethena"]["redeem"] == expected


def test_totalsupply_selector_matches_keccak() -> None:
    # 0x18160ddd is the canonical totalSupply selector.
    assert _sel("totalSupply()") == "0x18160ddd"
    assert selectors()["ethena_view"]["totalSupply"] == "0x18160ddd"


def test_setmaxmint_selector_matches_keccak() -> None:
    expected = _sel("setMaxMintPerBlock(uint256)")
    assert selectors()["ethena"]["setMaxMintPerBlock"] == expected


def test_program_ids_returns_two_addresses() -> None:
    pids = ethena.program_ids()
    assert pids["usde"] == DEFAULT_USDE_MAINNET
    assert pids["minting"] == DEFAULT_MINTING_MAINNET


def test_load_abi_inline_returns_nonempty_list() -> None:
    abi = ethena._inline_abi()
    assert isinstance(abi, list)
    assert len(abi) >= 2
    assert all(isinstance(e, dict) for e in abi)
    # Must include totalSupply.
    fnames = {e.get("name") for e in abi if e.get("type") == "function"}
    assert "totalSupply" in fnames
    assert "mintedPerBlock" in fnames


def test_load_abi_falls_back_to_inline_when_no_repo(tmp_path: Any) -> None:
    abi = ethena.load_abi(tmp_path)  # no repo here, so falls back
    assert isinstance(abi, list)
    assert len(abi) >= 2


def test_request_modules_exposed() -> None:
    # All public surface items are reachable.
    assert hasattr(ethena, "resolve_usde_total_supply")
    assert hasattr(ethena, "resolve_minting_caps")
    assert hasattr(ethena, "selectors")
    assert hasattr(ethena, "load_abi")


def test_normalize_block_preserves_latest_string() -> None:
    assert ethena._normalize_block("latest") == "latest"


def test_normalize_block_coerces_int_to_hex() -> None:
    n = ethena._normalize_block(123)
    assert isinstance(n, str) and n.startswith("0x")
    assert int(n, 16) == 123


def test_normalize_block_negative_int_becomes_latest() -> None:
    assert ethena._normalize_block(-1) == "latest"


def test_read_uint_zero() -> None:
    # 32-byte zero
    zero = "0x" + "00" * 32
    assert ethena._read_uint(zero, 0) == 0


def test_read_uint_decimal_value() -> None:
    # 32-byte = 1000000000 (1e9)
    one_g = "0x000000000000000000000000000000000000000000000000000000003b9aca00"
    assert ethena._read_uint(one_g, 0) == 1_000_000_000


def test_read_uint_short_payload_raises() -> None:
    with pytest.raises(RuntimeError):
        ethena._read_uint("0x1234", 0)


def test_resolve_usde_no_code_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ethena, "get_code", lambda *args, **kwargs: "0x")
    with pytest.raises(RuntimeError):
        ethena.resolve_usde_total_supply("https://rpc.invalid")


def test_resolve_usde_decodes_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    """resolve_usde_total_supply parses a 32-byte 1e18 integer from a mocked eth_call."""
    one_e18 = 1_000_000_000_000_000_000
    payload = "0x" + format(one_e18, "x").zfill(64)

    def fake_get_code(addr, rpc, block):
        return "0x608060405234801561001057600080fd5b50"

    def fake_eth_call(addr, data, rpc, block):
        return payload

    monkeypatch.setattr(ethena, "get_code", fake_get_code)
    monkeypatch.setattr(ethena, "eth_call", fake_eth_call)

    out = ethena.resolve_usde_total_supply("https://rpc.invalid", block="latest")
    assert out.total_supply == one_e18
    assert out.usde_address == DEFAULT_USDE_MAINNET


def test_resolve_minting_caps_decodes_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    """resolve_minting_caps parses both caps from a mocked eth_call."""
    cap_value = 2 * 10**25
    cap_payload = "0x" + format(cap_value, "x").zfill(64)

    def fake_get_code(addr, rpc, block):
        return "0x608060405234801561001057600080fd5b50"

    def fake_eth_call(addr, data, rpc, block):
        # Both selectors return the same payload for this mock.
        return cap_payload

    monkeypatch.setattr(ethena, "get_code", fake_get_code)
    monkeypatch.setattr(ethena, "eth_call", fake_eth_call)

    out = ethena.resolve_minting_caps("https://rpc.invalid", block="latest")
    assert out.max_mint_per_block == cap_value
    assert out.max_redeem_per_block == cap_value
    assert out.minting_address == DEFAULT_MINTING_MAINNET


def test_harness_metadata() -> None:
    assert ethena.HARNESS_TARGET == "ethena"
    assert ethena.HARNESS_PLATFORM == "immunefi"
    assert ethena.HARNESS_CHAIN == "ethereum"
    assert ethena.HARNESS_NAME == "Ethena"
