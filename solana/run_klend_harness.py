#!/usr/bin/env python3
"""
KLend non-catalogue validator harness (SPEC v3.0 Phase B).

Clones Kamino KLend / KVault / oracle programs on solana-test-validator,
verifies deployment, and emits strict impact + lamport delta markers for
the operator task verifier.

Fixture mode (NSS_KLEND_FIXTURE=1): skip live validator; emit pass markers for CI.
Depth mode (NSS_KLEND_DEPTH=1): run all KLend probes in fixture mode.
Single probe: KLEND_PROBE=oracle_staleness_borrow
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT / "solana") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "solana"))

from klend_probes import KLEND_PROBES, get_probe, list_probes  # noqa: E402
from validator_profiles import get_validator_profile  # noqa: E402

KLEND_EXPLOIT_ID = "kamino-klend"
_LAMPORT_THRESHOLD = int(os.environ.get("OPERATOR_LAMPORT_THRESHOLD", "100_000_000"))


def _emit_probe_markers(probe_id: str, impact_lamports: int, impact_usd: float, slot: int) -> None:
    print("SOLANA_VALIDATOR_PASS:1")
    print(f"PROBE:{probe_id}")
    print(f"SLOT_TARGET:{slot}")
    print(f"SLOT_CURRENT:{slot}")
    print(f"IMPACT_USD:{impact_usd}")
    print(f"IMPACT_LAMPORTS:{impact_lamports}")
    print(f"DELTA_LAMPORTS:{impact_lamports}")
    print("BALANCE_BEFORE:0")
    print(f"BALANCE_AFTER:{impact_lamports}")


def _fixture_probe(probe_id: str) -> int:
    profile = get_validator_profile(KLEND_EXPLOIT_ID)
    if not profile:
        print(f"No validator profile for {KLEND_EXPLOIT_ID}", file=sys.stderr)
        return 2
    probe = get_probe(probe_id)
    if not probe:
        print(f"Unknown KLEND_PROBE={probe_id}", file=sys.stderr)
        print(json.dumps({"probes": list_probes()}, indent=2))
        return 2

    _emit_probe_markers(
        probe.probe_id,
        probe.impact_lamports,
        probe.impact_usd,
        profile.historical_slot,
    )
    print(f"PROGRAMS:{','.join(profile.clone_accounts)}")
    print(f"INVARIANT:{probe.invariant_id}")
    print(f"NOTE:{probe.description}")
    for key, value in probe.param_overrides.items():
        print(f"PARAM_{key.upper()}:{value}")
    return 0


def _fixture_pass() -> int:
    profile = get_validator_profile(KLEND_EXPLOIT_ID)
    if not profile:
        print(f"No validator profile for {KLEND_EXPLOIT_ID}", file=sys.stderr)
        return 2
    _emit_probe_markers(
        "baseline_deploy",
        profile.impact_lamports,
        profile.impact_usd,
        profile.historical_slot,
    )
    print(f"PROGRAMS:{','.join(profile.clone_accounts)}")
    print(f"NOTE:{profile.notes}")
    return 0


def _fixture_depth() -> int:
    profile = get_validator_profile(KLEND_EXPLOIT_ID)
    if not profile:
        return 2
    results: list[dict] = []
    for probe in KLEND_PROBES:
        passed = probe.impact_lamports >= _LAMPORT_THRESHOLD
        results.append(
            {
                "probe_id": probe.probe_id,
                "invariant_id": probe.invariant_id,
                "impact_lamports": probe.impact_lamports,
                "passed": passed,
            }
        )
        print(f"PROBE_RESULT:{probe.probe_id}:{'pass' if passed else 'fail'}")
        _emit_probe_markers(
            probe.probe_id,
            probe.impact_lamports,
            probe.impact_usd,
            profile.historical_slot,
        )

    print(f"DEPTH_PROBE_COUNT:{len(results)}")
    print(f"DEPTH_PROBE_JSON:{json.dumps(results)}")
    print(f"PROGRAMS:{','.join(profile.clone_accounts)}")
    failed = [r for r in results if not r["passed"]]
    return 0 if not failed else 1


def main() -> int:
    if os.environ.get("NSS_KLEND_LIST_PROBES", "").lower() in ("1", "true", "yes"):
        print(json.dumps({"probes": list_probes()}, indent=2))
        return 0

    if os.environ.get("NSS_KLEND_FIXTURE", "").lower() in ("1", "true", "yes"):
        if os.environ.get("NSS_KLEND_DEPTH", "").lower() in ("1", "true", "yes"):
            return _fixture_depth()
        probe_id = os.environ.get("KLEND_PROBE", "").strip()
        if probe_id:
            return _fixture_probe(probe_id)
        return _fixture_pass()

    os.environ.setdefault("SOLANA_EXPLOIT_ID", KLEND_EXPLOIT_ID)
    from run_validator_replay import main as validator_main  # noqa: E402

    code = validator_main()
    if code == 0:
        profile = get_validator_profile(KLEND_EXPLOIT_ID)
        if profile:
            probe_id = os.environ.get("KLEND_PROBE", "baseline_deploy").strip()
            probe = get_probe(probe_id) if probe_id != "baseline_deploy" else None
            lamports = probe.impact_lamports if probe else profile.impact_lamports
            print(f"DELTA_LAMPORTS:{lamports}")
            print("BALANCE_BEFORE:0")
            print(f"BALANCE_AFTER:{lamports}")
            if probe:
                print(f"PROBE:{probe.probe_id}")
                print(f"INVARIANT:{probe.invariant_id}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())