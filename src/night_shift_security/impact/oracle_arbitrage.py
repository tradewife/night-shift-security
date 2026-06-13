"""Compare internal oracle price vs DEX spot on a fork for impact sizing."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Callable

from night_shift_security.operator.foundry_tools import ToolResult, run_cast_call

_HEX_UINT = re.compile(r"0x[0-9a-fA-F]+")
_DEFAULT_DIVERGENCE_THRESHOLD_PCT = 2.0


@dataclass
class OracleArbitrageResult:
    oracle_price: float
    dex_price: float
    divergence_pct: float
    exploitable: bool
    threshold_pct: float
    oracle_call: dict[str, Any]
    dex_call: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _parse_uint256(raw: str) -> int:
    text = raw.strip()
    if not text:
        return 0
    if text.startswith("0x"):
        return int(text, 16)
    return int(text)


def _price_from_uint(value: int, decimals: int) -> float:
    if decimals <= 0:
        return float(value)
    return value / (10**decimals)


def _uniswap_v2_spot_price(
    reserve0: int,
    reserve1: int,
    *,
    token0_decimals: int,
    token1_decimals: int,
    quote_is_token1: bool,
) -> float:
    if reserve0 <= 0 or reserve1 <= 0:
        return 0.0
    r0 = _price_from_uint(reserve0, token0_decimals)
    r1 = _price_from_uint(reserve1, token1_decimals)
    if quote_is_token1:
        return r1 / r0
    return r0 / r1


def compare_oracle_vs_dex(
    *,
    oracle: str,
    price_sig: str,
    pair: str,
    rpc_url: str | None = None,
    token0_decimals: int = 18,
    token1_decimals: int = 6,
    quote_is_token1: bool = True,
    divergence_threshold_pct: float = _DEFAULT_DIVERGENCE_THRESHOLD_PCT,
    cast_fn: Callable[..., ToolResult] | None = None,
) -> OracleArbitrageResult:
    """
    Read oracle getter and Uniswap-V2-style getReserves(); return divergence.

    `price_sig` example: `latestAnswer()(int256)` or `getPrice()(uint256)`.
    """
    cast = cast_fn or run_cast_call

    oracle_res = cast(to=oracle, signature=price_sig, rpc_url=rpc_url)
    if not oracle_res.success:
        raise RuntimeError(f"oracle call failed: {oracle_res.stderr}")

    oracle_raw = _parse_uint256(oracle_res.parsed.get("result", oracle_res.stdout))
    oracle_price = _price_from_uint(abs(oracle_raw), token1_decimals)

    reserves_res = cast(
        to=pair,
        signature="getReserves()(uint112,uint112,uint32)",
        rpc_url=rpc_url,
    )
    if not reserves_res.success:
        raise RuntimeError(f"pair reserves call failed: {reserves_res.stderr}")

    parts = [p.strip() for p in reserves_res.parsed.get("result", reserves_res.stdout).split()]
    nums = [_parse_uint256(p) for p in parts if _HEX_UINT.match(p) or p.isdigit()]
    if len(nums) < 2:
        raise RuntimeError(f"could not parse reserves: {reserves_res.stdout}")

    dex_price = _uniswap_v2_spot_price(
        nums[0],
        nums[1],
        token0_decimals=token0_decimals,
        token1_decimals=token1_decimals,
        quote_is_token1=quote_is_token1,
    )
    if dex_price <= 0 or oracle_price <= 0:
        divergence = 0.0
    else:
        divergence = abs(oracle_price - dex_price) / dex_price * 100.0

    return OracleArbitrageResult(
        oracle_price=oracle_price,
        dex_price=dex_price,
        divergence_pct=round(divergence, 4),
        exploitable=divergence >= divergence_threshold_pct,
        threshold_pct=divergence_threshold_pct,
        oracle_call=oracle_res.to_dict(),
        dex_call=reserves_res.to_dict(),
    )