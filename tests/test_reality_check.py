"""Tests for lab vs deployed reality classification."""

from night_shift_security.data.schemas import Finding, InvariantViolation, ReproductionStep, Severity
from night_shift_security.validation.reality_check import (
    compute_reality_check_finding,
    infer_reproduction_method,
)


def _fixture_finding(**overrides) -> Finding:
    base = Finding(
        finding_id="NSS-0001",
        template_id="flash_loan_oracle",
        target_id="kamino",
        severity=Severity.HIGH,
        severity_score=0.5,
        economic_impact_usd=1_000_000.0,
        capital_required_usd=100_000.0,
        reproducibility=1.0,
        parameters={},
        invariant_violations=[
            InvariantViolation("oracle_price_integrity", "desc", "fair", "manipulated"),
        ],
        reproduction_steps=[ReproductionStep("manipulate_oracle", "attacker", {})],
        solana_reproduced=True,
        solana_evidence={
            "method": "solana_fixture",
            "exploit_id": "mango-markets-2022",
            "target_id": "mango-markets-2022",
        },
        evidence_grade=1,
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


def test_infer_reproduction_method_fixture():
    assert infer_reproduction_method(
        solana_evidence={"method": "solana_fixture"},
        solana_reproduced=True,
    ) == "solana_fixture"


def test_catalog_analogue_detected_for_kamino_fixture():
    rc = compute_reality_check_finding(_fixture_finding())
    assert rc.catalog_analogue is True
    assert rc.deployed_viable is False
    assert rc.reproduction_tier == "solana_fixture"
    assert rc.submission_readiness == "shoestring"


def test_deployed_viable_for_validator():
    rc = compute_reality_check_finding(
        _fixture_finding(
            target_id="mango-markets-2022",
            solana_evidence={
                "method": "solana_validator",
                "exploit_id": "mango-markets-2022",
            },
            evidence_grade=3,
        )
    )
    assert rc.deployed_viable is True
    assert rc.catalog_analogue is False