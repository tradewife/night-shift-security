"""Tests for Scope OraclePrices timestamp patching."""

from __future__ import annotations

import struct
import sys
from pathlib import Path

import pytest

_SOLANA_ROOT = Path(__file__).resolve().parents[1] / "solana"
if str(_SOLANA_ROOT) not in sys.path:
    sys.path.insert(0, str(_SOLANA_ROOT))

from klend_scope_patch import (  # noqa: E402
    DATED_PRICE_SIZE,
    MAX_SCOPE_ENTRIES,
    ORACLE_PRICES_DISCRIMINATOR,
    ORACLE_PRICES_HEADER_SIZE,
    UNIX_TIMESTAMP_OFFSET_IN_ENTRY,
    patch_oracle_prices_timestamps,
)


def _sample_oracle_prices_account() -> bytes:
    body = bytearray(ORACLE_PRICES_HEADER_SIZE + DATED_PRICE_SIZE * MAX_SCOPE_ENTRIES)
    body[:8] = ORACLE_PRICES_DISCRIMINATOR
    entry_base = ORACLE_PRICES_HEADER_SIZE
    struct.pack_into("<Q", body, entry_base, 100)
    struct.pack_into("<Q", body, entry_base + 8, 8)
    struct.pack_into("<Q", body, entry_base + 16, 1)
    struct.pack_into("<Q", body, entry_base + 24, 1_700_000_000)
    return bytes(body)


def test_patch_oracle_prices_updates_populated_entries():
    raw = _sample_oracle_prices_account()
    patched, updated = patch_oracle_prices_timestamps(raw, unix_timestamp=1_900_000_000, slot=42)
    assert updated == 1
    entry_base = ORACLE_PRICES_HEADER_SIZE
    ts = struct.unpack_from("<Q", patched, entry_base + UNIX_TIMESTAMP_OFFSET_IN_ENTRY)[0]
    slot = struct.unpack_from("<Q", patched, entry_base + 16)[0]
    assert ts == 1_900_000_000
    assert slot == 42


def test_patch_oracle_prices_rejects_bad_discriminator():
    raw = _sample_oracle_prices_account()
    bad = b"\x00" * 8 + raw[8:]
    with pytest.raises(ValueError, match="discriminator"):
        patch_oracle_prices_timestamps(bad, unix_timestamp=1)