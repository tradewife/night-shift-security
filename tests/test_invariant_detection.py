"""Tests for invariant detection layer (B10_NO_INVARIANT_DETECTOR fix)."""

import pytest

from night_shift_security.data.schemas import (
    AttackCandidateResult,
    AttackResult,
    AttackVector,
    InvariantViolation,
    ReproductionStep,
    Severity,
)
from night_shift_security.validation.invariant_detection import (
    _is_fee_only,
    _is_fee_only_delta,
    _is_fee_only_lamports,
    detect_invariant_violations,
    stamp_detected_invariants,
)
from night_shift_security.validation.evidence_grading import compute_evidence_grade


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_candidate(
    *,
    template_id: str = "kamino",
    target_id: str = "kamino",
    catalog_analogue: bool = False,
    catalog_exploit_id: str = "",
    solana_reproduced: bool = False,
    solana_confirmed: bool = False,
    reproduction_tier: str = "solana_validator",
    invariant_violation_count: int = 0,
    mean_economic_impact_usd: float = 100_000.0,
    has_repro_steps: bool = True,
    solana_evidence: dict | None = None,
    fork_evidence: dict | None = None,
    v4_payload: dict | None = None,
    results: list | None = None,
) -> AttackCandidateResult:
    params: dict = {}
    if v4_payload is not None:
        params["candidate"] = v4_payload

    meta: dict = {}
    if v4_payload is not None:
        meta["candidate"] = v4_payload

    vector = AttackVector(
        template_id=template_id,
        target_id=target_id,
        parameters=params,
        metadata=meta,
    )

    if results is None:
        results = []
        if has_repro_steps:
            steps = [
                ReproductionStep(
                    action="execute_exploit",
                    actor="attacker",
                    details={"instruction": "exploit_ix"},
                )
            ]
        else:
            steps = []
        results.append(
            AttackResult(
                vector=vector,
                success=True,
                severity=Severity.HIGH,
                economic_impact_usd=mean_economic_impact_usd,
                reproduction_steps=steps,
            )
        )

    cand = AttackCandidateResult(
        vector=vector,
        success_rate=1.0,
        mean_severity_score=0.8,
        mean_economic_impact_usd=mean_economic_impact_usd,
        reproducibility=1.0,
        generality=0.5,
        realism_score=0.8,
        invariant_violation_count=invariant_violation_count,
        severity_score=0.8,
        reproduction_tier=reproduction_tier,
        solana_reproduced=solana_reproduced,
        solana_confirmed=solana_confirmed,
        solana_evidence=solana_evidence or {},
        fork_evidence=fork_evidence or {},
        catalog_analogue=catalog_analogue,
        catalog_exploit_id=catalog_exploit_id,
        results=results,
    )
    cand.mc_simulations = 0  # skip MC gate
    return cand


def _klend_evidence(
    *,
    probe_id: str = "refresh_reserve_live",
    harness_mode: str = "live_executed",
    stale_oracle: bool = True,
    slot_delta: int = 5,
    balance_delta: int = 0,
    impact_usd: float = 100_000.0,
) -> dict:
    output = ""
    if stale_oracle:
        output = "Price is too old (oracle staleness)"
    return {
        "method": "solana_klend_harness",
        "probe_id": probe_id,
        "harness_mode": harness_mode,
        "solana_output": output,
        "reserve_last_update_slot_delta": slot_delta,
        "balance_delta_lamports": balance_delta,
        "balance_verified": balance_delta != 0 or impact_usd > 0,
        "impact_usd": impact_usd,
        "impact_lamports": int(impact_usd * 1e9),
    }


def _v4_candidate_payload(
    *,
    measured: bool = True,
    above_threshold: list | None = None,
    threshold_raw: str = "1000000",
) -> dict:
    return {
        "candidate_schema_version": 4,
        "impact_oracle": {
            "measured": measured,
            "above_threshold_tokens": above_threshold or [],
            "threshold_raw_units": threshold_raw,
        },
    }


def _fork_measured_evidence(
    *,
    measured_impact: bool = True,
    raw_delta: int = 500_000,
    source_account: str = "0xOracleAccount",
) -> dict:
    return {
        "evidence_kind": "measured_impact_oracle.v1",
        "measured_impact": measured_impact,
        "delta": {
            "tokens": [
                {
                    "raw_delta": raw_delta,
                    "source_account": source_account,
                }
            ],
        },
    }


# ---------------------------------------------------------------------------
# Test: Non-catalogue KLend candidate with stale oracle → invariant stamped
# ---------------------------------------------------------------------------

