"""Morpho Blue NativeHarness — Blue + MorphoBlueCoreLib + IRM surface (Cantina).

Second per-target NativeHarness shipped under v5 (Phase 3 row 1). Mirrors the
``uniswap_v4.py`` template. The harness is read-only: it loads the ABI fragments
from ``sources/morpho/repo``, exposes the canonical 4-byte selectors for the
Morpho Blue core functions, and provides a thin resolver that confirms a
deployed Morpho Blue is live on an Ethereum mainnet RPC at a caller-specified block.

Design choices:
- Selectors derive from ``night_shift_security.crypto.evm_function_selector``.
- ABI fragments are sourced from the cloned repo or inline canonical fragments.
- ``resolve_market`` is best-effort: RPC outage bubbles up as ``RuntimeError``.
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
# Constants — single source of truth for the v5 Morpho Blue NativeHarness.
# -------------------------------------------------------------------------- #

HARNESS_TARGET = "morpho_blue"
HARNESS_PLATFORM = "cantina"
HARNESS_CHAIN = "ethereum"
HARNESS_NAME = "Morpho Blue"

# Canonical Morpho Blue deployment (Ethereum mainnet).
# Deployed by morpho-org; canonical address used in Cantina audit scope.
# https://docs.morpho.org/get-started/resources/addresses
DEFAULT_MORPHO_BLUE_MAINNET = "0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb"

# MarketParams struct tuple (5 fields — all addresses/uint256).
_MARKET_PARAMS_TUPLE = "(address,address,address,address,uint256)"

# Canonical Morpho Blue external functions (sourced from
# sources/morpho/repo/src/Morpho.sol + src/interfaces/IMorpho.sol).
MORPHO_FUNCTIONS: list[dict[str, str]] = [
    {
        "name": "createMarket",
        "signature": f"createMarket({_MARKET_PARAMS_TUPLE})",
        "source": "src/Morpho.sol",
    },
    {
        "name": "supply",
        "signature": f"supply({_MARKET_PARAMS_TUPLE},uint256,uint256,address,bytes)",
        "source": "src/Morpho.sol",
    },
    {
        "name": "withdraw",
        "signature": f"withdraw({_MARKET_PARAMS_TUPLE},uint256,uint256,address,address)",
        "source": "src/Morpho.sol",
    },
    {
        "name": "borrow",
        "signature": f"borrow({_MARKET_PARAMS_TUPLE},uint256,uint256,address,address)",
        "source": "src/Morpho.sol",
    },
    {
        "name": "repay",
        "signature": f"repay({_MARKET_PARAMS_TUPLE},uint256,uint256,address,bytes)",
        "source": "src/Morpho.sol",
    },
    {
        "name": "supplyCollateral",
        "signature": f"supplyCollateral({_MARKET_PARAMS_TUPLE},uint256,address,bytes)",
        "source": "src/Morpho.sol",
    },
    {
        "name": "withdrawCollateral",
        "signature": f"withdrawCollateral({_MARKET_PARAMS_TUPLE},uint256,address,address)",
        "source": "src/Morpho.sol",
    },
    {
        "name": "liquidate",
        "signature": f"liquidate({_MARKET_PARAMS_TUPLE},address,uint256,uint256,bytes)",
        "source": "src/Morpho.sol",
    },
    {
        "name": "flashLoan",
        "signature": "flashLoan(address,uint256,bytes)",
        "source": "src/Morpho.sol",
    },
    {
        "name": "setAuthorization",
        "signature": "setAuthorization(address,bool)",
        "source": "src/Morpho.sol",
    },
    {
        "name": "setAuthorizationWithSig",
        "signature": "setAuthorizationWithSig((address,address,bool,uint256,uint256),(uint8,bytes32,bytes32))",
        "source": "src/Morpho.sol",
    },
    {
        "name": "setOwner",
        "signature": "setOwner(address)",
        "source": "src/Morpho.sol",
    },
    {
        "name": "enableIrm",
        "signature": "enableIrm(address)",
        "source": "src/Morpho.sol",
    },
    {
        "name": "enableLltv",
        "signature": "enableLltv(uint256)",
        "source": "src/Morpho.sol",
    },
    {
        "name": "setFee",
        "signature": f"setFee({_MARKET_PARAMS_TUPLE},uint256)",
        "source": "src/Morpho.sol",
    },
    {
        "name": "setFeeRecipient",
        "signature": "setFeeRecipient(address)",
        "source": "src/Morpho.sol",
    },
    {
        "name": "accrueInterest",
        "signature": f"accrueInterest({_MARKET_PARAMS_TUPLE})",
        "source": "src/Morpho.sol",
    },
]

# View functions (read-only, used for state queries).
_MORPHO_VIEW_FUNCTIONS: list[dict[str, str]] = [
    {
        "name": "owner",
        "signature": "owner()",
        "source": "src/Morpho.sol",
    },
    {
        "name": "feeRecipient",
        "signature": "feeRecipient()",
        "source": "src/Morpho.sol",
    },
    {
        "name": "position",
        "signature": "position(bytes32,address)",
        "source": "src/Morpho.sol",
    },
    {
        "name": "market",
        "signature": "market(bytes32)",
        "source": "src/Morpho.sol",
    },
    {
        "name": "idToMarketParams",
        "signature": "idToMarketParams(bytes32)",
        "source": "src/Morpho.sol",
    },
    {
        "name": "isIrmEnabled",
        "signature": "isIrmEnabled(address)",
        "source": "src/Morpho.sol",
    },
    {
        "name": "isLltvEnabled",
        "signature": "isLltvEnabled(uint256)",
        "source": "src/Morpho.sol",
    },
    {
        "name": "isAuthorized",
        "signature": "isAuthorized(address,address)",
        "source": "src/Morpho.sol",
    },
    {
        "name": "nonce",
        "signature": "nonce(address)",
        "source": "src/Morpho.sol",
    },
    {
        "name": "DOMAIN_SEPARATOR",
        "signature": "DOMAIN_SEPARATOR()",
        "source": "src/Morpho.sol",
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
    """Canonical 4-byte selectors for Morpho Blue core + view functions.

    Returns a mapping from category to a name -> ``0x...`` selector dict.

    >>> funcs = selectors()["morpho"]
    >>> funcs["supply"].startswith("0x") and len(funcs["supply"]) == 10
    True
    """
    return {
        "morpho": _selector_map(MORPHO_FUNCTIONS),
        "morpho_view": _selector_map(_MORPHO_VIEW_FUNCTIONS),
    }


def signatures() -> dict[str, list[str]]:
    """Return canonical signatures per category.

    Mostly used for documentation / fixture generation.
    """
    return {
        "morpho": [entry["signature"] for entry in MORPHO_FUNCTIONS],
        "morpho_view": [entry["signature"] for entry in _MORPHO_VIEW_FUNCTIONS],
    }


def load_abi(repo_path: Path | str) -> list[dict[str, Any]]:
    """Load Morpho Blue ABI fragments from the repo.

    Resolution order:
    1. ``out/Morpho.sol/Morpho.json`` (Forge artifact).
    2. Fallback: synthesised inline ABI fragments for the canonical external
       functions only — never fabricated storage layout.
    """
    repo = Path(repo_path)

    artifact = repo / "out" / "Morpho.sol" / "Morpho.json"
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

    def fn(name: str, types: list[str], *, inputs: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        if inputs is None:
            inputs = [{"name": "_", "type": t, "indexed": False} for t in types]
        return {
            "type": "function",
            "name": name,
            "inputs": inputs,
            "outputs": [],
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

    mp = _MARKET_PARAMS_TUPLE
    abi: list[dict[str, Any]] = []
    abi.append(fn("createMarket", [mp]))
    abi.append(fn("supply", [mp, "uint256", "uint256", "address", "bytes"]))
    abi.append(fn("withdraw", [mp, "uint256", "uint256", "address", "address"]))
    abi.append(fn("borrow", [mp, "uint256", "uint256", "address", "address"]))
    abi.append(fn("repay", [mp, "uint256", "uint256", "address", "bytes"]))
    abi.append(fn("supplyCollateral", [mp, "uint256", "address", "bytes"]))
    abi.append(fn("withdrawCollateral", [mp, "uint256", "address", "address"]))
    abi.append(fn("liquidate", [mp, "address", "uint256", "uint256", "bytes"]))
    abi.append(fn("flashLoan", ["address", "uint256", "bytes"]))
    abi.append(fn("setAuthorization", ["address", "bool"]))
    abi.append(fn("setOwner", ["address"]))
    abi.append(fn("enableIrm", ["address"]))
    abi.append(fn("enableLltv", ["uint256"]))
    abi.append(fn("setFee", [mp, "uint256"]))
    abi.append(fn("setFeeRecipient", ["address"]))
    abi.append(fn("accrueInterest", [mp]))
    abi.append(view_fn("owner", [], [{"name": "", "type": "address"}]))
    abi.append(view_fn("feeRecipient", [], [{"name": "", "type": "address"}]))
    abi.append(
        view_fn(
            "position",
            [{"name": "id", "type": "bytes32"}, {"name": "user", "type": "address"}],
            [
                {"name": "supplyShares", "type": "uint256"},
                {"name": "borrowShares", "type": "uint128"},
                {"name": "collateral", "type": "uint128"},
            ],
        )
    )
    abi.append(
        view_fn(
            "market",
            [{"name": "id", "type": "bytes32"}],
            [
                {"name": "totalSupplyAssets", "type": "uint128"},
                {"name": "totalSupplyShares", "type": "uint128"},
                {"name": "totalBorrowAssets", "type": "uint128"},
                {"name": "totalBorrowShares", "type": "uint128"},
                {"name": "lastUpdate", "type": "uint128"},
                {"name": "fee", "type": "uint128"},
            ],
        )
    )
    return abi


# -------------------------------------------------------------------------- #
# Market resolver — RPC-bound market ID lookup
# -------------------------------------------------------------------------- #


@dataclass
class MarketParams:
    """Minimal Morpho Blue MarketParams description."""

    loan_token: str
    collateral_token: str
    oracle: str
    irm: str
    lltv: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "loanToken": self.loan_token,
            "collateralToken": self.collateral_token,
            "oracle": self.oracle,
            "irm": self.irm,
            "lltv": int(self.lltv),
        }


@dataclass
class MarketResolution:
    """Result of a ``resolve_market`` call."""

    market_id: str
    total_supply_assets: int
    total_supply_shares: int
    total_borrow_assets: int
    total_borrow_shares: int
    last_update: int
    fee: int
    block: int
    morpho_address: str
    market_params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "market_id": self.market_id,
            "total_supply_assets": self.total_supply_assets,
            "total_supply_shares": self.total_supply_shares,
            "total_borrow_assets": self.total_borrow_assets,
            "total_borrow_shares": self.total_borrow_shares,
            "last_update": self.last_update,
            "fee": self.fee,
            "block": self.block,
            "morpho_address": self.morpho_address,
            "market_params": self.market_params,
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


def _market_id(market_params: dict[str, Any]) -> str:
    """Compute the canonical market ID (Id = bytes32) for a MarketParams.

    Morpho Blue computes Id via keccak256(abi.encode(MarketParams)).
    """
    from night_shift_security.crypto import keccak256 as _k256

    def word_address(val: str) -> str:
        raw = val.lower().removeprefix("0x")
        if len(raw) != 40:
            raise ValueError(f"address_must_be_40_hex_chars:{val}")
        return "0" * 24 + raw

    def word_uint(value: int) -> str:
        return format(int(value) & ((1 << 256) - 1), "064x")

    parts: list[str] = []
    for field_name in ("loanToken", "collateralToken", "oracle", "irm"):
        parts.append(word_address(str(market_params.get(field_name) or "0x" + "0" * 40)))
    parts.append(word_uint(int(market_params.get("lltv") or 0)))
    raw = bytes.fromhex("".join(parts))
    digest = _k256(raw)
    return "0x" + digest.hex()


def resolve_market(
    market_params: dict[str, Any] | MarketParams,
    rpc_url: str,
    block: int | str = "latest",
    *,
    morpho_address: str | None = None,
    timeout: float = 10.0,
) -> MarketResolution:
    """Resolve a deployed Morpho Blue market against rpc_url.

    Calls ``market(Id)`` to read on-chain state. No transaction is broadcast.
    """
    if isinstance(market_params, MarketParams):
        mp = market_params.to_dict()
    else:
        mp = dict(market_params)
    morpho = morpho_address or DEFAULT_MORPHO_BLUE_MAINNET
    market_id_hex = _market_id(mp)

    # market(bytes32) selector — keccak256("market(bytes32)")[:4]
    selector = evm_selector("market(bytes32)")
    if isinstance(selector, dict):
        selector = selector["value"]
    calldata = selector + market_id_hex.removeprefix("0x")

    code = get_code(morpho, rpc_url, block)
    if not isinstance(code, str) or code in ("0x", ""):
        raise RuntimeError(
            f"rpc_no_code_at:{morpho}:block={block}:expected_deployed_MorphoBlue"
        )

    raw = eth_call(morpho, calldata, rpc_url, block)
    if not raw.startswith("0x") or len(raw) < 386:
        raise RuntimeError(
            f"rpc_invalid_response:market:short_payload={raw[:66]}"
        )

    # market returns 6 uint128 fields: totalSupplyAssets, totalSupplyShares,
    # totalBorrowAssets, totalBorrowShares, lastUpdate, fee
    # Each is a 16-byte (32-hex-char) value packed into 32-byte words.
    total_supply_assets = int(raw[2 + 0 : 2 + 64], 16)
    total_supply_shares = int(raw[2 + 64 : 2 + 128], 16)
    total_borrow_assets = int(raw[2 + 128 : 2 + 192], 16)
    total_borrow_shares = int(raw[2 + 192 : 2 + 256], 16)
    last_update = int(raw[2 + 256 : 2 + 320], 16)
    fee = int(raw[2 + 320 : 2 + 384], 16)

    block_num = -1
    if isinstance(block, int):
        block_num = block
    elif isinstance(block, str) and block.startswith("0x"):
        block_num = int(block, 16)

    return MarketResolution(
        market_id=market_id_hex,
        total_supply_assets=total_supply_assets,
        total_supply_shares=total_supply_shares,
        total_borrow_assets=total_borrow_assets,
        total_borrow_shares=total_borrow_shares,
        last_update=last_update,
        fee=fee,
        block=block_num,
        morpho_address=morpho,
        market_params=mp,
    )


__all__ = [
    "DEFAULT_MORPHO_BLUE_MAINNET",
    "HARNESS_CHAIN",
    "HARNESS_NAME",
    "HARNESS_PLATFORM",
    "HARNESS_TARGET",
    "MORPHO_FUNCTIONS",
    "MarketParams",
    "MarketResolution",
    "_MORPHO_VIEW_FUNCTIONS",
    "_market_id",
    "eth_call",
    "get_code",
    "load_abi",
    "resolve_market",
    "selectors",
    "signatures",
]
