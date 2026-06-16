"""Mainnet fork validation — Euler (EVM) and Mango (catalog analogue)."""

import os
import re
import shutil
import subprocess
from pathlib import Path

from night_shift_security.data.fork_targets import ForkTarget, get_fork_targets
from night_shift_security.data.schemas import AttackCandidateResult, ExploitRecord
from night_shift_security.domain.simulators.mock_simulator import MockSimulator
from night_shift_security.bridge.wormhole_economic import wormhole_economic_impact_verified
from night_shift_security.validation.rpc import rpc_available
from night_shift_security.validation.task_verifier import (
    apply_verifier_to_fork_entry,
    verify_from_forge_output,
)

_FOUNDRY_ROOT = Path(__file__).resolve().parents[3] / "foundry"


def resolve_fork_exploit_id(cand: AttackCandidateResult) -> str:
    """
    Strict catalog exploit id for fork eligibility.

    Only candidates with an explicit catalog_exploit_id qualify for
    fork_reproduced — no fuzzy vector or parameter matching.
    """
    return (cand.catalog_exploit_id or "").strip()


def is_fork_eligible(
    cand: AttackCandidateResult,
    targets: list[ForkTarget],
) -> ForkTarget | None:
    """Return EVM fork target when candidate is a strict catalog anchor."""
    exploit_id = resolve_fork_exploit_id(cand)
    if not exploit_id or cand.rejected:
        return None
    for target in targets:
        if target.exploit_id == exploit_id and not target.solana:
            return target
    return None


def _live_program_target_map(config: dict) -> dict[str, "ForkTarget"]:
    """Resolve configured live program fork targets (e.g. Wormhole core/bridge)."""
    live_ids = set(config.get("live_target_ids") or [])
    if not live_ids:
        return {}
    return {t.target_id: t for t in get_fork_targets() if t.target_id in live_ids}


def _resolve_live_program_target(
    cand: AttackCandidateResult,
    config: dict,
    live_targets: dict[str, "ForkTarget"],
) -> "ForkTarget | None":
    """Pick live program fork target for campaign candidates (not catalogue analogue)."""
    campaign_id = str(config.get("campaign_target_id") or "").strip()
    if not campaign_id or cand.vector.target_id != campaign_id:
        return None
    for target in live_targets.values():
        if target.template_id == cand.vector.template_id:
            return target
    return None


def _fork_candidate_set(
    candidates: list[AttackCandidateResult],
    config: dict,
) -> list[AttackCandidateResult]:
    """Catalog EVM anchors + top-N by severity (deduped by vector key)."""
    targets = get_fork_targets()
    passing = [c for c in candidates if not c.rejected]
    by_key: dict[str, AttackCandidateResult] = {}
    live_targets = _live_program_target_map(config)

    if config.get("always_test_catalog_evm_anchors", True):
        for cand in passing:
            if is_fork_eligible(cand, targets):
                by_key[str(cand.vector.key())] = cand

    top_n = config.get("top_n", 3)
    for cand in sorted(passing, key=lambda c: c.severity_score, reverse=True)[:top_n]:
        by_key[str(cand.vector.key())] = cand

    if live_targets:
        campaign_id = str(config.get("campaign_target_id") or "").strip()
        for cand in passing:
            if campaign_id and cand.vector.target_id == campaign_id:
                by_key[str(cand.vector.key())] = cand

    return list(by_key.values())


