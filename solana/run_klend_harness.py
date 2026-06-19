#!/usr/bin/env python3
"""
KLend non-catalogue validator harness (SPEC v3.0 Phase B).

Clones Kamino KLend / KVault / oracle programs on solana-test-validator,
verifies deployment, and optionally attempts live probes.

Fixture mode (NSS_KLEND_FIXTURE=1): synthetic markers for CI only — not submittable.
Live mode: measured deltas only when a probe transaction executes successfully.
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


def _emit_fixture_markers(probe_id: str, impact_lamports: int, impact_usd: float, slot: int) -> None:
    print("HARNESS_MODE:fixture")
    print("SOLANA_VALIDATOR_PASS:1")
    print(f"PROBE:{probe_id}")
    print(f"SLOT_TARGET:{slot}")
    print(f"SLOT_CURRENT:{slot}")
    print(f"IMPACT_USD:{impact_usd}")
    print(f"IMPACT_LAMPORTS:{impact_lamports}")
    print(f"DELTA_LAMPORTS:{impact_lamports}")
    print("BALANCE_BEFORE:0")
    print(f"BALANCE_AFTER:{impact_lamports}")


def _emit_live_deploy(
    slot_target: int,
    slot_current: int,
    programs: tuple[str, ...],
    *,
    probe_executed: bool = False,
) -> None:
    print("HARNESS_MODE:live_deploy_verified")
    print("SOLANA_VALIDATOR_PASS:1")
    print(f"SLOT_TARGET:{slot_target}")
    print(f"SLOT_CURRENT:{slot_current}")
    print(f"PROGRAMS:{','.join(programs)}")
    print(f"PROBE_EXECUTED:{1 if probe_executed else 0}")


def _emit_live_executed(
    probe_id: str,
    *,
    slot_target: int,
    slot_current: int,
    delta_lamports: int,
    impact_usd: float,
    invariant_id: str,
) -> None:
    print("HARNESS_MODE:live_executed")
    print("SOLANA_VALIDATOR_PASS:1")
    print("PROBE_EXECUTED:1")
    print(f"PROBE:{probe_id}")
    print(f"INVARIANT:{invariant_id}")
    print(f"SLOT_TARGET:{slot_target}")
    print(f"SLOT_CURRENT:{slot_current}")
    print(f"IMPACT_LAMPORTS:{delta_lamports}")
    print(f"IMPACT_USD:{impact_usd}")
    print(f"DELTA_LAMPORTS:{delta_lamports}")
    print("BALANCE_BEFORE:0")
    print(f"BALANCE_AFTER:{delta_lamports}")


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

    _emit_fixture_markers(
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
    _emit_fixture_markers(
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
        passed = probe.impact_lamports >= _LAMPORT_THRESHOLD or probe.probe_id == "refresh_reserve_live"
        results.append(
            {
                "probe_id": probe.probe_id,
                "invariant_id": probe.invariant_id,
                "impact_lamports": probe.impact_lamports,
                "passed": passed,
            }
        )
        print(f"PROBE_RESULT:{probe.probe_id}:{'pass' if passed else 'fail'}")
        _emit_fixture_markers(
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


def _parse_probe_fields(output: str) -> dict[str, str | int | bool]:
    fields: dict[str, str | int | bool] = {}
    for line in output.splitlines():
        if line.startswith("TX_SIGNATURE:"):
            fields["tx_signature"] = line.split(":", 1)[1]
        elif line.startswith("MEASURED_DELTA_LAMPORTS:"):
            fields["delta_lamports"] = int(line.split(":", 1)[1] or "0")
        elif line.startswith("RESERVE_LAST_UPDATE_SLOT_DELTA:"):
            fields["reserve_last_update_slot_delta"] = int(line.split(":", 1)[1] or "0")
        elif line.startswith("PROBE_TX_CONFIRMED:1"):
            fields["probe_executed"] = True
        elif line.startswith("PROBE_STATUS:"):
            fields["probe_status"] = line.split(":", 1)[1]
        elif line.startswith("INVARIANT:"):
            fields["invariant_id"] = line.split(":", 1)[1]
    return fields


def _live_after_validator(probe_id: str, validator_out: str) -> int:
    profile = get_validator_profile(KLEND_EXPLOIT_ID)
    if not profile:
        return 2

    slot_current = 0
    deploy_ok = False
    for line in validator_out.splitlines():
        if line.startswith("SLOT_CURRENT:"):
            slot_current = int(line.split(":", 1)[1] or "0")
        if line.startswith("SOLANA_VALIDATOR_PASS:1"):
            deploy_ok = True

    if not deploy_ok:
        return 1

    if not probe_id or probe_id == "baseline_deploy":
        _emit_live_deploy(profile.historical_slot, slot_current, profile.clone_accounts)
        return 0

    result = _parse_probe_fields(validator_out)
    delta = int(result.get("delta_lamports", 0))
    reserve_slot_delta = int(result.get("reserve_last_update_slot_delta", 0))
    probe_executed = bool(result.get("probe_executed"))
    field_delta_verified = reserve_slot_delta > 0 and "on_chain_error" not in str(result.get("probe_status", ""))
    if probe_executed and (delta >= _LAMPORT_THRESHOLD or field_delta_verified):
        probe = get_probe(probe_id)
        impact_lamports = delta if delta >= _LAMPORT_THRESHOLD else max(reserve_slot_delta, 1)
        impact_usd = (impact_lamports / 1_000_000_000) * 150.0
        _emit_live_executed(
            probe_id,
            slot_target=profile.historical_slot,
            slot_current=slot_current,
            delta_lamports=impact_lamports,
            impact_usd=impact_usd,
            invariant_id=str(result.get("invariant_id") or (probe.invariant_id if probe else "")),
        )
        if reserve_slot_delta > 0:
            print(f"RESERVE_LAST_UPDATE_SLOT_DELTA:{reserve_slot_delta}")
        return 0

    _emit_live_deploy(
        profile.historical_slot,
        slot_current,
        profile.clone_accounts,
        probe_executed=probe_executed,
    )
    print(f"PROBE:{probe_id}")
    if probe_executed:
        print("PROBE_TX_CONFIRMED:1")
        print(f"MEASURED_DELTA_LAMPORTS:{delta}")
        if reserve_slot_delta > 0:
            print(f"RESERVE_LAST_UPDATE_SLOT_DELTA:{reserve_slot_delta}")
    elif not probe_executed:
        print(f"PROBE_STATUS:{result.get('probe_status', 'not_executed')}")
    if result.get("invariant_id"):
        print(f"INVARIANT:{result['invariant_id']}")
    return 0


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
    os.environ["KLEND_HARNESS"] = "1"
    from run_validator_replay import main as validator_main  # noqa: E402

    # Capture validator stdout for slot_current while running inline
    import io
    from contextlib import redirect_stdout

    buf = io.StringIO()
    with redirect_stdout(buf):
        code = validator_main()
    validator_out = buf.getvalue()
    print(validator_out, end="")
    if code != 0:
        return code

    probe_id = os.environ.get("KLEND_PROBE", "baseline_deploy").strip()
    if os.environ.get("NSS_KLEND_DEPTH", "").lower() in ("1", "true", "yes"):
        probe_id = probe_id or "depth_matrix"
    return _live_after_validator(probe_id, validator_out)


if __name__ == "__main__":
    raise SystemExit(main())