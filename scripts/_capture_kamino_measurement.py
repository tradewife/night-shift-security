#!/usr/bin/env python3
"""Kamino KLend measured-delta capture — Solana cross-slot oracle."""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from night_shift_security.impact.solana_measured_oracle import capture_cross_slot  # noqa: E402


def _load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    env_file = REPO / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def main() -> int:
    env = _load_env()
    rpc = (
        env.get("SOLANA_MAINNET_RPC_URL")
        or os.environ.get("SOLANA_MAINNET_RPC_URL")
        or env.get("SOLANA_RPC_URL")
        or os.environ.get("SOLANA_RPC_URL")
        or ""
    )
    if not rpc:
        print("ERROR: SOLANA_MAINNET_RPC_URL not set", file=sys.stderr)
        return 1

    print("Capturing Kamino cross-slot measured delta ...")
    envelope = capture_cross_slot(rpc, slug="kamino", min_slot_gap=1, poll_seconds=1.0, max_polls=15)
    measured = envelope.get("measured_impact")
    print(f"measured_impact={measured} reason={envelope.get('measured_impact_reason')}")
    path = REPO / "data" / "security_results" / "impact" / "kamino_measured_delta.json"
    print(f"Evidence: {path}")
    return 0 if measured else 2


if __name__ == "__main__":
    sys.exit(main())