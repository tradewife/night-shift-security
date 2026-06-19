"""Tests for the Orca Whirlpools protocol fee wrapping_add analysis.

Per sources/orca/repo/programs/whirlpool/src/manager/swap_manager.rs:284:
    next_protocol_fee = next_protocol_fee.wrapping_add(delta);

This is an integer overflow vulnerability in the protocol fee accounting.
However, it's practically infeasible to trigger on mainnet because:
1. Requires ~1.8e19 lamports of accumulated protocol fees
2. Even for high-volume pools, this would take millions of years
3. The vault balance is NOT affected — only the accounting overflows
4. No user or LP loses funds

STATUS: rejected_theoretical
REASON: wrapping_add is a design choice for protocol fee accounting.
        Overflow requires ~u64::MAX / min_delta swaps, which is infeasible.
        The vault still holds the full token balance.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
FOUNDRY_DIR = REPO_ROOT / "foundry"


def test_wrapping_test_compiles() -> None:
    """The Orca wrapping test must compile."""
    result = subprocess.run(
        ["forge", "build"],
        cwd=str(FOUNDRY_DIR),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"forge build failed:\n{result.stderr}"


def test_wrapping_add_behavior() -> None:
    """Verify wrapping_add wraps around as expected."""
    result = subprocess.run(
        [
            "forge",
            "test",
            "--match-path",
            "test/OrcaProtocolFeeWrapping.t.sol",
            "--match-test",
            "test_wrapping_add_behavior",
            "-v",
        ],
        cwd=str(FOUNDRY_DIR),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"forge test failed:\n{result.stdout}\n{result.stderr}"


def test_practical_infeasibility() -> None:
    """Verify that overflow requires ~1.8e19 swaps (infeasible)."""
    result = subprocess.run(
        [
            "forge",
            "test",
            "--match-path",
            "test/OrcaProtocolFeeWrapping.t.sol",
            "--match-test",
            "test_practical_infeasibility",
            "-v",
        ],
        cwd=str(FOUNDRY_DIR),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"forge test failed:\n{result.stdout}\n{result.stderr}"


def test_vault_not_affected() -> None:
    """Verify the vault balance is NOT affected by the overflow."""
    result = subprocess.run(
        [
            "forge",
            "test",
            "--match-path",
            "test/OrcaProtocolFeeWrapping.t.sol",
            "--match-test",
            "test_vault_not_affected",
            "-v",
        ],
        cwd=str(FOUNDRY_DIR),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"forge test failed:\n{result.stdout}\n{result.stderr}"


def test_design_analysis() -> None:
    """Verify the design analysis test passes."""
    result = subprocess.run(
        [
            "forge",
            "test",
            "--match-path",
            "test/OrcaProtocolFeeWrapping.t.sol",
            "--match-test",
            "test_design_analysis",
            "-v",
        ],
        cwd=str(FOUNDRY_DIR),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"forge test failed:\n{result.stdout}\n{result.stderr}"


def test_wrapping_add_in_source() -> None:
    """Verify the wrapping_add is in the Orca source code.

    Per sources/orca/repo/programs/whirlpool/src/manager/swap_manager.rs:284:
        next_protocol_fee = next_protocol_fee.wrapping_add(delta);
    """
    swap_manager = (
        REPO_ROOT
        / "sources"
        / "orca"
        / "repo"
        / "programs"
        / "whirlpool"
        / "src"
        / "manager"
        / "swap_manager.rs"
    )
    if not swap_manager.is_file():
        pytest.skip("swap_manager.rs source not available")
    content = swap_manager.read_text()
    assert "wrapping_add" in content, "wrapping_add must be in swap_manager.rs"
    assert "next_protocol_fee" in content, "next_protocol_fee must be referenced"


def test_collect_protocol_fees_clears_owed() -> None:
    """Verify collect_protocol_fees clears the owed amount after collection.

    Per sources/orca/repo/programs/whirlpool/src/instructions/collect_protocol_fees.rs:
        ctx.accounts.whirlpool.reset_protocol_fees_owed();
    This sets protocol_fee_owed_a and protocol_fee_owed_b to 0.
    """
    collect_fees = (
        REPO_ROOT
        / "sources"
        / "orca"
        / "repo"
        / "programs"
        / "whirlpool"
        / "src"
        / "instructions"
        / "collect_protocol_fees.rs"
    )
    if not collect_fees.is_file():
        pytest.skip("collect_protocol_fees.rs source not available")
    content = collect_fees.read_text()
    assert "reset_protocol_fees_owed" in content


def test_whirlpool_state_has_protocol_fee_owed() -> None:
    """Verify the Whirlpool state has protocol_fee_owed_a and protocol_fee_owed_b."""
    whirlpool = (
        REPO_ROOT
        / "sources"
        / "orca"
        / "repo"
        / "programs"
        / "whirlpool"
        / "src"
        / "state"
        / "whirlpool.rs"
    )
    if not whirlpool.is_file():
        pytest.skip("whirlpool.rs source not available")
    content = whirlpool.read_text()
    assert "protocol_fee_owed_a" in content
    assert "protocol_fee_owed_b" in content
    # Verify the wrapping behavior
    assert "wrapping_add" in content or "self.protocol_fee_owed_a +=" in content
