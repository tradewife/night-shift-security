#!/usr/bin/env python3
"""
Makina fork-probe verification helper.

Runs the Foundry fork-test suites in `foundry/src/makina/tests/` against an
Ethereum mainnet RPC at the captured fork block (25,463,221) and reports
pass/fail per suite. Lightweight, read-only with respect to RPC; foundry
only creates a local fork via the --fork-url flag.

Usage:
  python3 hermes/scripts/makina_fork_probe_verify.py \
    --rpc $ETHEREUM_RPC_URL \
    [--block 25463221] \
    [--suite ForkProbe_H1_H21|ForkProbeH23_StaleAUM]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone


DEFAULT_BLOCK = 25463221
DEFAULT_FORGE_DIR = "foundry"
DEFAULT_PROFILE = "default"
DEFAULT_SUITES = ("ForkProbe_H1_H21", "ForkProbeH23_StaleAUM")


def _check_forge() -> bool:
    return shutil.which("forge") is not None


def _run_one_suite(
    forge_dir: str,
    rpc: str,
    block: int,
    profile: str,
    suite: str,
) -> dict:
    cmd = [
        "forge",
        "test",
        "--root", forge_dir,
        "--profile", profile,
        "--fork-url", rpc,
        "--fork-block-number", str(block),
        "--match-contract", suite,
        "-vv",
    ]
    started = datetime.now(timezone.utc).isoformat()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    finished = datetime.now(timezone.utc).isoformat()
    return {
        "suite": suite,
        "forge_dir": forge_dir,
        "profile": profile,
        "block": block,
        "started_utc": started,
        "finished_utc": finished,
        "exit_code": proc.returncode,
        "stdout_tail": "\n".join(proc.stdout.splitlines()[-25:]),
        "stderr_tail": "\n".join(proc.stderr.splitlines()[-25:]) if proc.stderr else "",
        "ok": proc.returncode == 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Makina fork-probe verification helper")
    parser.add_argument("--rpc", required=True,
                        help="Ethereum RPC URL (must support fork mode; e.g. Alchemy)")
    parser.add_argument("--block", type=int, default=DEFAULT_BLOCK,
                        help=f"Fork block number (default {DEFAULT_BLOCK})")
    parser.add_argument("--forge-dir", default=DEFAULT_FORGE_DIR,
                        help=f"Foundry project root (default {DEFAULT_FORGE_DIR})")
    parser.add_argument("--profile", default=DEFAULT_PROFILE,
                        help=f"Foundry profile (default {DEFAULT_PROFILE})")
    parser.add_argument("--suite", action="append", default=[],
                        help=f"Suite name to run (default: {', '.join(DEFAULT_SUITES)})")
    args = parser.parse_args()

    if not _check_forge():
        print("ERROR: forge CLI not on PATH", file=sys.stderr)
        return 1

    suites = args.suite or list(DEFAULT_SUITES)
    results = []
    for suite in suites:
        result = _run_one_suite(args.forge_dir, args.rpc, args.block, args.profile, suite)
        results.append(result)
        flag = "PASS" if result["ok"] else "FAIL"
        print(f"[{flag}] {suite} (forge exit={result['exit_code']})")

    summary = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "forge_dir": args.forge_dir,
        "profile": args.profile,
        "block": args.block,
        "rpc": "<redacted>",
        "results": results,
    }
    print(json.dumps(summary, indent=2, default=str))

    return 0 if all(r["ok"] for r in results) else 2


if __name__ == "__main__":
    sys.exit(main())
