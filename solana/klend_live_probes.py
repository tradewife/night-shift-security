"""Live KLend probe attempts on a local validator — measured deltas only."""

from __future__ import annotations

import base64
import json
import os
import shutil
import struct
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from klend_account_discovery import load_klend_accounts
from klend_probes import KLEND_PROGRAM, KVAULT_PROGRAM, ORACLE_PROGRAM, get_probe
from klend_tx import (
    FARMS_PROGRAM,
    b58decode,
    b58encode,
    build_signed_borrow_setup_transaction,
    build_signed_collateral_deposit_transaction,
    build_signed_probe_transaction,
    derive_associated_token_account,
    load_keypair,
    probe_instruction_account_summary,
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
_RESERVE_DISC_LEN = 8
_RESERVE_LAST_UPDATE_SLOT_OFF = _RESERVE_DISC_LEN + 8  # after version u64
_RESERVE_CUM_BORROW_RATE_OFF = _RESERVE_DISC_LEN + 8 + 16 + 96 + 8 + 16 + 16 + 8 + 8 + 8 + 8


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


def _reserve_account_raw(pubkey: str, *, url: str = LOCAL_RPC, commitment: str = "confirmed") -> bytes | None:
    try:
        result = _rpc(
            "getAccountInfo",
            [pubkey, {"encoding": "base64", "commitment": commitment}],
            url=url,
        )
        value = result.get("value")
        if not value or not value.get("data"):
            return None
        return base64.b64decode(value["data"][0])
    except (RuntimeError, ValueError):
        return None


def _reserve_field_snapshot(pubkey: str, *, url: str = LOCAL_RPC, commitment: str = "confirmed") -> dict[str, Any]:
    raw = _reserve_account_raw(pubkey, url=url, commitment=commitment)
    if not raw or len(raw) < _RESERVE_LAST_UPDATE_SLOT_OFF + 8:
        return {}
    last_slot = int(struct.unpack_from("<Q", raw, _RESERVE_LAST_UPDATE_SLOT_OFF)[0])
    cum_rate = ""
    if len(raw) >= _RESERVE_CUM_BORROW_RATE_OFF + 32:
        limbs = struct.unpack_from("<QQQQ", raw, _RESERVE_CUM_BORROW_RATE_OFF)
        cum_rate = ":".join(str(x) for x in limbs)
    return {
        "last_update_slot": last_slot,
        "cumulative_borrow_rate": cum_rate,
    }


def _reserve_last_update_slot(pubkey: str, *, url: str = LOCAL_RPC, commitment: str = "confirmed") -> int | None:
    snap = _reserve_field_snapshot(pubkey, url=url, commitment=commitment)
    slot = snap.get("last_update_slot")
    return int(slot) if slot is not None else None


def _chain_slot(url: str = LOCAL_RPC, *, commitment: str = "confirmed") -> int:
    return int(_rpc("getSlot", [{"commitment": commitment}], url=url))


def _wait_chain_slot_advance(*, url: str = LOCAL_RPC, min_delta: int = 2, timeout_s: float = 20.0) -> int:
    start = _chain_slot(url)
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        current = _chain_slot(url)
        if current >= start + min_delta:
            return current
        time.sleep(0.35)
    return _chain_slot(url)


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
    setup_result: dict[str, Any] = {}
    auto_setup = os.environ.get("NSS_KLEND_AUTO_SETUP", "1").lower() not in ("0", "false", "no")
    if auto_setup and probe_id == "oracle_staleness_borrow":
        setup_result = _attempt_borrow_probe_setup(
            rpc_url=rpc_url,
            keypair_path=keypair_path,
            signing_key=signing_key,
            blockhash=blockhash,
        )
    elif auto_setup and probe_id == "flash_loan_collateral_loop":
        setup_result = _attempt_flash_probe_setup(
            rpc_url=rpc_url,
            keypair_path=keypair_path,
            signing_key=signing_key,
        )
    elif auto_setup and probe_id in _NEW_PROBE_SETUP_IDS:
        setup_result = _attempt_new_probe_setup(
            rpc_url=rpc_url,
            keypair_path=keypair_path,
            signing_key=signing_key,
        )

    if os.environ.get("NSS_KLEND_SCOPE_VERIFY", "1").lower() not in ("0", "false", "no"):
        try:
            from klend_scope_patch import ORACLE_PRICES_HEADER_SIZE, UNIX_TIMESTAMP_OFFSET_IN_ENTRY

            klend_accounts = load_klend_accounts()
            scope_pk = str(klend_accounts["reserves"]["USDC"].get("scope_prices") or "")
            if scope_pk:
                scope_raw = _reserve_account_raw(scope_pk, url=rpc_url)
                if scope_raw and len(scope_raw) >= ORACLE_PRICES_HEADER_SIZE + 56:
                    slot_now = int(_rpc("getSlot", url=rpc_url))
                    chain_ts = int(_rpc("getBlockTime", [slot_now], url=rpc_url) or 0)
                    clock_info = _rpc(
                        "getAccountInfo",
                        ["SysvarC1ock11111111111111111111111111111111", {"encoding": "base64"}],
                        url=rpc_url,
                    )
                    clock_raw = base64.b64decode((clock_info.get("value") or {}).get("data", ["", ""])[0])
                    clock_unix = int(struct.unpack_from("<q", clock_raw, 32)[0]) if len(clock_raw) >= 40 else 0
                    for entry_idx in (13, 10):
                        base = ORACLE_PRICES_HEADER_SIZE + entry_idx * 56
                        scope_ts = struct.unpack_from("<Q", scope_raw, base + UNIX_TIMESTAMP_OFFSET_IN_ENTRY)[0]
                        print(
                            f"SCOPE_PRE_TX:token{entry_idx}:ts={scope_ts}:block_ts={chain_ts}:"
                            f"clock_unix={clock_unix}:age_block={max(0, chain_ts - scope_ts)}:"
                            f"age_clock={max(0, clock_unix - scope_ts)}",
                            flush=True,
                        )
        except Exception as exc:
            print(f"SCOPE_PRE_TX:error:{exc}", flush=True)

    signed = build_signed_probe_transaction(
        keypair=signing_key,
        probe_id=probe_id,
        recent_blockhash=blockhash,
    )
    encoded = b58encode(signed)
    print(f"PROBE_ACCOUNTS:{probe_instruction_account_summary(probe_id, signing_key.pubkey())}")

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
    tx_logs = _transaction_logs(signature, rpc_url=rpc_url)
    return {
        "signature": signature,
        "confirmed": confirmed,
        "failed_on_chain": failed_on_chain,
        "chain_error": chain_error,
        "tx_logs": tx_logs,
        "delta_lamports": max(delta, 0),
        "balance_before": balance_before,
        "balance_after": balance_after,
        "setup": setup_result,
        "chain_slot": _chain_slot(rpc_url),
    }


def _send_refresh_reserve_burst(
    *,
    rpc_url: str,
    keypair_path: Path,
    pubkey: str,
    attempts: int = 2,
) -> dict[str, Any]:
    """Run consecutive refresh_reserve txs so reserve.last_update.slot catches chain head."""
    _wait_chain_slot_advance(url=rpc_url, min_delta=2)
    last: dict[str, Any] = {}
    for _ in range(max(1, attempts)):
        last = _send_klend_invoke(
            rpc_url=rpc_url,
            keypair_path=keypair_path,
            pubkey=pubkey,
            probe_id="refresh_reserve_live",
        )
        if last.get("failed_on_chain"):
            break
        time.sleep(0.75)
        _wait_chain_slot_advance(url=rpc_url, min_delta=1, timeout_s=8.0)
    return last


def _wait_signature_status(signature: str, *, rpc_url: str, timeout_s: int = 30) -> dict[str, Any]:
    confirmed = False
    failed_on_chain = False
    chain_error: Any = None
    deadline = time.time() + timeout_s
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
    return {"confirmed": confirmed, "failed_on_chain": failed_on_chain, "chain_error": chain_error}


def _transaction_logs(signature: str, *, rpc_url: str) -> list[str]:
    try:
        result = _rpc(
            "getTransaction",
            [
                signature,
                {
                    "encoding": "json",
                    "commitment": "confirmed",
                    "maxSupportedTransactionVersion": 0,
                },
            ],
            url=rpc_url,
        )
    except Exception:
        return []
    meta = (result or {}).get("meta") or {}
    logs = meta.get("logMessages") or []
    return [str(line) for line in logs][-80:]


def _attempt_flash_probe_setup(
    *,
    rpc_url: str,
    keypair_path: Path,
    signing_key: Any,
) -> dict[str, Any]:
    result: dict[str, Any] = {"attempted": True}
    try:
        accounts = load_klend_accounts()
        symbol = os.environ.get("NSS_KLEND_FLASH_RESERVE", "SOL").strip().upper() or "SOL"
        reserve = accounts["reserves"][symbol]
        mint = reserve["mint"]
        destination = derive_associated_token_account(signing_key.pubkey(), mint)
        spl_token = shutil.which("spl-token")
        if not spl_token:
            result["ata_error"] = "spl-token CLI not found"
            return result
        fee_buffer = int(os.environ.get("NSS_KLEND_FLASH_FEE_BUFFER_LAMPORTS", "20000000"))
        if symbol == "SOL" and fee_buffer > 0:
            wrap_proc = subprocess.run(
                [
                    spl_token,
                    "-u",
                    rpc_url,
                    "--fee-payer",
                    str(keypair_path),
                    "wrap",
                    str(fee_buffer / 1_000_000_000),
                    str(keypair_path),
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            result.update(
                {
                    "reserve_symbol": symbol,
                    "ata": str(destination),
                    "fee_buffer_lamports": fee_buffer,
                    "wrap_returncode": wrap_proc.returncode,
                    "wrap_stdout": wrap_proc.stdout.strip()[-500:],
                    "wrap_stderr": wrap_proc.stderr.strip()[-500:],
                }
            )
            return result

        proc = subprocess.run(
            [
                spl_token,
                "-u",
                rpc_url,
                "--fee-payer",
                str(keypair_path),
                "create-account",
                mint,
                "--owner",
                str(signing_key.pubkey()),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        result.update(
            {
                "reserve_symbol": symbol,
                "ata": str(destination),
                "ata_returncode": proc.returncode,
                "ata_stdout": proc.stdout.strip()[-500:],
                "ata_stderr": proc.stderr.strip()[-500:],
            }
        )
    except Exception as exc:
        result["ata_error"] = str(exc)
    return result


_NEW_PROBE_SETUP_IDS = frozenset({
    "deposit_reserve_liquidity_live",
    "redeem_reserve_collateral_live",
    "flash_borrow_reserve_liquidity_live",
})


def _attempt_new_probe_setup(
    *,
    rpc_url: str,
    keypair_path: Path,
    signing_key: Any,
) -> dict[str, Any]:
    """Create USDC + collateral ATAs so deposit/redeem/flash_borrow probes can execute."""
    result: dict[str, Any] = {"attempted": True}
    spl_token = shutil.which("spl-token")
    if not spl_token:
        result["ata_error"] = "spl-token CLI not found"
        return result
    try:
        accounts = load_klend_accounts()
        reserve = accounts["reserves"]["USDC"]
        usdc_mint = reserve["mint"]
        collateral_mint = reserve.get("collateral_mint", None)
        for label, mint in [("usdc", usdc_mint), ("collateral", collateral_mint)]:
            if not mint:
                continue
            proc = subprocess.run(
                [
                    spl_token,
                    "-u", rpc_url,
                    "--fee-payer", str(keypair_path),
                    "create-account", mint,
                    "--owner", str(signing_key.pubkey()),
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            ata = derive_associated_token_account(signing_key.pubkey(), mint)
            result[f"{label}_ata"] = str(ata)
            result[f"{label}_returncode"] = proc.returncode
            result[f"{label}_stderr"] = proc.stderr.strip()[-500:]
    except Exception as exc:
        result["ata_error"] = str(exc)
    return result


def _attempt_borrow_probe_setup(
    *,
    rpc_url: str,
    keypair_path: Path,
    signing_key: Any,
    blockhash: bytes,
) -> dict[str, Any]:
    result: dict[str, Any] = {"attempted": True}
    try:
        setup_tx, setup_accounts = build_signed_borrow_setup_transaction(
            keypair=signing_key,
            recent_blockhash=blockhash,
        )
        setup_sig = _rpc(
            "sendTransaction",
            [b58encode(setup_tx), {"encoding": "base58", "skipPreflight": True, "maxRetries": 2}],
            url=rpc_url,
        )
        result.update({"setup_signature": str(setup_sig), **setup_accounts})
        result.update(_wait_signature_status(str(setup_sig), rpc_url=rpc_url))
    except Exception as exc:
        result.update({"setup_error": str(exc), "confirmed": False})

    collateral_lamports = int(os.environ.get("NSS_KLEND_COLLATERAL_LAMPORTS", "100000000"))
    if result.get("confirmed") and collateral_lamports > 0:
        try:
            spl_token = shutil.which("spl-token")
            if spl_token:
                wrap_lamports = collateral_lamports + int(
                    os.environ.get("NSS_KLEND_COLLATERAL_WRAP_BUFFER_LAMPORTS", "50000000")
                )
                accounts = load_klend_accounts()
                wsol_ata = derive_associated_token_account(
                    signing_key.pubkey(),
                    accounts["reserves"]["SOL"]["mint"],
                )
                wrap_proc = subprocess.run(
                    [
                        spl_token,
                        "-u",
                        rpc_url,
                        "--fee-payer",
                        str(keypair_path),
                        "wrap",
                        str(wrap_lamports / 1_000_000_000),
                        str(keypair_path),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                result.update(
                    {
                        "collateral_wrap_returncode": wrap_proc.returncode,
                        "collateral_wrap_stderr": wrap_proc.stderr.strip()[-500:],
                        "collateral_wrap_lamports": wrap_lamports,
                        "collateral_wsol_ata": str(wsol_ata),
                    }
                )
                deadline = time.time() + 15
                while time.time() < deadline:
                    try:
                        bal = _rpc(
                            "getTokenAccountBalance",
                            [str(wsol_ata)],
                            url=rpc_url,
                        )
                        amount_raw = int((bal.get("value") or {}).get("amount") or "0")
                        result["collateral_wsol_balance_raw"] = amount_raw
                        if amount_raw >= collateral_lamports:
                            break
                    except (urllib.error.URLError, RuntimeError, TypeError, ValueError):
                        pass
                    time.sleep(0.5)
            blockhash_resp = _rpc("getLatestBlockhash", [{"commitment": "confirmed"}], url=rpc_url)
            deposit_blockhash = b58decode(blockhash_resp["value"]["blockhash"])
            deposit_tx = build_signed_collateral_deposit_transaction(
                keypair=signing_key,
                recent_blockhash=deposit_blockhash,
                liquidity_amount=collateral_lamports,
            )
            deposit_sig = _rpc(
                "sendTransaction",
                [b58encode(deposit_tx), {"encoding": "base58", "skipPreflight": True, "maxRetries": 2}],
                url=rpc_url,
            )
            result["deposit_signature"] = str(deposit_sig)
            deposit_status = _wait_signature_status(str(deposit_sig), rpc_url=rpc_url, timeout_s=45)
            result["deposit_confirmed"] = deposit_status.get("confirmed")
            result["deposit_failed_on_chain"] = deposit_status.get("failed_on_chain")
            result["deposit_chain_error"] = deposit_status.get("chain_error")
            result["deposit_logs"] = _transaction_logs(str(deposit_sig), rpc_url=rpc_url)
            if result.get("collateral_wsol_balance_raw") is not None:
                result["collateral_wsol_balance_raw_after_deposit"] = result.get("collateral_wsol_balance_raw")
        except Exception as exc:
            result["deposit_error"] = str(exc)

    try:
        accounts = load_klend_accounts()
        mint = accounts["reserves"]["USDC"]["mint"]
        destination = derive_associated_token_account(signing_key.pubkey(), mint)
        spl_token = shutil.which("spl-token")
        if not spl_token:
            result["ata_error"] = "spl-token CLI not found"
            return result
        proc = subprocess.run(
            [
                spl_token,
                "-u",
                rpc_url,
                "--fee-payer",
                str(keypair_path),
                "create-account",
                mint,
                "--owner",
                str(signing_key.pubkey()),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        result.update(
            {
                "ata": str(destination),
                "ata_returncode": proc.returncode,
                "ata_stdout": proc.stdout.strip()[-500:],
                "ata_stderr": proc.stderr.strip()[-500:],
            }
        )
    except Exception as exc:
        result["ata_error"] = str(exc)
    return result


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
        for program in (KLEND_PROGRAM, KVAULT_PROGRAM, ORACLE_PROGRAM, FARMS_PROGRAM):
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
        reserve_pubkey = accounts["reserves"]["USDC"]["pubkey"]
        reserve_before = _reserve_field_snapshot(reserve_pubkey, url=rpc_url)
        chain_slot_before = _chain_slot(rpc_url)

        keypair_path, pubkey = _ensure_funded_keypair(rpc_url)
        if probe_id == "refresh_reserve_live":
            tx_result = _send_refresh_reserve_burst(
                rpc_url=rpc_url,
                keypair_path=keypair_path,
                pubkey=pubkey,
                attempts=int(os.environ.get("NSS_KLEND_REFRESH_ATTEMPTS", "2")),
            )
        else:
            tx_result = _send_klend_invoke(
                rpc_url=rpc_url,
                keypair_path=keypair_path,
                pubkey=pubkey,
                probe_id=probe_id,
            )
        shutil.rmtree(keypair_path.parent, ignore_errors=True)

        time.sleep(0.5)
        vault_after = _protocol_vault_deltas(accounts, url=rpc_url)
        reserve_after = _reserve_field_snapshot(reserve_pubkey, url=rpc_url, commitment="finalized")
        chain_slot_after = _chain_slot(rpc_url, commitment="finalized")
        reserve_slot_before = int(reserve_before.get("last_update_slot") or 0)
        reserve_slot_after = int(reserve_after.get("last_update_slot") or 0)
        reserve_slot_delta = max(0, reserve_slot_after - reserve_slot_before)
        cum_rate_changed = bool(
            reserve_before.get("cumulative_borrow_rate")
            and reserve_after.get("cumulative_borrow_rate")
            and reserve_before.get("cumulative_borrow_rate") != reserve_after.get("cumulative_borrow_rate")
        )
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
        refresh_log_ok = any(
            "instruction:refreshreserve" in str(line).lower().replace(" ", "")
            for line in (tx_result.get("tx_logs") or [])
        )
        field_delta_verified = (
            probe_id == "refresh_reserve_live"
            and not tx_result.get("failed_on_chain")
            and bool(tx_result.get("confirmed"))
            and (
                reserve_slot_delta > 0
                or cum_rate_changed
                or (refresh_log_ok and chain_slot_after > reserve_slot_before)
            )
        )
        result = {
            "probe_id": probe_id,
            "probe_executed": executed,
            "failed_on_chain": bool(tx_result.get("failed_on_chain")),
            "chain_error": tx_result.get("chain_error"),
            "tx_logs": tx_result.get("tx_logs") or [],
            "delta_lamports": delta,
            "wallet_delta_lamports": wallet_delta,
            "protocol_delta_lamports": protocol_delta_lamports,
            "usdc_vault_drain_micro": usdc_drain_micro,
            "sol_vault_drain_lamports": sol_drain_lamports,
            "tx_signature": tx_result.get("signature", ""),
            "setup": tx_result.get("setup") or {},
            "invariant_id": probe.invariant_id,
            "instruction": instruction_meta,
            "account_roles_count": len(account_roles.get("roles") or []),
            "account_roles_path": "data/security_results/klend/account_roles.json",
            "account_diff_path": _display_path(diff_path),
            "programs_verified": [KLEND_PROGRAM, KVAULT_PROGRAM, ORACLE_PROGRAM, FARMS_PROGRAM],
            "reserve_last_update_slot_before": reserve_slot_before,
            "reserve_last_update_slot_after": reserve_slot_after,
            "reserve_last_update_slot_delta": reserve_slot_delta,
            "cumulative_borrow_rate_changed": cum_rate_changed,
            "chain_slot_before": chain_slot_before,
            "chain_slot_after": chain_slot_after,
            "refresh_instruction_logged": refresh_log_ok,
            "meets_threshold": delta >= _LAMPORT_THRESHOLD or field_delta_verified,
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
