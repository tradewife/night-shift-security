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
_RESERVE_DISCRIMINATOR_SIZE = 8
_LIQUIDITY_MINT_OFFSET = 128
_LIQUIDITY_SUPPLY_VAULT_OFFSET = 160
_LIQUIDITY_FEE_VAULT_OFFSET = 192
_RESERVE_LIQUIDITY_SIZE = 1232
_RESERVE_LIQUIDITY_PADDING_SIZE = 150 * 8
_RESERVE_FARM_COLLATERAL_OFFSET = _RESERVE_DISCRIMINATOR_SIZE + 8 + 16 + 32
_COLLATERAL_MINT_OFFSET = (
    _RESERVE_DISCRIMINATOR_SIZE
    + 8
    + 16
    + 96
    + _RESERVE_LIQUIDITY_SIZE
    + _RESERVE_LIQUIDITY_PADDING_SIZE
)
_COLLATERAL_SUPPLY_VAULT_OFFSET = _COLLATERAL_MINT_OFFSET + 40
_TOKEN_INFO_OFFSET = 5_032
_SCOPE_PRICE_FEED_OFFSET = _TOKEN_INFO_OFFSET + 80
_SWITCHBOARD_PRICE_OFFSET = _TOKEN_INFO_OFFSET + 128
_SWITCHBOARD_TWAP_OFFSET = _TOKEN_INFO_OFFSET + 160
_PYTH_PRICE_OFFSET = _TOKEN_INFO_OFFSET + 192


def _b58encode(data: bytes) -> str:
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    num = int.from_bytes(data, "big")
    enc = ""
    while num > 0:
        num, rem = divmod(num, 58)
        enc = alphabet[rem] + enc
    pad = 0
    for byte in data:
        if byte == 0:
            pad += 1
        else:
            break
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


def _parse_farm_collateral_pubkey(account_data: bytes) -> str:
    if len(account_data) < _RESERVE_FARM_COLLATERAL_OFFSET + 32:
        raise ValueError("reserve account data too short for farm collateral parse")
    farm = _b58encode(account_data[_RESERVE_FARM_COLLATERAL_OFFSET : _RESERVE_FARM_COLLATERAL_OFFSET + 32])
    return farm if farm else ""


def _parse_collateral_pubkeys(account_data: bytes) -> tuple[str, str]:
    """Parse Reserve.collateral mint + supply vault from on-chain reserve layout."""
    if len(account_data) < _COLLATERAL_SUPPLY_VAULT_OFFSET + 32:
        raise ValueError("reserve account data too short for collateral parse")
    mint = _b58encode(account_data[_COLLATERAL_MINT_OFFSET : _COLLATERAL_MINT_OFFSET + 32])
    supply = _b58encode(
        account_data[_COLLATERAL_SUPPLY_VAULT_OFFSET : _COLLATERAL_SUPPLY_VAULT_OFFSET + 32]
    )
    if not mint or not supply:
        raise ValueError("reserve collateral mint/supply vault missing in account data")
    return mint, supply


def _parse_oracle_pubkeys(account_data: bytes) -> dict[str, str]:
    """Parse KLend Reserve.config.token_info oracle pubkeys from account data."""
    if len(account_data) < _PYTH_PRICE_OFFSET + 32:
        raise ValueError("reserve account data too short for oracle parse")

    def pubkey_at(offset: int) -> str:
        raw = account_data[offset : offset + 32]
        if raw == bytes(32):
            return ""
        return _b58encode(raw)

    return {
        "scope_prices": pubkey_at(_SCOPE_PRICE_FEED_OFFSET),
        "switchboard_price_oracle": pubkey_at(_SWITCHBOARD_PRICE_OFFSET),
        "switchboard_twap_oracle": pubkey_at(_SWITCHBOARD_TWAP_OFFSET),
        "pyth_oracle": pubkey_at(_PYTH_PRICE_OFFSET),
    }


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
                collateral_mint, collateral_supply = _parse_collateral_pubkeys(raw)
                farm_collateral = _parse_farm_collateral_pubkey(raw)
                reserve_info["supply_vault"] = supply
                reserve_info["fee_vault"] = fee
                reserve_info["collateral_mint"] = collateral_mint
                reserve_info["collateral_supply_vault"] = collateral_supply
                if farm_collateral:
                    reserve_info["farm_collateral"] = farm_collateral
                reserve_info.update(_parse_oracle_pubkeys(raw))
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


