"""Emit instruction/call sequences from ``concrete_candidates.jsonl``.

Replaces generic ``parameter_spaces`` grid emission for slugs at
``native_status >= harness_built`` (``SPEC_V5_COMPLETION.md`` Phase 10).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from night_shift_security.data.schemas import AttackVector
from night_shift_security.knowledge.concrete_candidates import load_candidate_records
from night_shift_security.native import load_manifest

DEFAULT_STORE = Path("data/security_results/knowledge/concrete_candidates.jsonl")
DEFAULT_MANIFEST = Path("data/security_results/loop/native_harness_status.json")

_NATIVE_READY_STATUSES = frozenset({"harness_built", "ready", "paused"})


@dataclass
class InstructionSequence:
    """Solana Anchor instruction chain."""

    slug: str
    steps: list[dict[str, Any]]
    candidate_id: str = ""
    discriminator: str = ""
    program_id: str = ""
    source_commit: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CallSequence:
    """EVM call chain."""

    slug: str
    steps: list[dict[str, Any]]
    candidate_id: str = ""
    selector: str = ""
    contract: str = ""
    source_commit: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def native_status_for_slug(slug: str, manifest_path: Path = DEFAULT_MANIFEST) -> str:
    manifest = load_manifest(manifest_path)
    entry = (manifest.get("harnesses") or {}).get(slug) or {}
    return str(entry.get("status") or "missing")


def _eligible(slug: str, manifest_path: Path) -> bool:
    return native_status_for_slug(slug, manifest_path) in _NATIVE_READY_STATUSES


def _records_for_slug(slug: str, store_path: Path) -> list[dict[str, Any]]:
    slug_l = slug.strip().lower()
    return [
        r
        for r in load_candidate_records(store_path)
        if str(r.get("target_slug") or "").lower() == slug_l
    ]


def sequences_for_slug(
    slug: str,
    *,
    store_path: Path = DEFAULT_STORE,
    manifest_path: Path = DEFAULT_MANIFEST,
    limit: int = 50,
) -> list[InstructionSequence | CallSequence]:
    if not _eligible(slug, manifest_path):
        return []

    out: list[InstructionSequence | CallSequence] = []
    for record in _records_for_slug(slug, store_path)[:limit]:
        entrypoint = record.get("entrypoint") if isinstance(record.get("entrypoint"), dict) else {}
        provenance = record.get("provenance") if isinstance(record.get("provenance"), dict) else {}
        source_ref = record.get("source_ref") if isinstance(record.get("source_ref"), dict) else {}
        commit = str(source_ref.get("commit") or provenance.get("commit") or "")
        disc = str(
            entrypoint.get("discriminator")
            or entrypoint.get("selector_or_discriminator")
            or record.get("discriminator")
            or ""
        )
        program = str(entrypoint.get("program_id") or entrypoint.get("target") or "")
        chain = str(record.get("chain") or record.get("ecosystem") or "evm").lower()
        step = {
            "instruction": str(entrypoint.get("name") or record.get("entrypoint_name") or ""),
            "discriminator": disc,
            "program_id": program,
            "accounts": entrypoint.get("accounts") or [],
            "params": record.get("params") or {},
        }
        if chain == "solana":
            out.append(
                InstructionSequence(
                    slug=slug,
                    steps=[step],
                    candidate_id=str(record.get("candidate_id") or ""),
                    discriminator=disc,
                    program_id=program,
                    source_commit=commit,
                )
            )
        else:
            out.append(
                CallSequence(
                    slug=slug,
                    steps=[step],
                    candidate_id=str(record.get("candidate_id") or ""),
                    selector=disc,
                    contract=program,
                    source_commit=commit,
                )
            )
    return out


def emit_concrete_sequences(
    slug: str,
    *,
    store_path: Path = DEFAULT_STORE,
    manifest_path: Path = DEFAULT_MANIFEST,
    limit: int = 50,
) -> list[AttackVector]:
    """Convert concrete store rows into ``AttackVector`` instances for depth pass."""
    vectors: list[AttackVector] = []
    for seq in sequences_for_slug(slug, store_path=store_path, manifest_path=manifest_path, limit=limit):
        if isinstance(seq, InstructionSequence):
            label = f"{slug}_concrete_{seq.candidate_id or seq.discriminator[:10]}"
            vectors.append(
                AttackVector(
                    template_id="concrete_sequence",
                    target_id=slug,
                    label=label,
                    parameters={
                        "sequence_kind": "instruction",
                        "steps": seq.steps,
                        "discriminator": seq.discriminator,
                        "program_id": seq.program_id,
                        "candidate_id": seq.candidate_id,
                    },
                    metadata={
                        "concrete_sequence": True,
                        "source_commit": seq.source_commit,
                        "trusted": False,
                    },
                )
            )
        else:
            label = f"{slug}_concrete_{seq.candidate_id or seq.selector[:10]}"
            vectors.append(
                AttackVector(
                    template_id="concrete_sequence",
                    target_id=slug,
                    label=label,
                    parameters={
                        "sequence_kind": "call",
                        "steps": seq.steps,
                        "selector": seq.selector,
                        "contract": seq.contract,
                        "candidate_id": seq.candidate_id,
                    },
                    metadata={
                        "concrete_sequence": True,
                        "source_commit": seq.source_commit,
                        "trusted": False,
                    },
                )
            )
    return vectors


__all__ = [
    "CallSequence",
    "InstructionSequence",
    "DEFAULT_MANIFEST",
    "DEFAULT_STORE",
    "emit_concrete_sequences",
    "native_status_for_slug",
    "sequences_for_slug",
]