"""Native-harness status manifest — v5 substrate precondition gate (carried into v6).

The manifest at ``data/security_results/loop/native_harness_status.json``
records per-target harness rollout state. The HIPIF cron bootstrap
(``nss-hipif-chain.sh``) refuses to run the legacy v4.2 chain unless at least
one target reaches ``status=ready``. Originally audit recommendation
C8 in the v5 phase (the v4.2-era audit was retired on 2026-06-20);
see ``SPEC.md`` §3 (audit saturation + pivot) and §14 (version history).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_PATH = Path("data/security_results/loop/native_harness_status.json")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class HarnessStatus:
    slug: str = ""
    name: str = ""
    platform: str = ""
    chain: str = ""
    contract_address: str = ""
    source_commit: str = ""
    status: str = "missing"  # missing, mapped, harness_built, ready, paused
    last_updated: str = field(default_factory=_utc_now)
    notes: str = ""
    measured_delta_count: int = 0
    fork_tests: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return {k: v for k, v in d.items() if v not in (None, "", [], 0)}


def empty_manifest() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "generated_at": _utc_now(),
        "reason": "paused_awaiting_native_harness",
        "minimum_required": 1,
        "ready_count": 0,
        "harnesses": {},
    }


def load_manifest(path: Path = DEFAULT_PATH) -> dict[str, Any]:
    if not path.is_file():
        return empty_manifest()
    try:
        import json
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return empty_manifest()
    if not isinstance(data, dict):
        return empty_manifest()
    # Defensive: recompute ready_count from the actual harnesses dict
    # so stale metadata never masks a data-corruption bug (duplicated
    # JSON keys, manual edits, etc.).  The original file's ready_count
    # is overwritten.
    harnesses = data.get("harnesses") or {}
    data["ready_count"] = sum(
        1 for h in harnesses.values()
        if isinstance(h, dict) and h.get("status") == "ready"
    )
    return data


def save_manifest(payload: dict[str, Any], path: Path = DEFAULT_PATH) -> Path:
    import json
    path.parent.mkdir(parents=True, exist_ok=True)
    payload["generated_at"] = _utc_now()
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n")
    return path


def upsert_harness(entry: HarnessStatus, path: Path = DEFAULT_PATH, *, persist: bool = True) -> dict[str, Any]:
    payload = load_manifest(path)
    harnesses = dict(payload.get("harnesses") or {})
    harnesses[entry.slug] = entry.to_dict()
    ready_count = sum(int(h.get("status") == "ready") for h in harnesses.values())
    payload["harnesses"] = harnesses
    payload["ready_count"] = ready_count
    if ready_count > 0 and payload.get("reason") == "paused_awaiting_native_harness":
        payload.pop("reason", None)
    if persist:
        save_manifest(payload, path)
    return payload


__all__ = [
    "DEFAULT_PATH",
    "HarnessStatus",
    "empty_manifest",
    "load_manifest",
    "save_manifest",
    "upsert_harness",
]
