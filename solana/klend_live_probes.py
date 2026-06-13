"""Live KLend probe attempts on a local validator — measured deltas only."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from klend_probes import KLEND_PROGRAM, KVAULT_PROGRAM, ORACLE_PROGRAM, get_probe

LOCAL_RPC = os.environ.get("SOLANA_VALIDATOR_RPC", "http://127.0.0.1:8899")


def _rpc(method: str, params: list | None = None, *, url: str = LOCAL_RPC) -> Any:
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = json.loads(resp.read().decode())
    if "error" in body:
        raise RuntimeError(f"RPC {method} failed: {body['error']}")
    return body["result"]


def _program_deployed(pubkey: str) -> bool:
    result = _rpc("getAccountInfo", [pubkey, {"encoding": "base64"}])
    value = result.get("value")
    if not value:
        return False
    return bool(value.get("executable"))


def attempt_live_probe(probe_id: str) -> dict[str, Any]:
    """
    Attempt a probe against cloned KLend programs on the local validator.

    Returns measured fields only — no hardcoded impact. A probe succeeds only when
    a real transaction produces a lamport delta above threshold.
    """
    probe = get_probe(probe_id)
    if not probe:
        return {
            "probe_id": probe_id,
            "probe_executed": False,
            "error": "unknown_probe",
            "delta_lamports": 0,
        }

    try:
        for program in (KLEND_PROGRAM, KVAULT_PROGRAM, ORACLE_PROGRAM):
            if not _program_deployed(program):
                return {
                    "probe_id": probe_id,
                    "probe_executed": False,
                    "error": f"program_not_deployed:{program}",
                    "delta_lamports": 0,
                }
    except (urllib.error.URLError, TimeoutError, OSError, RuntimeError) as exc:
        return {
            "probe_id": probe_id,
            "probe_executed": False,
            "error": str(exc),
            "delta_lamports": 0,
        }

    # No KLend CPI PoC wired yet — deploy verified, exploit tx not executed.
    return {
        "probe_id": probe_id,
        "probe_executed": False,
        "error": "probe_tx_not_implemented",
        "delta_lamports": 0,
        "programs_verified": [KLEND_PROGRAM, KVAULT_PROGRAM, ORACLE_PROGRAM],
        "invariant_id": probe.invariant_id,
    }