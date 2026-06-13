"""Tests for git patch shape miner."""

import subprocess
from pathlib import Path

from night_shift_security.triage.git_patches import (
    extract_patch_shapes,
    list_security_commits,
    mine_patch_shapes,
)


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=path,
        check=True,
        capture_output=True,
    )


def test_extract_patch_shapes_detects_auth_guard():
    diff = """
+++ b/contracts/Vault.sol
+    function withdraw() external onlyOwner {
+        require(balance > 0);
"""
    shapes = extract_patch_shapes(diff)
    assert "added_auth_guard" in shapes


def test_mine_patch_shapes_from_repo(tmp_path: Path):
    _init_repo(tmp_path)
    vault = tmp_path / "Vault.sol"
    vault.write_text("contract V {}\n")
    subprocess.run(["git", "add", "Vault.sol"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True)

    vault.write_text("contract V { function w() onlyOwner {} }\n")
    subprocess.run(["git", "add", "Vault.sol"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "security: add onlyOwner guard"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    commits = list_security_commits(tmp_path, max_commits=10)
    assert len(commits) >= 1
    shapes = mine_patch_shapes(tmp_path, max_commits=10)
    assert any("added_auth_guard" in s.shapes for s in shapes)