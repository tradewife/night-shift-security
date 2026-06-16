"""Failure trace RSI: classify failed executions into refinement hints."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FAILURE_SIGNATURES_PATH = Path("data/security_results/knowledge/failure_signatures.jsonl")
REFINEMENT_HINTS_PATH = Path("data/security_results/loop/refinement_hints.json")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def classify_failure(record: dict[str, Any]) -> tuple[str, str]:
    text = " ".join(
        str(record.get(k) or "")
        for k in ("error", "stderr_tail", "stdout_tail", "failure_class", "revert_reason", "program_logs")
    ).lower()
    if "missing signer" in text or "signature" in text and "missing" in text:
        return "missing_signer", "mutate_actor_or_account_role"
    if "owner" in text and ("mismatch" in text or "invalid" in text):
        return "wrong_account_owner", "repair_account_binding"
    if "bad discriminator" in text or "invalid instruction" in text or "instructionfallbacknotfound" in text:
        return "bad_discriminator", "refresh_idl_instruction_map"
    if (
        "triage_surface_requires_measured_delta" in text
        or "novel_fork_requires_balance_delta" in text
        or ("triage_surface_verified" in text and ("balance_delta_wei" in text or "delta_wei" in text))
    ):
        return "missing_economic_impact", "generate_value_moving_poc"
    if "revert" in text and "delta" not in text:
        return "revert_before_value_movement", "mutate_prestate_or_call_order"
    if "triage_surface_verified" in text or "catalogue" in text or "catalog" in text:
        return "catalogue_or_triage_only", "demand_semantic_seed_or_new_target"
    markers = record.get("markers") if isinstance(record.get("markers"), dict) else {}
    if (
        str(markers.get("DELTA_WEI") or markers.get("TOKEN_DELTA") or markers.get("MEASURED_DELTA_LAMPORTS") or "0")
        in {"0", ""}
        or record.get("failure_class") in {"fee_only", "no_protocol_delta"}
    ):
        return "no_delta_after_success", "downgrade_or_add_impact_oracle"
    return "unknown_failure", "classify_manually"


def fingerprint_failure(slug: str, record: dict[str, Any], failure_class: str) -> str:
    key = json.dumps(
        {
            "slug": slug,
            "candidate_id": record.get("candidate_id"),
            "artifact": record.get("artifact") or record.get("path"),
            "failure_class": failure_class,
            "error": str(record.get("error") or record.get("stderr_tail") or "")[:300],
        },
        sort_keys=True,
    )
    return hashlib.sha256(key.encode()).hexdigest()[:24]


def load_failure_signatures(path: Path = FAILURE_SIGNATURES_PATH) -> list[dict[str, Any]]:
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


def append_failure_signature(record: dict[str, Any], path: Path = FAILURE_SIGNATURES_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(record)
    payload.setdefault("recorded_at", _utc_now())
    with path.open("a") as fh:
        fh.write(json.dumps(payload, sort_keys=True) + "\n")
    return path


def _iter_trace_records(slug: str, traces_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    slug_dir = traces_dir / slug
    if slug_dir.is_dir():
        for path in sorted(slug_dir.glob("*.json")):
            try:
                payload = json.loads(path.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict):
                payload.setdefault("trace_path", str(path))
                records.append(payload)
    return records


def summarize_failure_traces(
    slug: str,
    *,
    traces_dir: Path = Path("data/security_results/traces"),
    signatures_path: Path = FAILURE_SIGNATURES_PATH,
    hints_path: Path = REFINEMENT_HINTS_PATH,
) -> dict[str, Any]:
    raw_records = _iter_trace_records(slug, traces_dir)
    existing = load_failure_signatures(signatures_path)
    prior_counts = Counter(str(r.get("fingerprint") or "") for r in existing)

    entries: list[dict[str, Any]] = []
    for record in raw_records:
        failure_class, action = classify_failure(record)
        fingerprint = fingerprint_failure(slug, record, failure_class)
        seen_count = prior_counts[fingerprint] + 1
        entry = {
            "slug": slug,
            "candidate_id": record.get("candidate_id") or "",
            "failure_class": failure_class,
            "recommended_action": action,
            "fingerprint": fingerprint,
            "seen_count": seen_count,
            "stop_trials": seen_count >= 3,
            "trace_path": record.get("trace_path") or "",
        }
        append_failure_signature(entry, signatures_path)
        prior_counts[fingerprint] += 1
        entries.append(entry)

    top = entries[0] if entries else None
    hints = {
        "generated_at": _utc_now(),
        "source": "failure_trace_rsi",
        "slug": slug,
        "entries": entries,
        "top": top,
        "semantic_recon_queued": any(e["stop_trials"] for e in entries),
    }
    hints_path.parent.mkdir(parents=True, exist_ok=True)
    hints_path.write_text(json.dumps(hints, indent=2, sort_keys=True) + "\n")
    return {
        "slug": slug,
        "traces": len(raw_records),
        "entries": len(entries),
        "stop_trials": sum(1 for e in entries if e["stop_trials"]),
        "hints_path": str(hints_path),
        "signatures_path": str(signatures_path),
    }
