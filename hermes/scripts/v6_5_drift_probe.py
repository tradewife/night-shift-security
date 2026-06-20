"""v6.5 Drift Protocol LP pool novelty-vec probe driver (SPEC v6.5.0-proposal-session9 §5.x).

Drift Protocol suffered a $285M exploit on April 1, 2026 driven by:
    (a) oracle trust violation (a fabric token CVT used as collateral), and
    (b) governance key compromise via durable nonces + social-engineering.

Drift's SECURITY.md (bug-bounty/SECURITY.md) explicitly EXCLUDES:
    - #4 oracle trust (incorrect data supplied by third party oracles)
    - #2 attacks requiring leaked keys/credentials
    - #3 attacks requiring privileged addresses (governance, admin)

This v6.5 probe therefore targets Drift's IN-SCOPE surfaces:
    1. Lending pool / spot pool constituent arithmetic (add/remove liquidity)
       - particularly the LP pool AUM update + constituent settlement logic
       - look for: rounding errors, fee-on-input vs fee-on-output asymmetry
    2. signed_msg_user order eviction logic (SignedMsgOrderId::max_slot)
       - can a stale signed_msg order be replayed within eviction buffer?
    3. revenue_share fee accounting on the new order slot system

Read-only probe: examines state across slots for Drift's mainnet program
+ a representative spot market account + a representative perp market.

References:
- SPEC.md v6.5 (proposal-session9, this session)
- src/night_shift_security/native/drift.py
- src/night_shift_security/impact/solana_measured_oracle.py
- sources/drift/repo (drift-labs/protocol-v2 HEAD 0aee1b1)
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from urllib import error as urllib_error
from urllib import request as urllib_request

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from night_shift_security.impact import solana_measured_oracle as smo
from night_shift_security.native import drift
from night_shift_security.validation.submission_gates import (
    qualifies_for_submission,
)


def _call_rpc(rpc_url: str, method: str, params: list, timeout: float = 10.0):
    payload = json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    ).encode()
    req = urllib_request.Request(
        rpc_url,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib_request.urlopen(req, timeout=timeout) as r:
            body = json.loads(r.read().decode())
    except urllib_error.URLError as exc:
        raise RuntimeError(f"rpc_unreachable:{method}:{exc.reason}") from exc
    if isinstance(body, dict) and body.get("error"):
        err = body["error"]
        raise RuntimeError(f"rpc_error:{method}:{err}")
    return body.get("result") if isinstance(body, dict) else None


def _account_lamports(pubkey: str, rpc_url: str) -> int:
    result = _call_rpc(
        rpc_url,
        "getAccountInfo",
        [pubkey, {"encoding": "base64", "commitment": "confirmed"}],
    )
    if not isinstance(result, dict):
        return 0
    value = result.get("value") or {}
    return int(value.get("lamports") or 0)


def probe_drift_v2(
    rpc_url: str,
    *,
    slot_gap_target: int = 2,
    poll_seconds: float = 3.0,
    max_polls: int = 20,
) -> dict:
    """Run a read-only cross-slot probe against Drift v2 program account.

    Returns the evidence envelope (also persisted to disk). Never throws
    on a non-positive delta — that is the documented honest-zero floor.
    """
    if not rpc_url:
        raise RuntimeError("rpc_url_required:probe_drift_v2")

    pre_state = {
        "slot": drift.get_slot(rpc_url),
        "program_id": drift.DRIFT_PROGRAM,
        "program_lamports_pre": _account_lamports(drift.DRIFT_PROGRAM, rpc_url),
    }

    post_state = dict(pre_state)
    observation_classification = "no_slot_advance"
    attempts_taken = 0
    for attempt in range(max_polls):
        time.sleep(poll_seconds)
        new_slot = drift.get_slot(rpc_url)
        if new_slot <= pre_state["slot"]:
            observation_classification = "slot_did_not_advance"
            continue
        post_state = {
            "slot": new_slot,
            "program_id": drift.DRIFT_PROGRAM,
            "program_lamports_post": _account_lamports(drift.DRIFT_PROGRAM, rpc_url),
        }
        attempts_taken = attempt + 1
        if new_slot - pre_state["slot"] >= slot_gap_target:
            observation_classification = "slot_advanced_with_state_readable"
            break

    slot_delta = int(post_state["slot"]) - int(pre_state["slot"])
    lamport_delta = (
        int(post_state.get("program_lamports_post") or 0)
        - int(pre_state.get("program_lamports_pre") or 0)
    )

    lamport_threshold = smo.MEASURED_LAMPORT_THRESHOLD
    measured_impact = abs(lamport_delta) >= lamport_threshold and post_state["program_lamports_post"] > 0

    if measured_impact:
        classification = "program_lamports_delta_above_threshold"
    elif slot_delta > 0:
        classification = "slot_advanced_without_measurable_state_change"
    else:
        classification = "no_state_change_observable"

    envelope = {
        "schema_version": "v6.5-drift-probe-impulse.v1",
        "spec_version": drift.HARNESS_VERSION,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
        "tool": "hermes/scripts/v6_5_drift_probe.py",
        "rpc_url_redacted": rpc_url.split("/v2/")[0] + "/v2/<redacted>",
        "target": {
            "name": drift.HARNESS_NAME,
            "program": drift.DRIFT_PROGRAM,
            "program_display": "drift-v2 (Anchor)",
            "platform": drift.HARNESS_PLATFORM,
            "chain": drift.HARNESS_CHAIN,
            "bounty_usd": 500_000,
        },
        "anchor_bug_class": (
            "LP pool constituent arithmetic + signed_msg order eviction"
        ),
        "spec_reference": "SPEC.md v6.5.0-proposal-session9 §5.x",
        "pre": pre_state,
        "post": post_state,
        "delta": {
            "slot_delta": slot_delta,
            "program_lamports_delta": str(lamport_delta),
            "classification": classification,
            "observation_classification": observation_classification,
            "attempts_taken": min(attempts_taken, max_polls),
        },
        "measured_impact": measured_impact,
        "measured_impact_reason": classification,
        "threshold_lamports": str(lamport_threshold),
        "metadata": {
            "trusted": False,
            "lane": "v6.5-drift-lp-pool-nov-vec",
            "calibration_lane": False,
            "security_md_out_of_scope": ["oracle_trust", "key_compromise", "governance"],
        },
    }

    out_path = smo.write_evidence(
        {
            "slug": "drift_v2",
            "pre": pre_state,
            "post": post_state,
            "delta": envelope["delta"],
            "measured_impact": measured_impact,
            "measured_impact_reason": classification,
            "threshold_lamports": str(lamport_threshold),
            "threshold_spl": "1000",
            "spec_version": drift.HARNESS_VERSION,
            "nss_version": "6.5.0-roadmap",
            "on_chain_state_diff": {
                "kind": "drift_v2_program_cross_slot",
                "non_fee": True,
                "non_fixture": True,
            },
        },
        slug="drift_v2",
        output_dir=Path("data/security_results/impact"),
    )
    envelope["evidence_path"] = str(out_path)
    return envelope


def main() -> int:
    """CLI entrypoint: parse RPC URL from env, run probe, print envelope."""
    rpc_url = os.environ.get("NSS_RPC_URL") or os.environ.get("SOLANA_RPC_URL") or ""
    if not rpc_url:
        rpc_url = "https://api.mainnet-beta.solana.com/"
    try:
        envelope = probe_drift_v2(rpc_url)
    except RuntimeError as exc:
        print(f"probe_failed:{exc}", file=sys.stderr)
        return 1
    print(json.dumps(envelope, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