class TestKLendReserveFreshness:
    def test_stale_oracle_stamps_invariant(self):
        cand = _make_candidate(
            template_id="kamino",
            catalog_analogue=False,
            solana_reproduced=True,
            reproduction_tier="solana_validator",
            solana_evidence=_klend_evidence(stale_oracle=True, probe_id="refresh_reserve_live"),
            v4_payload=_v4_candidate_payload(),
        )
        count = stamp_detected_invariants(cand)
        assert count >= 1
        ids = {v.invariant_id for r in cand.results for v in r.invariant_violations}
        assert "klend_reserve_freshness_bound" in ids
        assert cand.invariant_violation_count >= 1

    def test_no_stale_oracle_no_invariant(self):
        cand = _make_candidate(
            template_id="kamino",
            catalog_analogue=False,
            solana_reproduced=True,
            solana_evidence=_klend_evidence(
                stale_oracle=False,
                probe_id="deposit_reserve_liquidity_live",
                slot_delta=0,
            ),
        )
        count = stamp_detected_invariants(cand)
        assert count == 0
        ids = {v.invariant_id for r in cand.results for v in r.invariant_violations}
        assert "klend_reserve_freshness_bound" not in ids

    def test_fee_only_no_invariant(self):
        cand = _make_candidate(
            template_id="kamino",
            catalog_analogue=False,
            solana_reproduced=True,
            solana_evidence=_klend_evidence(
                stale_oracle=True,
                probe_id="refresh_reserve_live",
                balance_delta=5000,  # within fee threshold
                impact_usd=0.005,    # below fee threshold
            ),
        )
        count = stamp_detected_invariants(cand)
        # fee-only filter should prevent klend invariant
        klend_stamped = any(
            v.invariant_id == "klend_reserve_freshness_bound"
            for r in cand.results
            for v in r.invariant_violations
        )
        # May still get other adapters, but not klend if fee-only
        if klend_stamped:
            pytest.fail("klend invariant should not fire for fee-only CPI")


# ---------------------------------------------------------------------------
# Test: Catalogue analogue with same evidence → 0
# ---------------------------------------------------------------------------

class TestCatalogueFilter:
    def test_catalogue_analogue_no_invariant(self):
        cand = _make_candidate(
            template_id="kamino",
            catalog_analogue=True,
            catalog_exploit_id="mango-markets-2022",
            solana_reproduced=True,
            solana_evidence=_klend_evidence(stale_oracle=True),
            v4_payload=_v4_candidate_payload(),
        )
        count = stamp_detected_invariants(cand)
        assert count == 0

    def test_catalog_exploit_id_no_invariant(self):
        cand = _make_candidate(
            template_id="kamino",
            catalog_analogue=False,
            catalog_exploit_id="mango-markets-2022",
            solana_reproduced=True,
            solana_evidence=_klend_evidence(stale_oracle=True),
        )
        count = stamp_detected_invariants(cand)
        assert count == 0


# ---------------------------------------------------------------------------
# Test: Measured balance conservation invariant
# ---------------------------------------------------------------------------

class TestBalanceConservation:
    def test_fork_measured_evidence_stamps(self):
        cand = _make_candidate(
            template_id="uniswap_v4",
            catalog_analogue=False,
            fork_evidence=_fork_measured_evidence(measured_impact=True, raw_delta=500_000),
            v4_payload=_v4_candidate_payload(),
            solana_reproduced=False,
        )
        cand.fork_reproduced = True
        count = stamp_detected_invariants(cand)
        assert count >= 1
        ids = {v.invariant_id for r in cand.results for v in r.invariant_violations}
        assert "measured_balance_conservation" in ids

    def test_solana_balance_verified_stamps(self):
        cand = _make_candidate(
            template_id="kamino",
            catalog_analogue=False,
            solana_reproduced=True,
            solana_evidence={
                "balance_verified": True,
                "balance_delta_lamports": 50_000,  # above fee threshold
                "impact_usd": 100_000,
            },
            v4_payload=_v4_candidate_payload(),
        )
        count = stamp_detected_invariants(cand)
        assert count >= 1
        ids = {v.invariant_id for r in cand.results for v in r.invariant_violations}
        assert "measured_balance_conservation" in ids

    def test_fee_only_delta_no_invariant(self):
        cand = _make_candidate(
            template_id="kamino",
            catalog_analogue=False,
            solana_reproduced=True,
            solana_evidence={
                "balance_verified": True,
                "balance_delta_lamports": 5000,  # fee-only
                "impact_usd": 0.005,
            },
        )
        count = stamp_detected_invariants(cand)
        conservation_stamped = any(
            v.invariant_id == "measured_balance_conservation"
            for r in cand.results
            for v in r.invariant_violations
        )
        assert not conservation_stamped

    def test_no_reproduction_no_invariant(self):
        cand = _make_candidate(
            template_id="kamino",
            catalog_analogue=False,
            solana_reproduced=False,
        )
        cand.fork_reproduced = False
        count = stamp_detected_invariants(cand)
        assert count == 0

    def test_no_v4_payload_no_invariant(self):
        cand = _make_candidate(
            template_id="kamino",
            catalog_analogue=False,
            solana_reproduced=True,
            solana_evidence={
                "balance_verified": True,
                "balance_delta_lamports": 50_000,
                "impact_usd": 100_000,
            },
            v4_payload=None,
        )
        count = stamp_detected_invariants(cand)
        conservation_stamped = any(
            v.invariant_id == "measured_balance_conservation"
            for r in cand.results
            for v in r.invariant_violations
        )
        assert not conservation_stamped


