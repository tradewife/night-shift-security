"""Build v4 candidate envelopes from concrete candidates + PoC artifacts."""

from __future__ import annotations

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
    envelope = build_v4_candidate_envelope(concrete, poc, measured=_impact_measured(cand))
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