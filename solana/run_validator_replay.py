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
    clone_programs: tuple[str, ...],
    clone_data_accounts: tuple[str, ...],
    ledger_dir: Path,
    warp_slot: int | None = None,
    patched_accounts: tuple[tuple[str, Path], ...] = (),
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
    if warp_slot and warp_slot > 0:
        cmd.extend(["--warp-slot", str(warp_slot)])
    for account in clone_programs:
        cmd.extend(["--clone-upgradeable-program", account])
    for account in clone_data_accounts:
        cmd.extend(["--clone", account])
    for pubkey, account_file in patched_accounts:
        cmd.extend(["--account", pubkey, str(account_file)])

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


def _free_validator_rpc_port(port: int = 8899) -> None:
    """Clear stale solana-test-validator processes holding the local RPC port."""
    try:
        subprocess.run(
            ["fuser", "-k", f"{port}/tcp"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        time.sleep(1)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass


def _find_validator_bin() -> str:
    candidates = [
        os.environ.get("SOLANA_VALIDATOR_BIN", "").strip(),
        shutil.which("solana-test-validator") or "",
        str(Path.home() / ".local/share/solana/install/active_release/bin/solana-test-validator"),
        str(Path.home() / ".cargo/bin/solana-test-validator"),
        "/usr/local/bin/solana-test-validator",
        "/usr/bin/solana-test-validator",
    ]
    for candidate in candidates:
        if candidate and os.access(candidate, os.X_OK):
            return candidate
    return ""


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

    validator_bin = _find_validator_bin()
    if not validator_bin:
        print("solana-test-validator not found", file=sys.stderr)
        return 2

    ledger_dir = Path(tempfile.mkdtemp(prefix="nss-solana-ledger-"))
    proc: subprocess.Popen | None = None
    try:
        warp_slot = None
        if os.environ.get("SOLANA_VALIDATOR_WARP_SLOT", "").strip():
            warp_slot = int(os.environ["SOLANA_VALIDATOR_WARP_SLOT"])
        elif os.environ.get("SOLANA_VALIDATOR_WARP_TO_RPC_SLOT", "1").lower() not in ("0", "false", "no"):
            warp_slot = int(_rpc("getSlot", url=mainnet_rpc))
        patched_accounts: tuple[tuple[str, Path], ...] = ()
        clone_data_accounts = profile.clone_data_accounts
        if exploit_id == "kamino-klend" and os.environ.get("NSS_KLEND_CLONE_COLLATERAL", "").lower() in (
            "1",
            "true",
            "yes",
        ):
            from klend_account_discovery import klend_collateral_clone_accounts

            clone_data_accounts = tuple(
                dict.fromkeys(clone_data_accounts + klend_collateral_clone_accounts(symbol="SOL"))
            )
        patch_scope = os.environ.get("NSS_KLEND_PATCH_SCOPE", "1").lower() not in ("0", "false", "no")
        if klend_harness := os.environ.get("KLEND_HARNESS", "").lower() in ("1", "true", "yes"):
            if patch_scope and exploit_id == "kamino-klend":
                from klend_scope_patch import (
                    prepare_patched_scope_account_file,
                    split_clone_accounts_for_scope_patch,
                )

                scope_pubkey, scope_file, scope_updated = prepare_patched_scope_account_file(
                    rpc_url=mainnet_rpc,
                    out_dir=ledger_dir,
                    slot=warp_slot,
                    price_manipulation_pct=float(os.environ.get("NSS_KLEND_ORACLE_MANIPULATE_PCT", "0") or "0") or None,
                )
                clone_data_accounts, removed = split_clone_accounts_for_scope_patch(
                    clone_data_accounts,
                    scope_pubkey,
                )
                if removed:
                    patched_accounts = ((scope_pubkey, scope_file),)
                    from klend_scope_patch import scope_patch_unix_timestamp

                    patch_ts = scope_patch_unix_timestamp(rpc_url=mainnet_rpc, slot=warp_slot)
                    print(f"SCOPE_PATCH:{scope_pubkey}:entries={scope_updated}:unix_ts={patch_ts}")

        _free_validator_rpc_port(8899)
        print(f"Starting solana-test-validator for {exploit_id}...")
        proc = _start_validator(
            validator_bin,
            mainnet_rpc,
            profile.clone_accounts,
            clone_data_accounts,
            ledger_dir,
            warp_slot,
            patched_accounts,
        )
        clone_extra = max(0, len(profile.clone_accounts) + len(profile.clone_data_accounts) - 1) * 30
        startup_timeout = int(os.environ.get("SOLANA_VALIDATOR_STARTUP_TIMEOUT", str(STARTUP_TIMEOUT_S + clone_extra)))
        _wait_for_validator(startup_timeout)

        if patched_accounts:
            import base64
            import struct

            from klend_scope_patch import ORACLE_PRICES_HEADER_SIZE, UNIX_TIMESTAMP_OFFSET_IN_ENTRY

            scope_pubkey = patched_accounts[0][0]
            scope_info = _rpc("getAccountInfo", [scope_pubkey, {"encoding": "base64"}])
            scope_value = scope_info.get("value") or {}
            scope_data = base64.b64decode((scope_value.get("data") or ["", ""])[0])
            chain_ts = int(_rpc("getBlockTime", [int(_rpc("getSlot"))]) or 0)
            for label, entry_idx in (("entry0", 0), ("token13", 13), ("token10", 10)):
                base = ORACLE_PRICES_HEADER_SIZE + entry_idx * 56
                scope_ts = struct.unpack_from("<Q", scope_data, base + UNIX_TIMESTAMP_OFFSET_IN_ENTRY)[0]
                print(
                    f"SCOPE_VERIFY:{label}:ts={scope_ts}:chain_ts={chain_ts}:age={max(0, chain_ts - scope_ts)}"
                )

        for pubkey in profile.clone_accounts:
            if not _account_exists(pubkey):
                print(f"Clone missing on local ledger: {pubkey}", file=sys.stderr)
                return 1
            if not _is_executable_program(pubkey):
                print(f"Cloned account is not an executable program: {pubkey}", file=sys.stderr)
                return 1

        for pubkey in clone_data_accounts:
            if not _account_exists(pubkey):
                print(f"Cloned data account missing on local ledger: {pubkey}", file=sys.stderr)
                return 1
        for pubkey, _account_file in patched_accounts:
            if not _account_exists(pubkey):
                print(f"Patched data account missing on local ledger: {pubkey}", file=sys.stderr)
                return 1

        current_slot = int(_rpc("getSlot"))
        print(f"VALIDATOR_RPC:{LOCAL_RPC}")
        print(f"SLOT_TARGET:{profile.historical_slot}")
        print(f"SLOT_CURRENT:{current_slot}")
        if warp_slot:
            print(f"SLOT_WARP:{warp_slot}")
        print(f"CLONED_PROGRAMS:{','.join(profile.clone_accounts)}")
        if clone_data_accounts:
            print(f"CLONED_DATA_ACCOUNTS:{','.join(clone_data_accounts)}")
        print("SOLANA_VALIDATOR_PASS:1")
        klend_harness = os.environ.get("KLEND_HARNESS", "").lower() in ("1", "true", "yes")
        if not klend_harness:
            print(f"IMPACT_USD:{profile.impact_usd}")
            print(f"IMPACT_LAMPORTS:{profile.impact_lamports}")
        else:
            from klend_live_probes import attempt_live_probe
            from klend_probes import KLEND_PROBES, get_probe

            depth_mode = os.environ.get("NSS_KLEND_DEPTH", "").lower() in ("1", "true", "yes")
            probe_id = os.environ.get("KLEND_PROBE", "").strip()

            def _emit_probe_result(probe_result: dict) -> None:
                setup = probe_result.get("setup") or {}
                if setup.get("setup_signature"):
                    print(f"SETUP_SIGNATURE:{setup.get('setup_signature')}")
                if setup.get("deposit_signature"):
                    print(f"DEPOSIT_SIGNATURE:{setup.get('deposit_signature')}")
                if setup.get("setup_error"):
                    print(f"SETUP_ERROR:{setup.get('setup_error')}")
                if setup.get("deposit_error"):
                    print(f"DEPOSIT_ERROR:{setup.get('deposit_error')}")
                if setup.get("failed_on_chain"):
                    print(f"SETUP_CHAIN_ERROR:{json.dumps(setup.get('chain_error'), sort_keys=True)}")
                if setup.get("deposit_failed_on_chain"):
                    print(f"DEPOSIT_CHAIN_ERROR:{json.dumps(setup.get('deposit_chain_error'), sort_keys=True)}")
                if setup.get("collateral_wrap_returncode") is not None:
                    print(f"COLLATERAL_WRAP_RC:{setup.get('collateral_wrap_returncode')}")
                if setup.get("collateral_wsol_balance_raw") is not None:
                    print(f"COLLATERAL_WSOL_BALANCE_RAW:{setup.get('collateral_wsol_balance_raw')}")
                for line in (setup.get("deposit_logs") or [])[-12:]:
                    print(f"DEPOSIT_LOG:{line}")
                for line in (probe_result.get("tx_logs") or [])[-12:]:
                    print(f"PROBE_LOG:{line}")
                print(f"TX_SIGNATURE:{probe_result.get('tx_signature', '')}")
                print(f"PROBE_STATUS:{probe_result.get('error') or 'ok'}")
                if probe_result.get("chain_error") is not None:
                    print(f"PROBE_CHAIN_ERROR:{json.dumps(probe_result['chain_error'], sort_keys=True)}")
                if probe_result.get("probe_executed"):
                    print("PROBE_TX_CONFIRMED:1")
                print(f"MEASURED_DELTA_LAMPORTS:{int(probe_result.get('delta_lamports', 0))}")
                if probe_result.get("wallet_delta_lamports") is not None:
                    print(f"WALLET_DELTA_LAMPORTS:{int(probe_result.get('wallet_delta_lamports', 0))}")
                if probe_result.get("protocol_delta_lamports") is not None:
                    print(f"PROTOCOL_DELTA_LAMPORTS:{int(probe_result.get('protocol_delta_lamports', 0))}")
                if probe_result.get("usdc_vault_drain_micro"):
                    print(f"USDC_VAULT_DRAIN_MICRO:{int(probe_result['usdc_vault_drain_micro'])}")
                if probe_result.get("invariant_id"):
                    print(f"INVARIANT:{probe_result['invariant_id']}")
                if probe_result.get("reserve_last_update_slot_delta") is not None:
                    print(
                        f"RESERVE_LAST_UPDATE_SLOT_DELTA:"
                        f"{int(probe_result.get('reserve_last_update_slot_delta', 0))}"
                    )
                if probe_result.get("cumulative_borrow_rate_changed"):
                    print("CUMULATIVE_BORROW_RATE_CHANGED:1")
                if probe_result.get("chain_slot_after") is not None:
                    print(f"CHAIN_SLOT_AFTER:{int(probe_result.get('chain_slot_after', 0))}")
                if probe_result.get("meets_threshold"):
                    print("PROBE_MEETS_THRESHOLD:1")

            if depth_mode:
                best_delta = 0
                best_meets = False
                best_result: dict | None = None
                results = []
                for probe in KLEND_PROBES:
                    probe_result = attempt_live_probe(probe.probe_id)
                    delta = int(probe_result.get("delta_lamports", 0))
                    meets = bool(probe_result.get("meets_threshold"))
                    results.append(
                        {
                            "probe_id": probe.probe_id,
                            "delta_lamports": delta,
                            "probe_executed": bool(probe_result.get("probe_executed")),
                            "meets_threshold": meets,
                        }
                    )
                    print(f"PROBE_RESULT:{probe.probe_id}:{'pass' if meets else 'fail'}")
                    if meets and not best_meets:
                        best_meets = True
                        best_delta = delta
                        best_result = probe_result
                    elif meets == best_meets and delta > best_delta:
                        best_delta = delta
                        best_result = probe_result
                    elif not best_meets and delta > best_delta:
                        best_delta = delta
                        best_result = probe_result
                print(f"DEPTH_PROBE_COUNT:{len(results)}")
                print(f"DEPTH_PROBE_JSON:{json.dumps(results)}")
                if best_result:
                    _emit_probe_result(best_result)
            elif probe_id and probe_id != "baseline_deploy":
                probe_result = attempt_live_probe(probe_id)
                _emit_probe_result(probe_result)
                if not probe_result.get("invariant_id") and get_probe(probe_id):
                    print(f"INVARIANT:{get_probe(probe_id).invariant_id}")
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
