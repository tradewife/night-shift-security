"""Tests for the v5 NativeHarness manifest (audit recommendation C8)."""

from __future__ import annotations

import json
from pathlib import Path

from night_shift_security.native import (
    DEFAULT_PATH,
    HarnessStatus,
    empty_manifest,
    load_manifest,
    save_manifest,
    upsert_harness,
)


def test_empty_manifest_is_paused() -> None:
    payload = empty_manifest()
    assert payload["reason"] == "paused_awaiting_native_harness"
    assert payload["ready_count"] == 0
    assert payload["harnesses"] == {}


def test_upsert_inserts_and_counts_ready(tmp_path: Path) -> None:
    path = tmp_path / "native_harness_status.json"
    save_manifest(empty_manifest(), path)

    payload = upsert_harness(
        HarnessStatus(slug="uniswap_v4", name="Uniswap v4", status="mapped"),
        path,
    )
    assert payload["ready_count"] == 0
    assert payload["harnesses"]["uniswap_v4"]["status"] == "mapped"

    payload = upsert_harness(
        HarnessStatus(slug="uniswap_v4", name="Uniswap v4", status="ready"),
        path,
    )
    assert payload["ready_count"] == 1
    # Paused state clears once ready_count > 0.
    assert "reason" not in payload


def test_load_manifest_handles_missing_file(tmp_path: Path) -> None:
    payload = load_manifest(tmp_path / "missing.json")
    assert payload["ready_count"] == 0
    assert payload["reason"] == "paused_awaiting_native_harness"


def test_load_manifest_handles_garbage(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("not-json")
    payload = load_manifest(bad)
    assert payload["ready_count"] == 0


def test_default_path_is_in_data_dir() -> None:
    parts = list(DEFAULT_PATH.parts)
    assert "loop" in parts
    assert DEFAULT_PATH.name == "native_harness_status.json"


def test_persistence_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "native_harness_status.json"
    upsert_harness(HarnessStatus(slug="aave_v3", status="ready"), path)
    upsert_harness(HarnessStatus(slug="morpho", status="harness_built"), path)
    payload = load_manifest(path)
    assert payload["ready_count"] == 1
    assert set(payload["harnesses"].keys()) == {"aave_v3", "morpho"}

    raw = json.loads(path.read_text())
    assert raw["harnesses"]["aave_v3"]["status"] == "ready"
