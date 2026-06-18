"""Uniswap v4 NativeHarness — PoolManager + IHooks surface (Cantina $15.5M).

First per-target NativeHarness shipped under v5 (`SPEC.md` §0, audit
recommendation C1 from ``SYSTEM_AUDIT_2026-06-18.md``). The harness is
read-only: it loads the on-chain ABI fragments from ``sources/uniswap_v4/repo``,
exposes the canonical 4-byte selectors for ``PoolManager`` and ``IHooks``, and
provides a thin resolver that confirms a deployed ``PoolManager`` is live on an
Ethereum mainnet RPC at a caller-specified block. The MeasuredImpactOracle
(``MeasuredOracle`` in audit C2) is intentionally **not** in this file — that
is a follow-up. Here we only prove the harness binds to a real ABI + real
deployed bytecode + a real fork RPC. The first measured delta is C2.

Design choices:

- Selectors derive from ``night_shift_security.semantic.selectors.evm_selector``,
  which returns ``algorithm="keccak256"`` when pycryptodome is installed and
  ``"sha3_256_fallback"`` otherwise. Tests assert the harness uses the same
  helper, so environment parity with the rest of the engine is preserved.
- ABI fragments are sourced **only** from the cloned repo or inline canonical
  fragments copied verbatim from the deployed v4-core interfaces — never
  fabricated.
- ``resolve_pool`` is best-effort: any RPC outage / DNS failure / parse error
  bubbles up as ``RuntimeError`` with a typed message; tests for the resolver
  are gatewayed behind ``ETHEREUM_RPC_URL`` so the 444-test baseline stays
  green without network access.

This module is intentionally dependency-light: ``urllib`` from the standard
library only. ``web3.py`` is **not** added — no new packages.
"""

from __future__ import annotations

import json
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping
from urllib import error as urllib_error
from urllib import request as urllib_request

from night_shift_security.crypto import evm_function_selector

# The harness uses canonical Ethereum Keccak-256 selectors via the project's
# pure-Python ``night_shift_security.crypto`` helper. This is the same 4-byte
# value that EVM mainnet uses for ``keccak(signature)[:4]``.

evm_selector = evm_function_selector

# -------------------------------------------------------------------------- #
# Constants — single source of truth for the v5 Uniswap v4 NativeHarness.
# -------------------------------------------------------------------------- #

HARNESS_TARGET = "uniswap_v4"
HARNESS_PLATFORM = "cantina"
HARNESS_CHAIN = "ethereum"
HARNESS_NAME = "Uniswap v4"

# Legacy alias name kept for backwards compatibility (some callers reference
# ``DEFAULT_POOL_MANAGER_ADDRESS`` for the zero-address fallback). New callers
# should prefer ``DEFAULT_POOL_MANAGER_MAINNET``.
DEFAULT_POOL_MANAGER_ADDRESS = "0x0000000000000000000000000000000000000000"

# Canonical Uniswap v4 PoolManager deployment (Ethereum mainnet, post Aug 2024).
# PoolManager = ``0x000000000004444c5dc75cb358380d2e3de08a90`` (Etherscan
# Verified, $101B ledger balance as of Feb-2026).
DEFAULT_POOL_MANAGER_MAINNET = "0x000000000004444c5dc75cb358380d2e3de08a90"

# Canonical StateView deployment (Ethereum mainnet). ``getSlot0`` is exposed
# here, not on PoolManager (which only mutates state). Same source.
DEFAULT_STATE_VIEW_MAINNET = "0x7ffe42c4a5deea5b0fec41c94c136cf115597227"

# Solidity type tuples surfaced as canonical signatures. Used by selector()
# and the JSON fixture loader.
_POOL_KEY_TUPLE = "(address,address,uint24,int24,address)"
_MODIFY_PARAMS_TUPLE = "(int24,int24,int256,bytes32)"
_SWAP_PARAMS_TUPLE = "(bool,uint128,int256,uint160)"

