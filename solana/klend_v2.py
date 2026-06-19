"""KLend v2 instruction/account-role helpers for live probes."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from klend_probes import KLEND_PROGRAM, KVAULT_PROGRAM, ORACLE_PROGRAM, SPL_TOKEN_PROGRAM, SYSTEM_PROGRAM

REPO_ROOT = Path(__file__).resolve().parents[1]
KLEND_DIR = REPO_ROOT / "data/security_results/klend"
INSTRUCTION_MAP_PATH = KLEND_DIR / "instruction_map.json"
ACCOUNT_ROLES_PATH = KLEND_DIR / "account_roles.json"
PROBE_RESULTS_PATH = KLEND_DIR / "probe_results.jsonl"
ACCOUNT_DIFF_DIR = KLEND_DIR / "account_diffs"

ANCHOR_BUILTIN_ERRORS: dict[int, str] = {
    102: "InstructionDidNotDeserialize",
    3002: "AccountNotEnoughKeys",
    3007: "AccountOwnedByWrongProgram",
    3009: "InvalidProgramExecutable",
}

KLEND_LENDING_ERRORS: dict[int, str] = {
    6007: "MathOverflow",
    6009: "ReserveStale",
    6017: "ObligationStale",
    6020: "ObligationDepositsEmpty",
    6022: "ObligationDepositsZero",
}


PROBE_INSTRUCTION_NAMES: dict[str, str] = {
    "refresh_reserve_live": "refresh_reserve",
    "oracle_staleness_borrow": "borrow_obligation_liquidity_v2",
    "flash_loan_collateral_loop": "flash_borrow_reserve_liquidity",
    "reserve_isolation_drain": "redeem_reserve_collateral",
    "liquidation_solvency_gap": "liquidate_obligation_and_redeem_reserve_collateral_v2",
}

PUBLIC_KLEND_INSTRUCTIONS: tuple[str, ...] = (
    "init_lending_market",
    "update_lending_market",
    "init_reserve",
    "refresh_reserve",
    "deposit_reserve_liquidity",
    "redeem_reserve_collateral",
    "init_obligation",
    "refresh_obligation",
    "deposit_obligation_collateral",
    "deposit_obligation_collateral_v2",
    "withdraw_obligation_collateral",
    "withdraw_obligation_collateral_v2",
    "withdraw_obligation_collateral_and_redeem_reserve_collateral_v2",
    "borrow_obligation_liquidity_v2",
    "repay_obligation_liquidity",
    "repay_obligation_liquidity_v2",
    "liquidate_obligation_and_redeem_reserve_collateral_v2",
    "flash_borrow_reserve_liquidity",
    "flash_repay_reserve_liquidity",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def anchor_discriminator(name: str) -> str:
    return hashlib.sha256(f"global:{name}".encode()).digest()[:8].hex()


def klend_instruction_map() -> dict[str, Any]:
    instructions = {
        name: {
            "name": name,
            "discriminator_hex": anchor_discriminator(name),
            "discriminator": "0x" + anchor_discriminator(name),
            "program_id": KLEND_PROGRAM,
        }
        for name in PUBLIC_KLEND_INSTRUCTIONS
    }
    return {
        "schema_version": 2,
        "generated_at": _utc_now(),
        "program_id": KLEND_PROGRAM,
        "source": "anchor_discriminator_names",
        "instructions": instructions,
        "probe_bindings": {
            probe_id: instructions[name]
            for probe_id, name in PROBE_INSTRUCTION_NAMES.items()
            if name in instructions
        },
    }


def write_instruction_map(path: Path = INSTRUCTION_MAP_PATH) -> dict[str, Any]:
    payload = klend_instruction_map()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def instruction_data_for_probe(probe_id: str) -> bytes:
    name = PROBE_INSTRUCTION_NAMES.get(probe_id)
    if not name:
        return b"\xff"
    discriminator = bytes.fromhex(anchor_discriminator(name))
    one_unit = (1).to_bytes(8, "little")
    zero = (0).to_bytes(8, "little")
    if probe_id == "refresh_reserve_live":
        return discriminator
    if probe_id in {
        "oracle_staleness_borrow",
        "flash_loan_collateral_loop",
        "reserve_isolation_drain",
    }:
        return discriminator + one_unit
    if probe_id == "liquidation_solvency_gap":
        return discriminator + one_unit + zero + zero
    return discriminator


def instruction_meta_for_probe(probe_id: str) -> dict[str, Any]:
    mapping = klend_instruction_map()
    return dict((mapping.get("probe_bindings") or {}).get(probe_id) or {})


def build_account_roles(accounts: dict[str, Any]) -> dict[str, Any]:
    reserves = accounts.get("reserves") or {}
    roles: list[dict[str, Any]] = [
        {"role": "klend_program", "pubkey": KLEND_PROGRAM, "kind": "program", "executable": True},
        {"role": "kvault_program", "pubkey": KVAULT_PROGRAM, "kind": "program", "executable": True},
        {"role": "oracle_program", "pubkey": ORACLE_PROGRAM, "kind": "program", "executable": True},
        {"role": "spl_token_program", "pubkey": SPL_TOKEN_PROGRAM, "kind": "program", "executable": True},
        {"role": "system_program", "pubkey": SYSTEM_PROGRAM, "kind": "program", "executable": True},
        {"role": "lending_market", "pubkey": accounts.get("market_pubkey", ""), "kind": "data", "writable": True},
        {
            "role": "lending_market_authority",
            "pubkey": accounts.get("lending_market_authority", ""),
            "kind": "pda",
        },
        {"role": "global_config", "pubkey": accounts.get("global_config", ""), "kind": "data"},
    ]
    for symbol, reserve in reserves.items():
        if not isinstance(reserve, dict):
            continue
        prefix = str(symbol).lower()
        roles.extend(
            [
                {"role": f"{prefix}_reserve", "pubkey": reserve.get("pubkey", ""), "kind": "reserve", "writable": True},
                {"role": f"{prefix}_supply_vault", "pubkey": reserve.get("supply_vault", ""), "kind": "token_account", "writable": True},
                {"role": f"{prefix}_fee_vault", "pubkey": reserve.get("fee_vault", ""), "kind": "token_account", "writable": True},
                {"role": f"{prefix}_mint", "pubkey": reserve.get("mint", ""), "kind": "mint"},
            ]
        )
    return {
        "schema_version": 2,
        "generated_at": _utc_now(),
        "roles": [r for r in roles if r.get("pubkey")],
    }


def write_account_roles(accounts: dict[str, Any], path: Path = ACCOUNT_ROLES_PATH) -> dict[str, Any]:
    payload = build_account_roles(accounts)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def account_diff(before: dict[str, int], after: dict[str, int]) -> dict[str, Any]:
    keys = sorted(set(before) | set(after))
    return {
        "before": before,
        "after": after,
        "deltas": {key: int(after.get(key, 0)) - int(before.get(key, 0)) for key in keys},
    }


def _custom_error_code(result: dict[str, Any]) -> int | None:
    chain_error = result.get("chain_error")
    if isinstance(chain_error, dict):
        instruction_error = chain_error.get("InstructionError")
        if (
            isinstance(instruction_error, list)
            and len(instruction_error) >= 2
            and isinstance(instruction_error[1], dict)
            and "Custom" in instruction_error[1]
        ):
            try:
                return int(instruction_error[1]["Custom"])
            except (TypeError, ValueError):
                return None
    error = str(result.get("error") or "")
    if "Custom" not in error:
        return None
    for token in error.replace("{", " ").replace("}", " ").replace("[", " ").replace("]", " ").split():
        try:
            return int(token.strip(":,"))
        except ValueError:
            continue
    return None


def anchor_builtin_error_name(result: dict[str, Any]) -> str:
    code = _custom_error_code(result)
    return ANCHOR_BUILTIN_ERRORS.get(code or -1, "")


def klend_lending_error_name(result: dict[str, Any]) -> str:
    code = _custom_error_code(result)
    return KLEND_LENDING_ERRORS.get(code or -1, "")


def write_account_diff(probe_id: str, before: dict[str, int], after: dict[str, int]) -> Path:
    ACCOUNT_DIFF_DIR.mkdir(parents=True, exist_ok=True)
    safe_ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = ACCOUNT_DIFF_DIR / f"{probe_id}-{safe_ts}.json"
    path.write_text(json.dumps(account_diff(before, after), indent=2, sort_keys=True) + "\n")
    return path


def classify_failure(result: dict[str, Any]) -> str:
    error = str(result.get("error") or "").lower()
    if "data_account_missing" in error or "missing account" in error:
        return "missing_account"
    if "program_not_deployed" in error:
        return "missing_program"
    if "invalid instruction" in error or "bad discriminator" in error:
        return "bad_discriminator"
    if "owner" in error:
        return "owner_mismatch"
    if result.get("failed_on_chain"):
        tx_logs = "\n".join(str(line).lower() for line in result.get("tx_logs") or [])
        if "price is too old" in tx_logs or "pricetooold" in tx_logs:
            return "oracle_price_too_old"
        anchor_error = anchor_builtin_error_name(result)
        if anchor_error == "InstructionDidNotDeserialize":
            return "bad_instruction_data"
        if anchor_error == "AccountNotEnoughKeys":
            return "account_metas_incomplete"
        if anchor_error == "AccountOwnedByWrongProgram":
            return "account_owner_mismatch"
        if anchor_error == "InvalidProgramExecutable":
            return "invalid_program_executable"
        lending_error = klend_lending_error_name(result)
        if lending_error == "MathOverflow":
            return "math_overflow"
        if lending_error == "ReserveStale":
            return "reserve_stale"
        if lending_error == "ObligationStale":
            return "obligation_stale"
        if lending_error == "ObligationDepositsEmpty":
            return "obligation_deposits_empty"
        if lending_error == "ObligationDepositsZero":
            return "obligation_deposits_zero"
        return "failed_on_chain"
    if int(result.get("reserve_last_update_slot_delta") or 0) > 0 and not result.get("failed_on_chain"):
        return "reserve_refresh_verified"
    if result.get("refresh_instruction_logged") and not result.get("failed_on_chain"):
        if result.get("cumulative_borrow_rate_changed"):
            return "reserve_refresh_verified"
        return "reserve_refresh_executed"
    if result.get("probe_executed") and int(result.get("protocol_delta_lamports") or 0) <= 0:
        wallet_delta = int(result.get("wallet_delta_lamports") or result.get("delta_lamports") or 0)
        if wallet_delta > 0:
            return "fee_only"
        return "no_protocol_delta"
    if not result.get("probe_executed"):
        return "not_executed"
    return "non_blocking"


def append_probe_result(result: dict[str, Any], path: Path = PROBE_RESULTS_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(result)
    payload.setdefault("recorded_at", _utc_now())
    with path.open("a") as fh:
        fh.write(json.dumps(payload, sort_keys=True) + "\n")
    return path
