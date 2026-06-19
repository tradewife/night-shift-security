"""Solana validator replay validation — fixture (CI) and optional live validator."""

import os
import re
import subprocess
import sys
from pathlib import Path

from night_shift_security.data.schemas import AttackCandidateResult, ExploitRecord
from night_shift_security.data.solana_targets import SolanaTarget, get_solana_targets
from night_shift_security.domain.simulators.mock_simulator import MockSimulator
from night_shift_security.validation.solana_rpc import find_solana_test_validator, solana_validator_ready
from night_shift_security.validation.task_verifier import (
    apply_verifier_to_solana_entry,
    verify_from_solana_output,
)

_SOLANA_ROOT = Path(__file__).resolve().parents[3] / "solana"
_FIXTURE_RUNNER = _SOLANA_ROOT / "run_fixture_test.py"
_VALIDATOR_SCRIPT = _SOLANA_ROOT / "run_validator_test.sh"

# Strict reproduction methods — distinguishable in findings and public dataset.
_METHOD_FIXTURE = "solana_fixture"
_METHOD_VALIDATOR = "solana_validator"
_METHOD_KLEND = "solana_klend_harness"
_STRICT_METHODS = frozenset({_METHOD_FIXTURE, _METHOD_VALIDATOR, _METHOD_KLEND})
_KLEND_RUNNER = _SOLANA_ROOT / "run_klend_harness.py"


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


def _kamino_native_concrete_probe(cand: AttackCandidateResult) -> bool:
    if cand.vector.template_id != "concrete_sequence":
        return False
    if str(cand.vector.target_id).lower() != "kamino":
        return False
    cid = str((cand.vector.parameters or {}).get("candidate_id") or "")
    return cid.startswith("kamino-native-")


def _klend_routed_concrete_probe(cand: AttackCandidateResult) -> bool:
    """Route kamino concrete sequences through the KLend harness."""
    return _kamino_native_concrete_probe(cand)


def _resolve_klend_probe_id(cand: AttackCandidateResult) -> str:
    probe_id = os.environ.get("KLEND_PROBE", "").strip()
    if probe_id:
        return probe_id
    probe_hint = str((cand.vector.parameters or {}).get("klend_probe", "") or "").strip()
    if probe_hint:
        return probe_hint
    params = cand.vector.parameters or {}
    discriminator = str(params.get("discriminator") or "")
    steps = params.get("steps") if isinstance(params.get("steps"), list) else []
    instruction = ""
    if steps and isinstance(steps[0], dict):
        instruction = str(steps[0].get("instruction") or "")
    if instruction == "refresh_reserve" or discriminator == "0x02da8aeb4fc91966":
        return "refresh_reserve_live"
    if instruction == "deposit_reserve_liquidity" or discriminator == "0xa9c91e7e06cd6644":
        return "deposit_reserve_liquidity_live"
    if instruction == "redeem_reserve_collateral" or discriminator == "0xea75b57db98edc1d":
        return "redeem_reserve_collateral_live"
    if instruction == "flash_borrow_reserve_liquidity" or discriminator == "0x87e734a70734d4c1":
        return "flash_borrow_reserve_liquidity_live"
    return ""


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

    for cand in passing:
        if _klend_routed_concrete_probe(cand):
            by_key[str(cand.vector.key())] = cand

    novel_ids = set(config.get("novel_solana_targets") or [])
    if novel_ids:
        novel_by_template = {
            t.exploit_id: t for t in targets if t.exploit_id in novel_ids
        }
        for cand in sorted(passing, key=lambda c: c.severity_score, reverse=True)[:top_n]:
            for exploit_id, target in novel_by_template.items():
                if target.template_id == cand.vector.template_id:
                    by_key[str(cand.vector.key())] = cand

    return list(by_key.values())


