#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from decimal import Decimal, getcontext
from typing import Any

getcontext().prec = 80

ETHENA_ARM = "0xCEDa2d856238aA0D12f6329de20B9115f07C366d"
SUSDE = "0x9D39A5DE30e57443BfF2A8307A4256c8797A3497"
USDE = "0x4c9EDD5852cd905f086C759E8383e09bff1E68B3"


def cast_call(rpc: str, address: str, sig: str, *args: str) -> str:
    cmd = ["cast", "call", address, sig, *args, "--rpc-url", rpc]
    return subprocess.check_output(cmd, text=True).strip()


def parse_first_int(raw: str) -> int:
    return int(re.findall(r"(?<![\w.])-?\d+(?![\w.])", raw)[0])


def parse_ints(raw: str) -> list[int]:
    return [int(x) for x in re.findall(r"(?<![\w.])-?\d+(?![\w.])", raw)]


def parse_bool(raw: str) -> bool:
    return raw.strip().lower() == "true"


def quantify(queue_assets_raw: int, cross_price_raw: int, attacker_deposit_raw: int, total_assets_raw: int) -> dict[str, str]:
    scale = Decimal(10) ** 36
    one = Decimal(1)
    queue = Decimal(queue_assets_raw)
    cross = Decimal(cross_price_raw) / scale
    discount_release = queue * (one - cross)
    if total_assets_raw + attacker_deposit_raw == 0:
        extractable = Decimal(0)
    else:
        extractable = discount_release * Decimal(attacker_deposit_raw) / Decimal(total_assets_raw + attacker_deposit_raw)
    return {
        "cross_price": str(cross),
        "discount_bps": str((one - cross) * Decimal(10000)),
        "discount_release_raw": str(int(discount_release)),
        "extractable_raw": str(int(extractable)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only Origin ARM JIT-1 monitor")
    parser.add_argument("--rpc", default=os.environ.get("MAINNET_URL") or os.environ.get("PROVIDER_URL") or "https://ethereum.publicnode.com")
    parser.add_argument("--attacker-deposit-raw", default="0", help="Optional simulated JIT deposit in liquidity-asset raw units. Defaults to totalAssets.")
    args = parser.parse_args()

    block = int(subprocess.check_output(["cast", "block-number", "--rpc-url", args.rpc], text=True).strip())
    total_assets = parse_first_int(cast_call(args.rpc, ETHENA_ARM, "totalAssets()(uint256)"))
    total_supply = parse_first_int(cast_call(args.rpc, ETHENA_ARM, "totalSupply()(uint256)"))
    paused = parse_bool(cast_call(args.rpc, ETHENA_ARM, "paused()(bool)"))
    liq_balance = parse_first_int(cast_call(args.rpc, USDE, "balanceOf(address)(uint256)", ETHENA_ARM))
    base_balance = parse_first_int(cast_call(args.rpc, SUSDE, "balanceOf(address)(uint256)", ETHENA_ARM))
    config_raw = cast_call(
        args.rpc,
        ETHENA_ARM,
        "baseAssetConfigs(address)((uint128,uint128,uint128,uint128,uint128,uint120,bool,address))",
        SUSDE,
    )
    parts = parse_ints(config_raw)
    cross_price = parts[4]
    pending = parts[5]
    attacker_deposit = int(args.attacker_deposit_raw)
    if attacker_deposit == 0:
        attacker_deposit = total_assets

    result: dict[str, Any] = {
        "target": "origin-jit-1-monitor",
        "block": block,
        "arm": ETHENA_ARM,
        "base_asset": SUSDE,
        "liquidity_asset": USDE,
        "paused": paused,
        "total_assets_raw": str(total_assets),
        "total_supply_raw": str(total_supply),
        "liquidity_balance_raw": str(liq_balance),
        "base_balance_raw": str(base_balance),
        "pending_redeem_assets_raw": str(pending),
        "attacker_deposit_raw": str(attacker_deposit),
        "materiality": quantify(pending, cross_price, attacker_deposit, total_assets),
        "trigger": {
            "needs_requantification": (not paused) and pending > 0,
            "reason": "unpaused and pendingRedeemAssets > 0" if (not paused and pending > 0) else "paused or no pendingRedeemAssets",
        },
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
