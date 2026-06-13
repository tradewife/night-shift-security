"""Tests for operator foundry, slither, and docker sandbox adapters."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from night_shift_security.operator import anvil_sandbox, foundry_tools, slither_tools


def test_run_forge_test_parses_impact_and_delta(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(foundry_tools.shutil, "which", lambda name: "/usr/bin/forge")

    class Proc:
        returncode = 0
        stdout = (
            '{"test":"ForkTest","status":"success"}\n'
            "IMPACT_USD:1250.5\n"
            "DELTA_WEI:200000000000000000\n"
        )
        stderr = ""

    monkeypatch.setattr(foundry_tools.subprocess, "run", lambda *a, **k: Proc())

    result = foundry_tools.run_forge_test(
        match_test="testFork",
        foundry_root=tmp_path,
        fork_url="http://rpc.example",
        fork_block=16825925,
    )
    assert result.success
    assert result.parsed["impact_usd"] == 1250.5
    assert result.parsed["balance_delta_wei"] == 200_000_000_000_000_000
    assert "forge_json" in result.parsed


def test_run_cast_call_uses_rpc(monkeypatch):
    monkeypatch.setattr(foundry_tools.shutil, "which", lambda name: "/usr/bin/cast")

    class Proc:
        returncode = 0
        stdout = "0x0000000000000000000000000000000000000000000000000de0b6b3a7640000\n"
        stderr = ""

    captured: dict = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return Proc()

    monkeypatch.setattr(foundry_tools.subprocess, "run", fake_run)

    result = foundry_tools.run_cast_call(
        to="0xabc",
        signature="balanceOf(address)(uint256)",
        args=["0xdef"],
        rpc_url="http://127.0.0.1:8545",
    )
    assert result.success
    assert "--rpc-url" in captured["cmd"]
    assert "http://127.0.0.1:8545" in captured["cmd"]


def test_stop_anvil_no_pid_file(monkeypatch, tmp_path: Path):
    pid_file = tmp_path / "anvil.pid"
    monkeypatch.setattr(foundry_tools, "_ANVIL_PID_FILE", pid_file)

    result = foundry_tools.stop_anvil_fork()
    assert result.success
    assert "no anvil pid file" in result.stdout


def test_start_anvil_requires_fork_url(monkeypatch):
    monkeypatch.setattr(foundry_tools.shutil, "which", lambda name: "/usr/bin/anvil")
    monkeypatch.delenv("ETHEREUM_RPC_URL", raising=False)
    monkeypatch.delenv("FOUNDRY_FORK_URL", raising=False)

    with pytest.raises(ValueError, match="fork_url"):
        foundry_tools.start_anvil_fork()


def test_slither_unavailable_returns_clear_error(monkeypatch):
    monkeypatch.setattr(slither_tools, "slither_available", lambda: False)

    result = slither_tools.run_slither_on_files(
        ["src/Foo.sol"],
        project_root=Path("/tmp/repo"),
    )
    assert not result["success"]
    assert "slither not found" in result["error"]


def test_load_ranked_files_from_triage(tmp_path: Path):
    triage = tmp_path / "triage.json"
    triage.write_text(
        json.dumps(
            {
                "files": [
                    {"path": "a.sol", "score": 5},
                    {"path": "b.sol", "score": 3},
                    {"path": "c.sol", "score": 4},
                ]
            }
        )
    )
    ranked = slither_tools.load_ranked_files_from_triage(triage, min_score=4)
    assert ranked == ["a.sol", "c.sol"]


def test_run_slither_on_files_no_existing_files(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(slither_tools, "slither_available", lambda: True)
    (tmp_path / "other.sol").write_text("// unrelated")

    result = slither_tools.run_slither_on_files(
        ["missing.sol"],
        project_root=tmp_path,
    )
    assert not result["success"]
    assert "no existing files" in result["error"]


def test_run_slither_parses_detector_json(monkeypatch, tmp_path: Path):
    target = tmp_path / "Vault.sol"
    target.write_text("pragma solidity ^0.8.0; contract Vault {}")
    monkeypatch.setattr(slither_tools, "slither_available", lambda: True)

    payload = {
        "results": {
            "detectors": [
                {
                    "check": "reentrancy-eth",
                    "impact": "High",
                    "confidence": "Medium",
                    "description": "Reentrancy in withdraw",
                    "elements": [
                        {
                            "name": "withdraw",
                            "source_mapping": {"filename_short": "Vault.sol"},
                        }
                    ],
                }
            ]
        }
    }

    class Proc:
        returncode = 0
        stdout = json.dumps(payload)
        stderr = ""

    monkeypatch.setattr(slither_tools.subprocess, "run", lambda *a, **k: Proc())

    result = slither_tools.run_slither_on_files(
        ["Vault.sol"],
        project_root=tmp_path,
    )
    assert result["success"]
    assert len(result["findings"]) == 1
    assert result["findings"][0]["check"] == "reentrancy-eth"
    assert result["findings"][0]["filename"] == "Vault.sol"


def test_sandbox_compose_path():
    path = anvil_sandbox.sandbox_compose_path()
    assert path.name == "compose.yaml"
    assert path.parent.name == "anvil-sandbox"


def test_start_docker_sandbox_no_docker(monkeypatch):
    monkeypatch.setattr(anvil_sandbox, "shutil_which", lambda name: None)

    result = anvil_sandbox.start_docker_sandbox(fork_url="http://rpc.example")
    assert not result.success
    assert "docker not found" in result.stderr


def test_start_docker_sandbox_no_rpc(monkeypatch):
    monkeypatch.setattr(anvil_sandbox, "shutil_which", lambda name: "/usr/bin/docker")
    monkeypatch.delenv("ETHEREUM_RPC_URL", raising=False)
    monkeypatch.delenv("FOUNDRY_FORK_URL", raising=False)

    result = anvil_sandbox.start_docker_sandbox()
    assert not result.success
    assert "ETHEREUM_RPC_URL required" in result.stderr


def test_start_docker_sandbox_success(monkeypatch):
    monkeypatch.setattr(anvil_sandbox, "shutil_which", lambda name: "/usr/bin/docker")
    monkeypatch.setattr(anvil_sandbox.time, "sleep", lambda _: None)

    class Proc:
        returncode = 0
        stdout = "Container started"
        stderr = ""

    captured: dict = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["env"] = kwargs.get("env", {})
        return Proc()

    monkeypatch.setattr(anvil_sandbox.subprocess, "run", fake_run)

    result = anvil_sandbox.start_docker_sandbox(
        fork_url="http://rpc.example",
        fork_block=12345,
        port=8545,
    )
    assert result.success
    assert "docker" in captured["cmd"]
    assert "compose" in captured["cmd"]
    assert result.parsed["rpc_url"] == "http://127.0.0.1:8545"
    assert result.parsed["fork_block"] == 12345


def test_sandbox_status_without_docker(monkeypatch):
    monkeypatch.setattr(anvil_sandbox, "shutil_which", lambda name: None)

    status = anvil_sandbox.sandbox_status()
    assert not status["running"]
    assert status["error"] == "docker not found"