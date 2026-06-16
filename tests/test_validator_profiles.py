"""Tests for Solana validator profiles."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "solana"))

from validator_profiles import get_validator_profile, validator_backed_exploit_ids


def test_mango_validator_profile_exists():
    profile = get_validator_profile("mango-markets-2022")
    assert profile is not None
    assert profile.historical_slot == 152_000_000
    assert "4MangoMjqJ2firMokCjjGgoK8d4MXcrgL7XJaL3w6fVg" in profile.clone_accounts


def test_validator_backed_includes_mango():
    assert "mango-markets-2022" in validator_backed_exploit_ids()


def test_kamino_klend_clones_mainnet_data_accounts():
    profile = get_validator_profile("kamino-klend")
    assert profile is not None
    assert "FarmsPZpWu9i7Kky8tPN37rs2TpmMrAZrC7S7vJa91Hr" in profile.clone_accounts
    assert len(profile.clone_data_accounts) >= 8
    assert "7u3HeHxYDLhnCoErrtycNokbQYbWGzLs6JSDqGAv5PfF" in profile.clone_data_accounts
    assert "D6q6wuQSrifJKZYpR1M8R4YawnLDtDsMmWM1NbBmgJ59" in profile.clone_data_accounts