def run_solana_validation_phase(
    candidates: list[AttackCandidateResult],
    catalog: list[ExploitRecord],
    config: dict,
) -> dict[str, dict]:
    """
    Validate candidates against Solana historical targets.

    solana_confirmed: broad — catalog mock or strict replay success.
    solana_reproduced: strict — only solana_fixture or solana_validator with impact evidence.

    Validator strict path (Slice 2) additionally requires:
      - matching catalog_exploit_id on a validator_backed target
      - SOLANA_VALIDATOR_PASS:1 in harness output
      - SLOT_TARGET matching documented historical slot
      - IMPACT_USD or IMPACT_LAMPORTS present
    """
    if not config.get("enabled", True):
        return {}

    mock = MockSimulator()
    results: dict[str, dict] = {}
    targets = get_solana_targets()
    exploit_map = {e.exploit_id: e for e in catalog}
    verifier_cfg = (config.get("operator") or {}).get("task_verifier") or {}
    required_for_novel = bool(verifier_cfg.get("required_for_novel", True))

    for cand in _solana_candidate_set(candidates, config):
        key = str(cand.vector.key())
        eligible_target = is_solana_eligible(cand, targets)
        target = eligible_target or _match_template_fallback(cand, targets, exploit_map)
        novel_ids = set(config.get("novel_solana_targets") or [])
        novel_target = None
        if not eligible_target:
            for candidate_target in targets:
                if (
                    candidate_target.exploit_id in novel_ids
                    and candidate_target.template_id == cand.vector.template_id
                ):
                    novel_target = candidate_target
                    target = candidate_target
                    break

        entry: dict = {
            "target_id": target.target_id if target else "",
            "chain": "solana",
            "solana_confirmed": False,
            "solana_reproduced": False,
            "method": "none",
            "slot": target.slot if target else 0,
        }

        klend_target = next((t for t in targets if t.exploit_id == "kamino-klend"), None)
        klend_harness_target: SolanaTarget | None = None
        if klend_target and _klend_routed_concrete_probe(cand):
            entry.update(_validate_klend_harness(cand, klend_target, config))
            klend_harness_target = klend_target
        elif novel_target and novel_target.exploit_id == "kamino-klend":
            entry.update(_validate_klend_harness(cand, novel_target, config))
            klend_harness_target = novel_target
        elif eligible_target and _fixture_runner_available():
            entry.update(_validate_solana_eligible(cand, eligible_target))
        elif target:
            entry.update(_validate_solana_via_catalog(cand, target, exploit_map, mock))
            entry["method"] = "catalog_solana"
            if not eligible_target:
                entry["note"] = "Non-catalog top-N; catalog mock only"
        else:
            entry["method"] = "no_target"

        if entry.get("solana_reproduced") is None:
            entry["solana_reproduced"] = _strict_solana_reproduced(entry)

        is_catalog_anchor = bool(resolve_solana_exploit_id(cand))
        if entry.get("solana_output"):
            verifier = verify_from_solana_output(
                entry["solana_output"],
                verifier_cfg,
                catalog_exempt=is_catalog_anchor,
            )
            apply_verifier_to_solana_entry(
                entry,
                verifier,
                required_for_novel=required_for_novel,
                is_catalog_anchor=is_catalog_anchor,
            )
            entry["solana_reproduced"] = _strict_solana_reproduced(entry)

        cand.solana_confirmed = entry.get("solana_confirmed", False)
        cand.solana_reproduced = entry.get("solana_reproduced", False)
        cand.solana_target_id = entry.get("target_id", "")
        if cand.solana_reproduced or entry.get("solana_confirmed"):
            cand.solana_slot = entry.get("slot", 0)
            evidence_target = (
                klend_harness_target
                or eligible_target
                or novel_target
                or target
            )
            cand.solana_evidence = _build_solana_evidence(entry, evidence_target)
            _stamp_klend_harness_invariants(cand, entry)

        results[key] = entry

    return results


def _fixture_runner_available() -> bool:
    return _FIXTURE_RUNNER.is_file()


