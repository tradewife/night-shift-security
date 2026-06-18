"""Aave v3 NativeHarness — Pool + PoolAddressesProvider surface (Cantina).

Phase 3 row 2 harness. Mirrors the ``morpho_blue.py`` template. The harness
is read-only: it loads ABI fragments, exposes canonical 4-byte selectors for
the Pool contract, and provides a thin resolver that confirms a deployed
Aave v3 Pool is live on Ethereum mainnet.

Design choices:
- Selectors derive from ``night_shift_security.crypto.evm_function_selector``.
- ABI fragments are sourced from the cloned repo or inline canonical fragments.
- ``resolve_pool`` is best-effort: RPC outage bubbles up as ``RuntimeError``.
- stdlib + urllib only, no new packages.
"""

from __future__ import annotations

import json
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

from night_shift_security.crypto import evm_function_selector

evm_selector = evm_function_selector

# -------------------------------------------------------------------------- #
# Constants — single source of truth for the v5 Aave v3 NativeHarness.
# -------------------------------------------------------------------------- #

HARNESS_TARGET = "aave_v3"
HARNESS_PLATFORM = "cantina"
HARNESS_CHAIN = "ethereum"
HARNESS_NAME = "Aave v3"

# Canonical Aave v3 deployments (Ethereum mainnet).
# https://docs.aave.com/developers/deployed-contracts/v3-mainnet/ethereum-mainnet
DEFAULT_POOL_ADDRESSES_PROVIDER = "0x2f39d218133AFaB8F2B819B1066c7E434Ad94E9e"
DEFAULT_POOL = "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2"

# Canonical Aave v3 Pool external functions (sourced from
# sources/aave_v3/repo/contracts/interfaces/IPool.sol).
AAVE_POOL_FUNCTIONS: list[dict[str, str]] = [
    {
        "name": "supply",
        "signature": "supply(address,uint256,address,uint16)",
        "source": "contracts/interfaces/IPool.sol",
    },
    {
        "name": "borrow",
        "signature": "borrow(address,uint256,uint256,uint16,address)",
        "source": "contracts/interfaces/IPool.sol",
    },
    {
        "name": "repay",
        "signature": "repay(address,uint256,uint256,address)",
        "source": "contracts/interfaces/IPool.sol",
    },
    {
        "name": "withdraw",
        "signature": "withdraw(address,uint256,address)",
        "source": "contracts/interfaces/IPool.sol",
    },
    {
        "name": "flashLoanSimple",
        "signature": "flashLoanSimple(address,address,uint256,bytes,uint16)",
        "source": "contracts/interfaces/IPool.sol",
    },
    {
        "name": "liquidationCall",
        "signature": "liquidationCall(address,address,address,uint256,bool)",
        "source": "contracts/interfaces/IPool.sol",
    },
    {
        "name": "setUserUseReserveAsCollateral",
        "signature": "setUserUseReserveAsCollateral(address,bool)",
        "source": "contracts/interfaces/IPool.sol",
    },
    {
        "name": "swapBorrowRateMode",
        "signature": "swapBorrowRateMode(address,uint256)",
        "source": "contracts/interfaces/IPool.sol",
    },
    {
        "name": "setUserEMode",
        "signature": "setUserEMode(uint8)",
        "source": "contracts/interfaces/IPool.sol",
    },
    {
        "name": "flashLoan",
        "signature": "flashLoan(address,address[],uint256[],uint256[],address,bytes,uint16)",
        "source": "contracts/interfaces/IPool.sol",
    },
]

# View functions (read-only, used for state queries).
_AAVE_VIEW_FUNCTIONS: list[dict[str, str]] = [
    {
        "name": "getReserveData",
        "signature": "getReserveData(address)",
        "source": "contracts/interfaces/IPool.sol",
    },
    {
        "name": "getUserAccountData",
        "signature": "getUserAccountData(address)",
        "source": "contracts/interfaces/IPool.sol",
    },
    {
        "name": "getReservesList",
        "signature": "getReservesList()",
        "source": "contracts/interfaces/IPool.sol",
    },
    {
        "name": "getConfiguration",
        "signature": "getConfiguration(address)",
        "source": "contracts/interfaces/IPool.sol",
    },
    {
        "name": "getUserConfiguration",
        "signature": "getUserConfiguration(address)",
        "source": "contracts/interfaces/IPool.sol",
    },
    {
        "name": "getReserveNormalizedIncome",
        "signature": "getReserveNormalizedIncome(address)",
        "source": "contracts/interfaces/IPool.sol",
    },
    {
        "name": "getReserveNormalizedVariableDebt",
        "signature": "getReserveNormalizedVariableDebt(address)",
        "source": "contracts/interfaces/IPool.sol",
    },
]