def run_fork_validation_phase(
    candidates: list[AttackCandidateResult],
    catalog: list[ExploitRecord],
    config: dict,
) -> dict[str, dict]:
    """
    Validate candidates against historical mainnet fork targets.

    fork_confirmed: any fork-phase success (incl. catalog fallback).
    fork_reproduced: strict live EVM replay at historical block (method evm_fork).
    """
    if not config.get("enabled", True):
        return {}

    mock = MockSimulator()
    forge = shutil.which("forge")
    results: dict[str, dict] = {}
    targets = get_fork_targets()
    exploit_map = {e.exploit_id: e for e in catalog}
    verifier_cfg = (config.get("operator") or {}).get("task_verifier") or {}
    required_for_novel = bool(verifier_cfg.get("required_for_novel", True))

    live_targets = _live_program_target_map(config)

    for cand in _fork_candidate_set(candidates, config):
        key = str(cand.vector.key())
        eligible_target = is_fork_eligible(cand, targets)
        live_target = _resolve_live_program_target(cand, config, live_targets)
        prefer_live = bool(config.get("prefer_live_programs", True))
        campaign_id = str(config.get("campaign_target_id") or "").strip()
        use_live = (
            live_target
            and prefer_live
            and campaign_id
            and cand.vector.target_id == campaign_id
        )
        if use_live:
            target = live_target
            eligible_target = None
        else:
            target = eligible_target or live_target or _match_template_fallback(
                cand, targets, exploit_map
            )

        entry: dict = {
            "target_id": target.target_id if target else "",
            "chain": target.chain if target else "",
            "fork_confirmed": False,
            "fork_reproduced": False,
            "method": "none",
            "block_number": target.block_number if target else 0,
        }

        if target and target.solana:
            entry.update(_validate_solana_via_catalog(cand, target, exploit_map, mock))
        elif (eligible_target or live_target) and forge and rpc_available():
            fork_target = live_target if use_live else (eligible_target or live_target)
            assert fork_target is not None
            entry.update(_validate_evm_fork(cand, fork_target, forge))
        elif target and forge and rpc_available():
            entry.update(_validate_evm_fork(cand, target, forge))
        elif target:
            entry.update(_validate_solana_via_catalog(cand, target, exploit_map, mock))
            entry["method"] = "catalog_fallback"
            entry["note"] = f"RPC unavailable ({target.rpc_env_var})"
        else:
            entry["method"] = "no_target"

        entry["fork_reproduced"] = (
            entry.get("method") == "evm_fork" and entry.get("fork_confirmed", False)
        )

        is_catalog_anchor = bool(resolve_fork_exploit_id(cand))
        if entry.get("method") == "evm_fork" and entry.get("fork_output"):
            verifier = verify_from_forge_output(
                entry["fork_output"],
                verifier_cfg,
                catalog_exempt=is_catalog_anchor,
            )
            apply_verifier_to_fork_entry(
                entry,
                verifier,
                required_for_novel=required_for_novel,
                is_catalog_anchor=is_catalog_anchor,
            )

        cand.fork_confirmed = entry.get("fork_confirmed", False)
        cand.fork_reproduced = entry.get("fork_reproduced", False)
        cand.fork_target_id = entry.get("target_id", "")
        if cand.fork_reproduced or entry.get("fork_confirmed"):
            cand.fork_block_number = entry.get("block_number", 0)
            cand.fork_evidence = _build_fork_evidence(entry, eligible_target or target)

        results[key] = entry

    return results


def _match_template_fallback(
    cand: AttackCandidateResult,
    targets: list[ForkTarget],
    exploit_map: dict[str, ExploitRecord],
) -> ForkTarget | None:
    """Non-catalog top-N fallback: match by template only."""
    for exploit_id, record in exploit_map.items():
        if record.template_id != cand.vector.template_id:
            continue
        for target in targets:
            if target.exploit_id == exploit_id:
                return target
    for target in targets:
        if target.template_id == cand.vector.template_id:
            return target
    return None


