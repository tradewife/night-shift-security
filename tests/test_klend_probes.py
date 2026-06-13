"""Tests for KLend depth probes."""

import os
import subprocess
import sys
from pathlib import Path

import sys

_SOLANA_ROOT = Path(__file__).resolve().parents[1] / "solana"
if str(_SOLANA_ROOT) not in sys.path:
    sys.path.insert(0, str(_SOLANA_ROOT))

import klend_probes as kp  # noqa: E402


def test_klend_probes_matrix():
    probes = kp.list_probes()  # type: ignore[attr-defined]
    assert len(probes) >= 4
    ids = {p["probe_id"] for p in probes}
    assert "oracle_staleness_borrow" in ids


def test_klend_probe_account_matrix():
    oracle = kp.probe_account_specs("oracle_staleness_borrow")
    flash = kp.probe_account_specs("flash_loan_collateral_loop")
    assert len(oracle) == 4
    assert len(flash) == 5
    assert any(s.role == "spl_token" for s in flash)
    assert kp.probe_accounts_summary("reserve_isolation_drain").startswith("lending_market_program:")


def test_klend_harness_depth_mode():
    env = {
        **os.environ,
        "NSS_KLEND_FIXTURE": "1",
        "NSS_KLEND_DEPTH": "1",
    }
    proc = subprocess.run(
        [sys.executable, str(_SOLANA_ROOT / "run_klend_harness.py")],
        cwd=_SOLANA_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0
    assert "DEPTH_PROBE_COUNT:4" in proc.stdout
    assert "PROBE_RESULT:oracle_staleness_borrow:pass" in proc.stdout


def test_klend_harness_single_probe():
    env = {
        **os.environ,
        "NSS_KLEND_FIXTURE": "1",
        "KLEND_PROBE": "flash_loan_collateral_loop",
    }
    proc = subprocess.run(
        [sys.executable, str(_SOLANA_ROOT / "run_klend_harness.py")],
        cwd=_SOLANA_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0
    assert "PROBE:flash_loan_collateral_loop" in proc.stdout
    assert "INVARIANT:flash_loan_atomicity" in proc.stdout