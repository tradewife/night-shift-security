"""Rank sibling pools / clone deployments for post-PoC TVS maximization."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from night_shift_security.operator.foundry_tools import ToolResult, run_cast_call

_BALANCE_SIG = "balanceOf(address)(uint256)"
_TOTAL_SUPPLY_SIG = "totalSupply()(uint256)"


@dataclass
class PoolCandidate:
    address: str
    label: str
    chain: str
    metric: str
    metric_value: int
    rank_score: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _parse_uint(raw: str) -> int:
    text = raw.strip()
    if not text:
        return 0
    if text.startswith("0x"):
        return int(text, 16)
    return int(text)


def _metric_from_call(result: ToolResult) -> int:
    if not result.success:
        return 0
    return _parse_uint(result.parsed.get("result", result.stdout))


def rank_sibling_pools(
    *,
    base_pool: str,
    siblings: list[dict[str, Any]],
    holder: str | None = None,
    rpc_url: str | None = None,
    cast_fn: Callable[..., ToolResult] | None = None,
) -> dict[str, Any]:
    """
    Score clone/sibling pool addresses by on-fork liquidity proxy.

    Each sibling dict: {address, label?, chain?, metric?}
    metric: `balance` (default, uses holder) or `total_supply`.
    """
    cast = cast_fn or run_cast_call
    holder_addr = holder or base_pool
    candidates: list[PoolCandidate] = []

    for entry in siblings:
        addr = str(entry.get("address", "")).strip()
        if not addr:
            continue
        metric = str(entry.get("metric", "balance")).lower()
        if metric == "total_supply":
            res = cast(to=addr, signature=_TOTAL_SUPPLY_SIG, rpc_url=rpc_url)
            value = _metric_from_call(res)
            score = float(value)
        else:
            res = cast(
                to=addr,
                signature=_BALANCE_SIG,
                args=[holder_addr],
                rpc_url=rpc_url,
            )
            value = _metric_from_call(res)
            score = float(value)

        candidates.append(
            PoolCandidate(
                address=addr,
                label=str(entry.get("label", addr[:10])),
                chain=str(entry.get("chain", "evm")),
                metric=metric,
                metric_value=value,
                rank_score=score,
            )
        )

    candidates.sort(key=lambda c: -c.rank_score)
    return {
        "base_pool": base_pool,
        "holder": holder_addr,
        "candidate_count": len(candidates),
        "ranked": [c.to_dict() for c in candidates],
        "top": candidates[0].to_dict() if candidates else None,
    }


def load_sibling_registry(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    data = json.loads(path.read_text())
    if isinstance(data, list):
        return data
    return list(data.get("siblings", data.get("pools", [])))


def sweep_clone_addresses(
    text: str,
    *,
    chain: str = "evm",
) -> list[dict[str, str]]:
    """Extract EVM 0x… or Solana base58 addresses from free-form text."""
    evm = re.findall(r"0x[a-fA-F0-9]{40}", text)
    sol = re.findall(r"[1-9A-HJ-NP-Za-km-z]{32,44}", text)
    out: list[dict[str, str]] = []
    for addr in evm:
        out.append({"address": addr, "chain": "evm", "label": "extracted"})
    for addr in sol:
        if len(addr) >= 32:
            out.append({"address": addr, "chain": "solana", "label": "extracted"})
    return out