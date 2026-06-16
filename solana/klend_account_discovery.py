"""Discover and cache Kamino KLend mainnet accounts for validator clone depth."""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from solders.pubkey import Pubkey

from klend_probes import KLEND_PROGRAM, ProbeAccountSpec

_REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ACCOUNTS_PATH = _REPO_ROOT / "sources" / "kamino" / "klend_accounts.json"
KAMINO_MARKET_API = (
    "https://api.kamino.finance/kamino-market/{market}/reserves/metrics"
)
DEFAULT_MARKET = "7u3HeHxYDLhnCoErrtycNokbQYbWGzLs6JSDqGAv5PfF"
_LIQUIDITY_SUPPLY_VAULT_OFFSET = 160
_LIQUIDITY_FEE_VAULT_OFFSET = 192


def _b58encode(data: bytes) -> str:
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    num = int.from_bytes(data, "big")
    enc = ""
    while num > 0:
        num, rem = divmod(num, 58)
        enc = alphabet[rem] + enc
    pad = sum(1 for byte in data if byte == 0)
    return alphabet[0] * pad + (enc or alphabet[0])


def _rpc(method: str, params: list | None, rpc_url: str) -> Any:
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}).encode()
    req = urllib.request.Request(rpc_url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode())
    if "error" in body:
        raise RuntimeError(f"RPC {method} failed: {body['error']}")
    return body["result"]


def _fetch_reserve_metrics(market: str = DEFAULT_MARKET) -> list[dict[str, Any]]:
    url = KAMINO_MARKET_API.format(market=market)
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    if not isinstance(data, list):
        raise RuntimeError(f"unexpected Kamino API response for {market}")
    return data


def _parse_vault_pubkeys(account_data: bytes) -> tuple[str, str]:
    if len(account_data) < _LIQUIDITY_FEE_VAULT_OFFSET + 32:
        raise ValueError("reserve account data too short for vault parse")
    supply = _b58encode(account_data[_LIQUIDITY_SUPPLY_VAULT_OFFSET : _LIQUIDITY_SUPPLY_VAULT_OFFSET + 32])
    fee = _b58encode(account_data[_LIQUIDITY_FEE_VAULT_OFFSET : _LIQUIDITY_FEE_VAULT_OFFSET + 32])
    return supply, fee


def _derive_pdas(market_pubkey: str) -> dict[str, str]:
    program = Pubkey.from_string(KLEND_PROGRAM)
    market = Pubkey.from_string(market_pubkey)
    authority, _ = Pubkey.find_program_address([b"lma", bytes(market)], program)
    global_config, _ = Pubkey.find_program_address([b"global_config"], program)
    return {
        "lending_market_authority": str(authority),
        "global_config": str(global_config),
    }


def refresh_klend_accounts(
    *,
    market_pubkey: str = DEFAULT_MARKET,
    rpc_url: str | None = None,
    path: Path = DEFAULT_ACCOUNTS_PATH,
) -> dict[str, Any]:
    """Refresh cached KLend accounts from Kamino HTTP API (+ optional RPC vault parse)."""
    metrics = _fetch_reserve_metrics(market_pubkey)
    reserves: dict[str, dict[str, str]] = {}
    for entry in metrics:
        symbol = str(entry.get("liquidityToken", "")).upper()
        if symbol not in {"USDC", "SOL"}:
            continue
        reserve_pubkey = str(entry["reserve"])
        mint = str(entry.get("liquidityTokenMint", ""))
        reserve_info: dict[str, str] = {"pubkey": reserve_pubkey, "mint": mint}
        if rpc_url:
            result = _rpc("getAccountInfo", [reserve_pubkey, {"encoding": "base64"}], rpc_url)
            value = result.get("value")
            if value and value.get("data"):
                raw = base64.b64decode(value["data"][0])
                supply, fee = _parse_vault_pubkeys(raw)
                reserve_info["supply_vault"] = supply
                reserve_info["fee_vault"] = fee
        reserves[symbol] = reserve_info

    if "USDC" not in reserves or "SOL" not in reserves:
        raise RuntimeError("Kamino API missing USDC or SOL reserve for main market")

    pdas = _derive_pdas(market_pubkey)
    payload = {
        "discovery_version": "1.0",
        "market_pubkey": market_pubkey,
        "lending_market_authority": pdas["lending_market_authority"],
        "global_config": pdas["global_config"],
        "reserves": reserves,
        "source": "kamino-api" + ("+rpc" if rpc_url else ""),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")
    return payload


def load_klend_accounts(path: Path = DEFAULT_ACCOUNTS_PATH) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"KLend accounts cache missing: {path}")
    return json.loads(path.read_text())


def klend_clone_data_accounts(path: Path = DEFAULT_ACCOUNTS_PATH) -> tuple[str, ...]:
    """Pubkeys to `--clone` on solana-test-validator (non-program data accounts)."""
    data = load_klend_accounts(path)
    accounts = [
        data["market_pubkey"],
        data["lending_market_authority"],
        data["global_config"],
    ]
    for symbol in ("USDC", "SOL"):
        reserve = data["reserves"][symbol]
        accounts.extend(
            [
                reserve["pubkey"],
                reserve.get("mint", ""),
                reserve["supply_vault"],
                reserve.get("fee_vault", ""),
            ]
        )
    return tuple(dict.fromkeys(pubkey for pubkey in accounts if pubkey))


def probe_data_account_specs(probe_id: str, path: Path = DEFAULT_ACCOUNTS_PATH) -> tuple[ProbeAccountSpec, ...]:
    """Mainnet lending-market accounts appended before program metas for CPI depth."""
    data = load_klend_accounts(path)
    usdc = data["reserves"]["USDC"]
    sol = data["reserves"]["SOL"]
    common = (
        ProbeAccountSpec(data["market_pubkey"], is_writable=True, role="lending_market"),
        ProbeAccountSpec(data["lending_market_authority"], role="lending_market_authority"),
        ProbeAccountSpec(data["global_config"], role="global_config"),
        ProbeAccountSpec(usdc["pubkey"], is_writable=True, role="usdc_reserve"),
        ProbeAccountSpec(sol["pubkey"], is_writable=True, role="sol_reserve"),
        ProbeAccountSpec(usdc["supply_vault"], is_writable=True, role="usdc_supply_vault"),
        ProbeAccountSpec(sol["supply_vault"], is_writable=True, role="sol_supply_vault"),
    )
    if probe_id == "flash_loan_collateral_loop":
        return common + (
            ProbeAccountSpec(usdc["mint"], role="usdc_mint"),
            ProbeAccountSpec(sol["mint"], role="sol_mint"),
        )
    return common
