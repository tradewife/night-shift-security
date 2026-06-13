"""Tests for recon-driven invariant engine."""

from pathlib import Path

from night_shift_security.invariants.pbt import run_deterministic_invariants, run_invariant_tests


def test_kamino_recon_surfaces_counterexamples():
    recon_path = Path("sources/kamino/recon.json")
    results = run_deterministic_invariants(
        __import__("json").loads(recon_path.read_text())
    )
    failures = [r for r in results if not r.passed]
    assert failures, "kamino recon hints should trigger deterministic counterexamples"
    ids = {f.invariant_id for f in failures}
    assert "collateral_value_integrity" in ids


def test_run_invariant_tests_writes_refinement_seeds(tmp_path: Path):
    recon = {
        "target_id": "test",
        "invariants": [{"id": "reserve_isolation"}],
        "state_hints": {
            "treasury_balance_usd": 100,
            "max_flash_loan_usd": 500,
        },
    }
    recon_path = tmp_path / "recon.json"
    recon_path.write_text(__import__("json").dumps(recon))
    result = run_invariant_tests(recon_path, use_hypothesis=False)
    assert result["failed"] >= 1
    assert result["refinement_seeds"]