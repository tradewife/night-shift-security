"""Tests for Phase D impact tools."""

from __future__ import annotations

from pathlib import Path

import pytest

from night_shift_security.impact.oracle_arbitrage import compare_oracle_vs_dex
from night_shift_security.impact.tvs_maximization import (
    load_sibling_registry,
    rank_sibling_pools,
    sweep_clone_addresses,
)
from night_shift_security.operator.foundry_tools import ToolResult


def _cast_result(value: int) -> ToolResult:
    return ToolResult(
        success=True,
        command=[],
        stdout=hex(value),
        stderr="",
        exit_code=0,
        parsed={"result": hex(value)},
    )


def _reserves_result(r0: int, r1: int) -> ToolResult:
    return ToolResult(
        success=True,
        command=[],
        stdout=f"{hex(r0)} {hex(r1)} 0x1",
        stderr="",
        exit_code=0,
        parsed={"result": f"{hex(r0)} {hex(r1)} 0x1"},
    )


def test_compare_oracle_vs_dex_detects_divergence():
    calls: list[tuple[str, str]] = []

    def fake_cast(*, to: str, signature: str, **kwargs):
        calls.append((to, signature))
        if "getReserves" in signature:
            # 1000 WETH : 3_000_000 USDC → ~3000 USDC/ETH
            return _reserves_result(10**21, 3_000_000 * 10**6)
        # oracle reports 3300 USDC/ETH (6 decimals)
        return _cast_result(3300 * 10**6)

    result = compare_oracle_vs_dex(
        oracle="0xOracle",
        price_sig="latestAnswer()(int256)",
        pair="0xPair",
        token0_decimals=18,
        token1_decimals=6,
        divergence_threshold_pct=2.0,
        cast_fn=fake_cast,
    )
    assert result.oracle_price == 3300.0
    assert result.dex_price == 3000.0
    assert result.divergence_pct == pytest.approx(10.0, rel=0.01)
    assert result.exploitable is True
    assert len(calls) == 2


def test_rank_sibling_pools_orders_by_metric():
    balances = {"0xA": 100, "0xB": 500, "0xC": 200}

    def fake_cast(*, to: str, signature: str, **kwargs):
        return _cast_result(balances.get(to, 0))

    ranked = rank_sibling_pools(
        base_pool="0xBase",
        siblings=[
            {"address": "0xA", "label": "a"},
            {"address": "0xB", "label": "b"},
            {"address": "0xC", "label": "c", "metric": "total_supply"},
        ],
        holder="0xHolder",
        cast_fn=fake_cast,
    )
    scores = [r["rank_score"] for r in ranked["ranked"]]
    assert scores == sorted(scores, reverse=True)
    assert ranked["top"]["address"] == "0xB"


def test_load_sibling_registry(tmp_path: Path):
    path = tmp_path / "siblings.json"
    path.write_text(
        '{"siblings": [{"address": "0x1", "label": "one"}]}'
    )
    assert len(load_sibling_registry(path)) == 1


def test_sweep_clone_addresses():
    text = "core 0x98f3c9e6E3fAce36bAAd05FE09d375Ef1464288B on worm2ZoG2kUd4vFXhvjh93UUH596ayRfgQ2MgjNMTth"
    found = sweep_clone_addresses(text)
    chains = {f["chain"] for f in found}
    assert "evm" in chains
    assert "solana" in chains