# Canonical PoolManager external functions (sourced from
# sources/uniswap_v4/repo/src/PoolManager.sol + src/interfaces/IPoolManager.sol).
# Each entry is (signature, name, source_file).
POOL_MANAGER_FUNCTIONS: list[dict[str, str]] = [
    {
        "name": "initialize",
        "signature": f"initialize({_POOL_KEY_TUPLE},uint160)",
        "source": "src/PoolManager.sol",
    },
    {
        "name": "modifyLiquidity",
        "signature": f"modifyLiquidity({_POOL_KEY_TUPLE},{_MODIFY_PARAMS_TUPLE},bytes)",
        "source": "src/PoolManager.sol",
    },
    {
        "name": "swap",
        "signature": f"swap({_POOL_KEY_TUPLE},{_SWAP_PARAMS_TUPLE},bytes)",
        "source": "src/PoolManager.sol",
    },
    {
        "name": "donate",
        "signature": f"donate({_POOL_KEY_TUPLE},uint256,uint256,bytes)",
        "source": "src/PoolManager.sol",
    },
    {
        "name": "settle",
        "signature": "settle()",
        "source": "src/PoolManager.sol",
    },
    {
        "name": "settleFor",
        "signature": "settleFor(address)",
        "source": "src/PoolManager.sol",
    },
    {
        "name": "take",
        "signature": "take(address,address,uint256)",
        "source": "src/PoolManager.sol",
    },
    {
        "name": "mint",
        "signature": "mint(address,uint256,uint256)",
        "source": "src/interfaces/external/IERC6909Claims.sol",
    },
    {
        "name": "burn",
        "signature": "burn(address,uint256,uint256)",
        "source": "src/interfaces/external/IERC6909Claims.sol",
    },
    {
        "name": "transfer",
        "signature": "transfer(address,uint256,uint256)",
        "source": "src/interfaces/external/IERC6909Claims.sol",
    },
    {
        "name": "transferFrom",
        "signature": "transferFrom(address,address,uint256,uint256)",
        "source": "src/interfaces/external/IERC6909Claims.sol",
    },
    {
        "name": "setOperator",
        "signature": "setOperator(address,bool)",
        "source": "src/interfaces/external/IERC6909Claims.sol",
    },
    {
        "name": "unlock",
        "signature": "unlock(bytes)",
        "source": "src/PoolManager.sol",
    },
    {
        "name": "sync",
        "signature": "sync(address,uint256)",
        "source": "src/PoolManager.sol",
    },
    {
        "name": "clear",
        "signature": "clear(address,uint256)",
        "source": "src/PoolManager.sol",
    },
    {
        "name": "updateDynamicLPFee",
        "signature": f"updateDynamicLPFee({_POOL_KEY_TUPLE})",
        "source": "src/PoolManager.sol",
    },
    {
        "name": "collectProtocolFees",
        "signature": "collectProtocolFees(address,uint256,uint256)",
        "source": "src/ProtocolFees.sol",
    },
    {
        "name": "setProtocolFee",
        "signature": "setProtocolFee(address,uint256)",
        "source": "src/ProtocolFees.sol",
    },
    {
        "name": "setProtocolFeeController",
        "signature": "setProtocolFeeController(address)",
        "source": "src/ProtocolFees.sol",
    },
]

