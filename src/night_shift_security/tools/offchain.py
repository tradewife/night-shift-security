"""Scoped off-chain recon tool wrappers for web/API bounty surfaces."""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SUPPORTED_TOOLS = {
    "bbot": ["bbot"],
    "spiderfoot": ["spiderfoot", "-s"],
    "strix": ["strix"],
    "caido": ["caido"],
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_scope(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError("scope file must be a JSON object")
    return payload


def offchain_scope_enabled(scope: dict[str, Any]) -> bool:
    surfaces = scope.get("surfaces") if isinstance(scope.get("surfaces"), list) else []
    return any(str(s).lower() in {"web", "api", "domain", "cloud", "relayer"} for s in surfaces)


def run_offchain_tool(
    *,
    tool_name: str,
    scope_path: Path,
    out_dir: Path,
    target: str | None = None,
) -> dict[str, Any]:
    if tool_name not in SUPPORTED_TOOLS:
        return {"status": "unsupported_tool", "tool": tool_name}
    scope = load_scope(scope_path)
    if not offchain_scope_enabled(scope):
        return {
            "status": "scope_not_enabled",
            "tool": tool_name,
            "scope_path": str(scope_path),
            "message": "Scope file must include web/api/domain/cloud/relayer surface",
        }
    target_value = target or str(scope.get("target") or scope.get("domain") or "").strip()
    if not target_value:
        return {"status": "missing_target", "tool": tool_name, "scope_path": str(scope_path)}

    binary = shutil.which(SUPPORTED_TOOLS[tool_name][0])
    if not binary:
        return {"status": "tool_missing", "tool": tool_name, "target": target_value}

    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / f"{tool_name}.json"
    cmd = [binary] + SUPPORTED_TOOLS[tool_name][1:] + [target_value]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    payload = {
        "generated_at": _utc_now(),
        "tool": tool_name,
        "target": target_value,
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-5000:],
        "stderr_tail": proc.stderr[-2000:],
        "trusted": False,
    }
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return {
        "status": "ok" if proc.returncode == 0 else "failed",
        "tool": tool_name,
        "target": target_value,
        "output": str(output),
    }