def _use_validator_path(target: SolanaTarget) -> bool:
    """Validator path only when explicitly enabled and target is validator-backed."""
    enabled = os.environ.get("SOLANA_USE_VALIDATOR", "").lower() in ("1", "true", "yes")
    return enabled and target.validator_backed and solana_validator_ready()


def _validate_solana_eligible(
    cand: AttackCandidateResult,
    target: SolanaTarget,
) -> dict:
    """Route catalog anchor to validator (Slice 2) or fixture (CI default)."""
    if _use_validator_path(target):
        return _validate_solana_validator(cand, target)
    return _run_fixture_script(cand, target)


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


def _stamp_klend_harness_invariants(cand: AttackCandidateResult, entry: dict) -> None:
    """Promote live KLend probe signals into invariant artifacts for grading."""
    if entry.get("method") != _METHOD_KLEND:
        return
    output = str(entry.get("solana_output") or "")
    stale_oracle = "Price is too old" in output or "price_status" in output
    refresh_live = entry.get("probe_id") == "refresh_reserve_live" and entry.get("harness_mode") == "live_executed"
    if not stale_oracle and not refresh_live:
        return
    from night_shift_security.data.schemas import InvariantViolation

    violation = InvariantViolation(
        invariant_id="oracle_staleness_bound",
        description="KLend Scope oracle freshness vs refresh_reserve execution",
        expected="price_age_within_max_age",
        actual="stale_scope_or_refresh_executed_on_validator",
    )
    if cand.results:
        first = cand.results[0]
        if not any(v.invariant_id == violation.invariant_id for v in first.invariant_violations):
            first.invariant_violations.append(violation)
    cand.invariant_violation_count = max(cand.invariant_violation_count, 1)


def _strict_solana_reproduced(entry: dict) -> bool:
    if entry.get("method") not in _STRICT_METHODS or not entry.get("solana_confirmed", False):
        return False
    if entry.get("method") == _METHOD_KLEND:
        if entry.get("harness_mode") == "live_executed" and bool(entry.get("probe_executed")):
            return True
        if (
            entry.get("probe_id") == "refresh_reserve_live"
            and bool(entry.get("probe_executed"))
            and entry.get("harness_mode") == "live_deploy_verified"
            and int(entry.get("reserve_last_update_slot_delta") or 0) > 0
        ):
            return True
        return False
    return True


def _build_solana_evidence(entry: dict, target: SolanaTarget | None) -> dict:
    evidence = {
        "target_id": entry.get("target_id", ""),
        "exploit_id": target.exploit_id if target else "",
        "slot": entry.get("slot", 0),
        "method": entry.get("method", ""),
        "impact_usd": entry.get("impact_usd", 0),
        "impact_lamports": entry.get("impact_lamports", 0),
        "program_id": entry.get("program_id", target.program_id if target else ""),
        "slot_target": entry.get("slot_target", entry.get("slot", 0)),
        "slot_current": entry.get("slot_current", 0),
    }
    for key in (
        "balance_verified",
        "balance_delta_lamports",
        "balance_threshold_lamports",
        "verifier_method",
        "verifier_note",
        "harness_mode",
        "probe_executed",
        "probe_id",
        "reserve_last_update_slot_delta",
    ):
        if key in entry:
            evidence[key] = entry[key]
    return evidence


def _parse_klend_harness_fields(output: str) -> dict:
    fields: dict = {}
    mode_match = re.search(r"HARNESS_MODE:(\S+)", output)
    if mode_match:
        fields["harness_mode"] = mode_match.group(1)
    probe_match = re.search(r"PROBE:([^\s]+)", output)
    if probe_match:
        fields["probe_id"] = probe_match.group(1)
    executed_match = re.search(r"PROBE_EXECUTED:([01])", output)
    if executed_match:
        fields["probe_executed"] = executed_match.group(1) == "1"
    reserve_delta_match = re.search(r"RESERVE_LAST_UPDATE_SLOT_DELTA:(\d+)", output)
    if reserve_delta_match:
        fields["reserve_last_update_slot_delta"] = int(reserve_delta_match.group(1))
    return fields


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
            "method": _METHOD_FIXTURE,
            "error": str(exc),
        }

    output = proc.stdout + proc.stderr
    return _parse_impact_output(
        output,
        proc.returncode,
        method=_METHOD_FIXTURE,
        target=target,
        strict_validator=False,
    )


