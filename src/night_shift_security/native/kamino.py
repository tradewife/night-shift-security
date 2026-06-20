"""Kamino KLend NativeHarness — Anchor lending surface (Immunefi $1.5M).

Solana per-target NativeHarness first shipped under v5 and preserved
under v6. Read-only substrate: program IDs, top-10 KLend instruction
discriminators, IDL loader, and ``resolve_market`` against mainnet RPC
(see ``SPEC.md`` §14 v5.0.0-shipped Phase 7).

Measured-impact (audit C2 Solana analogue) lives in
``night_shift_security.impact.solana_measured_oracle`` — not here.
"""

from __future__ import annotations

import json
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping
from urllib import error as urllib_error
from urllib import request as urllib_request

from night_shift_security.semantic.selectors import anchor_discriminator

# -------------------------------------------------------------------------- #
# Constants
# -------------------------------------------------------------------------- #

HARNESS_TARGET = "kamino"
HARNESS_PLATFORM = "immunefi"
HARNESS_CHAIN = "solana"
HARNESS_NAME = "Kamino"

KLEND_PROGRAM = "KLend2g3cP87fffoy8q1mQqGKjrxjC8boSyAYavgmjD"
KVAULT_PROGRAM = "KvauGMspG5k6rtzrqqn7WNn3oZdyKqLKwK2XWQ8FLjd"
ORACLE_PROGRAM = "HFn8GnPADiny6XqUoWE8uRPPxb29ikn4yTuPa9MF2fWJ"
FARMS_PROGRAM = "FarmsPZpWu9i7Kky8tPN37rs2TpmMrAZrC7S7vJa91Hr"
SPL_TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
SYSTEM_PROGRAM = "11111111111111111111111111111111"

DEFAULT_MARKET_PUBKEY = "7u3HeHxYDLhnCoErrtycNokbQYbWGzLs6JSDqGAv5PfF"
DEFAULT_USDC_RESERVE = "D6q6wuQSrifJKZYpR1M8R4YawnLDtDsMmWM1NbBmgJ59"
DEFAULT_USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

