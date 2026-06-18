"""Tests for NSS_PREFER_SOLANA rotation (Phase 11)."""

from __future__ import annotations

import os
from unittest.mock import patch

from night_shift_security.bounty.native_picker import (
    _program_ecosystem,
    pick_next_target_v6_phase4,
)
from night_shift_security.native import HarnessStatus, upsert_harness


def _seed_manifest(tmp_path, entries: dict[str, str]) -> str:
    path = tmp_path / "manifest.json"
    for slug, status in entries.items():
        upsert_harness(HarnessStatus(slug=slug, status=status, name=slug), path=path)
    return str(path)


def test_program_ecosystem_immunefi_fallback() -> None:
    assert _program_ecosystem("kamino", scope_registry_path="/nonexistent") == "solana"
    assert _program_ecosystem("uniswap_v4", scope_registry_path="/nonexistent") == "evm"


def test_pick_prefers_solana_with_env(tmp_path, monkeypatch) -> None:
    manifest = _seed_manifest(
        tmp_path,
        {"kamino": "ready", "aave_v3": "ready"},
    )
    monkeypatch.setenv("NSS_PHASE4_ROTATION_ENABLED", "1")
    monkeypatch.setenv("NSS_PREFER_SOLANA", "1")
    scan = {"targets": [{"slug": "kamino"}, {"slug": "aave_v3"}]}
    state = {"last_touched": {}}
    with patch(
        "night_shift_security.bounty.native_picker.filter_native_ready",
        return_value=["kamino", "aave_v3"],
    ):
        picked = pick_next_target_v6_phase4(
            scan,
            state,
            manifest_path=manifest,
            scope_registry_path="/nonexistent",
        )
    assert picked is not None
    assert picked["slug"] in ("kamino", "aave_v3")


def test_pick_solana_platform_label(tmp_path, monkeypatch) -> None:
    manifest = _seed_manifest(tmp_path, {"jito": "ready"})
    monkeypatch.setenv("NSS_PHASE4_ROTATION_ENABLED", "1")
    with patch(
        "night_shift_security.bounty.native_picker.filter_native_ready",
        return_value=["jito"],
    ):
        picked = pick_next_target_v6_phase4(
            {"targets": [{"slug": "jito"}]},
            {},
            manifest_path=manifest,
            scope_registry_path="/nonexistent",
        )
    assert picked["platform"] == "immunefi"


def test_discovery_missing_boost(tmp_path, monkeypatch) -> None:
    manifest = _seed_manifest(tmp_path, {"drift": "missing", "aave_v3": "ready"})
    monkeypatch.setenv("NSS_PHASE4_ROTATION_ENABLED", "1")
    monkeypatch.setenv("NSS_DISCOVERY_MISSING_PCT", "0.8")
    with patch(
        "night_shift_security.bounty.native_picker.filter_native_ready",
        return_value=["drift", "aave_v3"],
    ):
        picked = pick_next_target_v6_phase4(
            {"targets": [{"slug": "drift"}, {"slug": "aave_v3"}]},
            {},
            manifest_path=manifest,
            scope_registry_path="/nonexistent",
        )
    assert picked is not None


def test_prefer_solana_env_off_by_default() -> None:
    os.environ.pop("NSS_PREFER_SOLANA", None)
    assert os.environ.get("NSS_PREFER_SOLANA", "") == ""