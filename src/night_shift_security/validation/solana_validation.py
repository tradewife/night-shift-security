"""Solana validator replay validation — fixture (CI) and optional live validator."""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from night_shift_security.data.schemas import AttackCandidateResult, ExploitRecord
from night_shift_security.data.solana_targets import SolanaTarget, get_solana_targets
from night_shift_security.domain.simulators.mock_simulator import MockSimulator
from night_shift_security.validation.solana_rpc import solana_validator_available

_SOLANA_ROOT = Path(__file__).resolve().parents[3] / "solana"
_FIXTURE_RUNNER = _SOLANA_ROOT / "run_fixture_test.py"
_STRICT_METHODS = frozenset({"solana_fixture", "solana_validator"})


def resolve_solana_exploit_id(cand: AttackCandidateResult) -> str:
    """Strict catalog exploit id for Solana eligibility."""
    return (cand.catalog_exploit_id or "").strip()


def is_solana_eligible(
    cand: AttackCandidateResult,
    targets: list[SolanaTarget],
) -> SolanaTarget | None:
    """Return Solana target when candidate is a strict catalog anchor."""
    exploit_id = resolve_solana_exploit_id(cand)
    if not exploit_id or cand.rejected:
        return None
    for target in targets:
        if target.exploit_id == exploit_id:
            return target
    return None


def _solana_candidate_set(
    candidates: list[AttackCandidateResult],
    config: dict,
) -> list[AttackCandidateResult]:
    """Catalog Solana anchors + top-N by severity (deduped by vector key)."""
    targets = get_solana_targets()
    passing = [c for c in candidates if not c.rejected]
    by_key: dict[str, AttackCandidateResult] = {}

    if config.get("always_test_catalog_solana_anchors", True):
        for cand in passing:
            if is_solana_eligible(cand, targets):
                by_key[str(cand.vector.key())] = cand

    top_n = config.get("top_n", 3)
    for cand in sorted(passing, key=lambda c: c.severity_score, reverse=True)[:top_n]:
        by_key[str(cand.vector.key())] = cand

    return list(by_key.values())


def run_solana_validation_phase(
    candidates: list[AttackCandidateResult],
    catalog: list[ExploitRecord],
    config: dict,
) -> dict[str, dict]:
    """
    Validate candidates against Solana historical targets.

    solana_confirmed: any Solana-phase success (incl. catalog mock).
    solana_reproduced: strict fixture or validator replay with impact evidence.
    """
    if not config.get("enabled", True):
        return {}

    mock = MockSimulator()
    results: dict[str, dict] = {}
    targets = get_solana_targets()
    exploit_map = {e.exploit_id: e for e in catalog}

    for cand in _solana_candidate_set(candidates, config):
        key = str(cand.vector.key())
        eligible_target = is_solana_eligible(cand, targets)
        target = eligible_target or _match_template_fallback(cand, targets, exploit_map)

        entry: dict = {
            "target_id": target.target_id if target else "",
            "chain": "solana",
            "solana_confirmed": False,
            "solana_reproduced": False,
            "method": "none",
            "slot": target.slot if target else 0,
        }

        if eligible_target and _fixture_runner_available():
            entry.update(_validate_solana_fixture(cand, eligible_target))
        elif target:
            entry.update(_validate_solana_via_catalog(cand, target, exploit_map, mock))
            entry["method"] = "catalog_solana"
            if not eligible_target:
                entry["note"] = "Non-catalog top-N; catalog mock only"
        else:
            entry["method"] = "no_target"

        entry["solana_reproduced"] = (
            entry.get("method") in _STRICT_METHODS
            and entry.get("solana_confirmed", False)
        )

        cand.solana_confirmed = entry.get("solana_confirmed", False)
        cand.solana_reproduced = entry.get("solana_reproduced", False)
        cand.solana_target_id = entry.get("target_id", "")
        if cand.solana_reproduced:
            cand.solana_slot = entry.get("slot", 0)
            cand.solana_evidence = _build_solana_evidence(entry, eligible_target or target)

        results[key] = entry

    return results


def _fixture_runner_available() -> bool:
    return _FIXTURE_RUNNER.is_file()


def _match_template_fallback(
    cand: AttackCandidateResult,
    targets: list[SolanaTarget],
    exploit_map: dict[str, ExploitRecord],
) -> SolanaTarget | None:
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


def _build_solana_evidence(entry: dict, target: SolanaTarget | None) -> dict:
    return {
        "target_id": entry.get("target_id", ""),
        "exploit_id": target.exploit_id if target else "",
        "slot": entry.get("slot", 0),
        "method": entry.get("method", ""),
        "impact_usd": entry.get("impact_usd", 0),
        "impact_lamports": entry.get("impact_lamports", 0),
        "program_id": entry.get("program_id", target.program_id if target else ""),
    }


