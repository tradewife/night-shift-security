"""HTB-style benchmark harness — detect vulnerable, reject patched, label discipline."""

from __future__ import annotations

from pathlib import Path

import pytest

from night_shift_security.benchmarks.runner import (
    DEFAULT_MANIFEST,
    evaluate_all,
    evaluate_challenge,
    load_manifest,
)

REPO = Path(__file__).resolve().parents[1]


def test_manifest_loads() -> None:
    manifest = load_manifest()
    assert manifest["schema_version"] == "benchmarks.v1"
    assert len(manifest["challenges"]) >= 6


@pytest.mark.parametrize(
    "challenge_id",
    [
        "evm_treasury_drain_vulnerable",
        "evm_treasury_drain_patched",
        "solana_reserve_delta_vulnerable",
        "solana_reserve_delta_patched",
        "catalog_mango_replay_not_novel",
        "solodit_analogue_stays_untrusted",
    ],
)
def test_each_benchmark_challenge_passes(challenge_id: str) -> None:
    manifest = load_manifest()
    challenge = next(c for c in manifest["challenges"] if c["id"] == challenge_id)
    result = evaluate_challenge(challenge)
    assert result.passed, f"{challenge_id}: {result.detail}"


def test_evaluate_all_green() -> None:
    results = evaluate_all(DEFAULT_MANIFEST)
    failures = [r for r in results if not r.passed]
    assert not failures, [f.to_dict() for f in failures]


def test_vulnerable_evm_measures_patched_does_not() -> None:
    manifest = load_manifest()
    vuln = next(c for c in manifest["challenges"] if c["id"] == "evm_treasury_drain_vulnerable")
    patch = next(c for c in manifest["challenges"] if c["id"] == "evm_treasury_drain_patched")
    vuln_result = evaluate_challenge(vuln)
    patch_result = evaluate_challenge(patch)
    assert vuln_result.measured_impact is True
    assert patch_result.measured_impact is False


def test_catalog_replay_not_labelled_novel() -> None:
    manifest = load_manifest()
    challenge = next(c for c in manifest["challenges"] if c["id"] == "catalog_mango_replay_not_novel")
    result = evaluate_challenge(challenge)
    assert result.passed
    assert "novel=False" in result.detail


def test_benchmark_fixtures_reference_foundry_contract() -> None:
    ref = REPO / "foundry" / "src" / "VulnerableProtocol.sol"
    assert ref.is_file()