"""Live KLend probe attempts on a local validator — measured deltas only."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from klend_account_discovery import load_klend_accounts
from klend_probes import KLEND_PROGRAM, KVAULT_PROGRAM, ORACLE_PROGRAM, get_probe, probe_accounts_summary
from klend_tx import (
    b58decode,
    b58encode,
    build_signed_probe_transaction,
    load_keypair,
)

LOCAL_RPC = os.environ.get("SOLANA_VALIDATOR_RPC", "http://127.0.0.1:8899")
_LAMPORT_THRESHOLD = int(os.environ.get("OPERATOR_LAMPORT_THRESHOLD", "100_000_000"))


def _rpc(method: str, params: list | None = None, *, url: str = LOCAL_RPC) -> Any:
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode())
    if "error" in body:
        raise RuntimeError(f"RPC {method} failed: {body['error']}")
    return body["result"]


def _account_exists(pubkey: str) -> bool:
    result = _rpc("getAccountInfo", [pubkey, {"encoding": "base64"}])
    return result.get("value") is not None


def _program_deployed(pubkey: str) -> bool:
    result = _rpc("getAccountInfo", [pubkey, {"encoding": "base64"}])
    value = result.get("value")
    if not value:
        return False
    return bool(value.get("executable"))


def _solana_bin() -> str | None:
    return shutil.which("solana") or shutil.which("solana-keygen") and shutil.which("solana")


def _wallet_balance_lamports(pubkey: str) -> int:
    result = _rpc("getBalance", [pubkey])
    return int(result.get("value", 0))


def _ensure_funded_keypair(rpc_url: str) -> tuple[Path, str]:
    solana = _solana_bin()
    if not solana:
        raise RuntimeError("solana CLI not found")

    tmpdir = Path(tempfile.mkdtemp(prefix="nss-klend-probe-"))
    keypair = tmpdir / "probe-key.json"
    subprocess.run(
        ["solana-keygen", "new", "--no-bip39-passphrase", "--force", "--silent", "-o", str(keypair)],
        check=True,
        capture_output=True,
        text=True,
    )
    pubkey = subprocess.run(
        ["solana-keygen", "pubkey", str(keypair)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    subprocess.run(
        ["solana", "-u", rpc_url, "airdrop", "2", pubkey],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    deadline = time.time() + 20
    while time.time() < deadline:
        if _wallet_balance_lamports(pubkey) >= 500_000_000:
            break
        time.sleep(0.5)
    return keypair, pubkey


def _send_klend_invoke(
    *,
    rpc_url: str,
    keypair_path: Path,
    pubkey: str,
    probe_id: str,
) -> dict[str, Any]:
    signing_key, _payer_pubkey = load_keypair(keypair_path)
    blockhash_resp = _rpc("getLatestBlockhash", [{"commitment": "confirmed"}], url=rpc_url)
    blockhash = b58decode(blockhash_resp["value"]["blockhash"])

    signed = build_signed_probe_transaction(
        keypair=signing_key,
        probe_id=probe_id,
        recent_blockhash=blockhash,
    )
    encoded = b58encode(signed)
    print(f"PROBE_ACCOUNTS:{probe_accounts_summary(probe_id)}")

    balance_before = _wallet_balance_lamports(pubkey)
    send_resp = _rpc(
        "sendTransaction",
        [encoded, {"encoding": "base58", "skipPreflight": True, "maxRetries": 2}],
        url=rpc_url,
    )
    signature = str(send_resp)

    confirmed = False
    failed_on_chain = False
    deadline = time.time() + 30
    while time.time() < deadline:
        status = _rpc("getSignatureStatuses", [[signature], {"searchTransactionHistory": True}], url=rpc_url)
        values = status.get("value") or []
        if values and values[0]:
            conf = values[0].get("confirmationStatus")
            if values[0].get("err"):
                failed_on_chain = True
                confirmed = conf in ("confirmed", "finalized")
                break
            if conf in ("confirmed", "finalized"):
                confirmed = True
                break
        time.sleep(0.5)

    balance_after = _wallet_balance_lamports(pubkey)
    delta = balance_before - balance_after
    return {
        "signature": signature,
        "confirmed": confirmed,
        "failed_on_chain": failed_on_chain,
        "delta_lamports": max(delta, 0),
        "balance_before": balance_before,
        "balance_after": balance_after,
    }


def attempt_live_probe(probe_id: str) -> dict[str, Any]:
    """
    Attempt a CPI invoke against cloned KLend on the local validator.

    probe_executed=True when a transaction lands (confirmed or failed on-chain).
    delta_lamports is measured from the probe wallet — never hardcoded.
    """
    probe = get_probe(probe_id)
    if not probe:
        return {
            "probe_id": probe_id,
            "probe_executed": False,
            "error": "unknown_probe",
            "delta_lamports": 0,
        }

    rpc_url = LOCAL_RPC
    try:
        for program in (KLEND_PROGRAM, KVAULT_PROGRAM, ORACLE_PROGRAM):
            if not _program_deployed(program):
                return {
                    "probe_id": probe_id,
                    "probe_executed": False,
                    "error": f"program_not_deployed:{program}",
                    "delta_lamports": 0,
                }

        accounts = load_klend_accounts()
        for label, pubkey in (
            ("lending_market", accounts["market_pubkey"]),
            ("usdc_reserve", accounts["reserves"]["USDC"]["pubkey"]),
            ("usdc_supply_vault", accounts["reserves"]["USDC"]["supply_vault"]),
        ):
            if not _account_exists(pubkey):
                return {
                    "probe_id": probe_id,
                    "probe_executed": False,
                    "error": f"data_account_missing:{label}:{pubkey}",
                    "delta_lamports": 0,
                }

        keypair_path, pubkey = _ensure_funded_keypair(rpc_url)
        tx_result = _send_klend_invoke(
            rpc_url=rpc_url,
            keypair_path=keypair_path,
            pubkey=pubkey,
            probe_id=probe_id,
        )
        shutil.rmtree(keypair_path.parent, ignore_errors=True)

        executed = bool(tx_result.get("confirmed")) or bool(tx_result.get("failed_on_chain"))
        delta = int(tx_result.get("delta_lamports", 0))
        return {
            "probe_id": probe_id,
            "probe_executed": executed,
            "delta_lamports": delta,
            "tx_signature": tx_result.get("signature", ""),
            "invariant_id": probe.invariant_id,
            "programs_verified": [KLEND_PROGRAM, KVAULT_PROGRAM, ORACLE_PROGRAM],
            "meets_threshold": delta >= _LAMPORT_THRESHOLD,
            "error": "" if executed else "tx_not_confirmed",
        }
    except (urllib.error.URLError, TimeoutError, OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        return {
            "probe_id": probe_id,
            "probe_executed": False,
            "error": str(exc),
            "delta_lamports": 0,
            "invariant_id": probe.invariant_id if probe else "",
        }