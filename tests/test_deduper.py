"""Tests for findings deduplication."""

from night_shift_security.data.schemas import Finding, InvariantViolation, Severity
from night_shift_security.export.deduper import (
    canonical_key,
    dedupe_findings,
    primary_invariant,
    protocol_id,
)
from night_shift_security.export.dataset import build_public_feed


def _finding(
    fid: str,
    template: str = "governance_capture",
    target: str = "beanstalk",
    params: dict | None = None,
    invariant: str = "treasury_non_decreasing",
    score: float = 0.9,
    rediscovered: str = "",
) -> Finding:
    return Finding(
        finding_id=fid,
        template_id=template,
        target_id=target,
        severity=Severity.CRITICAL,
        severity_score=score,
        economic_impact_usd=1_000_000,
        capital_required_usd=0,
        reproducibility=0.95,
        parameters=params or {"voting_power_pct": 51.0, "use_flash_loan": True},
        invariant_violations=[
            InvariantViolation(
                invariant_id=invariant,
                description="test",
                expected="x",
                actual="y",
            )
        ],
        reproduction_steps=[],
        rediscovered_exploit_id=rediscovered,
    )


def test_canonical_key_stable_across_param_order():
    a = _finding("NSS-0001", params={"b": 1, "a": True})
    b = _finding("NSS-0002", params={"a": True, "b": 1})
    assert canonical_key(a) == canonical_key(b)


def test_dedupe_collapses_grid_and_catalog_duplicates():
    catalog = _finding("NSS-0001", rediscovered="beanstalk-2022", score=0.92)
    grid_dup = _finding("NSS-0042", score=0.91)
    distinct = _finding(
        "NSS-0003",
        template="treasury_drain",
        target="ronin",
        params={"withdrawal_pct": 100.0},
        invariant="authorized_withdrawal_only",
    )
    deduped, report = dedupe_findings([catalog, grid_dup, distinct])
    assert report.before_count == 3
    assert report.after_count == 2
    assert report.dropped_count == 1
    assert deduped[0].finding_id == "NSS-0001"


def test_protocol_falls_back_to_rediscovered_exploit_id():
    f = _finding("NSS-0001", target="", rediscovered="nomad-bridge-2022")
    assert protocol_id(f) == "nomad-bridge-2022"


def test_primary_invariant_empty_when_none():
    f = _finding("NSS-0001")
    f.invariant_violations = []
    assert primary_invariant(f) == ""


def test_public_feed_includes_dedupe_stats():
    findings = [
        _finding("NSS-0001", score=0.92),
        _finding("NSS-0002", score=0.90),
    ]
    feed = build_public_feed(findings, {"run_at": "2026-06-06T00:00:00+00:00"})
    assert feed["dedupe"]["before_count"] == 2
    assert feed["dedupe"]["after_count"] == 1
    assert feed["summary"]["total_findings"] == 1


def test_webhook_env_only_when_set(monkeypatch):
    from night_shift_security.monitoring.hooks import resolve_webhook_url

    monkeypatch.delenv("NIGHT_SHIFT_WEBHOOK_URL", raising=False)
    assert resolve_webhook_url({}) == ""
    monkeypatch.setenv("NIGHT_SHIFT_WEBHOOK_URL", "https://example.com/hook")
    assert resolve_webhook_url({}) == "https://example.com/hook"
    assert resolve_webhook_url({"webhook_url": "https://config.example/hook"}) == "https://config.example/hook"