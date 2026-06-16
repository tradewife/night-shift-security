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
from klend_v2 import (
    append_probe_result,
    classify_failure,
    instruction_meta_for_probe,
    write_account_diff,
    write_account_roles,
    write_instruction_map,
)

LOCAL_RPC = os.environ.get("SOLANA_VALIDATOR_RPC", "http://127.0.0.1:8899")
_LAMPORT_THRESHOLD = int(os.environ.get("OPERATOR_LAMPORT_THRESHOLD", "100_000_000"))


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


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


def _token_account_amount(pubkey: str, *, url: str = LOCAL_RPC) -> int:
    """SPL token account balance in smallest token units (e.g. micro-USDC)."""
    result = _rpc(
        "getTokenAccountBalance",
        [pubkey],
        url=url,
    )
    value = result.get("value") or {}
    return int(value.get("amount", 0))


def _usdc_micro_to_lamport_equiv(micro_usdc: int, sol_usd: float = 150.0) -> int:
    """Convert USDC micro-unit drain to lamport-equivalent for OPERATOR_LAMPORT_THRESHOLD."""
    if micro_usdc <= 0 or sol_usd <= 0:
        return 0
    return int(micro_usdc * 1_000_000_000 / (sol_usd * 1_000_000))


def _protocol_vault_deltas(
    accounts: dict[str, Any],
    *,
    url: str = LOCAL_RPC,
) -> dict[str, int]:
    """Best-effort vault balances; cloned validator token accounts may lack mint metadata."""
    usdc_vault = accounts["reserves"]["USDC"]["supply_vault"]
    sol_vault = accounts["reserves"]["SOL"]["supply_vault"]
    out = {"usdc_supply_vault_micro": 0, "sol_supply_vault_lamports": 0}
    try:
        out["usdc_supply_vault_micro"] = _token_account_amount(usdc_vault, url=url)
    except RuntimeError:
        pass
    try:
        out["sol_supply_vault_lamports"] = _token_account_amount(sol_vault, url=url)
    except RuntimeError:
        pass
    return out


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
    chain_error: Any = None
    deadline = time.time() + 30
    while time.time() < deadline:
        status = _rpc("getSignatureStatuses", [[signature], {"searchTransactionHistory": True}], url=rpc_url)
        values = status.get("value") or []
        if values and values[0]:
            conf = values[0].get("confirmationStatus")
            if values[0].get("err"):
                failed_on_chain = True
                chain_error = values[0].get("err")
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
        "chain_error": chain_error,
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
        result = {
            "probe_id": probe_id,
            "probe_executed": False,
            "error": "unknown_probe",
            "delta_lamports": 0,
        }
        result["failure_class"] = classify_failure(result)
        append_probe_result(result)
        return result

    rpc_url = LOCAL_RPC
    try:
        write_instruction_map()
        instruction_meta = instruction_meta_for_probe(probe_id)
        for program in (KLEND_PROGRAM, KVAULT_PROGRAM, ORACLE_PROGRAM):
            if not _program_deployed(program):
                result = {
                    "probe_id": probe_id,
                    "probe_executed": False,
                    "error": f"program_not_deployed:{program}",
                    "delta_lamports": 0,
                    "instruction": instruction_meta,
                    "instruction_map_path": "data/security_results/klend/instruction_map.json",
                }
                result["failure_class"] = classify_failure(result)
                append_probe_result(result)
                return result

        accounts = load_klend_accounts()
        account_roles = write_account_roles(accounts)
        for label, pubkey in (
            ("lending_market", accounts["market_pubkey"]),
            ("usdc_reserve", accounts["reserves"]["USDC"]["pubkey"]),
            ("usdc_supply_vault", accounts["reserves"]["USDC"]["supply_vault"]),
        ):
            if not _account_exists(pubkey):
                result = {
                    "probe_id": probe_id,
                    "probe_executed": False,
                    "error": f"data_account_missing:{label}:{pubkey}",
                    "delta_lamports": 0,
                    "instruction": instruction_meta,
                    "account_roles_count": len(account_roles.get("roles") or []),
                    "account_roles_path": "data/security_results/klend/account_roles.json",
                }
                result["failure_class"] = classify_failure(result)
                append_probe_result(result)
                return result

        vault_before = _protocol_vault_deltas(accounts, url=rpc_url)

        keypair_path, pubkey = _ensure_funded_keypair(rpc_url)
        tx_result = _send_klend_invoke(
            rpc_url=rpc_url,
            keypair_path=keypair_path,
            pubkey=pubkey,
            probe_id=probe_id,
        )
        shutil.rmtree(keypair_path.parent, ignore_errors=True)

        vault_after = _protocol_vault_deltas(accounts, url=rpc_url)
        diff_path = write_account_diff(probe_id, vault_before, vault_after)
        usdc_drain_micro = max(
            0,
            vault_before["usdc_supply_vault_micro"] - vault_after["usdc_supply_vault_micro"],
        )
        sol_drain_lamports = max(
            0,
            vault_before["sol_supply_vault_lamports"] - vault_after["sol_supply_vault_lamports"],
        )
        protocol_delta_lamports = max(
            _usdc_micro_to_lamport_equiv(usdc_drain_micro),
            sol_drain_lamports,
        )

        executed = bool(tx_result.get("confirmed")) or bool(tx_result.get("failed_on_chain"))
        wallet_delta = int(tx_result.get("delta_lamports", 0))
        delta = max(wallet_delta, protocol_delta_lamports)
        result = {
            "probe_id": probe_id,
            "probe_executed": executed,
            "failed_on_chain": bool(tx_result.get("failed_on_chain")),
            "chain_error": tx_result.get("chain_error"),
            "delta_lamports": delta,
            "wallet_delta_lamports": wallet_delta,
            "protocol_delta_lamports": protocol_delta_lamports,
            "usdc_vault_drain_micro": usdc_drain_micro,
            "sol_vault_drain_lamports": sol_drain_lamports,
            "tx_signature": tx_result.get("signature", ""),
            "invariant_id": probe.invariant_id,
            "instruction": instruction_meta,
            "account_roles_count": len(account_roles.get("roles") or []),
            "account_roles_path": "data/security_results/klend/account_roles.json",
            "account_diff_path": _display_path(diff_path),
            "programs_verified": [KLEND_PROGRAM, KVAULT_PROGRAM, ORACLE_PROGRAM],
            "meets_threshold": delta >= _LAMPORT_THRESHOLD,
            "error": (
                f"on_chain_error:{json.dumps(tx_result.get('chain_error'), sort_keys=True)}"
                if tx_result.get("failed_on_chain")
                else ("" if executed else "tx_not_confirmed")
            ),
        }
        result["failure_class"] = classify_failure(result)
        append_probe_result(result)
        return result
    except (urllib.error.URLError, TimeoutError, OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        result = {
            "probe_id": probe_id,
            "probe_executed": False,
            "error": str(exc),
            "delta_lamports": 0,
            "invariant_id": probe.invariant_id if probe else "",
        }
        result["failure_class"] = classify_failure(result)
        append_probe_result(result)
        return result
