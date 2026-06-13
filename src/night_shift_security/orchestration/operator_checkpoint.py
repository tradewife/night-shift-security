"""Operator checkpoint — context rollover persistence for long-horizon hunts."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

_DEFAULT_PATH = Path("data/security_results/operator/checkpoint.json")

ContextReason = Literal["rollover", "manual", "pre_shutdown"]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_checkpoint() -> dict[str, Any]:
    return {
        "version": 1,
        "written_at": "",
        "session_id": "",
        "target_slug": "",
        "active_hypothesis": "",
        "ranked_files": [],
        "fork_block": 0,
        "last_verifier": {"passed": False, "delta_wei": 0},
        "next_commands": [],
        "context_reason": "manual",
    }


def checkpoint_path(path: Path | None = None) -> Path:
    return path or _DEFAULT_PATH


def load_checkpoint(path: Path | None = None) -> dict[str, Any]:
    p = checkpoint_path(path)
    if not p.is_file():
        return default_checkpoint()
    data = json.loads(p.read_text())
    base = default_checkpoint()
    base.update(data)
    return base


def save_checkpoint(payload: dict[str, Any], path: Path | None = None) -> Path:
    p = checkpoint_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = default_checkpoint()
    data.update(payload)
    data["written_at"] = data.get("written_at") or _utc_now()
    if not data.get("session_id"):
        data["session_id"] = str(uuid.uuid4())
    p.write_text(json.dumps(data, indent=2, default=str) + "\n")
    return p


def write_checkpoint(
    *,
    target_slug: str = "",
    active_hypothesis: str = "",
    ranked_files: list[dict[str, Any]] | None = None,
    fork_block: int = 0,
    last_verifier: dict[str, Any] | None = None,
    next_commands: list[str] | None = None,
    context_reason: ContextReason = "manual",
    session_id: str = "",
    path: Path | None = None,
) -> dict[str, Any]:
    existing = load_checkpoint(path)
    payload = {
        "version": 1,
        "written_at": _utc_now(),
        "session_id": session_id or existing.get("session_id") or str(uuid.uuid4()),
        "target_slug": target_slug,
        "active_hypothesis": active_hypothesis,
        "ranked_files": ranked_files or [],
        "fork_block": fork_block,
        "last_verifier": last_verifier or {"passed": False, "delta_wei": 0},
        "next_commands": next_commands or [],
        "context_reason": context_reason,
    }
    save_checkpoint(payload, path)
    return payload


def clear_checkpoint(path: Path | None = None) -> None:
    p = checkpoint_path(path)
    if p.is_file():
        p.unlink()