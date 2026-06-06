"""Phase 3 tests — new templates, disclosure, API pagination/filtering."""

import json
import urllib.error
import urllib.request
from pathlib import Path

from night_shift_security.api.query import filter_findings, paginate_findings, parse_query_params
from night_shift_security.api.server import serve_background
from night_shift_security.core.evaluation import evaluate_attack_vector
from night_shift_security.data.exploit_catalog import get_exploit_catalog
from night_shift_security.data.schemas import AttackVector, Finding, Severity
from night_shift_security.domain.attack_templates.base import get_template, list_templates
from night_shift_security.export.dataset import build_public_feed, export_dataset
from night_shift_security.export.disclosure import (
    apply_disclosure_policy,
    build_disclosure_report,
    redact_finding_for_public,
    update_disclosure_status,
)

import night_shift_security.domain.attack_templates.composability_risk  # noqa: F401
import night_shift_security.domain.attack_templates.upgradeability_risk  # noqa: F401
import night_shift_security.domain.attack_templates.access_control_escalation  # noqa: F401


def test_phase3_templates_registered():
    templates = list_templates()
    assert "composability_risk" in templates
    assert "upgradeability_risk" in templates
    assert "access_control_escalation" in templates


def test_composability_rediscovers_curve():
    catalog = get_exploit_catalog()
    exploit = next(e for e in catalog if e.exploit_id == "curve-vyper-2023")
    vector = AttackVector(
        template_id="composability_risk",
        parameters=exploit.known_parameters,
    )
    cand = evaluate_attack_vector(vector, [exploit.state])
    assert not cand.rejected
    assert cand.mean_economic_impact_usd > 0


def test_upgradeability_rediscovers_audius():
    catalog = get_exploit_catalog()
    exploit = next(e for e in catalog if e.exploit_id == "audius-2022")
    vector = AttackVector(
        template_id="upgradeability_risk",
        parameters=exploit.known_parameters,
    )
    cand = evaluate_attack_vector(vector, [exploit.state])
    assert not cand.rejected


def test_access_control_rediscovers_nomad():
    catalog = get_exploit_catalog()
    exploit = next(e for e in catalog if e.exploit_id == "nomad-bridge-2022")
    vector = AttackVector(
        template_id="access_control_escalation",
        parameters=exploit.known_parameters,
    )
    cand = evaluate_attack_vector(vector, [exploit.state])
    assert not cand.rejected
    assert cand.mean_economic_impact_usd >= 100_000_000


def test_catalog_has_16_exploits():
    assert len(get_exploit_catalog()) == 16


def test_disclosure_auto_embargoes_critical():
    finding = Finding(
        finding_id="NSS-0001",
        template_id="governance_capture",
        target_id="",
        severity=Severity.CRITICAL,
        severity_score=0.9,
        economic_impact_usd=1_000_000,
        capital_required_usd=0,
        reproducibility=0.9,
        parameters={"voting_power_pct": 51},
        invariant_violations=[],
        reproduction_steps=[],
    )
    tagged = apply_disclosure_policy([finding])
    assert tagged[0].disclosure_status == "embargoed"


def test_disclosure_redacts_embargoed_details():
    finding = Finding(
        finding_id="NSS-0001",
        template_id="reentrancy",
        target_id="",
        severity=Severity.CRITICAL,
        severity_score=0.9,
        economic_impact_usd=1_000_000,
        capital_required_usd=0,
        reproducibility=0.9,
        parameters={"recursion_depth": 10},
        invariant_violations=[],
        reproduction_steps=[],
        disclosure_status="embargoed",
    )
    public = redact_finding_for_public(finding)
    assert public["parameters"]["recursion_depth"] == "[redacted]"
    assert public["reproduction_steps"] == []
    assert "disclosure_note" in public


def test_disclosure_status_update(tmp_path: Path):
    payload = {
        "run_at": "2026-06-06T00:00:00+00:00",
        "findings": [
            {"finding_id": "NSS-0001", "disclosure_status": "embargoed"},
            {"finding_id": "NSS-0002", "disclosure_status": "draft"},
        ],
    }
    path = tmp_path / "findings.json"
    path.write_text(json.dumps(payload))

    result = update_disclosure_status(path, "NSS-0001", "disclosed")
    assert result["disclosure_status"] == "disclosed"

    updated = json.loads(path.read_text())
    assert updated["findings"][0]["disclosure_status"] == "disclosed"
    assert "disclosed_at" in updated["findings"][0]