# PoolAddressesProvider view functions.
_AAVE_PROVIDER_FUNCTIONS: list[dict[str, str]] = [
    {
        "name": "getPool",
        "signature": "getPool()",
        "source": "contracts/interfaces/IPoolAddressesProvider.sol",
    },
    {
        "name": "getPoolDataProvider",
        "signature": "getPoolDataProvider()",
        "source": "contracts/interfaces/IPoolAddressesProvider.sol",
    },
]


# -------------------------------------------------------------------------- #
# Public harness surface
# -------------------------------------------------------------------------- #


def _selector_map(entries: list[dict[str, str]]) -> "OrderedDict[str, str]":
    out: "OrderedDict[str, str]" = OrderedDict()
    for entry in entries:
        selector = evm_selector(entry["signature"])
        if isinstance(selector, dict):
            selector = selector["value"]
        out[entry["name"]] = selector
    return out


def selectors() -> dict[str, dict[str, str]]:
    """Canonical 4-byte selectors for Aave v3 Pool + PoolAddressesProvider.

    Returns a mapping from category to a name -> ``0x...`` selector dict.

    >>> funcs = selectors()["pool"]
    >>> funcs["supply"].startswith("0x") and len(funcs["supply"]) == 10
    True
    """
    return {
        "pool": _selector_map(AAVE_POOL_FUNCTIONS),
        "pool_view": _selector_map(_AAVE_VIEW_FUNCTIONS),
        "provider": _selector_map(_AAVE_PROVIDER_FUNCTIONS),
    }


def signatures() -> dict[str, list[str]]:
    """Return canonical signatures per category.

    Mostly used for documentation / fixture generation.
    """
    return {
        "pool": [entry["signature"] for entry in AAVE_POOL_FUNCTIONS],
        "pool_view": [entry["signature"] for entry in _AAVE_VIEW_FUNCTIONS],
        "provider": [entry["signature"] for entry in _AAVE_PROVIDER_FUNCTIONS],
    }


def load_abi(repo_path: Path | str) -> list[dict[str, Any]]:
    """Load Aave v3 Pool ABI fragments from the repo.

    Resolution order:
    1. ``artifacts/contracts/protocol/lendingpool/LendingPool.sol/LendingPool.json``
       (Hardhat artifact).
    2. Fallback: synthesised inline ABI fragments for the canonical external
       functions only — never fabricated storage layout.
    """
    repo = Path(repo_path)

    artifact = (
        repo
        / "artifacts"
        / "contracts"
        / "protocol"
        / "lendingpool"
        / "LendingPool.sol"
        / "LendingPool.json"
    )
    if artifact.is_file():
        try:
            payload = json.loads(artifact.read_text())
            abi = payload.get("abi") if isinstance(payload, dict) else None
            if isinstance(abi, list) and abi:
                return list(abi)
        except (OSError, ValueError, json.JSONDecodeError):
            pass

    return _inline_abi()