TOP_KLEND_INSTRUCTIONS: tuple[str, ...] = (
    "init_lending_market",
    "refresh_reserve",
    "deposit_reserve_liquidity",
    "redeem_reserve_collateral",
    "init_obligation",
    "refresh_obligation",
    "borrow_obligation_liquidity_v2",
    "repay_obligation_liquidity_v2",
    "liquidate_obligation_and_redeem_reserve_collateral_v2",
    "flash_borrow_reserve_liquidity",
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ACCOUNTS_PATH = _REPO_ROOT / "sources" / "kamino" / "klend_accounts.json"
DEFAULT_KLEND_REPO = _REPO_ROOT / "sources" / "kamino" / "klend"
DEFAULT_IDL_PATH = DEFAULT_KLEND_REPO / "target" / "idl" / "klend.json"


# -------------------------------------------------------------------------- #
# Public harness surface
# -------------------------------------------------------------------------- #


def program_ids() -> dict[str, str]:
    """Canonical Kamino / KLend program IDs on Solana mainnet."""
    return {
        "klend": KLEND_PROGRAM,
        "kvault": KVAULT_PROGRAM,
        "oracle": ORACLE_PROGRAM,
        "farms": FARMS_PROGRAM,
        "spl_token": SPL_TOKEN_PROGRAM,
        "system": SYSTEM_PROGRAM,
    }


def discriminators() -> dict[str, str]:
    """Top-10 KLend instruction discriminators (8-byte Anchor sighash)."""
    return OrderedDict(
        (name, anchor_discriminator(name)) for name in TOP_KLEND_INSTRUCTIONS
    )


def instruction_names() -> list[str]:
    return list(TOP_KLEND_INSTRUCTIONS)


def load_accounts(path: Path | str | None = None) -> dict[str, Any]:
    """Load cached mainnet account map (``sources/kamino/klend_accounts.json``)."""
    p = Path(path) if path is not None else DEFAULT_ACCOUNTS_PATH
    if not p.is_file():
        return {
            "market_pubkey": DEFAULT_MARKET_PUBKEY,
            "reserves": {
                "USDC": {
                    "pubkey": DEFAULT_USDC_RESERVE,
                    "mint": DEFAULT_USDC_MINT,
                }
            },
        }
    return json.loads(p.read_text())


def load_idl(repo_path: Path | str | None = None) -> dict[str, Any]:
    """Load KLend IDL from Forge artifact or synthesise from instruction names."""
    repo = Path(repo_path) if repo_path is not None else DEFAULT_KLEND_REPO
    candidates = [
        repo / "target" / "idl" / "klend.json",
        repo / "idl" / "klend.json",
        DEFAULT_IDL_PATH,
    ]
    for candidate in candidates:
        if candidate.is_file():
            try:
                payload = json.loads(candidate.read_text())
                if isinstance(payload, dict) and payload.get("instructions"):
                    return payload
            except (OSError, ValueError, json.JSONDecodeError):
                pass
    return _inline_idl()


def _inline_idl() -> dict[str, Any]:
    instructions = [
        {
            "name": name,
            "discriminator": list(bytes.fromhex(anchor_discriminator(name).removeprefix("0x"))),
        }
        for name in TOP_KLEND_INSTRUCTIONS
    ]
    return {
        "address": KLEND_PROGRAM,
        "metadata": {"name": "klend", "spec": "inline-canonical"},
        "instructions": instructions,
    }


# -------------------------------------------------------------------------- #
# Market resolver — Solana RPC
# -------------------------------------------------------------------------- #


@dataclass
class AccountResolution:
    """Result of ``resolve_market`` / ``resolve_accounts``."""

    market_pubkey: str
    reserve_pubkey: str
    program_id: str
    slot: int
    lamports: int
    data_len: int
    executable: bool
    owner: str
    reserve_symbol: str = "USDC"
    accounts_path: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "market_pubkey": self.market_pubkey,
            "reserve_pubkey": self.reserve_pubkey,
            "program_id": self.program_id,
            "slot": int(self.slot),
            "lamports": int(self.lamports),
            "data_len": int(self.data_len),
            "executable": bool(self.executable),
            "owner": self.owner,
            "reserve_symbol": self.reserve_symbol,
            "accounts_path": self.accounts_path,
            "extra": self.extra,
        }


def _call_rpc(rpc_url: str, method: str, params: list[Any], timeout: float = 15.0) -> Any:
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib_request.Request(
        rpc_url,
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib_request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            body = json.loads(resp.read().decode())
    except urllib_error.URLError as exc:
        raise RuntimeError(f"rpc_url_unreachable:{method}:{exc.reason}") from exc
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"rpc_invalid_response:{method}:{exc}") from exc

    if isinstance(body, dict) and body.get("error"):
        err = body["error"]
        raise RuntimeError(
            f"rpc_error:{method}:{err.get('code')}:{err.get('message')}"
        )
    return body.get("result") if isinstance(body, dict) else None


def get_slot(rpc_url: str) -> int:
    result = _call_rpc(rpc_url, "getSlot", [{"commitment": "confirmed"}])
    if not isinstance(result, int):
        raise RuntimeError(f"rpc_invalid_response:getSlot:expected_int,got={type(result).__name__}")
    return result


def get_account_info(pubkey: str, rpc_url: str) -> dict[str, Any]:
    result = _call_rpc(
        rpc_url,
        "getAccountInfo",
        [pubkey, {"encoding": "base64", "commitment": "confirmed"}],
    )
    if not isinstance(result, dict):
        raise RuntimeError(
            f"rpc_invalid_response:getAccountInfo:expected_dict,got={type(result).__name__}"
        )
    return result


