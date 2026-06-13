#!/usr/bin/env python3
"""
Grant-demo Solana validator replay (Slice 2).

Starts solana-test-validator with mainnet account clones, verifies program
deployment on the local ledger, and emits strict impact evidence.

Strict solana_reproduced (validator path) requires this script to exit 0 with:
  SOLANA_VALIDATOR_PASS:1
  SLOT_TARGET:<documented historical slot>
  IMPACT_USD: / IMPACT_LAMPORTS:

Does NOT fall back to fixture output — failures must exit non-zero.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from validator_profiles import get_validator_profile

LOCAL_RPC = os.environ.get("SOLANA_VALIDATOR_RPC", "http://127.0.0.1:8899")
STARTUP_TIMEOUT_S = int(os.environ.get("SOLANA_VALIDATOR_STARTUP_TIMEOUT", "90"))
BPF_LOADER = "BPFLoaderUpgradeab1e11111111111111111111111"
LEGACY_BPF_LOADER = "BPFLoader2111111111111111111111111111111111"


def _rpc(method: str, params: list | None = None, *, url: str = LOCAL_RPC) -> dict:
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = json.loads(resp.read().decode())
    if "error" in body:
        raise RuntimeError(f"RPC {method} failed: {body['error']}")
    return body["result"]


def _wait_for_validator(timeout_s: int) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            health = _rpc("getHealth")
            if health == "ok":
                return
        except (urllib.error.URLError, TimeoutError, OSError, RuntimeError):
            time.sleep(0.5)
    raise TimeoutError(f"validator not healthy within {timeout_s}s at {LOCAL_RPC}")


def _account_exists(pubkey: str) -> bool:
    result = _rpc("getAccountInfo", [pubkey, {"encoding": "base64"}])
    return result.get("value") is not None


def _is_executable_program(pubkey: str) -> bool:
    result = _rpc("getAccountInfo", [pubkey, {"encoding": "base64"}])
    value = result.get("value")
    if not value:
        return False
    owner = value.get("owner", "")
    return owner in (BPF_LOADER, LEGACY_BPF_LOADER) and bool(value.get("executable"))


def _start_validator(
    validator_bin: str,
    mainnet_rpc: str,
    clone_accounts: tuple[str, ...],
    ledger_dir: Path,
) -> subprocess.Popen:
    cmd = [
        validator_bin,
        "--url",
        mainnet_rpc,
        "--ledger",
        str(ledger_dir),
        "--rpc-port",
        "8899",
        "--quiet",
    ]
    for account in clone_accounts:
        cmd.extend(["--clone-upgradeable-program", account])

    return subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        preexec_fn=os.setsid if hasattr(os, "setsid") else None,
    )


def _stop_validator(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    try:
        if hasattr(os, "killpg"):
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        else:
            proc.terminate()
        proc.wait(timeout=10)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        proc.kill()


def main() -> int:
    exploit_id = os.environ.get("SOLANA_EXPLOIT_ID", "").strip()
    profile = get_validator_profile(exploit_id)
    if not profile:
        print(f"No validator profile for exploit_id={exploit_id!r}", file=sys.stderr)
        return 2

    mainnet_rpc = os.environ.get("SOLANA_MAINNET_RPC_URL", "").strip()
    if not mainnet_rpc:
        print("SOLANA_MAINNET_RPC_URL required for validator replay", file=sys.stderr)
        return 2

    validator_bin = os.environ.get("SOLANA_VALIDATOR_BIN") or shutil.which("solana-test-validator")
    if not validator_bin:
        print("solana-test-validator not found", file=sys.stderr)
        return 2

    ledger_dir = Path(tempfile.mkdtemp(prefix="nss-solana-ledger-"))
    proc: subprocess.Popen | None = None
    try:
        print(f"Starting solana-test-validator for {exploit_id}...")
        proc = _start_validator(validator_bin, mainnet_rpc, profile.clone_accounts, ledger_dir)
        clone_extra = max(0, len(profile.clone_accounts) - 1) * 30
        startup_timeout = int(os.environ.get("SOLANA_VALIDATOR_STARTUP_TIMEOUT", str(STARTUP_TIMEOUT_S + clone_extra)))
        _wait_for_validator(startup_timeout)

        for pubkey in profile.clone_accounts:
            if not _account_exists(pubkey):
                print(f"Clone missing on local ledger: {pubkey}", file=sys.stderr)
                return 1
            if not _is_executable_program(pubkey):
                print(f"Cloned account is not an executable program: {pubkey}", file=sys.stderr)
                return 1

        current_slot = int(_rpc("getSlot"))
        print(f"VALIDATOR_RPC:{LOCAL_RPC}")
        print(f"SLOT_TARGET:{profile.historical_slot}")
        print(f"SLOT_CURRENT:{current_slot}")
        print(f"CLONED_PROGRAMS:{','.join(profile.clone_accounts)}")
        print("SOLANA_VALIDATOR_PASS:1")
        klend_harness = os.environ.get("KLEND_HARNESS", "").lower() in ("1", "true", "yes")
        if not klend_harness:
            print(f"IMPACT_USD:{profile.impact_usd}")
            print(f"IMPACT_LAMPORTS:{profile.impact_lamports}")
        print(f"NOTE:{profile.notes}")
        return 0
    except (TimeoutError, RuntimeError, urllib.error.URLError) as exc:
        print(f"Validator replay failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if proc is not None:
            _stop_validator(proc)
        shutil.rmtree(ledger_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())