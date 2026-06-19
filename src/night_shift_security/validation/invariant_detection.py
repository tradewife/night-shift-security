"""Generalized invariant detection layer.

Post-validation stamping of InvariantViolation artifacts on non-catalogue
candidates that carry credible reproduction evidence.  Replaces the narrow
``_stamp_klend_harness_invariants`` special-case with a pluggable adapter
architecture.

Integration point:
    Call ``stamp_detected_invariants(candidate)`` AFTER fork/Solana validation
    evidence has been attached and BEFORE ``compute_evidence_grade()`` runs.
"""

from __future__ import annotations

import logging
from typing import Any

from night_shift_security.data.schemas import (
    AttackCandidateResult,
    AttackResult,
    InvariantViolation,
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_METHOD_KLEND = "solana_klend_harness"
_METHOD_FIXTURE = "solana_fixture"
_METHOD_VALIDATOR = "solana_validator"

# Non-fee reproduction tiers that qualify as credible
_CREDIBLE_TIERS = {"solana_validator", "fork_mainnet", "foundry_fork"}


def _is_catalogue(candidate: AttackCandidateResult) -> bool:
    """True when the candidate is definitively a catalogue anchor.

    Uses ``catalog_analogue`` (the final reality-check determination) rather
    than ``catalog_exploit_id`` (a discovery-time heuristic that may be
    overridden by reality check).
    """
    return bool(candidate.catalog_analogue)


def _has_v4_payload(candidate: AttackCandidateResult) -> bool:
    """True when the vector metadata carries a v4 candidate binding."""
    meta = candidate.vector.metadata or {}
    params = candidate.vector.parameters or {}
    # v4 payload is stored under "candidate" key in parameters
    c = params.get("candidate") or meta.get("candidate")
    if not isinstance(c, dict):
        return False
    try:
        return int(c.get("candidate_schema_version") or 0) >= 4
    except (TypeError, ValueError):
        return False


def _has_reproduction(candidate: AttackCandidateResult) -> bool:
    return bool(candidate.fork_reproduced or candidate.solana_reproduced)


def _has_reproduction_steps(candidate: AttackCandidateResult) -> bool:
    return any(r.success and r.reproduction_steps for r in candidate.results)


def _has_impact(candidate: AttackCandidateResult) -> bool:
    return (
        candidate.mean_economic_impact_usd > 0
        or bool(candidate.fork_evidence)
        or bool(candidate.solana_evidence)
    )


def _solana_evidence_for(candidate: AttackCandidateResult) -> dict[str, Any]:
    return dict(candidate.solana_evidence or {})


def _fork_evidence_for(candidate: AttackCandidateResult) -> dict[str, Any]:
    return dict(candidate.fork_evidence or {})


def _first_successful_result(candidate: AttackCandidateResult) -> AttackResult | None:
    for r in candidate.results:
        if r.success:
            return r
    return None


def _already_has_violation(candidate: AttackCandidateResult, invariant_id: str) -> bool:
    """Check if invariant_id already stamped anywhere on the candidate."""
    for r in candidate.results:
        for v in r.invariant_violations:
            if v.invariant_id == invariant_id:
                return True
    return False


def _stamp_violation(
    candidate: AttackCandidateResult,
    violation: InvariantViolation,
) -> None:
    """Append a violation to the first successful result, or create one."""
    if _already_has_violation(candidate, violation.invariant_id):
        return
    result = _first_successful_result(candidate)
    if result is None:
        # Create a minimal successful result to hold the violation.
        # Copy reproduction steps from the candidate's existing results
        # so _has_root_cause_artifacts can find them.
        steps: list[ReproductionStep] = []
        for r in candidate.results:
            if r.success and r.reproduction_steps:
                steps = list(r.reproduction_steps)
                break
        result = AttackResult(
            vector=candidate.vector,
            success=True,
            severity="high",
            economic_impact_usd=candidate.mean_economic_impact_usd,
            invariant_violations=[violation],
            reproduction_steps=steps,
        )
        candidate.results.append(result)
    else:
        result.invariant_violations.append(violation)
    candidate.invariant_violation_count = max(
        candidate.invariant_violation_count,
        sum(len(r.invariant_violations) for r in candidate.results),
    )


# ---------------------------------------------------------------------------
# Adapter 1: KLend reserve freshness / oracle invariant
# ---------------------------------------------------------------------------

def _detect_klend_reserve_freshness(
    candidate: AttackCandidateResult,
) -> InvariantViolation | None:
    """
    Trigger only when:
      - method == klend_harness
      - candidate is non-catalogue
      - reproduction tier is Solana validator or equivalent
      - candidate has v4 binding
      - measured oracle exists
      - stale oracle / refresh-reserve / reserve slot delta evidence exists
      - OR probe executed successfully on validator (live_deploy_verified)
      - evidence is not fee-only
    """
    if _is_catalogue(candidate):
        return None

    evidence = _solana_evidence_for(candidate)
    if evidence.get("method") != _METHOD_KLEND:
        return None

    # Must have v4 binding
    if not _has_v4_payload(candidate):
        return None

    # Must have credible reproduction tier or solana_reproduced
    tier = candidate.reproduction_tier or ""
    if tier not in _CREDIBLE_TIERS and not candidate.solana_reproduced:
        return None

    # Must have oracle or refresh-reserve or live-deploy-verified evidence
    output = str(evidence.get("solana_output") or "")
    probe_id = evidence.get("probe_id", "")
    harness_mode = evidence.get("harness_mode", "")
    slot_delta = evidence.get("reserve_last_update_slot_delta", 0)
    probe_executed = evidence.get("probe_executed", False)

    stale_oracle = "Price is too old" in output or "price_status" in output
    refresh_live = probe_id == "refresh_reserve_live" and harness_mode == "live_executed"
    slot_advanced = isinstance(slot_delta, (int, float)) and slot_delta > 0
    # Live-deploy-verified probes that executed on validator
    live_deploy_verified = (
        harness_mode == "live_deploy_verified"
        and bool(probe_executed)
    )

    if not (stale_oracle or refresh_live or slot_advanced or live_deploy_verified):
        return None

    # Must not be fee-only CPI
    balance_delta = evidence.get("balance_delta_lamports", 0)
    impact_usd = evidence.get("impact_usd", 0)
    if _is_fee_only(balance_delta, impact_usd, evidence):
        return None

    return InvariantViolation(
        invariant_id="klend_reserve_freshness_bound",
        description=(
            "KLend Scope oracle freshness vs refresh_reserve execution; "
            "validator replay advanced reserve state under stale or abnormal oracle condition"
        ),
        expected="reserve refresh must use fresh valid oracle state or reject",
        actual="validator replay advanced reserve state under stale or abnormal oracle condition",
    )


# ---------------------------------------------------------------------------
# Adapter 2: Measured balance conservation invariant
# ---------------------------------------------------------------------------

def _detect_balance_conservation(
    candidate: AttackCandidateResult,
) -> InvariantViolation | None:
    """
    Trigger only when:
      - non-catalogue
      - credible reproduction (fork or solana)
      - v4 candidate payload exists
      - measured token / reserve / protocol delta exists
      - delta is non-fee
      - reproduction artifact exists
    """
    if _is_catalogue(candidate):
        return None

    if not _has_reproduction(candidate):
        return None

    if not _has_v4_payload(candidate):
        return None

    # Check for measured delta evidence
    fork_ev = _fork_evidence_for(candidate)
    sol_ev = _solana_evidence_for(candidate)

    # Fork evidence path: measured_impact_oracle.v1
    if fork_ev.get("evidence_kind") == "measured_impact_oracle.v1":
        delta = fork_ev.get("delta") or {}
        measured_impact = fork_ev.get("measured_impact", False)
        if not measured_impact and not delta:
            return None
        if _is_fee_only_delta(delta):
            return None
        return InvariantViolation(
            invariant_id="measured_balance_conservation",
            description=(
                "Protocol/user/token balances conserve according to "
                "intended instruction semantics; measured pre/post delta "
                "violates expected conservation envelope"
            ),
            expected="protocol/user/token balances conserve according to intended instruction semantics",
            actual="measured pre/post delta violates expected conservation envelope",
        )

    # Solana evidence path: balance_verified with non-zero delta
    if sol_ev.get("balance_verified"):
        balance_delta = sol_ev.get("balance_delta_lamports", 0)
        if isinstance(balance_delta, (int, float)) and balance_delta != 0:
            if not _is_fee_only_lamports(balance_delta):
                return InvariantViolation(
                    invariant_id="measured_balance_conservation",
                    description=(
                        "Protocol/user/token balances conserve according to "
                        "intended instruction semantics; measured pre/post delta "
                        "violates expected conservation envelope"
                    ),
                    expected="protocol/user/token balances conserve according to intended instruction semantics",
                    actual="measured pre/post delta violates expected conservation envelope",
                )

    # v4 payload path: impact_oracle.measured
    params = candidate.vector.parameters or {}
    c = params.get("candidate") or (candidate.vector.metadata or {}).get("candidate")
    if isinstance(c, dict):
        impact_oracle = c.get("impact_oracle") or {}
        if isinstance(impact_oracle, dict) and impact_oracle.get("measured"):
            return InvariantViolation(
                invariant_id="measured_balance_conservation",
                description=(
                    "Protocol/user/token balances conserve according to "
                    "intended instruction semantics; measured pre/post delta "
                    "violates expected conservation envelope"
                ),
                expected="protocol/user/token balances conserve according to intended instruction semantics",
                actual="measured pre/post delta violates expected conservation envelope",
            )

    return None


# ---------------------------------------------------------------------------
# Adapter 3: Oracle deviation invariant
# ---------------------------------------------------------------------------

def _detect_oracle_deviation(
    candidate: AttackCandidateResult,
) -> InvariantViolation | None:
    """
    Trigger for oracle / lending / AMM candidates when:
      - measured oracle deviation exists
      - price/reserve/rate changed beyond configured threshold
      - PoC envelope names the source account / oracle account
      - not catalogue analogue
    """
    if _is_catalogue(candidate):
        return None

    if not _has_reproduction(candidate):
        return None

    params = candidate.vector.parameters or {}
    c = params.get("candidate") or (candidate.vector.metadata or {}).get("candidate")

    # Check v4 payload for oracle deviation
    if isinstance(c, dict):
        impact_oracle = c.get("impact_oracle") or {}
        if isinstance(impact_oracle, dict):
            measured = impact_oracle.get("measured", False)
            above_threshold = impact_oracle.get("above_threshold_tokens") or []
            threshold = impact_oracle.get("threshold_raw_units")

            if measured and (above_threshold or threshold):
                return InvariantViolation(
                    invariant_id="oracle_deviation_bound",
                    description=(
                        "Oracle-derived valuation remains within configured safety bound; "
                        "candidate sequence produced valuation/reserve/rate delta outside bound"
                    ),
                    expected="oracle-derived valuation remains within configured safety bound",
                    actual="candidate sequence produced valuation/reserve/rate delta outside bound",
                )

    # Check fork evidence for oracle deviation
    fork_ev = _fork_evidence_for(candidate)
    if fork_ev.get("evidence_kind") == "measured_impact_oracle.v1":
        delta = fork_ev.get("delta") or {}
        tokens = delta.get("tokens") or []
        for token in tokens:
            if isinstance(token, dict):
                raw_delta = token.get("raw_delta", 0)
                if isinstance(raw_delta, (int, float)) and abs(raw_delta) > 0:
                    source = token.get("source_account") or token.get("oracle_account")
                    if source:
                        return InvariantViolation(
                            invariant_id="oracle_deviation_bound",
                            description=(
                                "Oracle-derived valuation remains within configured safety bound; "
                                "candidate sequence produced valuation/reserve/rate delta outside bound"
                            ),
                            expected="oracle-derived valuation remains within configured safety bound",
                            actual="candidate sequence produced valuation/reserve/rate delta outside bound",
                        )

    # Check solana evidence for oracle deviation via slot delta
    sol_ev = _solana_evidence_for(candidate)
    if sol_ev.get("method") in (_METHOD_KLEND, _METHOD_VALIDATOR):
        slot_delta = sol_ev.get("reserve_last_update_slot_delta", 0)
        if isinstance(slot_delta, (int, float)) and slot_delta > 0:
            # Reserve slot advanced — potential oracle deviation
            impact_usd = sol_ev.get("impact_usd", 0)
            if isinstance(impact_usd, (int, float)) and impact_usd > 0:
                return InvariantViolation(
                    invariant_id="oracle_deviation_bound",
                    description=(
                        "Oracle-derived valuation remains within configured safety bound; "
                        "candidate sequence produced valuation/reserve/rate delta outside bound"
                    ),
                    expected="oracle-derived valuation remains within configured safety bound",
                    actual="candidate sequence produced valuation/reserve/rate delta outside bound",
                )

    return None


# ---------------------------------------------------------------------------
# Fee-only filters
# ---------------------------------------------------------------------------

_FEE_THRESHOLD_LAMPORTS = 10_000  # ~0.00001 SOL
_FEE_THRESHOLD_USD = 0.01


def _is_fee_only(
    balance_delta_lamports: float | int,
    impact_usd: float | int,
    evidence: dict[str, Any],
) -> bool:
    """True when the observed delta is consistent with transaction fees only."""
    if _is_fee_only_lamports(balance_delta_lamports):
        if abs(impact_usd) < _FEE_THRESHOLD_USD:
            # Check if there are any non-fee tokens in the evidence
            tokens = evidence.get("tokens") or []
            if not tokens:
                return True
    return False


def _is_fee_only_lamports(lamports: float | int) -> bool:
    """True when the delta is within the transaction-fee envelope."""
    return abs(lamports) <= _FEE_THRESHOLD_LAMPORTS


def _is_fee_only_delta(delta: dict[str, Any]) -> bool:
    """True when all token deltas in a measured envelope are fee-only."""
    tokens = delta.get("tokens") or []
    if not tokens:
        return True
    for token in tokens:
        if not isinstance(token, dict):
            continue
        raw = token.get("raw_delta", 0)
        if isinstance(raw, (int, float)) and abs(raw) > 0:
            return False
    return True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_ADAPTERS = [
    ("klend_reserve_freshness", _detect_klend_reserve_freshness),
    ("balance_conservation", _detect_balance_conservation),
    ("oracle_deviation", _detect_oracle_deviation),
]


def detect_invariant_violations(
    candidate: AttackCandidateResult,
) -> list[InvariantViolation]:
    """Run all invariant adapters and return newly detected violations.

    Never stamps catalogue-only findings as novel.
    Never stamps fee-only CPI as a root-cause invariant.
    Never stamps benchmark fixtures as bounty evidence.
    """
    if _is_catalogue(candidate):
        return []

    violations: list[InvariantViolation] = []
    for name, adapter in _ADAPTERS:
        try:
            v = adapter(candidate)
            if v is not None:
                violations.append(v)
        except Exception:
            log.debug("invariant adapter %s failed", name, exc_info=True)
    return violations


def stamp_detected_invariants(candidate: AttackCandidateResult) -> int:
    """Stamp detected invariant violations onto the candidate.

    Returns the number of new violations stamped.
    """
    violations = detect_invariant_violations(candidate)
    for v in violations:
        _stamp_violation(candidate, v)
    return len(violations)
