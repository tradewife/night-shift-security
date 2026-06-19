"""Tests for candidate-specific PoC generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from night_shift_security.knowledge.concrete_candidates import load_candidate_records
from night_shift_security.orchestration.bounty_loop import (
    _is_catalog_anchor_finding,
    _is_novel_finding,
)
from night_shift_security.data.schemas import AttackCandidateResult, AttackVector
from night_shift_security.pocgen import generate_poc_for_candidate, verify_candidate_poc
from night_shift_security.pocgen.envelope import attach_poc_envelope, build_v4_candidate_envelope
from night_shift_security.pocgen.kamino_bindings import resolve_kamino_bindings
from night_shift_security.validation.submission_gates import _v4_candidate_submission_ok
from night_shift_security.semantic.candidates import ConcreteCandidate

KAMINO_STORE = Path("data/security_results/knowledge/concrete_candidates.jsonl")


def _candidate(chain: str = "ethereum") -> ConcreteCandidate:
    kind = "solana_instruction" if chain == "solana" else "solidity_function"
    return ConcreteCandidate(
        candidate_id="11111111-1111-4111-8111-111111111111",
        target_slug="wormhole" if chain != "solana" else "kamino",
        campaign_id="test",
        chain=chain,
        source_ref={"repo": "repo", "file": "Bridge.sol", "symbol": "completeTransfer"},
        entrypoint={
            "kind": kind,
            "name": "completeTransfer",
            "selector_or_discriminator": "0x12345678",
            "file": "Bridge.sol",
            "line": 3,
        },
        actors=[{"role": "attacker", "constraints": ["not_authorized"]}],
        state_bindings={"contracts": {}, "accounts": {}, "storage_slots": {}, "token_accounts": {}},
        sequence=[{"call": "completeTransfer", "params": {}, "sender": "attacker"}],
        invariant={"id": "bridge_accounting", "predicate": "p", "expected_violation": "v"},
        impact_oracle={"metric": "TOKEN_DELTA", "threshold": "positive", "measured": False},
        provenance={"source": "semantic_recon", "trusted": False},
    )


def test_generate_foundry_poc_fail_closed(tmp_path: Path):
    result = generate_poc_for_candidate(_candidate(), foundry_root=tmp_path / "foundry")
    path = Path(result["path"])
    assert path.is_file()
    text = path.read_text()
    assert "DELTA_WEI" in text
    assert "candidate-specific bindings required" in text
    assert result["fail_closed"] is True


def test_generate_solana_poc_fail_closed(tmp_path: Path):
    generic = _candidate("solana")
    generic.target_slug = "raydium"
    result = generate_poc_for_candidate(generic, solana_root=tmp_path / "solana")
    path = Path(result["path"])
    accounts = Path(result["accounts"])
    assert path.is_file()
    assert accounts.is_file()
    assert "MEASURED_DELTA_LAMPORTS:0" in path.read_text()
    assert result["fail_closed"] is True


def _kamino_native_candidate() -> ConcreteCandidate | None:
    for record in load_candidate_records(KAMINO_STORE):
        if record.get("candidate_id") == "kamino-native-001":
            return ConcreteCandidate.from_dict(record)
    return None


def test_kamino_native_candidate_poc_binds_real_accounts(tmp_path: Path):
    candidate = _kamino_native_candidate()
    assert candidate is not None, "kamino-native-001 missing from concrete_candidates.jsonl"
    bindings = resolve_kamino_bindings(candidate)
    assert bindings["discriminator"] == "0x02da8aeb4fc91966"
    assert bindings["program_id"] == "KLend2g3cP87fffoy8q1mQqGKjrxjC8boSyAYavgmjD"
    assert bindings["market_pubkey"]
    assert bindings["reserve_pubkey"]
    assert bindings["source_ref"]["commit"]

    result = generate_poc_for_candidate(candidate, solana_root=tmp_path / "solana")
    assert result["bindings_complete"] is True
    assert result["reproduction_artifact"] == result["path"]
    bindings_data = json.loads(Path(result["bindings"]).read_text())
    assert bindings_data["instruction"] == "refresh_reserve"
    test_text = Path(result["path"]).read_text()
    assert "MEASURED_DELTA_LAMPORTS:0" in test_text
    assert "fee-only CPI does not qualify" in test_text


def test_kamino_poc_verify_fee_only_fails_closed(tmp_path: Path):
    candidate = _kamino_native_candidate()
    assert candidate is not None
    result = generate_poc_for_candidate(candidate, solana_root=tmp_path / "solana")
    store = tmp_path / "candidates.jsonl"
    store.write_text(json.dumps(candidate.to_dict(), sort_keys=True) + "\n")
    verify = verify_candidate_poc(
        candidate.candidate_id,
        store_path=store,
        artifact_path=Path(result["path"]),
        output_dir=tmp_path / "poc_out",
    )
    assert verify["status"] == "failed_closed"
    assert verify["markers"].get("MEASURED_DELTA_LAMPORTS") == "0"


def test_attach_poc_envelope_kamino_native_001(tmp_path: Path):
    candidate = _kamino_native_candidate()
    assert candidate is not None
    store = tmp_path / "candidates.jsonl"
    store.write_text(json.dumps(candidate.to_dict(), sort_keys=True) + "\n")
    poc = generate_poc_for_candidate(candidate, solana_root=tmp_path / "solana")
    envelope = build_v4_candidate_envelope(candidate, poc, measured=False)
    assert envelope["candidate_schema_version"] == 4
    assert envelope["target_pinned"] is True
    assert envelope["reproduction_artifact"] == poc["path"]
    assert envelope["entrypoint"]["selector_or_discriminator"] == "0x02da8aeb4fc91966"
    assert envelope["impact_oracle"]["measured"] is False
    assert envelope["bindings_complete"] is True

    vector = AttackVector(
        template_id="concrete_sequence",
        target_id="kamino",
        label="kamino_concrete_kamino-native-001",
        parameters={
            "sequence_kind": "instruction",
            "candidate_id": "kamino-native-001",
            "discriminator": "0x02da8aeb4fc91966",
            "program_id": "KLend2g3cP87fffoy8q1mQqGKjrxjC8boSyAYavgmjD",
            "steps": [],
        },
    )
    cand = AttackCandidateResult(
        vector=vector,
        success_rate=0.0,
        mean_severity_score=0.1,
        mean_economic_impact_usd=0.0,
        reproducibility=0.0,
        generality=0.0,
        realism_score=0.5,
        invariant_violation_count=0,
        severity_score=0.1,
        rejected=False,
    )
    assert attach_poc_envelope(
        cand,
        store_path=store,
        solana_root=tmp_path / "solana",
    )
    bound = cand.vector.parameters["candidate"]
    assert bound["candidate_id"] == "kamino-native-001"
    assert bound["reproduction_artifact"] == poc["path"]
    assert bound["source_ref"]["commit"]


def test_native_seed_envelope_uses_harness_measured_attestation(tmp_path: Path):
    candidate = _kamino_native_candidate()
    assert candidate is not None
    store = tmp_path / "candidates.jsonl"
    store.write_text(json.dumps(candidate.to_dict(), sort_keys=True) + "\n")
    impact_dir = tmp_path / "impact"
    impact_dir.mkdir(parents=True)
    impact_path = impact_dir / "kamino_measured_delta.json"
    impact_path.write_text(
        json.dumps(
            {
                "measured_impact": True,
                "measured_impact_reason": "reserve_last_update_slot_advanced",
                "delta": {
                    "lamport_delta": "56",
                    "reserve_deltas": {
                        "last_update_slot_delta": "55",
                        "cumulative_borrow_rate_changed": True,
                    },
                },
                "on_chain_state_diff": {"non_fee": True},
            }
        )
        + "\n"
    )
    vector = AttackVector(
        template_id="concrete_sequence",
        target_id="kamino",
        parameters={"candidate_id": "kamino-native-001", "sequence_kind": "instruction", "steps": []},
    )
    cand = AttackCandidateResult(
        vector=vector,
        success_rate=0.0,
        mean_severity_score=0.0,
        mean_economic_impact_usd=0.0,
        reproducibility=0.0,
        generality=0.0,
        realism_score=0.5,
        invariant_violation_count=0,
        severity_score=0.0,
        rejected=False,
    )
    from night_shift_security.pocgen import envelope as env_mod

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(env_mod, "_harness_measured_path", lambda slug: impact_path)
    try:
        assert attach_poc_envelope(cand, store_path=store, solana_root=tmp_path / "solana")
    finally:
        monkeypatch.undo()
    bound = cand.vector.parameters["candidate"]
    assert bound["impact_oracle"]["measured"] is True
    assert cand.solana_evidence["protocol_delta_lamports"] == 56
    assert cand.solana_evidence["evidence_kind"] == "solana_measured_oracle.v1"


def test_v4_envelope_blocks_without_measured_impact():
    candidate = _kamino_native_candidate()
    assert candidate is not None
    envelope = build_v4_candidate_envelope(
        candidate,
        {"path": "solana/generated/kamino/kamino-native-001_test.py", "fail_closed": True},
        measured=False,
    )
    finding = type(
        "FindingStub",
        (),
        {
            "parameters": {"candidate": envelope},
            "fork_evidence": {},
            "solana_evidence": {},
        },
    )()
    assert _v4_candidate_submission_ok(finding) is False


def test_catalog_replay_not_labelled_novel():
    entry = {
        "target_id": "kamino",
        "catalog_analogue": True,
        "parameters": {"method": "catalog_fallback", "candidate": {"candidate_schema_version": 4}},
    }
    assert _is_catalog_anchor_finding(entry)
    assert not _is_novel_finding(entry)
