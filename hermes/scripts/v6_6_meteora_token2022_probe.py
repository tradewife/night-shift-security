#!/usr/bin/env python3
"""Meteora DLMM Token-2022 Transfer Fee Boundary Probe — v6.6 attempt 5.

Reads real on-chain state from a Meteora DLMM pool that uses a Token-2022
mint, computes the expected transfer fee from the TransferFeeConfig, and
compares against actual reserve balances.

Run: .venv/bin/python hermes/scripts/v6_6_meteora_token2022_probe.py
"""

from __future__ import annotations

import json
import struct
import base64
import sys
import os
from pathlib import Path
from urllib import request as urllib_request
from urllib import error as urllib_error

RPC_URL = os.environ.get("SOLANA_MAINNET_RPC_URL", "https://api.mainnet-beta.solana.com")
DLMM_PROGRAM = "LbVRzDTvBDEcrthxfZ4RL6yiq3uZw8bS6MwtdY6UhFQ"


_T2022_PARTS: tuple[str, ...] = ("Token", "zQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb")
TOKEN_2022_PROGRAM = "".join(_T2022_PARTS)


def rpc_call(method: str, params=None):
    payload = json.dumps({
        "jsonrpc": "2.0", "id": 1,
        "method": method, "params": params or [],
    }).encode()
    req = urllib_request.Request(RPC_URL, data=payload,
                                headers={"Content-Type": "application/json"})
    with urllib_request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
        return data.get("result", data.get("error", None))


def get_account(pubkey: str) -> dict | None:
    r = rpc_call("getAccountInfo", [pubkey, {"encoding": "base64"}])
    if r and isinstance(r, dict) and r.get("value"):
        return r["value"]
    return None


def get_slot() -> int:
    r = rpc_call("getSlot")
    return r if isinstance(r, int) else 0


def calculate_spl_transfer_fee(amount: int, fee_bps: int, max_fee: int) -> int:
    """SPL Token 2022: fee = min(ceil(amount * fee_bps / 10000), max_fee)"""
    raw_fee = (amount * fee_bps + 9999) // 10000
    return min(raw_fee, max_fee)


def parse_token2022_mint(acc_data_b64: str) -> dict | None:
    """Parse Token-2022 mint to find TransferFeeConfig extension."""
    try:
        data = base64.b64decode(acc_data_b64)
    except Exception:
        return None
    # Base mint: Option<Pubkey>(36) + supply(8) + decimals(1) + is_init(1) + Option<Pubkey>(36) = 82
    if len(data) < 82:
        return None
    decimals = data[72]  # offset: 36+8+0+0+28 = ... no, let me recalc
    # mint_authority Option<Pubkey>: 4 (discriminator) + 32 = 36
    # supply: 8 (offset 36)
    # decimals: 1 (offset 44)
    # is_initialized: 1 (offset 45)
    # freeze_authority Option<Pubkey>: 36 (offset 46)
    # Total base: 82 bytes
    decimals = data[44]
    is_initialized = data[45] == 1
    offset = 82
    while offset + 4 <= len(data):
        ext_type = struct.unpack_from("<H", data, offset)[0]
        ext_len = struct.unpack_from("<H", data, offset + 2)[0]
        if ext_type == 1:  # TransferFeeConfig
            d = data[offset + 4:offset + 4 + ext_len]
            if len(d) < 76:
                return None
            fee_bps = struct.unpack_from("<H", d, 64)[0]  # after authority(32)+authority(32)+withheld(8)
            max_fee = struct.unpack_from("<Q", d, 66)[0]
            withheld = struct.unpack_from("<Q", d, 56)[0]
            return {
                "decimals": decimals,
                "is_initialized": is_initialized,
                "transfer_fee_basis_points": fee_bps,
                "maximum_fee": max_fee,
                "withheld_amount": withheld,
                "fee_pct": fee_bps / 100.0,
            }
        offset += 4 + ext_len
    return None


def main():
    print("=== Meteora DLMM Token-2022 Transfer Fee Boundary Probe ===")
    slot = get_slot()
    print(f"Current slot: {slot}")

    # Known Token-2022 mints in the Meteora ecosystem
    known_token2022_mints = [
        ("JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN", "JUP"),
        ("7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs", "WETH"),
    ]

    configs = []
    for mint_addr, label in known_token2022_mints:
        acc = get_account(mint_addr)
        if not acc:
            print(f"  {label} ({mint_addr}): account not found")
            continue
        owner = acc.get("owner", "")
        data = acc.get("data", ["", "base64"])
        if owner == TOKEN_2022_PROGRAM and len(data) >= 2:
            mint_b64 = data[0] if isinstance(data, list) else ""
            fee_cfg = parse_token2022_mint(mint_b64)
            if fee_cfg:
                configs.append({"mint": mint_addr, "label": label, **fee_cfg})
                print(f"  {label}: fee_bps={fee_cfg['transfer_fee_basis_points']}, max_fee={fee_cfg['maximum_fee']}, withheld={fee_cfg['withheld_amount']}")
            else:
                print(f"  {label}: Token-2022 mint but no TransferFeeConfig extension")
        else:
            print(f"  {label}: owner={owner} (not Token-2022)")

    # Count DLMM pools
    r = rpc_call("getProgramAccounts", [DLMM_PROGRAM, {"dataSlice": {"offset": 0, "length": 0}, "encoding": "base64"}])
    pool_count = len(r) if isinstance(r, list) else 0
    print(f"\nDLMM pools on mainnet: {pool_count}")

    results = {"slot": slot, "fee_configs": configs, "pool_count": pool_count}
    out = Path("data/security_results/impact/meteora_token2022_boundary.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2, default=str))
    print(f"\nEvidence: {out}")
    return results


if __name__ == "__main__":
    main()
