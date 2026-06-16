"""Tests for Kamino KLend mainnet account discovery cache."""

import json
import sys
from pathlib import Path

_SOLANA_ROOT = Path(__file__).resolve().parents[1] / "solana"
if str(_SOLANA_ROOT) not in sys.path:
    sys.path.insert(0, str(_SOLANA_ROOT))

from klend_account_discovery import (  # noqa: E402
    DEFAULT_ACCOUNTS_PATH,
    _PYTH_PRICE_OFFSET,
    _SCOPE_PRICE_FEED_OFFSET,
    _SWITCHBOARD_PRICE_OFFSET,
    _SWITCHBOARD_TWAP_OFFSET,
    _parse_oracle_pubkeys,
    klend_clone_data_accounts,
    load_klend_accounts,
    probe_data_account_specs,
)
from solders.pubkey import Pubkey  # noqa: E402


def test_klend_accounts_cache_has_main_market_reserves():
    data = load_klend_accounts()
    assert data["market_pubkey"] == "7u3HeHxYDLhnCoErrtycNokbQYbWGzLs6JSDqGAv5PfF"
    assert data["reserves"]["USDC"]["pubkey"] == "D6q6wuQSrifJKZYpR1M8R4YawnLDtDsMmWM1NbBmgJ59"
    assert data["reserves"]["SOL"]["pubkey"] == "d4A2prbA2whesmvHaL88BH6Ewn5N4bTSU2Ze8P6Bc4Q"
    assert data["reserves"]["USDC"]["supply_vault"] == "Bgq7trRgVMeq33yt235zM2onQ4bRDBsY5EWiTetF4qw6"


def test_klend_clone_data_accounts_includes_market_and_vaults():
    clones = klend_clone_data_accounts()
    assert "7u3HeHxYDLhnCoErrtycNokbQYbWGzLs6JSDqGAv5PfF" in clones
    assert "Bgq7trRgVMeq33yt235zM2onQ4bRDBsY5EWiTetF4qw6" in clones
    assert len(clones) >= 8


def test_probe_data_account_specs_prepend_market_accounts():
    specs = probe_data_account_specs("oracle_staleness_borrow")
    roles = [s.role for s in specs]
    assert roles[:3] == ["lending_market", "lending_market_authority", "global_config"]
    assert "usdc_supply_vault" in roles


def test_klend_accounts_json_valid():
    payload = json.loads(DEFAULT_ACCOUNTS_PATH.read_text())
    assert payload["discovery_version"] == "1.0"
    assert "USDC" in payload["reserves"]
    assert "SOL" in payload["reserves"]


def test_parse_oracle_pubkeys_from_reserve_layout():
    raw = bytearray(_PYTH_PRICE_OFFSET + 32)
    keys = {
        _SCOPE_PRICE_FEED_OFFSET: "HFn8GnPADiny6XqUoWE8uRPPxb29ikn4yTuPa9MF2fWJ",
        _SWITCHBOARD_PRICE_OFFSET: "So11111111111111111111111111111111111111112",
        _SWITCHBOARD_TWAP_OFFSET: "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        _PYTH_PRICE_OFFSET: "11111111111111111111111111111111",
    }
    for offset, key in keys.items():
        raw[offset : offset + 32] = bytes(Pubkey.from_string(key))
    parsed = _parse_oracle_pubkeys(bytes(raw))
    assert parsed["scope_prices"] == "HFn8GnPADiny6XqUoWE8uRPPxb29ikn4yTuPa9MF2fWJ"
    assert parsed["switchboard_price_oracle"] == "So11111111111111111111111111111111111111112"
    assert parsed["switchboard_twap_oracle"] == "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    assert parsed["pyth_oracle"] == ""
