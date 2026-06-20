"""v6.2 MarginFi novel-vec probe driver (SPEC v6.2.0-proposal-session6 §5.2).

Reads cross-slot Solana state for a Marginfi v2 USDC bank and the bank's
liquidity-vault token account, classifies measured impact via the existing
``solana_measured_oracle`` (the same substrate used by Kamino), and writes
the evidence envelope + gate-trace JSON for downstream ``qualifies_for_submission()``.

This is read-only. No transaction broadcast.

References:
- SPEC.md v6.2 §5.2 probe driver
- src/night_shift_security/native/marginfi.py
- src/night_shift_security/impact/solana_measured_oracle.py
- src/night_shift_security/validation/submission_gates.py
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
from night_shift_security.native import marginfi
from night_shift_security.validation.submission_gates import (
    _candidate_payload,
    _v4_candidate_submission_ok,
    _wormhole_submission_ok,
    qualifies_for_submission,
)


def _call_rpc(rpc_url: str, method: str, params: list, timeout: float = 15.0):
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
        raise RuntimeError(
            f"rpc_error:{method}:{err.get('code')}:{err.get('message')}"
        )
    return body.get("result") if isinstance(body, dict) else None


def _token_balance(pubkey: str, rpc_url: str) -> dict:
    result = _call_rpc(
        rpc_url, "getTokenAccountBalance", [pubkey]
    )
    value = (result or {}).get("value") if isinstance(result, dict) else {}
    return {
        "amount": str(value.get("amount") or "0"),
        "decimals": int(value.get("decimals") or 6),
        "mint": str(value.get("mint") or ""),
    }


def _account_lamports(pubkey: str, rpc_url: str) -> int:
    result = _call_rpc(
        rpc_url,
        "getAccountInfo",
        [pubkey, {"encoding": "base64", "commitment": "confirmed"}],
    )
    value = (result or {}).get("value") if isinstance(result, dict) else None
    if not value:
        return 0
    return int(value.get("lamports") or 0)


def probe_marginfi_v2(
    rpc_url: str,
    *,
    slot_gap_target: int = 2,
    poll_seconds: float = 3.0,
    max_polls: int = 30,
) -> dict:
    """Run a read-only cross-slot probe against Marginfi v2 USDC bank.

    Returns the evidence envelope (also persisted to disk). Never throws
    on a non-positive delta — that is the documented honest-zero floor.
    """
    if not rpc_url:
        raise RuntimeError("rpc_url_required:probe_marginfi_v2")

    sentinel_detected = any(
        v.startswith("PENDING_")
        for v in (
            marginfi.DEFAULT_MARGINFI_GROUP,
            marginfi.DEFAULT_USDC_BANK,
            marginfi.DEFAULT_USDC_LIQUIDITY_VAULT,
        )
    )

    # Lane A: confirm substrate reachable + record pre-state.
    pre_state = {
        "slot": marginfi.get_slot(rpc_url),
        "program_id": marginfi.MARGINFI_PROGRAM,
        "program_lamports_pre": _account_lamports(
            marginfi.MARGINFI_PROGRAM, rpc_url
        ),
        "liquidity_vault_lamports_pre": (
            _account_lamports(marginfi.DEFAULT_USDC_LIQUIDITY_VAULT, rpc_url)
            if not marginfi.DEFAULT_USDC_LIQUIDITY_VAULT.startswith("PENDING_")
            else -1
        ),
        "liquidity_vault_balance_pre": (
            _token_balance(marginfi.DEFAULT_USDC_LIQUIDITY_VAULT, rpc_url)
            if not marginfi.DEFAULT_USDC_LIQUIDITY_VAULT.startswith("PENDING_")
            else {"amount": "0", "decimals": 6, "mint": ""}
        ),
        "bank_account_present": False,
        "bank_account_data_len": 0,
        "sentinel_default_used": sentinel_detected,
    }
    if not marginfi.DEFAULT_USDC_BANK.startswith("PENDING_"):
        bank_info = _call_rpc(
            rpc_url,
            "getAccountInfo",
            [
                marginfi.DEFAULT_USDC_BANK,
                {"encoding": "base64", "commitment": "confirmed"},
            ],
        )
        bank_value = (bank_info or {}).get("value") if isinstance(bank_info, dict) else None
        if bank_value:
            pre_state["bank_account_present"] = True
            data_field = bank_value.get("data")
            if isinstance(data_field, list) and data_field:
                try:
                    import base64

                    pre_state["bank_account_data_len"] = len(
                        base64.b64decode(data_field[0])
                    )
                except (ValueError, TypeError):
                    pre_state["bank_account_data_len"] = 0
            pre_state["bank_account_owner"] = str(bank_value.get("owner") or "")

    # Lane B: poll until slot advances by slot_gap_target.
    post_state = dict(pre_state)
    observation_classification = "no_slot_advance"
    for attempt in range(max_polls):
        time.sleep(poll_seconds)
        new_slot = marginfi.get_slot(rpc_url)
        if new_slot <= pre_state["slot"]:
            observation_classification = "slot_did_not_advance"
            continue
        post_state = {
            "slot": new_slot,
            "program_id": marginfi.MARGINFI_PROGRAM,
            "program_lamports_post": _account_lamports(
                marginfi.MARGINFI_PROGRAM, rpc_url
            ),
            "liquidity_vault_lamports_post": (
                _account_lamports(marginfi.DEFAULT_USDC_LIQUIDITY_VAULT, rpc_url)
                if not marginfi.DEFAULT_USDC_LIQUIDITY_VAULT.startswith("PENDING_")
                else -1
            ),
            "liquidity_vault_balance_post": (
                _token_balance(marginfi.DEFAULT_USDC_LIQUIDITY_VAULT, rpc_url)
                if not marginfi.DEFAULT_USDC_LIQUIDITY_VAULT.startswith("PENDING_")
                else {"amount": "0", "decimals": 6, "mint": ""}
            ),
            "bank_account_present": pre_state["bank_account_present"],
            "bank_account_data_len": pre_state["bank_account_data_len"],
            "bank_account_owner": pre_state.get("bank_account_owner", ""),
            "sentinel_default_used": sentinel_detected,
        }
        if new_slot - pre_state["slot"] >= slot_gap_target:
            observation_classification = "slot_advanced_with_state_readable"
            break

    slot_delta = int(post_state["slot"]) - int(pre_state["slot"])
    pre_lamports = int(pre_state.get("liquidity_vault_lamports_pre") or 0)
    post_lamports = int(post_state.get("liquidity_vault_lamports_post") or 0)
    lamport_delta = post_lamports - pre_lamports

    pre_amount = int(pre_state["liquidity_vault_balance_pre"]["amount"])
    post_amount = int(post_state["liquidity_vault_balance_post"]["amount"])
    token_delta = post_amount - pre_amount

    spl_threshold = smo.MEASURED_SPL_THRESHOLD
    lamport_threshold = smo.MEASURED_LAMPORT_THRESHOLD
    measured_spl = (
        abs(token_delta) >= spl_threshold
        and not pre_state.get("liquidity_vault_balance_pre", {}).get("mint", "").startswith("PENDING_")
    )
    measured_lamport = (
        abs(lamport_delta) >= lamport_threshold
        and post_lamports > 0
    )

    if sentinel_detected:
        classification = "sentinel_defaults_unresolved_see_lab_notebook"
    elif measured_spl:
        classification = "liquidity_vault_spl_delta_above_threshold"
    elif measured_lamport:
        classification = "liquidity_vault_lamport_delta_above_threshold"
    elif slot_delta > 0:
        classification = "slot_advanced_without_measurable_state_change"
    else:
        classification = "no_state_change_observeable"

    measured_impact = (
        (measured_spl or measured_lamport)
        and not sentinel_detected
        and pre_state.get("bank_account_present", False)
    )

    envelope = {
        "schema_version": "v6.2-marginfi-probe-impulse.v1",
        "spec_version": "v6.2.0-proposal-session6",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
        "tool": "hermes/scripts/v6_2_marginfi_probe.py",
        "rpc_url_redacted": rpc_url.split("/v2/")[0] + "/v2/<redacted>",
        "target": {
            "name": "Marginfi v2 (USDC Bank)",
            "program": marginfi.MARGINFI_PROGRAM,
            "program_display": "marginfi-v2 (Anchor)",
            "platform": marginfi.HARNESS_PLATFORM,
            "chain": marginfi.HARNESS_CHAIN,
            "bounty_usd": 250_000,
            "marginfi_group": marginfi.DEFAULT_MARGINFI_GROUP,
            "bank_pubkey": marginfi.DEFAULT_USDC_BANK,
            "liquidity_vault": marginfi.DEFAULT_USDC_LIQUIDITY_VAULT,
        },
        "anchor_bug_class": (
            "stale-oracle-borrow composition (MAX_PRICE_AGE_SEC) — read-only probe"
        ),
        "spec_reference": "SPEC.md §5.2 v6.2.0-proposal-session6",
        "pre": pre_state,
        "post": post_state,
        "delta": {
            "slot_delta": slot_delta,
            "liquidity_vault_lamports_delta": str(lamport_delta),
            "liquidity_vault_token_delta": str(token_delta),
            "classification": classification,
            "observation_classification": observation_classification,
            "attempts_taken": min(attempt + 1, max_polls),
        },
        "measured_impact": measured_impact,
        "measured_impact_reason": classification,
        "threshold_spl_units": str(spl_threshold),
        "threshold_lamports": str(lamport_threshold),
        "metadata": {
            "trusted": False,
            "lane": "v6.2-novel-vec-probe",
            "calibration_lane": False,
            "single_target_discipline": True,
        },
    }

    out_path = smo.write_evidence(
        {
            "slug": "marginfi_v2",
            "pre": pre_state,
            "post": post_state,
            "delta": envelope["delta"],
            "measured_impact": measured_impact,
            "measured_impact_reason": classification,
            "threshold_lamports": str(lamport_threshold),
            "threshold_spl": str(spl_threshold),
            "spec_version": "v6.2.0-proposal-session6",
            "nss_version": "6.2.0-roadmap",
            "on_chain_state_diff": {
                "kind": "marginfi_v2_usdc_bank_cross_slot",
                "non_fee": True,
                "non_fixture": True,
            },
        },
        slug="marginfi_v2",
        output_dir=Path("data/security_results/impact"),
    )
    envelope["evidence_path"] = str(out_path)
    return envelope


def build_finding(envelope: dict) -> dict:
    """Construct an AttackCandidateResult-shaped dict from the envelope.

    Mirrors the kamino envelope wiring used in ``solana_measured_oracle`` —
    no submit-time coercion. The bool returned by ``qualifies_for_submission``
    is authoritative; do not Falsify it manually here.
    """
    lamport_delta = int(envelope["delta"]["liquidity_vault_lamports_delta"] or "0")
    token_delta = int(envelope["delta"]["liquidity_vault_token_delta"] or "0")

    candidate = {
        "candidate_schema_version": 4,
        "target_pinned": True,
        "slug": "marginfi_v2",
        "source_ref": {
            "commit": "v6.2-marginfi-probe-onboard",
            "module": "night_shift_security.impact.solana_measured_oracle",
            "spec_version": envelope["spec_version"],
        },
        "entrypoint": {
            "selector_or_discriminator": marginfi.discriminators()[
                "lending_account_borrow"
            ],
            "target": envelope["target"]["program"],
            "function": "lending_account_borrow",
        },
        "reproduction_artifact": "hermes/scripts/v6_2_marginfi_probe.py",
        "impact_oracle": {
            "measured": bool(envelope.get("measured_impact")),
            "threshold_raw_units": envelope["threshold_spl_units"],
            "above_threshold_tokens": [],
            "reason": envelope.get("measured_impact_reason"),
        },
        "failure_trace": {"blocking": False},
    }

    return {
        "target_id": "marginfi_v2",
        "reproduction_tier": (
            "solana_validator" if envelope.get("measured_impact") else "simulation"
        ),
        "evidence_grade": 0,
        "catalog_analogue": False,
        "deployed_viable": bool(envelope["pre"].get("bank_account_present")),
        "parameters": {"candidate": candidate},
        "fork_evidence": {
            "target_id": "marginfi_v2",
            "balance_delta_wei": "0",
            "reserve_last_update_slot_delta": str(envelope["delta"]["slot_delta"]),
            "balance_delta_lamports": str(lamport_delta),
            "token_delta": str(token_delta),
            "evidence_kind": "v6.2-marginfi-probe-impulse.v1",
            "evidence_path": envelope.get("evidence_path"),
        },
        "solana_evidence": {
            "method": "solana_validator",
            "probe_id": "stale_oracle_borrow_composition",
            "harness_mode": "read_state",
            "balance_verified": False,
            "balance_delta_lamports": str(lamport_delta),
            "evidence_path": envelope.get("evidence_path"),
        },
        "submission_recommendation_pretend": (
            "submit_now" if envelope.get("measured_impact") else "reject"
        ),
    }


def main() -> int:
    rpc_url = os.environ.get("SOLANA_MAINNET_RPC_URL", "").strip()
    if not rpc_url:
        print(
            json.dumps(
                {
                    "error": "rpc_unreachable:SOLANA_MAINNET_RPC_URL_not_set",
                    "advice": "set SOLANA_MAINNET_RPC_URL before invoking v6.2 probe",
                },
                indent=2,
            )
        )
        return 0

    envelope = probe_marginfi_v2(rpc_url)
    finding = build_finding(envelope)

    # Gate trace — read-only, no gate modification.
    gate_trace = {
        "_v4_candidate_submission_ok": _v4_candidate_submission_ok(finding),
        "_wormhole_submission_ok": _wormhole_submission_ok(finding),
        "finding_has_credible_reproduction": bool(
            finding.get("solana_evidence", {}).get("evidence_path")
        ),
        "finding_balance_verified": False,
        "_candidate_payload_present": bool(_candidate_payload(finding)),
        "qualifies_for_submission": False,
        "measured_impact": envelope.get("measured_impact"),
        "classification": envelope.get("measured_impact_reason"),
        "slot_delta": envelope["delta"]["slot_delta"],
        "liquidity_vault_lamports_delta": envelope["delta"]["liquidity_vault_lamports_delta"],
        "liquidity_vault_token_delta": envelope["delta"]["liquidity_vault_token_delta"],
    }
    print(json.dumps({"envelope_summary": envelope["delta"], "gate_trace": gate_trace}, indent=2))

    # Persist gate trace.
    trace_path = (
        ROOT
        / "data"
        / "security_results"
        / "bounty"
        / "submittable"
        / "marginfi_v2"
        / "nss-mfi2-1-gate-trace.json"
    )
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    trace_path.write_text(json.dumps(gate_trace, indent=2) + "\n")

    # Persist finding JSON (always, even when honest-zero — gates honest-zero is auditable).
    finding_path = (
        ROOT
        / "data"
        / "security_results"
        / "bounty"
        / "submittable"
        / "marginfi_v2"
        / "NSS-MFI2-1.json"
    )
    finding_path.write_text(
        json.dumps(
            {
                "schema_version": "v6.2-finding-envelope.v1",
                "finding": finding,
                "envelope_path": envelope.get("evidence_path"),
                "gate_trace_path": str(trace_path),
                "qualifies_for_submission": False,
                "submit_ready": False,
                "metadata": {
                    "trusted": False,
                    "lane": "v6.2-novel-vec-probe",
                },
            },
            indent=2,
            default=str,
        )
        + "\n"
    )
    print(f"\nPersisted: {envelope.get('evidence_path')}\nPersisted: {trace_path}\nPersisted: {finding_path}")

    # Update manifest.
    manifest_path = (
        ROOT / "data" / "security_results" / "bounty" / "submittable" / "manifest.json"
    )
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text())
        except (OSError, ValueError):
            manifest = {}
    else:
        manifest = {}
    manifest.setdefault("schema_version", "2.0")
    manifest.setdefault("source", "night-shift-security")
    manifest.setdefault("export_track", "submittable")
    manifest["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    manifest.setdefault("packs", [])
    if gate_trace["qualifies_for_submission"]:
        manifest["pack_count"] = len(manifest["packs"]) + 1
        manifest["packs"].append(
            {"id": "NSS-MFI2-1", "path": str(finding_path), "lane": "v6.2-novel-vec-probe"}
        )
    else:
        manifest["pack_count"] = 0  # honest-zero: never inflate pack_count
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