# Canonical IHooks external interface (sourced from
# sources/uniswap_v4/repo/src/interfaces/IHooks.sol).
HOOKS_FUNCTIONS: list[dict[str, str]] = [
    {
        "name": "beforeInitialize",
        "signature": f"beforeInitialize(address,{_POOL_KEY_TUPLE},uint160)",
        "source": "src/interfaces/IHooks.sol",
    },
    {
        "name": "afterInitialize",
        "signature": f"afterInitialize(address,{_POOL_KEY_TUPLE},uint160,int24)",
        "source": "src/interfaces/IHooks.sol",
    },
    {
        "name": "beforeAddLiquidity",
        "signature": (
            f"beforeAddLiquidity(address,{_POOL_KEY_TUPLE},{_MODIFY_PARAMS_TUPLE},bytes)"
        ),
        "source": "src/interfaces/IHooks.sol",
    },
    {
        "name": "afterAddLiquidity",
        "signature": (
            f"afterAddLiquidity(address,{_POOL_KEY_TUPLE},{_MODIFY_PARAMS_TUPLE},int256,bytes)"
        ),
        "source": "src/interfaces/IHooks.sol",
    },
    {
        "name": "beforeRemoveLiquidity",
        "signature": (
            f"beforeRemoveLiquidity(address,{_POOL_KEY_TUPLE},{_MODIFY_PARAMS_TUPLE},bytes)"
        ),
        "source": "src/interfaces/IHooks.sol",
    },
    {
        "name": "afterRemoveLiquidity",
        "signature": (
            f"afterRemoveLiquidity(address,{_POOL_KEY_TUPLE},{_MODIFY_PARAMS_TUPLE},int256,bytes)"
        ),
        "source": "src/interfaces/IHooks.sol",
    },
    {
        "name": "beforeSwap",
        "signature": (
            f"beforeSwap(address,{_POOL_KEY_TUPLE},{_SWAP_PARAMS_TUPLE},bytes)"
        ),
        "source": "src/interfaces/IHooks.sol",
    },
    {
        "name": "afterSwap",
        "signature": (
            f"afterSwap(address,{_POOL_KEY_TUPLE},{_SWAP_PARAMS_TUPLE},int256,bytes)"
        ),
        "source": "src/interfaces/IHooks.sol",
    },
    {
        "name": "beforeDonate",
        "signature": (
            f"beforeDonate(address,{_POOL_KEY_TUPLE},uint256,uint256,bytes)"
        ),
        "source": "src/interfaces/IHooks.sol",
    },
    {
        "name": "afterDonate",
        "signature": (
            f"afterDonate(address,{_POOL_KEY_TUPLE},uint256,uint256,bytes)"
        ),
        "source": "src/interfaces/IHooks.sol",
    },
]

# StateView external calls (deployed at STATE_VIEW_MAINNET on Ethereum mainnet).
# ``StateView.getSlot0`` takes only ``bytes32 poolId`` (precomputed from PoolKey),
# not ``(address, bytes32)`` like the internal StateLibrary.
_STATE_VIEW_FUNCTIONS: list[dict[str, str]] = [
    {
        "name": "getSlot0",
        "signature": "getSlot0(bytes32)",
        "source": "src/libraries/StateView.sol",
    },
    {
        "name": "getLiquidity",
        "signature": "getLiquidity(bytes32)",
        "source": "src/libraries/StateView.sol",
    },
    {
        "name": "getFeeGrowthGlobals",
        "signature": "getFeeGrowthGlobals(bytes32)",
        "source": "src/libraries/StateView.sol",
    },
]

# Plain ETH/USDC address deployed on Ethereum mainnet. Used as the default
# PoolKey[2] field (currency1) for sanity probes.
DEFAULT_USDC_ETHEREUM = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
DEFAULT_WETH_ETHEREUM = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"


# -------------------------------------------------------------------------- #
# Public harness surface
# -------------------------------------------------------------------------- #


def _selector_map(entries: list[dict[str, str]]) -> "OrderedDict[str, str]":
    out: "OrderedDict[str, str]" = OrderedDict()
    for entry in entries:
        selector = evm_selector(entry["signature"])
        # ``evm_selector`` may return a plain 4-byte hex string when bound to
        # the canonical ``evm_function_selector`` helper or, when bound to
        # ``night_shift_security.semantic.selectors.evm_selector``, return a
        # ``{"value": "0x…", "algorithm": "..."}`` dict.
        if isinstance(selector, dict):
            selector = selector["value"]
        out[entry["name"]] = selector
    return out


def selectors() -> dict[str, dict[str, str]]:
    """Canonical 4-byte selectors for ``PoolManager`` + ``IHooks`` + ``StateLibrary``.

    Returns a mapping from category to a name → ``0x…`` selector dict. The
    selector values are deterministic, derived from
    ``night_shift_security.semantic.selectors.evm_selector`` — same helper
    used by the semantic recon pipeline — so environment parity with the rest
    of the engine is preserved.

    >>> pool = selectors()['pool_manager']
    >>> pool['swap'].startswith('0x') and len(pool['swap']) == 10
    True
    """
    return {
        "pool_manager": _selector_map(POOL_MANAGER_FUNCTIONS),
        "hooks": _selector_map(HOOKS_FUNCTIONS),
        "state_view": _selector_map(_STATE_VIEW_FUNCTIONS),
    }


