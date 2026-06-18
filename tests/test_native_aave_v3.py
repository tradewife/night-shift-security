"""Tests for the Aave v3 native harness."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from night_shift_security.native.aave_v3 import (
    DEFAULT_POOL,
    DEFAULT_POOL_ADDRESSES_PROVIDER,
    HARNESS_CHAIN,
    HARNESS_NAME,
    HARNESS_PLATFORM,
    HARNESS_TARGET,
    AAVE_POOL_FUNCTIONS,
    ReserveResolution,
    _AAVE_VIEW_FUNCTIONS,
    _AAVE_PROVIDER_FUNCTIONS,
    eth_call,
    get_code,
    load_abi,
    resolve_pool,
    selectors,
    signatures,
)


# ------------------------------------------------------------------ #
# Harness metadata tests
# ------------------------------------------------------------------ #


def test_harness_metadata():
    assert HARNESS_TARGET == "aave_v3"
    assert HARNESS_PLATFORM == "cantina"
    assert HARNESS_CHAIN == "ethereum"
    assert HARNESS_NAME == "Aave v3"


# ------------------------------------------------------------------ #
# Selector / signature tests
# ------------------------------------------------------------------ #


def test_selectors_returns_expected_keys():
    sels = selectors()
    assert "pool" in sels
    assert "pool_view" in sels
    assert "provider" in sels
    assert isinstance(sels["pool"], dict)
    assert isinstance(sels["pool_view"], dict)
    assert isinstance(sels["provider"], dict)


def test_pool_selectors_count():
    sels = selectors()
    assert len(sels["pool"]) == len(AAVE_POOL_FUNCTIONS)


def test_supply_selector_is_10_chars():
    sels = selectors()
    supply_sel = sels["pool"]["supply"]
    assert supply_sel.startswith("0x")
    assert len(supply_sel) == 10


def test_supply_selector_matches_keccak():
    from night_shift_security.crypto import keccak256 as _k256

    sels = selectors()
    sig = "supply(address,uint256,address,uint16)"
    expected = "0x" + _k256(sig.encode()).hex()[:8]
    assert sels["pool"]["supply"] == expected


def test_get_reserve_data_selector_matches_keccak():
    from night_shift_security.crypto import keccak256 as _k256

    sels = selectors()
    sig = "getReserveData(address)"
    expected = "0x" + _k256(sig.encode()).hex()[:8]
    assert sels["pool_view"]["getReserveData"] == expected


def test_signatures_match_selectors():
    sigs = signatures()
    sels = selectors()
    assert set(sigs["pool"]) > set()
    for name in sels["pool"]:
        assert any(name in sig for sig in sigs["pool"])


def test_provider_selectors():
    sels = selectors()
    assert "getPool" in sels["provider"]
    assert "getPoolDataProvider" in sels["provider"]


def test_all_selectors_are_10_chars():
    sels = selectors()
    for category, func_map in sels.items():
        for name, sel in func_map.items():
            assert sel.startswith("0x"), f"{category}.{name}: {sel}"
            assert len(sel) == 10, f"{category}.{name}: {sel}"


# ------------------------------------------------------------------ #
# Canonical addresses
# ------------------------------------------------------------------ #


def test_pool_address_is_42_chars():
    assert len(DEFAULT_POOL) == 42
    assert DEFAULT_POOL.startswith("0x")


def test_pool_addresses_provider_is_42_chars():
    assert len(DEFAULT_POOL_ADDRESSES_PROVIDER) == 42
    assert DEFAULT_POOL_ADDRESSES_PROVIDER.startswith("0x")


# ------------------------------------------------------------------ #
# ABI loading
# ------------------------------------------------------------------ #


def test_load_abi_returns_non_empty_list(tmp_path):
    abi = load_abi(tmp_path)
    assert isinstance(abi, list)
    assert len(abi) > 0


def test_load_abi_has_supply_function():
    abi = load_abi(Path("/nonexistent"))
    names = [entry.get("name") for entry in abi if isinstance(entry, dict)]
    assert "supply" in names
    assert "borrow" in names
    assert "repay" in names
    assert "withdraw" in names
    assert "flashLoanSimple" in names


def test_load_abi_from_artifact(tmp_path):
    artifact_dir = (
        tmp_path / "artifacts" / "contracts" / "protocol" / "lendingpool"
        / "LendingPool.sol"
    )
    artifact_dir.mkdir(parents=True)
    abi_entry = {
        "type": "function",
        "name": "supply",
        "inputs": [],
        "outputs": [],
        "stateMutability": "nonpayable",
    }
    artifact_file = artifact_dir / "LendingPool.json"
    artifact_file.write_text(json.dumps({"abi": [abi_entry]}))
    result = load_abi(tmp_path)
    assert len(result) == 1
    assert result[0]["name"] == "supply"


# ------------------------------------------------------------------ #
# resolve_pool (mocked RPC)
# ------------------------------------------------------------------ #


def test_resolve_pool_no_code():
    with patch(
        "night_shift_security.native.aave_v3.get_code",
        return_value="0x",
    ):
        with pytest.raises(RuntimeError, match="rpc_no_code_at"):
            resolve_pool(
                "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                "https://rpc.example.com",
            )


def test_resolve_pool_short_payload():
    with (
        patch(
            "night_shift_security.native.aave_v3.get_code",
            return_value="0xabcdef",
        ),
        patch(
            "night_shift_security.native.aave_v3.eth_call",
            return_value="0x1234",
        ),
    ):
        with pytest.raises(RuntimeError, match="short_payload"):
            resolve_pool(
                "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                "https://rpc.example.com",
            )


def test_resolve_pool_success():
    # getReserveData returns 15 × 32-byte words = 960 hex chars + "0x" = 962 chars
    mock_response = "0x" + "0" * 960
    with (
        patch(
            "night_shift_security.native.aave_v3.get_code",
            return_value="0xabcdef",
        ),
        patch(
            "night_shift_security.native.aave_v3.eth_call",
            return_value=mock_response,
        ),
    ):
        result = resolve_pool(
            "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "https://rpc.example.com",
        )
        assert isinstance(result, ReserveResolution)
        assert result.pool_address == DEFAULT_POOL
        assert result.current_liquidity_rate == 0
        assert result.block == -1


def test_reserve_resolution_to_dict():
    rr = ReserveResolution(
        asset="0x" + "a" * 40,
        pool_address="0x" + "b" * 40,
        a_token_address="0x" + "c" * 40,
        variable_debt_token_address="0x" + "d" * 40,
        stable_debt_token_address="0x" + "e" * 40,
        interest_rate_strategy_address="0x" + "f" * 40,
        current_liquidity_rate=42,
        current_variable_borrow_rate=100,
        current_stable_borrow_rate=200,
        liquidity_index=1000000,
        variable_borrow_index=1000000,
        last_update_timestamp=1700000000,
        block=20000000,
    )
    d = rr.to_dict()
    assert d["asset"] == "0x" + "a" * 40
    assert d["current_liquidity_rate"] == 42
    assert d["block"] == 20000000
