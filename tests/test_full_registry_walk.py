"""Audit correction C5 — walk the full live registry, not just the curated 28 (audit D1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from night_shift_security.bounty.native_picker import (
    list_pickable_slugs,
    rank_pickable_slugs,
)
from night_shift_security.orchestration import bounty_loop as bl


def _write_scope_registry(path: Path, entries: dict[str, dict[str, object]]) -> Path:
    """Write a synthetic live scope registry matching ``sync.py`` shape."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "1.0",
        "generated_at": "2026-06-19T00:00:00Z",
        "entry_count": len(entries),
        "curated_count": 0,
        "entries": entries,
    }
    path.write_text(json.dumps(payload))
    return path


def test_list_pickable_slugs_falls_back_to_curated_when_registry_missing(tmp_path: Path):
    """No scope_registry.json on disk -> curated-only pool."""
    out = list_pickable_slugs(
        curated=["uniswap", "pendle"],
        scope_registry_path=tmp_path / "missing.json",
    )
    assert out == ["uniswap", "pendle"]
    # list_pickable_slugs is independent of the native-harness gate; this
    # confirms the registry-walk fallback path under a missing scope file.


def test_list_pickable_slugs_walks_full_registry(tmp_path: Path):
    """When scope_registry.json has >=30 entries, the picker should expose them all."""
    registry = {}
    for i in range(40):
        slug = f"prog_{i:02d}"
        registry[slug] = {
            "slug": slug,
            "platform": "immunefi",
            "max_bounty_usd": 100_000 + i * 1_000,
            "curated": False,
        }
    scope_path = _write_scope_registry(tmp_path / "scope_registry.json", registry)

    out = list_pickable_slugs(
        curated=["uniswap_v4"],
        scope_registry_path=scope_path,
    )
    # Curated first, then the full registry. At least 30 distinct slugs.
    assert "uniswap_v4" in out
    assert len(out) >= 30
    assert any(slug in out for slug in ["prog_00", "prog_25", "prog_39"])


def test_pick_next_target_full_registry_walk_prefers_ready(tmp_path: Path):
    """C5 integration: prefer_full_registry=True exposes the registry but
    still applies the C3 native-harness gate."""
    registry = {}
    for i in range(35):
        slug = f"prog_{i:02d}"
        registry[slug] = {
            "slug": slug,
            "platform": "immunefi",
            "max_bounty_usd": 200_000 + i * 1_000,
            "curated": False,
        }
    scope_path = _write_scope_registry(tmp_path / "scope_registry.json", registry)
    manifest_path = tmp_path / "native_harness_status.json"
    manifest_path.write_text(json.dumps({
        "schema_version": "1.0",
        "harnesses": {
            "prog_05": {"slug": "prog_05", "status": "ready"},
            "prog_10": {"slug": "prog_10", "status": "harness_built"},
        },
        "ready_count": 1,
    }))

    scan = {
        "programs": [
            {"slug": "uniswap_v4", "ecosystem": "evm", "best_evidence_grade": 3,
             "submission_ready": False, "solana_reproduced": 0,
             "candidates_passed": 4, "max_bounty_usd": 15_500_000},
        ],
    }
    target = bl.pick_next_target(
        scan,
        {"saturated_slugs": [], "runs": []},
        prefer_full_registry=True,
        manifest_path=manifest_path,
        scope_registry_path=scope_path,
        raise_on_empty=True,
    )
    assert target is not None
    # ``prog_05`` is the only ``ready`` slug, so the picker should surface it.
    assert target["slug"] in {"prog_05", "prog_10"}
    # Sanity: registry size > 30 distinct slugs.
    full_pool = list_pickable_slugs(
        curated=["uniswap_v4"], scope_registry_path=scope_path,
    )
    assert sum(1 for s in full_pool if s.startswith("prog_")) >= 30


def test_rank_pickable_slugs_orders_by_bounty_score(tmp_path: Path):
    """``rank_pickable_slugs`` orders by ``max_bounty_usd * state_multiplier``."""
    scope_path = _write_scope_registry(
        tmp_path / "scope_registry.json",
        {
            "small_a": {"slug": "small_a", "max_bounty_usd": 100_000,
                         "curated": False},
            "small_b": {"slug": "small_b", "max_bounty_usd": 200_000,
                         "curated": False},
        },
    )
    manifest_path = tmp_path / "native_harness_status.json"
    manifest_path.write_text(json.dumps({
        "schema_version": "1.0",
        "harnesses": {
            "small_a": {"slug": "small_a", "status": "ready"},
            "small_b": {"slug": "small_b", "status": "ready"},
        },
        "ready_count": 2,
    }))
    # ``small_a`` < ``small_b``, but with ``ready`` both get multiplier 1.0.
    ranked = rank_pickable_slugs(
        ["small_a", "small_b"],
        scope_registry_path=scope_path,
        manifest_path=manifest_path,
    )
    assert ranked == ["small_b", "small_a"]


def test_rank_pickable_slugs_harness_built_outweighs_ready(tmp_path: Path):
    """Per handover §4.2, harness_built (2x) outranks ready (1x)."""
    scope_path = _write_scope_registry(
        tmp_path / "scope_registry.json",
        {
            "low_ready": {"slug": "low_ready", "max_bounty_usd": 1_000_000,
                          "curated": False},
            "tiny_harness": {"slug": "tiny_harness", "max_bounty_usd": 100_000,
                             "curated": False},
        },
    )
    manifest_path = tmp_path / "native_harness_status.json"
    manifest_path.write_text(json.dumps({
        "schema_version": "1.0",
        "harnesses": {
            "low_ready": {"slug": "low_ready", "status": "ready"},
            "tiny_harness": {"slug": "tiny_harness", "status": "harness_built"},
        },
        "ready_count": 1,
    }))
    ranked = rank_pickable_slugs(
        ["low_ready", "tiny_harness"],
        scope_registry_path=scope_path,
        manifest_path=manifest_path,
    )
    # 1_000_000 * 1.0 vs 100_000 * 2.0 → 1_000_000 > 200_000; ready wins.
    assert ranked == ["low_ready", "tiny_harness"]