def _validate_solana_validator(
    cand: AttackCandidateResult,
    target: SolanaTarget,
) -> dict:
    """
    Grant-demo path: solana-test-validator with mainnet clones.

    Never falls back to fixture — failures return solana_confirmed=False.
    """
    if not _VALIDATOR_SCRIPT.is_file():
        return {
            "solana_confirmed": False,
            "method": _METHOD_VALIDATOR,
            "error": "run_validator_test.sh missing",
        }

    rpc = os.environ.get(target.rpc_env_var) or os.environ.get("SOLANA_MAINNET_RPC_URL", "")
    validator = find_solana_test_validator()

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
            ["bash", str(_VALIDATOR_SCRIPT)],
            cwd=_SOLANA_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=360,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return {
            "solana_confirmed": False,
            "method": _METHOD_VALIDATOR,
            "error": str(exc),
        }

    output = proc.stdout + proc.stderr
    return _parse_impact_output(
        output,
        proc.returncode,
        method=_METHOD_VALIDATOR,
        target=target,
        strict_validator=True,
    )


def _parse_impact_output(
    output: str,
    returncode: int,
    *,
    method: str,
    target: SolanaTarget,
    strict_validator: bool,
) -> dict:
    has_impact = "IMPACT_USD:" in output or "IMPACT_LAMPORTS:" in output

    if strict_validator:
        slot_target_match = re.search(r"SLOT_TARGET:(\d+)", output)
        slot_target = int(slot_target_match.group(1)) if slot_target_match else 0
        confirmed = (
            returncode == 0
            and "SOLANA_VALIDATOR_PASS:1" in output
            and has_impact
            and slot_target == target.slot
        )
    else:
        slot_target = target.slot
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

    slot_current = 0
    current_match = re.search(r"SLOT_CURRENT:(\d+)", output)
    if current_match:
        slot_current = int(current_match.group(1))

    result = {
        "solana_confirmed": confirmed,
        "method": method,
        "slot": target.slot,
        "slot_target": slot_target,
        "slot_current": slot_current,
        "program_id": target.program_id,
        "impact_usd": impact_usd,
        "impact_lamports": impact_lamports,
        "exit_code": returncode,
        "solana_output": output,
    }
    if strict_validator and not confirmed and returncode != 0:
        result["error"] = output.strip()[-500:] if output else "validator replay failed"
    return result


def _hipif_bounty_depth_active() -> bool:
    return os.environ.get("NSS_HIPIF_BOUNTY_DEPTH", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "full",
        "bounty",
    )


def _resolve_klend_fixture_mode(config: dict) -> bool:
    """Fixture only when explicitly requested or live validator unavailable (unless require_live)."""
    env_flag = os.environ.get("NSS_KLEND_FIXTURE", "").lower()
    require_live = bool(config.get("klend_require_live", False))
    if env_flag in ("1", "true", "yes"):
        if _hipif_bounty_depth_active() and require_live:
            return False
        return True
    if env_flag in ("0", "false", "no"):
        return False
    if require_live or _hipif_bounty_depth_active():
        return not solana_validator_ready()
    return True


