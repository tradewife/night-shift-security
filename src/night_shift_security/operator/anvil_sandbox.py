"""Docker Anvil sandbox lifecycle for destructive fork replay."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Any

from night_shift_security.operator.foundry_tools import ToolResult

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SANDBOX_DIR = _REPO_ROOT / "docker" / "anvil-sandbox"


def sandbox_compose_path() -> Path:
    return _SANDBOX_DIR / "compose.yaml"


def start_docker_sandbox(
    *,
    fork_url: str | None = None,
    fork_block: int | None = None,
    attacker: str | None = None,
    attacker_balance_eth: int = 1_000_000,
    port: int = 8545,
) -> ToolResult:
    """Start Docker Compose Anvil sandbox."""
    compose = shutil_which("docker")
    if not compose:
        return ToolResult(
            success=False,
            command=[],
            stdout="",
            stderr="docker not found on PATH",
            exit_code=127,
            parsed={},
        )

    rpc = fork_url or os.environ.get("ETHEREUM_RPC_URL") or os.environ.get("FOUNDRY_FORK_URL", "")
    if not rpc:
        return ToolResult(
            success=False,
            command=[],
            stdout="",
            stderr="ETHEREUM_RPC_URL required for docker sandbox",
            exit_code=2,
            parsed={},
        )

    env = {
        **os.environ,
        "ETHEREUM_RPC_URL": rpc,
        "FORK_BLOCK": str(fork_block or os.environ.get("FORK_BLOCK", "16825925")),
        "OPERATOR_ATTACKER": attacker
        or os.environ.get("OPERATOR_ATTACKER", "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"),
        "ATTACKER_BALANCE_ETH": str(attacker_balance_eth),
        "ANVIL_PORT": str(port),
    }
    cmd = ["docker", "compose", "-f", str(sandbox_compose_path()), "up", "-d", "--remove-orphans"]
    proc = subprocess.run(cmd, cwd=_SANDBOX_DIR, env=env, capture_output=True, text=True, timeout=120)
    time.sleep(3)
    return ToolResult(
        success=proc.returncode == 0,
        command=cmd,
        stdout=proc.stdout,
        stderr=proc.stderr,
        exit_code=proc.returncode,
        parsed={
            "rpc_url": f"http://127.0.0.1:{port}",
            "fork_block": int(env["FORK_BLOCK"]),
            "attacker": env["OPERATOR_ATTACKER"],
            "mode": "docker",
        },
    )


def stop_docker_sandbox() -> ToolResult:
    compose = shutil_which("docker")
    if not compose:
        return ToolResult(
            success=False,
            command=[],
            stdout="",
            stderr="docker not found",
            exit_code=127,
            parsed={},
        )
    cmd = ["docker", "compose", "-f", str(sandbox_compose_path()), "down"]
    proc = subprocess.run(cmd, cwd=_SANDBOX_DIR, capture_output=True, text=True, timeout=60)
    return ToolResult(
        success=proc.returncode == 0,
        command=cmd,
        stdout=proc.stdout,
        stderr=proc.stderr,
        exit_code=proc.returncode,
        parsed={},
    )


def sandbox_status() -> dict[str, Any]:
    cmd = ["docker", "compose", "-f", str(sandbox_compose_path()), "ps", "--format", "json"]
    if not shutil_which("docker"):
        return {"running": False, "error": "docker not found"}
    proc = subprocess.run(cmd, cwd=_SANDBOX_DIR, capture_output=True, text=True, timeout=30)
    return {
        "running": proc.returncode == 0 and bool(proc.stdout.strip()),
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
        "compose": str(sandbox_compose_path()),
    }


def shutil_which(name: str) -> str | None:
    import shutil

    return shutil.which(name)