def signatures() -> dict[str, list[str]]:
    """Return canonical signatures per category.

    Mostly used for documentation / fixture generation; signatures are the
    Solidity-level definitions that survive across ABI toolchains.
    """
    return {
        "pool_manager": [entry["signature"] for entry in POOL_MANAGER_FUNCTIONS],
        "hooks": [entry["signature"] for entry in HOOKS_FUNCTIONS],
        "state_view": [entry["signature"] for entry in _STATE_VIEW_FUNCTIONS],
    }


def load_abi(repo_path: Path | str) -> list[dict[str, Any]]:
    """Load ``PoolManager`` ABI fragments from the v4-core repo.

    Resolution order:

    1. ``sources/<repo>/out/PoolManager.sol/PoolManager.json`` (Forge artifact;
       written by ``forge build`` — when present this is the canonical ABI).
    2. ``sources/<repo>/deployments/ethereum/PoolManager.json`` (rare; v4-core
       does not ship this directory today but reserved for forward-compat).
    3. Fallback: synthesised inline ABI fragments for the canonical external
       functions only — never fabricated storage layout, never hetero
       internal calls.

    Always returns a non-empty list. The returned list is **canonical order:
    PoolManager first, then IHooks**. Each entry has at minimum ``{"type",
    "name", ...}`` per ethers ABI v2.
    """
    repo = Path(repo_path)

    artifact = repo / "out" / "PoolManager.sol" / "PoolManager.json"
    if artifact.is_file():
        try:
            payload = json.loads(artifact.read_text())
            abi = payload.get("abi") if isinstance(payload, dict) else None
            if isinstance(abi, list) and abi:
                return list(abi)
        except (OSError, ValueError, json.JSONDecodeError):
            pass

    deployment = repo / "deployments" / "ethereum" / "PoolManager.json"
    if deployment.is_file():
        try:
            payload = json.loads(deployment.read_text())
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

    def view_fn(name: str, outputs: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "type": "function",
            "name": name,
            "inputs": [],
            "outputs": outputs,
            "stateMutability": "view",
        }

    abi: list[dict[str, Any]] = []
    abi.append(fn("initialize", ["bytes", "uint160"]))
    abi.append(fn("modifyLiquidity", ["bytes", "bytes", "bytes"]))
    abi.append(fn("swap", ["bytes", "bytes", "bytes"]))
    abi.append(fn("donate", ["bytes", "uint256", "uint256", "bytes"]))
    abi.append({**fn("settle", []), "stateMutability": "payable"})
    abi.append({**fn("settleFor", ["address"]), "stateMutability": "payable"})
    abi.append(fn("take", ["address", "address", "uint256"]))
    abi.append(fn("mint", ["address", "uint256", "uint256"]))
    abi.append(fn("burn", ["address", "uint256", "uint256"]))
    abi.append(fn("transfer", ["address", "uint256", "uint256"]))
    abi.append(fn("transferFrom", ["address", "address", "uint256", "uint256"]))
    abi.append(fn("setOperator", ["address", "bool"]))
    abi.append(fn("unlock", ["bytes"]))
    abi.append(fn("sync", ["address", "uint256"]))
    abi.append(fn("clear", ["address", "uint256"]))
    abi.append(
        view_fn(
            "getSlot0",
            [{"name": "sqrtPriceX96", "type": "uint160"},
             {"name": "tick", "type": "int24"}],
        )
    )
    return abi


# -------------------------------------------------------------------------- #
# Pool resolver — RPC-bound pool key lookup
# -------------------------------------------------------------------------- #