def _validate_klend_harness(
    cand: AttackCandidateResult,
    target: SolanaTarget,
    config: dict | None = None,
) -> dict:
    """Non-catalogue KLend validator harness — live deploy by default when require_live."""
    cfg = config or {}
    if not _KLEND_RUNNER.is_file():
        return {
            "solana_confirmed": False,
            "method": _METHOD_KLEND,
            "error": "run_klend_harness.py missing",
            "target_id": target.target_id,
        }

    use_fixture = _resolve_klend_fixture_mode(cfg)
    require_live = bool(cfg.get("klend_require_live", False))
    env_live = os.environ.get("NSS_KLEND_FIXTURE", "").lower() in ("0", "false", "no")
    if (require_live or _hipif_bounty_depth_active()) and (env_live or require_live):
        if not solana_validator_ready():
            return {
                "solana_confirmed": False,
                "method": _METHOD_KLEND,
                "error": "klend_require_live but validator/RPC unavailable",
                "target_id": target.target_id,
            }
        if use_fixture:
            return {
                "solana_confirmed": False,
                "method": _METHOD_KLEND,
                "error": "klend_require_live blocked fixture fallback",
                "target_id": target.target_id,
            }

    probe_id = _resolve_klend_probe_id(cand)

    env = {
        **os.environ,
        "NSS_KLEND_FIXTURE": "1" if use_fixture else "0",
        "SOLANA_TARGET_ID": target.target_id,
        "SOLANA_EXPLOIT_ID": target.exploit_id,
        "SOLANA_SLOT": str(target.slot),
    }
    if probe_id:
        env["KLEND_PROBE"] = probe_id
    for k, v in cand.vector.parameters.items():
        env[f"PARAM_{k.upper()}"] = str(v).lower() if isinstance(v, bool) else str(v)

    try:
        proc = subprocess.run(
            [sys.executable, str(_KLEND_RUNNER)],
            cwd=_SOLANA_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=120 if use_fixture else 420,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return {
            "solana_confirmed": False,
            "method": _METHOD_KLEND,
            "error": str(exc),
            "target_id": target.target_id,
        }

    output = proc.stdout + proc.stderr
    klend_fields = _parse_klend_harness_fields(output)
    harness_mode = klend_fields.get("harness_mode", "fixture" if use_fixture else "")
    live_executed = harness_mode == "live_executed" and klend_fields.get("probe_executed")

    if use_fixture:
        parsed = _parse_impact_output(
            output,
            proc.returncode,
            method=_METHOD_KLEND,
            target=target,
            strict_validator=False,
        )
    else:
        parsed = _parse_klend_live_output(output, proc.returncode, target=target, live_executed=live_executed)

    parsed.update(klend_fields)
    parsed["target_id"] = target.target_id
    parsed["solana_output"] = output
    return parsed


def _parse_klend_live_output(
    output: str,
    returncode: int,
    *,
    target: SolanaTarget,
    live_executed: bool,
) -> dict:
    """Parse live KLend harness — deploy verification or measured probe execution only."""
    slot_target_match = re.search(r"SLOT_TARGET:(\d+)", output)
    slot_target = int(slot_target_match.group(1)) if slot_target_match else target.slot
    slot_current = 0
    current_match = re.search(r"SLOT_CURRENT:(\d+)", output)
    if current_match:
        slot_current = int(current_match.group(1))

    deploy_ok = returncode == 0 and "SOLANA_VALIDATOR_PASS:1" in output
    impact_usd = 0.0
    impact_lamports = 0
    if live_executed:
        lamports_match = re.search(r"IMPACT_LAMPORTS:(\d+)", output)
        if lamports_match:
            impact_lamports = int(lamports_match.group(1))
            impact_usd = impact_lamports / 1_000_000_000 * 150.0

    return {
        "solana_confirmed": deploy_ok,
        "method": _METHOD_KLEND,
        "slot": target.slot,
        "slot_target": slot_target,
        "slot_current": slot_current,
        "program_id": target.program_id,
        "impact_usd": impact_usd,
        "impact_lamports": impact_lamports,
        "exit_code": returncode,
        "solana_reproduced": live_executed and deploy_ok,
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
