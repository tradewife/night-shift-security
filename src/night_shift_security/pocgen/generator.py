"""Generate fail-closed PoC verifier artifacts from concrete candidates."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from night_shift_security.semantic.candidates import ConcreteCandidate


def _safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", value)
    if not cleaned or cleaned[0].isdigit():
        cleaned = f"Candidate_{cleaned}"
    return cleaned


def _solidity_test(candidate: ConcreteCandidate) -> str:
    cid = candidate.candidate_id
    test_name = _safe_name(f"test_{candidate.target_slug}_{cid.replace('-', '_')}")
    entry = candidate.entrypoint
    invariant = candidate.invariant
    source = candidate.source_ref
    return f"""// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;

import "forge-std/Test.sol";

contract Generated_{_safe_name(candidate.target_slug)}_{_safe_name(cid[:8])} is Test {{
    string constant CANDIDATE_ID = "{cid}";
    string constant TARGET_SLUG = "{candidate.target_slug}";
    string constant ENTRYPOINT = "{entry.get('name', '')}";
    string constant INVARIANT_ID = "{invariant.get('id', '')}";
    string constant SOURCE_FILE = "{source.get('file', '')}";

    function {test_name}() public {{
        emit log_string(string.concat("CANDIDATE_ID:", CANDIDATE_ID));
        emit log_string(string.concat("TARGET_SLUG:", TARGET_SLUG));
        emit log_string(string.concat("ENTRYPOINT:", ENTRYPOINT));
        emit log_string(string.concat("INVARIANT_ID:", INVARIANT_ID));
        emit log_named_uint("DELTA_WEI", 0);
        emit log_named_uint("TOKEN_DELTA", 0);
        fail("candidate-specific bindings required before this verifier can prove impact");
    }}
}}
"""


def _solana_test(candidate: ConcreteCandidate) -> str:
    payload = json.dumps(candidate.to_dict(), indent=2, sort_keys=True)
    return f'''"""Generated fail-closed Solana verifier for {candidate.candidate_id}."""

import json


CANDIDATE = json.loads("""{payload.replace(chr(34), chr(92) + chr(34))}""")


def test_candidate_requires_real_bindings():
    print("CANDIDATE_ID:", CANDIDATE["candidate_id"])
    print("TARGET_SLUG:", CANDIDATE["target_slug"])
    print("MEASURED_DELTA_LAMPORTS:0")
    assert CANDIDATE["entrypoint"].get("selector_or_discriminator")
    raise AssertionError("candidate-specific account bindings required before impact proof")
'''


def generate_poc_for_candidate(
    candidate: ConcreteCandidate,
    *,
    foundry_root: Path = Path("foundry/generated"),
    solana_root: Path = Path("solana/generated"),
) -> dict[str, Any]:
    if candidate.chain == "solana":
        out_dir = solana_root / candidate.target_slug
        out_dir.mkdir(parents=True, exist_ok=True)
        test_path = out_dir / f"{candidate.candidate_id}_test.py"
        accounts_path = out_dir / f"{candidate.candidate_id}_accounts.json"
        test_path.write_text(_solana_test(candidate))
        accounts_path.write_text(json.dumps(candidate.state_bindings, indent=2, sort_keys=True) + "\n")
        return {
            "candidate_id": candidate.candidate_id,
            "kind": "solana_validator_test",
            "path": str(test_path),
            "accounts": str(accounts_path),
            "fail_closed": True,
        }

    out_dir = foundry_root / candidate.target_slug
    out_dir.mkdir(parents=True, exist_ok=True)
    test_path = out_dir / f"{candidate.candidate_id}.t.sol"
    test_path.write_text(_solidity_test(candidate))
    return {
        "candidate_id": candidate.candidate_id,
        "kind": "foundry_test",
        "path": str(test_path),
        "fail_closed": True,
    }
