"""Tests for the Morpho Blue native harness."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from night_shift_security.native.morpho_blue import (
    DEFAULT_MORPHO_BLUE_MAINNET,
    MarketParams,
    MarketResolution,
    _market_id,
    selectors,
    signatures,
    load_abi,
    resolve_market,
)


def _keccak256(data: bytes) -> bytes:
    """Pure Python keccak-256 (same as the crypto module)."""
    from night_shift_security.crypto import keccak256 as _k256

    return _k256(data)


# ------------------------------------------------------------------ #
# Selector / signature tests
# ------------------------------------------------------------------ #


def test_selectors_returns_expected_keys():
    sels = selectors()
    assert "morpho" in sels
    assert "morpho_view" in sels
    assert isinstance(sels["morpho"], dict)
    assert isinstance(sels["morpho_view"], dict)


def test_supply_selector_is_10_chars():
    sels = selectors()
    supply_sel = sels["morpho"]["supply"]
    assert supply_sel.startswith("0x")
    assert len(supply_sel) == 10


def test_borrow_selector_matches_keccak():
    from night_shift_security.crypto import keccak256 as _k256

    sels = selectors()
    sig = "borrow((address,address,address,address,uint256),uint256,uint256,address,address)"
    expected = "0x" + _k256(sig.encode()).hex()[:8]
    borrow_sel = sels["morpho"]["borrow"]
    assert borrow_sel == expected


def test_signatures_match_selectors():
    sigs = signatures()
    sels = selectors()
    assert set(sigs["morpho"]) > set()
    for name in sels["morpho"]:
        assert any(name in sig for sig in sigs["morpho"])


def test_view_selector_is_10_chars():
    sels = selectors()
    owner_sel = sels["morpho_view"]["owner"]
    assert owner_sel.startswith("0x")
    assert len(owner_sel) == 10


# ------------------------------------------------------------------ #
# Market ID computation
# ------------------------------------------------------------------ #


def test_market_id_returns_66_chars():
    mp = {
        "loanToken": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "collateralToken": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "oracle": "0x0000000000000000000000000000000000000001",
        "irm": "0x0000000000000000000000000000000000000002",
        "lltv": 850000000000000000,
    }
    mid = _market_id(mp)
    assert mid.startswith("0x")
    assert len(mid) == 66


def test_market_id_deterministic():
    mp = {
        "loanToken": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "collateralToken": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "oracle": "0x0000000000000000000000000000000000000001",
        "irm": "0x0000000000000000000000000000000000000002",
        "lltv": 850000000000000000,
    }
    assert _market_id(mp) == _market_id(mp)


def test_market_id_changes_with_params():
    mp1 = {
        "loanToken": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "collateralToken": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "oracle": "0x0000000000000000000000000000000000000001",
        "irm": "0x0000000000000000000000000000000000000002",
        "lltv": 850000000000000000,
    }
    mp2 = dict(mp1)
    mp2["lltv"] = 750000000000000000
    assert _market_id(mp1) != _market_id(mp2)


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
    assert "liquidate" in names
    assert "flashLoan" in names


def test_load_abi_from_artifact(tmp_path):
    artifact_dir = tmp_path / "out" / "Morpho.sol"
    artifact_dir.mkdir(parents=True)
    abi_entry = {
        "type": "function",
        "name": "supply",
        "inputs": [],
        "outputs": [],
        "stateMutability": "nonpayable",
    }
    artifact_file = artifact_dir / "Morpho.json"
    artifact_file.write_text(json.dumps({"abi": [abi_entry]}))
    result = load_abi(tmp_path)
    assert len(result) == 1
    assert result[0]["name"] == "supply"


# ------------------------------------------------------------------ #
# resolve_market (mocked RPC)
# ------------------------------------------------------------------ #


def test_resolve_market_rpc_error():
    with patch(
        "night_shift_security.native.morpho_blue.get_code",
        side_effect=RuntimeError("rpc_no_code_at"),
    ):
        with pytest.raises(RuntimeError, match="rpc_no_code_at"):
            resolve_market(
                {
                    "loanToken": "0x" + "0" * 40,
                    "collateralToken": "0x" + "0" * 40,
                    "oracle": "0x" + "0" * 40,
                    "irm": "0x" + "0" * 40,
                    "lltv": 0,
                },
                "https://rpc.example.com",
            )


def test_resolve_market_short_payload():
    with (
        patch(
            "night_shift_security.native.morpho_blue.get_code",
            return_value="0xabcdef",
        ),
        patch(
            "night_shift_security.native.morpho_blue.eth_call",
            return_value="0x1234",
        ),
    ):
        with pytest.raises(RuntimeError, match="short_payload"):
            resolve_market(
                {
                    "loanToken": "0x" + "0" * 40,
                    "collateralToken": "0x" + "0" * 40,
                    "oracle": "0x" + "0" * 40,
                    "irm": "0x" + "0" * 40,
                    "lltv": 0,
                },
                "https://rpc.example.com",
            )


def test_resolve_market_success():
    # Build a valid 6-word (384 hex chars + "0x" = 386 chars) response
    mock_response = "0x" + "0" * 384
    with (
        patch(
            "night_shift_security.native.morpho_blue.get_code",
            return_value="0xabcdef",
        ),
        patch(
            "night_shift_security.native.morpho_blue.eth_call",
            return_value=mock_response,
        ),
    ):
        result = resolve_market(
            {
                "loanToken": "0x" + "1" * 40,
                "collateralToken": "0x" + "2" * 40,
                "oracle": "0x" + "3" * 40,
                "irm": "0x" + "4" * 40,
                "lltv": 850000000000000000,
            },
            "https://rpc.example.com",
        )
        assert isinstance(result, MarketResolution)
        assert result.market_id.startswith("0x")
        assert len(result.market_id) == 66
        assert result.total_supply_assets == 0
        assert result.block == -1


def test_market_params_to_dict():
    mp = MarketParams(
        loan_token="0x" + "1" * 40,
        collateral_token="0x" + "2" * 40,
        oracle="0x" + "3" * 40,
        irm="0x" + "4" * 40,
        lltv=850000000000000000,
    )
    d = mp.to_dict()
    assert d["loanToken"] == "0x" + "1" * 40
    assert d["lltv"] == 850000000000000000


def test_market_resolution_to_dict():
    mr = MarketResolution(
        market_id="0x" + "a" * 64,
        total_supply_assets=1000,
        total_supply_shares=900,
        total_borrow_assets=500,
        total_borrow_shares=450,
        last_update=1000000,
        fee=10000,
        block=20000000,
        morpho_address="0x" + "b" * 40,
    )
    d = mr.to_dict()
    assert d["market_id"] == "0x" + "a" * 64
    assert d["total_supply_assets"] == 1000
    assert d["fee"] == 10000