def _build_fork_evidence(entry: dict, target: ForkTarget | None) -> dict:
    evidence = {
        "target_id": entry.get("target_id", ""),
        "exploit_id": target.exploit_id if target else "",
        "block_number": entry.get("block_number", 0),
        "method": entry.get("method", ""),
        "impact_usd": entry.get("impact_usd", 0),
        "contract": entry.get("contract", target.contract_address if target else ""),
        "triage_surface_verified": bool(entry.get("triage_surface_verified")),
    }
    for key in (
        "balance_verified",
        "balance_delta_wei",
        "balance_threshold_wei",
        "verifier_method",
        "verifier_note",
        "harness_auth_mocked",
        "real_signed_vaa",
        "authorized_replay",
    ):
        if key in entry:
            evidence[key] = entry[key]
    if str(evidence.get("target_id") or "").startswith("wormhole"):
        evidence["economic_impact_verified"] = wormhole_economic_impact_verified(evidence)
        if evidence.get("triage_surface_verified") and not evidence["economic_impact_verified"]:
            evidence.setdefault("failure_class", "missing_economic_impact")
    return evidence


def _validate_evm_fork(
    cand: AttackCandidateResult,
    target: ForkTarget,
    forge: str,
) -> dict:
    """Run Foundry fork test at historical block."""
    rpc = (
        os.environ.get(target.rpc_env_var)
        or os.environ.get("FOUNDRY_FORK_URL")
        or os.environ.get("ETHEREUM_RPC_URL", "")
    )
    test_name = target.fork_test or "testForkEulerHistoricalBlock"

    if cand.vector.template_id == "flash_loan_oracle":
        test_name = "testForkEvmOracleManipulationPattern"

    env = {
        **os.environ,
        "ETHEREUM_RPC_URL": rpc,
        "FOUNDRY_FORK_URL": rpc,
    }
    if target.block_number > 0:
        env["FORK_BLOCK_NUMBER"] = str(target.block_number)
    for k, v in cand.vector.parameters.items():
        env[k.upper()] = str(v).lower() if isinstance(v, bool) else str(v)

    cmd = [forge, "test", "--match-test", test_name, "-vv"]

    try:
        proc = subprocess.run(
            cmd,
            cwd=_FOUNDRY_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return {
            "fork_confirmed": False,
            "method": "evm_fork",
            "error": str(exc),
        }

    output = proc.stdout + proc.stderr
    confirmed = proc.returncode == 0 and (
        "IMPACT_USD:" in output or "WORMHOLE_VALUE_PROBE:" in output
    )
    impact = 0.0
    match = re.search(r"IMPACT_USD:(\d+(?:\.\d+)?)", output)
    if match:
        impact = float(match.group(1))
    triage_surface = bool(re.search(r"TRIAGE_SURFACE_VERIFIED:1", output))
    harness_auth_mocked = bool(re.search(r"HARNESS_AUTH_MOCKED:1", output))
    real_signed_vaa = bool(re.search(r"REAL_SIGNED_VAA:1", output))
    authorized_replay = bool(re.search(r"AUTHORIZED_REPLAY:1", output))

    return {
        "fork_confirmed": confirmed,
        "method": "evm_fork",
        "block_number": target.block_number,
        "contract": target.contract_address,
        "impact_usd": impact,
        "exit_code": proc.returncode,
        "fork_output": output,
        "triage_surface_verified": triage_surface,
        "harness_auth_mocked": harness_auth_mocked,
        "real_signed_vaa": real_signed_vaa,
        "authorized_replay": authorized_replay,
    }


def _validate_solana_via_catalog(
    cand: AttackCandidateResult,
    target: ForkTarget,
    exploit_map: dict[str, ExploitRecord],
    mock: MockSimulator,
) -> dict:
    """Mango (Solana) — replay via Python catalog at known parameters."""
    exploit = exploit_map.get(target.exploit_id)
    if not exploit:
        return {"fork_confirmed": False, "method": "catalog", "error": "exploit not in catalog"}

    result = mock.execute(cand.vector, exploit.state)
    return {
        "fork_confirmed": result.success,
        "method": "catalog_solana",
        "impact_usd": result.economic_impact_usd,
        "note": "Solana exploit validated via catalog; not fork_reproduced",
        "block_number": target.block_number,
    }
