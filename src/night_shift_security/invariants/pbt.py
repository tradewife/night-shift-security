"""Property-based and deterministic invariant tests from recon JSON."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class InvariantResult:
    invariant_id: str
    passed: bool
    counterexample: dict[str, Any] | None
    engine: str  # deterministic | hypothesis

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_recon(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _state_hints(recon: dict[str, Any]) -> dict[str, Any]:
    return dict(recon.get("state_hints") or {})


def _check_collateral_value_integrity(hints: dict[str, Any]) -> InvariantResult:
    """Borrow capacity must not exceed fair collateral under manipulation flag."""
    manipulable = bool(hints.get("oracle_manipulable"))
    collateral = float(hints.get("collateral_liquidity_usd") or 0)
    max_flash = float(hints.get("max_flash_loan_usd") or 0)
    if manipulable and max_flash >= collateral * 0.5:
        return InvariantResult(
            invariant_id="collateral_value_integrity",
            passed=False,
            counterexample={
                "oracle_manipulable": True,
                "max_flash_loan_usd": max_flash,
                "collateral_liquidity_usd": collateral,
            },
            engine="deterministic",
        )
    return InvariantResult(
        invariant_id="collateral_value_integrity",
        passed=True,
        counterexample=None,
        engine="deterministic",
    )


def _check_reserve_isolation(hints: dict[str, Any]) -> InvariantResult:
    treasury = float(hints.get("treasury_balance_usd") or 0)
    max_flash = float(hints.get("max_flash_loan_usd") or 0)
    if max_flash > treasury:
        return InvariantResult(
            invariant_id="reserve_isolation",
            passed=False,
            counterexample={"max_flash_loan_usd": max_flash, "treasury_balance_usd": treasury},
            engine="deterministic",
        )
    return InvariantResult(
        invariant_id="reserve_isolation",
        passed=True,
        counterexample=None,
        engine="deterministic",
    )


def _check_flash_loan_atomicity(hints: dict[str, Any]) -> InvariantResult:
    if not hints.get("flash_loan_available"):
        return InvariantResult(
            invariant_id="flash_loan_atomicity",
            passed=True,
            counterexample=None,
            engine="deterministic",
        )
    if not hints.get("cross_protocol_enabled"):
        return InvariantResult(
            invariant_id="flash_loan_atomicity",
            passed=True,
            counterexample=None,
            engine="deterministic",
        )
    max_flash = float(hints.get("max_flash_loan_usd") or 0)
    collateral = float(hints.get("collateral_liquidity_usd") or 1)
    ratio = max_flash / collateral
    if ratio > 0.6:
        return InvariantResult(
            invariant_id="flash_loan_atomicity",
            passed=False,
            counterexample={"flash_to_collateral_ratio": ratio},
            engine="deterministic",
        )
    return InvariantResult(
        invariant_id="flash_loan_atomicity",
        passed=True,
        counterexample=None,
        engine="deterministic",
    )


_DETERMINISTIC_CHECKS: dict[str, Callable[[dict[str, Any]], InvariantResult]] = {
    "collateral_value_integrity": _check_collateral_value_integrity,
    "reserve_isolation": _check_reserve_isolation,
    "flash_loan_atomicity": _check_flash_loan_atomicity,
}


def run_deterministic_invariants(recon: dict[str, Any]) -> list[InvariantResult]:
    hints = _state_hints(recon)
    results: list[InvariantResult] = []
    declared = {inv.get("id") for inv in recon.get("invariants") or [] if inv.get("id")}
    for inv_id, checker in _DETERMINISTIC_CHECKS.items():
        if declared and inv_id not in declared:
            continue
        results.append(checker(hints))
    return results


def _run_hypothesis_invariants(recon: dict[str, Any], *, max_examples: int) -> list[InvariantResult]:
    try:
        from hypothesis import given, settings
        from hypothesis import strategies as st
    except ImportError:
        return []

    hints = _state_hints(recon)
    if not hints.get("oracle_manipulable"):
        return []

    max_flash_cap = float(hints.get("max_flash_loan_usd") or 1_000_000)
    collateral_cap = float(hints.get("collateral_liquidity_usd") or 1_000_000)
    captured: list[InvariantResult] = []

    @given(
        loan=st.floats(min_value=1.0, max_value=max(max_flash_cap * 1.5, 1.0)),
        manipulation=st.floats(min_value=1.0, max_value=150.0),
    )
    @settings(max_examples=max_examples, deadline=None)
    def prop_oracle_borrow_bounded(loan: float, manipulation: float) -> None:
        effective_collateral = collateral_cap / (1 + manipulation / 100)
        borrow_capacity = effective_collateral * 0.8
        if loan > borrow_capacity:
            captured.append(
                InvariantResult(
                    invariant_id="oracle_staleness_bound",
                    passed=False,
                    counterexample={
                        "loan_amount_usd": loan,
                        "price_manipulation_pct": manipulation,
                        "borrow_capacity_usd": borrow_capacity,
                    },
                    engine="hypothesis",
                )
            )
            raise AssertionError("borrow exceeds manipulated collateral capacity")

    try:
        prop_oracle_borrow_bounded()
    except AssertionError:
        pass

    if captured:
        return captured
    return [
        InvariantResult(
            invariant_id="oracle_staleness_bound",
            passed=True,
            counterexample=None,
            engine="hypothesis",
        )
    ]


def run_invariant_tests(
    recon_path: Path,
    *,
    use_hypothesis: bool = True,
    max_examples: int = 50,
) -> dict[str, Any]:
    recon = load_recon(recon_path)
    deterministic = run_deterministic_invariants(recon)
    hypothesis_results: list[InvariantResult] = []
    if use_hypothesis:
        hypothesis_results = _run_hypothesis_invariants(recon, max_examples=max_examples)

    all_results = deterministic + hypothesis_results
    failures = [r for r in all_results if not r.passed]
    return {
        "target_id": recon.get("target_id", ""),
        "recon_path": str(recon_path),
        "total": len(all_results),
        "passed": len(all_results) - len(failures),
        "failed": len(failures),
        "results": [r.to_dict() for r in all_results],
        "refinement_seeds": [
            {
                "invariant_id": f.invariant_id,
                "counterexample": f.counterexample,
                "engine": f.engine,
            }
            for f in failures
        ],
    }