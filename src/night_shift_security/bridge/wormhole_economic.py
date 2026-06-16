"""Wormhole economic-impact invariants and artifacts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from night_shift_security.semantic.candidates import ConcreteCandidate

WORMHOLE_DIR = Path("data/security_results/wormhole")
MESSAGE_FIXTURE_DIR = WORMHOLE_DIR / "message_fixtures"
ECONOMIC_DELTAS_PATH = WORMHOLE_DIR / "economic_deltas.jsonl"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def bridge_accounting_violation(record: dict[str, Any]) -> bool:
    """True only when release/mint exceeds authorized source lock/burn."""
    released = int(record.get("released_amount") or record.get("minted_amount") or 0)
    authorized = int(record.get("locked_amount") or record.get("burned_amount") or 0)
    replay_count = int(record.get("message_replay_count") or 0)
    unauthorized = bool(record.get("unauthorized_emitter") or record.get("invalid_quorum"))
    if released <= 0:
        return False
    if replay_count > 1:
        return True
    if unauthorized:
        return True
    return released > authorized


def wormhole_economic_impact_verified(evidence: dict[str, Any]) -> bool:
    if not evidence:
        return False
    if bool(evidence.get("harness_auth_mocked")):
        return False
    if bool(evidence.get("authorized_replay")) and not bool(evidence.get("bridge_accounting_violation")):
        return False
    if bool(evidence.get("economic_impact_proven")):
        return True
    if int(evidence.get("balance_delta_wei") or 0) > 0:
        return True
    if int(evidence.get("token_delta") or evidence.get("token_delta_units") or 0) > 0:
        return True
    if float(evidence.get("tvs_at_risk_usd") or 0.0) > 0:
        return True
    if bool(evidence.get("bridge_accounting_violation")):
        return True
    return bridge_accounting_violation(evidence)


def write_message_fixture(candidate: ConcreteCandidate, out_dir: Path = MESSAGE_FIXTURE_DIR) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{candidate.candidate_id}.json"
    payload = {
        "schema_version": 1,
        "generated_at": _utc_now(),
        "candidate_id": candidate.candidate_id,
        "target_slug": candidate.target_slug,
        "entrypoint": candidate.entrypoint,
        "invariant": candidate.invariant,
        "sequence": candidate.sequence,
        "message": {
            "emitter_chain": "",
            "emitter_address": "",
            "sequence": "",
            "payload_hash": "",
        },
        "expected_impact": candidate.impact_oracle,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def append_economic_delta(record: dict[str, Any], path: Path = ECONOMIC_DELTAS_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(record)
    payload.setdefault("recorded_at", _utc_now())
    payload["economic_impact_verified"] = wormhole_economic_impact_verified(payload)
    with path.open("a") as fh:
        fh.write(json.dumps(payload, sort_keys=True) + "\n")
    return path


def generated_wormhole_poc(candidate: ConcreteCandidate, out_dir: Path = Path("foundry/generated/wormhole")) -> Path:
    """Generate a Wormhole-specific fail-closed economic assertion test."""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{candidate.candidate_id}.t.sol"
    path.write_text(
        f"""// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;

import "forge-std/Test.sol";

contract WormholeEconomic_{candidate.candidate_id.replace('-', '_')[:16]} is Test {{
    string constant CANDIDATE_ID = "{candidate.candidate_id}";
    string constant ENTRYPOINT = "{candidate.entrypoint.get('name', '')}";

    function testBridgeAccountingRequiresMeasuredImpact() public {{
        emit log_string(string.concat("CANDIDATE_ID:", CANDIDATE_ID));
        emit log_string(string.concat("ENTRYPOINT:", ENTRYPOINT));
        emit log_named_uint("TOKEN_DELTA", 0);
        emit log_named_uint("TVS_AT_RISK", 0);
        fail("Wormhole grade 4 requires token/native delta, accounting violation, or bounded TVS");
    }}
}}
"""
    )
    return path
