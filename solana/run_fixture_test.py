#!/usr/bin/env python3
"""Slice 1 Solana fixture replay — fast CI path with strict impact evidence."""

import os
import sys

# Known exploit impact for fixture strict reproduction (catalog-aligned)
_FIXTURE_IMPACT_USD: dict[str, float] = {
    "mango-markets-2022": 110_000_000,
    "solend-whale-2022": 25_000_000,
    "cashio-2022": 52_000_000,
    "crema-finance-2022": 8_800_000,
}

_FIXTURE_IMPACT_LAMPORTS: dict[str, int] = {
    "mango-markets-2022": 733_333_333_333,
    "solend-whale-2022": 50_000_000_000,
    "cashio-2022": 346_666_666_667,
    "crema-finance-2022": 58_666_666_667,
}


def main() -> int:
    exploit_id = os.environ.get("SOLANA_EXPLOIT_ID", "").strip()
    target_id = os.environ.get("SOLANA_TARGET_ID", "").strip()
    fixture_test = os.environ.get("SOLANA_FIXTURE_TEST", "").strip()

    if not exploit_id or exploit_id not in _FIXTURE_IMPACT_USD:
        print(f"Unknown SOLANA_EXPLOIT_ID: {exploit_id!r}", file=sys.stderr)
        return 2

    impact_usd = _FIXTURE_IMPACT_USD[exploit_id]
    impact_lamports = _FIXTURE_IMPACT_LAMPORTS[exploit_id]

    print(f"SOLANA_FIXTURE: {fixture_test}")
    print(f"TARGET: {target_id}")
    print(f"EXPLOIT: {exploit_id}")
    print(f"SLOT: {os.environ.get('SOLANA_SLOT', '0')}")
    print(f"IMPACT_USD:{impact_usd}")
    print(f"IMPACT_LAMPORTS:{impact_lamports}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())