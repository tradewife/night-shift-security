"""Tests for scoped off-chain recon wrappers."""

from __future__ import annotations

import json
from pathlib import Path

from night_shift_security.tools.offchain import offchain_scope_enabled, run_offchain_tool


def test_offchain_scope_enabled_only_for_web_api_surfaces():
    assert offchain_scope_enabled({"surfaces": ["api"]}) is True
    assert offchain_scope_enabled({"surfaces": ["protocol"]}) is False


def test_offchain_tool_missing_is_nonfatal_when_scoped(tmp_path: Path):
    scope = tmp_path / "scope.json"
    scope.write_text(json.dumps({"surfaces": ["web"], "target": "example.com"}))
    result = run_offchain_tool(
        tool_name="bbot",
        scope_path=scope,
        out_dir=tmp_path / "out",
        target=None,
    )
    assert result["status"] in {"tool_missing", "ok", "failed"}
    assert result["tool"] == "bbot"


def test_offchain_tool_rejects_protocol_only_scope(tmp_path: Path):
    scope = tmp_path / "scope.json"
    scope.write_text(json.dumps({"surfaces": ["protocol"], "target": "example.com"}))
    result = run_offchain_tool(
        tool_name="bbot",
        scope_path=scope,
        out_dir=tmp_path / "out",
        target=None,
    )
    assert result["status"] == "scope_not_enabled"
