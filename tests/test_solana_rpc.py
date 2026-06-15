"""Tests for Solana tool discovery in cron-like environments."""

from __future__ import annotations

from pathlib import Path

from night_shift_security.validation import solana_rpc


def test_find_solana_test_validator_uses_env_bin(tmp_path: Path, monkeypatch):
    validator = tmp_path / "solana-test-validator"
    validator.write_text("#!/bin/sh\n")
    validator.chmod(0o755)

    monkeypatch.setenv("SOLANA_VALIDATOR_BIN", str(validator))
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))

    assert solana_rpc.find_solana_test_validator() == str(validator)
    assert solana_rpc.solana_validator_available() is True


def test_find_solana_test_validator_uses_active_release_when_path_is_stripped(
    tmp_path: Path,
    monkeypatch,
):
    home = tmp_path / "home"
    validator = home / ".local/share/solana/install/active_release/bin/solana-test-validator"
    validator.parent.mkdir(parents=True)
    validator.write_text("#!/bin/sh\n")
    validator.chmod(0o755)

    monkeypatch.delenv("SOLANA_VALIDATOR_BIN", raising=False)
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    monkeypatch.setattr(solana_rpc.Path, "home", lambda: home)

    assert solana_rpc.find_solana_test_validator() == str(validator)
    assert solana_rpc.solana_status()["validator_bin"] == str(validator)
