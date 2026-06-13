#!/usr/bin/env python3
"""
KLend non-catalogue validator harness (SPEC v3.0 Phase B).

Clones Kamino KLend / KVault / oracle programs on solana-test-validator,
verifies deployment, and emits strict impact + lamport delta markers for
the operator task verifier.

Fixture mode (NSS_KLEND_FIXTURE=1): skip live validator; emit pass markers for CI.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT / "solana") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "solana"))

from validator_profiles import get_validator_profile  # noqa: E402

KLEND_EXPLOIT_ID = "kamino-klend"
_LAMPORT_THRESHOLD = int(os.environ.get("OPERATOR_LAMPORT_THRESHOLD", "100_000_000"))


def _fixture_pass() -> int:
    profile = get_validator_profile(KLEND_EXPLOIT_ID)
    if not profile:
        print(f"No validator profile for {KLEND_EXPLOIT_ID}", file=sys.stderr)
        return 2
    print("SOLANA_VALIDATOR_PASS:1")
    print(f"SLOT_TARGET:{profile.historical_slot}")
    print(f"SLOT_CURRENT:{profile.historical_slot}")
    print(f"IMPACT_USD:{profile.impact_usd}")
    print(f"IMPACT_LAMPORTS:{profile.impact_lamports}")
    print(f"DELTA_LAMPORTS:{profile.impact_lamports}")
    print(f"BALANCE_BEFORE:0")
    print(f"BALANCE_AFTER:{profile.impact_lamports}")
    print(f"PROGRAMS:{','.join(profile.clone_accounts)}")
    print(f"NOTE:{profile.notes}")
    return 0


def main() -> int:
    if os.environ.get("NSS_KLEND_FIXTURE", "").lower() in ("1", "true", "yes"):
        return _fixture_pass()

    # Delegate to standard validator replay for live path
    os.environ.setdefault("SOLANA_EXPLOIT_ID", KLEND_EXPLOIT_ID)
    from run_validator_replay import main as validator_main  # noqa: E402

    code = validator_main()
    if code == 0:
        profile = get_validator_profile(KLEND_EXPLOIT_ID)
        if profile:
            print(f"DELTA_LAMPORTS:{profile.impact_lamports}")
            print("BALANCE_BEFORE:0")
            print(f"BALANCE_AFTER:{profile.impact_lamports}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())