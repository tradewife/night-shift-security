"""Mainnet fork validation — Euler (EVM) and Mango (catalog analogue)."""

import os
import re
import shutil
import subprocess
from pathlib import Path

from night_shift_security.data.fork_targets import ForkTarget, get_fork_targets
from night_shift_security.data.schemas import AttackCandidateResult, ExploitRecord
from night_shift_security.domain.simulators.mock_simulator import MockSimulator
from night_shift_security.validation.rpc import rpc_available

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


def _fork_candidate_set(
    candidates: list[AttackCandidateResult],
    config: dict,
) -> list[AttackCandidateResult]:
    """Catalog EVM anchors + top-N by severity (deduped by vector key)."""
    targets = get_fork_targets()
    passing = [c for c in candidates if not c.rejected]
    by_key: dict[str, AttackCandidateResult] = {}

    if config.get("always_test_catalog_evm_anchors", True):
        for cand in passing:
            if is_fork_eligible(cand, targets):
                by_key[str(cand.vector.key())] = cand

    top_n = config.get("top_n", 3)
    for cand in sorted(passing, key=lambda c: c.severity_score, reverse=True)[:top_n]:
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

    for cand in _fork_candidate_set(candidates, config):
        key = str(cand.vector.key())
        eligible_target = is_fork_eligible(cand, targets)
        target = eligible_target or _match_template_fallback(cand, targets, exploit_map)

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
        elif eligible_target and forge and rpc_available():
            entry.update(_validate_evm_fork(cand, eligible_target, forge))
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

        cand.fork_confirmed = entry.get("fork_confirmed", False)
        cand.fork_reproduced = entry.get("fork_reproduced", False)
        cand.fork_target_id = entry.get("target_id", "")
        if cand.fork_reproduced:
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
    return {
        "target_id": entry.get("target_id", ""),
        "exploit_id": target.exploit_id if target else "",
        "block_number": entry.get("block_number", 0),
        "method": entry.get("method", ""),
        "impact_usd": entry.get("impact_usd", 0),
        "contract": entry.get("contract", target.contract_address if target else ""),
    }


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
        "FORK_BLOCK_NUMBER": str(target.block_number),
    }
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
    confirmed = proc.returncode == 0 and "IMPACT_USD:" in output
    impact = 0.0
    match = re.search(r"IMPACT_USD:(\d+(?:\.\d+)?)", output)
    if match:
        impact = float(match.group(1))

    return {
        "fork_confirmed": confirmed,
        "method": "evm_fork",
        "block_number": target.block_number,
        "contract": target.contract_address,
        "impact_usd": impact,
        "exit_code": proc.returncode,
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