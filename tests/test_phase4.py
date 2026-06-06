"""Phase 4 tests — Foundry harness, catalog seeds, monitoring, bounty, RPC."""

import json
from pathlib import Path
from unittest.mock import patch

from night_shift_security.bounty.pipeline import build_bounty_submission, export_bounty_pack
from night_shift_security.config.loader import gates_from_config, load_config
from night_shift_security.core.pipeline import run_security_pipeline
from night_shift_security.data.exploit_catalog import get_exploit_catalog
from night_shift_security.data.schemas import Finding, Severity
from night_shift_security.domain.simulators.foundry_simulator import FoundrySimulator
from night_shift_security.monitoring.hooks import build_alert_payload, emit_monitoring_event
from night_shift_security.validation.catalog_seeds import evaluate_catalog_seeds, is_catalog_anchor
from night_shift_security.validation.rpc import get_ethereum_rpc, rpc_status

import night_shift_security.domain.attack_templates.governance_capture  # noqa: F401
import night_shift_security.domain.attack_templates.treasury_drain  # noqa: F401
import night_shift_security.domain.attack_templates.flash_loan_oracle  # noqa: F401
import night_shift_security.domain.attack_templates.reentrancy  # noqa: F401
import night_shift_security.domain.attack_templates.composability_risk  # noqa: F401
import night_shift_security.domain.attack_templates.upgradeability_risk  # noqa: F401
import night_shift_security.domain.attack_templates.access_control_escalation  # noqa: F401


def test_catalog_seeds_count_matches_catalog():
    catalog = get_exploit_catalog()
    gates = gates_from_config(load_config())
    seeds = evaluate_catalog_seeds(catalog, gates)
    assert len(seeds) == len(catalog)
    assert all(s.catalog_exploit_id for s in seeds)


def test_catalog_anchor_exempt_from_cpcv_rejection():
    catalog = get_exploit_catalog()
    gates = gates_from_config(load_config())
    seeds = evaluate_catalog_seeds(catalog, gates)
    nomad = next(s for s in seeds if s.catalog_exploit_id == "nomad-bridge-2022")
    assert is_catalog_anchor(nomad, catalog)


def test_foundry_simulator_has_all_template_tests():
    sim = FoundrySimulator()
    if not sim.is_available():
        return
    templates = [
        "governance_capture",
        "treasury_drain",
        "flash_loan_oracle",
        "reentrancy",
        "composability_risk",
        "upgradeability_risk",
        "access_control_escalation",
    ]
    from night_shift_security.domain.simulators.foundry_simulator import _TEMPLATE_TEST_MAP
    for t in templates:
        assert t in _TEMPLATE_TEST_MAP


def test_monitoring_builds_alert_payload():
    findings = [
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
        )
    ]
    payload = build_alert_payload(findings, {"min_severity": "high"})
    assert payload["alert_count"] == 1


def test_monitoring_writes_alert_file(tmp_path: Path):
    findings = [
        Finding(
            finding_id="NSS-0001",
            template_id="reentrancy",
            target_id="",
            severity=Severity.HIGH,
            severity_score=0.8,
            economic_impact_usd=500_000,
            capital_required_usd=0,
            reproducibility=0.9,
            parameters={},
            invariant_violations=[],
            reproduction_steps=[],
        )
    ]
    alert_file = tmp_path / "alerts.jsonl"
    result = emit_monitoring_event(
        findings,
        {"run_at": "2026-06-06T00:00:00+00:00"},
        {"enabled": True, "min_severity": "high", "alert_file": str(alert_file)},
    )
    assert result["emitted"] == 1
    assert alert_file.exists()


def test_bounty_submission_shape():
    finding = Finding(
        finding_id="NSS-0001",
        template_id="access_control_escalation",
        target_id="nomad",
        severity=Severity.CRITICAL,
        severity_score=0.95,
        economic_impact_usd=190_000_000,
        capital_required_usd=0,
        reproducibility=1.0,
        parameters={"use_zero_root": True},
        invariant_violations=[],
        reproduction_steps=[],
        mitigations=["Enforce RBAC"],
        disclosure_status="embargoed",
    )
    sub = build_bounty_submission(finding)
    assert sub["severity"] == "critical"
    assert "reproduction" in sub
    assert sub["disclosure_status"] == "embargoed"


def test_export_bounty_pack(tmp_path: Path):
    findings = [
        Finding(
            finding_id="NSS-0001",
            template_id="treasury_drain",
            target_id="",
            severity=Severity.HIGH,
            severity_score=0.8,
            economic_impact_usd=1_000_000,
            capital_required_usd=0,
            reproducibility=0.9,
            parameters={},
            invariant_violations=[],
            reproduction_steps=[],
        )
    ]
    path = export_bounty_pack(findings, {"run_at": "2026-06-06T00:00:00+00:00"}, tmp_path)
    data = json.loads(path.read_text())
    assert data["submission_count"] == 1


def test_rpc_status_without_env():
    with patch.dict("os.environ", {}, clear=True):
        assert get_ethereum_rpc() == ""
        status = rpc_status()
        assert status["configured"] is False


def test_pipeline_rediscovery_19_of_19():
    result = run_security_pipeline()
    assert result["rediscovery"]["rediscovered"] == 19
    assert result["rediscovery"]["catalog_size"] == 19