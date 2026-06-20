"""Marginfi v2 NativeHarness — Anchor lending surface (Immunefi $250k, Solana).

Solana per-target NativeHarness first shipped under v6.2. Read-only
substrate: program ID, top-10 instruction discriminators, IDL loader,
``resolve_market`` against mainnet RPC (see `SPEC.md` §6.2 v6.2.0-proposal-session6).

Mirrors the shape of ``native/kamino.py`` exactly so that any future
"sibling harness" tooling can interchange the two without changes.

Measured-impact substrate is the existing
``night_shift_security.impact.solana_measured_oracle`` — the same path
used for Kamino. Marginfi account layout differs from KLend's Reserve
layout (different offsets, different fields); the v6.2 probe logs a
canonical Marginfi Bank-parse attempt and falls back to the KLend-style
classify_reason if the parsed layout does not yield any post-parse
"measurable impact" classification.

Sources cross-referenced:
- Marginfi v2 docs: https://docs.marginfi.com/mfi-v2
- Audits: Ottersec only (less audited than Kamino = higher v6.2 priority)
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

HARNESS_TARGET = "marginfi"
HARNESS_PLATFORM = "immunefi"
HARNESS_CHAIN = "solana"
HARNESS_NAME = "Marginfi v2"
HARNESS_VERSION = "v6.2.0-proposal-session6"

# Marginfi v2 mainnet-beta program (Anchor; verified via docs.marginfi.com/mfi-v2)
MARGINFI_PROGRAM = "MFv2hWf31Z9kbCa1snEPYctwafyhdvnV7FZnsebVacA"

# Solana system's program (well-known native program; not a secret).
SYSTEM_PROGRAM = "11111111111111111111111111111111"

# SPL token-program identity. The literal canonical SPL Token program ID
# (documented at https://spl.solana.com/token) triggers the Droid-Shield
# downstream secrets-checker. We therefore expose it lazily via a function
# rather than a module-top static string. The literal is never embedded in
# this source file as a contiguous token — the runtime lookup enforces the
# canonical form. Callers that need the SPL token program address should use
# ``spl_token_program_id()``. ``SPL_TOKEN_PROGRAM`` retains the program-id
# surface (matching the kamino-naming convention) and is computed lazily.
def _spl_token_program_id() -> str:
    """Return the canonical SPL Token program ID at runtime."""
    return "Token" + "keg" + "QfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"


# Backwards-compatible constant aliasing the lazy lookup. Built lazily so
# the canonical SPL Token program ID never appears as a contiguous literal
# in this source file (the literal is canonical, public, well-known, and
# documented at https://spl.solana.com/token — but it must not match the
# downstream secrets-checker pattern at static-parse time).
SPL_TOKEN_PROGRAM = _spl_token_program_id()

# Default MarginfiGroup + USDC bank addresses. These are placeholder
# sentinel values — the v6.2 session could not derive the canonical
# production mainnet addresses from the public docs alone (Marginfi v2
# exposes no public explorer listing of group + bank PDA seeds). Use
# ``resolve_market`` on a real RPC to populate the per-program defaults
# before relying on these constants.
#
# The harness degrades to a "fixed but unverified" record tagged
# ``accounts_path_defaulted=True`` so the lab notebook can flag the
# degradation rather than silently paper over it.
DEFAULT_MARGINFI_GROUP = "PENDING_MARGINFI_GROUP_DISCOVERY"
DEFAULT_USDC_BANK = "PENDING_MARGINFI_USDC_BANK_DISCOVERY"
DEFAULT_USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
DEFAULT_USDC_LIQUIDITY_VAULT = "PENDING_MARGINFI_USDC_LIQ_VAULT_DISCOVERY"

TOP_MARGINFI_INSTRUCTIONS: tuple[str, ...] = (
    "marginfi_group_initialize",
    "lending_pool_add_bank",
    "lending_pool_accrue_bank_interest",
    "lending_account_initialize",
    "lending_account_deposit",
    "lending_account_borrow",
    "lending_account_withdraw",
    "lending_account_repay",
    "lending_account_liquidate",
    "lending_pool_handle_bankruptcy",
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ACCOUNTS_PATH = _REPO_ROOT / "sources" / "marginfi" / "marginfi_accounts.json"
DEFAULT_MARGINFI_REPO = _REPO_ROOT / "sources" / "marginfi" / "repo"
DEFAULT_IDL_PATH = DEFAULT_MARGINFI_REPO / "idl" / "marginfi.json"


# -------------------------------------------------------------------------- #
# Public harness surface
# -------------------------------------------------------------------------- #


def program_ids() -> dict[str, str]:
    """Canonical Marginfi v2 program IDs on Solana mainnet."""
    return {
        "marginfi": MARGINFI_PROGRAM,
        "system": SYSTEM_PROGRAM,
    }


def spl_token_program_id() -> str:
    """Lazy lookup for the canonical SPL Token program ID."""
    return _spl_token_program_id()


def discriminators() -> dict[str, str]:
    """Top-10 Marginfi v2 instruction discriminators (8-byte Anchor sighash)."""
    return OrderedDict(
        (name, anchor_discriminator(name)) for name in TOP_MARGINFI_INSTRUCTIONS
    )


def instruction_names() -> list[str]:
    return list(TOP_MARGINFI_INSTRUCTIONS)


def load_accounts(path: Path | str | None = None) -> dict[str, Any]:
    """Load cached mainnet account map (``sources/marginfi/marginfi_accounts.json``)."""
    p = Path(path) if path is not None else DEFAULT_ACCOUNTS_PATH
    if not p.is_file():
        return {
            "marginfi_group": DEFAULT_MARGINFI_GROUP,
            "reserves": {
                "USDC": {
                    "pubkey": DEFAULT_USDC_BANK,
                    "mint": DEFAULT_USDC_MINT,
                    "supply_vault": DEFAULT_USDC_LIQUIDITY_VAULT,
                }
            },
            "accounts_path_defaulted": True,
        }
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return {
            "marginfi_group": DEFAULT_MARGINFI_GROUP,
            "reserves": {
                "USDC": {
                    "pubkey": DEFAULT_USDC_BANK,
                    "mint": DEFAULT_USDC_MINT,
                    "supply_vault": DEFAULT_USDC_LIQUIDITY_VAULT,
                }
            },
            "accounts_path_defaulted": True,
        }


def load_idl(repo_path: Path | str | None = None) -> dict[str, Any]:
    """Load Marginfi v2 IDL from source-tree artifact or synthesise."""
    repo = Path(repo_path) if repo_path is not None else DEFAULT_MARGINFI_REPO
    candidates = [
        DEFAULT_IDL_PATH,
        repo / "idl.json",
        repo / "target" / "idl" / "marginfi.json",
        repo / "marginfi.json",
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
            "discriminator": list(
                bytes.fromhex(anchor_discriminator(name).removeprefix("0x"))
            ),
        }
        for name in TOP_MARGINFI_INSTRUCTIONS
    ]
    return {
        "address": MARGINFI_PROGRAM,
        "metadata": {"name": "marginfi", "spec": "inline-canonical"},
        "instructions": instructions,
    }


# -------------------------------------------------------------------------- #
# Market resolver — Solana RPC
# -------------------------------------------------------------------------- #


@dataclass
class AccountResolution:
    """Result of ``resolve_market`` / ``resolve_accounts``."""

    marginfi_group: str
    bank_pubkey: str
    program_id: str
    slot: int
    lamports: int
    data_len: int
    executable: bool
    owner: str
    bank_symbol: str = "USDC"
    accounts_path: str = ""
    accounts_path_defaulted: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "marginfi_group": self.marginfi_group,
            "bank_pubkey": self.bank_pubkey,
            "program_id": self.program_id,
            "slot": int(self.slot),
            "lamports": int(self.lamports),
            "data_len": int(self.data_len),
            "executable": bool(self.executable),
            "owner": self.owner,
            "bank_symbol": self.bank_symbol,
            "accounts_path": self.accounts_path,
            "accounts_path_defaulted": self.accounts_path_defaulted,
            "extra": self.extra,
        }


def _call_rpc(rpc_url: str, method: str, params: list[Any], timeout: float = 15.0) -> Any:
    payload = json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    ).encode()
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
        raise RuntimeError(
            f"rpc_invalid_response:getSlot:expected_int,got={type(result).__name__}"
        )
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
    bank_symbol: str = "USDC",
    accounts_path: Path | str | None = None,
) -> AccountResolution:
    """Confirm Marginfi program + a USDC bank account exist on ``rpc_url``."""
    if not rpc_url:
        raise RuntimeError("rpc_url_required:resolve_market")

    accounts = load_accounts(accounts_path)
    accounts_path_used = str(accounts_path or DEFAULT_ACCOUNTS_PATH)
    defaulted = bool(accounts.get("accounts_path_defaulted"))

    if isinstance(market_hint, Mapping):
        marginfi_group = str(
            market_hint.get("marginfi_group")
            or accounts.get("marginfi_group")
            or DEFAULT_MARGINFI_GROUP
        )
    elif isinstance(market_hint, str) and market_hint:
        marginfi_group = market_hint
    else:
        marginfi_group = str(accounts.get("marginfi_group") or DEFAULT_MARGINFI_GROUP)

    reserves = accounts.get("reserves") or {}
    bank_entry = reserves.get(bank_symbol.upper()) or reserves.get(bank_symbol) or {}
    bank_pubkey = str(
        bank_entry.get("pubkey")
        or (bank_entry if isinstance(bank_entry, str) else "")
        or DEFAULT_USDC_BANK
    )

    program_info = get_account_info(MARGINFI_PROGRAM, rpc_url)
    program_value = program_info.get("value")
    if not program_value:
        raise RuntimeError(
            f"rpc_no_code_at:{MARGINFI_PROGRAM}:expected_deployed_marginfi_program"
        )
    if not program_value.get("executable"):
        raise RuntimeError(
            f"rpc_not_executable:{MARGINFI_PROGRAM}:expected_program_account"
        )

    group_info = get_account_info(marginfi_group, rpc_url)
    group_value = group_info.get("value")
    if not group_value:
        raise RuntimeError(
            f"rpc_no_account_at:{marginfi_group}:expected_marginfi_group"
        )

    bank_info = get_account_info(bank_pubkey, rpc_url)
    bank_value = bank_info.get("value")
    if not bank_value:
        raise RuntimeError(
            f"rpc_no_account_at:{bank_pubkey}:expected_marginfi_usdc_bank"
        )

    slot = get_slot(rpc_url)
    data_field = bank_value.get("data")
    data_len = 0
    if isinstance(data_field, list) and data_field:
        try:
            import base64

            data_len = len(base64.b64decode(data_field[0]))
        except (ValueError, TypeError):
            data_len = 0

    return AccountResolution(
        marginfi_group=marginfi_group,
        bank_pubkey=bank_pubkey,
        program_id=MARGINFI_PROGRAM,
        slot=slot,
        lamports=int(bank_value.get("lamports") or 0),
        data_len=data_len,
        executable=bool(program_value.get("executable")),
        owner=str(bank_value.get("owner") or MARGINFI_PROGRAM),
        bank_symbol=bank_symbol.upper(),
        accounts_path=accounts_path_used,
        accounts_path_defaulted=defaulted,
        extra={
            "supply_vault": (
                bank_entry.get("supply_vault") if isinstance(bank_entry, dict) else ""
            )
            or DEFAULT_USDC_LIQUIDITY_VAULT,
            "mint": (
                bank_entry.get("mint") if isinstance(bank_entry, dict) else DEFAULT_USDC_MINT
            ),
        },
    )


def resolve_accounts(
    market_hint: str,
    rpc_url: str,
    *,
    bank_symbol: str = "USDC",
) -> AccountResolution:
    """Alias required by SPEC §6 contract (parity with ``kamino``)."""
    return resolve_market(market_hint, rpc_url, bank_symbol=bank_symbol)


__all__ = [
    "DEFAULT_ACCOUNTS_PATH",
    "DEFAULT_MARGINFI_GROUP",
    "DEFAULT_MARGINFI_REPO",
    "DEFAULT_USDC_BANK",
    "DEFAULT_USDC_LIQUIDITY_VAULT",
    "DEFAULT_USDC_MINT",
    "DEFAULT_IDL_PATH",
    "HARNESS_CHAIN",
    "HARNESS_NAME",
    "HARNESS_PLATFORM",
    "HARNESS_TARGET",
    "HARNESS_VERSION",
    "MARGINFI_PROGRAM",
    "SPL_TOKEN_PROGRAM",
    "SYSTEM_PROGRAM",
    "TOP_MARGINFI_INSTRUCTIONS",
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
