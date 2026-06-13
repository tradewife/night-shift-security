"""Foundry tool adapters for operator MCP and CLI."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_FOUNDRY_ROOT = _REPO_ROOT / "foundry"
_ANVIL_PID_FILE = _REPO_ROOT / "data/security_results/operator/anvil.pid"
_ANVIL_RPC_DEFAULT = "http://127.0.0.1:8545"


@dataclass
class ToolResult:
    success: bool
    command: list[str]
    stdout: str
    stderr: str
    exit_code: int
    parsed: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _which_or_raise(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise FileNotFoundError(f"{name} not found on PATH")
    return path


def run_forge_test(
    *,
    match_test: str,
    foundry_root: Path | None = None,
    fork_url: str | None = None,
    fork_block: int | None = None,
    extra_env: dict[str, str] | None = None,
    timeout_s: int = 180,
) -> ToolResult:
    """Run `forge test --match-test` against the NSS harness or custom root."""
    forge = _which_or_raise("forge")
    root = foundry_root or _DEFAULT_FOUNDRY_ROOT
    env = {**os.environ, **(extra_env or {})}
    rpc = fork_url or env.get("FOUNDRY_FORK_URL") or env.get("ETHEREUM_RPC_URL", "")
    if rpc:
        env["FOUNDRY_FORK_URL"] = rpc
        env["ETHEREUM_RPC_URL"] = rpc
    if fork_block is not None:
        env["FORK_BLOCK_NUMBER"] = str(fork_block)

    cmd = [forge, "test", "--match-test", match_test, "-vv", "--json"]
    proc = subprocess.run(
        cmd,
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )
    output = proc.stdout + proc.stderr
    parsed: dict[str, Any] = {
        "impact_usd": 0.0,
        "balance_delta_wei": None,
    }
    impact_match = re.search(r"IMPACT_USD:(\d+(?:\.\d+)?)", output)
    if impact_match:
        parsed["impact_usd"] = float(impact_match.group(1))
    delta_match = re.search(r"DELTA_WEI:(-?\d+)", output)
    if delta_match:
        parsed["balance_delta_wei"] = int(delta_match.group(1))

    try:
        for line in proc.stdout.splitlines():
            line = line.strip()
            if line.startswith("{"):
                parsed["forge_json"] = json.loads(line)
                break
    except json.JSONDecodeError:
        pass

    return ToolResult(
        success=proc.returncode == 0,
        command=cmd,
        stdout=proc.stdout,
        stderr=proc.stderr,
        exit_code=proc.returncode,
        parsed=parsed,
    )


def run_cast_call(
    *,
    to: str,
    signature: str,
    args: list[str] | None = None,
    rpc_url: str | None = None,
    from_addr: str | None = None,
    timeout_s: int = 60,
) -> ToolResult:
    """Run `cast call` against a fork RPC."""
    cast = _which_or_raise("cast")
    rpc = rpc_url or os.environ.get("FOUNDRY_FORK_URL") or os.environ.get("ETHEREUM_RPC_URL") or _ANVIL_RPC_DEFAULT
    cmd = [cast, "call", to, signature, *(args or []), "--rpc-url", rpc]
    if from_addr:
        cmd.extend(["--from", from_addr])

    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
    return ToolResult(
        success=proc.returncode == 0,
        command=cmd,
        stdout=proc.stdout,
        stderr=proc.stderr,
        exit_code=proc.returncode,
        parsed={"result": proc.stdout.strip()},
    )


def start_anvil_fork(
    *,
    fork_url: str | None = None,
    fork_block: int | None = None,
    port: int = 8545,
    attacker: str | None = None,
    attacker_balance_eth: int = 1_000_000,
    use_docker: bool | None = None,
) -> ToolResult:
    """Start local Anvil or Docker sandbox fork with funded attacker."""
    if use_docker is None:
        use_docker = os.environ.get("NSS_ANVIL_DOCKER", "").lower() in ("1", "true", "yes")

    if use_docker:
        from night_shift_security.operator.anvil_sandbox import start_docker_sandbox

        return start_docker_sandbox(
            fork_url=fork_url,
            fork_block=fork_block,
            attacker=attacker,
            attacker_balance_eth=attacker_balance_eth,
            port=port,
        )

    anvil = _which_or_raise("anvil")
    rpc = fork_url or os.environ.get("ETHEREUM_RPC_URL") or os.environ.get("FOUNDRY_FORK_URL", "")
    if not rpc:
        raise ValueError("fork_url or ETHEREUM_RPC_URL required for anvil fork")

    _ANVIL_PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    if _ANVIL_PID_FILE.is_file():
        stop_anvil_fork()

    cmd = [
        anvil,
        "--fork-url",
        rpc,
        "--host",
        "0.0.0.0",
        "--port",
        str(port),
    ]
    if fork_block is not None:
        cmd.extend(["--fork-block-number", str(fork_block)])

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    _ANVIL_PID_FILE.write_text(str(proc.pid))
    time.sleep(2)

    funded = False
    fund_error = ""
    attacker_addr = attacker or os.environ.get(
        "OPERATOR_ATTACKER",
        "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
    )
    if shutil.which("cast"):
        try:
            wei = subprocess.run(
                ["cast", "--to-wei", str(attacker_balance_eth), "ether"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            fund_proc = subprocess.run(
                [
                    "cast",
                    "rpc",
                    "anvil_setBalance",
                    attacker_addr,
                    wei,
                    "--rpc-url",
                    f"http://127.0.0.1:{port}",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            funded = fund_proc.returncode == 0
            if not funded:
                fund_error = fund_proc.stderr.strip()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            fund_error = str(exc)

    return ToolResult(
        success=proc.poll() is None,
        command=cmd,
        stdout=f"anvil pid={proc.pid} rpc=http://127.0.0.1:{port}",
        stderr=fund_error,
        exit_code=0 if proc.poll() is None else proc.returncode or 1,
        parsed={
            "pid": proc.pid,
            "rpc_url": f"http://127.0.0.1:{port}",
            "attacker": attacker_addr,
            "attacker_funded": funded,
            "fork_block": fork_block,
        },
    )


def stop_anvil_fork() -> ToolResult:
    if not _ANVIL_PID_FILE.is_file():
        return ToolResult(
            success=True,
            command=[],
            stdout="no anvil pid file",
            stderr="",
            exit_code=0,
            parsed={},
        )
    pid = int(_ANVIL_PID_FILE.read_text().strip())
    _ANVIL_PID_FILE.unlink(missing_ok=True)
    try:
        os.kill(pid, 15)
        return ToolResult(
            success=True,
            command=["kill", str(pid)],
            stdout=f"stopped anvil pid={pid}",
            stderr="",
            exit_code=0,
            parsed={"pid": pid},
        )
    except OSError as exc:
        return ToolResult(
            success=False,
            command=["kill", str(pid)],
            stdout="",
            stderr=str(exc),
            exit_code=1,
            parsed={"pid": pid},
        )