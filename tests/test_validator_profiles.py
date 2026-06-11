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