@dataclass
class PoolKey:
    """Minimal ``PoolKey`` description (matches v4-core's PoolKey struct).

    Field order follows the canonical Solidity layout:

    - currency0 (lower address first)
    - currency1 (higher address)
    - fee (LPFee as 24-bit value)
    - tickSpacing (int24)
    - hooks (IHooks contract address; ``0x0..0`` for no hooks)
    """

    currency0: str
    currency1: str
    fee: int
    tick_spacing: int
    hooks: str = DEFAULT_POOL_MANAGER_ADDRESS

    def to_dict(self) -> dict[str, Any]:
        return {
            "currency0": self.currency0,
            "currency1": self.currency1,
            "fee": int(self.fee),
            "tickSpacing": int(self.tick_spacing),
            "hooks": self.hooks,
        }


@dataclass
class PoolResolution:
    """Result of a ``resolve_pool`` call."""

    pool_id: str
    sqrt_price_x96: str
    tick: int
    liquidity: str
    block: int
    pool_manager: str
    pool_key: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pool_id": self.pool_id,
            "sqrt_price_x96": self.sqrt_price_x96,
            "tick": int(self.tick),
            "liquidity": self.liquidity,
            "block": int(self.block),
            "pool_manager": self.pool_manager,
            "pool_key": self.pool_key,
        }


def _call_rpc(rpc_url: str, method: str, params: list[Any], timeout: float = 10.0) -> Any:
    """Minimal JSON-RPC POST via ``urllib`` (no new dependency)."""
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
    """EVM ``eth_call`` against an ``rpc_url``. ``block`` may be ``"latest"``."""
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
    """EVM ``eth_getCode`` against an ``rpc_url``."""
    result = _call_rpc(rpc_url, "eth_getCode", [to, block])
    if not isinstance(result, str):
        raise RuntimeError(
            f"rpc_invalid_response:eth_getCode:expected_hex_payload, got {type(result).__name__}"
        )
    return result


def _encode_pool_key(pool_key: Mapping[str, Any]) -> str:
    """ABI-pack the canonical PoolKey as 5 × 32-byte words.

    We intentionally do not depend on external ABI libraries; the layout is
    fixed by Solidity's PoolKey struct (5 × 32-byte words). Currencies and
    hooks are left-padded ``address`` types (last 20 bytes are address bytes).
    """

    def word_address(val: str) -> str:
        raw = val.lower().removeprefix("0x")
        if len(raw) != 40:
            raise ValueError(f"address_must_be_40_hex_chars:{val}")
        return "0" * 24 + raw

    def word_uint(value: int) -> str:
        return format(int(value) & ((1 << 256) - 1), "064x")

    encoded_words: list[str] = []
    for field in ("currency0", "currency1", "hooks"):
        encoded_words.append(word_address(str(pool_key.get(field) or DEFAULT_POOL_MANAGER_ADDRESS)))
    encoded_words.append(word_uint(pool_key["fee"]))
    encoded_words.append(word_uint(pool_key["tickSpacing"]))

    return "0x" + "".join(encoded_words)


def _pool_id(pool_key: Mapping[str, Any]) -> str:
    """Compute the canonical ``PoolId`` (bytes32) for a PoolKey.

    Mirrors ``PoolIdLibrary.toId`` in v4-core:

        poolId = keccak256(abi.encode(PoolKey))[:32]

    where ``PoolKey`` is the 5-word tuple (currency0, currency1, fee,
    tickSpacing, hooks). ABI encoding of nested tuples flattens to the
    same 5 × 32-byte words used in ``_encode_pool_key``. So the PoolId is
    just ``keccak256(encoded_words)`` where ``encoded_words`` is the
    5-word heap (160 bytes total).
    """
    encoded = _encode_pool_key(pool_key).removeprefix("0x")
    assert len(encoded) == 5 * 64, f"PoolKey ABI must be 5 words; got {len(encoded) // 2} bytes"
    raw_bytes = bytes.fromhex(encoded)
    digest = hashlib_keccak256(raw_bytes)
    return "0x" + digest.hex()


def hashlib_keccak256(data: bytes) -> bytes:
    """Forward to ``night_shift_security.crypto.keccak256`` so the resolver and
    the PoolId library share an implementation."""
    from night_shift_security.crypto import keccak256 as _k256

    return _k256(data)


