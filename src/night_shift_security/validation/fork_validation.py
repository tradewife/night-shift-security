"""Mainnet fork validation — Euler (EVM) and Mango (catalog analogue)."""

import os
import re
import shutil
import subprocess
from pathlib import Path

from night_shift_security.data.fork_targets import ForkTarget, evm_fork_targets, get_fork_targets
from night_shift_security.data.schemas import AttackCandidateResult, ExploitRecord
from night_shift_security.domain.simulators.mock_simulator import MockSimulator

_FOUNDRY_ROOT = Path(__file__).resolve().parents[3] / "foundry"


def run_fork_validation_phase(
    candidates: list[AttackCandidateResult],
    catalog: list[ExploitRecord],
    config: dict,
) -> dict[str, dict]:
    """
    Validate top candidates against historical mainnet fork targets.

    - Euler: Foundry fork at block 16825925 (Ethereum)
    - Mango: Solana exploit — Python catalog replay (no EVM fork)
    - Mango EVM analogue: Foundry testForkEvmOracleManipulationPattern
    """
    if not config.get("enabled", True):
        return {}

    top_n = config.get("top_n", 3)
    mock = MockSimulator()
    forge = shutil.which("forge")
    results: dict[str, dict] = {}

    passing = sorted(
        [c for c in candidates if not c.rejected],
        key=lambda c: c.severity_score,
        reverse=True,
    )[:top_n]

    exploit_map = {e.exploit_id: e for e in catalog}
    targets = get_fork_targets()

    for cand in passing:
        key = str(cand.vector.key())
        target = _match_fork_target(cand, targets, exploit_map)
        entry: dict = {
            "target_id": target.target_id if target else "",
            "chain": target.chain if target else "",
            "fork_confirmed": False,
            "method": "none",
            "block_number": target.block_number if target else 0,
        }

        if target and target.solana:
            entry.update(_validate_solana_via_catalog(cand, target, exploit_map, mock))
        elif target and forge and _rpc_available(target):
            entry.update(_validate_evm_fork(cand, target, forge))
        elif target:
            entry.update(_validate_solana_via_catalog(cand, target, exploit_map, mock))
            entry["method"] = "catalog_fallback"
            entry["note"] = f"RPC unavailable ({target.rpc_env_var})"
        else:
            entry["method"] = "no_target"

        cand.fork_confirmed = entry.get("fork_confirmed", False)
        cand.fork_target_id = entry.get("target_id", "")
        results[key] = entry

    return results


def _match_fork_target(
    cand: AttackCandidateResult,
    targets: list[ForkTarget],
    exploit_map: dict[str, ExploitRecord],
) -> ForkTarget | None:
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


def _rpc_available(target: ForkTarget) -> bool:
    rpc = os.environ.get(target.rpc_env_var) or os.environ.get("FOUNDRY_FORK_URL", "")
    return bool(rpc)


def _validate_evm_fork(
    cand: AttackCandidateResult,
    target: ForkTarget,
    forge: str,
) -> dict:
    """Run Foundry fork test at historical block."""
    rpc = os.environ.get(target.rpc_env_var) or os.environ.get("FOUNDRY_FORK_URL", "")
    test_name = target.fork_test or "testForkEulerHistoricalBlock"

    if cand.vector.template_id == "flash_loan_oracle":
        test_name = "testForkEvmOracleManipulationPattern"
    elif cand.vector.template_id == "access_control_escalation":
        test_name = target.fork_test or "testForkNomadBridgeBytecode"
    elif cand.vector.template_id == "upgradeability_risk":
        test_name = "testForkEulerHistoricalBlock"

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
    analogue_test = "testForkEvmOracleManipulationPattern"
    return {
        "fork_confirmed": result.success,
        "method": "catalog_solana",
        "impact_usd": result.economic_impact_usd,
        "note": "Solana exploit validated via catalog; EVM analogue: " + analogue_test,
        "block_number": target.block_number,
    }