#!/usr/bin/env python3
"""Aave v3 measured-delta capture — mirrors _capture_morpho_measurement.py.

Runs the Foundry test, parses its log output, and writes an evidence
envelope via the measured oracle.

Requires:
    ETHEREUM_RPC_URL in .env (or environment)
    foundry/ directory with test/AaveV3Measure.t.sol compiled
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO / "scripts"
IMPACT_DIR = REPO / "data" / "security_results" / "impact"
EVIDENCE_FILE = IMPACT_DIR / "aave_v3_measured_delta.json"


def _load_env() -> dict[str, str]:
    """Load .env into a dict (stdlib only)."""
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


def _run_forge_test(rpc_url: str) -> str:
    """Run forge test and return combined stdout+stderr."""
    foundry_dir = REPO / "foundry"
    env = os.environ.copy()
    env["ETH_RPC_URL"] = rpc_url
    result = subprocess.run(
        [
            "forge", "test",
            "--match-contract", "AaveV3Measure",
            "-vv",
        ],
        cwd=str(foundry_dir),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return result.stdout + "\n" + result.stderr


def _parse_forge_log(output: str) -> dict[str, int]:
    """Extract PRE_*/POST_* markers from forge output."""
    values: dict[str, int] = {}
    for line in output.splitlines():
        line = line.strip()
        for prefix in (
            "BLOCK:", "PRE_LIQUIDITY_INDEX:", "POST_LIQUIDITY_INDEX:",
            "PRE_LIQUIDITY_RATE:", "POST_LIQUIDITY_RATE:",
            "PRE_BORROW_INDEX:", "POST_BORROW_INDEX:",
            "PRE_ACCRUED_TO_TREASURY:", "POST_ACCRUED_TO_TREASURY:",
            "PRE_UNBACKED:", "POST_UNBACKED:",
            "PRE_ISOLATION_MODE_TOTAL_DEBT:", "POST_ISOLATION_MODE_TOTAL_DEBT:",
            "PRE_LAST_UPDATE:", "POST_LAST_UPDATE:",
        ):
            if line.startswith(prefix):
                val_str = line[len(prefix):].strip()
                try:
                    values[prefix.rstrip(":")] = int(val_str)
                except ValueError:
                    pass
    return values


def _write_evidence(values: dict[str, int]) -> Path:
    """Write the evidence envelope JSON."""
    IMPACT_DIR.mkdir(parents=True, exist_ok=True)
    envelope = {
        "schema_version": "measured-oracle.v1",
        "target": "aave_v3",
        "platform": "cantina",
        "chain": "ethereum",
        "harness": "foundry/test/AaveV3Measure.t.sol",
        "method": "read-across-blocks",
        "block": values.get("BLOCK", 0),
        "pre": {
            "liquidity_index": values.get("PRE_LIQUIDITY_INDEX", 0),
            "current_liquidity_rate": values.get("PRE_LIQUIDITY_RATE", 0),
            "variable_borrow_index": values.get("PRE_BORROW_INDEX", 0),
            "accrued_to_treasury": values.get("PRE_ACCRUED_TO_TREASURY", 0),
            "unbacked": values.get("PRE_UNBACKED", 0),
            "isolation_mode_total_debt": values.get("PRE_ISOLATION_MODE_TOTAL_DEBT", 0),
            "last_update_timestamp": values.get("PRE_LAST_UPDATE", 0),
        },
        "post": {
            "liquidity_index": values.get("POST_LIQUIDITY_INDEX", 0),
            "current_liquidity_rate": values.get("POST_LIQUIDITY_RATE", 0),
            "variable_borrow_index": values.get("POST_BORROW_INDEX", 0),
            "accrued_to_treasury": values.get("POST_ACCRUED_TO_TREASURY", 0),
            "unbacked": values.get("POST_UNBACKED", 0),
            "isolation_mode_total_debt": values.get("POST_ISOLATION_MODE_TOTAL_DEBT", 0),
            "last_update_timestamp": values.get("POST_LAST_UPDATE", 0),
        },
        "delta": {
            k: values.get(f"POST_{k.removeprefix('PRE_').replace('CURRENT_', '').lower()}", 0)
            - values.get(k, 0)
            for k in [
                "PRE_LIQUIDITY_INDEX", "PRE_LIQUIDITY_RATE",
                "PRE_BORROW_INDEX", "PRE_ACCRUED_TO_TREASURY",
                "PRE_UNBACKED", "PRE_ISOLATION_MODE_TOTAL_DEBT",
                "PRE_LAST_UPDATE",
            ]
        },
        "oracle_note": "honest-path: same-block read; pre==post by design. Cross-block delta requires two forge invocations at different blocks.",
    }
    EVIDENCE_FILE.write_text(json.dumps(envelope, indent=2) + "\n")
    return EVIDENCE_FILE


def main() -> int:
    env = _load_env()
    rpc_url = env.get("ETHEREUM_RPC_URL") or os.environ.get("ETHEREUM_RPC_URL", "")
    if not rpc_url:
        print("ERROR: ETHEREUM_RPC_URL not set", file=sys.stderr)
        return 1

    print("Running forge test AaveV3Measure ...")
    output = _run_forge_test(rpc_url)
    print(output)

    if "Suite result: ok" not in output:
        print("ERROR: forge test failed", file=sys.stderr)
        return 1

    values = _parse_forge_log(output)
    if not values:
        print("ERROR: no PRE_*/POST_* markers found in forge output", file=sys.stderr)
        return 1

    path = _write_evidence(values)
    print(f"Evidence written: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
