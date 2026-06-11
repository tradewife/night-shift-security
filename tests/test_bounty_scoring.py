"""Tests for bounty readiness scoring and candidate ledger."""

import json
from pathlib import Path

from night_shift_security.bounty.candidates import rank_findings_by_bounty_score, write_bounty_candidates_jsonl
from night_shift_security.bounty.pipeline import build_bounty_submission, export_bounty_pack
from night_shift_security.bounty.scoring import compute_bounty_score, resolve_program_for_finding
from night_shift_security.data.bounty_program import BountyProgram
from night_shift_security.data.schemas import Finding, InvariantViolation, ReproductionStep, Severity


def _finding(**overrides) -> Finding:
    base = Finding(
        finding_id="NSS-0001",
        template_id="flash_loan_oracle",
        target_id="kamino",
        severity=Severity.CRITICAL,
        severity_score=0.55,
        economic_impact_usd=15_000_000.0,
        capital_required_usd=500_000.0,
        reproducibility=1.0,
        parameters={"loan_amount_usd": 50_000_000},
        invariant_violations=[
            InvariantViolation("oracle_price_integrity", "Oracle integrity", "~$0.10", "$0.20")
        ],
        reproduction_steps=[ReproductionStep("flash_loan", "attacker", {"amount_usd": 50_000_000})],
        evidence_grade=4,
        evidence_grade_label="root_cause_artifacts",
        axis_survival_rate=0.62,
        priority_score=0.7,
        novelty_score=0.5,
        reproduction_tier="solana_fixture",
        solana_reproduced=True,
        catalog_analogue=True,
        rediscovered_exploit_id="mango-markets-2022",
        solana_evidence={"method": "solana_fixture", "exploit_id": "mango-markets-2022"},
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


def test_grade_below_three_blocks_score():
    score = compute_bounty_score(
        _finding(
            evidence_grade=2,
            reproduction_tier="simulation",
            solana_reproduced=False,
            solana_evidence={},
        )
    )
    assert score.bounty_readiness == 0.0
    assert score.submission_recommendation == "hold"


def test_validator_outranks_fixture():
    validator = compute_bounty_score(
        _finding(
            reproduction_tier="solana_validator",
            solana_evidence={"method": "solana_validator", "exploit_id": "mango-markets-2022"},
        )
    )
    fixture = compute_bounty_score(_finding())
    assert validator.bounty_readiness > fixture.bounty_readiness


def test_catalog_analogue_penalty():
    analogue = compute_bounty_score(_finding(catalog_analogue=True))
    novel = compute_bounty_score(_finding(catalog_analogue=False))
    assert novel.bounty_readiness > analogue.bounty_readiness


def test_program_cap_limits_payout_proxy():
    program = BountyProgram(
        platform="immunefi",
        slug="kamino",
        name="Kamino",
        ecosystem="solana",
        max_bounty_usd=1_500_000,
        product_types=("lending",),
        templates=("flash_loan_oracle",),
        catalog_analogue="mango-markets-2022",
    )
    score = compute_bounty_score(
        _finding(economic_impact_usd=110_000_000.0),
        program,
    )
    assert score.expected_payout_proxy_usd <= 1_500_000 * 0.15


def test_deposit_required_penalty():
    program = BountyProgram(
        platform="cantina",
        slug="euler",
        name="Euler",
        ecosystem="evm",
        max_bounty_usd=7_500_000,
        product_types=("lending",),
        templates=("reentrancy",),
        catalog_analogue="euler-finance-2023",
        cantina_id="4d285eee-602e-440a-845e-25e155cec26a",
        deposit_required=True,
    )
    with_deposit = compute_bounty_score(_finding(target_id="euler"), program)
    without = compute_bounty_score(
        _finding(target_id="euler"),
        BountyProgram(
            platform="cantina",
            slug="euler",
            name="Euler",
            ecosystem="evm",
            max_bounty_usd=7_500_000,
            product_types=("lending",),
            templates=("reentrancy",),
            catalog_analogue="euler-finance-2023",
            deposit_required=False,
        ),
    )
    assert with_deposit.bounty_readiness < without.bounty_readiness


def test_resolve_program_for_kamino():
    program = resolve_program_for_finding(_finding())
    assert program is not None
    assert program.slug == "kamino"


def test_export_bounty_pack_sorted_by_readiness(tmp_path: Path):
    high = _finding(
        finding_id="NSS-HIGH",
        evidence_grade=4,
        reproduction_tier="solana_validator",
        solana_evidence={"method": "solana_validator", "exploit_id": "mango-markets-2022"},
        economic_impact_usd=50_000_000,
    )
    low = _finding(
        finding_id="NSS-LOW",
        evidence_grade=3,
        reproduction_tier="simulation",
        economic_impact_usd=1_000_000,
        axis_survival_rate=0.2,
        priority_score=0.1,
        novelty_score=0.1,
    )
    path = export_bounty_pack(
        [low, high],
        {"run_at": "2026-06-11T00:00:00+00:00"},
        tmp_path,
        min_severity="high",
    )
    pack = json.loads(path.read_text())
    assert pack["submissions"][0]["submission_id"] == "NSS-HIGH"
    assert "bounty_readiness" in pack["submissions"][0]


def test_build_bounty_submission_includes_score_fields():
    sub = build_bounty_submission(_finding())
    assert "bounty_readiness" in sub
    assert "expected_payout_proxy_usd" in sub
    assert "submission_recommendation" in sub


def test_write_bounty_candidates_jsonl(tmp_path: Path):
    scored = rank_findings_by_bounty_score([
        _finding(),
        _finding(
            evidence_grade=1,
            reproduction_tier="simulation",
            solana_reproduced=False,
            solana_evidence={},
        ),
    ])
    out = tmp_path / "candidates.jsonl"
    write_bounty_candidates_jsonl(scored, out, run_at="2026-06-11T00:00:00+00:00")
    lines = out.read_text().strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["yield_signals"]["attack_surface"] == "oracle"
    assert record["bounty_readiness"] > 0