# ---------------------------------------------------------------------------
# Test: Oracle deviation invariant
# ---------------------------------------------------------------------------

class TestOracleDeviation:
    def test_above_threshold_stamps(self):
        cand = _make_candidate(
            template_id="kamino",
            catalog_analogue=False,
            solana_reproduced=True,
            v4_payload=_v4_candidate_payload(
                measured=True,
                above_threshold=["token_mint_123"],
            ),
            solana_evidence={"impact_usd": 100_000},
        )
        count = stamp_detected_invariants(cand)
        assert count >= 1
        ids = {v.invariant_id for r in cand.results for v in r.invariant_violations}
        assert "oracle_deviation_bound" in ids

    def test_fork_oracle_source_stamps(self):
        cand = _make_candidate(
            template_id="kamino",
            catalog_analogue=False,
            fork_evidence=_fork_measured_evidence(
                measured_impact=True,
                raw_delta=100_000,
                source_account="0xOracleAddress",
            ),
            v4_payload=_v4_candidate_payload(),
        )
        cand.fork_reproduced = True
        count = stamp_detected_invariants(cand)
        assert count >= 1
        ids = {v.invariant_id for r in cand.results for v in r.invariant_violations}
        assert "oracle_deviation_bound" in ids

    def test_no_deviation_no_invariant(self):
        cand = _make_candidate(
            template_id="kamino",
            catalog_analogue=False,
            solana_reproduced=True,
            v4_payload=_v4_candidate_payload(measured=False, above_threshold=[]),
            solana_evidence={"impact_usd": 0},
        )
        count = stamp_detected_invariants(cand)
        deviation_stamped = any(
            v.invariant_id == "oracle_deviation_bound"
            for r in cand.results
            for v in r.invariant_violations
        )
        assert not deviation_stamped


# ---------------------------------------------------------------------------
# Test: Fee-only helper
# ---------------------------------------------------------------------------

class TestFeeOnlyHelpers:
    def test_fee_only_lamports(self):
        assert _is_fee_only_lamports(5000)
        assert _is_fee_only_lamports(-5000)
        assert not _is_fee_only_lamports(50_000)

    def test_fee_only_delta_no_tokens(self):
        assert _is_fee_only_delta({"tokens": []})
        assert _is_fee_only_delta({})

    def test_fee_only_delta_with_nonzero_token(self):
        assert not _is_fee_only_delta({"tokens": [{"raw_delta": 100_000}]})

    def test_is_fee_only_combined(self):
        assert _is_fee_only(5000, 0.005, {})
        assert not _is_fee_only(50_000, 100.0, {})


# ---------------------------------------------------------------------------
# Test: Patched/negative-control benchmark → 0
# ---------------------------------------------------------------------------

class TestBenchmarkNegative:
    def test_patched_benchmark_no_invariant(self):
        cand = _make_candidate(
            template_id="kamino",
            catalog_analogue=False,
            solana_reproduced=True,
            solana_evidence={
                "method": "solana_fixture",
                "balance_verified": True,
                "balance_delta_lamports": 0,
                "impact_usd": 0,
                "verifier_method": "catalog_exempt",
            },
            mean_economic_impact_usd=0,
        )
        count = stamp_detected_invariants(cand)
        # No measured delta, no oracle evidence → no invariants
        assert count == 0


# ---------------------------------------------------------------------------
# Test: Grade 4 path with stamped invariants
# ---------------------------------------------------------------------------

class TestGrade4Path:
    def test_stamped_candidate_reaches_grade_4(self):
        cand = _make_candidate(
            template_id="kamino",
            catalog_analogue=False,
            solana_reproduced=True,
            reproduction_tier="solana_validator",
            solana_evidence=_klend_evidence(
                stale_oracle=True,
                probe_id="refresh_reserve_live",
                balance_delta=50_000,
                impact_usd=100_000,
            ),
            v4_payload=_v4_candidate_payload(),
            mean_economic_impact_usd=100_000,
        )
        # Pass MC (mc_simulations=0 → auto-pass)
        cand.pbo = 0.0
        cand.cpcv_verdict = "SAFE"

        # Stamp invariants
        count = stamp_detected_invariants(cand)
        assert count >= 1

        # Compute grade
        grade = compute_evidence_grade(cand, {"level_1_mc_min": 0.70, "max_pbo": 0.30})
        assert grade == 4, f"Expected grade 4, got {grade}"

    def test_unstamped_candidate_stays_below_grade_4(self):
        cand = _make_candidate(
            template_id="kamino",
            catalog_analogue=False,
            solana_reproduced=True,
            reproduction_tier="solana_validator",
            solana_evidence=_klend_evidence(stale_oracle=False),
            mean_economic_impact_usd=100_000,
        )
        cand.pbo = 0.0
        cand.cpcv_verdict = "SAFE"
        # Do NOT stamp invariants
        grade = compute_evidence_grade(cand, {"level_1_mc_min": 0.70, "max_pbo": 0.30})
        assert grade <= 3, f"Expected grade <= 3 without invariants, got {grade}"
