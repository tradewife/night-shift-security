"""Patch cloned Kamino Scope OraclePrices timestamps for validator depth probes."""

from __future__ import annotations

import base64
import json
import os
import struct
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from klend_account_discovery import load_klend_accounts

# Anchor discriminator for scope::OraclePrices (mainnet 3t4JZcue... account).
ORACLE_PRICES_DISCRIMINATOR = bytes.fromhex("598076dd0648b492")
DATED_PRICE_SIZE = 56
MAX_SCOPE_ENTRIES = 512
ORACLE_PRICES_HEADER_SIZE = 8 + 32  # disc + oracle_mappings pubkey
PRICE_VALUE_OFFSET_IN_ENTRY = 0
PRICE_EXP_OFFSET_IN_ENTRY = 8
LAST_UPDATED_SLOT_OFFSET_IN_ENTRY = 16
UNIX_TIMESTAMP_OFFSET_IN_ENTRY = 24


def _rpc(method: str, params: list | None, rpc_url: str) -> Any:
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}).encode()
    req = urllib.request.Request(rpc_url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode())
    if "error" in body:
        raise RuntimeError(f"RPC {method} failed: {body['error']}")
    return body["result"]


def fetch_account_snapshot(pubkey: str, *, rpc_url: str) -> dict[str, Any]:
    result = _rpc("getAccountInfo", [pubkey, {"encoding": "base64"}], rpc_url)
    value = result.get("value")
    if not value or not value.get("data"):
        raise RuntimeError(f"account missing: {pubkey}")
    return {
        "pubkey": pubkey,
        "lamports": int(value.get("lamports", 0)),
        "owner": str(value.get("owner", "")),
        "executable": bool(value.get("executable", False)),
        "rentEpoch": int(value.get("rentEpoch", 0)),
        "data": base64.b64decode(value["data"][0]),
    }


def patch_oracle_prices_timestamps(
    data: bytes,
    *,
    unix_timestamp: int | None = None,
    slot: int | None = None,
    price_manipulation_pct: float | None = None,
    target_entry_idx: int | None = None,
) -> tuple[bytes, int]:
    """Refresh DatedPrice unix_timestamp / last_updated_slot for populated Scope entries.

    Optionally manipulate price values to simulate oracle manipulation on the validator.
    price_manipulation_pct: e.g. 50.0 means inflate price by 50% (multiply value by 1.5).
    Negative values deflate: -50.0 means deflate by 50% (multiply value by 0.5).
    target_entry_idx: if set, only manipulate this entry; otherwise manipulate all.
    """
    if len(data) < ORACLE_PRICES_HEADER_SIZE + DATED_PRICE_SIZE:
        raise ValueError(f"scope account too short: {len(data)}")
    if data[:8] != ORACLE_PRICES_DISCRIMINATOR:
        raise ValueError(f"unexpected scope discriminator: {data[:8].hex()}")

    now_ts = int(unix_timestamp if unix_timestamp is not None else time.time())
    now_slot = int(slot if slot is not None else 0)
    patched = bytearray(data)
    updated = 0

    for entry_idx in range(MAX_SCOPE_ENTRIES):
        base = ORACLE_PRICES_HEADER_SIZE + entry_idx * DATED_PRICE_SIZE
        if base + DATED_PRICE_SIZE > len(patched):
            break
        value = struct.unpack_from("<Q", patched, base + PRICE_VALUE_OFFSET_IN_ENTRY)[0]
        exp = struct.unpack_from("<Q", patched, base + PRICE_EXP_OFFSET_IN_ENTRY)[0]
        if value == 0 and exp == 0:
            continue
        struct.pack_into("<Q", patched, base + UNIX_TIMESTAMP_OFFSET_IN_ENTRY, now_ts)
        if now_slot > 0:
            struct.pack_into("<Q", patched, base + LAST_UPDATED_SLOT_OFFSET_IN_ENTRY, now_slot)
        if price_manipulation_pct is not None:
            if target_entry_idx is None or target_entry_idx == entry_idx:
                factor = 1.0 + (price_manipulation_pct / 100.0)
                new_value = int(value * factor)
                new_value = max(1, min(new_value, (1 << 64) - 1))
                struct.pack_into("<Q", patched, base + PRICE_VALUE_OFFSET_IN_ENTRY, new_value)
        updated += 1

    return bytes(patched), updated


def write_validator_account_json(snapshot: dict[str, Any], *, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "pubkey": snapshot["pubkey"],
        "account": {
            "lamports": snapshot["lamports"],
            "data": [base64.b64encode(snapshot["data"]).decode(), "base64"],
            "owner": snapshot["owner"],
            "executable": snapshot["executable"],
            "rentEpoch": snapshot["rentEpoch"],
        },
    }
    out_path.write_text(json.dumps(payload) + "\n")
    return out_path


def scope_prices_pubkey() -> str:
    accounts = load_klend_accounts()
    return str(accounts["reserves"]["USDC"].get("scope_prices") or "")


def resolve_validator_unix_timestamp(*, rpc_url: str, slot: int | None = None) -> int:
    """Match Scope price age checks to the warped validator clock, not wall clock."""
    if slot and slot > 0:
        try:
            block_time = _rpc("getBlockTime", [slot], rpc_url)
            if block_time is not None:
                return int(block_time)
        except (RuntimeError, urllib.error.URLError, ValueError, TypeError):
            pass
    return int(time.time())


def scope_patch_unix_timestamp(*, rpc_url: str, slot: int | None = None) -> int:
    """Pad patched Scope timestamps ahead of post-setup validator clock drift on test-validator."""
    base = resolve_validator_unix_timestamp(rpc_url=rpc_url, slot=slot)
    buffer_s = int(os.environ.get("NSS_KLEND_SCOPE_TS_BUFFER", "90000"))
    return base + max(0, buffer_s)


def prepare_patched_scope_account_file(
    *,
    rpc_url: str,
    out_dir: Path,
    unix_timestamp: int | None = None,
    slot: int | None = None,
    price_manipulation_pct: float | None = None,
    target_entry_idx: int | None = None,
) -> tuple[str, Path, int]:
    """Fetch mainnet scope_prices, patch timestamps, write validator --account JSON."""
    pubkey = scope_prices_pubkey()
    if not pubkey:
        raise RuntimeError("scope_prices pubkey missing from klend_accounts.json")

    snapshot = fetch_account_snapshot(pubkey, rpc_url=rpc_url)
    effective_ts = (
        int(unix_timestamp)
        if unix_timestamp is not None
        else scope_patch_unix_timestamp(rpc_url=rpc_url, slot=slot)
    )
    patched_data, updated = patch_oracle_prices_timestamps(
        snapshot["data"],
        unix_timestamp=effective_ts,
        slot=slot,
        price_manipulation_pct=price_manipulation_pct,
        target_entry_idx=target_entry_idx,
    )
    snapshot["data"] = patched_data
    out_path = out_dir / f"scope_prices_{pubkey[:8]}.json"
    write_validator_account_json(snapshot, out_path=out_path)
    return pubkey, out_path, updated


def split_clone_accounts_for_scope_patch(
    clone_data_accounts: tuple[str, ...],
    scope_pubkey: str,
) -> tuple[tuple[str, ...], str | None]:
    """Remove scope_prices pubkey from --clone list when loading patched --account file."""
    if not scope_pubkey:
        return clone_data_accounts, None
    remaining = tuple(pubkey for pubkey in clone_data_accounts if pubkey and pubkey != scope_pubkey)
    removed = scope_pubkey if scope_pubkey in clone_data_accounts else None
    return remaining, removed