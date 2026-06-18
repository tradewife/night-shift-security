"""Tests for Phase 4 rotation — cold-program float, opt-in flag, last_touched tracking."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from night_shift_security.bounty.native_picker import (
    phase4_rotation_enabled,
    pick_next_target_v6_phase4,
    rotate_target,
    _days_since_last_touched,
)

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "data" / "security_results" / "loop" / "native_harness_status.json"


def _make_state(
    *,
    last_touched: dict[str, str] | None = None,
    saturated_slugs: list[str] | None = None,
) -> dict:
    return {
        "saturated_slugs": saturated_slugs or [],
        "runs": [],
        "last_touched": last_touched or {},
    }


def _make_scan_report(slugs: list[str] | None = None) -> dict:
    if slugs is None:
        slugs = ["uniswap_v4", "morpho_blue"]
    return {"targets": [{"slug": s, "platform": "cantina"} for s in slugs]}


# ------------------------------------------------------------------ #
# phase4_rotation_enabled
# ------------------------------------------------------------------ #


def test_phase4_disabled_by_default():
    """Phase 4 rotation is off when the env var is not set."""
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("NSS_PHASE4_ROTATION_ENABLED", None)
        assert phase4_rotation_enabled() is False


def test_phase4_enabled_with_true():
    with patch.dict(os.environ, {"NSS_PHASE4_ROTATION_ENABLED": "true"}):
        assert phase4_rotation_enabled() is True


def test_phase4_enabled_with_1():
    with patch.dict(os.environ, {"NSS_PHASE4_ROTATION_ENABLED": "1"}):
        assert phase4_rotation_enabled() is True


def test_phase4_disabled_with_garbage():
    with patch.dict(os.environ, {"NSS_PHASE4_ROTATION_ENABLED": "nope"}):
        assert phase4_rotation_enabled() is False


# ------------------------------------------------------------------ #
# rotate_target + _days_since_last_touched
# ------------------------------------------------------------------ #


def test_rotate_target_populates_last_touched():
    state: dict = {}
    rotate_target(state, "morpho_blue")
    assert "last_touched" in state
    assert "morpho_blue" in state["last_touched"]
    # Must be a valid ISO timestamp
    datetime.fromisoformat(state["last_touched"]["morpho_blue"])


def test_rotate_target_with_explicit_now():
    state: dict = {}
    now = datetime(2026, 6, 19, 12, 0, 0, tzinfo=timezone.utc)
    rotate_target(state, "morpho_blue", now=now)
    assert state["last_touched"]["morpho_blue"] == "2026-06-19T12:00:00+00:00"


def test_days_since_never_touched_is_large():
    assert _days_since_last_touched("morpho_blue", {}) == 9999.0


def test_days_since_recently_touched_is_small():
    now = datetime(2026, 6, 19, 12, 0, 0, tzinfo=timezone.utc)
    touched = (now - timedelta(hours=1)).isoformat()
    state = {"last_touched": {"morpho_blue": touched}}
    days = _days_since_last_touched("morpho_blue", state, now=now)
    assert 0.0 <= days <= 0.1


# ------------------------------------------------------------------ #
# pick_next_target_v6_phase4 — cold floats above warm
# ------------------------------------------------------------------ #


def test_cold_program_floats_above_warm():
    """Two slugs with equal bounty and equal status multiplier; A was never
    touched, B was touched yesterday. A must be returned first because it
    is colder."""
    now = datetime(2026, 6, 19, 12, 0, 0, tzinfo=timezone.utc)
    state = _make_state(
        last_touched={
            "morpho_blue": (now - timedelta(days=1)).isoformat(),
        }
    )
    scan = _make_scan_report(["uniswap_v4", "morpho_blue"])
    # Mock _scope_max_bounty so both have equal non-zero bounty, and mock
    # native_status_of so both have the same status (equal multiplier).
    # Also mock list_pickable_slugs to avoid scope registry leakage.
    from night_shift_security.bounty.native_picker import NativePickerEntry

    def _fake_status(slug, manifest_path=None):
        return NativePickerEntry(
            slug=slug, status="ready",
        )

    with (
        patch(
            "night_shift_security.bounty.native_picker._scope_max_bounty",
            return_value=15500000,
        ),
        patch(
            "night_shift_security.bounty.native_picker.native_status_of",
            side_effect=_fake_status,
        ),
        patch(
            "night_shift_security.bounty.native_picker.list_pickable_slugs",
            return_value=["uniswap_v4", "morpho_blue"],
        ),
    ):
        result = pick_next_target_v6_phase4(
            scan,
            state,
            now=now,
            manifest_path=MANIFEST,
        )
    assert result is not None
    assert result["slug"] == "uniswap_v4"


def test_rotation_returns_none_on_empty():
    """Empty scan report returns None."""
    state = _make_state()
    scan = {"targets": []}
    result = pick_next_target_v6_phase4(scan, state, manifest_path=MANIFEST)
    assert result is None


def test_rotation_records_last_touched_on_success():
    """When a pick succeeds, the slug is recorded in state['last_touched']."""
    now = datetime(2026, 6, 19, 12, 0, 0, tzinfo=timezone.utc)
    state = _make_state()
    scan = _make_scan_report(["uniswap_v4"])
    result = pick_next_target_v6_phase4(scan, state, now=now, manifest_path=MANIFEST)
    assert result is not None
    # Manually rotate (the wrapper in bounty_loop does this)
    rotate_target(state, result["slug"], now=now)
    assert "uniswap_v4" in state["last_touched"]
    assert state["last_touched"]["uniswap_v4"] == now.isoformat()
