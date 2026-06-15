"""Tests for candidate-specific PoC generation."""

from __future__ import annotations

from pathlib import Path

from night_shift_security.pocgen import generate_poc_for_candidate
from night_shift_security.semantic.candidates import ConcreteCandidate


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
    result = generate_poc_for_candidate(_candidate("solana"), solana_root=tmp_path / "solana")
    path = Path(result["path"])
    accounts = Path(result["accounts"])
    assert path.is_file()
    assert accounts.is_file()
    assert "MEASURED_DELTA_LAMPORTS:0" in path.read_text()
    assert result["fail_closed"] is True
