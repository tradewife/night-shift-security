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
    assert hf.next_subgoal_id(ctx) == "depth_wormhole_bridge"


def test_chain_subgoals_order():
    assert hf.CHAIN_SUBGOALS[0] == "bootstrap"
    assert hf.CHAIN_SUBGOALS[-1] == "gate"
    assert hf.CHAIN_SUBGOALS.index("depth_wormhole_bridge") == hf.CHAIN_SUBGOALS.index("depth_wormhole") + 1
    assert hf.CHAIN_SUBGOALS.index("kamino_preflight") < hf.CHAIN_SUBGOALS.index("depth_kamino")
    assert "cantina_slates" in hf.CHAIN_SUBGOALS


def test_history_folder_explicit_subgoal_advances_index():
    ctx = hf.FoldedContext(task="t", current_subgoal="depth_wormhole", subgoal_index=2)
    ctx = hf.history_folder(ctx, "depth_wormhole_bridge", "bridge refinement ok", metrics={"fork": 60})
    assert ctx.folded_history[-1].subgoal_id == "depth_wormhole_bridge"
    assert ctx.current_subgoal == "kamino_preflight"
    assert ctx.subgoal_index == 4


def test_folded_record_compact_line():
    rec = hf.FoldedRecord(
        subgoal_id="depth_wormhole",
        outcome_summary="fork depth ok",
        metrics={"fork_reproduced": 47, "findings": 13},
    )
    line = rec.compact_line()
    assert "[depth_wormhole]" in line
    assert "fork_reproduced=47" in line


def test_agent_subgoals_are_bridge_refine_coordinator():
    assert hf.AGENT_SUBGOALS == frozenset(
        {"depth_wormhole_bridge", "refine_conditional", "coordinator_conditional"}
    )
    assert "depth_wormhole" not in hf.AGENT_SUBGOALS
    assert len(hf.DETERMINISTIC_SUBGOALS) + len(hf.AGENT_SUBGOALS) == len(hf.CHAIN_SUBGOALS)


def test_validate_chain_complete_requires_all_folds():
    ctx = hf.FoldedContext(task="t", chain_status="complete", current_subgoal="gate")
    ctx = hf.history_folder(ctx, "bootstrap", "ok")
    result = hf.validate_chain_complete(ctx)
    assert result.ok is False
    assert any("insufficient_folds" in e for e in result.errors)
    assert any("missing_fold:gate" in e for e in result.errors)


def test_validate_chain_complete_ok_when_all_folded():
    ctx = hf.FoldedContext(task="t", chain_status="running", current_subgoal="bootstrap")
    for sg in hf.CHAIN_SUBGOALS:
        ctx = hf.history_folder(ctx, sg, f"{sg} ok", metrics={"n": 1})
        if sg == "rsi_fold":
            ctx = hf.mark_awaiting_agent(ctx)
    result = hf.validate_chain_complete(ctx)
    assert result.ok is True
    assert result.folds == len(hf.CHAIN_SUBGOALS)


def test_mark_awaiting_agent_sets_first_pending():
    ctx = hf.FoldedContext(task="t", chain_status="running", current_subgoal="rsi_fold")
    for sg in ("bootstrap", "scan_all", "depth_wormhole", "kamino_preflight", "depth_kamino"):
        ctx = hf.history_folder(ctx, sg, "ok")
    ctx = hf.mark_awaiting_agent(ctx)
    assert ctx.chain_status == "awaiting_agent"
    assert ctx.bulk_phase_complete is True
    assert ctx.current_subgoal == "depth_wormhole_bridge"


def test_authorize_fold_blocks_agent_bulk_subgoal(monkeypatch):
    ctx = hf.FoldedContext(task="t", chain_status="running", current_subgoal="kamino_preflight")
    monkeypatch.delenv("NSS_HIPIF_RUNNER", raising=False)
    auth = hf.authorize_fold(ctx, "kamino_preflight")
    assert auth.ok is False
    assert "bulk_requires" in auth.error


def test_authorize_fold_blocks_agent_before_handoff(monkeypatch):
    ctx = hf.FoldedContext(task="t", chain_status="running", current_subgoal="depth_wormhole_bridge")
    for sg in ("bootstrap", "scan_all", "depth_wormhole"):
        ctx = hf.history_folder(ctx, sg, "ok")
    monkeypatch.delenv("NSS_HIPIF_RUNNER", raising=False)
    auth = hf.authorize_fold(ctx, "depth_wormhole_bridge")
    assert auth.ok is False
    assert "bulk_phase_incomplete" in auth.error


def test_authorize_fold_allows_agent_after_handoff(monkeypatch):
    ctx = hf.FoldedContext(task="t", chain_status="awaiting_agent", bulk_phase_complete=True)
    for sg in ("bootstrap", "scan_all", "depth_wormhole", "kamino_preflight", "depth_kamino", "cantina_slates", "hunt_rotation", "rsi_fold"):
        ctx = hf.history_folder(ctx, sg, "ok")
    monkeypatch.delenv("NSS_HIPIF_RUNNER", raising=False)
    auth = hf.authorize_fold(ctx, "depth_wormhole_bridge")
    assert auth.ok is True


def test_cli_hipif_gate_incomplete(tmp_path: Path):
    import subprocess
    import sys

    ctx_path = tmp_path / "ctx.json"
    ctx = hf.init_context("gate test", ctx_path)
    hf.save_context(ctx, ctx_path)
    repo = Path(__file__).resolve().parents[1]
    proc = subprocess.run(
        [sys.executable, "-m", "night_shift_security.cli.main", "hipif", "gate", "--context", str(ctx_path)],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert payload["ok"] is False


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