def test_build_disclosure_report():
    findings = apply_disclosure_policy([
        Finding(
            finding_id="NSS-0001",
            template_id="governance_capture",
            target_id="",
            severity=Severity.CRITICAL,
            severity_score=0.9,
            economic_impact_usd=1_000_000,
            capital_required_usd=0,
            reproducibility=0.9,
            parameters={},
            invariant_violations=[],
            reproduction_steps=[],
            mitigations=["timelock"],
        )
    ])
    report = build_disclosure_report(findings)
    assert report["by_status"]["embargoed"] == 1


def test_api_pagination_and_filtering():
    findings = [
        {"finding_id": "NSS-0001", "severity": "critical", "template_id": "governance_capture", "severity_score": 0.9},
        {"finding_id": "NSS-0002", "severity": "high", "template_id": "treasury_drain", "severity_score": 0.7},
        {"finding_id": "NSS-0003", "severity": "critical", "template_id": "reentrancy", "severity_score": 0.85},
    ]
    params = parse_query_params("severity=critical&page=1&limit=1")
    filtered = filter_findings(findings, params)
    assert len(filtered) == 2

    page = paginate_findings(filtered, params["page"], params["limit"])
    assert len(page["findings"]) == 1
    assert page["pagination"]["total"] == 2
    assert page["pagination"]["has_next"] is True


def test_api_filter_by_template():
    findings = [
        {"finding_id": "NSS-0001", "severity": "critical", "template_id": "composability_risk", "severity_score": 0.9},
        {"finding_id": "NSS-0002", "severity": "high", "template_id": "treasury_drain", "severity_score": 0.7},
    ]
    params = parse_query_params("template_id=composability_risk")
    filtered = filter_findings(findings, params)
    assert len(filtered) == 1
    assert filtered[0]["template_id"] == "composability_risk"


def test_public_feed_includes_disclosure_status(tmp_path: Path):
    findings = apply_disclosure_policy([
        Finding(
            finding_id="NSS-0001",
            template_id="governance_capture",
            target_id="",
            severity=Severity.CRITICAL,
            severity_score=0.9,
            economic_impact_usd=1_000_000,
            capital_required_usd=0,
            reproducibility=0.9,
            parameters={"v": 1},
            invariant_violations=[],
            reproduction_steps=[],
        )
    ])
    feed = build_public_feed(findings, {"run_at": "2026-06-06T00:00:00+00:00"})
    assert feed["findings"][0]["disclosure_status"] == "embargoed"


def test_api_paginated_endpoint(tmp_path: Path):
    findings = [
        Finding(
            finding_id=f"NSS-{i:04d}",
            template_id="governance_capture" if i % 2 else "treasury_drain",
            target_id="",
            severity=Severity.HIGH,
            severity_score=0.8 - i * 0.01,
            economic_impact_usd=1_000_000,
            capital_required_usd=0,
            reproducibility=0.9,
            parameters={},
            invariant_violations=[],
            reproduction_steps=[],
        )
        for i in range(1, 6)
    ]
    paths = export_dataset(findings, {"run_at": "2026-06-06T00:00:00+00:00"}, tmp_path)
    server = serve_background(port=18788, dataset_path=paths["latest"])

    try:
        url = "http://127.0.0.1:18788/api/v1/findings?page=1&limit=2&severity=high"
        resp = json.loads(urllib.request.urlopen(url).read())
        assert resp["pagination"]["limit"] == 2
        assert len(resp["findings"]) == 2
        assert resp["pagination"]["total"] == 5
    finally:
        server.shutdown()


def test_api_auth_rejects_without_key(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("NIGHT_SHIFT_API_KEY", "secret-key")
    findings = [
        Finding(
            finding_id="NSS-0001",
            template_id="governance_capture",
            target_id="",
            severity=Severity.LOW,
            severity_score=0.3,
            economic_impact_usd=1000,
            capital_required_usd=0,
            reproducibility=0.5,
            parameters={},
            invariant_violations=[],
            reproduction_steps=[],
        )
    ]
    paths = export_dataset(findings, {"run_at": "2026-06-06T00:00:00+00:00"}, tmp_path)
    server = serve_background(port=18789, dataset_path=paths["latest"])

    try:
        req = urllib.request.Request("http://127.0.0.1:18789/api/v1/feed")
        try:
            urllib.request.urlopen(req)
            assert False, "expected 401"
        except urllib.error.HTTPError as exc:
            assert exc.code == 401

        req_ok = urllib.request.Request(
            "http://127.0.0.1:18789/api/v1/feed?api_key=secret-key"
        )
        resp = json.loads(urllib.request.urlopen(req_ok).read())
        assert resp["total"] == 1
    finally:
        server.shutdown()
        monkeypatch.delenv("NIGHT_SHIFT_API_KEY", raising=False)