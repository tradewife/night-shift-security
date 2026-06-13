"""Tests for HIPIF orchestration hooks."""

from __future__ import annotations

import json
from pathlib import Path

from night_shift_security.orchestration import hipif as hf


def test_parse_agent_turn_valid():
    text = """
<reflection>Scan artifact exists.</reflection>
<completion>yes</completion>
<subgoal>scan_all</subgoal>
<action>scan --platform all</action>
"""
    parsed = hf.parse_agent_turn(text)
    assert parsed.format_ok is True
    assert parsed.completion is True
    assert parsed.subgoal == "scan_all"
    assert "scan" in parsed.action


def test_parse_agent_turn_missing_tags():
    parsed = hf.parse_agent_turn("no tags here")
    assert parsed.format_ok is False
    assert "missing <reflection>" in parsed.format_errors


def test_history_folder_clears_local_and_advances():
    ctx = hf.FoldedContext(task="test", current_subgoal="bootstrap", subgoal_index=0)
    ctx.local_history.append(hf.LocalStep(action="git pull", observation="ok"))
    ctx = hf.history_folder(ctx, "bootstrap", "context loaded", metrics={"status": "ok"})
    assert len(ctx.local_history) == 0
    assert len(ctx.folded_history) == 1
    assert ctx.current_subgoal == "scan_all"
    assert ctx.subgoal_index == 1


def test_repetition_monitor_blocks_at_three():
    steps = [
        hf.LocalStep(action="bounty loop --iterations 1", observation="fail"),
        hf.LocalStep(action="bounty loop --iterations 1", observation="fail"),
    ]
    rep = hf.repetition_monitor(steps, "bounty loop --iterations 1", observation="fail")
    assert rep.repeat_count == 2
    assert rep.blocked is False
    steps.append(hf.LocalStep(action="bounty loop --iterations 1", observation="fail"))
    rep2 = hf.repetition_monitor(steps, "bounty loop --iterations 1", observation="fail")
    assert rep2.blocked is True


def test_grounding_check_accepts_wormhole_action(tmp_path: Path):
    ctx = hf.FoldedContext(task="t", current_subgoal="depth_wormhole")
    result = hf.grounding_check(
        ctx,
        "depth_wormhole",
        "NSS_LOOP_DEPTH_SLUG=wormhole bounty loop --iterations 1",
        repo_root=tmp_path,
    )
    assert result.ok is True


def test_grounding_check_rejects_unknown_subgoal():
    ctx = hf.FoldedContext(task="t", current_subgoal="bootstrap")
    result = hf.grounding_check(ctx, "nonexistent_subgoal", "scan --platform all")
    assert result.ok is False
    assert any("unknown_subgoal" in m for m in result.missing_refs)


def test_init_and_save_load_roundtrip(tmp_path: Path):
    path = tmp_path / "folded_context.json"
    ctx = hf.init_context("Night chain test", path)
    assert ctx.current_subgoal == "bootstrap"
    loaded = hf.load_context(path)
    assert loaded is not None
    assert loaded.task == "Night chain test"


def test_next_subgoal_id_follows_chain():
    ctx = hf.FoldedContext(task="t", subgoal_index=2)
    assert hf.next_subgoal_id(ctx) == "depth_kamino"


def test_chain_subgoals_order():
    assert hf.CHAIN_SUBGOALS[0] == "bootstrap"
    assert hf.CHAIN_SUBGOALS[-1] == "gate"
    assert "depth_wormhole" in hf.CHAIN_SUBGOALS
    assert "depth_kamino" in hf.CHAIN_SUBGOALS


def test_folded_record_compact_line():
    rec = hf.FoldedRecord(
        subgoal_id="depth_wormhole",
        outcome_summary="fork depth ok",
        metrics={"fork_reproduced": 47, "findings": 13},
    )
    line = rec.compact_line()
    assert "[depth_wormhole]" in line
    assert "fork_reproduced=47" in line


def test_cli_hipif_init_and_read(tmp_path: Path, monkeypatch):
    import subprocess
    import sys

    ctx_path = tmp_path / "ctx.json"
    repo = Path(__file__).resolve().parents[1]
    init = subprocess.run(
        [
            sys.executable,
            "-m",
            "night_shift_security.cli.main",
            "hipif",
            "init",
            "--task",
            "cli test",
            "--context",
            str(ctx_path),
        ],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    assert init.returncode == 0
    data = json.loads(init.stdout)
    assert data["current_subgoal"] == "bootstrap"

    read = subprocess.run(
        [
            sys.executable,
            "-m",
            "night_shift_security.cli.main",
            "hipif",
            "read",
            "--context",
            str(ctx_path),
        ],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    assert read.returncode == 0
    assert "cli test" in read.stdout