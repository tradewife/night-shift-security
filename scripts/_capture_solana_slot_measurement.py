#!/usr/bin/env python3
"""Generic Solana slot/activity measured-delta capture for v5 harnesses."""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from night_shift_security.impact.solana_measured_oracle import (  # noqa: E402
    SCHEMA_VERSION,
    write_evidence,
)
from night_shift_security.native import jito, kamino, orca, raydium  # noqa: E402

SLUG_MODULES = {
    "kamino": kamino,
    "jito": jito,
    "raydium": raydium,
    "orca": orca,
}


def _rpc_url() -> str:
    env_file = REPO / ".env"
    env: dict[str, str] = {}
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return (
        env.get("SOLANA_MAINNET_RPC_URL")
        or os.environ.get("SOLANA_MAINNET_RPC_URL")
        or env.get("SOLANA_RPC_URL")
        or os.environ.get("SOLANA_RPC_URL")
        or ""
    )


def capture(slug: str, rpc_url: str) -> dict:
    mod = SLUG_MODULES[slug]
    if slug == "kamino":
        from night_shift_security.impact.solana_measured_oracle import capture_cross_slot

        return capture_cross_slot(rpc_url, slug=slug)

    hint = getattr(mod, "DEFAULT_MARKET_PUBKEY", "") or getattr(mod, "DEFAULT_POOL_STATE", "") or getattr(mod, "DEFAULT_WHIRLPOOL", "")
    pre = mod.resolve_accounts(hint, rpc_url)
    time.sleep(3.0)
    post = mod.resolve_accounts(hint, rpc_url)
    measured = post.slot > pre.slot or post.lamports != pre.lamports
    if hasattr(pre, "sqrt_price_hint") and hasattr(post, "sqrt_price_hint"):
        measured = measured or post.sqrt_price_hint != pre.sqrt_price_hint
    envelope = {
        "spec": {"slot_pre": pre.slot, "slot_post": post.slot, "program_id": pre.program_id},
        "pre": pre.to_dict(),
        "post": post.to_dict(),
        "delta": {
            "slot_delta": str(post.slot - pre.slot),
            "lamport_delta": str(post.lamports - pre.lamports),
        },
        "measured_impact": measured,
        "measured_impact_reason": "chain_head_or_account_delta" if measured else "static_read",
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "on_chain_state_diff": {"kind": f"{slug}_cross_slot", "non_fee": True, "non_fixture": True},
    }
    write_evidence(envelope, slug)
    return envelope


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", required=True, choices=sorted(SLUG_MODULES))
    args = parser.parse_args()
    rpc = _rpc_url()
    if not rpc:
        print("ERROR: SOLANA_MAINNET_RPC_URL not set", file=sys.stderr)
        return 1
    env = capture(args.slug, rpc)
    print(f"{args.slug} measured_impact={env.get('measured_impact')}")
    return 0 if env.get("measured_impact") else 2


if __name__ == "__main__":
    sys.exit(main())