def _validate_solana_fixture(
    cand: AttackCandidateResult,
    target: SolanaTarget,
) -> dict:
    """Run fixture harness (CI default) or live validator when configured."""
    use_validator = os.environ.get("SOLANA_USE_VALIDATOR", "").lower() in ("1", "true", "yes")
    validator = shutil.which("solana-test-validator")

    if use_validator and validator and solana_validator_available():
        return _validate_solana_validator(cand, target, validator)

    return _run_fixture_script(cand, target)


def _run_fixture_script(
    cand: AttackCandidateResult,
    target: SolanaTarget,
) -> dict:
    env = {
        **os.environ,
        "SOLANA_TARGET_ID": target.target_id,
        "SOLANA_EXPLOIT_ID": target.exploit_id,
        "SOLANA_SLOT": str(target.slot),
        "SOLANA_FIXTURE_TEST": target.fixture_test,
    }
    for k, v in cand.vector.parameters.items():
        env[f"PARAM_{k.upper()}"] = str(v).lower() if isinstance(v, bool) else str(v)

    try:
        proc = subprocess.run(
            [sys.executable, str(_FIXTURE_RUNNER)],
            cwd=_SOLANA_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return {
            "solana_confirmed": False,
            "method": "solana_fixture",
            "error": str(exc),
        }

    output = proc.stdout + proc.stderr
    return _parse_impact_output(
        output,
        proc.returncode,
        method="solana_fixture",
        target=target,
    )


def _validate_solana_validator(
    cand: AttackCandidateResult,
    target: SolanaTarget,
    validator: str,
) -> dict:
    """Grant-demo path: solana-test-validator with mainnet clones."""
    rpc = os.environ.get(target.rpc_env_var) or os.environ.get("SOLANA_MAINNET_RPC_URL", "")
    script = _SOLANA_ROOT / "run_validator_test.sh"
    if not script.is_file():
        return _run_fixture_script(cand, target)

    env = {
        **os.environ,
        "SOLANA_VALIDATOR_BIN": validator,
        "SOLANA_MAINNET_RPC_URL": rpc,
        "SOLANA_TARGET_ID": target.target_id,
        "SOLANA_EXPLOIT_ID": target.exploit_id,
        "SOLANA_SLOT": str(target.slot),
        "SOLANA_FIXTURE_TEST": target.fixture_test,
    }

    try:
        proc = subprocess.run(
            ["bash", str(script)],
            cwd=_SOLANA_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return {
            "solana_confirmed": False,
            "method": "solana_validator",
            "error": str(exc),
        }

    output = proc.stdout + proc.stderr
    return _parse_impact_output(
        output,
        proc.returncode,
        method="solana_validator",
        target=target,
    )


def _parse_impact_output(
    output: str,
    returncode: int,
    *,
    method: str,
    target: SolanaTarget,
) -> dict:
    has_impact = "IMPACT_USD:" in output or "IMPACT_LAMPORTS:" in output
    confirmed = returncode == 0 and has_impact

    impact_usd = 0.0
    impact_lamports = 0

    usd_match = re.search(r"IMPACT_USD:(\d+(?:\.\d+)?)", output)
    if usd_match:
        impact_usd = float(usd_match.group(1))

    lamports_match = re.search(r"IMPACT_LAMPORTS:(\d+)", output)
    if lamports_match:
        impact_lamports = int(lamports_match.group(1))
        if impact_usd == 0:
            impact_usd = impact_lamports / 1_000_000_000 * 150.0

    return {
        "solana_confirmed": confirmed,
        "method": method,
        "slot": target.slot,
        "program_id": target.program_id,
        "impact_usd": impact_usd,
        "impact_lamports": impact_lamports,
        "exit_code": returncode,
    }


def _validate_solana_via_catalog(
    cand: AttackCandidateResult,
    target: SolanaTarget,
    exploit_map: dict[str, ExploitRecord],
    mock: MockSimulator,
) -> dict:
    """Broad confirmation via Python catalog replay at known parameters."""
    exploit = exploit_map.get(target.exploit_id)
    if not exploit:
        return {"solana_confirmed": False, "method": "catalog_solana", "error": "exploit not in catalog"}

    result = mock.execute(cand.vector, exploit.state)
    return {
        "solana_confirmed": result.success,
        "method": "catalog_solana",
        "impact_usd": result.economic_impact_usd,
        "note": "Solana exploit validated via catalog; not solana_reproduced",
        "slot": target.slot,
        "program_id": target.program_id,
    }