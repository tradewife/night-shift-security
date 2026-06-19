"""Kamino KLend account + instruction bindings for candidate-specific PoCs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from night_shift_security.native import kamino as kamino_harness
from night_shift_security.semantic.candidates import ConcreteCandidate


def resolve_kamino_bindings(candidate: ConcreteCandidate) -> dict[str, Any]:
    """Merge candidate state_bindings with native harness defaults."""
    accounts = kamino_harness.load_accounts()
    market_pubkey = str(
        candidate.state_bindings.get("market_hint")
        or accounts.get("market_pubkey")
        or kamino_harness.DEFAULT_MARKET_PUBKEY
    )
    reserve_entry = (accounts.get("reserves") or {}).get("USDC") or {}
    reserve_pubkey = str(
        candidate.state_bindings.get("reserve_pubkey")
        or reserve_entry.get("pubkey")
        or kamino_harness.DEFAULT_USDC_RESERVE
    )
    entry = candidate.entrypoint
    instruction = str(entry.get("name") or "")
    discriminator = str(
        entry.get("selector_or_discriminator")
        or entry.get("discriminator")
        or kamino_harness.discriminators().get(instruction, "")
    )
    program_id = str(entry.get("program_id") or kamino_harness.KLEND_PROGRAM)
    source = candidate.source_ref
    return {
        "candidate_id": candidate.candidate_id,
        "target_slug": candidate.target_slug,
        "program_id": program_id,
        "instruction": instruction,
        "discriminator": discriminator,
        "market_pubkey": market_pubkey,
        "reserve_pubkey": reserve_pubkey,
        "supply_vault": str(
            candidate.state_bindings.get("supply_vault")
            or reserve_entry.get("supply_vault")
            or ""
        ),
        "mint": str(
            candidate.state_bindings.get("mint")
            or reserve_entry.get("mint")
            or kamino_harness.DEFAULT_USDC_MINT
        ),
        "source_ref": {
            "commit": str(source.get("commit") or ""),
            "module": str(source.get("module") or source.get("repo") or ""),
            "file": str(source.get("file") or entry.get("file") or ""),
            "symbol": str(source.get("symbol") or instruction),
        },
        "impact_oracle": {
            "kind": "solana_measured_oracle",
            "path": "data/security_results/impact/kamino_measured_delta.json",
            "fee_only_rejects": True,
        },
        "invariant_id": str(candidate.invariant.get("id") or ""),
    }


def bindings_complete(bindings: dict[str, Any]) -> bool:
    required = ("program_id", "discriminator", "market_pubkey", "reserve_pubkey", "source_ref")
    if not all(bindings.get(k) for k in required):
        return False
    commit = (bindings.get("source_ref") or {}).get("commit")
    return bool(commit)


def kamino_solana_test_source(bindings_path: Path) -> str:
    """Generate pytest source that asserts bindings then fail-closes on impact."""
    return f'''"""Generated Kamino candidate verifier — bindings real, impact fail-closed."""

import json
from pathlib import Path

BINDINGS_PATH = Path("{bindings_path}")
BINDINGS = json.loads(BINDINGS_PATH.read_text())


def test_kamino_candidate_bindings_present():
    assert BINDINGS["program_id"] == "KLend2g3cP87fffoy8q1mQqGKjrxjC8boSyAYavgmjD"
    assert BINDINGS["discriminator"].startswith("0x")
    assert len(BINDINGS["discriminator"]) == 18
    assert BINDINGS["market_pubkey"]
    assert BINDINGS["reserve_pubkey"]
    assert BINDINGS["source_ref"]["commit"]
    print("CANDIDATE_ID:", BINDINGS["candidate_id"])
    print("TARGET_SLUG:", BINDINGS["target_slug"])
    print("INSTRUCTION:", BINDINGS["instruction"])
    print("MEASURED_DELTA_LAMPORTS:0")
    raise AssertionError(
        "candidate-specific impact proof required — fee-only CPI does not qualify"
    )
'''