def _inline_abi() -> list[dict[str, Any]]:
    """Return the inline canonical ABI fragments (no fabrication)."""

    def fn(name: str, inputs: list[dict[str, Any]], outputs: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        return {
            "type": "function",
            "name": name,
            "inputs": inputs,
            "outputs": outputs or [],
            "stateMutability": "nonpayable",
        }

    def view_fn(name: str, inputs: list[dict[str, Any]], outputs: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "type": "function",
            "name": name,
            "inputs": inputs,
            "outputs": outputs,
            "stateMutability": "view",
        }

    abi: list[dict[str, Any]] = []
    abi.append(fn("supply", [
        {"name": "asset", "type": "address"},
        {"name": "amount", "type": "uint256"},
        {"name": "onBehalfOf", "type": "address"},
        {"name": "referralCode", "type": "uint16"},
    ]))
    abi.append(fn("borrow", [
        {"name": "asset", "type": "address"},
        {"name": "amount", "type": "uint256"},
        {"name": "interestRateMode", "type": "uint256"},
        {"name": "referralCode", "type": "uint16"},
        {"name": "onBehalfOf", "type": "address"},
    ]))
    abi.append(fn("repay", [
        {"name": "asset", "type": "address"},
        {"name": "amount", "type": "uint256"},
        {"name": "interestRateMode", "type": "uint256"},
        {"name": "onBehalfOf", "type": "address"},
    ]))
    abi.append(fn("withdraw", [
        {"name": "asset", "type": "address"},
        {"name": "amount", "type": "uint256"},
        {"name": "to", "type": "address"},
    ]))
    abi.append(fn("flashLoanSimple", [
        {"name": "receiverAddress", "type": "address"},
        {"name": "asset", "type": "address"},
        {"name": "amount", "type": "uint256"},
        {"name": "params", "type": "bytes"},
        {"name": "referralCode", "type": "uint16"},
    ]))
    abi.append(fn("liquidationCall", [
        {"name": "collateralAsset", "type": "address"},
        {"name": "debtAsset", "type": "address"},
        {"name": "user", "type": "address"},
        {"name": "debtToCover", "type": "uint256"},
        {"name": "receiveAToken", "type": "bool"},
    ]))
    abi.append(fn("setUserUseReserveAsCollateral", [
        {"name": "asset", "type": "address"},
        {"name": "useAsCollateral", "type": "bool"},
    ]))
    abi.append(fn("swapBorrowRateMode", [
        {"name": "asset", "type": "address"},
        {"name": "interestRateMode", "type": "uint256"},
    ]))
    abi.append(fn("setUserEMode", [
        {"name": "categoryId", "type": "uint8"},
    ]))
    abi.append(view_fn("getReserveData", [
        {"name": "asset", "type": "address"},
    ], [
        {"name": "configuration", "type": "uint256"},
        {"name": "liquidityIndex", "type": "uint128"},
        {"name": "currentLiquidityRate", "type": "uint128"},
        {"name": "variableBorrowIndex", "type": "uint128"},
        {"name": "currentVariableBorrowRate", "type": "uint128"},
        {"name": "currentStableBorrowRate", "type": "uint128"},
        {"name": "lastUpdateTimestamp", "type": "uint40"},
        {"name": "id", "type": "uint16"},
        {"name": "aTokenAddress", "type": "address"},
        {"name": "stableDebtTokenAddress", "type": "address"},
        {"name": "variableDebtTokenAddress", "type": "address"},
        {"name": "interestRateStrategyAddress", "type": "address"},
        {"name": "accruedToTreasury", "type": "uint128"},
        {"name": "unbacked", "type": "uint128"},
        {"name": "isolationModeTotalDebt", "type": "uint128"},
    ]))
    abi.append(view_fn("getUserAccountData", [
        {"name": "user", "type": "address"},
    ], [
        {"name": "totalCollateralBase", "type": "uint256"},
        {"name": "totalDebtBase", "type": "uint256"},
        {"name": "availableBorrowsBase", "type": "uint256"},
        {"name": "currentLiquidationThreshold", "type": "uint256"},
        {"name": "ltv", "type": "uint256"},
        {"name": "healthFactor", "type": "uint256"},
    ]))
    abi.append(view_fn("getReservesList", [], [
        {"name": "", "type": "address[]"},
    ]))
    return abi


# -------------------------------------------------------------------------- #
# Pool resolver — RPC-bound pool address lookup
# -------------------------------------------------------------------------- #


@dataclass
class ReserveResolution:
    """Result of a ``resolve_pool`` call for a single reserve asset."""

    asset: str
    pool_address: str
    a_token_address: str
    variable_debt_token_address: str
    stable_debt_token_address: str
    interest_rate_strategy_address: str
    current_liquidity_rate: int
    current_variable_borrow_rate: int
    current_stable_borrow_rate: int
    liquidity_index: int
    variable_borrow_index: int
    last_update_timestamp: int
    block: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset": self.asset,
            "pool_address": self.pool_address,
            "a_token_address": self.a_token_address,
            "variable_debt_token_address": self.variable_debt_token_address,
            "stable_debt_token_address": self.stable_debt_token_address,
            "interest_rate_strategy_address": self.interest_rate_strategy_address,
            "current_liquidity_rate": self.current_liquidity_rate,
            "current_variable_borrow_rate": self.current_variable_borrow_rate,
            "current_stable_borrow_rate": self.current_stable_borrow_rate,
            "liquidity_index": self.liquidity_index,
            "variable_borrow_index": self.variable_borrow_index,
            "last_update_timestamp": self.last_update_timestamp,
            "block": self.block,
        }


def _call_rpc(rpc_url: str, method: str, params: list[Any], timeout: float = 10.0) -> Any:
    """Minimal JSON-RPC POST via urllib (no new dependency)."""
    payload = json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    ).encode("utf-8")
    req = urllib_request.Request(
        rpc_url,
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib_request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            body = resp.read().decode("utf-8")
            data = json.loads(body)
    except urllib_error.URLError as exc:
        raise RuntimeError(f"rpc_url_unreachable:{method}:{exc.reason}") from exc
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"rpc_invalid_response:{method}:{exc}") from exc

    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(
            f"rpc_error:{method}:{data['error'].get('code')}:{data['error'].get('message')}"
        )
    return data.get("result") if isinstance(data, dict) else None


