"""Tests for Wormhole economic-impact gates."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from night_shift_security.bridge.wormhole_economic import (
    bridge_accounting_violation,
    generated_wormhole_poc,
    wormhole_economic_impact_verified,
    write_message_fixture,
)
from night_shift_security.data.schemas import Finding, InvariantViolation, ReproductionStep, Severity
from night_shift_security.semantic.candidates import ConcreteCandidate
from night_shift_security.validation.submission_gates import qualifies_for_submission


def _candidate() -> ConcreteCandidate:
    return ConcreteCandidate(
        candidate_id="22222222-2222-4222-8222-222222222222",
        target_slug="wormhole",
        campaign_id="test",
        chain="ethereum",
        source_ref={"repo": "repo", "file": "Bridge.sol", "symbol": "completeTransfer"},
        entrypoint={"kind": "solidity_function", "name": "completeTransfer", "selector_or_discriminator": "0x12345678"},
        actors=[{"role": "attacker", "constraints": ["not_authorized"]}],
        state_bindings={"contracts": {}, "accounts": {}, "storage_slots": {}, "token_accounts": {}},
        sequence=[{"call": "completeTransfer", "params": {}, "sender": "attacker"}],
        invariant={"id": "bridge_accounting", "predicate": "p", "expected_violation": "v"},
        impact_oracle={"metric": "TOKEN_DELTA", "threshold": "positive", "measured": False},
        provenance={"source": "semantic_recon", "trusted": False},
    )


def _wormhole_finding(fork_evidence: dict) -> Finding:
    return Finding(
        finding_id="NSS-WH",
        template_id="composability_risk",
        target_id="wormhole",
        severity=Severity.CRITICAL,
        severity_score=0.9,
        economic_impact_usd=1_000_000,
        capital_required_usd=1,
        reproducibility=1.0,
        parameters={
            "candidate": {
                "candidate_schema_version": 4,
                "target_pinned": True,
                "source_ref": {"commit": "abc123", "file": "contracts/Bridge.sol"},
                "entrypoint": {"selector_or_discriminator": "0x12345678"},
                "reproduction_artifact": "tests/test_wormhole_economic.py",
                "impact_oracle": {"measured": True},
            }
        },
        invariant_violations=[InvariantViolation("bridge_accounting", "Bridge accounting", "locked", "released")],
        reproduction_steps=[ReproductionStep("fork", "attacker", {})],
        evidence_grade=4,
        reproduction_tier="fork_reproduced",
        fork_reproduced=True,
        deployed_viable=True,
        catalog_analogue=False,
        fork_evidence=fork_evidence,
    )


def test_bridge_accounting_violation_cases():
    assert bridge_accounting_violation({"released_amount": 10, "locked_amount": 5})
    assert bridge_accounting_violation({"released_amount": 10, "locked_amount": 10, "message_replay_count": 2})
    assert bridge_accounting_violation({"released_amount": 10, "locked_amount": 10, "unauthorized_emitter": True})
    assert not bridge_accounting_violation({"released_amount": 10, "locked_amount": 10})


def test_wormhole_economic_impact_verified_markers():
    assert wormhole_economic_impact_verified({"token_delta": 1})
    assert wormhole_economic_impact_verified({"tvs_at_risk_usd": 1000})
    assert not wormhole_economic_impact_verified({"token_delta": 1, "harness_auth_mocked": True})
    assert not wormhole_economic_impact_verified({"triage_surface_verified": True})


def test_wormhole_artifact_writers(tmp_path: Path):
    candidate = _candidate()
    fixture = write_message_fixture(candidate, tmp_path / "fixtures")
    poc = generated_wormhole_poc(candidate, tmp_path / "foundry")
    assert fixture.is_file()
    assert poc.is_file()
    assert "TOKEN_DELTA" in poc.read_text()


def test_qualifies_for_submission_blocks_wormhole_triage_only():
    finding = _wormhole_finding(
        {
            "method": "evm_fork",
            "target_id": "wormhole-token-bridge-ethereum",
            "triage_surface_verified": True,
            "balance_verified": True,
            "balance_delta_wei": 0,
        }
    )
    score = SimpleNamespace(submission_recommendation="submit_now")
    assert qualifies_for_submission(finding, score) is False


def test_qualifies_for_submission_allows_wormhole_measured_delta():
    finding = _wormhole_finding(
        {
            "method": "evm_fork",
            "target_id": "wormhole-token-bridge-ethereum",
            "triage_surface_verified": True,
            "balance_verified": True,
            "balance_delta_wei": 10**18,
        }
    )
    score = SimpleNamespace(submission_recommendation="submit_now")
    assert qualifies_for_submission(finding, score) is True
