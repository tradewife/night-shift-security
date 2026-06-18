"""Raydium NativeHarness — CLMM surface (Immunefi $505K)."""

from __future__ import annotations

import json
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

from night_shift_security.semantic.selectors import anchor_discriminator

HARNESS_TARGET = "raydium"
HARNESS_PLATFORM = "immunefi"
HARNESS_CHAIN = "solana"
HARNESS_NAME = "Raydium"

CLMM_PROGRAM = "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK"
DEFAULT_POOL_STATE = "3ucNos4NbumPLZNkztM7FWCLUYS2i9WkBB6Z3t6j9FL"  # optional; may be absent on RPC

TOP_INSTRUCTIONS: tuple[str, ...] = (
    "create_pool",
    "open_position",
    "open_position_v2",
    "increase_liquidity",
    "decrease_liquidity",
    "swap",
    "swap_v2",
    "collect_fund_fee",
    "collect_protocol_fee",
    "update_pool_status",
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REPO = _REPO_ROOT / "sources" / "raydium" / "repo"


def program_ids() -> dict[str, str]:
    return {"clmm": CLMM_PROGRAM}


def discriminators() -> dict[str, str]:
    return OrderedDict((n, anchor_discriminator(n)) for n in TOP_INSTRUCTIONS)


def instruction_names() -> list[str]:
    return list(TOP_INSTRUCTIONS)


def load_idl(repo_path: Path | str | None = None) -> dict[str, Any]:
    repo = Path(repo_path) if repo_path is not None else DEFAULT_REPO
    artifact = repo / "target" / "idl" / "amm_v3.json"
    if artifact.is_file():
        try:
            return json.loads(artifact.read_text())
        except (OSError, ValueError, json.JSONDecodeError):
            pass
    return {
        "address": CLMM_PROGRAM,
        "instructions": [
            {"name": n, "discriminator": list(bytes.fromhex(anchor_discriminator(n).removeprefix("0x")))}
            for n in TOP_INSTRUCTIONS
        ],
    }


@dataclass
class AccountResolution:
    program_id: str
    pool_state: str
    slot: int
    lamports: int
    data_len: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "program_id": self.program_id,
            "pool_state": self.pool_state,
            "slot": int(self.slot),
            "lamports": int(self.lamports),
            "data_len": int(self.data_len),
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
    pool = market_hint or DEFAULT_POOL_STATE
    prog = _rpc(rpc_url, "getAccountInfo", [CLMM_PROGRAM, {"encoding": "base64"}])
    prog_val = (prog or {}).get("value")
    if not prog_val:
        raise RuntimeError(f"rpc_no_code_at:{CLMM_PROGRAM}")
    pool_val = None
    if pool:
        try:
            pool_info = _rpc(rpc_url, "getAccountInfo", [pool, {"encoding": "base64"}])
            pool_val = (pool_info or {}).get("value")
        except RuntimeError:
            pool_val = None
    import base64

    data_len = 0
    lamports = int(prog_val.get("lamports") or 0)
    if pool_val:
        data = base64.b64decode(pool_val["data"][0])
        data_len = len(data)
        lamports = int(pool_val.get("lamports") or 0)
    slot = int(_rpc(rpc_url, "getSlot", [{"commitment": "confirmed"}]))
    return AccountResolution(
        program_id=CLMM_PROGRAM,
        pool_state=pool if pool_val else "",
        slot=slot,
        lamports=lamports,
        data_len=data_len,
    )


__all__ = [
    "CLMM_PROGRAM",
    "DEFAULT_POOL_STATE",
    "HARNESS_CHAIN",
    "HARNESS_NAME",
    "HARNESS_PLATFORM",
    "HARNESS_TARGET",
    "AccountResolution",
    "discriminators",
    "instruction_names",
    "load_idl",
    "program_ids",
    "resolve_accounts",
]