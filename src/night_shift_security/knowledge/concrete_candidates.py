"""JSONL store for v4 concrete candidates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from night_shift_security.semantic.candidates import ConcreteCandidate

DEFAULT_CANDIDATE_STORE = Path("data/security_results/knowledge/concrete_candidates.jsonl")


def load_candidate_records(path: Path = DEFAULT_CANDIDATE_STORE) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def upsert_candidates(
    candidates: list[ConcreteCandidate],
    path: Path = DEFAULT_CANDIDATE_STORE,
    *,
    replace_target_slug: str | None = None,
    replace_provenance_source: str | None = None,
) -> dict[str, Any]:
    existing: dict[str, dict[str, Any]] = {}
    for record in load_candidate_records(path):
        if not record.get("candidate_id"):
            continue
        if replace_target_slug and record.get("target_slug") == replace_target_slug:
            if replace_provenance_source:
                provenance = record.get("provenance") if isinstance(record.get("provenance"), dict) else {}
                if provenance.get("source") == replace_provenance_source:
                    continue
            else:
                continue
        existing[str(record.get("candidate_id"))] = record
    before = len(existing)
    for candidate in candidates:
        existing[candidate.candidate_id] = candidate.to_dict()
    ordered = sorted(existing.values(), key=lambda r: str(r.get("candidate_id") or ""))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        for record in ordered:
            fh.write(json.dumps(record, sort_keys=True) + "\n")
    return {
        "path": str(path),
        "before": before,
        "after": len(ordered),
        "upserted": len(candidates),
    }