def refresh_klend_accounts_from_rpc(
    *,
    rpc_url: str,
    path: Path = DEFAULT_ACCOUNTS_PATH,
) -> dict[str, Any]:
    """Refresh vault/oracle fields from RPC using the cached market/reserve keys."""
    payload = load_klend_accounts(path)
    for symbol, reserve_info in payload.get("reserves", {}).items():
        reserve_pubkey = str(reserve_info["pubkey"])
        result = _rpc("getAccountInfo", [reserve_pubkey, {"encoding": "base64"}], rpc_url)
        value = result.get("value")
        if not value or not value.get("data"):
            raise RuntimeError(f"RPC missing reserve account data for {symbol}:{reserve_pubkey}")
        raw = base64.b64decode(value["data"][0])
        supply, fee = _parse_vault_pubkeys(raw)
        collateral_mint, collateral_supply = _parse_collateral_pubkeys(raw)
        farm_collateral = _parse_farm_collateral_pubkey(raw)
        reserve_info["supply_vault"] = supply
        reserve_info["fee_vault"] = fee
        reserve_info["collateral_mint"] = collateral_mint
        reserve_info["collateral_supply_vault"] = collateral_supply
        if farm_collateral:
            reserve_info["farm_collateral"] = farm_collateral
        reserve_info.update(_parse_oracle_pubkeys(raw))
    payload["source"] = str(payload.get("source") or "cached") + "+rpc-oracles"
    path.write_text(json.dumps(payload, indent=2) + "\n")
    return payload


def load_klend_accounts(path: Path = DEFAULT_ACCOUNTS_PATH) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"KLend accounts cache missing: {path}")
    return json.loads(path.read_text())


def derive_reserve_pdas(reserve_pubkey: str) -> dict[str, str]:
    """KLend reserve liquidity/collateral vault PDAs (matches klend-interface pda.rs)."""
    program = Pubkey.from_string(KLEND_PROGRAM)
    reserve = Pubkey.from_string(reserve_pubkey)

    def _pda(seed: bytes) -> str:
        pubkey, _bump = Pubkey.find_program_address([seed, bytes(reserve)], program)
        return str(pubkey)

    return {
        "liquidity_supply_vault": _pda(b"reserve_liq_supply"),
        "fee_vault": _pda(b"fee_receiver"),
        "collateral_mint": _pda(b"reserve_coll_mint"),
        "collateral_supply_vault": _pda(b"reserve_coll_supply"),
    }


def reserve_collateral_accounts(
    *,
    symbol: str = "SOL",
    path: Path = DEFAULT_ACCOUNTS_PATH,
) -> tuple[str, str]:
    """Collateral mint + supply vault pubkeys parsed from mainnet reserve state."""
    data = load_klend_accounts(path)
    reserve = (data.get("reserves") or {}).get(symbol.upper())
    if not reserve:
        raise KeyError(f"reserve missing for symbol={symbol}")
    mint = str(reserve.get("collateral_mint") or "").strip()
    supply = str(reserve.get("collateral_supply_vault") or "").strip()
    if not mint or not supply:
        raise RuntimeError(
            f"reserve collateral accounts missing for {symbol}; run refresh_klend_accounts_from_rpc"
        )
    return mint, supply


def derive_obligation_farm_user_state(*, farm_state: str, obligation: str) -> str:
    farms_program = Pubkey.from_string("FarmsPZpWu9i7Kky8tPN37rs2TpmMrAZrC7S7vJa91Hr")
    farm_pubkey = Pubkey.from_string(farm_state)
    obligation_pubkey = Pubkey.from_string(obligation)
    user_state, _bump = Pubkey.find_program_address(
        [b"user", bytes(farm_pubkey), bytes(obligation_pubkey)],
        farms_program,
    )
    return str(user_state)


def reserve_farm_collateral_account(
    *,
    symbol: str = "SOL",
    path: Path = DEFAULT_ACCOUNTS_PATH,
) -> str:
    data = load_klend_accounts(path)
    reserve = (data.get("reserves") or {}).get(symbol.upper()) or {}
    farm = str(reserve.get("farm_collateral") or "").strip()
    if not farm:
        raise RuntimeError(f"farm_collateral missing for {symbol}; run refresh_klend_accounts_from_rpc")
    return farm


def klend_collateral_clone_accounts(
    *,
    symbol: str = "SOL",
    path: Path = DEFAULT_ACCOUNTS_PATH,
) -> tuple[str, ...]:
    """Reserve collateral mint + supply vault accounts for deposit/borrow depth."""
    accounts: list[str] = []
    try:
        mint, supply = reserve_collateral_accounts(symbol=symbol, path=path)
        accounts.extend([mint, supply])
    except (KeyError, RuntimeError):
        pass
    try:
        accounts.append(reserve_farm_collateral_account(symbol=symbol, path=path))
    except RuntimeError:
        pass
    return tuple(dict.fromkeys(pubkey for pubkey in accounts if pubkey))


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
                reserve.get("pyth_oracle", ""),
                reserve.get("switchboard_price_oracle", ""),
                reserve.get("switchboard_twap_oracle"),
                reserve.get("scope_prices", ""),
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
