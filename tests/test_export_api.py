"""Tests for public dataset export and findings API."""

import json
import urllib.request
from pathlib import Path

from night_shift_security.api.server import serve_background
from night_shift_security.bridge.tokenomics import generate_tokenomics_risk_feed
from night_shift_security.data.schemas import Finding, Severity
from night_shift_security.export.dataset import build_public_feed, export_dataset
from night_shift_security.export.loader import findings_from_run_json


def _sample_findings() -> list[Finding]:
    return [
        Finding(
            finding_id="NSS-0001",
            template_id="governance_capture",
            target_id="",
            severity=Severity.CRITICAL,
            severity_score=0.92,
            economic_impact_usd=1_000_000,
            capital_required_usd=50_000,
            reproducibility=0.95,
            parameters={"voting_power_pct": 51},
            invariant_violations=[],
            reproduction_steps=[],
            mitigations=["Add timelock"],
            confidence=0.9,
            rediscovered_exploit_id="beanstalk-2022",
        ),
        Finding(
            finding_id="NSS-0002",
            template_id="treasury_drain",
            target_id="",
            severity=Severity.HIGH,
            severity_score=0.75,
            economic_impact_usd=500_000,
            capital_required_usd=0,
            reproducibility=0.88,
            parameters={"withdrawal_pct": 80},
            invariant_violations=[],
            reproduction_steps=[],
            mitigations=["Enforce multisig"],
            confidence=0.8,
        ),
    ]


def test_build_public_feed_ranks_by_severity(tmp_path: Path):
    run_meta = {"run_at": "2026-06-06T00:00:00+00:00", "elapsed_seconds": 1.0}
    feed = build_public_feed(_sample_findings(), run_meta)

    assert feed["summary"]["total_findings"] == 2
    assert feed["findings"][0]["finding_id"] == "NSS-0001"
    assert feed["findings"][0]["rank"] == 1
    assert feed["findings"][0]["severity"] == "critical"


def test_export_dataset_writes_artifacts(tmp_path: Path):
    run_meta = {
        "run_at": "2026-06-06T00:00:00+00:00",
        "elapsed_seconds": 1.0,
        "candidates_evaluated": 10,
        "candidates_passed_gates": 2,
        "rediscovery": {"rate": 0.5},
    }
    paths = export_dataset(_sample_findings(), run_meta, tmp_path)

    assert paths["latest"].exists()
    assert paths["feed"].exists()
    assert paths["jsonl"].exists()
    assert paths["tokenomics_bridge"].exists()

    with open(paths["latest"]) as f:
        latest = json.load(f)
    assert latest["summary"]["total_findings"] == 2

    with open(paths["tokenomics_bridge"]) as f:
        bridge = json.load(f)
    assert bridge["source"] == "night-shift-security"
    assert len(bridge["risk_patterns"]) >= 1


def test_tokenomics_bridge_includes_attack_surfaces():
    feed = generate_tokenomics_risk_feed(_sample_findings())
    surfaces = {s["attack_surface"] for s in feed["high_risk_attack_surfaces"]}
    assert "governance" in surfaces
    assert "treasury" in surfaces


def test_findings_from_run_json_roundtrip(tmp_path: Path):
    run_meta = {"run_at": "2026-06-06T00:00:00+00:00", "elapsed_seconds": 1.0}
    export_dataset(_sample_findings(), run_meta, tmp_path)
    run_file = tmp_path / "run.json"
    run_file.write_text(
        json.dumps(
            {
                "run_at": run_meta["run_at"],
                "elapsed_seconds": 1.0,
                "findings": build_public_feed(_sample_findings(), run_meta)["findings"],
            }
        )
    )
    # Rebuild minimal findings.json shape from exported feed
    findings_json = {
        "run_at": run_meta["run_at"],
        "elapsed_seconds": 1.0,
        "candidates_evaluated": 2,
        "candidates_passed_gates": 2,
        "findings": [
            {
                **f,
                "capital_required_usd": 0,
                "reproducibility": 0.9,
                "parameters": {},
                "invariant_violations": [],
                "reproduction_steps": [],
                "mitigations": [],
                "confidence": 0.8,
            }
            for f in build_public_feed(_sample_findings(), run_meta)["findings"]
        ],
    }
    src = tmp_path / "findings.json"
    src.write_text(json.dumps(findings_json))
    loaded, meta = findings_from_run_json(src)
    assert len(loaded) == 2
    assert meta["run_at"] == run_meta["run_at"]


def test_api_serves_endpoints(tmp_path: Path):
    run_meta = {"run_at": "2026-06-06T00:00:00+00:00", "elapsed_seconds": 1.0}
    paths = export_dataset(_sample_findings(), run_meta, tmp_path)
    server = serve_background(port=18787, dataset_path=paths["latest"])

    try:
        health = json.loads(urllib.request.urlopen("http://127.0.0.1:18787/api/v1/health").read())
        assert health["status"] == "ok"
        assert health["findings_loaded"] == 2

        feed = json.loads(urllib.request.urlopen("http://127.0.0.1:18787/api/v1/feed").read())
        assert feed["total"] == 2
        assert "pagination" in feed

        detail = json.loads(
            urllib.request.urlopen("http://127.0.0.1:18787/api/v1/findings/NSS-0001").read()
        )
        assert detail["template_id"] == "governance_capture"

        bridge = json.loads(
            urllib.request.urlopen("http://127.0.0.1:18787/api/v1/bridge/tokenomics").read()
        )
        assert bridge["findings_count"] == 2
    finally:
        server.shutdown()