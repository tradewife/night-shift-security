"""Tests for the cron registry flip — prefer_full_registry=True wired at the runner."""

from __future__ import annotations

import os
import sys
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO = Path(__file__).resolve().parents[1]


def test_chain_run_importable():
    """The chain run module is importable."""
    # Just verify the script can be parsed as Python
    script = REPO / "hermes/scripts/nss-hipif-chain-run.py"
    assert script.is_file()
    result = subprocess.run(
        [sys.executable, "-c", f"import ast; ast.parse(open('{script}').read())"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Script has syntax errors: {result.stderr}"


def test_run_loop_iteration_reads_prefer_full_registry_env():
    """run_loop_iteration reads NSS_PREFER_FULL_REGISTRY and passes to pick_next_target."""
    from night_shift_security.orchestration.bounty_loop import run_loop_iteration

    state = {"saturated_slugs": [], "runs": []}

    with (
        patch(
            "night_shift_security.orchestration.bounty_loop.pick_next_target",
            return_value=None,
        ) as mock_pick,
        patch(
            "night_shift_security.orchestration.bounty_loop.load_loop_state",
            return_value=state,
        ),
        patch(
            "night_shift_security.orchestration.bounty_loop.save_loop_state",
        ),
    ):
        os.environ["NSS_PREFER_FULL_REGISTRY"] = "1"
        try:
            run_loop_iteration(
                state_path=MagicMock(),
                scan_path=MagicMock(is_file=MagicMock(return_value=False)),
                refresh_scan=True,
            )
            mock_pick.assert_called_once()
            call_kwargs = mock_pick.call_args[1]
            assert call_kwargs.get("prefer_full_registry") is True
        finally:
            os.environ.pop("NSS_PREFER_FULL_REGISTRY", None)


def test_run_loop_iteration_default_no_full_registry():
    """When NSS_PREFER_FULL_REGISTRY is not set, prefer_full_registry defaults to False."""
    from night_shift_security.orchestration.bounty_loop import run_loop_iteration

    state = {"saturated_slugs": [], "runs": []}

    with (
        patch(
            "night_shift_security.orchestration.bounty_loop.pick_next_target",
            return_value=None,
        ) as mock_pick,
        patch(
            "night_shift_security.orchestration.bounty_loop.load_loop_state",
            return_value=state,
        ),
        patch(
            "night_shift_security.orchestration.bounty_loop.save_loop_state",
        ),
    ):
        os.environ.pop("NSS_PREFER_FULL_REGISTRY", None)
        run_loop_iteration(
            state_path=MagicMock(),
            scan_path=MagicMock(is_file=MagicMock(return_value=False)),
            refresh_scan=True,
        )
        mock_pick.assert_called_once()
        call_kwargs = mock_pick.call_args[1]
        assert call_kwargs.get("prefer_full_registry") is False
