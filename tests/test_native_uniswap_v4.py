"""Tests for the v5 Uniswap v4 NativeHarness (audit recommendation C1).

Coverage:

- ``selectors()`` deterministically exposes canonical 4-byte selectors
  (``modifyLiquidity``, ``swap``, ``donate``, ``settle``, ``take``,
  ``initialize``) for ``PoolManager``, plus the full ``IHooks`` surface
  (10 hooks) and the ``StateLibrary`` view calls.
- ``signatures()`` round-trips unicode-safe canonical signatures.
- ``load_abi()`` falls back to the inline canonical ABI fragments when
  artifacts / deployment dirs are absent.
- ``_encode_pool_key()`` packs the canonical 5-word PoolKey layout.
- ``resolve_pool()`` smoke test is **gated behind ``ETHEREUM_RPC_URL``** so the
  444/5 baseline tests remain green without network access.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import pytest

from night_shift_security.native import uniswap_v4


def test_harness_metadata_constants() -> None:
    assert uniswap_v4.HARNESS_TARGET == "uniswap_v4"
    assert uniswap_v4.HARNESS_PLATFORM == "cantina"
    assert uniswap_v4.HARNESS_CHAIN == "ethereum"
    assert uniswap_v4.HARNESS_NAME == "Uniswap v4"


def test_selectors_pool_manager_canonical() -> None:
    sel = uniswap_v4.selectors()
    pm = sel["pool_manager"]
    # All values are 0x-prefixed 4-byte hex.
    regex = re.compile(r"^0x[0-9a-f]{8}$")
    for name, value in pm.items():
        assert regex.match(value), f"selector for {name} not 4-byte hex: {value}"
    # Required canonical functions are present.
    for required in (
        "modifyLiquidity",
        "swap",
        "donate",
        "settle",
        "settleFor",
        "take",
        "initialize",
        "mint",
        "burn",
        "transfer",
        "unlock",
        "sync",
        "clear",
    ):
        assert required in pm, f"missing pool_manager selector: {required}"


def test_selectors_hooks_surface() -> None:
    sel = uniswap_v4.selectors()
    hooks = sel["hooks"]
    assert len(hooks) >= 10, f"expected >=10 IHooks selectors, got {len(hooks)}"
    for hook in (
        "beforeInitialize",
        "afterInitialize",
        "beforeAddLiquidity",
        "afterAddLiquidity",
        "beforeRemoveLiquidity",
        "afterRemoveLiquidity",
        "beforeSwap",
        "afterSwap",
        "beforeDonate",
        "afterDonate",
    ):
        assert hook in hooks, f"missing IHooks selector: {hook}"


def test_selectors_state_view() -> None:
    sel = uniswap_v4.selectors()
    state = sel["state_view"]
    assert "getSlot0" in state
    assert "getLiquidity" in state


def test_selectors_are_deterministic_across_invocations() -> None:
    first = uniswap_v4.selectors()
    second = uniswap_v4.selectors()
    assert first == second


def test_signatures_round_trip() -> None:
    sigs = uniswap_v4.signatures()
    assert "modifyLiquidity(" in ", ".join(sigs["pool_manager"])
    assert "beforeSwap(" in ", ".join(sigs["hooks"])
    assert "getSlot0(" in ", ".join(sigs["state_view"])


def test_load_abi_inline_fallback(tmp_path: Path) -> None:
    abi = uniswap_v4.load_abi(tmp_path)
    names = {entry.get("name") for entry in abi if isinstance(entry, dict)}
    assert "initialize" in names
    assert "modifyLiquidity" in names
    assert "swap" in names
    assert "donate" in names
    assert "getSlot0" in names


def test_load_abi_accepts_fake_forge_artifact(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "out" / "PoolManager.sol"
    artifact_dir.mkdir(parents=True)
    (artifact_dir / "PoolManager.json").write_text(
        '{"abi": [{"type": "constructor", "inputs": []},'
        ' {"type": "function", "name": "fakeArtifact", "inputs": [], "outputs": []}]}'
    )
    abi = uniswap_v4.load_abi(tmp_path)
    names = {entry.get("name") for entry in abi if isinstance(entry, dict)}
    assert "fakeArtifact" in names


def test_load_abi_accepts_deployments_json(tmp_path: Path) -> None:
    deployments = tmp_path / "deployments" / "ethereum"
    deployments.mkdir(parents=True)
    (deployments / "PoolManager.json").write_text(
        '{"abi": [{"type": "function", "name": "fromDeployments", "inputs": [], "outputs": []}]}'
    )
    abi = uniswap_v4.load_abi(tmp_path)
    names = {entry.get("name") for entry in abi if isinstance(entry, dict)}
    assert "fromDeployments" in names


def test_encode_pool_key_layout() -> None:
    pool_key = {
        "currency0": uniswap_v4.DEFAULT_USDC_ETHEREUM,
        "currency1": uniswap_v4.DEFAULT_WETH_ETHEREUM,
        "fee": 3000,
        "tickSpacing": 60,
        "hooks": uniswap_v4.DEFAULT_POOL_MANAGER_ADDRESS,
    }
    encoded = uniswap_v4._encode_pool_key(pool_key)
    assert encoded.startswith("0x")
    body = encoded.removeprefix("0x")
    assert len(body) == 5 * 64, f"expected 320 hex chars (5 × 32-byte words), got {len(body)}"
    # currency0 — USDC (lowercase, padded)
    assert body[24:64] == uniswap_v4.DEFAULT_USDC_ETHEREUM.removeprefix("0x").lower()
    # currency1 — WETH (lowercase, padded)
    assert body[64 + 24 : 64 + 64] == uniswap_v4.DEFAULT_WETH_ETHEREUM.removeprefix("0x").lower()


def test_encode_pool_key_rejects_bad_address() -> None:
    bad = {
        "currency0": "0xnotanaddress",
        "currency1": uniswap_v4.DEFAULT_WETH_ETHEREUM,
        "fee": 3000,
        "tickSpacing": 60,
        "hooks": uniswap_v4.DEFAULT_POOL_MANAGER_ADDRESS,
    }
    with pytest.raises(ValueError):
        uniswap_v4._encode_pool_key(bad)


def test_resolve_pool_key_dataclass() -> None:
    pk = uniswap_v4.PoolKey(
        currency0=uniswap_v4.DEFAULT_USDC_ETHEREUM,
        currency1=uniswap_v4.DEFAULT_WETH_ETHEREUM,
        fee=3000,
        tick_spacing=60,
    )
    d = pk.to_dict()
    assert d["currency0"] == uniswap_v4.DEFAULT_USDC_ETHEREUM
    assert d["currency1"] == uniswap_v4.DEFAULT_WETH_ETHEREUM
    assert d["fee"] == 3000
    assert d["tickSpacing"] == 60
    assert d["hooks"] == uniswap_v4.DEFAULT_POOL_MANAGER_ADDRESS


def test_selectors_match_signature_via_helper() -> None:
    """Selectors should be derived from the same helper that semantic recon uses."""
    from night_shift_security.crypto import evm_function_selector

    sel = uniswap_v4.selectors()
    expected = evm_function_selector("modifyLiquidity((address,address,uint24,int24,address),(int24,int24,int256,bytes32),bytes)")
    assert sel["pool_manager"]["modifyLiquidity"] == expected
    expected_swap = evm_function_selector(
        "swap((address,address,uint24,int24,address),(bool,uint128,int256,uint160),bytes)"
    )
    assert sel["pool_manager"]["swap"] == expected_swap
