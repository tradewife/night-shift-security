#!/usr/bin/env python3
"""MCP server exposing Slither static analysis on triage-ranked files."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "src"))

from mcp.server.fastmcp import FastMCP

from night_shift_security.operator.slither_tools import (
    load_ranked_files_from_triage,
    run_slither_on_files,
    slither_available,
)

mcp = FastMCP("nss-slither")


@mcp.tool()
def slither_scan(
    project_root: str,
    files: list[str] | None = None,
    triage_json: str | None = None,
    min_score: int = 4,
    detectors: list[str] | None = None,
) -> str:
    """
    Run Slither on ranked files only.

    Provide `files` explicitly or `triage_json` path from `triage files` output.
    """
    root = Path(project_root)
    ranked = list(files or [])
    if triage_json:
        ranked = load_ranked_files_from_triage(Path(triage_json), min_score=min_score)
    result = run_slither_on_files(
        ranked,
        project_root=root,
        detectors=detectors,
    )
    result["slither_available"] = slither_available()
    return json.dumps(result, indent=2)


if __name__ == "__main__":
    mcp.run()