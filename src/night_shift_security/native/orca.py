"""Orca NativeHarness — Whirlpools CLMM surface (Immunefi $500K)."""

from __future__ import annotations

import json
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

from night_shift_security.semantic.selectors import anchor_discriminator

HARNESS_TARGET = "orca"
HARNESS_PLATFORM = "immunefi"
HARNESS_CHAIN = "solana"
HARNESS_NAME = "Orca"

WHIRLPOOL_PROGRAM = "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc"
DEFAULT_WHIRLPOOL = "Czfq3xZZDmsdGdUyrNLtRhGc47cXcZtLG4crryfu44zE"

TOP_INSTRUCTIONS: tuple[str, ...] = (
    "initialize_pool",
    "initialize_tick_array",
    "open_position",
    "open_position_with_metadata",
    "increase_liquidity",
    "decrease_liquidity",
    "swap",
    "collect_fees",
    "collect_reward",
    "update_fees_and_rewards",
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REPO = _REPO_ROOT / "sources" / "orca" / "repo"


def program_ids() -> dict[str, str]:
    return {"whirlpool": WHIRLPOOL_PROGRAM}


def discriminators() -> dict[str, str]:
    return OrderedDict((n, anchor_discriminator(n)) for n in TOP_INSTRUCTIONS)


def instruction_names() -> list[str]:
    return list(TOP_INSTRUCTIONS)


def load_idl(repo_path: Path | str | None = None) -> dict[str, Any]:
    repo = Path(repo_path) if repo_path is not None else DEFAULT_REPO
    artifact = repo / "target" / "idl" / "whirlpool.json"
    if artifact.is_file():
        try:
            return json.loads(artifact.read_text())
        except (OSError, ValueError, json.JSONDecodeError):
            pass
    return {
        "address": WHIRLPOOL_PROGRAM,
        "instructions": [
            {"name": n, "discriminator": list(bytes.fromhex(anchor_discriminator(n).removeprefix("0x")))}
            for n in TOP_INSTRUCTIONS
        ],
    }


@dataclass
class AccountResolution:
    program_id: str
    whirlpool: str
    slot: int
    lamports: int
    data_len: int
    sqrt_price_hint: str = "0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "program_id": self.program_id,
            "whirlpool": self.whirlpool,
            "slot": int(self.slot),
            "lamports": int(self.lamports),
            "data_len": int(self.data_len),
            "sqrt_price_hint": self.sqrt_price_hint,
        }


def _rpc(rpc_url: str, method: str, params: list[Any]) -> Any:
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib_request.Request(rpc_url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib_request.urlopen(req, timeout=15) as resp:  # noqa: S310
            body = json.loads(resp.read().decode())
    except urllib_error.URLError as exc:
        raise RuntimeError(f"rpc_url_unreachable:{method}:{exc.reason}") from exc
    if body.get("error"):
        raise RuntimeError(f"rpc_error:{method}:{body['error']}")
    return body.get("result")


def resolve_accounts(market_hint: str, rpc_url: str) -> AccountResolution:
    pool = market_hint or DEFAULT_WHIRLPOOL
    prog = _rpc(rpc_url, "getAccountInfo", [WHIRLPOOL_PROGRAM, {"encoding": "base64"}])
    if not (prog or {}).get("value"):
        raise RuntimeError(f"rpc_no_code_at:{WHIRLPOOL_PROGRAM}")
    pool_info = _rpc(rpc_url, "getAccountInfo", [pool, {"encoding": "base64"}])
    pool_val = (pool_info or {}).get("value")
    if not pool_val:
        raise RuntimeError(f"rpc_no_account_at:{pool}")
    import base64

    data = base64.b64decode(pool_val["data"][0])
    sqrt_price = "0"
    if len(data) >= 81:
        import struct

        sqrt_price = str(struct.unpack_from("<Q", data, 65)[0])
    slot = int(_rpc(rpc_url, "getSlot", [{"commitment": "confirmed"}]))
    return AccountResolution(
        program_id=WHIRLPOOL_PROGRAM,
        whirlpool=pool,
        slot=slot,
        lamports=int(pool_val.get("lamports") or 0),
        data_len=len(data),
        sqrt_price_hint=sqrt_price,
    )


__all__ = [
    "DEFAULT_WHIRLPOOL",
    "HARNESS_CHAIN",
    "HARNESS_NAME",
    "HARNESS_PLATFORM",
    "HARNESS_TARGET",
    "WHIRLPOOL_PROGRAM",
    "AccountResolution",
    "discriminators",
    "instruction_names",
    "load_idl",
    "program_ids",
    "resolve_accounts",
]