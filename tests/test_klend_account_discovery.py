"""Tests for Kamino KLend mainnet account discovery cache."""

import json
import sys
from pathlib import Path

_SOLANA_ROOT = Path(__file__).resolve().parents[1] / "solana"
if str(_SOLANA_ROOT) not in sys.path:
    sys.path.insert(0, str(_SOLANA_ROOT))

from klend_account_discovery import (  # noqa: E402
    DEFAULT_ACCOUNTS_PATH,
    klend_clone_data_accounts,
    load_klend_accounts,
    probe_data_account_specs,
)


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