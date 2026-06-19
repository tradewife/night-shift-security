"""Tests for concrete hypothesis sequences (Phase 10)."""

from __future__ import annotations

import json
from pathlib import Path

from night_shift_security.hypothesis.concrete_sequences import (
    emit_concrete_sequences,
    native_status_for_slug,
    sequences_for_slug,
)
from night_shift_security.knowledge.concrete_candidates import upsert_candidates
from night_shift_security.native import HarnessStatus, upsert_harness
from night_shift_security.semantic.candidates import ConcreteCandidate


def _write_manifest(tmp_path: Path, slug: str, status: str) -> Path:
    path = tmp_path / "native_harness_status.json"
    upsert_harness(
        HarnessStatus(slug=slug, status=status, name=slug),
        path=path,
    )
    return path


def _minimal_candidate(slug: str, chain: str, cid: str) -> ConcreteCandidate:
    return ConcreteCandidate(
        candidate_id=cid,
        target_slug=slug,
        campaign_id=f"campaign-{slug}",
        chain=chain,
        source_ref={"commit": "abc123"},
        entrypoint={
            "name": "refresh_reserve",
            "discriminator": "0x02da8aeb4fc91966",
            "program_id": "KLend2g3cP87fffoy8q1mQqGKjrxjC8boSyAYavgmjD",
        },
        actors=[],
        state_bindings={},
        sequence=[],
        invariant={"id": "reserve_solvency"},
        impact_oracle={"measured": False},
        provenance={"source": "semantic_map"},
    )


def _write_store(tmp_path: Path, slug: str, chain: str = "solana") -> Path:
    path = tmp_path / "concrete_candidates.jsonl"
    upsert_candidates([_minimal_candidate(slug, chain, f"{slug}-001")], path=path)
    return path


def test_native_status_missing(tmp_path: Path) -> None:
    path = _write_manifest(tmp_path, "kamino", "missing")
    assert native_status_for_slug("kamino", path) == "missing"


def test_sequences_empty_when_not_eligible(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path, "kamino", "missing")
    store = _write_store(tmp_path, "kamino")
    assert sequences_for_slug("kamino", store_path=store, manifest_path=manifest) == []


def test_sequences_for_harness_built(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path, "kamino", "harness_built")
    store = _write_store(tmp_path, "kamino")
    seqs = sequences_for_slug("kamino", store_path=store, manifest_path=manifest)
    assert len(seqs) == 1
    assert seqs[0].discriminator.startswith("0x")


def test_emit_attack_vectors(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path, "kamino", "ready")
    store = _write_store(tmp_path, "kamino")
    vectors = emit_concrete_sequences("kamino", store_path=store, manifest_path=manifest)
    assert len(vectors) == 1
    assert vectors[0].metadata.get("concrete_sequence") is True
    assert vectors[0].parameters["sequence_kind"] == "instruction"


def test_evm_call_sequence(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path, "uniswap_v4", "ready")
    store = _write_store(tmp_path, "uniswap_v4", chain="ethereum")
    seqs = sequences_for_slug("uniswap_v4", store_path=store, manifest_path=manifest)
    assert len(seqs) == 1
    from night_shift_security.hypothesis.concrete_sequences import CallSequence

    assert isinstance(seqs[0], CallSequence)


def test_concrete_sequence_vector_key_is_hashable(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path, "kamino", "ready")
    store = _write_store(tmp_path, "kamino")
    vectors = emit_concrete_sequences("kamino", store_path=store, manifest_path=manifest)
    assert vectors
    keys = {v.key() for v in vectors}
    assert len(keys) == len(vectors)


def test_concrete_sequence_template_registered() -> None:
    import night_shift_security.domain.attack_templates.concrete_sequence  # noqa: F401
    from night_shift_security.domain.attack_templates.base import get_template

    template = get_template("concrete_sequence")
    assert template.template_id == "concrete_sequence"


def test_limit_respected(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path, "kamino", "ready")
    store = tmp_path / "store.jsonl"
    candidates = [_minimal_candidate("kamino", "solana", f"kamino-{i:03d}") for i in range(5)]
    upsert_candidates(candidates, path=store)
    seqs = sequences_for_slug("kamino", store_path=store, manifest_path=manifest, limit=3)
    assert len(seqs) == 3