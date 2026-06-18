"""Tests for Phase 4 rotation rollout — saturation guard (Option B).

Covers:
- is_saturated_for_rotation logic
- Saturation guard in pick_next_target_v6_phase4
- Cold floats above saturated warm
- Saturated candidate re-enters after window
- Empty result when all candidates are saturated
- Cron YAML defaults Phase 4 off
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from night_shift_security.bounty.native_picker import (
    is_saturated_for_rotation,
    phase4_rotation_enabled,
    pick_next_target_v6_phase4,
    rotate_target,
    _days_since_last_touched,
)

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "data" / "security_results" / "loop" / "native_harness_status.json"
CRON_YAML = REPO / "hermes" / "cron" / "jobs.example.yaml"


def _make_state(*, last_touched: dict[str, str] | None = None) -> dict:
    return {"saturated_slugs": [], "runs": [], "last_touched": last_touched or {}}


def _make_scan_report(slugs: list[str]) -> dict:
    return {"targets": [{"slug": s} for s in slugs]}


def test_saturated_for_rotation_returns_true_within_window() -> None:
    """Candidate touched 3 days ago is saturated (within 14-day window)."""
    now = datetime(2026, 6, 19, tzinfo=timezone.utc)
    touched = (now - timedelta(days=3)).isoformat()
    state = _make_state(last_touched={"morpho_blue": touched})
    assert is_saturated_for_rotation("morpho_blue", state, now=now, window_days=14) is True


def test_saturated_for_rotation_returns_false_outside_window() -> None:
    """Candidate touched 20 days ago is NOT saturated (outside window)."""
    now = datetime(2026, 6, 19, tzinfo=timezone.utc)
    touched = (now - timedelta(days=20)).isoformat()
    state = _make_state(last_touched={"morpho_blue": touched})
    assert is_saturated_for_rotation("morpho_blue", state, now=now, window_days=14) is False


def test_saturated_for_rotation_never_touched_is_false() -> None:
    """Never-touched candidate is NOT saturated."""
    state = _make_state()
    assert is_saturated_for_rotation("morpho_blue", state) is False


def test_saturated_for_rotation_empty_state() -> None:
    """Empty state dict returns False."""
    assert is_saturated_for_rotation("morpho_blue", {}) is False
    assert is_saturated_for_rotation("morpho_blue", None) is False


def test_cold_floats_above_saturated_warm() -> None:
    """Cold non-saturated candidate is preferred over warm saturated."""
    now = datetime(2026, 6, 19, tzinfo=timezone.utc)
    warm_touched = (now - timedelta(days=3)).isoformat()
    state = _make_state(last_touched={"morpho_blue": warm_touched})
    scan = _make_scan_report(["morpho_blue", "uniswap_v4"])
    result = pick_next_target_v6_phase4(
        scan, state, manifest_path=MANIFEST, now=now,
    )
    # morpho_blue is saturated (harness_built, touched 3 days ago)
    # uniswap_v4 is ready and never touched -> should be picked
    assert result is not None
    assert result["slug"] == "uniswap_v4"


def test_saturated_candidate_re_enters_after_window() -> None:
    """Candidate touched 20 days ago re-enters (outside window)."""
    now = datetime(2026, 6, 19, tzinfo=timezone.utc)
    touched = (now - timedelta(days=20)).isoformat()
    state = _make_state(last_touched={"morpho_blue": touched})
    # morpho_blue should NOT be saturated (outside window)
    assert is_saturated_for_rotation("morpho_blue", state, now=now, window_days=14) is False


def test_empty_returns_none_when_all_saturated() -> None:
    """When all candidates are saturated, result is None."""
    now = datetime(2026, 6, 19, tzinfo=timezone.utc)
    warm_touched = (now - timedelta(days=3)).isoformat()
    state = _make_state(last_touched={
        "morpho_blue": warm_touched,
        "aave_v3": warm_touched,
        "uniswap_v4": warm_touched,
    })
    scan = _make_scan_report(["morpho_blue", "aave_v3", "uniswap_v4"])
    result = pick_next_target_v6_phase4(
        scan, state, manifest_path=MANIFEST, now=now,
    )
    # All three are harness_built/ready and touched within window
    # Only ready candidates are NOT filtered by saturation guard
    # (the guard applies to all candidates via is_saturated_for_rotation)
    # Since all are touched within window, all are saturated -> None
    assert result is None


def test_cron_yaml_defaults_phase4_off() -> None:
    """Cron YAML does NOT include NSS_PHASE4_ROTATION_ENABLED=1."""
    yaml_text = CRON_YAML.read_text()
    assert "NSS_PHASE4_ROTATION_ENABLED=1" not in yaml_text, (
        "Phase 4 rotation should be off by default in cron YAML"
    )


def test_cron_yaml_nss_env_not_present() -> None:
    """Cron YAML nss-hipif-chain job has no NSS_PHASE4_ROTATION_ENABLED env."""
    yaml_text = CRON_YAML.read_text()
    # The nss-hipif-chain job section should not have the phase4 flag
    # Look between the nss-hipif-chain job definition and the next job
    lines = yaml_text.split("\n")
    in_chain_job = False
    for line in lines:
        if "nss-hipif-chain" in line and "name:" in line:
            in_chain_job = True
        elif in_chain_job and line.strip().startswith("- name:"):
            break
        elif in_chain_job and "NSS_PHASE4_ROTATION_ENABLED" in line:
            pytest.fail("NSS_PHASE4_ROTATION_ENABLED found in nss-hipif-chain job")
