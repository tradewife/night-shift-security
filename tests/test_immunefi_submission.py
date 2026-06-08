"""Tests for Immunefi submission pack generation."""

import json
from pathlib import Path

from night_shift_security.data.schemas import (
    Finding,
    InvariantViolation,
    ReproductionStep,
    Severity,
)
from night_shift_security.export.immunefi_submission import (
    build_full_submission_pack,
    export_immunefi_packs,
    generate_immunefi_markdown,
    severity_justification,
)


def _sample_finding(**overrides) -> Finding:
    base = Finding(
        finding_id="NSS-0044",
        template_id="composability_risk",
        target_id="crema_finance",
        severity=Severity.HIGH,
        severity_score=0.41,
        economic_impact_usd=2_640_000.0,
        capital_required_usd=2_000_000.0,
        reproducibility=1.0,
        parameters={"protocol_hops": 3, "leverage_multiplier": 5.0, "use_callback_chain": True},
        solana_evidence={
            "exploit_id": "crema-finance-2022",
            "method": "solana_fixture",
            "slot": 140_000_000,
        },
        invariant_violations=[
            InvariantViolation(
                invariant_id="isolated_protocol_risk",
                description="Cross-protocol exposure must be bounded",
                expected="bounded exposure",
                actual="3-hop chain",
            )
        ],
        reproduction_steps=[
            ReproductionStep("map_protocol_graph", "attacker", {"hops": 3}),
        ],
        mitigations=["Isolate collateral accounting"],
        evidence_grade=4,
        evidence_grade_label="root_cause_artifacts",
        solana_reproduced=True,
        solana_slot=140_000_000,
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


def test_generate_immunefi_markdown_includes_sections():
    md = generate_immunefi_markdown(_sample_finding())
    assert "## Severity Justification" in md
    assert "## Invariant Violations" in md
    assert "isolated_protocol_risk" in md
    assert "map_protocol_graph" in md


def test_severity_justification_mentions_evidence_grade():
    text = severity_justification(_sample_finding())
    assert "evidence grade 4" in text.lower()


def test_build_full_submission_pack_writes_three_files(tmp_path: Path):
    finding = _sample_finding()
    paths = build_full_submission_pack(finding, output_dir=tmp_path)
    assert paths["markdown"].exists()
    assert paths["reproduction_script"].exists()
    assert paths["json"].exists()
    assert paths["reproduction_script"].name.endswith("_repro.sh")
    payload = json.loads(paths["json"].read_text())
    assert payload["evidence_grade"] == 4
    assert payload["severity_justification"]


def test_export_immunefi_packs_filters_by_grade(tmp_path: Path):
    findings = [
        _sample_finding(evidence_grade=4),
        _sample_finding(finding_id="NSS-0001", evidence_grade=1, solana_reproduced=False),
    ]
    result = export_immunefi_packs(
        findings,
        {"run_at": "2026-06-09T00:00:00+00:00"},
        tmp_path,
        min_evidence_grade=3,
    )
    assert result["pack_count"] == 1
    manifest = json.loads(Path(result["manifest_path"]).read_text())
    assert manifest["pack_count"] == 1