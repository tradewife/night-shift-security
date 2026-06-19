"""Build v4 candidate envelopes from concrete candidates + PoC artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from night_shift_security.data.schemas import AttackCandidateResult
from night_shift_security.knowledge.concrete_candidates import (
    DEFAULT_CANDIDATE_STORE,
    load_candidate_records,
)
from night_shift_security.pocgen.generator import generate_poc_for_candidate
from night_shift_security.semantic.candidates import ConcreteCandidate


def _load_concrete_candidate(
    candidate_id: str,
    store_path: Path,
) -> ConcreteCandidate | None:
    for record in load_candidate_records(store_path):
        if str(record.get("candidate_id") or "") == candidate_id:
            return ConcreteCandidate.from_dict(record)
    return None


def _harness_measured_path(slug: str) -> Path:
    return Path("data/security_results/impact") / f"{slug}_measured_delta.json"


def _load_harness_measured(slug: str) -> dict[str, Any] | None:
    path = _harness_measured_path(slug)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or not payload.get("measured_impact"):
        return None
    return payload


def _is_native_harness_seed(concrete: ConcreteCandidate) -> bool:
    provenance = concrete.provenance if isinstance(concrete.provenance, dict) else {}
    cid = concrete.candidate_id
    return (
        str(provenance.get("source") or "") == "native_harness_seed"
        or cid.endswith("-native-001")
        or cid.startswith(f"{concrete.target_slug}-native-")
    )


def _merge_harness_solana_evidence(
    cand: AttackCandidateResult,
    concrete: ConcreteCandidate,
    harness: dict[str, Any],
) -> None:
    delta = harness.get("delta") if isinstance(harness.get("delta"), dict) else {}
    reserve = delta.get("reserve_deltas") if isinstance(delta.get("reserve_deltas"), dict) else {}
    sol = dict(cand.solana_evidence or {})
    attestation = {
        "evidence_kind": "solana_measured_oracle.v1",
        "evidence_path": str(_harness_measured_path(concrete.target_slug)),
        "measured_impact_reason": str(harness.get("measured_impact_reason") or ""),
        "protocol_delta_lamports": int(delta.get("lamport_delta") or 0),
        "reserve_last_update_slot_delta": int(reserve.get("last_update_slot_delta") or 0),
        "cumulative_borrow_rate_changed": bool(reserve.get("cumulative_borrow_rate_changed")),
        "non_fee": bool((harness.get("on_chain_state_diff") or {}).get("non_fee")),
        "harness_measured_attestation": True,
    }
    if sol.get("method") == "solana_klend_harness":
        sol.update(attestation)
        sol.setdefault("exploit_id", "kamino-klend")
        sol.setdefault("target_id", concrete.target_slug)
    else:
        sol.update(
            {
                "target_id": concrete.target_slug,
                "exploit_id": "kamino-klend",
                "method": "solana_measured_oracle",
                **attestation,
            }
        )
    cand.solana_evidence = sol


def _impact_measured(cand: AttackCandidateResult) -> bool:
    sol = cand.solana_evidence or {}
    if int(sol.get("balance_delta_lamports") or sol.get("protocol_delta_lamports") or 0) > 0:
        return True
    fork = cand.fork_evidence or {}
    if int(fork.get("balance_delta_wei") or 0) > 0:
        return True
    if int(fork.get("token_delta") or fork.get("token_delta_units") or 0) > 0:
        return True
    return False


def build_v4_candidate_envelope(
    concrete: ConcreteCandidate,
    poc: dict[str, Any],
    *,
    measured: bool = False,
) -> dict[str, Any]:
    entrypoint = concrete.entrypoint
    source = concrete.source_ref
    oracle = dict(concrete.impact_oracle)
    oracle["measured"] = measured
    if measured:
        oracle.setdefault("kind", "solana_measured_oracle")
        oracle.setdefault("path", str(_harness_measured_path(concrete.target_slug)))
    return {
        "candidate_schema_version": 4,
        "target_pinned": True,
        "slug": concrete.target_slug,
        "candidate_id": concrete.candidate_id,
        "source_ref": {
            "commit": str(source.get("commit") or ""),
            "file": str(source.get("file") or entrypoint.get("file") or ""),
            "module": str(source.get("module") or source.get("repo") or ""),
            "symbol": str(source.get("symbol") or entrypoint.get("name") or ""),
        },
        "entrypoint": {
            "selector_or_discriminator": str(
                entrypoint.get("selector_or_discriminator")
                or entrypoint.get("discriminator")
                or ""
            ),
            "name": str(entrypoint.get("name") or ""),
            "program_id": str(entrypoint.get("program_id") or ""),
        },
        "reproduction_artifact": str(poc.get("reproduction_artifact") or poc.get("path") or ""),
        "impact_oracle": oracle,
        "failure_trace": {"blocking": False},
        "poc_kind": str(poc.get("kind") or ""),
        "bindings_artifact": str(poc.get("bindings") or ""),
        "bindings_complete": bool(poc.get("bindings_complete", False)),
        "poc_fail_closed": bool(poc.get("fail_closed", True)),
    }


def attach_poc_envelope(
    cand: AttackCandidateResult,
    *,
    store_path: Path = DEFAULT_CANDIDATE_STORE,
    foundry_root: Path = Path("foundry/generated"),
    solana_root: Path = Path("solana/generated"),
) -> bool:
    """Generate PoC artifacts and attach a v4 candidate envelope to vector parameters."""
    if cand.vector.template_id != "concrete_sequence":
        return False
    params = dict(cand.vector.parameters or {})
    candidate_id = str(params.get("candidate_id") or "").strip()
    if not candidate_id:
        return False
    concrete = _load_concrete_candidate(candidate_id, store_path)
    if concrete is None:
        return False
    poc = generate_poc_for_candidate(
        concrete,
        foundry_root=foundry_root,
        solana_root=solana_root,
    )
    measured = _impact_measured(cand)
    harness = _load_harness_measured(concrete.target_slug)
    if harness and _is_native_harness_seed(concrete):
        measured = True
        _merge_harness_solana_evidence(cand, concrete, harness)
    envelope = build_v4_candidate_envelope(concrete, poc, measured=measured)
    params["candidate"] = envelope
    cand.vector.parameters = params
    if cand.solana_evidence:
        sol = dict(cand.solana_evidence)
        sol["candidate"] = envelope
        cand.solana_evidence = sol
    if cand.fork_evidence:
        fork = dict(cand.fork_evidence)
        fork["candidate"] = envelope
        cand.fork_evidence = fork
    if harness and _is_native_harness_seed(concrete):
        from night_shift_security.validation.reality_check import apply_reality_check_candidate

        apply_reality_check_candidate(cand)
    return True


def enrich_concrete_sequence_candidates(
    candidates: list[AttackCandidateResult],
    *,
    store_path: Path = DEFAULT_CANDIDATE_STORE,
) -> list[AttackCandidateResult]:
    """Attach PoC-bound v4 envelopes for concrete_sequence depth-pass survivors."""
    for cand in candidates:
        if cand.rejected:
            continue
        attach_poc_envelope(cand, store_path=store_path)
    return candidates


__all__ = [
    "attach_poc_envelope",
    "build_v4_candidate_envelope",
    "enrich_concrete_sequence_candidates",
]