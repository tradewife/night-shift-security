"""Jito NativeHarness — stake pool + tip payment surface (Immunefi $2M)."""

from __future__ import annotations

import json
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

from night_shift_security.semantic.selectors import anchor_discriminator

HARNESS_TARGET = "jito"
HARNESS_PLATFORM = "immunefi"
HARNESS_CHAIN = "solana"
HARNESS_NAME = "Jito"

SPL_STAKE_POOL_PROGRAM = "SPoo1Ku8WFXoNDMHPsrGSTSG1Y47rzgn41SLUNakuHy"
JITO_STAKE_POOL = "Jito4APyf642JPZPx3hGc6WWJ8zPKtRbRs4P815Awbb"
INTERCEPTOR_PROGRAM = "5TAiuAh3YGDbwjEruC1ZpXTJWdNDS7Ur7VeqNNiHMmGV"
JITOSOL_MINT = "J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn"

TOP_INSTRUCTIONS: tuple[str, ...] = (
    "initialize",
    "deposit",
    "withdraw",
    "claim",
    "update_stake_pool",
    "update_tip_distribution",
    "claim_tips",
    "close_tip_distribution_account",
    "initialize_tip_distribution_account",
    "update_validator_list",
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REPO = _REPO_ROOT / "sources" / "jito" / "repo"


def program_ids() -> dict[str, str]:
    return {
        "spl_stake_pool": SPL_STAKE_POOL_PROGRAM,
        "jito_stake_pool": JITO_STAKE_POOL,
        "interceptor": INTERCEPTOR_PROGRAM,
        "jitosol_mint": JITOSOL_MINT,
    }


def discriminators() -> dict[str, str]:
    return OrderedDict((n, anchor_discriminator(n)) for n in TOP_INSTRUCTIONS)


def instruction_names() -> list[str]:
    return list(TOP_INSTRUCTIONS)


def load_idl(repo_path: Path | str | None = None) -> dict[str, Any]:
    repo = Path(repo_path) if repo_path is not None else DEFAULT_REPO
    for candidate in (repo / "target" / "idl" / "jito_stake.json", repo / "idl.json"):
        if candidate.is_file():
            try:
                return json.loads(candidate.read_text())
            except (OSError, ValueError, json.JSONDecodeError):
                pass
    return {
        "address": SPL_STAKE_POOL_PROGRAM,
        "instructions": [
            {"name": n, "discriminator": list(bytes.fromhex(anchor_discriminator(n).removeprefix("0x")))}
            for n in TOP_INSTRUCTIONS
        ],
    }


@dataclass
class AccountResolution:
    program_id: str
    slot: int
    lamports: int
    executable: bool
    hint: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "program_id": self.program_id,
            "slot": int(self.slot),
            "lamports": int(self.lamports),
            "executable": bool(self.executable),
            "hint": self.hint,
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
    program = market_hint or SPL_STAKE_POOL_PROGRAM
    info = _rpc(rpc_url, "getAccountInfo", [program, {"encoding": "base64"}])
    value = (info or {}).get("value")
    if not value:
        raise RuntimeError(f"rpc_no_code_at:{program}")
    slot = _rpc(rpc_url, "getSlot", [{"commitment": "confirmed"}])
    return AccountResolution(
        program_id=program,
        slot=int(slot),
        lamports=int(value.get("lamports") or 0),
        executable=bool(value.get("executable")),
        hint=market_hint,
    )


__all__ = [
    "HARNESS_CHAIN",
    "HARNESS_NAME",
    "HARNESS_PLATFORM",
    "HARNESS_TARGET",
    "INTERCEPTOR_PROGRAM",
    "JITOSOL_MINT",
    "JITO_STAKE_POOL",
    "SPL_STAKE_POOL_PROGRAM",
    "AccountResolution",
    "discriminators",
    "instruction_names",
    "load_idl",
    "program_ids",
    "resolve_accounts",
]