def resolve_market(
    market_hint: str | Mapping[str, Any] | None = None,
    rpc_url: str = "",
    *,
    reserve_symbol: str = "USDC",
    accounts_path: Path | str | None = None,
) -> AccountResolution:
    """Confirm KLend market + USDC reserve accounts exist on ``rpc_url``."""
    if not rpc_url:
        raise RuntimeError("rpc_url_required:resolve_market")

    accounts = load_accounts(accounts_path)
    if isinstance(market_hint, Mapping):
        market_pubkey = str(market_hint.get("market_pubkey") or accounts.get("market_pubkey") or DEFAULT_MARKET_PUBKEY)
    elif isinstance(market_hint, str) and market_hint:
        market_pubkey = market_hint
    else:
        market_pubkey = str(accounts.get("market_pubkey") or DEFAULT_MARKET_PUBKEY)

    reserves = accounts.get("reserves") or {}
    reserve_entry = reserves.get(reserve_symbol.upper()) or reserves.get(reserve_symbol) or {}
    reserve_pubkey = str(
        reserve_entry.get("pubkey")
        or (reserve_entry if isinstance(reserve_entry, str) else "")
        or DEFAULT_USDC_RESERVE
    )

    program_info = get_account_info(KLEND_PROGRAM, rpc_url)
    program_value = program_info.get("value")
    if not program_value:
        raise RuntimeError(f"rpc_no_code_at:{KLEND_PROGRAM}:expected_deployed_KLend_program")
    if not program_value.get("executable"):
        raise RuntimeError(f"rpc_not_executable:{KLEND_PROGRAM}:expected_program_account")

    market_info = get_account_info(market_pubkey, rpc_url)
    market_value = market_info.get("value")
    if not market_value:
        raise RuntimeError(f"rpc_no_account_at:{market_pubkey}:expected_lending_market")

    reserve_info = get_account_info(reserve_pubkey, rpc_url)
    reserve_value = reserve_info.get("value")
    if not reserve_value:
        raise RuntimeError(f"rpc_no_account_at:{reserve_pubkey}:expected_reserve_account")

    slot = get_slot(rpc_url)
    data_field = reserve_value.get("data")
    data_len = 0
    if isinstance(data_field, list) and data_field:
        try:
            import base64

            data_len = len(base64.b64decode(data_field[0]))
        except (ValueError, TypeError):
            data_len = 0

    return AccountResolution(
        market_pubkey=market_pubkey,
        reserve_pubkey=reserve_pubkey,
        program_id=KLEND_PROGRAM,
        slot=slot,
        lamports=int(reserve_value.get("lamports") or 0),
        data_len=data_len,
        executable=bool(program_value.get("executable")),
        owner=str(reserve_value.get("owner") or KLEND_PROGRAM),
        reserve_symbol=reserve_symbol.upper(),
        accounts_path=str(accounts_path or DEFAULT_ACCOUNTS_PATH),
        extra={
            "supply_vault": (reserve_entry.get("supply_vault") if isinstance(reserve_entry, dict) else ""),
            "mint": (reserve_entry.get("mint") if isinstance(reserve_entry, dict) else DEFAULT_USDC_MINT),
        },
    )


def resolve_accounts(
    market_hint: str,
    rpc_url: str,
    *,
    reserve_symbol: str = "USDC",
) -> AccountResolution:
    """Alias required by SPEC §6 Solana contract."""
    return resolve_market(market_hint, rpc_url, reserve_symbol=reserve_symbol)


__all__ = [
    "DEFAULT_ACCOUNTS_PATH",
    "DEFAULT_KLEND_REPO",
    "DEFAULT_MARKET_PUBKEY",
    "DEFAULT_USDC_MINT",
    "DEFAULT_USDC_RESERVE",
    "FARMS_PROGRAM",
    "HARNESS_CHAIN",
    "HARNESS_NAME",
    "HARNESS_PLATFORM",
    "HARNESS_TARGET",
    "KLEND_PROGRAM",
    "KVAULT_PROGRAM",
    "ORACLE_PROGRAM",
    "TOP_KLEND_INSTRUCTIONS",
    "AccountResolution",
    "discriminators",
    "get_account_info",
    "get_slot",
    "instruction_names",
    "load_accounts",
    "load_idl",
    "program_ids",
    "resolve_accounts",
    "resolve_market",
]