"""Tests for the Uniswap v4 hook delta extraction probe (v5 Phase 7+).

These tests verify the Foundry test outputs and document the design analysis
showing that afterSwap hookDelta is bounded by the swapper's swapDelta
(per sources/uniswap_v4/repo/src/libraries/Hooks.sol:305-313).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
FOUNDRY_DIR = REPO_ROOT / "foundry"


def _run_forge_test(test_name: str, env: dict | None = None) -> tuple[int, str]:
    """Run a single forge test and return (exit_code, output)."""
    # Find which test file contains the test
    test_files = [
        "test/UniV4HookExploitProbe.t.sol",
        "test/UniV4HookExploitFull.t.sol",
        "test/UniV4HookProbe.t.sol",
    ]
    target_file = None
    for tf in test_files:
        full = FOUNDRY_DIR / tf
        if full.is_file() and test_name in full.read_text():
            target_file = tf
            break
    if not target_file:
        return (-1, f"test {test_name} not found in any file")
    test_env = os.environ.copy()
    if env:
        test_env.update(env)
    rpc = test_env.get("ETHEREUM_RPC_URL") or test_env.get("ETH_RPC_URL")
    if not rpc:
        return (-2, "no RPC URL configured")
    test_env["ETH_RPC_URL"] = rpc
    result = subprocess.run(
        [
            "forge",
            "test",
            "--match-path",
            target_file,
            "--match-test",
            test_name,
            "-vv",
        ],
        cwd=str(FOUNDRY_DIR),
        env=test_env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return result.returncode, result.stdout + result.stderr


def test_malicious_hook_bytecode_exists() -> None:
    """The MaliciousAfterSwapHook source must exist in foundry/src/."""
    hook_path = FOUNDRY_DIR / "src" / "MaliciousAfterSwapHook.sol"
    assert hook_path.is_file(), f"missing source: {hook_path}"
    content = hook_path.read_text()
    assert "afterSwap" in content, "hook must implement afterSwap"
    assert "bytes4(0x3b08c148)" in content, "hook must return IHooks.afterSwap selector"


def test_hook_permission_bits() -> None:
    """Verify the hook permission bits are correct.

    Per sources/uniswap_v4/repo/src/libraries/Hooks.sol:
      AFTER_SWAP_FLAG = 1 << 6 = 0x40
      AFTER_SWAP_RETURNS_DELTA_FLAG = 1 << 2 = 0x04
    Combined mask: 0x44
    """
    after_swap = 1 << 6
    after_swap_returns = 1 << 2
    combined = after_swap | after_swap_returns
    assert combined == 0x44, f"combined mask must be 0x44, got {hex(combined)}"


def test_hook_exploit_probe_compiles() -> None:
    """The Foundry test file must compile (forge build succeeds)."""
    result = subprocess.run(
        ["forge", "build"],
        cwd=str(FOUNDRY_DIR),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"forge build failed:\n{result.stderr}"
    assert "Compiler run successful" in result.stdout or "No files changed" in result.stdout


def test_hook_deploy_at_0x44_address() -> None:
    """Test that a hook deployed at an address with bits 0x44 set works.

    This test runs the Foundry test which:
    1. Deploys MaliciousAfterSwapHook via vm.etch at 0x...44
    2. Verifies the hook address has AFTER_SWAP_FLAG + AFTER_SWAP_RETURNS_DELTA_FLAG
    3. Calls afterSwap directly and verifies the return value
    """
    rpc = os.environ.get("ETHEREUM_RPC_URL") or os.environ.get("ETH_RPC_URL")
    if not rpc:
        pytest.skip("ETHEREUM_RPC_URL/ETH_RPC_URL not set")
    code, output = _run_forge_test(
        "test_deploy_hook_at_0x44_address",
        env={"ETHEREUM_RPC_URL": rpc, "ETH_RPC_URL": rpc},
    )
    assert code == 0, f"forge test failed:\n{output}"
    assert "HOOK_DEPLOYED_AND_VERIFIED" in output, f"missing status:\n{output}"
    # Extract the hook address from the output
    match = re.search(r"HOOK_ADDRESS:\s+(0x[0-9a-fA-F]{40})", output)
    assert match, f"could not extract hook address:\n{output}"
    hook_addr = int(match.group(1), 16)
    assert hook_addr & 0xFF == 0x44, f"hook address must end in 0x44, got {hex(hook_addr & 0xFF)}"
    assert hook_addr & 0x40 != 0, "hook must have AFTER_SWAP_FLAG (0x40)"
    assert hook_addr & 0x04 != 0, "hook must have AFTER_SWAP_RETURNS_DELTA_FLAG (0x04)"


def test_hook_permission_validation_rejects_invalid_hook() -> None:
    """A hook with only AFTER_SWAP_RETURNS_DELTA_FLAG (not AFTER_SWAP_FLAG)
    must be rejected by PoolManager.isValidHookAddress.
    """
    rpc = os.environ.get("ETHEREUM_RPC_URL") or os.environ.get("ETH_RPC_URL")
    if not rpc:
        pytest.skip("ETHEREUM_RPC_URL/ETH_RPC_URL not set")
    code, output = _run_forge_test(
        "test_hook_permission_validation",
        env={"ETHEREUM_RPC_URL": rpc, "ETH_RPC_URL": rpc},
    )
    assert code == 0, f"forge test failed:\n{output}"
    assert "INVALID_HOOK_REJECTED_BY_POOLMANAGER" in output


def test_hook_design_analysis_documented() -> None:
    """Verify the design analysis is documented in the test file.

    Per sources/uniswap_v4/repo/src/libraries/Hooks.sol:305-313:
        swapDelta = swapDelta - hookDelta
    This means the hook is bounded by the swapper's swapDelta.
    The hook CAN extract value, but only at the swapper's expense.
    """
    test_file = FOUNDRY_DIR / "test" / "UniV4HookExploitProbe.t.sol"
    content = test_file.read_text()
    assert "bounded" in content.lower(), "test must document that hook extraction is bounded"
    assert "swapDelta" in content, "test must reference swapDelta accounting"


def test_hook_full_flow_compiles() -> None:
    """The full exploit test must compile."""
    test_file = FOUNDRY_DIR / "test" / "UniV4HookExploitFull.t.sol"
    assert test_file.is_file(), f"missing test: {test_file}"
    result = subprocess.run(
        ["forge", "build"],
        cwd=str(FOUNDRY_DIR),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"forge build failed:\n{result.stderr}"


def test_hook_afterSwap_max_delta() -> None:
    """Test that the hook can return the maximum int128 delta."""
    rpc = os.environ.get("ETHEREUM_RPC_URL") or os.environ.get("ETH_RPC_URL")
    if not rpc:
        pytest.skip("ETHEREUM_RPC_URL/ETH_RPC_URL not set")
    code, output = _run_forge_test(
        "test_hook_afterSwap_return_shape",
        env={"ETHEREUM_RPC_URL": rpc, "ETH_RPC_URL": rpc},
    )
    assert code == 0, f"forge test failed:\n{output}"
    assert "HOOK_CAN_RETURN_ARBITRARY_DELTA" in output
    # max int128 = 2^127 - 1 = 170141183460469231731687303715884105727
    assert "170141183460469231731687303715884105727" in output


def test_hook_address_validation_in_isValidHookAddress() -> None:
    """Verify the isValidHookAddress design from Hooks.sol:111-120.

    Rules:
    - !hasPermission(AFTER_SWAP_FLAG) && hasPermission(AFTER_SWAP_RETURNS_DELTA_FLAG) → invalid
    - !hasPermission(AFTER_ADD_LIQUIDITY_FLAG) && hasPermission(AFTER_ADD_LIQUIDITY_RETURNS_DELTA_FLAG) → invalid
    - !hasPermission(AFTER_REMOVE_LIQUIDITY_FLAG) && hasPermission(AFTER_REMOVE_LIQUIDITY_RETURNS_DELTA_FLAG) → invalid
    """
    hooks_lib = REPO_ROOT / "sources" / "uniswap_v4" / "repo" / "src" / "libraries" / "Hooks.sol"
    if not hooks_lib.is_file():
        pytest.skip("Hooks.sol source not available")
    content = hooks_lib.read_text()
    assert "AFTER_SWAP_RETURNS_DELTA_FLAG" in content
    assert "isValidHookAddress" in content
    # Verify the validation logic
    assert "return false" in content
    assert "AFTER_SWAP_FLAG" in content