def eth_call(to: str, data: str, rpc_url: str, block: int | str) -> str:
    """EVM eth_call against an rpc_url."""
    result = _call_rpc(
        rpc_url,
        "eth_call",
        [{"to": to, "data": data}, block],
    )
    if not isinstance(result, str):
        raise RuntimeError(
            f"rpc_invalid_response:eth_call:expected_hex_payload, got {type(result).__name__}"
        )
    return result


def get_code(to: str, rpc_url: str, block: int | str) -> str:
    """EVM eth_getCode against an rpc_url."""
    result = _call_rpc(rpc_url, "eth_getCode", [to, block])
    if not isinstance(result, str):
        raise RuntimeError(
            f"rpc_invalid_response:eth_getCode:expected_hex_payload, got {type(result).__name__}"
        )
    return result


def resolve_pool(
    asset_address: str,
    rpc_url: str,
    block: int | str = "latest",
    *,
    pool_address: str | None = None,
    timeout: float = 10.0,
) -> ReserveResolution:
    """Resolve an Aave v3 reserve asset against rpc_url.

    Calls ``getReserveData(asset)`` to read on-chain state. No transaction
    is broadcast.
    """
    pool = pool_address or DEFAULT_POOL

    # getReserveData(address) selector — keccak256("getReserveData(address)")[:4]
    selector = evm_selector("getReserveData(address)")
    if isinstance(selector, dict):
        selector = selector["value"]
    asset_word = "0" * 24 + asset_address.lower().removeprefix("0x")
    calldata = selector + asset_word

    code = get_code(pool, rpc_url, block)
    if not isinstance(code, str) or code in ("0x", ""):
        raise RuntimeError(
            f"rpc_no_code_at:{pool}:block={block}:expected_deployed_AaveV3Pool"
        )

    raw = eth_call(pool, calldata, rpc_url, block)
    if not raw.startswith("0x") or len(raw) < 32 * 16 + 2:
        raise RuntimeError(
            f"rpc_invalid_response:getReserveData:short_payload={raw[:66]}"
        )

    # getReserveData returns 16 fields. Each is a 32-byte word.
    offset = 2  # skip "0x"
    def _read_word(idx: int) -> int:
        start = offset + idx * 64
        return int(raw[start : start + 64], 16)

    configuration = _read_word(0)
    liquidity_index = _read_word(1)
    current_liquidity_rate = _read_word(2)
    variable_borrow_index = _read_word(3)
    current_variable_borrow_rate = _read_word(4)
    current_stable_borrow_rate = _read_word(5)
    last_update_timestamp = _read_word(6)
    reserve_id = _read_word(7)
    # Words 8-11 are addresses (left-padded to 32 bytes)
    a_token_address = "0x" + raw[offset + 8 * 64 + 24 : offset + 9 * 64]
    stable_debt_token_address = "0x" + raw[offset + 9 * 64 + 24 : offset + 10 * 64]
    variable_debt_token_address = "0x" + raw[offset + 10 * 64 + 24 : offset + 11 * 64]
    interest_rate_strategy_address = "0x" + raw[offset + 11 * 64 + 24 : offset + 12 * 64]
    accrued_to_treasury = _read_word(12)
    unbacked = _read_word(13)
    isolation_mode_total_debt = _read_word(14)

    block_num = -1
    if isinstance(block, int):
        block_num = block
    elif isinstance(block, str) and block.startswith("0x"):
        block_num = int(block, 16)

    return ReserveResolution(
        asset=asset_address,
        pool_address=pool,
        a_token_address=a_token_address,
        variable_debt_token_address=variable_debt_token_address,
        stable_debt_token_address=stable_debt_token_address,
        interest_rate_strategy_address=interest_rate_strategy_address,
        current_liquidity_rate=current_liquidity_rate,
        current_variable_borrow_rate=current_variable_borrow_rate,
        current_stable_borrow_rate=current_stable_borrow_rate,
        liquidity_index=liquidity_index,
        variable_borrow_index=variable_borrow_index,
        last_update_timestamp=last_update_timestamp,
        block=block_num,
    )


__all__ = [
    "DEFAULT_POOL",
    "DEFAULT_POOL_ADDRESSES_PROVIDER",
    "HARNESS_CHAIN",
    "HARNESS_NAME",
    "HARNESS_PLATFORM",
    "HARNESS_TARGET",
    "AAVE_POOL_FUNCTIONS",
    "ReserveResolution",
    "_AAVE_VIEW_FUNCTIONS",
    "_AAVE_PROVIDER_FUNCTIONS",
    "eth_call",
    "get_code",
    "load_abi",
    "resolve_pool",
    "selectors",
    "signatures",
]
