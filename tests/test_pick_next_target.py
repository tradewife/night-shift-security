"""Audit correction C3 — native-harness precondition gate for ``pick_next_target``.

The picker must refuse any candidate slug whose native-harness entry is
missing or in the ``mapped`` state (audit C3 exports a typed exception
rather than silent skip; the legacy 28-curated test surface retains
silent ``None`` as long as the manifest is absent so the old fixtures
keep behaving). Tests use a fixture manifest so no live RPC is required.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from night_shift_security.bounty.native_picker import (
    EmptyManifest,
    NativeStatusIncomplete,
    PickRefused,
    filter_native_ready,
    has_measured_delta,
    list_pickable_slugs,
    native_status_of,
    pick_native_ready_or_raise,
)
from night_shift_security.orchestration import bounty_loop as bl


def _write_manifest(path: Path, harnesses: dict[str, dict[str, object]]) -> Path:
    payload = {
        "schema_version": "1.0",
        "harnesses": harnesses,
        "ready_count": sum(
            1 for h in harnesses.values() if h.get("status") == "ready"
        ),
    }
    path.write_text(json.dumps(payload))
    return path


def test_native_status_of_returns_entry(tmp_path: Path):
    manifest = _write_manifest(
        tmp_path / "manifest.json",
        {"uniswap_v4": {"slug": "uniswap_v4", "status": "ready"}},
    )
    entry = native_status_of("uniswap_v4", manifest_path=manifest)
    assert entry is not None
    assert entry.status == "ready"
    assert entry.rank == 3


def test_native_status_of_empty_returns_none(tmp_path: Path):
    manifest = tmp_path / "empty.json"
    assert native_status_of("uniswap_v4", manifest_path=manifest) is None


def test_filter_native_ready_drops_missing_and_mapped(tmp_path: Path):
    manifest = _write_manifest(
        tmp_path / "manifest.json",
        {
            "uniswap_v4": {"slug": "uniswap_v4", "status": "ready"},
            "pendle": {"slug": "pendle", "status": "harness_built"},
            "wormhole": {"slug": "wormhole", "status": "paused"},
            "kamino": {"slug": "kamino", "status": "mapped"},
            "euler": {"slug": "euler", "status": "missing"},
        },
    )
    slugs = filter_native_ready(
        ["uniswap_v4", "pendle", "wormhole", "kamino", "euler"],
        manifest_path=manifest,
    )
    assert slugs == ["uniswap_v4", "pendle", "wormhole"]


def test_pick_native_ready_or_raise_prefers_ready(tmp_path: Path):
    manifest = _write_manifest(
        tmp_path / "manifest.json",
        {
            "pendle": {"slug": "pendle", "status": "harness_built"},
            "uniswap_v4": {"slug": "uniswap_v4", "status": "ready"},
            "kamino": {"slug": "kamino", "status": "ready"},
        },
    )
    slug = pick_native_ready_or_raise(
        ["pendle", "uniswap_v4", "kamino"],
        manifest_path=manifest,
    )
    assert slug in {"uniswap_v4", "kamino"}


def test_pick_native_ready_or_raise_fallback_to_harness_built(tmp_path: Path):
    manifest = _write_manifest(
        tmp_path / "manifest.json",
        {
            "pendle": {"slug": "pendle", "status": "harness_built"},
            "wormhole": {"slug": "wormhole", "status": "paused"},
        },
    )
    slug = pick_native_ready_or_raise(
        ["pendle", "wormhole"],
        manifest_path=manifest,
    )
    assert slug in {"pendle", "wormhole"}


def test_pick_native_ready_or_raise_raises_when_only_mapped(tmp_path: Path):
    manifest = _write_manifest(
        tmp_path / "manifest.json",
        {
            "pendle": {"slug": "pendle", "status": "mapped"},
            "kamino": {"slug": "kamino", "status": "missing"},
        },
    )
    with pytest.raises(NativeStatusIncomplete) as excinfo:
        pick_native_ready_or_raise(
            ["pendle", "kamino"],
            manifest_path=manifest,
        )
    assert "refused states seen" in str(excinfo.value)


def test_pick_native_ready_or_raise_raises_on_empty_manifest(tmp_path: Path):
    empty = tmp_path / "empty.json"
    empty.write_text(json.dumps({"schema_version": "1.0", "harnesses": {}}))
    with pytest.raises(EmptyManifest):
        pick_native_ready_or_raise(["x"], manifest_path=empty)


def test_pick_next_target_enforces_native_gate(tmp_path: Path):
    """When ``prefer_full_registry=False`` and the manifest refuses all
    candidates, ``pick_next_target`` returns ``None`` for backwards-compat
    callers but raises when ``raise_on_empty=True``."""
    state = bl._default_state()
    manifest = _write_manifest(
        tmp_path / "manifest.json",
        {"kamino": {"slug": "kamino", "status": "missing"}},
    )
    scan = {
        "programs": [
            {"slug": "kamino", "ecosystem": "solana", "best_evidence_grade": 4,
             "submission_ready": True, "solana_reproduced": 2,
             "candidates_passed": 5, "max_bounty_usd": 1_500_000},
        ],
    }
    # 1) Without raise_on_empty: pick_next_target silently returns None.
    out = bl.pick_next_target(scan, state, manifest_path=manifest)
    assert out is None
    # 2) raise_on_empty escalates the empty-pool situation to a typed exception.
    with pytest.raises(PickRefused):
        bl.pick_next_target(
            scan, state,
            manifest_path=manifest,
            raise_on_empty=True,
        )


def test_pick_next_target_prefers_ready_over_harness_built(tmp_path: Path):
    """Highest-tier slug wins; alphabetical/tiebreak test of the picker."""
    state = bl._default_state()
    manifest = _write_manifest(
        tmp_path / "manifest.json",
        {
            "pendle": {"slug": "pendle", "status": "harness_built"},
            "uniswap_v4": {"slug": "uniswap_v4", "status": "ready"},
        },
    )
    scan = {
        "programs": [
            {"slug": "pendle", "ecosystem": "evm", "best_evidence_grade": 3,
             "submission_ready": False, "solana_reproduced": 0,
             "candidates_passed": 4, "max_bounty_usd": 2_000_000},
            {"slug": "uniswap_v4", "ecosystem": "evm", "best_evidence_grade": 0,
             "submission_ready": False, "solana_reproduced": 0,
             "candidates_passed": 0, "max_bounty_usd": 15_500_000},
        ],
    }
    target = bl.pick_next_target(
        scan, state, manifest_path=manifest, raise_on_empty=True, min_grade=0,
    )
    assert target is not None
    assert target["slug"] == "uniswap_v4"


def test_list_pickable_slugs_includes_curated_when_scope_missing(tmp_path: Path):
    out = list_pickable_slugs(
        curated=["a", "b"],
        scope_registry_path=tmp_path / "missing.json",
    )
    assert out == ["a", "b"]