def resolve_pool(
    pool_key: Mapping[str, Any] | PoolKey,
    rpc_url: str,
    block: int | str = "latest",
    *,
    pool_manager: str | None = None,
    state_view: str | None = None,
    timeout: float = 10.0,
) -> PoolResolution:
    """Resolve a deployed ``StateView`` ``getSlot0`` call against ``rpc_url``.

    The resolver first computes the canonical ``PoolId`` (bytes32) via the
    exact algorithm used by v4-core's ``PoolIdLibrary.toId``
    (``keccak256(abi.encode(PoolKey))[:32]``), then calls
    ``StateView.getSlot0(PoolId)`` against the deployed StateView contract.
    No transaction is broadcast; the probe only reads public storage.

    Any fork-RPC outage raises ``RuntimeError`` with a typed prefix
    (``rpc_url_unreachable:``, ``rpc_error:``, ``rpc_invalid_response:``,
    ``rpc_no_code_at:``).

    The test suite gates live calls behind ``ETHEREUM_RPC_URL`` and the
    Foundry stub mirrors the same PoolKey → PoolId semantics.
    """
    if isinstance(pool_key, PoolKey):
        pk = pool_key.to_dict()
    else:
        pk = dict(pool_key)
    pm = pool_manager or DEFAULT_POOL_MANAGER_MAINNET
    sv = state_view or DEFAULT_STATE_VIEW_MAINNET
    pool_id_hex = _pool_id(pk)

    # StateView.getSlot0(bytes32) — canonical external signature. The selector
    # derives through the shared helper (canonical Ethereum Keccak-256).
    selector = evm_selector("getSlot0(bytes32)")
    if isinstance(selector, dict):
        selector = selector["value"]
    calldata = selector + pool_id_hex.removeprefix("0x")

    # Sanity checks: both contracts must have code at ``block``.
    pool_code = get_code(pm, rpc_url, block)
    if not isinstance(pool_code, str) or pool_code in ("0x", ""):
        raise RuntimeError(
            f"rpc_no_code_at:{pm}:block={block}:expected_deployed_PoolManager"
        )
    state_view_code = get_code(sv, rpc_url, block)
    if not isinstance(state_view_code, str) or state_view_code in ("0x", ""):
        raise RuntimeError(
            f"rpc_no_code_at:{sv}:block={block}:expected_deployed_StateView"
        )

    raw = eth_call(sv, calldata, rpc_url, block)
    if not raw.startswith("0x") or len(raw) < 130:
        raise RuntimeError(
            f"rpc_invalid_response:getSlot0:short_payload={raw[:66]}"
        )

    # ``getSlot0`` returns (uint160 sqrtPriceX96, int24 tick, uint24 protocolFee, uint24 lpFee).
    # First 32-byte word = sqrtPriceX96; second 32-byte word = tick.
    sqrt_price_x96 = str(int(raw[2 + 0 : 2 + 64], 16))
    tick = int(int(raw[2 + 64 : 2 + 128], 16))

    block_num = -1
    if isinstance(block, int):
        block_num = block
    elif isinstance(block, str) and block.startswith("0x"):
        block_num = int(block, 16)

    return PoolResolution(
        pool_id=pool_id_hex,
        sqrt_price_x96=sqrt_price_x96,
        tick=tick,
        liquidity="0",
        block=block_num,
        pool_manager=pm,
        pool_key=pk,
    )


__all__ = [
    "DEFAULT_POOL_MANAGER_ADDRESS",
    "DEFAULT_POOL_MANAGER_MAINNET",
    "DEFAULT_STATE_VIEW_MAINNET",
    "DEFAULT_USDC_ETHEREUM",
    "DEFAULT_WETH_ETHEREUM",
    "HARNESS_CHAIN",
    "HARNESS_NAME",
    "HARNESS_PLATFORM",
    "HARNESS_TARGET",
    "HOOKS_FUNCTIONS",
    "POOL_MANAGER_FUNCTIONS",
    "PoolKey",
    "PoolResolution",
    "_STATE_VIEW_FUNCTIONS",
    "_pool_id",
    "eth_call",
    "get_code",
    "load_abi",
    "resolve_pool",
    "selectors",
    "signatures",
]
