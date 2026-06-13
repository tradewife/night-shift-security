"""Tests for KLend validator harness."""

import os
import subprocess
import sys
from pathlib import Path

import importlib.util

from night_shift_security.data.solana_targets import get_solana_targets

_SOLANA_ROOT = Path(__file__).resolve().parents[1] / "solana"


def _load_validator_profiles():
    spec = importlib.util.spec_from_file_location(
        "validator_profiles",
        _SOLANA_ROOT / "validator_profiles.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_klend_validator_profile_exists():
    vp = _load_validator_profiles()
    profile = vp.get_validator_profile("kamino-klend")
    assert profile is not None
    assert "KLend2g3cP87fffoy8q1mQqGKjrxjC8boSyAYavgmjD" in profile.clone_accounts


def test_klend_solana_target_registered():
    kamino = next(t for t in get_solana_targets() if t.exploit_id == "kamino-klend")
    assert kamino.validator_backed is True
    assert kamino.template_id == "flash_loan_oracle"


def test_klend_harness_fixture_mode():
    env = {**os.environ, "NSS_KLEND_FIXTURE": "1"}
    proc = subprocess.run(
        [sys.executable, str(_SOLANA_ROOT / "run_klend_harness.py")],
        cwd=_SOLANA_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0
    assert "HARNESS_MODE:fixture" in proc.stdout
    assert "SOLANA_VALIDATOR_PASS:1" in proc.stdout
    assert "DELTA_LAMPORTS:" in proc.stdout